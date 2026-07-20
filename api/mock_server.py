"""Loopback-only, in-memory mock for the AIKING lead-capture contract.

This module has no notification, email, CRM, persistence, or other outbound
integration. It intentionally stores only idempotency fingerprints and opaque
request IDs for the lifetime of the process.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "api" / "schemas" / "lead-request.schema.json"
ENDPOINT = "/v1/lead-requests"
MAX_BODY_BYTES = 16_384
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{15,127}$")
CONTENT_LENGTH_PATTERN = re.compile(r"^[0-9]+$")
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def load_schema() -> dict[str, Any]:
    with SCHEMA_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def reject_duplicate_json_members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Build a JSON object while rejecting ambiguous repeated member names."""
    result: dict[str, Any] = {}
    for name, value in pairs:
        if name in result:
            raise ValueError("duplicate JSON member")
        result[name] = value
    return result


def validate_payload(schema: dict[str, Any], payload: Any) -> list[dict[str, str]]:
    """Validate the request keywords used by the checked-in JSON Schema."""
    if not isinstance(payload, dict):
        return [{"field": "$", "code": "invalid_type"}]

    errors: list[dict[str, str]] = []
    properties = schema["properties"]
    for field in schema["required"]:
        if field not in payload:
            errors.append({"field": field, "code": "required"})

    if schema.get("additionalProperties") is False:
        if payload.keys() - properties.keys():
            # Do not reflect attacker-controlled property names in the response.
            errors.append({"field": "$", "code": "additional_property"})

    for field, value in payload.items():
        field_schema = properties.get(field)
        if field_schema is None:
            continue
        if field_schema.get("type") == "string" and not isinstance(value, str):
            errors.append({"field": field, "code": "invalid_type"})
            continue
        if isinstance(value, str):
            if len(value) < field_schema.get("minLength", 0):
                errors.append({"field": field, "code": "too_short"})
            if len(value) > field_schema.get("maxLength", len(value)):
                errors.append({"field": field, "code": "too_long"})
            if value not in field_schema.get("enum", [value]):
                errors.append({"field": field, "code": "invalid_choice"})
            if field_schema.get("format") == "email" and not EMAIL_PATTERN.fullmatch(value):
                errors.append({"field": field, "code": "invalid_format"})
            pattern = field_schema.get("pattern")
            if pattern is not None and re.fullmatch(pattern.strip("^$"), value) is None:
                errors.append({"field": field, "code": "invalid_format"})

    return errors[:20]


def error_response(
    code: str, message: str, fields: list[dict[str, str]] | None = None
) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if fields:
        error["fields"] = fields
    return {"error": error}


