"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { fetchObservatories, type Observatory } from "@/lib/api";
import { SiteHeader } from "@/components/site-header";
import { Card, CardContent } from "@/components/ui/card";

// Leaflet touches window, so load the map only on the client.
const ObservatoryMap = dynamic(
  () => import("@/components/observatory-map"),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-[70vh] items-center justify-center rounded-xl border border-border text-sm text-muted-foreground">
        Loading map…
      </div>
    ),
  }
);

const LEGEND = [
  { label: "Excellent (80+)", color: "#10b981" },
  { label: "Good (60–79)", color: "#38bdf8" },
  { label: "Marginal (40–59)", color: "#f59e0b" },
  { label: "Poor (<40)", color: "#f43f5e" },
];

export default function MapPage() {
  const [data, setData] = useState<Observatory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchObservatories({ limit: 2000 })
      .then((r) => setData(r.observatories))
      .catch((e) => setError(String((e as Error).message)))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <SiteHeader />
      <main className="mx-auto max-w-6xl px-6 py-8">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight">
              Live Weather Map
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Observing conditions at every tracked observatory, coloured by
              observing-quality score.
            </p>
          </div>
          <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
            {LEGEND.map((l) => (
              <span key={l.label} className="inline-flex items-center gap-1.5">
                <span
                  className="h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: l.color }}
                />
                {l.label}
              </span>
            ))}
          </div>
        </div>

        {error ? (
          <Card className="border-destructive/30 bg-destructive/5">
            <CardContent className="pt-6 text-sm text-destructive">
              Couldn&apos;t reach the GOWC API ({error}).
            </CardContent>
          </Card>
        ) : loading ? (
          <div className="flex h-[70vh] items-center justify-center rounded-xl border border-border text-sm text-muted-foreground">
            Loading observatories…
          </div>
        ) : (
          <>
            <ObservatoryMap data={data} />
            <p className="mt-3 text-center text-xs text-muted-foreground">
              {data.length} observatories · click a marker for details.
            </p>
          </>
        )}
      </main>
    </div>
  );
}
