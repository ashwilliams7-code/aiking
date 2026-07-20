/**
 * AIKING lead capture — Cloudflare Worker implementing
 * api/lead-capture.openapi.json (POST /v1/lead-requests).
 *
 * Mirrors the checked-in mock (api/mock_server.py): same status codes,
 * error envelope, field-error codes, idempotency and rate-limit semantics.
 * HTTP framing edges (Host/Content-Length/Transfer-Encoding games) are
 * handled by the Workers runtime before this code runs.
 *
 * Bindings:
 *   LEADS        KV namespace — leads, idempotency records, rate windows
 *   EXPORT_TOKEN secret — bearer token for GET /v1/lead-exports
 */

const ENDPOINT = "/v1/lead-requests";
const EXPORT_ENDPOINT = "/v1/lead-exports";
const MAX_BODY_BYTES = 16_384;
const IDEMPOTENCY_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._:-]{15,127}$/;
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const RATE_LIMIT = 5;
const RATE_WINDOW_SECONDS = 60;
const IDEMPOTENCY_TTL_SECONDS = 86_400;

import schema from "../../api/schemas/lead-request.schema.json";

function errorResponse(code, message, fields) {
  const error = { code, message };
  if (fields && fields.length) error.fields = fields;
  return { error };
}

function json(status, body, headers = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "no-store",
      ...headers,
    },
  });
}

/**
 * Parse JSON while rejecting objects that repeat a member name, matching
 * reject_duplicate_json_members in the mock. JSON.parse silently keeps the
 * last duplicate, so scan the raw text with a minimal tokenizer.
 */
function parseStrictJson(text) {
  const value = JSON.parse(text); // throws on malformed JSON first
  let i = 0;

  function skipWs() {
    while (i < text.length && /[\s]/.test(text[i])) i++;
  }

  function scanString() {
    // assumes text[i] === '"'
    let out = "";
    i++;
    while (i < text.length) {
      const c = text[i];
      if (c === "\\") {
        out += text[i + 1] === "u" ? text.slice(i, i + 6) : text.slice(i, i + 2);
        i += text[i + 1] === "u" ? 6 : 2;
        continue;
      }
      if (c === '"') {
        i++;
        return out;
      }
      out += c;
      i++;
    }
    throw new Error("unterminated string");
  }

  function scanValue() {
    skipWs();
    const c = text[i];
    if (c === '"') {
      scanString();
    } else if (c === "{") {
      scanObject();
    } else if (c === "[") {
      i++;
      skipWs();
      if (text[i] === "]") {
        i++;
        return;
      }
      for (;;) {
        scanValue();
        skipWs();
        if (text[i] === ",") {
          i++;
          continue;
        }
        if (text[i] === "]") {
          i++;
          return;
        }
        throw new Error("bad array");
      }
    } else {
      while (i < text.length && !/[\s,\]}]/.test(text[i])) i++;
    }
  }

  function scanObject() {
    // assumes text[i] === '{'
    const seen = new Set();
    i++;
    skipWs();
    if (text[i] === "}") {
      i++;
      return;
    }
    for (;;) {
      skipWs();
      if (text[i] !== '"') throw new Error("bad object key");
      const key = scanString();
      if (seen.has(key)) throw new Error("duplicate JSON member");
      seen.add(key);
      skipWs();
      if (text[i] !== ":") throw new Error("bad object");
      i++;
      scanValue();
      skipWs();
      if (text[i] === ",") {
        i++;
        continue;
      }
      if (text[i] === "}") {
        i++;
        return;
      }
      throw new Error("bad object");
    }
  }

  skipWs();
  if (text[i] === "{") scanObject();
  else scanValue();
  return value;
}

/** Port of validate_payload in api/mock_server.py — same codes, same order. */
function validatePayload(payload) {
  if (typeof payload !== "object" || payload === null || Array.isArray(payload)) {
    return [{ field: "$", code: "invalid_type" }];
  }
  const errors = [];
  const properties = schema.properties;

  for (const field of schema.required) {
    if (!(field in payload)) errors.push({ field, code: "required" });
  }

  if (schema.additionalProperties === false) {
    for (const key of Object.keys(payload)) {
      if (!(key in properties)) {
        // Do not reflect attacker-controlled property names in the response.
        errors.push({ field: "$", code: "additional_property" });
        break;
      }
    }
  }

  for (const [field, value] of Object.entries(payload)) {
    const fieldSchema = properties[field];
    if (!fieldSchema) continue;
    if (fieldSchema.type === "string" && typeof value !== "string") {
      errors.push({ field, code: "invalid_type" });
      continue;
    }
    if (typeof value === "string") {
      const chars = [...value].length;
      if (chars < (fieldSchema.minLength ?? 0)) errors.push({ field, code: "too_short" });
      if (chars > (fieldSchema.maxLength ?? chars)) errors.push({ field, code: "too_long" });
      if (fieldSchema.enum && !fieldSchema.enum.includes(value))
        errors.push({ field, code: "invalid_choice" });
      if (fieldSchema.format === "email" && !EMAIL_PATTERN.test(value))
        errors.push({ field, code: "invalid_format" });
      if (fieldSchema.pattern && !new RegExp(fieldSchema.pattern).test(value))
        errors.push({ field, code: "invalid_format" });
    }
  }
  return errors.slice(0, 20);
}

