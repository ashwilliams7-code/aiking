import copy
import json
import re
import unittest
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / "api"
SPEC_PATH = API_DIR / "lead-capture.openapi.json"
SCHEMA_PATH = API_DIR / "schemas" / "lead-request.schema.json"


def load_json(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def iter_refs(value):
    if isinstance(value, dict):
        if "$ref" in value:
            yield value["$ref"]
        for child in value.values():
            yield from iter_refs(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_refs(child)


def resolve_pointer(document, pointer):
    value = document
    for token in pointer.removeprefix("#/").split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        value = value[token]
    return value


def validate_schema_subset(schema, value, path="$"):
    """Validate the JSON Schema keywords used by the request contract."""
    errors = []
    expected_type = schema.get("type")
    type_matches = {
        "object": isinstance(value, dict),
        "string": isinstance(value, str),
        "boolean": isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "array": isinstance(value, list),
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
        if "pattern" in schema and re.fullmatch(schema["pattern"], value) is None:
            errors.append(f"{path}: does not match pattern")
        if schema.get("format") == "email":
            email_pattern = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
            if re.fullmatch(email_pattern, value) is None:
                errors.append(f"{path}: invalid email format")

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
                    validate_schema_subset(properties[field], child, f"{path}.{field}")
                )

    return errors


class LeadCaptureContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = load_json(SPEC_PATH)
        cls.request_schema = load_json(SCHEMA_PATH)
        cls.post = cls.spec["paths"]["/v1/lead-requests"]["post"]
        cls.example = cls.post["requestBody"]["content"]["application/json"][
            "example"
        ]

    def test_contract_is_openapi_31_and_loopback_only(self):
        self.assertEqual(self.spec["openapi"], "3.1.0")
        self.assertEqual(
            self.spec["jsonSchemaDialect"],
            "https://json-schema.org/draft/2020-12/schema",
        )
        self.assertTrue(self.spec["servers"])
        for server in self.spec["servers"]:
            parsed = urlparse(server["url"])
            self.assertEqual(parsed.scheme, "http")
            self.assertIn(parsed.hostname, {"127.0.0.1", "localhost", "::1"})

    def test_all_references_resolve(self):
        for ref in iter_refs(self.spec):
            if ref.startswith("#/"):
                self.assertIsNotNone(resolve_pointer(self.spec, ref))
                continue
            target = (API_DIR / ref).resolve()
            self.assertTrue(target.is_relative_to(API_DIR.resolve()))
            self.assertTrue(target.is_file(), ref)
            self.assertIsInstance(load_json(target), dict)

    def test_post_requires_json_and_idempotency_key(self):
        parameters = {
            (parameter["in"], parameter["name"]): parameter
            for parameter in self.post["parameters"]
        }
        idempotency = parameters[("header", "Idempotency-Key")]
        self.assertTrue(idempotency["required"])
        self.assertGreaterEqual(idempotency["schema"]["minLength"], 16)
        self.assertIn("application/json", self.post["requestBody"]["content"])
        self.assertEqual(
            self.post["requestBody"]["content"]["application/json"]["schema"][
                "$ref"
            ],
            "./schemas/lead-request.schema.json",
        )

    def test_response_and_safety_contract(self):
        self.assertTrue(
            {"202", "400", "409", "415", "422", "429", "500"}.issubset(
                self.post["responses"]
            )
        )
        self.assertTrue(
            self.post["responses"]["429"]["$ref"].endswith("/RateLimited")
        )
        handling = self.post["x-data-handling"]
        self.assertFalse(handling["responseEchoesSubmittedFields"])
        self.assertFalse(handling["notificationSideEffectsInLocalDevelopment"])

        accepted = self.spec["components"]["schemas"]["LeadAccepted"]
        self.assertTrue(accepted["additionalProperties"] is False)
        self.assertTrue(
            set(self.request_schema["properties"]).isdisjoint(
                accepted["properties"]
            )
        )

    def test_documented_example_satisfies_request_schema(self):
        self.assertEqual(validate_schema_subset(self.request_schema, self.example), [])

    def test_invalid_payload_classes_are_rejected(self):
        cases = {}

        missing_email = copy.deepcopy(self.example)
        missing_email.pop("email")
        cases["missing required field"] = missing_email

        bad_email = copy.deepcopy(self.example)
        bad_email["email"] = "not-an-email"
        cases["invalid email"] = bad_email

        unknown_property = copy.deepcopy(self.example)
        unknown_property["internal_note"] = "must not be accepted"
        cases["unknown property"] = unknown_property

        short_outcome = copy.deepcopy(self.example)
        short_outcome["outcome"] = "Too short"
        cases["short outcome"] = short_outcome

        filled_honeypot = copy.deepcopy(self.example)
        filled_honeypot["website"] = "https://example.com"
        cases["filled honeypot"] = filled_honeypot

        bad_timeframe = copy.deepcopy(self.example)
        bad_timeframe["timeframe"] = "immediately"
        cases["unknown timeframe"] = bad_timeframe

        for label, payload in cases.items():
            with self.subTest(label=label):
                self.assertTrue(validate_schema_subset(self.request_schema, payload))


if __name__ == "__main__":
    unittest.main()
