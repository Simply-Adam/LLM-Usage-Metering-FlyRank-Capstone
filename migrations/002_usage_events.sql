CREATE TABLE usage_events (
    id INTEGER PRIMARY KEY,

    tenant_id INTEGER NOT NULL REFERENCES tenants(id),

    idempotency_key TEXT NOT NULL CHECK (
        length(idempotency_key) BETWEEN 1 AND 255
        AND length(trim(idempotency_key)) > 0
    ),

    request_hash TEXT NOT NULL CHECK (
        length(request_hash) = 64
    ),

    api_calls INTEGER NOT NULL DEFAULT 1 CHECK (
        typeof(api_calls) = 'integer' AND api_calls = 1
    ),

    input_tokens INTEGER NOT NULL CHECK (
        typeof(input_tokens) = 'integer'
        AND input_tokens BETWEEN 0 AND 1000000000
    ),

    cached_input_tokens INTEGER NOT NULL DEFAULT 0 CHECK (
        typeof(cached_input_tokens) = 'integer'
        AND cached_input_tokens BETWEEN 0 AND 1000000000
    ),

    output_tokens INTEGER NOT NULL CHECK (
        typeof(output_tokens) = 'integer'
        AND output_tokens BETWEEN 0 AND 1000000000
    ),

    reasoning_tokens INTEGER NOT NULL DEFAULT 0 CHECK (
        typeof(reasoning_tokens) = 'integer'
        AND reasoning_tokens BETWEEN 0 AND 1000000000
    ),

    created_at TEXT NOT NULL DEFAULT (
        strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
    ),

    response_status INTEGER NOT NULL CHECK (
        typeof(response_status) = 'integer'
        AND response_status BETWEEN 200 AND 299
    ),

    response_body TEXT NOT NULL,

    CHECK (cached_input_tokens <= input_tokens),
    CHECK (reasoning_tokens <= output_tokens),

    UNIQUE (tenant_id, idempotency_key)
);

CREATE INDEX idx_usage_events_tenant_created
ON usage_events(tenant_id, created_at);