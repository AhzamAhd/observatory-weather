"use client";

import { useState } from "react";
import Link from "next/link";
import {
  rankSites,
  TargetNotFound,
  type RankResponse,
  type RankedSite,
} from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
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

const EXAMPLES = ["Sco X-1", "Cyg X-1", "the Moon", "Jupiter", "GX 339-4"];

function BestSiteCard({ site, date }: { site: RankedSite; date: string }) {
  return (
    <Card className="border-primary/30 bg-primary/5">
      <CardHeader className="pb-2">
        <CardTitle className="text-xs font-medium uppercase tracking-wide text-primary">
          Best site tonight
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-1">
        <div className="text-2xl font-semibold">{site.site}</div>
        <div className="text-sm text-muted-foreground">{site.country}</div>
        <div className="mt-3 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
          <Metric label="Score" value={site.score.toFixed(1)} />
          <Metric
            label="Airmass"
            value={site.min_airmass != null ? site.min_airmass.toFixed(2) : "—"}
          />
          <Metric label="Best time" value={site.best_time_utc ?? "—"} />
          <Metric label="Window" value={`${site.window_hours} h`} />
        </div>
        <div className="pt-2 text-xs text-muted-foreground">For {date} · times UTC</div>
      </CardContent>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div className="font-medium tabular-nums">{value}</div>
    </div>
  );
}

export default function AssistantPage() {
  const [target, setTarget] = useState("");
  const [result, setResult] = useState<RankResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<string[]>([]);

  async function run(q: string) {
    const query = q.trim();
    if (!query) return;
    setLoading(true);
    setError(null);
    setCandidates([]);
    setResult(null);
    try {
      const r = await rankSites(query);
      setResult(r);
    } catch (e) {
      if (e instanceof TargetNotFound) {
        setError(e.message);
        setCandidates(e.candidates);
      } else {
        setError(
          `Couldn't reach the GOWC API. Is the backend running? (${
            (e as Error).message
          })`
        );
      }
    } finally {
      setLoading(false);
    }
  }

  const observable = result?.ranked.filter((s) => s.observable) ?? [];

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b border-border/60 bg-card/40 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
          <Link href="/" className="flex items-center gap-3">
            <span className="text-2xl">🔭</span>
            <div>
              <h1 className="text-lg font-semibold leading-tight">GOWC</h1>
              <p className="text-xs text-muted-foreground">
                Global Observatory Weather Tracker
              </p>
            </div>
          </Link>
          <Link
            href="/"
            className="text-sm text-muted-foreground hover:text-foreground"
          >
            ← Dashboard
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8">
        <div className="mb-6">
          <h2 className="text-2xl font-semibold tracking-tight">
            Observing Assistant
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Enter a target — an X-ray binary, the Moon, a planet — and see which
            observatories can catch it tonight, ranked by a real observability
            engine. Every number is computed, never invented.
          </p>
        </div>

        <Card className="mb-6">
          <CardContent className="pt-6">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                run(target);
              }}
              className="flex flex-col gap-3 sm:flex-row"
            >
              <Input
                placeholder="e.g. Sco X-1, the Moon, Jupiter…"
                value={target}
                onChange={(e) => setTarget(e.target.value)}
                className="sm:flex-1"
              />
              <Button type="submit" disabled={loading}>
                {loading ? "Computing…" : "Rank sites"}
              </Button>
            </form>
            <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <span>Try:</span>
              {EXAMPLES.map((ex) => (
                <button
                  key={ex}
                  onClick={() => {
                    setTarget(ex);
                    run(ex);
                  }}
                  className="rounded-full border border-border px-2.5 py-0.5 hover:bg-accent hover:text-accent-foreground"
                >
                  {ex}
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        {error && (
          <Card className="mb-6 border-amber-500/30 bg-amber-500/5">
            <CardContent className="pt-6 text-sm">
              <p className="text-amber-600 dark:text-amber-400">{error}</p>
              {candidates.length > 0 && (
                <div className="mt-3">
                  <p className="text-muted-foreground">Did you mean:</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {candidates.map((c) => (
                      <button
                        key={c}
                        onClick={() => {
                          setTarget(c);
                          run(c);
                        }}
                        className="rounded-full border border-border px-2.5 py-0.5 text-xs hover:bg-accent hover:text-accent-foreground"
                      >
                        {c}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {result && (
          <div className="space-y-6">
            {result.best_site ? (
              <BestSiteCard site={result.best_site} date={result.date_utc} />
            ) : (
              <Card className="border-muted">
                <CardContent className="pt-6 text-sm text-muted-foreground">
                  This target isn&apos;t observable from any of the tracked
                  sites in astronomical darkness on {result.date_utc} — it may be
                  a daytime object on this date.
                </CardContent>
              </Card>
            )}

            {observable.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">
                    All observable sites{" "}
                    <span className="font-normal text-muted-foreground">
                      ({observable.length})
                    </span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Site</TableHead>
                          <TableHead>Country</TableHead>
                          <TableHead className="text-right">Airmass</TableHead>
                          <TableHead className="text-right">Best (UTC)</TableHead>
                          <TableHead className="text-right">Window</TableHead>
                          <TableHead className="text-right">Weather</TableHead>
                          <TableHead className="text-right">Score</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {observable.map((s) => (
                          <TableRow key={s.site}>
                            <TableCell className="font-medium">{s.site}</TableCell>
                            <TableCell className="text-muted-foreground">
                              {s.country}
                            </TableCell>
                            <TableCell className="text-right tabular-nums">
                              {s.min_airmass != null ? s.min_airmass.toFixed(2) : "—"}
                            </TableCell>
                            <TableCell className="text-right tabular-nums text-muted-foreground">
                              {s.best_time_utc?.split(" ")[1] ?? "—"}
                            </TableCell>
                            <TableCell className="text-right tabular-nums text-muted-foreground">
                              {s.window_hours} h
                            </TableCell>
                            <TableCell className="text-right tabular-nums text-muted-foreground">
                              {s.weather_score.toFixed(0)}
                              {!s.weather_known && (
                                <span className="ml-1 text-xs">*</span>
                              )}
                            </TableCell>
                            <TableCell className="text-right font-semibold tabular-nums">
                              {s.score.toFixed(1)}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                    <p className="mt-3 text-xs text-muted-foreground">
                      Ranked by a blend of airmass and live GOWC conditions.
                      * = no nearby weather station; a neutral score was used.
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
