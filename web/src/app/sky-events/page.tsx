"use client";

import { useEffect, useState } from "react";
import {
  fetchMeteorShowers,
  fetchEclipses,
  type MeteorShower,
  type EclipseEvent,
} from "@/lib/api";
import { SiteHeader } from "@/components/site-header";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

function ShowerCard({ s, active }: { s: MeteorShower; active: boolean }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="text-base">{s.name}</CardTitle>
          {active && (
            <Badge className="bg-emerald-500/15 text-emerald-500 ring-1 ring-inset ring-emerald-500/30">
              Active now
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        <div className="flex flex-wrap gap-x-6 gap-y-1 text-muted-foreground">
          {s.peak_date && (
            <span>
              Peak: <span className="text-foreground">{s.peak_date}</span>
            </span>
          )}
          {s.zhr != null && (
            <span>
              ZHR: <span className="text-foreground tabular-nums">{s.zhr}</span>
            </span>
          )}
          {s.speed_km_s != null && (
            <span>
              Speed:{" "}
              <span className="text-foreground tabular-nums">
                {s.speed_km_s} km/s
              </span>
            </span>
          )}
        </div>
        {s.active_start && s.active_end && (
          <div className="text-xs text-muted-foreground">
            Active {s.active_start} – {s.active_end}
          </div>
        )}
        {s.description && (
          <p className="text-xs text-muted-foreground">{s.description}</p>
        )}
      </CardContent>
    </Card>
  );
}

export default function SkyEventsPage() {
  const [active, setActive] = useState<MeteorShower[]>([]);
  const [upcoming, setUpcoming] = useState<MeteorShower[]>([]);
  const [eclipses, setEclipses] = useState<EclipseEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([fetchMeteorShowers(), fetchEclipses()])
      .then(([ms, ec]) => {
        setActive(ms.active);
        setUpcoming(ms.upcoming);
        setEclipses(ec.events);
      })
      .catch((e) => setError(String((e as Error).message)))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <SiteHeader />
      <main className="mx-auto max-w-5xl px-6 py-8">
        <div className="mb-6">
          <h2 className="text-2xl font-semibold tracking-tight">Sky Events</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Meteor showers and upcoming eclipses.
          </p>
        </div>

        {error && (
          <Card className="mb-6 border-destructive/30 bg-destructive/5">
            <CardContent className="pt-6 text-sm text-destructive">
              Couldn&apos;t reach the GOWC API ({error}).
            </CardContent>
          </Card>
        )}

        {loading ? (
          <p className="py-16 text-center text-sm text-muted-foreground">
            Loading sky events…
          </p>
        ) : (
          <div className="space-y-8">
            {/* Meteor showers */}
            <section>
              <h3 className="mb-3 text-lg font-semibold">Meteor showers</h3>
              {active.length === 0 && upcoming.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No active or upcoming showers.
                </p>
              ) : (
                <div className="grid gap-4 sm:grid-cols-2">
                  {active.map((s) => (
                    <ShowerCard key={s.name} s={s} active />
                  ))}
                  {upcoming.map((s) => (
                    <ShowerCard key={s.name} s={s} active={false} />
                  ))}
                </div>
              )}
            </section>

            {/* Eclipses */}
            <section>
              <h3 className="mb-3 text-lg font-semibold">Upcoming eclipses</h3>
              {eclipses.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No upcoming eclipses.
                </p>
              ) : (
                <Card>
                  <CardContent className="divide-y divide-border/60 p-0">
                    {eclipses.map((e, i) => (
                      <div
                        key={`${e.date}-${i}`}
                        className="flex items-center justify-between gap-4 px-6 py-4"
                      >
                        <div>
                          <div className="font-medium">{e.type}</div>
                          <div className="text-sm text-muted-foreground">
                            {e.date}
                            {e.max_eclipse && ` · max ${e.max_eclipse} UTC`}
                          </div>
                        </div>
                        {e.magnitude != null && (
                          <div className="text-right text-sm text-muted-foreground">
                            <div className="text-xs uppercase tracking-wide">
                              Magnitude
                            </div>
                            <div className="font-medium tabular-nums text-foreground">
                              {e.magnitude}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}
            </section>
          </div>
        )}
      </main>
    </div>
  );
}
