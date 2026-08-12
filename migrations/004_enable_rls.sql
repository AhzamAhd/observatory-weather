-- Enable Row Level Security on all app tables.
--
-- Supabase auto-exposes every public table through its PostgREST REST
-- API (anon/authenticated roles). Without RLS, anyone with the project
-- URL + anon key can read these tables directly over HTTP, bypassing the
-- app — a data-exposure hole flagged by the Supabase linter
-- (rls_disabled_in_public, sensitive_columns_exposed).
--
-- The app itself connects as the `postgres` role, which has BYPASSRLS,
-- so enabling RLS does NOT affect the app's own queries. With RLS on and
-- NO policies, the anon/authenticated API roles get zero rows — which is
-- exactly what we want: this data is only ever meant to be reached
-- through the app's backend, never the public API.
ALTER TABLE public.users                ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.saved_observatories  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.observation_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.saved_searches       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.page_visits          ENABLE ROW LEVEL SECURITY;
