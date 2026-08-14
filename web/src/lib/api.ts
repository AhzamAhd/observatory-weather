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
