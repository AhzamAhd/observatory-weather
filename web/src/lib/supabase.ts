// Supabase browser client for authentication.
// These two values are PUBLIC (safe in the browser) — the anon key is
// protected by Row-Level Security on the database. Set them in .env.local
// (local) and Vercel env vars (production).
import { createBrowserClient } from "@supabase/ssr";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

// Whether auth is configured. If not, the UI hides login rather than crashing.
export const authConfigured = Boolean(url && anonKey);

export function createClient() {
  if (!authConfigured) {
    throw new Error("Supabase auth is not configured (missing env vars).");
  }
  return createBrowserClient(url!, anonKey!);
}
