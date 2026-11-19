def find_event(connection, tenant_id, key):
    return connection.execute(
        """
        SELECT request_hash, response_status, response_body
        FROM usage_events
        WHERE tenant_id = ? AND idempotency_key = ?
        """,
        (tenant_id, key),
    ).fetchone()


def get_subscription(connection, tenant_id):
    return connection.execute(
        """
        SELECT subscriptions.status,
               plans.api_call_limit,
               plans.token_limit
        FROM subscriptions
        JOIN plans ON plans.id = subscriptions.plan_id
        WHERE subscriptions.tenant_id = ?
        """,
        (tenant_id,),
    ).fetchone()


def get_usage(connection, tenant_id, start, end):
    return connection.execute(
        """
        SELECT COALESCE(SUM(api_calls), 0) AS api_calls,
               COALESCE(SUM(input_tokens + output_tokens), 0) AS tokens
        FROM usage_events
        WHERE tenant_id = ?
          AND created_at >= ?
          AND created_at < ?
        """,
        (tenant_id, start, end),
    ).fetchone()


def insert_event(connection, event):
    connection.execute(
        """
        INSERT INTO usage_events (
            tenant_id, idempotency_key, request_hash, api_calls,
            input_tokens, cached_input_tokens,
            output_tokens, reasoning_tokens, created_at,
            response_status, response_body
        )
        VALUES (
            :tenant_id, :idempotency_key, :request_hash, :api_calls,
            :input_tokens, :cached_input_tokens,
            :output_tokens, :reasoning_tokens, :created_at,
            :response_status, :response_body
        )
        """,
        event,
    )