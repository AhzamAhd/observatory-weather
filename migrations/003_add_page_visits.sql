-- Create page_visits table
-- Records one row per Streamlit session load, so the site keeps its own
-- gap-free visitor count independent of Google Analytics. user_id is NULL
-- for anonymous (not-logged-in) visitors.
CREATE TABLE IF NOT EXISTS page_visits (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    page VARCHAR(255),
    visited_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_page_visits_visited_at ON page_visits(visited_at);
CREATE INDEX IF NOT EXISTS idx_page_visits_session_id ON page_visits(session_id);
