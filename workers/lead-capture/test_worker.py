#!/usr/bin/env python3
"""Contract tests for the deployed/dev lead-capture Worker.

Run against `npx wrangler dev` (default http://127.0.0.1:8787) or a deployed
origin: python3 test_worker.py [base_url]

Ports the application-level cases from tests/test_lead_capture_mock.py;
HTTP-framing edges are the runtime's job and are not repeated here.
"""
import json
import sys
import urllib.request
import urllib.error
import uuid

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8787"
ENDPOINT = BASE + "/v1/lead-requests"

PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("PASS", name)
    else:
        FAIL += 1
        print("FAIL", name, "—", detail)


def call(method="POST", path="/v1/lead-requests", body=None, headers=None, raw=None):
    data = raw.encode() if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(BASE + path, data=data, method=method)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, dict(r.headers), json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), json.loads(e.read() or b"{}")


def key():
    return "BRF-TEST:" + str(uuid.uuid4())


def valid_payload(**over):
    p = {
        "name": "Test Person",
        "role": "Director",
        "organisation": "Example Pty Ltd",
        "email": "test@example.com",
        "timeframe": "next_30_days",
        "maturity": "pilots_underway",
        "outcome": "We want reporting and follow-up handled by controlled agents.",
        "website": "",
        "ref": "BRF-TT01",
        "page": "/contact.html",
    }
    p.update(over)
    return p


JSONCT = {"Content-Type": "application/json"}

# --- happy path -----------------------------------------------------------
k = key()
s, h, b = call(body=valid_payload(), headers={**JSONCT, "Idempotency-Key": k})
check("accepts valid submission with 202", s == 202, (s, b))
check("returns request_id", isinstance(b.get("request_id"), str) and len(b["request_id"]) > 10, b)
check("duplicate false on first accept", b.get("duplicate") is False, b)
check("rate limit headers present", "RateLimit-Remaining" in h, h)
rid = b.get("request_id")

# --- idempotency ----------------------------------------------------------
s, h, b = call(body=valid_payload(), headers={**JSONCT, "Idempotency-Key": k})
check("idempotent replay returns 202 duplicate", s == 202 and b.get("duplicate") is True, (s, b))
check("replay returns same request_id", b.get("request_id") == rid, b)

s, h, b = call(body=valid_payload(name="Different Person"), headers={**JSONCT, "Idempotency-Key": k})
check("conflicting reuse returns 409", s == 409 and b["error"]["code"] == "idempotency_conflict", (s, b))

s, h, b = call(body=valid_payload(), headers=JSONCT)
check("missing idempotency key is 422", s == 422 and b["error"]["fields"][0]["field"] == "Idempotency-Key", (s, b))

s, h, b = call(body=valid_payload(), headers={**JSONCT, "Idempotency-Key": "short"})
check("malformed idempotency key is 422", s == 422, (s, b))

# --- validation -----------------------------------------------------------
p = valid_payload()
del p["name"]
s, h, b = call(body=p, headers={**JSONCT, "Idempotency-Key": key()})
check("missing required field is 422", s == 422 and {"field": "name", "code": "required"} in b["error"]["fields"], (s, b))

s, h, b = call(body=valid_payload(extra="x"), headers={**JSONCT, "Idempotency-Key": key()})
check("additional property rejected without echo", s == 422 and {"field": "$", "code": "additional_property"} in b["error"]["fields"] and "extra" not in json.dumps(b), (s, b))

s, h, b = call(body=valid_payload(website="http://spam.example"), headers={**JSONCT, "Idempotency-Key": key()})
check("honeypot value rejected", s == 422 and any(f["field"] == "website" for f in b["error"]["fields"]), (s, b))

s, h, b = call(body=valid_payload(email="not-an-email"), headers={**JSONCT, "Idempotency-Key": key()})
check("invalid email is 422", s == 422 and any(f == {"field": "email", "code": "invalid_format"} for f in b["error"]["fields"]), (s, b))

s, h, b = call(body=valid_payload(timeframe="tomorrow"), headers={**JSONCT, "Idempotency-Key": key()})
check("enum violation is 422", s == 422 and any(f["code"] == "invalid_choice" for f in b["error"]["fields"]), (s, b))

