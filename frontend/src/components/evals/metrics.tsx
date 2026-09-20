import { cn } from "@/lib/utils";
import { pct, scoreTone, type Tone } from "@/lib/format";

const toneText = {
  low: "text-low",
  medium: "text-medium",
  high: "text-high",
  none: "text-ink-subtle",
} as const;

const toneBar = {
  low: "bg-low",
  medium: "bg-medium",
  high: "bg-high",
  none: "bg-line-strong",
} as const;

export function Stat({
  label,
  value,
  caption,
  tone = "none",
}: {
  label: string;
  value: string;
  caption?: string;
  tone?: Tone;
}) {
  return (
    <div className="rounded-card border border-line bg-surface px-4 py-3">
      <div className="text-[11px] font-medium uppercase tracking-wide text-ink-subtle">
        {label}
      </div>
      <div
        className={cn(
          "mt-1 text-2xl font-semibold tabular-nums tracking-tight",
          toneText[tone],
        )}
      >
        {value}
      </div>
      {caption && <div className="mt-0.5 text-[12px] text-ink-muted">{caption}</div>}
    </div>
  );
}

/** A labelled proportion bar. Used for per-field accuracy and recall. */
export function Meter({
  label,
  value,
  detail,
}: {
  label: string;
  value: number | null;
  detail?: string;
}) {
  const tone = scoreTone(value);
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1 py-1.5">
      <div className="truncate text-[13px] text-ink">{label}</div>
      <div className="flex items-baseline gap-2 tabular-nums">
        <span className={cn("text-[13px] font-medium", toneText[tone])}>{pct(value)}</span>
        {detail && <span className="text-[12px] text-ink-subtle">{detail}</span>}
      </div>
      <div className="col-span-2 h-1.5 overflow-hidden rounded-full bg-raised">
        <div
          className={cn("h-full rounded-full transition-[width]", toneBar[tone])}
          style={{ width: `${Math.round((value ?? 0) * 100)}%` }}
        />
      </div>
    </div>
  );
}
