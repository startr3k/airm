import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { FlaskConical } from "lucide-react";
import { api, type EvalResult, type GoldCase } from "@/lib/api";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CaseTable } from "@/components/evals/CaseTable";
import { ConfusionMatrix } from "@/components/evals/ConfusionMatrix";
import { Meter, Stat } from "@/components/evals/metrics";
import { pct, scoreTone } from "@/lib/format";
import { RunControl } from "@/components/evals/RunControl";
import { cn, formatTokens } from "@/lib/utils";

const FIELD_LABELS: Record<string, string> = {
  ai_in_scope: "In scope under Section 1.1",
  ai_type: "AI type",
  inherent_risk_tier: "Inherent tier (exact)",
  tier_within_tolerance: "Inherent tier (within tolerance)",
  recommended_oversight_mode: "Oversight mode",
  confidence_calibrated: "Confidence not overstated",
  agentic_analysis: "Agentic analysis present iff agentic",
  risk_analysis_withheld: "Analysis withheld when out of scope",
};

const RECALL_LABELS: Record<string, string> = {
  dimension_floors: "Dimensions rated at or above their floor",
  top_10_flags: "ABS top-10 risks flagged",
  considerations: "Appendix H Considerations cited",
  policy_rules: "Policy rules fired",
};

export function EvalsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["evals", "latest"],
    queryFn: api.evalsLatest,
  });
  const [selected, setSelected] = useState<string | null>(null);

  const goldById = useMemo(() => {
    const index: Record<string, GoldCase> = {};
    for (const item of data?.gold ?? []) index[item.id] = item;
    return index;
  }, [data]);

  const results = data?.models ?? [];
  const active: EvalResult | undefined =
    results.find((r) => r.model === selected) ?? results[0];

  return (
    <div className="mx-auto max-w-[1400px] px-5 py-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">Evals</h2>
          <p className="mt-1 max-w-[70ch] text-[13px] text-ink-muted">
            {data?.gold.length ?? 10} hand-written use cases, each run {active?.n ?? 3} times
            and graded only on what the handbook actually settles — scope, type, tier, oversight
            mode, and whether the risks and Considerations that apply were cited. Judgement
            calls are left ungraded rather than scored against one analyst's opinion.
          </p>
        </div>
        <RunControl
          model={active?.model ?? "claude-sonnet-5"}
          cases={data?.gold.length ?? 10}
          n={active?.n ?? 3}
        />
      </header>

      {data && data.gold_problems.length > 0 && (
        <Card className="mt-5 border-l-4 border-l-high">
          <CardHeader>
            <CardTitle>The gold set does not match the framework pack</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-1 text-[13px] text-ink-muted">
              {data.gold_problems.map((problem) => (
                <li key={problem}>{problem}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {isLoading && <p className="mt-6 text-[13px] text-ink-subtle">Loading results…</p>}
      {error && <p className="mt-6 text-[13px] text-high">Could not load eval results.</p>}

      {data && results.length === 0 && (
        <Card className="mt-5">
          <CardContent className="py-12 text-center">
            <FlaskConical className="mx-auto size-5 text-ink-subtle" />
            <p className="mt-3 text-[13px] text-ink-muted">
              No runs yet. Run <code className="text-ink">make evals</code>, or use the button
              above.
            </p>
          </CardContent>
        </Card>
      )}

      {active && (
        <>
          {results.length > 1 && (
            <div className="mt-5 flex flex-wrap gap-1.5" role="tablist" aria-label="Model">
              {results.map((result) => (
                <button
                  key={result.model}
                  role="tab"
                  aria-selected={result.model === active.model}
                  onClick={() => setSelected(result.model)}
                  className={cn(
                    "rounded-lg border px-3 py-1.5 text-[13px] font-medium transition-colors",
                    result.model === active.model
                      ? "border-accent/30 bg-accent-soft text-accent"
                      : "border-line bg-surface text-ink-muted hover:bg-raised",
                  )}
                >
                  {result.model}
                </button>
              ))}
            </div>
          )}

          <section className="mt-5 grid grid-cols-2 gap-3 lg:grid-cols-5">
            <Stat
              label="Check accuracy"
              value={pct(active.summary.overall_accuracy)}
              caption={`${active.summary.checks_graded} graded assertions`}
              tone={scoreTone(active.summary.overall_accuracy)}
            />
            <Stat
              label="Tier exact"
              value={pct(active.summary.field_accuracy.inherent_risk_tier?.accuracy ?? null)}
              caption={`within tolerance ${pct(
                active.summary.field_accuracy.tier_within_tolerance?.accuracy ?? null,
              )}`}
              tone={scoreTone(
                active.summary.field_accuracy.inherent_risk_tier?.accuracy ?? null,
              )}
            />
            <Stat
              label="Run-to-run agreement"
              value={pct(active.summary.tier_consistency.mean_modal_agreement)}
              caption={`${active.summary.tier_consistency.unanimous_cases}/${active.cases} unanimous`}
              tone={scoreTone(active.summary.tier_consistency.mean_modal_agreement)}
            />
            <Stat
              label="Median latency"
              value={`${(active.summary.latency_ms.p50 / 1000).toFixed(1)}s`}
              caption={`p95 ${(active.summary.latency_ms.p95 / 1000).toFixed(1)}s`}
            />
            <Stat
              label="Cost per assessment"
              value={`$${active.summary.cost_usd.per_assessment.toFixed(4)}`}
              caption={`$${active.summary.cost_usd.total.toFixed(2)} this run`}
            />
          </section>

          <section className="mt-4 grid gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Per-field accuracy</CardTitle>
                <CardDescription>
                  Each assertion is graded once per run. Fields a case does not pin down are not
                  graded for that case.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {Object.entries(active.summary.field_accuracy).map(([field, block]) => (
                  <Meter
                    key={field}
                    label={FIELD_LABELS[field] ?? field}
                    value={block.accuracy}
                    detail={`${block.passed}/${block.graded}`}
                  />
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Tier confusion</CardTitle>
                <CardDescription>Gold tier against what the tool returned.</CardDescription>
              </CardHeader>
              <CardContent>
                <ConfusionMatrix matrix={active.summary.tier_confusion} />
              </CardContent>
            </Card>
          </section>

          <section className="mt-4 grid gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Recall against the handbook</CardTitle>
                <CardDescription>
                  Not "did it say something sensible", but "did it name the specific thing the
                  handbook names".
                </CardDescription>
              </CardHeader>
              <CardContent>
                {Object.entries(active.summary.recall).map(([name, block]) => (
                  <Meter
                    key={name}
                    label={RECALL_LABELS[name] ?? name}
                    value={block.recall}
                    detail={`${block.matched}/${block.expected}`}
                  />
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Run</CardTitle>
                <CardDescription>What produced these numbers.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-1.5 text-[13px]">
                <Row label="Model" value={<code className="text-ink">{active.model}</code>} />
                <Row label="Effort" value={active.effort} />
                <Row label="Runs" value={`${active.cases} cases × ${active.n}`} />
                <Row label="Duration" value={`${(active.duration_s / 60).toFixed(1)} min`} />
                <Row label="Cache hit rate" value={pct(active.summary.tokens.cache_hit_rate)} />
                <Row label="Output tokens" value={formatTokens(active.summary.tokens.output)} />
                <Row
                  label="API errors"
                  value={
                    <span className={active.summary.runs_errored ? "text-high" : undefined}>
                      {active.summary.runs_errored} ({active.summary.retries} retried)
                    </span>
                  }
                />
                <Row label="Pack" value={`v${active.pack_version}`} />
                <Row
                  label="Prompt"
                  value={
                    <code className="text-ink-muted">
                      {active.prompt_sha256?.slice(0, 12) ?? "—"}
                    </code>
                  }
                />
                <Row
                  label="Finished"
                  value={new Date(active.started_at).toLocaleString("en-GB")}
                />
              </CardContent>
            </Card>
          </section>

          <section className="mt-5">
            <div className="mb-2 flex items-baseline justify-between">
              <h3 className="text-sm font-semibold tracking-tight">The gold set</h3>
              <p className="text-[12px] text-ink-subtle">
                “Model alone” is the tier before the policy layer floored it.
              </p>
            </div>
            <CaseTable rows={active.summary.per_case} gold={goldById} />
          </section>

          {results.length > 1 && (
            <section className="mt-5">
              <h3 className="mb-2 text-sm font-semibold tracking-tight">Model comparison</h3>
              <Comparison results={results} />
            </section>
          )}
        </>
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <span className="text-ink-muted">{label}</span>
      <span className="text-right tabular-nums text-ink">{value}</span>
    </div>
  );
}

function Comparison({ results }: { results: EvalResult[] }) {
  const rows: { label: string; value: (r: EvalResult) => string }[] = [
    { label: "Check accuracy", value: (r) => pct(r.summary.overall_accuracy) },
    {
      label: "Tier exact",
      value: (r) => pct(r.summary.field_accuracy.inherent_risk_tier?.accuracy ?? null),
    },
    {
      label: "Oversight mode",
      value: (r) => pct(r.summary.field_accuracy.recommended_oversight_mode?.accuracy ?? null),
    },
    {
      label: "Consideration recall",
      value: (r) => pct(r.summary.recall.considerations?.recall ?? null),
    },
    {
      label: "Run-to-run agreement",
      value: (r) => pct(r.summary.tier_consistency.mean_modal_agreement),
    },
    {
      label: "Median latency",
      value: (r) => `${(r.summary.latency_ms.p50 / 1000).toFixed(1)}s`,
    },
    {
      label: "Cost per assessment",
      value: (r) => `$${r.summary.cost_usd.per_assessment.toFixed(4)}`,
    },
  ];

  return (
    <div className="overflow-hidden rounded-card border border-line bg-surface">
      <table className="w-full text-[13px]">
        <thead className="border-b border-line bg-raised/60 text-[11px] uppercase tracking-wide text-ink-subtle">
          <tr>
            <th className="px-3 py-2 text-left font-medium">Metric</th>
            {results.map((result) => (
              <th key={result.model} className="px-3 py-2 text-right font-medium">
                {result.model}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.label} className="border-b border-line/70 last:border-0">
              <td className="px-3 py-2 text-ink-muted">{row.label}</td>
              {results.map((result) => (
                <td key={result.model} className="px-3 py-2 text-right tabular-nums text-ink">
                  {row.value(result)}
                </td>
              ))}
            </tr>
          ))}
          <tr>
            <td className="px-3 py-2 text-ink-muted">Runs</td>
            {results.map((result) => (
              <td key={result.model} className="px-3 py-2 text-right">
                <Badge>{`${result.cases} × ${result.n}`}</Badge>
              </td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  );
}
