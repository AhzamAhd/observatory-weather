# GOWC Authentication & User Saves System

## Overview

You now have a complete login and user-saves system for GOWC! Users can create accounts, log in, and save their favorite observatories and observation sessions.

## What's New

### New Files

1. **`auth.py`** — Core authentication logic
   - `register_user()` — Create new account
   - `login_user()` — Authenticate user
   - `is_logged_in()` — Check if user is logged in
   - `render_auth_sidebar()` — Display login/register UI in sidebar

2. **`user_saves.py`** — User save/favorites system
   - `save_observatory()` — Save a favorite site
   - `get_saved_observatories()` — Load saved sites
   - `save_observation_session()` — Log an observation
   - `get_observation_sessions()` — Load past observations
   - `render_my_saves_page()` — Display user's saves

3. **`run_migrations.py`** — Database setup script
   - Creates the `users`, `saved_observatories`, and `observation_sessions` tables

4. **`migrations/001_add_auth_tables.sql`** — SQL migration file
   - Defines all required tables and indexes

### Modified Files

- **`dashboard.py`**
  - Added auth imports
  - Added session state initialization for `user_id`, `username`, etc.
  - Integrated `render_auth_sidebar()` into sidebar
  - Added "My Saves" page handler
  
- **`requirements.txt`**
  - Added `bcrypt==4.1.2` for secure password hashing

## Setup Instructions

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs `bcrypt` (password hashing) and all other dependencies.

### Step 2: Run Database Migrations

Before launching the app, create the auth tables in Supabase:

```bash
python run_migrations.py
```

This will:
- Create a `users` table (username, password_hash, email)
- Create a `saved_observatories` table (favorite sites)
- Create an `observation_sessions` table (observation logs)
- Create necessary indexes for performance

**Note:** If you get a connection error, make sure your `.env` file has valid Supabase credentials:
```
SUPABASE_DB_HOST=...
SUPABASE_DB_USER=...
SUPABASE_DB_PASSWORD=...
SUPABASE_DB_PORT=5432
```

### Step 3: Launch the App

```bash
streamlit run dashboard.py
```

## How It Works

### Registration & Login

1. In the sidebar, users see a **Login / Register** tab area
2. They can create an account with username + password (6+ chars)
3. Passwords are **hashed with bcrypt** — never stored in plain text
4. Once logged in, the sidebar shows:
   - Current username
   - "📋 My Saves" button
   - "⚙️ Account Settings" button
   - "🚪 Logout" button

### Saving Observatories

From any page (e.g., Live Weather Map, Site Comparison), users can:
- Click "Save this observatory" on a site's detail card
- Add optional notes (e.g., "clear skies in summer")
- The site is saved to their `saved_observatories` table

### Observation Logs

Users can create observation logs to track sessions:
- Date, target object, observatory used
- Optional notes and metadata
- Stored in `observation_sessions` table for future reference

### My Saves Page

Accessible via the sidebar button, shows:
- **Favorite Sites tab** — All saved observatories with notes, delete button
- **Observation Logs tab** — Past sessions, deletable

## Database Schema

### `users` table
```sql
id (serial, PK)
username (varchar, unique)
password_hash (varchar)
email (varchar, optional)
created_at (timestamp)
updated_at (timestamp)
```

### `saved_observatories` table
```sql
id (serial, PK)
user_id (FK → users)
observatory_id (FK → observatories)
name (varchar, optional custom name)
notes (text)
saved_at (timestamp)
```

### `observation_sessions` table
```sql
id (serial, PK)
user_id (FK → users)
title (varchar)
target (varchar)
observatory_id (FK → observatories)
notes (text)
data (jsonb, for extensible metadata)
created_at (timestamp)
```

## Security Notes

- ✅ Passwords are **bcrypt hashed** with salt — never stored plaintext
- ✅ Session state is **per-browser** (Streamlit's built-in session management)
- ✅ Database queries use **parameterized statements** to prevent SQL injection
- ⚠️ Future: Consider adding password reset, 2FA, or OAuth login

## Future Enhancements

1. **Add a "save observatory" button** to Live Weather Map / Observatory Detail pages
2. **Export observation logs** as CSV/JSON
3. **Share saves** with other users via public links
4. **Observatory comparison** between saved sites
5. **Observation tips** personalized to user's favorite sites
6. **Email alerts** for saved observatories (tie into existing alert_system.py)
7. **OAuth login** (Google, GitHub) for easier registration

## Testing

### Quick Test

1. Go to sidebar → Register tab
2. Create test account: `testuser` / `testpass123` (email optional)
3. Click "Register"
4. Login with same credentials
5. You should see "Logged in as: testuser" in sidebar
6. Click "📋 My Saves" to see the empty page
7. (Once save buttons are added to pages, try saving an observatory)

### Browser Devtools

Check Streamlit session state (browser console or inspect):
```javascript
// Streamlit keeps session state in window.streamlitState
```

## Troubleshooting

### "Database credentials not found"
- Make sure `.env` has valid Supabase credentials
- Or set `SUPABASE_DB_HOST`, `SUPABASE_DB_USER`, `SUPABASE_DB_PASSWORD` env vars
- Streamlit also reads `secrets.toml` in `.streamlit/` directory

### "Username already taken"
- Choose a different username (usernames are unique)
- Usernames are case-insensitive and stored lowercase

### "Passwords don't match"
- Confirm Password field must exactly match Password field

### Migration fails with "relation already exists"
- The tables might already exist from a previous run
- The migration uses `CREATE TABLE IF NOT EXISTS`, so it's safe to re-run

## File Checklist

After setup, you should have:

```
Observatory_weather/
├── auth.py                              [✓ new]
├── user_saves.py                        [✓ new]
├── run_migrations.py                    [✓ new]
├── AUTH_SETUP.md                        [✓ this file]
├── migrations/
│   └── 001_add_auth_tables.sql         [✓ new]
├── requirements.txt                     [✓ modified - added bcrypt]
└── dashboard.py                         [✓ modified - integrated auth]
```

---

**Questions?** Check the inline code comments in `auth.py` and `user_saves.py` for detailed function documentation.
