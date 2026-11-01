CREATE TABLE plans (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE CHECK (name IN ('free', 'pro')),
    api_call_limit INTEGER NOT NULL CHECK (api_call_limit >= 0),
    token_limit INTEGER NOT NULL CHECK (token_limit >= 0)
);

CREATE TABLE tenants (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    api_key_hash TEXT NOT NULL UNIQUE CHECK (length(api_key_hash) = 64),
    created_at TEXT NOT NULL DEFAULT (
        strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
    )
);

CREATE TABLE subscriptions (
    tenant_id INTEGER PRIMARY KEY REFERENCES tenants(id),
    plan_id INTEGER NOT NULL REFERENCES plans(id),

    status TEXT NOT NULL DEFAULT 'active' CHECK (
        status IN (
            'active',
            'trialing',
            'past_due',
            'unpaid',
            'canceled',
            'incomplete',
            'incomplete_expired',
            'paused'
        )
    ),

    stripe_customer_id TEXT UNIQUE,
    stripe_subscription_id TEXT UNIQUE
);

CREATE INDEX idx_subscriptions_plan_id
ON subscriptions(plan_id);