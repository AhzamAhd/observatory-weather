"use client";

import { useEffect, useState } from "react";
import {
  fetchTelescopeEfficiency,
  type EfficiencySite,
} from "@/lib/api";
import { SiteHeader } from "@/components/site-header";
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

const TYPES = ["optical", "infrared", "radio"];

function GradeBadge({ grade }: { grade: string }) {
  const color = grade.startsWith("A")
    ? "bg-emerald-500/15 text-emerald-500 ring-emerald-500/30"
    : grade.startsWith("B")
    ? "bg-sky-500/15 text-sky-400 ring-sky-500/30"
    : grade.startsWith("C")
    ? "bg-amber-500/15 text-amber-500 ring-amber-500/30"
    : "bg-rose-500/15 text-rose-500 ring-rose-500/30";
  return (
    <span
      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ring-1 ring-inset ${color}`}
    >
      {grade}
    </span>
  );
}

export default function TelescopesPage() {
  const [type, setType] = useState("optical");
  const [sites, setSites] = useState<EfficiencySite[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchTelescopeEfficiency(type, 100)
      .then((r) => setSites(r.sites))
      .catch((e) => setError(String((e as Error).message)))
      .finally(() => setLoading(false));
  }, [type]);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <SiteHeader />
      <main className="mx-auto max-w-6xl px-6 py-8">
        <div className="mb-6">
          <h2 className="text-2xl font-semibold tracking-tight">
            Telescope Efficiency
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            How well each observatory can observe right now for a given
            telescope type — blending weather, dark hours, seeing and water
            vapour into an efficiency grade.
          </p>
        </div>

        <div className="mb-4 inline-flex rounded-lg border border-border p-1">
          {TYPES.map((t) => (
            <button
              key={t}
              onClick={() => setType(t)}
              className={`rounded-md px-3 py-1.5 text-sm capitalize transition-colors ${
                type === t
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-base capitalize">
              {type} telescopes{" "}
              {sites.length > 0 && (
                <span className="font-normal text-muted-foreground">
                  ({sites.length} sites, best first)
                </span>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <p className="py-12 text-center text-sm text-muted-foreground">
                Computing efficiency…
              </p>
            ) : error ? (
              <p className="py-12 text-center text-sm text-destructive">
                Couldn&apos;t reach the GOWC API ({error}).
              </p>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Observatory</TableHead>
                      <TableHead>Country</TableHead>
                      <TableHead className="text-right">Seeing</TableHead>
                      <TableHead className="text-right">Usable hrs</TableHead>
                      <TableHead className="text-right">Efficiency</TableHead>
                      <TableHead className="text-right">Grade</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {sites.map((s, i) => (
                      <TableRow key={`${s.observatory}-${i}`}>
                        <TableCell className="font-medium">
                          {s.observatory.replace(/^\d+\s+/, "")}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {s.country ?? "—"}
                        </TableCell>
                        <TableCell className="text-right tabular-nums text-muted-foreground">
                          {s.seeing_arcsec != null ? `${s.seeing_arcsec}″` : "—"}
                        </TableCell>
                        <TableCell className="text-right tabular-nums text-muted-foreground">
                          {s.usable_hours != null ? `${s.usable_hours}h` : "—"}
                        </TableCell>
                        <TableCell className="text-right font-semibold tabular-nums">
                          {s.efficiency_score}
                        </TableCell>
                        <TableCell className="text-right">
                          <GradeBadge grade={s.grade} />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