function canonicalFingerprintInput(value) {
  // Match json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=True)
  if (value === null || typeof value === "number" || typeof value === "boolean") {
    return JSON.stringify(value);
  }
  if (typeof value === "string") {
    return JSON.stringify(value).replace(/[\u007f-\uffff]/g, (c) =>
      "\\u" + c.charCodeAt(0).toString(16).padStart(4, "0")
    );
  }
  if (Array.isArray(value)) {
    return "[" + value.map(canonicalFingerprintInput).join(",") + "]";
  }
  return (
    "{" +
    Object.keys(value)
      .sort()
      .map((k) => canonicalFingerprintInput(k) + ":" + canonicalFingerprintInput(value[k]))
      .join(",") +
    "}"
  );
}

async function sha256Hex(text) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

async function applyRateLimit(env, clientId) {
  const key = `rl:${clientId}`;
  const nowSec = Date.now() / 1000;
  let attempts = [];
  try {
    attempts = JSON.parse((await env.LEADS.get(key)) || "[]");
  } catch (_) {
    attempts = [];
  }
  const recent = attempts.filter((t) => nowSec - t < RATE_WINDOW_SECONDS);
  if (recent.length >= RATE_LIMIT) {
    const retryAfter = Math.max(1, Math.ceil(RATE_WINDOW_SECONDS - (nowSec - recent[0])));
    return { limited: true, retryAfter };
  }
  recent.push(nowSec);
  await env.LEADS.put(key, JSON.stringify(recent), {
    expirationTtl: Math.max(RATE_WINDOW_SECONDS, 60),
  });
  return {
    limited: false,
    headers: {
      "RateLimit-Limit": String(RATE_LIMIT),
      "RateLimit-Remaining": String(RATE_LIMIT - recent.length),
    },
  };
}

async function handleSubmit(request, env) {
  const contentType = (request.headers.get("Content-Type") || "").split(";")[0].trim();
  if (contentType.toLowerCase() !== "application/json") {
    return json(415, errorResponse("unsupported_media_type", "Content-Type must be application/json."));
  }

  const raw = await request.text();
  if (raw.length < 1 || new TextEncoder().encode(raw).length > MAX_BODY_BYTES) {
    return json(400, errorResponse("invalid_json", "Request body must be valid JSON."));
  }

  // A duplicated Idempotency-Key header arrives comma-joined and fails the
  // pattern, matching the mock's single-header requirement.
  const idempotencyKey = request.headers.get("Idempotency-Key");
  if (!idempotencyKey || !IDEMPOTENCY_PATTERN.test(idempotencyKey)) {
    return json(
      422,
      errorResponse("invalid_request", "One or more fields are invalid.", [
        { field: "Idempotency-Key", code: "invalid_format" },
      ])
    );
  }

  let payload;
  try {
    payload = parseStrictJson(raw);
  } catch (_) {
    return json(400, errorResponse("invalid_json", "Request body must be valid JSON."));
  }

  const fieldErrors = validatePayload(payload);
  if (fieldErrors.length) {
    return json(422, errorResponse("invalid_request", "One or more fields are invalid.", fieldErrors));
  }

  const clientId = request.headers.get("CF-Connecting-IP") || "local";
  const rate = await applyRateLimit(env, clientId);
  if (rate.limited) {
    return json(429, errorResponse("rate_limited", "Too many requests. Try again later."), {
      "Retry-After": String(rate.retryAfter),
    });
  }

  const fingerprint = await sha256Hex(canonicalFingerprintInput(payload));
  const idemKvKey = `idem:${idempotencyKey}`;
  const existing = await env.LEADS.get(idemKvKey, "json");
  if (existing) {
    if (existing.fingerprint !== fingerprint) {
      return json(
        409,
        errorResponse("idempotency_conflict", "Idempotency key was already used for a different request."),
        rate.headers
      );
    }
    return json(202, { request_id: existing.request_id, status: "accepted", duplicate: true }, rate.headers);
  }

  const requestId = crypto.randomUUID();
  await env.LEADS.put(idemKvKey, JSON.stringify({ fingerprint, request_id: requestId }), {
    expirationTtl: IDEMPOTENCY_TTL_SECONDS,
  });

  const receivedAt = new Date().toISOString();
  await env.LEADS.put(
    `lead:${receivedAt}:${requestId}`,
    JSON.stringify({
      request_id: requestId,
      received_at: receivedAt,
      country: request.cf?.country || null,
      payload,
    })
  );

  return json(202, { request_id: requestId, status: "accepted", duplicate: false }, rate.headers);
}

async function handleExport(request, env) {
  const auth = request.headers.get("Authorization") || "";
  const token = auth.startsWith("Bearer ") ? auth.slice(7) : "";
  if (!env.EXPORT_TOKEN || token !== env.EXPORT_TOKEN) {
    return json(401, errorResponse("unauthorized", "A valid export token is required."));
  }
  const list = await env.LEADS.list({ prefix: "lead:", limit: 1000 });
  const leads = [];
  for (const key of list.keys) {
    const lead = await env.LEADS.get(key.name, "json");
    if (lead) leads.push(lead);
  }
  return json(200, { count: leads.length, leads });
}

export default {
  async fetch(request, env) {
    const path = new URL(request.url).pathname;

    if (path === ENDPOINT) {
      if (request.method !== "POST") {
        return json(
          405,
          errorResponse("invalid_request", "Method is not supported for this endpoint."),
          { Allow: "POST" }
        );
      }
      return handleSubmit(request, env);
    }

    if (path === EXPORT_ENDPOINT) {
      if (request.method !== "GET") {
        return json(405, errorResponse("invalid_request", "Method is not supported for this endpoint."), {
          Allow: "GET",
        });
      }
      return handleExport(request, env);
    }

    return json(404, errorResponse("invalid_request", "Requested endpoint was not found."));
  },
};
