// Client for the GOWC FastAPI backend (the api/ folder).
// Every value here comes from the real API — no mock data.

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export interface Observatory {
  id: number;
  observatory: string;
  country: string | null;
  latitude: number;
  longitude: number;
  altitude_m: number | null;
  observation_score: number;
  cloud_cover_pct: number | null;
  humidity_pct: number | null;
  wind_speed_ms: number | null;
  temperature_c: number | null;
  fetch_datetime: string | null;
}

export interface ObservatoriesResponse {
  count: number;
  observatories: Observatory[];
}

export async function fetchObservatories(
  params: { limit?: number; minScore?: number } = {}
): Promise<ObservatoriesResponse> {
  const qs = new URLSearchParams();
  if (params.limit) qs.set("limit", String(params.limit));
  if (params.minScore != null) qs.set("min_score", String(params.minScore));

  const res = await fetch(`${API_BASE}/observatories?${qs.toString()}`, {
    // Always fetch fresh conditions.
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}`);
  }
  return res.json();
}

// ── Observe / rank ────────────────────────────────────────────────

export interface RankedSite {
  site: string;
  country: string;
  observable: boolean;
  min_airmass: number | null;
  best_time_utc: string | null;
  window_start_utc: string | null;
  window_end_utc: string | null;
  window_hours: number;
  weather_score: number;
  weather_known: boolean;
  score: number;
}

export interface RankResponse {
  target: { ra_deg?: number; dec_deg?: number; name?: string };
  date_utc: string;
  ranked: RankedSite[];
  best_site: RankedSite | null;
}

// The API returns a 404 with { detail: { message, candidates } } when a target
// can't be resolved — surface that as a typed error the UI can render.
export class TargetNotFound extends Error {
  candidates: string[];
  constructor(message: string, candidates: string[]) {
    super(message);
    this.name = "TargetNotFound";
    this.candidates = candidates;
  }
}

export async function rankSites(target: string): Promise<RankResponse> {
  const qs = new URLSearchParams({ target });
  const res = await fetch(`${API_BASE}/observe/rank?${qs.toString()}`, {
    cache: "no-store",
  });
  if (res.status === 404) {
    const body = await res.json().catch(() => ({}));
    const detail = body?.detail ?? {};
    throw new TargetNotFound(
      detail.message ?? `Couldn't resolve "${target}".`,
      detail.candidates ?? []
    );
  }
  if (!res.ok) {
    throw new Error(`API error ${res.status}`);
  }
  return res.json();
}
