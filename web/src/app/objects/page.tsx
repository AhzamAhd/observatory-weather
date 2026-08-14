"use client";

import { useEffect, useMemo, useState } from "react";
import {
  fetchObjectCatalog,
  fetchObjectVisibility,
  type CatalogObject,
  type VisibilitySite,
} from "@/lib/api";
import { SiteHeader } from "@/components/site-header";
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

export default function ObjectsPage() {
  const [catalog, setCatalog] = useState<CatalogObject[]>([]);
  const [filter, setFilter] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const [sites, setSites] = useState<VisibilitySite[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchObjectCatalog()
      .then((r) => setCatalog(r.objects))
      .catch((e) => setError(String((e as Error).message)));
  }, []);

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    const list = q
      ? catalog.filter(
          (o) =>
            o.name.toLowerCase().includes(q) || o.type.toLowerCase().includes(q)
        )
      : catalog;
    return list.slice(0, 60);
  }, [catalog, filter]);

  async function choose(name: string) {
    setSelected(name);
    setLoading(true);
    setError(null);
    setMessage(null);
    setSites([]);
    try {
      const r = await fetchObjectVisibility(name);
      setSites(r.sites);
      setMessage(r.message ?? null);
    } catch (e) {
      setError(String((e as Error).message));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <SiteHeader />
      <main className="mx-auto max-w-6xl px-6 py-8">
        <div className="mb-6">
          <h2 className="text-2xl font-semibold tracking-tight">
            Object Visibility
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Pick a deep-sky object, planet or star and see which observatories
            can see it right now — with real altitude and airmass.
          </p>
        </div>

        {error && (
          <Card className="mb-6 border-destructive/30 bg-destructive/5">
            <CardContent className="pt-6 text-sm text-destructive">
              Couldn&apos;t reach the GOWC API ({error}).
            </CardContent>
          </Card>
        )}

        <div className="grid gap-6 md:grid-cols-[300px_1fr]">
          {/* Object picker */}
          <Card className="h-fit">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">
                Objects{" "}
                <span className="font-normal text-muted-foreground">
                  ({catalog.length})
                </span>
              </CardTitle>
              <Input
                placeholder="Search e.g. Andromeda, M42, Jupiter…"
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                className="mt-2"
              />
            </CardHeader>
            <CardContent className="max-h-[520px] space-y-0.5 overflow-y-auto">
              {filtered.map((o) => (
                <button
                  key={o.name}
                  onClick={() => choose(o.name)}
                  className={`flex w-full items-center justify-between rounded-md px-2 py-1.5 text-left text-sm transition-colors ${
                    selected === o.name
                      ? "bg-primary/10 font-medium text-primary"
                      : "hover:bg-accent"
                  }`}
                >
                  <span className="truncate">{o.name}</span>
                  <span className="ml-2 shrink-0 text-xs text-muted-foreground">
                    {o.type}
                  </span>
                </button>
              ))}
              {filtered.length === 0 && (
                <p className="py-4 text-center text-sm text-muted-foreground">
                  No objects match.
                </p>
              )}
            </CardContent>
          </Card>

          {/* Visibility results */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                {selected ?? "Select an object"}
                {sites.length > 0 && (
                  <span className="font-normal text-muted-foreground">
                    {" "}
                    · {sites.length} sites can see it now
                  </span>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {!selected ? (
                <p className="py-12 text-center text-sm text-muted-foreground">
                  Choose an object from the list to see where it&apos;s
                  observable.
                </p>
              ) : loading ? (
                <p className="py-12 text-center text-sm text-muted-foreground">
                  Computing visibility…
                </p>
              ) : message ? (
                <p className="py-12 text-center text-sm text-muted-foreground">
                  {message}
                </p>
              ) : sites.length === 0 ? (
                <p className="py-12 text-center text-sm text-muted-foreground">
                  Not currently visible from any tracked site.
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Observatory</TableHead>
                        <TableHead>Country</TableHead>
                        <TableHead className="text-right">Altitude</TableHead>
                        <TableHead className="text-right">Airmass</TableHead>
                        <TableHead className="text-right">Quality</TableHead>
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
                          <TableCell className="text-right tabular-nums">
                            {s.altitude_deg != null ? `${s.altitude_deg}°` : "—"}
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {s.airmass != null ? s.airmass.toFixed(2) : "—"}
                          </TableCell>
                          <TableCell className="text-right text-muted-foreground">
                            {s.visibility_quality ?? "—"}
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
