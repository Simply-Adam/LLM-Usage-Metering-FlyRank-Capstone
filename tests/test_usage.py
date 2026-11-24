import io
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.database import get_connection
from app.main import app
from app.migrate import migrate
from app.schemas import GenerateRequest
from app.seed import seed_data
from app.services.metering import record_usage
from app.services.usage import get_usage_summary


TEST_A = "test-tenant-a-" + "a" * 32
TEST_B = "test-tenant-b-" + "b" * 32


class UsageTests(unittest.TestCase):
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

        self.now = datetime(2030, 1, 15, tzinfo=timezone.utc)

        clock_patch = patch(
            "app.routers.usage.get_usage_summary",
            partial(get_usage_summary, now=self.now),
        )
        clock_patch.start()
        self.addCleanup(clock_patch.stop)

        self.client = TestClient(app)
        self.addCleanup(self.client.close)

        self.request = GenerateRequest(
            input_tokens=1000,
            cached_input_tokens=200,
            output_tokens=300,
            reasoning_tokens=100,
        )

    def db(self, sql, parameters=()):
        connection = get_connection()

        try:
            return connection.execute(sql, parameters).fetchall()
        finally:
            connection.close()

    def record(self, tenant_id=1, key="usage-1", when=None):
        return record_usage(
            tenant_id,
            self.request,
            key,
            now=self.now if when is None else when,
        )

    def summary(self, api_key=TEST_A, path="/usage"):
        return self.client.get(
            path,
            headers={"X-API-Key": api_key},
        )

    def test_empty_usage(self):
        response = self.summary()
        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(data["plan"], "free")
        self.assertEqual(data["subscription_status"], "active")
        self.assertEqual(data["used"], {
            "api_calls": 0,
            "tokens": 0,
        })
        self.assertEqual(data["remaining"], {
            "api_calls": 1000,
            "tokens": 100000,
        })
        self.assertEqual(data["period"], {
            "start": "2030-01-01T00:00:00.000Z",
            "end": "2030-02-01T00:00:00.000Z",
        })

    def test_usage_and_remaining(self):
        self.record()
        data = self.summary().json()

        self.assertEqual(data["used"], {
            "api_calls": 1,
            "tokens": 1300,
        })
        self.assertEqual(data["limits"], {
            "api_calls": 1000,
            "tokens": 100000,
        })
        self.assertEqual(data["remaining"], {
            "api_calls": 999,
            "tokens": 98700,
        })

    def test_tenants_are_isolated(self):
        self.record(tenant_id=1)

        data = self.summary(
            TEST_B,
            "/usage?tenant_id=1",
        ).json()

        self.assertEqual(data["tenant_id"], 2)
        self.assertEqual(data["used"], {
            "api_calls": 0,
            "tokens": 0,
        })
        self.assertEqual(self.summary().json()["used"], {
            "api_calls": 1,
            "tokens": 1300,
        })

    def test_month_boundaries(self):
        moments = [
            datetime(
                2029, 12, 31, 23, 59, 59, 999000,
                tzinfo=timezone.utc,
            ),
            datetime(2030, 1, 1, tzinfo=timezone.utc),
            datetime(
                2030, 1, 31, 23, 59, 59, 999000,
                tzinfo=timezone.utc,
            ),
            datetime(2030, 2, 1, tzinfo=timezone.utc),
        ]

        for index, moment in enumerate(moments):
            self.record(
                key=f"month-{index}",
                when=moment,
            )

        self.assertEqual(self.summary().json()["used"], {
            "api_calls": 2,
            "tokens": 2600,
        })

    def test_plan_change_is_reflected(self):
        self.record()

        self.db(
            """
            UPDATE subscriptions
            SET plan_id = (
                SELECT id FROM plans WHERE name = 'pro'
            )
            WHERE tenant_id = 1
            """
        )

        data = self.summary().json()

        self.assertEqual(data["plan"], "pro")
        self.assertEqual(data["limits"], {
            "api_calls": 10000,
            "tokens": 1000000,
        })
        self.assertEqual(data["remaining"], {
            "api_calls": 9999,
            "tokens": 998700,
        })

    def test_authentication_is_required(self):
        self.assertEqual(
            self.client.get("/usage").status_code,
            401,
        )
        self.assertEqual(
            self.summary("invalid-key").status_code,
            401,
        )

    def test_reading_usage_does_not_create_events(self):
        self.db(
            "UPDATE plans SET api_call_limit = 1 WHERE name = 'free'"
        )
        self.record()

        first = self.summary()
        second = self.summary()

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json(), second.json())
        self.assertEqual(
            self.db("SELECT COUNT(*) FROM usage_events")[0][0],
            1,
        )

    def test_inactive_subscription_can_read_usage(self):
        self.record()

        self.db(
            """
            UPDATE subscriptions
            SET status = 'past_due'
            WHERE tenant_id = 1
            """
        )

        response = self.summary()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["subscription_status"],
            "past_due",
        )
        self.assertEqual(
            response.json()["used"]["tokens"],
            1300,
        )

    def test_missing_subscription_returns_503(self):
        self.db(
            "DELETE FROM subscriptions WHERE tenant_id = 1"
        )

        response = self.summary()

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json()["detail"]["code"],
            "subscription_unavailable",
        )

    def test_remaining_never_becomes_negative(self):
        self.record()

        self.db(
            "UPDATE plans SET token_limit = 1000 WHERE name = 'free'"
        )

        data = self.summary().json()

        self.assertEqual(data["used"]["tokens"], 1300)
        self.assertEqual(data["remaining"]["tokens"], 0)
        
    
    def test_empty_usage_has_zero_cost(self):
        cost = self.summary().json()["cost"]

        self.assertEqual(cost["kind"], "usage_estimate")
        self.assertEqual(cost["currency"], "USD")
        self.assertEqual(cost["pricing_version"], "demo-v1")
        self.assertEqual(cost["total_micros"], 0)
        self.assertEqual(cost["total_usd"], "0.000000")

    def test_monthly_cost_rollup(self):
        self.record(key="cost-1")
        self.record(key="cost-2")

        self.record(
            key="previous-month",
            when=datetime(2029, 12, 31, tzinfo=timezone.utc),
        )

        data = self.summary().json()

        self.assertEqual(data["used"], {
            "api_calls": 2,
            "tokens": 2600,
        })
        self.assertEqual(
            data["cost"]["total_micros"],
            8600,
        )
        self.assertEqual(
            data["cost"]["total_usd"],
            "0.008600",
        )

    def test_costs_are_isolated_and_reads_add_no_cost(self):
        self.record()

        first = self.summary().json()
        second = self.summary().json()
        other = self.summary(TEST_B).json()

        self.assertEqual(first["cost"], second["cost"])
        self.assertEqual(first["cost"]["total_micros"], 4300)
        self.assertEqual(other["tenant_id"], 2)
        self.assertEqual(other["cost"]["total_micros"], 0)

        self.assertEqual(
            self.db("SELECT COUNT(*) FROM usage_events")[0][0],
            1,
        )