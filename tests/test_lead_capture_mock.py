import copy
import http.client
import io
import json
import socket
import threading
import unittest
import uuid
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from api.mock_server import MAX_BODY_BYTES, LeadCaptureMock, create_server


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "api" / "lead-capture.openapi.json"

VALID_PAYLOAD = {
    "name": "Jordan Example",
    "role": "Operations Director",
    "organisation": "Example Industries",
    "email": "jordan@example.com",
    "timeframe": "next_30_days",
    "maturity": "pilots_underway",
    "outcome": "Reduce manual reporting time and improve operational visibility.",
    "website": "",
}


def resolve_local_ref(document, value):
    while isinstance(value, dict) and "$ref" in value:
        ref = value["$ref"]
        if not ref.startswith("#/"):
            raise AssertionError(f"response contract uses unsupported reference: {ref}")
        value = document
        for token in ref.removeprefix("#/").split("/"):
            token = token.replace("~1", "/").replace("~0", "~")
            value = value[token]
    return value


def response_schema_errors(document, schema, value, path="$"):
    """Validate the response-schema keywords used by the OpenAPI document."""
    schema = resolve_local_ref(document, schema)
    errors = []
    expected_type = schema.get("type")
    type_matches = {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "boolean": isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
    }
    if expected_type and not type_matches.get(expected_type, False):
        return [f"{path}: expected {expected_type}"]

    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: does not match const")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: not in enum")

    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{path}: shorter than minLength")
        if len(value) > schema.get("maxLength", len(value)):
            errors.append(f"{path}: longer than maxLength")
        if schema.get("format") == "uuid":
            try:
                uuid.UUID(value)
            except (ValueError, AttributeError):
                errors.append(f"{path}: invalid UUID format")

    if isinstance(value, int) and not isinstance(value, bool):
        if value < schema.get("minimum", value):
            errors.append(f"{path}: below minimum")

    if isinstance(value, list):
        if len(value) > schema.get("maxItems", len(value)):
            errors.append(f"{path}: longer than maxItems")
        if "items" in schema:
            for index, item in enumerate(value):
                errors.extend(
                    response_schema_errors(
                        document, schema["items"], item, f"{path}[{index}]"
                    )
                )

    if isinstance(value, dict):
        properties = schema.get("properties", {})
        for field in schema.get("required", []):
            if field not in value:
                errors.append(f"{path}.{field}: required")
        if schema.get("additionalProperties") is False:
            for field in value.keys() - properties.keys():
                errors.append(f"{path}.{field}: additional property")
        for field, child in value.items():
            if field in properties:
                errors.extend(
                    response_schema_errors(
                        document, properties[field], child, f"{path}.{field}"
                    )
                )

    return errors


@contextmanager
def running_mock(*, rate_limit=5):
    application = LeadCaptureMock(rate_limit=rate_limit)
    server = create_server(port=0, application=application)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, application
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def post(
    server,
    *,
    payload=VALID_PAYLOAD,
    key="local-test-key-0001",
    content_type="application/json",
    raw=None,
):
    body = raw if raw is not None else json.dumps(payload).encode("utf-8")
    connection = http.client.HTTPConnection(*server.server_address, timeout=2)
    connection.request(
        "POST",
        "/v1/lead-requests",
        body=body,
        headers={"Content-Type": content_type, "Idempotency-Key": key},
    )
    response = connection.getresponse()
    response_body = json.loads(response.read().decode("utf-8"))
    headers = dict(response.getheaders())
    connection.close()
    return response.status, headers, response_body


def post_with_raw_framing(
    server, framing_headers, *, body=None, half_close_write=False
):
    """Send framing that http.client would otherwise normalize for us."""
    body = body if body is not None else json.dumps(VALID_PAYLOAD).encode("utf-8")
    host, port = server.server_address
    header_lines = [
        "POST /v1/lead-requests HTTP/1.1",
        f"Host: {host}:{port}",
        "Content-Type: application/json",
        "Idempotency-Key: local-test-key-framing",
        "Connection: close",
        *framing_headers,
    ]
    request = "\r\n".join([*header_lines, "", ""]).encode("ascii") + body

    with socket.create_connection(server.server_address, timeout=2) as sock:
        sock.sendall(request)
        if half_close_write:
            sock.shutdown(socket.SHUT_WR)
        response = http.client.HTTPResponse(sock)
        response.begin()
        response_body = json.loads(response.read().decode("utf-8"))
        headers = dict(response.getheaders())
        return response.status, headers, response_body


def post_without_declared_body(
    server,
    *,
    method="POST",
    target="/v1/lead-requests",
    host_header=None,
    content_type_header: str | None = "Content-Type: application/json",
    idempotency_header: str | None = (
        "Idempotency-Key: local-test-key-invalid-request"
    ),
    content_length="1",
    extra_headers=(),
):
    """Prove invalid headers or framing are rejected before body processing."""
    header_lines = [f"{method} {target} HTTP/1.1"]
    if host_header is not None:
        header_lines.append(host_header)
    header_lines.extend(
        [
            *([content_type_header] if content_type_header is not None else []),
            *([idempotency_header] if idempotency_header is not None else []),
            f"Content-Length: {content_length}",
            "Connection: keep-alive",
            *extra_headers,
        ]
    )
    request = "\r\n".join([*header_lines, "", ""]).encode("ascii")

    with socket.create_connection(server.server_address, timeout=2) as sock:
        # Intentionally leave the declared body unsent. Invalid requests must
        # be rejected before body processing rather than blocking here.
        sock.sendall(request)
        response = http.client.HTTPResponse(sock)
        response.begin()
        response_body = json.loads(response.read().decode("utf-8"))
        headers = dict(response.getheaders())
        connection_will_close = response.will_close
        peer_closed = sock.recv(1) == b""
        return (
            response.status,
            headers,
            response_body,
            connection_will_close,
            peer_closed,
        )


