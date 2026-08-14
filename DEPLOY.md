# Deploying GOWC (new stack: FastAPI backend + Next.js frontend)

This deploys the **new** app. The Streamlit app is untouched and keeps running.

Two services:
- **Backend** (FastAPI, the `api/` folder) → **Render**
- **Frontend** (Next.js, the `web/` folder) → **Vercel**

Deploy the backend FIRST (the frontend needs its URL).

---

## Part 1 — Backend on Render

1. Render dashboard → **New +** → **Web Service** → connect this GitHub repo.
2. Settings:
   - **Root Directory:** `api`
   - **Runtime:** Python
   - **Build Command:** `pip install -r requirements.txt -r ../requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Instance type:** Free works (sleeps when idle → slow first request).
     Pick a paid tier (~$7/mo) for always-on.
3. **Environment variables** (Environment tab) — copy the same DB values your
   Streamlit service uses:
   - `SUPABASE_DB_HOST`
   - `SUPABASE_DB_USER`
   - `SUPABASE_DB_PASSWORD`
   - `SUPABASE_DB_PORT`
   - `ADS_API_TOKEN` (for Literature search)
   - `GOWC_CORS_ORIGINS` — leave unset for now; you'll set it to the Vercel URL
     in Part 3.
4. Create the service. When it's live, note its URL, e.g.
   `https://gowc-api.onrender.com`. Test it: open `<that URL>/health` — you
   should see `{"status":"ok",...}`, and `<that URL>/docs` for the API docs.

---

## Part 2 — Frontend on Vercel

1. vercel.com → **Add New** → **Project** → import this GitHub repo.
2. Settings:
   - **Root Directory:** `web`
   - Framework preset: **Next.js** (auto-detected).
3. **Environment Variables:**
   - `NEXT_PUBLIC_API_BASE` = your Render backend URL from Part 1
     (e.g. `https://gowc-api.onrender.com`) — **no trailing slash**.
4. Deploy. Vercel gives you a URL, e.g. `https://gowc.vercel.app`.

---

## Part 3 — Connect them (CORS)

The browser will block the frontend from calling the backend until the backend
allows the frontend's origin.

1. Back in **Render** → your API service → Environment → set:
   - `GOWC_CORS_ORIGINS` = your Vercel URL (e.g. `https://gowc.vercel.app`)
2. Save (Render redeploys). Now the frontend can reach the backend.

---

## Verify

Open your Vercel URL. The dashboard should load live observatory data. Click
through Observing Assistant, Transients, Literature. If the dashboard shows
"Couldn't reach the GOWC API":
- Check the Render service is awake (free tier sleeps — first hit wakes it,
  ~30s).
- Check `NEXT_PUBLIC_API_BASE` has no trailing slash and matches the Render URL.
- Check `GOWC_CORS_ORIGINS` on Render matches the Vercel URL exactly.

---

## Notes

- **Free-tier cold starts:** Render's free backend sleeps after ~15 min idle.
  The first request after that takes ~30s to wake. Upgrade to a paid instance
  for always-on.
- **Secrets:** never commit real tokens. They live only in the Render/Vercel
  dashboards.
- **The Streamlit app is unaffected** by any of this.
