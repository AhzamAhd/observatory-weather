"use client";

import { useEffect, useMemo, useState } from "react";
import {
  fetchObservatories,
  type Observatory,
} from "@/lib/api";
import { SiteHeader } from "@/components/site-header";
import { ScoreBadge } from "@/components/score-badge";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <Card className="gap-1 py-4">
      <CardHeader className="pb-0">
        <CardTitle className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {label}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-semibold tabular-nums">{value}</div>
        {hint && <div className="text-xs text-muted-foreground">{hint}</div>}
      </CardContent>
    </Card>
  );
}

export default function Dashboard() {
  const [data, setData] = useState<Observatory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchObservatories({ limit: 500 })
      .then((r) => {
        if (!cancelled) {
          setData(r.observatories);
          setError(null);
        }
      })
      .catch((e) => {
        if (!cancelled) setError(String(e.message ?? e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return data;
    return data.filter(
      (o) =>
        o.observatory.toLowerCase().includes(q) ||
        (o.country ?? "").toLowerCase().includes(q)
    );
  }, [data, query]);

  const stats = useMemo(() => {
    if (data.length === 0) return null;
    const best = data[0];
    const excellent = data.filter((o) => o.observation_score >= 80).length;
    const avg =
      data.reduce((s, o) => s + o.observation_score, 0) / data.length;
    return { best, excellent, avg, total: data.length };
  }, [data]);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <SiteHeader />

      <main className="mx-auto max-w-6xl px-6 py-8">
        <div className="mb-6">
          <h2 className="text-2xl font-semibold tracking-tight">
            Observatory Dashboard
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Real-time observing conditions across the world&apos;s
            observatories, ranked by observing-quality score.
          </p>
        </div>

        {/* KPI row */}
        {stats && (
          <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
            <Stat
              label="Best site now"
              value={stats.best.observatory.replace(/^\d+\s+/, "").slice(0, 18)}
              hint={`Score ${stats.best.observation_score.toFixed(0)}`}
            />
            <Stat label="Observatories" value={String(stats.total)} hint="monitored" />
            <Stat
              label="Excellent now"
              value={String(stats.excellent)}
              hint="score ≥ 80"
            />
            <Stat
              label="Average score"
              value={stats.avg.toFixed(0)}
              hint="across all sites"
            />
          </div>
        )}

        {/* Search + table */}
        <Card>
          <CardHeader className="gap-3">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <CardTitle className="text-base">
                Conditions{" "}
                <span className="font-normal text-muted-foreground">
                  ({filtered.length})
                </span>
              </CardTitle>
              <Input
                placeholder="Search observatory or country…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="sm:max-w-xs"
              />
            </div>
          </CardHeader>
          <CardContent>
            {loading && (
              <div className="py-16 text-center text-sm text-muted-foreground">
                Loading live conditions…
              </div>
            )}
            {error && (
              <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-6 text-center text-sm text-destructive">
                Couldn&apos;t reach the GOWC API ({error}).
                <div className="mt-1 text-xs text-muted-foreground">
                  Is the backend running? <code>cd api &amp;&amp; uvicorn main:app --port 8000</code>
                </div>
              </div>
            )}
            {!loading && !error && (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Observatory</TableHead>
                      <TableHead>Country</TableHead>
                      <TableHead className="text-right">Cloud</TableHead>
                      <TableHead className="text-right">Wind</TableHead>
                      <TableHead className="text-right">Temp</TableHead>
                      <TableHead className="text-right">Condition</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filtered.slice(0, 100).map((o) => (
                      <TableRow key={o.id}>
                        <TableCell className="font-medium">
                          {o.observatory.replace(/^\d+\s+/, "")}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {o.country ?? "—"}
                        </TableCell>
                        <TableCell className="text-right tabular-nums text-muted-foreground">
                          {o.cloud_cover_pct != null ? `${o.cloud_cover_pct}%` : "—"}
                        </TableCell>
                        <TableCell className="text-right tabular-nums text-muted-foreground">
                          {o.wind_speed_ms != null ? `${o.wind_speed_ms} m/s` : "—"}
                        </TableCell>
                        <TableCell className="text-right tabular-nums text-muted-foreground">
                          {o.temperature_c != null ? `${o.temperature_c}°C` : "—"}
                        </TableCell>
                        <TableCell className="text-right">
                          <ScoreBadge score={o.observation_score} />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                {filtered.length === 0 && (
                  <div className="py-12 text-center text-sm text-muted-foreground">
                    No observatories match &quot;{query}&quot;.
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        <p className="mt-6 text-center text-xs text-muted-foreground">
          Data from the GOWC API · Weather via Open-Meteo · Forecasts are
          planning estimates, not official observatory conditions.
        </p>
      </main>
    </div>
  );
}
