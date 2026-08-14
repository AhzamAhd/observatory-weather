"use client";

import { useEffect, useMemo, useState } from "react";
import { fetchObservatories, type Observatory } from "@/lib/api";
import { SiteHeader } from "@/components/site-header";
import { ScoreBadge } from "@/components/score-badge";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const MAX = 3;

export default function ComparePage() {
  const [all, setAll] = useState<Observatory[]>([]);
  const [filter, setFilter] = useState("");
  const [picked, setPicked] = useState<Observatory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchObservatories({ limit: 2000 })
      .then((r) => setAll(r.observatories))
      .catch((e) => setError(String((e as Error).message)))
      .finally(() => setLoading(false));
  }, []);

  const results = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return [];
    return all
      .filter(
        (o) =>
          !picked.some((p) => p.id === o.id) &&
          (o.observatory.toLowerCase().includes(q) ||
            (o.country ?? "").toLowerCase().includes(q))
      )
      .slice(0, 8);
  }, [all, filter, picked]);

  function add(o: Observatory) {
    if (picked.length < MAX) {
      setPicked([...picked, o]);
      setFilter("");
    }
  }
  function remove(id: number) {
    setPicked(picked.filter((p) => p.id !== id));
  }

  const rows: { label: string; get: (o: Observatory) => string }[] = [
    { label: "Country", get: (o) => o.country ?? "—" },
    {
      label: "Cloud cover",
      get: (o) => (o.cloud_cover_pct != null ? `${o.cloud_cover_pct}%` : "—"),
    },
    {
      label: "Humidity",
      get: (o) => (o.humidity_pct != null ? `${o.humidity_pct}%` : "—"),
    },
    {
      label: "Wind",
      get: (o) => (o.wind_speed_ms != null ? `${o.wind_speed_ms} m/s` : "—"),
    },
    {
      label: "Temperature",
      get: (o) => (o.temperature_c != null ? `${o.temperature_c}°C` : "—"),
    },
    {
      label: "Altitude",
      get: (o) => (o.altitude_m != null ? `${o.altitude_m} m` : "—"),
    },
  ];

  return (
    <div className="min-h-screen bg-background text-foreground">
      <SiteHeader />
      <main className="mx-auto max-w-5xl px-6 py-8">
        <div className="mb-6">
          <h2 className="text-2xl font-semibold tracking-tight">
            Site Comparison
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Compare current conditions at up to {MAX} observatories side by side.
          </p>
        </div>

        {error && (
          <Card className="mb-6 border-destructive/30 bg-destructive/5">
            <CardContent className="pt-6 text-sm text-destructive">
              Couldn&apos;t reach the GOWC API ({error}).
            </CardContent>
          </Card>
        )}

        {/* Picker */}
        <Card className="mb-6">
          <CardContent className="pt-6">
            <Input
              placeholder={
                picked.length >= MAX
                  ? `Remove one to add another (max ${MAX})`
                  : "Search an observatory to add…"
              }
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              disabled={loading || picked.length >= MAX}
            />
            {results.length > 0 && (
              <div className="mt-2 space-y-0.5">
                {results.map((o) => (
                  <button
                    key={o.id}
                    onClick={() => add(o)}
                    className="flex w-full items-center justify-between rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent"
                  >
                    <span>{o.observatory.replace(/^\d+\s+/, "")}</span>
                    <span className="text-xs text-muted-foreground">
                      {o.country ?? "—"}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Comparison */}
        {picked.length === 0 ? (
          <p className="py-12 text-center text-sm text-muted-foreground">
            Add observatories above to compare them.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <div
              className="grid gap-4"
              style={{
                gridTemplateColumns: `140px repeat(${picked.length}, minmax(0, 1fr))`,
              }}
            >
              {/* header row */}
              <div />
              {picked.map((o) => (
                <Card key={o.id}>
                  <CardHeader className="pb-2">
                    <div className="flex items-start justify-between gap-2">
                      <CardTitle className="text-sm leading-snug">
                        {o.observatory.replace(/^\d+\s+/, "")}
                      </CardTitle>
                      <button
                        onClick={() => remove(o.id)}
                        className="text-xs text-muted-foreground hover:text-destructive"
                      >
                        ✕
                      </button>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <ScoreBadge score={o.observation_score} />
                  </CardContent>
                </Card>
              ))}

              {/* metric rows */}
              {rows.map((row) => (
                <div key={row.label} className="contents">
                  <div className="flex items-center text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    {row.label}
                  </div>
                  {picked.map((o) => (
                    <div
                      key={o.id}
                      className="flex items-center rounded-lg border border-border/60 px-3 py-2 text-sm tabular-nums"
                    >
                      {row.get(o)}
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
