from app.database import get_connection
from app.periods import month_bounds
from app.repositories import usage_repository
from app.services.metering import MeteringError


def get_usage_summary(tenant_id, now=None):
    start, end = month_bounds(now)
    connection = get_connection()

    try:
        connection.execute("BEGIN")

        subscription = usage_repository.get_subscription(
            connection, tenant_id
        )

        if subscription is None:
            raise MeteringError(
                "subscription_unavailable",
                "No subscription is configured for this tenant.",
            )

        totals = usage_repository.get_usage(
            connection, tenant_id, start, end
        )

        used = {
            "api_calls": totals["api_calls"],
            "tokens": totals["tokens"],
        }

        limits = {
            "api_calls": subscription["api_call_limit"],
            "tokens": subscription["token_limit"],
        }

        result = {
            "tenant_id": tenant_id,
            "plan": subscription["plan_name"],
            "subscription_status": subscription["status"],
            "period": {
                "start": start,
                "end": end,
            },
            "used": used,
            "limits": limits,
            "remaining": {
                resource: max(0, limits[resource] - used[resource])
                for resource in limits
            },
        }

        connection.execute("COMMIT")
        return result

    except Exception:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise

    finally:
        connection.close()