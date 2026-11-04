import os
import secrets

from dotenv import load_dotenv

from app.database import PROJECT_ROOT, get_connection
from app.security import hash_api_key


def create_demo_env():
    env_path = PROJECT_ROOT / ".env"

    try:
        with env_path.open("x", encoding="utf-8") as file:
            file.write(
                f"TENANT_A_API_KEY={secrets.token_hex(32)}\n"
                f"TENANT_B_API_KEY={secrets.token_hex(32)}\n"
            )
    except FileExistsError:
        return

    print("Created .env with demo API keys. Values are hidden.")


def get_demo_tenants():
    load_dotenv(
        PROJECT_ROOT / ".env",
        encoding="utf-8-sig",
    )

    settings = [
        (1, "Demo Tenant A", "TENANT_A_API_KEY"),
        (2, "Demo Tenant B", "TENANT_B_API_KEY"),
    ]

    tenants = []

    for tenant_id, name, variable_name in settings:
        api_key = os.getenv(variable_name, "").strip()

        if len(api_key) < 32:
            raise ValueError(
                f"{variable_name} must contain an API key "
                "with at least 32 characters."
            )

        tenants.append((tenant_id, name, api_key))

    if tenants[0][2] == tenants[1][2]:
        raise ValueError("The two tenants must use different API keys.")

    return tenants


def seed_data(connection, tenants):
    plans = [
        ("free", 1_000, 100_000),
        ("pro", 10_000, 1_000_000),
    ]

    try:
        connection.execute("BEGIN IMMEDIATE")

        for name, api_call_limit, token_limit in plans:
            connection.execute(
                """
                INSERT INTO plans (
                    name, api_call_limit, token_limit
                )
                VALUES (?, ?, ?)
                ON CONFLICT(name) DO NOTHING
                """,
                (name, api_call_limit, token_limit),
            )

        free_plan_id = connection.execute(
            "SELECT id FROM plans WHERE name = ?",
            ("free",),
        ).fetchone()["id"]

        for tenant_id, name, api_key in tenants:
            key_hash = hash_api_key(api_key)

            connection.execute(
                """
                INSERT INTO tenants (id, name, api_key_hash)
                VALUES (?, ?, ?)
                ON CONFLICT(id) DO NOTHING
                """,
                (tenant_id, name, key_hash),
            )

            existing = connection.execute(
                """
                SELECT name, api_key_hash
                FROM tenants
                WHERE id = ?
                """,
                (tenant_id,),
            ).fetchone()

            if (
                existing["name"] != name
                or existing["api_key_hash"] != key_hash
            ):
                raise ValueError(
                    f"Demo tenant {tenant_id} already exists "
                    "with different details. Check your .env keys."
                )

            connection.execute(
                """
                INSERT INTO subscriptions (
                    tenant_id, plan_id, status
                )
                VALUES (?, ?, ?)
                ON CONFLICT(tenant_id) DO NOTHING
                """,
                (tenant_id, free_plan_id, "active"),
            )

        connection.execute("COMMIT")

    except Exception:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise


def seed():
    create_demo_env()
    tenants = get_demo_tenants()
    connection = get_connection()

    try:
        seed_data(connection, tenants)

        rows = connection.execute(
            """
            SELECT tenants.name,
                   plans.name AS plan,
                   subscriptions.status
            FROM tenants
            JOIN subscriptions
                ON subscriptions.tenant_id = tenants.id
            JOIN plans
                ON plans.id = subscriptions.plan_id
            WHERE tenants.id IN (1, 2)
            ORDER BY tenants.id
            """
        ).fetchall()

        print("Seed complete.")

        for row in rows:
            print(
                f"{row['name']}: "
                f"plan={row['plan']}, "
                f"status={row['status']}"
            )

    finally:
        connection.close()


if __name__ == "__main__":
    seed()