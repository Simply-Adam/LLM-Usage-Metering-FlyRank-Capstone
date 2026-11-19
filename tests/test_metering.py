import io
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.database import get_connection
from app.main import app
from app.migrate import migrate
from app.seed import seed_data
from app.services.metering import record_usage


TEST_A = "test-tenant-a-" + "a" * 32
TEST_B = "test-tenant-b-" + "b" * 32


class MeteringTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)

        database_patch = patch(
            "app.database.DATABASE_PATH",
            Path(directory.name) / "test.db",
        )
        database_patch.start()
        self.addCleanup(database_patch.stop)

        with redirect_stdout(io.StringIO()):
            migrate()

        connection = get_connection()

        try:
            seed_data(connection, [
                (1, "Demo Tenant A", TEST_A),
                (2, "Demo Tenant B", TEST_B),
            ])
        finally:
            connection.close()

        clock_patch = patch(
            "app.routers.generate.record_usage",
            partial(
                record_usage,
                now=datetime(2030, 1, 15, tzinfo=timezone.utc),
            ),
        )
        clock_patch.start()
        self.addCleanup(clock_patch.stop)

        self.client = TestClient(app)
        self.addCleanup(self.client.close)

        self.payload = {
            "input_tokens": 1000,
            "cached_input_tokens": 200,
            "output_tokens": 300,
            "reasoning_tokens": 100,
        }

    def db(self, sql, parameters=()):
        connection = get_connection()

        try:
            return connection.execute(sql, parameters).fetchall()
        finally:
            connection.close()

    def generate(self, key, payload=None, api_key=TEST_A):
        return self.client.post(
            "/generate",
            headers={
                "X-API-Key": api_key,
                "Idempotency-Key": key,
            },
            json=self.payload if payload is None else payload,
        )

    def count_events(self):
        return self.db("SELECT COUNT(*) FROM usage_events")[0][0]

    def test_retry_returns_original_response(self):
        first = self.generate("retry-1")
        second = self.generate("retry-1")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.content, second.content)
        self.assertEqual(self.count_events(), 1)

    def test_changed_payload_returns_409(self):
        self.assertEqual(
            self.generate("conflict-1").status_code,
            200,
        )

        changed = {**self.payload, "input_tokens": 1001}
        response = self.generate("conflict-1", changed)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.count_events(), 1)

    def test_api_quota_boundary_and_replay(self):
        self.db(
            "UPDATE plans SET api_call_limit = 2 WHERE name = 'free'"
        )

        self.assertEqual(self.generate("call-1").status_code, 200)

        boundary = self.generate("call-2")
        blocked = self.generate("call-3")
        replay = self.generate("call-2")

        self.assertEqual(boundary.status_code, 200)
        self.assertEqual(blocked.status_code, 429)

        self.assertEqual(
            blocked.json()["detail"]["resource"],
            "api_calls",
        )

        self.assertIn("retry-after", blocked.headers)
        self.assertEqual(replay.status_code, 200)
        self.assertEqual(replay.content, boundary.content)
        self.assertEqual(self.count_events(), 2)

    def test_token_boundary_without_double_counting(self):
        self.db(
            "UPDATE plans SET token_limit = 1300 WHERE name = 'free'"
        )

        boundary = self.generate("token-1")
        blocked = self.generate(
            "token-2",
            {"input_tokens": 1, "output_tokens": 0},
        )

        self.assertEqual(boundary.status_code, 200)

        self.assertEqual(
            boundary.json()["usage"]["total_tokens"],
            1300,
        )

        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(blocked.json()["detail"]["resource"], "tokens")
        self.assertEqual(blocked.json()["detail"]["used"], 1300)
        self.assertEqual(self.count_events(), 1)

    def test_inactive_subscription_returns_402(self):
        self.db(
            """
            UPDATE subscriptions
            SET status = 'past_due'
            WHERE tenant_id = 1
            """
        )

        response = self.generate("inactive-1")

        self.assertEqual(response.status_code, 402)
        self.assertEqual(self.count_events(), 0)

    def test_tenants_have_independent_keys_and_quotas(self):
        self.db(
            "UPDATE plans SET api_call_limit = 1 WHERE name = 'free'"
        )

        first = self.generate("shared-key", api_key=TEST_A)
        second = self.generate("shared-key", api_key=TEST_B)
        blocked = self.generate("another-key", api_key=TEST_A)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["tenant_id"], 1)
        self.assertEqual(second.json()["tenant_id"], 2)
        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(self.count_events(), 2)

    def test_invalid_requests_are_not_metered(self):
        response = self.generate(
            "invalid-1",
            {**self.payload, "input_tokens": -1},
        )
        self.assertEqual(response.status_code, 422)

        response = self.client.post(
            "/generate",
            headers={"X-API-Key": TEST_A},
            json=self.payload,
        )
        self.assertEqual(response.status_code, 422)

        for key in ["   ", "x" * 256]:
            self.assertEqual(self.generate(key).status_code, 422)

        response = self.client.post(
            "/generate",
            headers={"Idempotency-Key": "missing-auth"},
            json=self.payload,
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.count_events(), 0)

    def test_concurrent_requests_cannot_exceed_quota(self):
        self.db(
            "UPDATE plans SET api_call_limit = 1 WHERE name = 'free'"
        )

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(
                self.generate,
                ["parallel-1", "parallel-2"],
            ))

        self.assertEqual(
            sorted(response.status_code for response in responses),
            [200, 429],
        )
        self.assertEqual(self.count_events(), 1)

    def test_concurrent_retries_create_one_event(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(
                self.generate,
                ["parallel-retry", "parallel-retry"],
            ))

        self.assertEqual(
            [response.status_code for response in responses],
            [200, 200],
        )

        self.assertEqual(responses[0].content, responses[1].content)
        self.assertEqual(self.count_events(), 1)