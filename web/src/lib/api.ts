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

// Full detail for one observatory (adds fields the list omits).
export interface ObservatoryDetail extends Observatory {
  mpc_code: string | null;
  precipitation_mm: number | null;
  surface_pressure: number | null;
  jet_stream_ms: number | null;
  condition: string;
}

export async function fetchObservatory(id: number): Promise<ObservatoryDetail> {
  const res = await fetch(`${API_BASE}/observatories/${id}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
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

// ── Transients ────────────────────────────────────────────────────

export interface TransientClass {
  name: string;
  live: boolean;
}
export interface TransientClassesResponse {
  groups: Record<string, TransientClass[]>;
}

export interface TransientTarget {
  name: string;
  alt_name?: string | null;
  ra_deg: number | null;
  dec_deg: number | null;
  kind?: string | null;
  catalog?: boolean;
  comment?: string | null;
  alert_level?: string | null;
  updated?: string | null;
}
export interface TransientTargetsResponse {
  target_class: string;
  targets: TransientTarget[];
}

export async function fetchTransientClasses(): Promise<TransientClassesResponse> {
  const res = await fetch(`${API_BASE}/transients/classes`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

export async function fetchTransientTargets(
  targetClass: string
): Promise<TransientTargetsResponse> {
  const qs = new URLSearchParams({ target_class: targetClass });
  const res = await fetch(`${API_BASE}/transients/targets?${qs.toString()}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

// ── Literature (NASA ADS) ─────────────────────────────────────────

export interface Paper {
  title: string;
  authors: string;
  year: string | null;
  pub: string | null;
  citations: number;
  link: string | null;
  link_type: string | null;
  bibcode: string | null;
}
export interface LiteratureResponse {
  query: string;
  count: number;
  papers: Paper[];
}

export async function searchLiterature(params: {
  q: string;
  sort?: string;
  rows?: number;
}): Promise<LiteratureResponse> {
  const qs = new URLSearchParams({ q: params.q });
  if (params.sort) qs.set("sort", params.sort);
  if (params.rows) qs.set("rows", String(params.rows));
  const res = await fetch(`${API_BASE}/literature/search?${qs.toString()}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail ?? `API error ${res.status}`);
  }
  return res.json();
}

// ── Object visibility ─────────────────────────────────────────────

export interface CatalogObject {
  name: string;
  type: string;
}
export interface CatalogResponse {
  count: number;
  objects: CatalogObject[];
}

export interface VisibilitySite {
  observatory: string;
  country: string | null;
  altitude_deg: number | null;
  direction?: string | null;
  visibility_quality?: string | null;
  airmass: number | null;
  hours_visible?: number | null;
  weather_score?: number | null;
  combined_score?: number | null;
}
export interface VisibilityResponse {
  object: string;
  count?: number;
  sites: VisibilitySite[];
  message?: string;
}

export async function fetchObjectCatalog(
  q?: string
): Promise<CatalogResponse> {
  const qs = new URLSearchParams();
  if (q) qs.set("q", q);
  qs.set("limit", "400");
  const res = await fetch(`${API_BASE}/objects/catalog?${qs.toString()}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

export async function fetchObjectVisibility(
  objectName: string
): Promise<VisibilityResponse> {
  const qs = new URLSearchParams({ object_name: objectName });
  const res = await fetch(`${API_BASE}/objects/visibility?${qs.toString()}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

// ── Sky events ────────────────────────────────────────────────────

export interface MeteorShower {
  name: string;
  peak_date?: string;
  active_start?: string;
  active_end?: string;
  zhr?: number;
  speed_km_s?: number;
  parent?: string;
  description?: string;
}
export interface MeteorShowersResponse {
  active: MeteorShower[];
  upcoming: MeteorShower[];
}

export interface EclipseEvent {
  date: string;
  type: string;
  subtype?: string;
  magnitude?: number;
  max_eclipse?: string | null;
  [k: string]: unknown;
}
export interface EclipsesResponse {
  count: number;
  events: EclipseEvent[];
}

export async function fetchMeteorShowers(): Promise<MeteorShowersResponse> {
  const res = await fetch(`${API_BASE}/sky-events/meteor-showers`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

export async function fetchEclipses(): Promise<EclipsesResponse> {
  const res = await fetch(`${API_BASE}/sky-events/eclipses`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}
