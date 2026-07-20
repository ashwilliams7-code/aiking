var __defProp = Object.defineProperty;
var __name = (target, value) => __defProp(target, "name", { value, configurable: true });

// ../../api/schemas/lead-request.schema.json
var lead_request_schema_default = {
  $schema: "https://json-schema.org/draft/2020-12/schema",
  $id: "https://aiking.info/schemas/lead-request.schema.json",
  title: "AIKING lead request",
  description: "Data-minimized input for a private briefing request.",
  type: "object",
  additionalProperties: false,
  required: [
    "name",
    "role",
    "organisation",
    "email",
    "timeframe",
    "outcome"
  ],
  properties: {
    name: {
      type: "string",
      minLength: 1,
      maxLength: 100
    },
    role: {
      type: "string",
      minLength: 1,
      maxLength: 120
    },
    organisation: {
      type: "string",
      minLength: 1,
      maxLength: 160
    },
    email: {
      type: "string",
      format: "email",
      maxLength: 254
    },
    timeframe: {
      type: "string",
      enum: [
        "exploring_now",
        "next_30_days",
        "next_quarter",
        "later_this_year"
      ]
    },
    maturity: {
      type: "string",
      enum: [
        "not_started",
        "individual_tools",
        "pilots_underway",
        "systems_in_production"
      ]
    },
    outcome: {
      type: "string",
      minLength: 20,
      maxLength: 2e3
    },
    website: {
      type: "string",
      maxLength: 0,
      description: "Honeypot field. Browser clients leave this empty; a non-empty value fails validation."
    },
    ref: {
      type: "string",
      pattern: "^BRF-[A-Z0-9]{4}$",
      description: "Client-generated briefing reference shown to the requester."
    },
    page: {
      type: "string",
      maxLength: 200,
      description: "Site path the briefing form was submitted from."
    }
  }
};

