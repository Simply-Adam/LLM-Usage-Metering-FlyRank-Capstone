import unittest

from pydantic import ValidationError

from app.schemas import GenerateRequest, MAX_TOKEN_COUNT


class GenerateRequestTests(unittest.TestCase):
    def setUp(self):
        self.payload = {
            "input_tokens": 1000,
            "cached_input_tokens": 200,
            "output_tokens": 300,
            "reasoning_tokens": 100,
        }

    def test_valid_payload(self):
        request = GenerateRequest(**self.payload)

        self.assertEqual(request.model_dump(), self.payload)

    def test_zero_counts_and_optional_defaults(self):
        request = GenerateRequest(
            input_tokens=0,
            output_tokens=0,
        )

        self.assertEqual(request.model_dump(), {
            "input_tokens": 0,
            "cached_input_tokens": 0,
            "output_tokens": 0,
            "reasoning_tokens": 0,
        })

    def test_invalid_counts(self):
        bad_values = [
            -1,
            1.5,
            1.0,
            "100",
            True,
            None,
            MAX_TOKEN_COUNT + 1,
        ]

        for field in self.payload:
            for value in bad_values:
                with self.subTest(field=field, value=value):
                    payload = {**self.payload, field: value}

                    with self.assertRaises(ValidationError):
                        GenerateRequest(**payload)

    def test_cached_input_cannot_exceed_input(self):
        self.payload["cached_input_tokens"] = 1001

        with self.assertRaises(ValidationError):
            GenerateRequest(**self.payload)

    def test_reasoning_cannot_exceed_output(self):
        self.payload["reasoning_tokens"] = 301

        with self.assertRaises(ValidationError):
            GenerateRequest(**self.payload)

    def test_required_counts_cannot_be_missing(self):
        for field in ["input_tokens", "output_tokens"]:
            with self.subTest(field=field):
                payload = self.payload.copy()
                del payload[field]

                with self.assertRaises(ValidationError):
                    GenerateRequest(**payload)

    def test_unknown_fields_are_rejected(self):
        with self.assertRaises(ValidationError):
            GenerateRequest(**self.payload, tenant_id=2)