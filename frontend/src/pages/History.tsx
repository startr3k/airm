import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, History as HistoryIcon, Loader2 } from "lucide-react";
import { api, type HistoryRow, type Tier } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ResultsView } from "@/components/results/ResultsView";
import { aiTypeLabel, cn, oversightLabel, tierBorder, tierLabel } from "@/lib/utils";

const TIERS: Tier[] = ["low", "medium", "high"];

export function HistoryPage() {
  const [openId, setOpenId] = useState<string | null>(null);
  const [tier, setTier] = useState<Tier | "all">("all");
  const [model, setModel] = useState<string>("all");

  const rows = useQuery({ queryKey: ["assessments"], queryFn: api.assessments });

  const models = useMemo(
    () => Array.from(new Set((rows.data ?? []).map((row) => row.model))).sort(),
    [rows.data],
  );

  const filtered = (rows.data ?? []).filter(
    (row) =>
      (tier === "all" || row.inherent_risk_tier === tier) &&
      (model === "all" || row.model === model),
  );

  if (openId) {
    return <Detail id={openId} onBack={() => setOpenId(null)} />;
  }

  return (
    <div className="mx-auto max-w-[1400px] px-5 py-6">
      <header>
        <h2 className="text-lg font-semibold tracking-tight">History</h2>
        <p className="mt-1 max-w-[76ch] text-[13px] text-ink-muted">
          Every assessment this instance has run, newest first. Each one is stored with the
          request that produced it, the model that answered, and the policy adjustments that
          were applied — so a past answer can be re-read exactly as it was given.
        </p>
      </header>

      <div className="mt-5 flex flex-wrap items-center gap-4">
        <Filter
          label="Tier"
          value={tier}
          options={["all", ...TIERS]}
          render={(value) => (value === "all" ? "All" : tierLabel[value as Tier])}
          onChange={(value) => setTier(value as Tier | "all")}
        />
        {models.length > 1 && (
          <Filter
            label="Model"
            value={model}
            options={["all", ...models]}
            render={(value) => (value === "all" ? "All" : value)}
            onChange={setModel}
          />
        )}
        <span className="text-[12px] text-ink-subtle">
          {filtered.length} of {rows.data?.length ?? 0}
        </span>
      </div>

      {rows.isLoading && <p className="mt-6 text-[13px] text-ink-subtle">Loading…</p>}
      {rows.error && (
        <p className="mt-6 text-[13px] text-high">Could not load past assessments.</p>
      )}

      {rows.data && filtered.length === 0 && (
        <Card className="mt-5">
          <CardContent className="py-12 text-center">
            <HistoryIcon className="mx-auto size-5 text-ink-subtle" />
            <p className="mt-3 text-[13px] text-ink-muted">
              {rows.data.length === 0
                ? "Nothing assessed yet."
                : "No assessment matches those filters."}
            </p>
          </CardContent>
        </Card>
      )}

      {filtered.length > 0 && (
        <ul className="mt-4 space-y-2">
          {filtered.map((row) => (
            <li key={row.id}>
              <Row row={row} onOpen={() => setOpenId(row.id)} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Filter({
  label,
  value,
  options,
  render,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  render: (value: string) => string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-[12px] text-ink-muted">{label}</span>
      <div className="flex gap-1">
        {options.map((option) => (
          <button
            key={option}
            onClick={() => onChange(option)}
            aria-pressed={option === value}
            className={cn(
              "rounded-md border px-2 py-1 text-[12px] font-medium transition-colors",
              option === value
                ? "border-accent/30 bg-accent-soft text-accent"
                : "border-line bg-surface text-ink-muted hover:bg-raised",
            )}
          >
            {render(option)}
          </button>
        ))}
      </div>
    </div>
  );
}

function Row({ row, onOpen }: { row: HistoryRow; onOpen: () => void }) {
  return (
    <button
      onClick={onOpen}
      className={cn(
        "flex w-full items-start gap-4 rounded-card border border-l-4 border-line bg-surface px-4 py-3 text-left transition-colors hover:bg-raised",
        tierBorder[row.inherent_risk_tier],
      )}
    >
      <div className="min-w-0 flex-1">
        <p className="line-clamp-2 text-[13px] text-ink">{row.summary}</p>
        <div className="mt-2 flex flex-wrap items-center gap-1.5">
          <Badge variant={row.inherent_risk_tier}>
            {tierLabel[row.inherent_risk_tier]} inherent risk
          </Badge>
          {!row.ai_in_scope && <Badge>Out of scope</Badge>}
          <Badge>{aiTypeLabel[row.ai_type]}</Badge>
          <Badge>{oversightLabel[row.oversight_mode]}</Badge>
          {row.override_count > 0 && (
            <Badge variant="accent">
              {row.override_count} policy adjustment{row.override_count === 1 ? "" : "s"}
            </Badge>
          )}
        </div>
      </div>
      <div className="shrink-0 text-right text-[12px] text-ink-subtle">
        <div>{new Date(row.created_at).toLocaleString("en-GB")}</div>
        <div className="mt-0.5 tabular-nums">
          {row.model} · {(row.latency_ms / 1000).toFixed(1)}s
        </div>
      </div>
    </button>
  );
}

function Detail({ id, onBack }: { id: string; onBack: () => void }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["assessment", id],
    queryFn: () => api.assessment(id),
  });

  return (
    <div className="mx-auto max-w-[1000px] px-5 py-6">
      <Button variant="ghost" size="sm" onClick={onBack} className="-ml-2">
        <ArrowLeft /> Back to history
      </Button>
      {isLoading && (
        <p className="mt-6 flex items-center gap-2 text-[13px] text-ink-muted">
          <Loader2 className="size-3.5 animate-spin" /> Loading…
        </p>
      )}
      {error && (
        <p className="mt-6 text-[13px] text-high">That assessment could not be loaded.</p>
      )}
      {data && (
        <div className="mt-4">
          <p className="mb-4 rounded-card border border-line bg-raised/50 px-4 py-3 text-[13px] leading-relaxed text-ink-muted">
            <span className="mb-1 block text-[11px] font-medium uppercase tracking-wide text-ink-subtle">
              What was submitted
            </span>
            {String(data.request.description)}
          </p>
          <ResultsView response={data} />
        </div>
      )}
    </div>
  );
}
