-- Assistant safeguards: per-user rate limiting + global spend tracking.
-- One row per assistant request, so we can (a) count a user's recent requests
-- for the rate limit and (b) sum cost for the hard spending cap. Both are
-- required before the Intelligent Observing Assistant goes public.
CREATE TABLE IF NOT EXISTS assistant_requests (
    id SERIAL PRIMARY KEY,
    user_key VARCHAR(64) NOT NULL,          -- user id, or a session/IP hash for anon
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd NUMERIC(10, 6) NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_assistant_requests_user_time
    ON assistant_requests(user_key, created_at);
CREATE INDEX IF NOT EXISTS idx_assistant_requests_time
    ON assistant_requests(created_at);