s, h, b = call(body=valid_payload(outcome="too short"), headers={**JSONCT, "Idempotency-Key": key()})
check("short outcome is 422", s == 422 and any(f == {"field": "outcome", "code": "too_short"} for f in b["error"]["fields"]), (s, b))

s, h, b = call(body=valid_payload(ref="WRONG"), headers={**JSONCT, "Idempotency-Key": key()})
check("bad ref pattern is 422", s == 422 and any(f["field"] == "ref" for f in b["error"]["fields"]), (s, b))

s, h, b = call(body=valid_payload(name=123), headers={**JSONCT, "Idempotency-Key": key()})
check("non-string field is 422 invalid_type", s == 422 and any(f == {"field": "name", "code": "invalid_type"} for f in b["error"]["fields"]), (s, b))

s, h, b = call(body=["not", "an", "object"], headers={**JSONCT, "Idempotency-Key": key()})
check("non-object payload is 422", s == 422 and b["error"]["fields"] == [{"field": "$", "code": "invalid_type"}], (s, b))

# --- body / parsing -------------------------------------------------------
s, h, b = call(raw="{not json", headers={**JSONCT, "Idempotency-Key": key()})
check("malformed JSON is 400", s == 400 and b["error"]["code"] == "invalid_json", (s, b))

s, h, b = call(raw='{"name":"A","name":"B"}', headers={**JSONCT, "Idempotency-Key": key()})
check("duplicate JSON members rejected", s == 400 and b["error"]["code"] == "invalid_json", (s, b))

s, h, b = call(raw="", headers={**JSONCT, "Idempotency-Key": key()})
check("empty body is 400", s == 400, (s, b))

s, h, b = call(raw=json.dumps(valid_payload(outcome="x" * 20000)), headers={**JSONCT, "Idempotency-Key": key()})
check("oversized body is 400", s == 400 and b["error"]["code"] == "invalid_json", (s, b))

nested = valid_payload()
s, h, b = call(raw='{"a":{"b":1,"b":2},"name":"x"}', headers={**JSONCT, "Idempotency-Key": key()})
check("nested duplicate members rejected", s == 400, (s, b))

# --- content type / method / path ----------------------------------------
s, h, b = call(body=valid_payload(), headers={"Content-Type": "text/plain", "Idempotency-Key": key()})
check("wrong content type is 415", s == 415 and b["error"]["code"] == "unsupported_media_type", (s, b))

s, h, b = call(raw=json.dumps(valid_payload()), headers={"Idempotency-Key": key()})
check("urlencoded default content type is 415", s == 415, (s, b))

s, h, b = call(body=valid_payload(), headers={"Content-Type": "application/json; charset=utf-8", "Idempotency-Key": key()})
check("json with charset accepted", s == 202, (s, b))

s, h, b = call(method="GET")
check("GET is 405 with Allow", s == 405 and h.get("Allow") == "POST", (s, h))

s, h, b = call(method="DELETE")
check("DELETE is 405", s == 405, s)

s, h, b = call(method="POST", path="/v1/nope", body=valid_payload(), headers={**JSONCT, "Idempotency-Key": key()})
check("unknown path is 404", s == 404 and b["error"]["code"] == "invalid_request", (s, b))

# --- rate limiting (dev-only: single client id) ---------------------------
statuses = []
for i in range(7):
    s, h, b = call(body=valid_payload(outcome=f"Rate limit probe number {i} with enough length."), headers={**JSONCT, "Idempotency-Key": key()})
    statuses.append(s)
check("rate limit kicks in within window", 429 in statuses, statuses)
if 429 in statuses:
    idx = statuses.index(429)
    s, h, b = call(body=valid_payload(), headers={**JSONCT, "Idempotency-Key": key()})
    check("rate limited response has Retry-After", s != 429 or "Retry-After" in h, h)

# --- export auth ----------------------------------------------------------
s, h, b = call(method="GET", path="/v1/lead-exports")
check("export without token is 401", s == 401, (s, b))
s, h, b = call(method="GET", path="/v1/lead-exports", headers={"Authorization": "Bearer wrong"})
check("export with wrong token is 401", s == 401, (s, b))

print(f"\n{PASS}/{PASS + FAIL} passed")
sys.exit(1 if FAIL else 0)
