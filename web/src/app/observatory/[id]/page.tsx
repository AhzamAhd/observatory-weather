"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import {
  fetchObservatory,
  type ObservatoryDetail,
} from "@/lib/api";
import { SiteHeader } from "@/components/site-header";
import { ScoreBadge } from "@/components/score-badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

function Field({
  label,
  value,
}: {
  label: string;
  value: string | number | null | undefined;
}) {
  return (
    <div className="rounded-lg border border-border/60 p-4">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div className="mt-1 text-lg font-semibold tabular-nums">
        {value ?? "—"}
      </div>
    </div>
  );
}

export default function ObservatoryDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [obs, setObs] = useState<ObservatoryDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchObservatory(Number(id))
      .then(setObs)
      .catch((e) => setError(String((e as Error).message)))
      .finally(() => setLoading(false));
  }, [id]);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <SiteHeader />
      <main className="mx-auto max-w-4xl px-6 py-8">
        <Link
          href="/"
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          ← Back to dashboard
        </Link>

        {loading && (
          <p className="py-16 text-center text-sm text-muted-foreground">
            Loading…
          </p>
        )}
        {error && (
          <Card className="mt-6 border-destructive/30 bg-destructive/5">
            <CardContent className="pt-6 text-sm text-destructive">
              Couldn&apos;t load this observatory ({error}).
            </CardContent>
          </Card>
        )}

        {obs && (
          <div className="mt-4 space-y-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h2 className="text-2xl font-semibold tracking-tight">
                  {obs.observatory.replace(/^\d+\s+/, "")}
                </h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  {obs.country ?? "—"}
                  {obs.mpc_code && ` · MPC ${obs.mpc_code}`}
                </p>
              </div>
              <ScoreBadge score={obs.observation_score} />
            </div>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Current conditions</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  <Field
                    label="Cloud cover"
                    value={obs.cloud_cover_pct != null ? `${obs.cloud_cover_pct}%` : null}
                  />
                  <Field
                    label="Humidity"
                    value={obs.humidity_pct != null ? `${obs.humidity_pct}%` : null}
                  />
                  <Field
                    label="Wind"
                    value={obs.wind_speed_ms != null ? `${obs.wind_speed_ms} m/s` : null}
                  />
                  <Field
                    label="Temperature"
                    value={obs.temperature_c != null ? `${obs.temperature_c}°C` : null}
                  />
                  <Field
                    label="Precipitation"
                    value={obs.precipitation_mm != null ? `${obs.precipitation_mm} mm` : null}
                  />
                  <Field
                    label="Pressure"
                    value={obs.surface_pressure != null ? `${obs.surface_pressure} hPa` : null}
                  />
                </div>
                {obs.fetch_datetime && (
                  <p className="mt-4 text-xs text-muted-foreground">
                    Updated {obs.fetch_datetime}
                  </p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Location</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  <Field label="Latitude" value={obs.latitude?.toFixed(4)} />
                  <Field label="Longitude" value={obs.longitude?.toFixed(4)} />
                  <Field
                    label="Altitude"
                    value={obs.altitude_m != null ? `${obs.altitude_m} m` : null}
                  />
                </div>
                <a
                  href={`https://www.google.com/maps/search/?api=1&query=${obs.latitude},${obs.longitude}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-4 inline-block text-sm text-primary hover:underline"
                >
                  View on map →
                </a>
              </CardContent>
            </Card>
          </div>
        )}
      </main>
    </div>
  );
}