class LeadCaptureMock:
    """Thread-safe application state with bounded, in-memory abuse controls."""

    def __init__(
        self,
        *,
        rate_limit: int = 5,
        rate_window_seconds: int = 60,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if rate_limit < 1 or rate_window_seconds < 1:
            raise ValueError("rate limit and window must be positive")
        self.schema = load_schema()
        self.rate_limit = rate_limit
        self.rate_window_seconds = rate_window_seconds
        self.clock = clock
        self._accepted: dict[str, dict[str, str]] = {}
        self._attempts: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def submit(
        self, idempotency_key: str | None, payload: Any, client_id: str
    ) -> tuple[int, dict[str, str], dict[str, Any]]:
        if idempotency_key is None or not IDEMPOTENCY_PATTERN.fullmatch(idempotency_key):
            return (
                422,
                {},
                error_response(
                    "invalid_request",
                    "One or more fields are invalid.",
                    [{"field": "Idempotency-Key", "code": "invalid_format"}],
                ),
            )

        fields = validate_payload(self.schema, payload)
        if fields:
            return (
                422,
                {},
                error_response(
                    "invalid_request", "One or more fields are invalid.", fields
                ),
            )

        canonical = json.dumps(
            payload, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        fingerprint = hashlib.sha256(canonical).hexdigest()

        with self._lock:
            now = self.clock()
            recent = [
                attempt
                for attempt in self._attempts.get(client_id, [])
                if now - attempt < self.rate_window_seconds
            ]
            if len(recent) >= self.rate_limit:
                self._attempts[client_id] = recent
                retry_after = max(
                    1, math.ceil(self.rate_window_seconds - (now - recent[0]))
                )
                return (
                    429,
                    {"Retry-After": str(retry_after)},
                    error_response(
                        "rate_limited", "Too many requests. Try again later."
                    ),
                )

            recent.append(now)
            self._attempts[client_id] = recent
            rate_headers = {
                "RateLimit-Limit": str(self.rate_limit),
                "RateLimit-Remaining": str(self.rate_limit - len(recent)),
            }

            existing = self._accepted.get(idempotency_key)
            if existing is not None:
                if existing["fingerprint"] != fingerprint:
                    return (
                        409,
                        rate_headers,
                        error_response(
                            "idempotency_conflict",
                            "Idempotency key was already used for a different request.",
                        ),
                    )
                return (
                    202,
                    rate_headers,
                    {
                        "request_id": existing["request_id"],
                        "status": "accepted",
                        "duplicate": True,
                    },
                )

            request_id = str(uuid.uuid4())
            self._accepted[idempotency_key] = {
                "fingerprint": fingerprint,
                "request_id": request_id,
            }
            return (
                202,
                rate_headers,
                {
                    "request_id": request_id,
                    "status": "accepted",
                    "duplicate": False,
                },
            )


class LeadCaptureHandler(BaseHTTPRequestHandler):
    application: LeadCaptureMock
    server_version = "AIKINGLeadCaptureMock/0.1"
    sys_version = ""

    def log_message(self, format: str, *args: Any) -> None:
        # Do not log request data in this local data-handling mock.
        return

    def _write_json(
        self,
        status: int,
        body: dict[str, Any],
        headers: dict[str, str] | None = None,
        *,
        write_body: bool = True,
    ) -> None:
        encoded = json.dumps(body, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        if write_body:
            try:
                self.wfile.write(encoded)
            except (BrokenPipeError, ConnectionResetError):
                self.close_connection = True

    def send_error(  # type: ignore[override]
        self, code: int, message: str | None = None, explain: str | None = None
    ) -> None:
        """Return safe JSON for parser/default-method errors instead of HTML."""
        self.close_connection = True
        if getattr(self, "request_version", self.default_request_version) == self.default_request_version:
            # Parser errors can occur before BaseHTTPRequestHandler records an
            # HTTP version. Force a real status line/headers instead of its
            # HTTP/0.9 fallback, which would write only the response body.
            self.request_version = self.protocol_version
        if code == 501:
            self._write_json(
                405,
                error_response("invalid_request", "HTTP method is not allowed."),
                {"Allow": "POST"},
                write_body=getattr(self, "command", "") != "HEAD",
            )
            return

        status = 400 if code in {414, 431, 505} else code
        self._write_json(
            status,
            error_response("invalid_request", "HTTP request is invalid."),
            write_body=getattr(self, "command", "") != "HEAD",
        )

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
        if urlsplit(self.path).path != ENDPOINT:
            self.close_connection = True
            self._write_json(
                404,
                error_response("invalid_request", "Requested endpoint was not found."),
            )
            return

        host_values = self.headers.get_all("Host", [])
        if len(host_values) != 1 or not host_values[0].strip():
            self.close_connection = True
            self._write_json(
                400,
                error_response("invalid_request", "Request headers are invalid."),
            )
            return

        content_types = self.headers.get_all("Content-Type", [])
        if (
            len(content_types) != 1
            or self.headers.get_content_type() != "application/json"
        ):
            self._write_json(
                415,
                error_response(
                    "unsupported_media_type", "Content-Type must be application/json."
                ),
            )
            return

        content_lengths = self.headers.get_all("Content-Length", [])
        if self.headers.get_all("Transfer-Encoding") or len(content_lengths) != 1:
            self.close_connection = True
            self._write_json(
                400,
                error_response("invalid_json", "Request body must be valid JSON."),
            )
            return

        try:
            if CONTENT_LENGTH_PATTERN.fullmatch(content_lengths[0]) is None:
                raise ValueError("Content-Length must use decimal digits")
            content_length = int(content_lengths[0])
        except ValueError:
            content_length = -1
        if content_length < 1 or content_length > MAX_BODY_BYTES:
            self.close_connection = content_length < 0 or content_length > MAX_BODY_BYTES
            self._write_json(
                400,
                error_response("invalid_json", "Request body must be valid JSON."),
            )
            return

        idempotency_keys = self.headers.get_all("Idempotency-Key", [])
        if (
            len(idempotency_keys) != 1
            or IDEMPOTENCY_PATTERN.fullmatch(idempotency_keys[0]) is None
        ):
            self.close_connection = True
            self._write_json(
                422,
                error_response(
                    "invalid_request",
                    "One or more fields are invalid.",
                    [{"field": "Idempotency-Key", "code": "invalid_format"}],
                ),
            )
            return

        raw_body = self.rfile.read(content_length)
        if len(raw_body) != content_length:
            self.close_connection = True
            self._write_json(
                400,
                error_response("invalid_json", "Request body must be valid JSON."),
            )
            return
        try:
            payload = json.loads(
                raw_body.decode("utf-8"),
                object_pairs_hook=reject_duplicate_json_members,
                parse_constant=lambda value: (_ for _ in ()).throw(
                    ValueError(f"non-standard JSON constant: {value}")
                ),
            )
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            self._write_json(
                400,
                error_response("invalid_json", "Request body must be valid JSON."),
            )
            return

        try:
            status, headers, body = self.application.submit(
                idempotency_keys[0] if idempotency_keys else None,
                payload,
                self.client_address[0],
            )
        except Exception:
            # Keep unexpected application details out of HTTP responses and logs.
            self._write_json(
                500,
                error_response("internal_error", "Request could not be processed."),
            )
            return
        self._write_json(status, body, headers)


def handler_for(application: LeadCaptureMock) -> type[LeadCaptureHandler]:
    class BoundLeadCaptureHandler(LeadCaptureHandler):
        pass

    BoundLeadCaptureHandler.application = application
    return BoundLeadCaptureHandler


def create_server(
    port: int = 8787, application: LeadCaptureMock | None = None
) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(
        ("127.0.0.1", port), handler_for(application or LeadCaptureMock())
    )
    server.daemon_threads = True
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    if not 0 <= args.port <= 65_535:
        parser.error("--port must be between 0 and 65535")

    server = create_server(port=args.port)
    host = server.server_address[0]
    port = server.server_address[1]
    print(f"AIKING lead-capture mock listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
