-- Create saved_searches table
-- Stores a named search/filter (map search text, min score, condition, map style)
-- so users can re-run a Live Map query with one click.
CREATE TABLE IF NOT EXISTS saved_searches (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    query_text VARCHAR(255),
    min_score INTEGER,
    condition VARCHAR(50),
    map_style VARCHAR(50),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_saved_searches_user_id ON saved_searches(user_id);