// worker.js
var ENDPOINT = "/v1/lead-requests";
var EXPORT_ENDPOINT = "/v1/lead-exports";
var MAX_BODY_BYTES = 16384;
var IDEMPOTENCY_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._:-]{15,127}$/;
var EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
var RATE_LIMIT = 5;
var RATE_WINDOW_SECONDS = 60;
var IDEMPOTENCY_TTL_SECONDS = 86400;
function errorResponse(code, message, fields) {
  const error = { code, message };
  if (fields && fields.length) error.fields = fields;
  return { error };
}
__name(errorResponse, "errorResponse");
function json(status, body, headers = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "no-store",
      ...headers
    }
  });
}
__name(json, "json");
function parseStrictJson(text) {
  const value = JSON.parse(text);
  let i = 0;
  function skipWs() {
    while (i < text.length && /[\s]/.test(text[i])) i++;
  }
  __name(skipWs, "skipWs");
  function scanString() {
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
  __name(scanString, "scanString");
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
      for (; ; ) {
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
  __name(scanValue, "scanValue");
  function scanObject() {
    const seen = /* @__PURE__ */ new Set();
    i++;
    skipWs();
    if (text[i] === "}") {
      i++;
      return;
    }
    for (; ; ) {
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
  __name(scanObject, "scanObject");
  skipWs();
  if (text[i] === "{") scanObject();
  else scanValue();
  return value;
}
__name(parseStrictJson, "parseStrictJson");
function validatePayload(payload) {
  if (typeof payload !== "object" || payload === null || Array.isArray(payload)) {
    return [{ field: "$", code: "invalid_type" }];
  }
  const errors = [];
  const properties = lead_request_schema_default.properties;
  for (const field of lead_request_schema_default.required) {
    if (!(field in payload)) errors.push({ field, code: "required" });
  }
  if (lead_request_schema_default.additionalProperties === false) {
    for (const key of Object.keys(payload)) {
      if (!(key in properties)) {
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
__name(validatePayload, "validatePayload");
function canonicalFingerprintInput(value) {
  if (value === null || typeof value === "number" || typeof value === "boolean") {
    return JSON.stringify(value);
  }
  if (typeof value === "string") {
    return JSON.stringify(value).replace(
      /[\u007f-\uffff]/g,
      (c) => "\\u" + c.charCodeAt(0).toString(16).padStart(4, "0")
    );
  }
  if (Array.isArray(value)) {
    return "[" + value.map(canonicalFingerprintInput).join(",") + "]";
  }
  return "{" + Object.keys(value).sort().map((k) => canonicalFingerprintInput(k) + ":" + canonicalFingerprintInput(value[k])).join(",") + "}";
}
__name(canonicalFingerprintInput, "canonicalFingerprintInput");
async function sha256Hex(text) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}
__name(sha256Hex, "sha256Hex");
async function applyRateLimit(env, clientId) {
  const key = `rl:${clientId}`;
  const nowSec = Date.now() / 1e3;
  let attempts = [];
  try {
    attempts = JSON.parse(await env.LEADS.get(key) || "[]");
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
    expirationTtl: Math.max(RATE_WINDOW_SECONDS, 60)
  });
  return {
    limited: false,
    headers: {
      "RateLimit-Limit": String(RATE_LIMIT),
      "RateLimit-Remaining": String(RATE_LIMIT - recent.length)
    }
  };
}
__name(applyRateLimit, "applyRateLimit");
async function handleSubmit(request, env) {
  const contentType = (request.headers.get("Content-Type") || "").split(";")[0].trim();
  if (contentType.toLowerCase() !== "application/json") {
    return json(415, errorResponse("unsupported_media_type", "Content-Type must be application/json."));
  }
  const raw = await request.text();
  if (raw.length < 1 || new TextEncoder().encode(raw).length > MAX_BODY_BYTES) {
    return json(400, errorResponse("invalid_json", "Request body must be valid JSON."));
  }
  const idempotencyKey = request.headers.get("Idempotency-Key");
  if (!idempotencyKey || !IDEMPOTENCY_PATTERN.test(idempotencyKey)) {
    return json(
      422,
      errorResponse("invalid_request", "One or more fields are invalid.", [
        { field: "Idempotency-Key", code: "invalid_format" }
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
      "Retry-After": String(rate.retryAfter)
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
    expirationTtl: IDEMPOTENCY_TTL_SECONDS
  });
  const receivedAt = (/* @__PURE__ */ new Date()).toISOString();
  await env.LEADS.put(
    `lead:${receivedAt}:${requestId}`,
    JSON.stringify({
      request_id: requestId,
      received_at: receivedAt,
      country: request.cf?.country || null,
      payload
    })
  );
  return json(202, { request_id: requestId, status: "accepted", duplicate: false }, rate.headers);
}
__name(handleSubmit, "handleSubmit");
async function handleExport(request, env) {
  const auth = request.headers.get("Authorization") || "";
  const token = auth.startsWith("Bearer ") ? auth.slice(7) : "";
  if (!env.EXPORT_TOKEN || token !== env.EXPORT_TOKEN) {
    return json(401, errorResponse("unauthorized", "A valid export token is required."));
  }
  const list = await env.LEADS.list({ prefix: "lead:", limit: 1e3 });
  const leads = [];
  for (const key of list.keys) {
    const lead = await env.LEADS.get(key.name, "json");
    if (lead) leads.push(lead);
  }
  return json(200, { count: leads.length, leads });
}
__name(handleExport, "handleExport");
var worker_default = {
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
          Allow: "GET"
        });
      }
      return handleExport(request, env);
    }
    return json(404, errorResponse("invalid_request", "Requested endpoint was not found."));
  }
};

// ../../../../.npm/_npx/d77349f55c2be1c0/node_modules/wrangler/templates/middleware/middleware-ensure-req-body-drained.ts
var drainBody = /* @__PURE__ */ __name(async (request, env, _ctx, middlewareCtx) => {
  try {
    return await middlewareCtx.next(request, env);
  } finally {
    try {
      if (request.body !== null && !request.bodyUsed) {
        const reader = request.body.getReader();
        while (!(await reader.read()).done) {
        }
      }
    } catch (e) {
      console.error("Failed to drain the unused request body.", e);
    }
  }
}, "drainBody");
var middleware_ensure_req_body_drained_default = drainBody;

// ../../../../.npm/_npx/d77349f55c2be1c0/node_modules/wrangler/templates/middleware/middleware-miniflare3-json-error.ts
function reduceError(e) {
  return {
    name: e?.name,
    message: e?.message ?? String(e),
    stack: e?.stack,
    cause: e?.cause === void 0 ? void 0 : reduceError(e.cause)
  };
}
__name(reduceError, "reduceError");
var jsonError = /* @__PURE__ */ __name(async (request, env, _ctx, middlewareCtx) => {
  try {
    return await middlewareCtx.next(request, env);
  } catch (e) {
    const error = reduceError(e);
    return Response.json(error, {
      status: 500,
      headers: { "MF-Experimental-Error-Stack": "true" }
    });
  }
}, "jsonError");
var middleware_miniflare3_json_error_default = jsonError;

// .wrangler/tmp/bundle-99pseF/middleware-insertion-facade.js
var __INTERNAL_WRANGLER_MIDDLEWARE__ = [
  middleware_ensure_req_body_drained_default,
  middleware_miniflare3_json_error_default
];
var middleware_insertion_facade_default = worker_default;

// ../../../../.npm/_npx/d77349f55c2be1c0/node_modules/wrangler/templates/middleware/common.ts
var __facade_middleware__ = [];
function __facade_register__(...args) {
  __facade_middleware__.push(...args.flat());
}
__name(__facade_register__, "__facade_register__");
function __facade_invokeChain__(request, env, ctx, dispatch, middlewareChain) {
  const [head, ...tail] = middlewareChain;
  const middlewareCtx = {
    dispatch,
    next(newRequest, newEnv) {
      return __facade_invokeChain__(newRequest, newEnv, ctx, dispatch, tail);
    }
  };
  return head(request, env, ctx, middlewareCtx);
}
__name(__facade_invokeChain__, "__facade_invokeChain__");
function __facade_invoke__(request, env, ctx, dispatch, finalMiddleware) {
  return __facade_invokeChain__(request, env, ctx, dispatch, [
    ...__facade_middleware__,
    finalMiddleware
  ]);
}
__name(__facade_invoke__, "__facade_invoke__");

// .wrangler/tmp/bundle-99pseF/middleware-loader.entry.ts
var __Facade_ScheduledController__ = class ___Facade_ScheduledController__ {
  constructor(scheduledTime, cron, noRetry) {
    this.scheduledTime = scheduledTime;
    this.cron = cron;
    this.#noRetry = noRetry;
  }
  scheduledTime;
  cron;
  static {
    __name(this, "__Facade_ScheduledController__");
  }
  #noRetry;
  noRetry() {
    if (!(this instanceof ___Facade_ScheduledController__)) {
      throw new TypeError("Illegal invocation");
    }
    this.#noRetry();
  }
};
function wrapExportedHandler(worker) {
  if (__INTERNAL_WRANGLER_MIDDLEWARE__ === void 0 || __INTERNAL_WRANGLER_MIDDLEWARE__.length === 0) {
    return worker;
  }
  for (const middleware of __INTERNAL_WRANGLER_MIDDLEWARE__) {
    __facade_register__(middleware);
  }
  const fetchDispatcher = /* @__PURE__ */ __name(function(request, env, ctx) {
    if (worker.fetch === void 0) {
      throw new Error("Handler does not export a fetch() function.");
    }
    return worker.fetch(request, env, ctx);
  }, "fetchDispatcher");
  return {
    ...worker,
    fetch(request, env, ctx) {
      const dispatcher = /* @__PURE__ */ __name(function(type, init) {
        if (type === "scheduled" && worker.scheduled !== void 0) {
          const controller = new __Facade_ScheduledController__(
            Date.now(),
            init.cron ?? "",
            () => {
            }
          );
          return worker.scheduled(controller, env, ctx);
        }
      }, "dispatcher");
      return __facade_invoke__(request, env, ctx, dispatcher, fetchDispatcher);
    }
  };
}
__name(wrapExportedHandler, "wrapExportedHandler");
function wrapWorkerEntrypoint(klass) {
  if (__INTERNAL_WRANGLER_MIDDLEWARE__ === void 0 || __INTERNAL_WRANGLER_MIDDLEWARE__.length === 0) {
    return klass;
  }
  for (const middleware of __INTERNAL_WRANGLER_MIDDLEWARE__) {
    __facade_register__(middleware);
  }
  return class extends klass {
    #fetchDispatcher = /* @__PURE__ */ __name((request, env, ctx) => {
      this.env = env;
      this.ctx = ctx;
      if (super.fetch === void 0) {
        throw new Error("Entrypoint class does not define a fetch() function.");
      }
      return super.fetch(request);
    }, "#fetchDispatcher");
    #dispatcher = /* @__PURE__ */ __name((type, init) => {
      if (type === "scheduled" && super.scheduled !== void 0) {
        const controller = new __Facade_ScheduledController__(
          Date.now(),
          init.cron ?? "",
          () => {
          }
        );
        return super.scheduled(controller);
      }
    }, "#dispatcher");
    fetch(request) {
      return __facade_invoke__(
        request,
        this.env,
        this.ctx,
        this.#dispatcher,
        this.#fetchDispatcher
      );
    }
  };
}
__name(wrapWorkerEntrypoint, "wrapWorkerEntrypoint");
var WRAPPED_ENTRY;
if (typeof middleware_insertion_facade_default === "object") {
  WRAPPED_ENTRY = wrapExportedHandler(middleware_insertion_facade_default);
} else if (typeof middleware_insertion_facade_default === "function") {
  WRAPPED_ENTRY = wrapWorkerEntrypoint(middleware_insertion_facade_default);
}
var middleware_loader_entry_default = WRAPPED_ENTRY;
export {
  __INTERNAL_WRANGLER_MIDDLEWARE__,
  middleware_loader_entry_default as default
};
//# sourceMappingURL=worker.js.map
