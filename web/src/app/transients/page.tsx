"use client";

import { useEffect, useMemo, useState } from "react";
import {
  fetchTransientClasses,
  fetchTransientTargets,
  type TransientClass,
  type TransientTarget,
} from "@/lib/api";
import { SiteHeader } from "@/components/site-header";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export default function TransientsPage() {
  const [groups, setGroups] = useState<Record<string, TransientClass[]>>({});
  const [selected, setSelected] = useState<string | null>(null);
  const [targets, setTargets] = useState<TransientTarget[]>([]);
  const [loadingClasses, setLoadingClasses] = useState(true);
  const [loadingTargets, setLoadingTargets] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchTransientClasses()
      .then((r) => {
        setGroups(r.groups);
        // default: first live class
        const firstLive = Object.values(r.groups)
          .flat()
          .find((c) => c.live);
        if (firstLive) setSelected(firstLive.name);
      })
      .catch((e) => setError(String((e as Error).message)))
      .finally(() => setLoadingClasses(false));
  }, []);

  useEffect(() => {
    if (!selected) return;
    setLoadingTargets(true);
    fetchTransientTargets(selected)
      .then((r) => setTargets(r.targets))
      .catch(() => setTargets([]))
      .finally(() => setLoadingTargets(false));
  }, [selected]);

  const alerts = useMemo(
    () => targets.filter((t) => t.alert_level),
    [targets]
  );

  return (
    <div className="min-h-screen bg-background text-foreground">
      <SiteHeader />
      <main className="mx-auto max-w-6xl px-6 py-8">
        <div className="mb-6">
          <h2 className="text-2xl font-semibold tracking-tight">
            Transient Follow-Up
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Active transient targets by class — curated catalogues plus live
            outburst alerts from the MAXI/RIKEN monitor.
          </p>
        </div>

        {error && (
          <Card className="mb-6 border-destructive/30 bg-destructive/5">
            <CardContent className="pt-6 text-sm text-destructive">
              Couldn&apos;t reach the GOWC API ({error}). Is the backend running?
            </CardContent>
          </Card>
        )}

        <div className="grid gap-6 md:grid-cols-[260px_1fr]">
          {/* Class picker */}
          <Card className="h-fit">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Target classes</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {loadingClasses && (
                <p className="text-sm text-muted-foreground">Loading…</p>
              )}
              {Object.entries(groups).map(([group, classes]) => (
                <div key={group}>
                  <div className="mb-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    {group}
                  </div>
                  <div className="space-y-0.5">
                    {classes.map((c) => (
                      <button
                        key={c.name}
                        disabled={!c.live}
                        onClick={() => c.live && setSelected(c.name)}
                        className={`flex w-full items-center justify-between rounded-md px-2 py-1.5 text-left text-sm transition-colors ${
                          selected === c.name
                            ? "bg-primary/10 font-medium text-primary"
                            : c.live
                            ? "hover:bg-accent"
                            : "cursor-not-allowed text-muted-foreground/50"
                        }`}
                      >
                        <span className="truncate">{c.name}</span>
                        {c.live ? (
                          <span className="ml-1 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500" />
                        ) : (
                          <span className="ml-1 shrink-0 text-[10px] uppercase">
                            soon
                          </span>
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Targets */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                {selected ?? "Select a class"}{" "}
                {targets.length > 0 && (
                  <span className="font-normal text-muted-foreground">
                    ({targets.length} targets
                    {alerts.length > 0 && `, ${alerts.length} in outburst`})
                  </span>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {loadingTargets ? (
                <p className="py-12 text-center text-sm text-muted-foreground">
                  Loading targets…
                </p>
              ) : targets.length === 0 ? (
                <p className="py-12 text-center text-sm text-muted-foreground">
                  No targets for this class.
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Target</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead className="text-right">RA</TableHead>
                        <TableHead className="text-right">Dec</TableHead>
                        <TableHead className="text-right">Status</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {targets.map((t, i) => (
                        <TableRow key={`${t.name}-${i}`}>
                          <TableCell>
                            <div className="font-medium">{t.name}</div>
                            {t.comment && (
                              <div className="text-xs text-muted-foreground">
                                {t.comment}
                              </div>
                            )}
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {t.kind ?? "—"}
                          </TableCell>
                          <TableCell className="text-right tabular-nums text-muted-foreground">
                            {t.ra_deg != null ? t.ra_deg.toFixed(3) : "—"}
                          </TableCell>
                          <TableCell className="text-right tabular-nums text-muted-foreground">
                            {t.dec_deg != null ? t.dec_deg.toFixed(3) : "—"}
                          </TableCell>
                          <TableCell className="text-right">
                            {t.alert_level ? (
                              <Badge variant="destructive">
                                {t.alert_level}
                              </Badge>
                            ) : t.catalog ? (
                              <span className="text-xs text-muted-foreground">
                                Catalogue
                              </span>
                            ) : (
                              <span className="text-xs text-muted-foreground">
                                Alert
                              </span>
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
