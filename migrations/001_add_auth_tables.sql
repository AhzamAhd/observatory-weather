-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create saved_observatories table
CREATE TABLE IF NOT EXISTS saved_observatories (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    observatory_id INTEGER NOT NULL REFERENCES observatories(id) ON DELETE CASCADE,
    name VARCHAR(255),
    notes TEXT,
    saved_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, observatory_id)
);

-- Create observation_sessions table (for logging observations)
CREATE TABLE IF NOT EXISTS observation_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    target VARCHAR(255),
    observatory_id INTEGER NOT NULL REFERENCES observatories(id),
    notes TEXT,
    data JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_saved_observatories_user_id ON saved_observatories(user_id);
CREATE INDEX IF NOT EXISTS idx_observation_sessions_user_id ON observation_sessions(user_id);
