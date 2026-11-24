import unittest

from app.services.pricing import calculate_cost, format_usd


class PricingTests(unittest.TestCase):
    def setUp(self):
        self.counts = {
            "api_calls": 1,
            "input_tokens": 1000,
            "cached_input_tokens": 200,
            "output_tokens": 300,
            "reasoning_tokens": 100,
        }

    def test_sample_cost(self):
        cost = calculate_cost(**self.counts)

        self.assertEqual(cost["breakdown_micros"], {
            "api_calls": 100,
            "fresh_input_tokens": 1600,
            "cached_input_tokens": 200,
            "output_tokens": 2400,
        })
        self.assertEqual(cost["total_micros"], 4300)
        self.assertEqual(cost["total_usd"], "0.004300")

    def test_zero_usage(self):
        cost = calculate_cost(0, 0, 0, 0, 0)

        self.assertEqual(cost["total_micros"], 0)
        self.assertEqual(cost["total_usd"], "0.000000")

    def test_cached_input_is_cheaper(self):
        fresh = calculate_cost(0, 1000, 0, 0, 0)
        cached = calculate_cost(0, 1000, 1000, 0, 0)

        self.assertEqual(fresh["total_micros"], 2000)
        self.assertEqual(cached["total_micros"], 1000)

    def test_reasoning_is_not_charged_twice(self):
        first = calculate_cost(**self.counts)
        changed = {**self.counts, "reasoning_tokens": 300}

        self.assertEqual(first, calculate_cost(**changed))

    def test_one_million_fresh_tokens(self):
        cost = calculate_cost(0, 1_000_000, 0, 0, 0)

        self.assertEqual(cost["total_micros"], 2_000_000)
        self.assertEqual(cost["total_usd"], "2.000000")

    def test_one_microdollar_format(self):
        self.assertEqual(format_usd(1), "0.000001")

    def test_one_dollar_format(self):
        self.assertEqual(format_usd(1_000_000), "1.000000")

    def test_large_integer_format(self):
        self.assertEqual(
            format_usd(10**18 + 1),
            "1000000000000.000001",
        )

    def test_invalid_values_are_rejected(self):
        for name in self.counts:
            for value in [-1, 1.5, "1", True, None]:
                with self.subTest(name=name, value=value):
                    changed = {**self.counts, name: value}

                    with self.assertRaises(ValueError):
                        calculate_cost(**changed)

        for value in [-1, 1.5, "100", True, None]:
            with self.subTest(money=value):
                with self.assertRaises(ValueError):
                    format_usd(value)

    def test_cached_input_cannot_exceed_input(self):
        changed = {
            **self.counts,
            "cached_input_tokens": 1001,
        }

        with self.assertRaises(ValueError):
            calculate_cost(**changed)

    def test_reasoning_cannot_exceed_output(self):
        changed = {
            **self.counts,
            "reasoning_tokens": 301,
        }

        with self.assertRaises(ValueError):
            calculate_cost(**changed)

    def test_money_fields_use_integers(self):
        cost = calculate_cost(**self.counts)

        self.assertIs(type(cost["total_micros"]), int)
        self.assertIs(type(cost["total_usd"]), str)

        for amount in cost["breakdown_micros"].values():
            self.assertIs(type(amount), int)