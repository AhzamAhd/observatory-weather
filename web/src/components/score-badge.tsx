import { cn } from "@/lib/utils";

// Condition band from the observing-quality score, matching GOWC's bands.
function band(score: number): { label: string; cls: string } {
  if (score >= 80)
    return { label: "Excellent", cls: "bg-emerald-500/15 text-emerald-500 ring-emerald-500/30" };
  if (score >= 60)
    return { label: "Good", cls: "bg-sky-500/15 text-sky-400 ring-sky-500/30" };
  if (score >= 40)
    return { label: "Marginal", cls: "bg-amber-500/15 text-amber-500 ring-amber-500/30" };
  return { label: "Poor", cls: "bg-rose-500/15 text-rose-500 ring-rose-500/30" };
}

export function ScoreBadge({ score }: { score: number }) {
  const b = band(score);
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset tabular-nums",
        b.cls
      )}
    >
      <span className="font-semibold">{score.toFixed(0)}</span>
      <span className="opacity-80">{b.label}</span>
    </span>
  );
}