def send_raw_http_request(server, request):
    """Send a pre-framed request and parse the JSON response."""
    with socket.create_connection(server.server_address, timeout=2) as sock:
        sock.sendall(request)
        response = http.client.HTTPResponse(sock)
        response.begin()
        response_body = json.loads(response.read().decode("utf-8"))
        headers = dict(response.getheaders())
        connection_will_close = response.will_close
        peer_closed = sock.recv(1) == b""
        return (
            response.status,
            headers,
            response_body,
            connection_will_close,
            peer_closed,
        )


class LeadCaptureMockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with SPEC_PATH.open(encoding="utf-8") as handle:
            cls.spec = json.load(handle)
        cls.responses = cls.spec["paths"]["/v1/lead-requests"]["post"][
            "responses"
        ]

    def assert_response_conforms(self, status, headers, body):
        response = resolve_local_ref(self.spec, self.responses[str(status)])
        content = response["content"]
        self.assertEqual(set(content), {"application/json"})

        normalized_headers = {name.lower(): value for name, value in headers.items()}
        self.assertEqual(
            normalized_headers["content-type"].split(";", 1)[0], "application/json"
        )
        self.assertEqual(normalized_headers["cache-control"], "no-store")

        schema = content["application/json"]["schema"]
        self.assertEqual(response_schema_errors(self.spec, schema, body), [])

        for name, header_contract in response.get("headers", {}).items():
            actual = normalized_headers.get(name.lower())
            if header_contract.get("required"):
                self.assertIsNotNone(actual, f"missing required response header: {name}")
            if actual is None:
                continue
            header_schema = resolve_local_ref(
                self.spec, header_contract.get("schema", {})
            )
            header_value = int(actual) if header_schema.get("type") == "integer" else actual
            self.assertEqual(
                response_schema_errors(self.spec, header_schema, header_value), []
            )

    def assert_json_error_conforms(self, headers, body):
        normalized_headers = {name.lower(): value for name, value in headers.items()}
        self.assertEqual(
            normalized_headers["content-type"].split(";", 1)[0], "application/json"
        )
        self.assertEqual(normalized_headers["cache-control"], "no-store")
        self.assertEqual(
            response_schema_errors(
                self.spec, self.spec["components"]["schemas"]["ErrorResponse"], body
            ),
            [],
        )

    def test_all_endpoint_response_classes_conform_to_openapi(self):
        changed = copy.deepcopy(VALID_PAYLOAD)
        changed["outcome"] = (
            "Replace a different manual reporting workflow with governed automation."
        )
        invalid = copy.deepcopy(VALID_PAYLOAD)
        invalid.pop("email")

        with running_mock(rate_limit=20) as (server, _application):
            accepted = post(server)
            outcomes = {
                "accepted": accepted,
                "replayed": post(server),
                "idempotency conflict": post(server, payload=changed),
                "malformed JSON": post(server, raw=b'{"name":'),
                "unsupported media type": post(server, content_type="text/plain"),
                "validation failure": post(
                    server, payload=invalid, key="local-test-key-0002"
                ),
            }

        with running_mock(rate_limit=1) as (server, _application):
            post(server)
            outcomes["rate limited"] = post(server, key="local-test-key-0002")

        failure_detail = "internal test sentinel"
        with running_mock(rate_limit=20) as (server, application):
            with patch.object(
                application, "submit", side_effect=RuntimeError(failure_detail)
            ):
                outcomes["internal failure"] = post(server)

        expected_statuses = {202, 400, 409, 415, 422, 429, 500}
        self.assertEqual({outcome[0] for outcome in outcomes.values()}, expected_statuses)
        for label, (status, headers, body) in outcomes.items():
            with self.subTest(label=label, status=status):
                self.assert_response_conforms(status, headers, body)

        failure_status, _failure_headers, failure_body = outcomes["internal failure"]
        self.assertEqual(failure_status, 500)
        self.assertEqual(
            failure_body,
            {
                "error": {
                    "code": "internal_error",
                    "message": "Request could not be processed.",
                }
            },
        )
        self.assertNotIn(failure_detail, json.dumps(failure_body))

    def test_server_binds_only_to_loopback(self):
        with running_mock() as (server, _application):
            self.assertEqual(server.server_address[0], "127.0.0.1")

    def test_unsupported_method_is_rejected_before_body_and_application(self):
        with running_mock(rate_limit=20) as (server, application):
            with patch.object(
                application, "submit", wraps=application.submit
            ) as submit:
                (
                    status,
                    headers,
                    body,
                    connection_will_close,
                    peer_closed,
                ) = post_without_declared_body(
                    server,
                    method="BREW",
                    host_header=(
                        f"Host: {server.server_address[0]}:{server.server_address[1]}"
                    ),
                )

            submit.assert_not_called()
            self.assertEqual(application._accepted, {})
            self.assertEqual(application._attempts, {})

        self.assertEqual(status, 405)
        self.assertEqual(headers["Allow"], "POST")
        self.assertEqual(
            body,
            {
                "error": {
                    "code": "invalid_request",
                    "message": "HTTP method is not allowed.",
                }
            },
        )
        self.assert_json_error_conforms(headers, body)
        self.assertTrue(connection_will_close)
        self.assertTrue(peer_closed)

    def test_head_method_returns_headers_only_without_body_or_application(self):
        expected_body = {
            "error": {
                "code": "invalid_request",
                "message": "HTTP method is not allowed.",
            }
        }
        expected_body_length = len(
            json.dumps(expected_body, separators=(",", ":")).encode("utf-8")
        )

        with running_mock(rate_limit=20) as (server, application):
            host = str(server.server_address[0])
            port = int(server.server_address[1])
            connection = http.client.HTTPConnection(host, port, timeout=2)
            try:
                with patch.object(
                    application, "submit", wraps=application.submit
                ) as submit:
                    connection.request(
                        "HEAD",
                        "/v1/lead-requests",
                        body=None,
                        headers={
                            "Content-Type": "application/json",
                            "Content-Length": "1",
                            "Idempotency-Key": "local-test-key-head-method",
                        },
                    )
                    response = connection.getresponse()
                    response_body = response.read()
                    headers = dict(response.getheaders())
                    connection_will_close = response.will_close

                submit.assert_not_called()
                self.assertEqual(application._accepted, {})
                self.assertEqual(application._attempts, {})
            finally:
                connection.close()

        self.assertEqual(response.status, 405)
        self.assertEqual(headers["Allow"], "POST")
        self.assertEqual(response_body, b"")
        self.assertEqual(headers["Content-Length"], str(expected_body_length))
        self.assertEqual(headers["Content-Type"].split(";", 1)[0], "application/json")
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertTrue(connection_will_close)

    def test_options_method_is_rejected_before_body_and_application(self):
        with running_mock(rate_limit=20) as (server, application):
            with patch.object(
                application, "submit", wraps=application.submit
            ) as submit:
                (
                    status,
                    headers,
                    body,
                    connection_will_close,
                    peer_closed,
                ) = post_without_declared_body(
                    server,
                    method="OPTIONS",
                    host_header=(
                        f"Host: {server.server_address[0]}:{server.server_address[1]}"
                    ),
                    idempotency_header="Idempotency-Key: local-test-key-options",
                )

            submit.assert_not_called()
            self.assertEqual(application._accepted, {})
            self.assertEqual(application._attempts, {})

        self.assertEqual(status, 405)
        self.assertEqual(headers["Allow"], "POST")
        self.assertEqual(
            body,
            {
                "error": {
                    "code": "invalid_request",
                    "message": "HTTP method is not allowed.",
                }
            },
        )
        self.assert_json_error_conforms(headers, body)
        self.assertTrue(connection_will_close)
        self.assertTrue(peer_closed)

    def test_unknown_route_is_rejected_before_body_and_application(self):
        with running_mock(rate_limit=20) as (server, application):
            with patch.object(
                application, "submit", wraps=application.submit
            ) as submit:
                (
                    status,
                    headers,
                    body,
                    connection_will_close,
                    peer_closed,
                ) = post_without_declared_body(
                    server,
                    target="/v1/not-lead-requests",
                    host_header=(
                        f"Host: {server.server_address[0]}:{server.server_address[1]}"
                    ),
                )

            submit.assert_not_called()
            self.assertEqual(application._accepted, {})
            self.assertEqual(application._attempts, {})

        self.assertEqual(status, 404)
        self.assertEqual(
            body,
            {
                "error": {
                    "code": "invalid_request",
                    "message": "Requested endpoint was not found.",
                }
            },
        )
        self.assert_json_error_conforms(headers, body)
        self.assertTrue(connection_will_close)
        self.assertTrue(peer_closed)

    def test_malformed_request_line_returns_safe_json_without_body_processing(self):
        marker = "unique-untrusted-request-target-fragment"
        with running_mock(rate_limit=20) as (server, application):
            host, port = server.server_address[:2]
            request = "\r\n".join(
                [
                    f"POST /v1/lead-requests/{marker} HTTP/1.1 unexpected",
                    f"Host: {host}:{port}",
                    "Content-Type: application/json",
                    "Idempotency-Key: local-test-key-malformed",
                    "Content-Length: 1",
                    "Connection: keep-alive",
                    "",
                    "",
                ]
            ).encode("ascii")

            with patch.object(
                application, "submit", wraps=application.submit
            ) as submit:
                (
                    status,
                    headers,
                    body,
                    connection_will_close,
                    peer_closed,
                ) = send_raw_http_request(server, request)

            submit.assert_not_called()
            self.assertEqual(application._accepted, {})
            self.assertEqual(application._attempts, {})

        self.assertEqual(status, 400)
        self.assertEqual(
            body,
            {
                "error": {
                    "code": "invalid_request",
                    "message": "HTTP request is invalid.",
                }
            },
        )
        self.assert_json_error_conforms(headers, body)
        self.assertNotIn(marker, json.dumps(body))
        self.assertTrue(connection_will_close)
        self.assertTrue(peer_closed)

    def test_parser_edge_failures_are_normalized_to_safe_contract_400(self):
        marker = "unique-parser-edge-request-target-fragment"

        with running_mock(rate_limit=20) as (server, application):
            host, port = server.server_address[:2]
            common_headers = "\r\n".join(
                [
                    f"Host: {host}:{port}",
                    "Content-Type: application/json",
                    "Idempotency-Key: local-test-key-parser-edge",
                    "Content-Length: 1",
                    "Connection: keep-alive",
                    "",
                    "",
                ]
            )
            invalid_version = (
                f"POST /v1/lead-requests/{marker} HTTP/2.0\r\n"
                + common_headers
            ).encode("ascii")
            oversized_request_line = (
                "POST /v1/lead-requests/"
                + marker
                + ("x" * 70_000)
                + " HTTP/1.1\r\n"
                + common_headers
            ).encode("ascii")
            oversized_header_line = (
                "\r\n".join(
                    [
                        "POST /v1/lead-requests HTTP/1.1",
                        f"Host: {host}:{port}",
                        "X-Oversized-Header: " + marker + ("x" * 70_000),
                        "Content-Type: application/json",
                        "Idempotency-Key: local-test-key-parser-edge",
                        "Content-Length: 1",
                        "Connection: keep-alive",
                        "",
                        "",
                    ]
                )
            ).encode("ascii")
            too_many_headers = (
                "\r\n".join(
                    [
                        "POST /v1/lead-requests HTTP/1.1",
                        f"Host: {host}:{port}",
                        "Content-Type: application/json",
                        "Idempotency-Key: local-test-key-parser-edge",
                        "Content-Length: 1",
                        "Connection: keep-alive",
                        *[
                            f"X-Filler-{index}: {marker}"
                            for index in range(110)
                        ],
                        "",
                        "",
                    ]
                )
            ).encode("ascii")

            with patch.object(
                application, "submit", wraps=application.submit
            ) as submit:
                outcomes = {
                    "invalid HTTP version": send_raw_http_request(
                        server, invalid_version
                    ),
                    "oversized request line": send_raw_http_request(
                        server, oversized_request_line
                    ),
                    "oversized header line": send_raw_http_request(
                        server, oversized_header_line
                    ),
                    "too many headers": send_raw_http_request(
                        server, too_many_headers
                    ),
                }

            submit.assert_not_called()
            self.assertEqual(application._accepted, {})
            self.assertEqual(application._attempts, {})

        expected_body = {
            "error": {
                "code": "invalid_request",
                "message": "HTTP request is invalid.",
            }
        }
        for label, (
            status,
            headers,
            body,
            connection_will_close,
            peer_closed,
        ) in outcomes.items():
            with self.subTest(label=label):
                self.assertEqual(status, 400)
                self.assertEqual(body, expected_body)
                self.assert_response_conforms(status, headers, body)
                self.assertNotIn(marker, json.dumps(body))
                self.assertTrue(connection_will_close)
                self.assertTrue(peer_closed)

    def test_accepts_and_replays_without_echoing_or_storing_contact_fields(self):
        with running_mock() as (server, application):
            first_status, first_headers, first = post(server)
            replay_status, _replay_headers, replay = post(server)

            self.assertEqual(first_status, 202)
            self.assertEqual(replay_status, 202)
            self.assertEqual(first["status"], "accepted")
            self.assertFalse(first["duplicate"])
            self.assertTrue(replay["duplicate"])
            self.assertEqual(first["request_id"], replay["request_id"])
            uuid.UUID(first["request_id"])
            self.assertEqual(first_headers["Cache-Control"], "no-store")
            self.assertNotIn(VALID_PAYLOAD["email"], json.dumps([first, replay]))

            stored = application._accepted["local-test-key-0001"]
            self.assertEqual(set(stored), {"fingerprint", "request_id"})
            self.assertNotIn(VALID_PAYLOAD["email"], json.dumps(stored))

    def test_conflicting_idempotency_payload_returns_409(self):
        changed = copy.deepcopy(VALID_PAYLOAD)
        changed["outcome"] = "Replace a different manual reporting workflow with governed automation."
        with running_mock() as (server, _application):
            self.assertEqual(post(server)[0], 202)
            status, _headers, body = post(server, payload=changed)

        self.assertEqual(status, 409)
        self.assertEqual(body["error"]["code"], "idempotency_conflict")
        self.assertNotIn(changed["outcome"], json.dumps(body))

    def test_wrong_content_type_returns_415(self):
        with running_mock() as (server, _application):
            status, _headers, body = post(server, content_type="text/plain")

        self.assertEqual(status, 415)
        self.assertEqual(body["error"]["code"], "unsupported_media_type")

    def test_wrong_content_type_is_rejected_before_body_and_application(self):
        with running_mock(rate_limit=20) as (server, application):
            with patch.object(
                application, "submit", wraps=application.submit
            ) as submit:
                (
                    status,
                    headers,
                    body,
                    connection_will_close,
                    peer_closed,
                ) = post_without_declared_body(
                    server,
                    host_header=(
                        f"Host: {server.server_address[0]}:{server.server_address[1]}"
                    ),
                    content_type_header="Content-Type: text/plain",
                )

            submit.assert_not_called()
            self.assertEqual(application._accepted, {})
            self.assertEqual(application._attempts, {})

        self.assertEqual(status, 415)
        self.assertEqual(
            body,
            {
                "error": {
                    "code": "unsupported_media_type",
                    "message": "Content-Type must be application/json.",
                }
            },
        )
        self.assert_response_conforms(status, headers, body)
        self.assertTrue(connection_will_close)
        self.assertTrue(peer_closed)

    def test_missing_or_empty_content_type_is_rejected_before_body_and_application(self):
        expected_body = {
            "error": {
                "code": "unsupported_media_type",
                "message": "Content-Type must be application/json.",
            }
        }

        with running_mock(rate_limit=20) as (server, application):
            host_header = (
                f"Host: {server.server_address[0]}:{server.server_address[1]}"
            )
            with patch.object(
                application, "submit", wraps=application.submit
            ) as submit:
                outcomes = {
                    "missing": post_without_declared_body(
                        server,
                        host_header=host_header,
                        content_type_header=None,
                    ),
                    "empty": post_without_declared_body(
                        server,
                        host_header=host_header,
                        content_type_header="Content-Type:",
                    ),
                }

            submit.assert_not_called()
            self.assertEqual(application._accepted, {})
            self.assertEqual(application._attempts, {})

        for label, (
            status,
            headers,
            body,
            connection_will_close,
            peer_closed,
        ) in outcomes.items():
            with self.subTest(label=label):
                self.assertEqual(status, 415)
                self.assertEqual(body, expected_body)
                self.assert_response_conforms(status, headers, body)
                self.assertTrue(connection_will_close)
                self.assertTrue(peer_closed)

    def test_duplicate_content_type_is_rejected_before_application(self):
        body_length = len(json.dumps(VALID_PAYLOAD).encode("utf-8"))

        with running_mock(rate_limit=20) as (server, application):
            with patch.object(
                application, "submit", wraps=application.submit
            ) as submit:
                outcomes = {
                    "equal values": post_with_raw_framing(
                        server,
                        [
                            "Content-Type: application/json",
                            f"Content-Length: {body_length}",
                        ],
                    ),
                    "conflicting values": post_with_raw_framing(
                        server,
                        [
                            "Content-Type: text/plain",
                            f"Content-Length: {body_length}",
                        ],
                    ),
                }

            submit.assert_not_called()
            self.assertEqual(application._accepted, {})
            self.assertEqual(application._attempts, {})

        expected_body = {
            "error": {
                "code": "unsupported_media_type",
                "message": "Content-Type must be application/json.",
            }
        }
        for label, (status, headers, body) in outcomes.items():
            with self.subTest(label=label):
                self.assertEqual(status, 415)
                self.assertEqual(body, expected_body)
                self.assert_response_conforms(status, headers, body)

    def test_duplicate_content_type_is_rejected_before_body_and_application(self):
        expected_body = {
            "error": {
                "code": "unsupported_media_type",
                "message": "Content-Type must be application/json.",
            }
        }

        with running_mock(rate_limit=20) as (server, application):
            host_header = (
                f"Host: {server.server_address[0]}:{server.server_address[1]}"
            )
            with patch.object(
                application, "submit", wraps=application.submit
            ) as submit:
                outcomes = {
                    "equal values": post_without_declared_body(
                        server,
                        host_header=host_header,
                        extra_headers=["Content-Type: application/json"],
                    ),
                    "conflicting values": post_without_declared_body(
                        server,
                        host_header=host_header,
                        extra_headers=["Content-Type: text/plain"],
                    ),
                }

            submit.assert_not_called()
            self.assertEqual(application._accepted, {})
            self.assertEqual(application._attempts, {})

        for label, (
            status,
            headers,
            body,
            connection_will_close,
            peer_closed,
        ) in outcomes.items():
            with self.subTest(label=label):
                self.assertEqual(status, 415)
                self.assertEqual(body, expected_body)
                self.assert_response_conforms(status, headers, body)
                self.assertTrue(connection_will_close)
                self.assertTrue(peer_closed)

    def test_duplicate_host_is_rejected_before_application(self):
        body_length = len(json.dumps(VALID_PAYLOAD).encode("utf-8"))

        with running_mock(rate_limit=20) as (server, application):
            authority = f"{server.server_address[0]}:{server.server_address[1]}"
            with patch.object(
                application, "submit", wraps=application.submit
            ) as submit:
                outcomes = {
                    "equal values": post_with_raw_framing(
                        server,
                        [
                            f"Host: {authority}",
                            f"Content-Length: {body_length}",
                        ],
                    ),
                    "conflicting values": post_with_raw_framing(
                        server,
                        [
                            "Host: localhost:1",
                            f"Content-Length: {body_length}",
                        ],
                    ),
                }

            submit.assert_not_called()
            self.assertEqual(application._accepted, {})
            self.assertEqual(application._attempts, {})

        expected_body = {
            "error": {
                "code": "invalid_request",
                "message": "Request headers are invalid.",
            }
        }
        for label, (status, headers, body) in outcomes.items():
            with self.subTest(label=label):
                self.assertEqual(status, 400)
                self.assertEqual(body, expected_body)
                self.assert_response_conforms(status, headers, body)

    def test_duplicate_host_is_rejected_before_body_and_application(self):
        expected_body = {
            "error": {
                "code": "invalid_request",
                "message": "Request headers are invalid.",
            }
        }

        with running_mock(rate_limit=20) as (server, application):
            authority = f"{server.server_address[0]}:{server.server_address[1]}"
            with patch.object(
                application, "submit", wraps=application.submit
            ) as submit:
                outcomes = {
                    "equal values": post_without_declared_body(
                        server,
                        host_header=f"Host: {authority}",
                        extra_headers=[f"Host: {authority}"],
                    ),
                    "conflicting values": post_without_declared_body(
                        server,
                        host_header=f"Host: {authority}",
                        extra_headers=["Host: localhost:1"],
                    ),
                }

            submit.assert_not_called()
            self.assertEqual(application._accepted, {})
            self.assertEqual(application._attempts, {})

        for label, (
            status,
            headers,
            body,
            connection_will_close,
            peer_closed,
        ) in outcomes.items():
            with self.subTest(label=label):
                self.assertEqual(status, 400)
                self.assertEqual(body, expected_body)
                self.assert_response_conforms(status, headers, body)
                self.assertTrue(connection_will_close)
                self.assertTrue(peer_closed)

    def test_missing_host_is_rejected_before_body_and_application(self):
        with running_mock(rate_limit=20) as (server, application):
            with patch.object(
                application, "submit", wraps=application.submit
            ) as submit:
                (
                    status,
                    headers,
                    body,
                    connection_will_close,
                    peer_closed,
                ) = post_without_declared_body(server)

            submit.assert_not_called()
            self.assertEqual(application._accepted, {})
            self.assertEqual(application._attempts, {})

        self.assertEqual(status, 400)
        self.assertEqual(
            body,
            {
                "error": {
                    "code": "invalid_request",
                    "message": "Request headers are invalid.",
                }
            },
        )
        self.assert_response_conforms(status, headers, body)
        self.assertTrue(connection_will_close)
        self.assertTrue(peer_closed)

    def test_empty_host_is_rejected_before_body_and_application(self):
        with running_mock(rate_limit=20) as (server, application):
            with patch.object(
                application, "submit", wraps=application.submit
            ) as submit:
                (
                    status,
                    headers,
                    body,
                    connection_will_close,
                    peer_closed,
                ) = post_without_declared_body(server, host_header="Host:")

            submit.assert_not_called()
            self.assertEqual(application._accepted, {})
            self.assertEqual(application._attempts, {})

        self.assertEqual(status, 400)
        self.assertEqual(
            body,
            {
                "error": {
                    "code": "invalid_request",
                    "message": "Request headers are invalid.",
                }
            },
        )
        self.assert_response_conforms(status, headers, body)
        self.assertTrue(connection_will_close)
        self.assertTrue(peer_closed)

    def test_malformed_json_returns_400(self):
        with running_mock() as (server, _application):
            status, _headers, body = post(server, raw=b'{"name":')

        self.assertEqual(status, 400)
        self.assertEqual(body["error"]["code"], "invalid_json")

    def test_duplicate_json_member_is_rejected_before_application(self):
        encoded = json.dumps(VALID_PAYLOAD, separators=(",", ":"))
        repeated_name = json.dumps("name") + ":" + json.dumps("Another Example")
        raw = ("{" + repeated_name + "," + encoded[1:]).encode("utf-8")

        with running_mock(rate_limit=20) as (server, application):
            with patch.object(
                application, "submit", wraps=application.submit
            ) as submit:
                status, headers, body = post(
                    server, raw=raw, key="local-test-key-duplicate-member"
                )

            submit.assert_not_called()
            self.assertEqual(application._accepted, {})
            self.assertEqual(application._attempts, {})

        self.assertEqual(status, 400)
        self.assertEqual(
            body,
            {
                "error": {
                    "code": "invalid_json",
                    "message": "Request body must be valid JSON.",
                }
            },
        )
        self.assert_response_conforms(status, headers, body)

    def test_duplicate_idempotency_key_is_rejected_before_application(self):
        body_length = len(json.dumps(VALID_PAYLOAD).encode("utf-8"))

        with running_mock(rate_limit=20) as (server, application):
            with patch.object(
                application, "submit", wraps=application.submit
            ) as submit:
                outcomes = {
                    "equal values": post_with_raw_framing(
                        server,
                        [
                            f"Content-Length: {body_length}",
                            "Idempotency-Key: local-test-key-framing",
                        ],
                    ),
                    "conflicting values": post_with_raw_framing(
                        server,
                        [
                            f"Content-Length: {body_length}",
                            "Idempotency-Key: local-test-key-other-0001",
                        ],
                    ),
                }

            submit.assert_not_called()
            self.assertEqual(application._accepted, {})
            self.assertEqual(application._attempts, {})

        expected_body = {
            "error": {
                "code": "invalid_request",
                "message": "One or more fields are invalid.",
                "fields": [
                    {"field": "Idempotency-Key", "code": "invalid_format"}
                ],
            }
        }
        for label, (status, headers, body) in outcomes.items():
            with self.subTest(label=label):
                self.assertEqual(status, 422)
                self.assertEqual(body, expected_body)
                self.assert_response_conforms(status, headers, body)

    def test_duplicate_idempotency_key_is_rejected_before_body_and_application(self):
        with running_mock(rate_limit=20) as (server, application):
            with patch.object(
                application, "submit", wraps=application.submit
            ) as submit:
                (
                    status,
                    headers,
                    body,
                    connection_will_close,
                    peer_closed,
                ) = post_without_declared_body(
                    server,
                    host_header=(
                        f"Host: {server.server_address[0]}:{server.server_address[1]}"
                    ),
                    extra_headers=[
                        "Idempotency-Key: local-test-key-invalid-request"
                    ],
                )

            submit.assert_not_called()
            self.assertEqual(application._accepted, {})
            self.assertEqual(application._attempts, {})

        self.assertEqual(status, 422)
        self.assertEqual(
            body,
            {
                "error": {
                    "code": "invalid_request",
                    "message": "One or more fields are invalid.",
                    "fields": [
                        {"field": "Idempotency-Key", "code": "invalid_format"}
                    ],
                }
            },
        )
        self.assert_response_conforms(status, headers, body)
        self.assertTrue(connection_will_close)
        self.assertTrue(peer_closed)

    def test_missing_idempotency_key_is_rejected_before_body_and_application(self):
        with running_mock(rate_limit=20) as (server, application):
            with patch.object(
                application, "submit", wraps=application.submit
            ) as submit:
                (
                    status,
                    headers,
                    body,
                    connection_will_close,
                    peer_closed,
                ) = post_without_declared_body(
                    server,
                    host_header=(
                        f"Host: {server.server_address[0]}:{server.server_address[1]}"
                    ),
                    idempotency_header=None,
                )

            submit.assert_not_called()
            self.assertEqual(application._accepted, {})
            self.assertEqual(application._attempts, {})

        self.assertEqual(status, 422)
        self.assertEqual(
            body,
            {
                "error": {
                    "code": "invalid_request",
                    "message": "One or more fields are invalid.",
                    "fields": [
                        {"field": "Idempotency-Key", "code": "invalid_format"}
                    ],
                }
            },
        )
        self.assert_response_conforms(status, headers, body)
        self.assertTrue(connection_will_close)
        self.assertTrue(peer_closed)

    def test_invalid_single_idempotency_key_is_rejected_before_body_and_application(self):
        expected_body = {
            "error": {
                "code": "invalid_request",
                "message": "One or more fields are invalid.",
                "fields": [
                    {"field": "Idempotency-Key", "code": "invalid_format"}
                ],
            }
        }

        with running_mock(rate_limit=20) as (server, application):
            host_header = (
                f"Host: {server.server_address[0]}:{server.server_address[1]}"
            )
            with patch.object(
                application, "submit", wraps=application.submit
            ) as submit:
                outcomes = {
                    "empty": post_without_declared_body(
                        server,
                        host_header=host_header,
                        idempotency_header="Idempotency-Key:",
                    ),
                    "too short": post_without_declared_body(
                        server,
                        host_header=host_header,
                        idempotency_header="Idempotency-Key: short",
                    ),
                    "invalid character": post_without_declared_body(
                        server,
                        host_header=host_header,
                        idempotency_header=(
                            "Idempotency-Key: invalid-key-000!"
                        ),
                    ),
                }

            submit.assert_not_called()
            self.assertEqual(application._accepted, {})
            self.assertEqual(application._attempts, {})

        for label, (
            status,
            headers,
            body,
            connection_will_close,
            peer_closed,
        ) in outcomes.items():
            with self.subTest(label=label):
                self.assertEqual(status, 422)
                self.assertEqual(body, expected_body)
                self.assert_response_conforms(status, headers, body)
                self.assertTrue(connection_will_close)
                self.assertTrue(peer_closed)

    def test_body_size_boundary_is_inclusive_and_safe(self):
        encoded = json.dumps(VALID_PAYLOAD, separators=(",", ":")).encode("utf-8")
        exactly_at_limit = encoded + (b" " * (MAX_BODY_BYTES - len(encoded)))
        one_byte_over = exactly_at_limit + b" "
        self.assertEqual(len(exactly_at_limit), MAX_BODY_BYTES)
        self.assertEqual(len(one_byte_over), MAX_BODY_BYTES + 1)

        with running_mock(rate_limit=20) as (server, application):
            accepted = post(
                server, raw=exactly_at_limit, key="local-test-key-at-limit"
            )
            rejected = post(
                server, raw=one_byte_over, key="local-test-key-over-limit"
            )

            self.assertIn("local-test-key-at-limit", application._accepted)
            self.assertNotIn("local-test-key-over-limit", application._accepted)

        accepted_status, accepted_headers, accepted_body = accepted
        self.assertEqual(accepted_status, 202)
        self.assert_response_conforms(
            accepted_status, accepted_headers, accepted_body
        )

        rejected_status, rejected_headers, rejected_body = rejected
        self.assertEqual(rejected_status, 400)
        self.assertEqual(
            rejected_body,
            {
                "error": {
                    "code": "invalid_json",
                    "message": "Request body must be valid JSON.",
                }
            },
        )
        self.assert_response_conforms(
            rejected_status, rejected_headers, rejected_body
        )

    def test_invalid_content_length_framing_is_rejected_before_application(self):
        with running_mock(rate_limit=20) as (server, application):
            with patch.object(
                application, "submit", wraps=application.submit
            ) as submit:
                outcomes = {
                    "missing": post_with_raw_framing(server, []),
                    "zero": post_with_raw_framing(server, ["Content-Length: 0"]),
                    "malformed": post_with_raw_framing(
                        server, ["Content-Length: not-a-number"]
                    ),
                }

            submit.assert_not_called()
            self.assertEqual(application._accepted, {})
            self.assertEqual(application._attempts, {})

        expected_body = {
            "error": {
                "code": "invalid_json",
                "message": "Request body must be valid JSON.",
            }
        }
        for label, (status, headers, body) in outcomes.items():
            with self.subTest(label=label):
                self.assertEqual(status, 400)
                self.assertEqual(body, expected_body)
                self.assert_response_conforms(status, headers, body)

    def test_signed_content_length_is_rejected_before_body_and_application(self):
        with running_mock(rate_limit=20) as (server, application):
            with patch.object(
                application, "submit", wraps=application.submit
            ) as submit:
                (
                    status,
                    headers,
                    body,
                    connection_will_close,
                    peer_closed,
                ) = post_without_declared_body(
                    server,
                    host_header=(
                        f"Host: {server.server_address[0]}:{server.server_address[1]}"
                    ),
                    content_length="+1",
                )

            submit.assert_not_called()
            self.assertEqual(application._accepted, {})
            self.assertEqual(application._attempts, {})

        self.assertEqual(status, 400)
        self.assertEqual(
            body,
            {
                "error": {
                    "code": "invalid_json",
                    "message": "Request body must be valid JSON.",
                }
            },
        )
        self.assert_response_conforms(status, headers, body)
        self.assertTrue(connection_will_close)
        self.assertTrue(peer_closed)

    def test_ambiguous_request_framing_is_rejected_before_application(self):
        body_length = len(json.dumps(VALID_PAYLOAD).encode("utf-8"))
        with running_mock(rate_limit=20) as (server, application):
            with patch.object(
                application, "submit", wraps=application.submit
            ) as submit:
                outcomes = {
                    "transfer encoding": post_with_raw_framing(
                        server,
                        [
                            f"Content-Length: {body_length}",
                            "Transfer-Encoding: chunked",
                        ],
                    ),
                    "duplicate equal content length": post_with_raw_framing(
                        server,
                        [
                            f"Content-Length: {body_length}",
                            f"Content-Length: {body_length}",
                        ],
                    ),
                    "duplicate conflicting content length": post_with_raw_framing(
                        server,
                        [
                            f"Content-Length: {body_length}",
                            "Content-Length: 1",
                        ],
                    ),
                }

            submit.assert_not_called()
            self.assertEqual(application._accepted, {})
            self.assertEqual(application._attempts, {})

        expected_body = {
            "error": {
                "code": "invalid_json",
                "message": "Request body must be valid JSON.",
            }
        }
        for label, (status, headers, body) in outcomes.items():
            with self.subTest(label=label):
                self.assertEqual(status, 400)
                self.assertEqual(body, expected_body)
                self.assert_response_conforms(status, headers, body)

    def test_transfer_encoding_with_content_length_is_rejected_before_body_and_application(
        self,
    ):
        with running_mock(rate_limit=20) as (server, application):
            with patch.object(
                application, "submit", wraps=application.submit
            ) as submit:
                (
                    status,
                    headers,
                    body,
                    connection_will_close,
                    peer_closed,
                ) = post_without_declared_body(
                    server,
                    host_header=(
                        f"Host: {server.server_address[0]}:{server.server_address[1]}"
                    ),
                    extra_headers=("Transfer-Encoding: chunked",),
                )

            submit.assert_not_called()
            self.assertEqual(application._accepted, {})
            self.assertEqual(application._attempts, {})

        self.assertEqual(status, 400)
        self.assertEqual(
            body,
            {
                "error": {
                    "code": "invalid_json",
                    "message": "Request body must be valid JSON.",
                }
            },
        )
        self.assert_response_conforms(status, headers, body)
        self.assertTrue(connection_will_close)
        self.assertTrue(peer_closed)

    def test_duplicate_content_length_is_rejected_before_body_and_application(
        self,
    ):
        expected_body = {
            "error": {
                "code": "invalid_json",
                "message": "Request body must be valid JSON.",
            }
        }

        with running_mock(rate_limit=20) as (server, application):
            host_header = (
                f"Host: {server.server_address[0]}:{server.server_address[1]}"
            )
            with patch.object(
                application, "submit", wraps=application.submit
            ) as submit:
                outcomes = {
                    "equal values": post_without_declared_body(
                        server,
                        host_header=host_header,
                        content_length="1",
                        extra_headers=("Content-Length: 1",),
                    ),
                    "conflicting values": post_without_declared_body(
                        server,
                        host_header=host_header,
                        content_length="1",
                        extra_headers=("Content-Length: 2",),
                    ),
                }

            submit.assert_not_called()
            self.assertEqual(application._accepted, {})
            self.assertEqual(application._attempts, {})

        for label, (
            status,
            headers,
            body,
            connection_will_close,
            peer_closed,
        ) in outcomes.items():
            with self.subTest(label=label):
                self.assertEqual(status, 400)
                self.assertEqual(body, expected_body)
                self.assert_response_conforms(status, headers, body)
                self.assertTrue(connection_will_close)
                self.assertTrue(peer_closed)

    def test_truncated_request_body_is_rejected_before_application(self):
        body = json.dumps(VALID_PAYLOAD).encode("utf-8")
        with running_mock(rate_limit=20) as (server, application):
            with patch.object(
                application, "submit", wraps=application.submit
            ) as submit:
                status, headers, response_body = post_with_raw_framing(
                    server,
                    [f"Content-Length: {len(body) + 1}"],
                    body=body,
                    half_close_write=True,
                )

            submit.assert_not_called()
            self.assertEqual(application._accepted, {})
            self.assertEqual(application._attempts, {})

        self.assertEqual(status, 400)
        self.assertEqual(
            response_body,
            {
                "error": {
                    "code": "invalid_json",
                    "message": "Request body must be valid JSON.",
                }
            },
        )
        self.assert_response_conforms(status, headers, response_body)

    def test_invalid_payload_returns_safe_422_fields(self):
        invalid = copy.deepcopy(VALID_PAYLOAD)
        invalid.pop("email")
        invalid["website"] = "filled"
        invalid["private-value@example.invalid"] = "must not be reflected"
        with running_mock() as (server, _application):
            status, _headers, body = post(server, payload=invalid)

        self.assertEqual(status, 422)
        self.assertEqual(body["error"]["code"], "invalid_request")
        self.assertIn({"field": "email", "code": "required"}, body["error"]["fields"])
        self.assertIn({"field": "website", "code": "too_long"}, body["error"]["fields"])
        self.assertNotIn("filled", json.dumps(body))
        self.assertNotIn("private-value", json.dumps(body))

    def test_rate_limit_returns_429_and_retry_after(self):
        with running_mock(rate_limit=2) as (server, _application):
            self.assertEqual(post(server, key="local-test-key-0001")[0], 202)
            self.assertEqual(post(server, key="local-test-key-0002")[0], 202)
            status, headers, body = post(server, key="local-test-key-0003")

        self.assertEqual(status, 429)
        self.assertGreaterEqual(int(headers["Retry-After"]), 1)
        self.assertEqual(body["error"]["code"], "rate_limited")


if __name__ == "__main__":
    unittest.main()
