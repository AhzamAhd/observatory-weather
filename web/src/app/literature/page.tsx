"use client";

import { useState } from "react";
import { searchLiterature, type Paper } from "@/lib/api";
import { SiteHeader } from "@/components/site-header";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const SORTS = ["Relevance", "Most cited", "Newest first"];

function PaperRow({ p }: { p: Paper }) {
  const meta = [p.authors, p.year, p.pub].filter(Boolean).join(" · ");
  return (
    <div className="border-b border-border/60 py-4 last:border-0">
      {p.link ? (
        <a
          href={p.link}
          target="_blank"
          rel="noopener noreferrer"
          className="font-medium text-primary hover:underline"
        >
          {p.title}
          {p.link_type && (
            <span className="ml-2 text-xs font-normal text-muted-foreground">
              [{p.link_type}]
            </span>
          )}
        </a>
      ) : (
        <span className="font-medium">{p.title}</span>
      )}
      <div className="mt-1 text-sm text-muted-foreground">
        {meta}
        {p.citations > 0 && (
          <span className="ml-2">· {p.citations} citations</span>
        )}
      </div>
    </div>
  );
}

export default function LiteraturePage() {
  const [q, setQ] = useState("");
  const [sort, setSort] = useState("Relevance");
  const [papers, setPapers] = useState<Paper[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    const query = q.trim();
    if (!query) return;
    setLoading(true);
    setError(null);
    setPapers(null);
    try {
      const r = await searchLiterature({ q: query, sort, rows: 15 });
      setPapers(r.papers);
    } catch (e) {
      setError(String((e as Error).message));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <SiteHeader />
      <main className="mx-auto max-w-4xl px-6 py-8">
        <div className="mb-6">
          <h2 className="text-2xl font-semibold tracking-tight">
            Literature Search
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Search real astronomy papers via NASA ADS. Every result is a genuine
            record — titles, authors and links come straight from ADS, never
            AI-generated.
          </p>
        </div>

        <Card className="mb-6">
          <CardContent className="pt-6">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                run();
              }}
              className="flex flex-col gap-3 sm:flex-row"
            >
              <Input
                placeholder="e.g. X-ray binaries, neutron star mergers"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                className="sm:flex-1"
              />
              <select
                value={sort}
                onChange={(e) => setSort(e.target.value)}
                className="h-9 rounded-md border border-input bg-transparent px-3 text-sm"
              >
                {SORTS.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
              <Button type="submit" disabled={loading}>
                {loading ? "Searching…" : "Search"}
              </Button>
            </form>
          </CardContent>
        </Card>

        {error && (
          <Card className="mb-6 border-amber-500/30 bg-amber-500/5">
            <CardContent className="pt-6 text-sm text-amber-600 dark:text-amber-400">
              {error}
              <div className="mt-1 text-xs text-muted-foreground">
                Literature search needs the ADS_API_TOKEN set on the backend.
              </div>
            </CardContent>
          </Card>
        )}

        {papers && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                {papers.length > 0
                  ? `${papers.length} papers from NASA ADS`
                  : "No papers found"}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {papers.length === 0 ? (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  Try broader or different keywords.
                </p>
              ) : (
                <>
                  {papers.map((p, i) => (
                    <PaperRow key={p.bibcode ?? i} p={p} />
                  ))}
                  <p className="mt-4 text-xs text-muted-foreground">
                    Links prefer DOI, then arXiv, then the ADS abstract page.
                    Data: NASA Astrophysics Data System.
                  </p>
                </>
              )}
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
}
