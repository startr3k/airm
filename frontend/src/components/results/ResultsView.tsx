import { useState } from "react";
import {
  AlertTriangle,
  ChevronDown,
  Copy,
  Download,
  Printer,
  Info,
  ShieldAlert,
  Zap,
} from "lucide-react";
import type { AssessResponse } from "@/lib/api";
import {
  aiTypeLabel,
  cn,
  formatTokens,
  oversightLabel,
  tierBorder,
  tierLabel,
  tierStyles,
  type Tier,
} from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DimensionRadarLazy } from "./DimensionRadarLazy";
import { SourceChip } from "@/components/source/SourceChip";
import { useCitations } from "@/lib/citations";

function TierBadge({ tier, size = "sm" }: { tier: Tier; size?: "sm" | "lg" }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-lg border font-semibold",
        tierStyles[tier],
        size === "lg" ? "px-3 py-1.5 text-sm" : "px-2 py-0.5 text-[12px]",
      )}
    >
      {tierLabel[tier]}
      {/* The space is real, not just a margin: without it this reads aloud as
          "Highinherent risk". */}
      {size === "lg" && <span className="ml-1.5 font-normal opacity-80"> inherent risk</span>}
    </span>
  );
}

/** A citation chip, rendered only when the pack actually has that name. */
function Cite({
  kind,
  name,
  citations,
}: {
  kind: "guardrails" | "metrics" | "considerations" | "dimensions";
  name: string | number;
  citations: ReturnType<typeof useCitations>;
}) {
  const itemId = citations.lookup(kind, name);
  if (!itemId) return null;
  return <SourceChip itemId={itemId} page={citations.page(itemId)} className="print:hidden" />;
}

export function ResultsView({ response }: { response: AssessResponse }) {
  const citations = useCitations();
  const { assessment: a, policy_overrides: overrides, usage } = response;
  const [openDimension, setOpenDimension] = useState<string | null>(null);

  const copyJson = () => navigator.clipboard.writeText(JSON.stringify(response, null, 2));
  const downloadJson = () => {
    const blob = new Blob([JSON.stringify(response, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `assessment-${response.assessment_id}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4">
      <Card data-print-block className={cn("border-l-4", tierBorder[a.inherent_risk_tier])}>
        <CardContent className="pt-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <p className="text-sm leading-relaxed text-ink">{a.use_case_summary}</p>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <Badge variant="accent">{aiTypeLabel[a.ai_type]}</Badge>
                <Badge>Confidence: {tierLabel[a.confidence]}</Badge>
                {a.ai_in_scope && <Badge>{oversightLabel[a.recommended_oversight_mode]}</Badge>}
              </div>
            </div>
            {a.ai_in_scope && <TierBadge tier={a.inherent_risk_tier} size="lg" />}
          </div>
          <p className="mt-4 border-t border-line pt-3 text-[11px] text-ink-subtle">
            {response.model} · {(response.latency_ms / 1000).toFixed(1)}s ·{" "}
            {formatTokens(usage.input_tokens)} in / {formatTokens(usage.output_tokens)} out ·{" "}
            {usage.cache_read_input_tokens > 0 ? (
              <span className="text-low">
                {formatTokens(usage.cache_read_input_tokens)} tokens from cache
              </span>
            ) : (
              <>cache written ({formatTokens(usage.cache_creation_input_tokens)})</>
            )}
          </p>
        </CardContent>
      </Card>

      {!a.ai_in_scope && (
        <div
          role="alert"
          className="rounded-card border border-medium-line bg-medium-soft p-4 text-[13px] text-medium"
        >
          <div className="flex items-start gap-2.5">
            <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden />
            <div>
              <p className="font-semibold">Not AI under Section 1.1 — no assessment produced</p>
              <p className="mt-1.5 whitespace-pre-line leading-relaxed opacity-90">
                {a.assessor_notes}
              </p>
            </div>
          </div>
        </div>
      )}

      {overrides.length > 0 && (
        <Card data-print-block className="border-l-4 border-l-accent">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldAlert className="size-4 text-accent" aria-hidden />
              Policy layer adjusted this result
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {overrides.map((o, i) => (
              <div key={i} className="rounded-lg border border-line bg-raised p-3">
                <div className="flex flex-wrap items-center gap-2 text-[12px]">
                  <code className="rounded bg-accent-soft px-1.5 py-0.5 font-mono text-accent">
                    {o.rule}
                  </code>
                  <span className="text-ink-muted">{o.field}</span>
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-2 text-[12px]">
                  <span className="text-ink-subtle">model said</span>
                  <code className="rounded border border-line bg-surface px-1.5 py-0.5 font-mono">
                    {JSON.stringify(o.before)}
                  </code>
                  <span className="text-ink-subtle">→ policy said</span>
                  <code className="rounded border border-accent/30 bg-accent-soft px-1.5 py-0.5 font-mono text-accent">
                    {Array.isArray(o.after)
                      ? `${o.after.length} item(s)`
                      : JSON.stringify(o.after)}
                  </code>
                </div>
                <p className="mt-2 text-[12px] leading-relaxed text-ink-muted">{o.reason}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {a.ai_in_scope && (
        <>
          <Card data-print-block>
            <CardHeader>
              <CardTitle>Risk dimensions</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 lg:grid-cols-2">
              <DimensionRadarLazy dimensions={a.risk_dimensions} />
              <ul className="space-y-1.5">
                {a.risk_dimensions.map((d) => {
                  const open = openDimension === d.dimension;
                  return (
                    <li
                      key={d.dimension}
                      className={cn(
                        "rounded-lg border border-line border-l-4",
                        tierBorder[d.rating],
                      )}
                    >
                      <button
                        type="button"
                        onClick={() => setOpenDimension(open ? null : d.dimension)}
                        aria-expanded={open}
                        className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left"
                      >
                        <span className="text-[13px] font-medium text-ink">{d.dimension}</span>
                        <span className="flex items-center gap-1.5">
                          <TierBadge tier={d.rating} />
                          <ChevronDown
                            className={cn(
                              "size-3.5 text-ink-subtle transition-transform",
                              open && "rotate-180",
                            )}
                            aria-hidden
                          />
                        </span>
                      </button>
                      {open && (
                        <div className="border-t border-line px-3 py-2.5">
                          <p className="text-[12px] leading-relaxed text-ink-muted">
                            {d.rationale}
                          </p>
                          {d.key_risks.length > 0 && (
                            <ul className="mt-2 flex flex-wrap gap-1.5">
                              {d.key_risks.map((risk) => (
                                <li key={risk}>
                                  <Badge className="text-[11px]">{risk}</Badge>
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>
                      )}
                    </li>
                  );
                })}
              </ul>
            </CardContent>
          </Card>

          <Card data-print-block>
            <CardHeader>
              <CardTitle>Materiality factors</CardTitle>
            </CardHeader>
            <CardContent>
              <table className="w-full text-left text-[13px]">
                <thead>
                  <tr className="border-b border-line text-[12px] text-ink-subtle">
                    <th scope="col" className="pb-2 font-medium">
                      Factor
                    </th>
                    <th scope="col" className="pb-2 font-medium">
                      Rating
                    </th>
                    <th scope="col" className="pb-2 font-medium">
                      Rationale
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {a.materiality_factors.map((f) => (
                    <tr
                      key={f.factor}
                      className="border-b border-line/60 last:border-0 align-top"
                    >
                      <td className="py-2.5 pr-3 font-medium text-ink">{f.factor}</td>
                      <td className="py-2.5 pr-3">
                        <TierBadge tier={f.rating} />
                      </td>
                      <td className="py-2.5 text-[12px] leading-relaxed text-ink-muted">
                        {f.rationale}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>

          {a.agentic_considerations && (
            <Card data-print-block className="border-l-4 border-l-high">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Zap className="size-4 text-high" aria-hidden />
                  Agentic considerations
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 text-[13px]">
                <div>
                  <h4 className="mb-1 text-[12px] font-semibold text-ink-muted">
                    Tool access risk
                  </h4>
                  <p className="leading-relaxed text-ink-muted">
                    {a.agentic_considerations.tool_access_risk}
                  </p>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <h4 className="mb-1.5 text-[12px] font-semibold text-ink-muted">
                      Least privilege
                    </h4>
                    <ul className="space-y-1 text-[12px] text-ink-muted">
                      {a.agentic_considerations.least_privilege_recommendations.map((item) => (
                        <li key={item} className="flex gap-1.5">
                          <span aria-hidden>·</span>
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <h4 className="mb-1.5 text-[12px] font-semibold text-ink-muted">
                      Interruption controls
                    </h4>
                    <ul className="space-y-1 text-[12px] text-ink-muted">
                      {a.agentic_considerations.interruption_controls.map((item) => (
                        <li key={item} className="flex gap-1.5">
                          <span aria-hidden>·</span>
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
                {a.agentic_considerations.never_delegate_flags.length > 0 && (
                  <div className="rounded-lg border border-high-line bg-high-soft p-3">
                    <h4 className="mb-2 flex items-center gap-1.5 text-[12px] font-semibold text-high">
                      <AlertTriangle className="size-3.5" aria-hidden />
                      Never delegate
                    </h4>
                    <ul className="space-y-1 text-[12px] text-high">
                      {a.agentic_considerations.never_delegate_flags.map((flag) => (
                        <li key={flag} className="flex gap-1.5">
                          <span aria-hidden>·</span>
                          {flag}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          <Card data-print-block>
            <CardHeader>
              <CardTitle>Recommended controls</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <h4 className="mb-2 text-[12px] font-semibold text-ink-muted">
                  Guardrails ({a.recommended_guardrails.length})
                </h4>
                <ul className="space-y-1.5">
                  {a.recommended_guardrails.map((g) => (
                    <li key={g.guardrail} className="rounded-lg border border-line px-3 py-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-[13px] font-medium text-ink">{g.guardrail}</span>
                        <Badge className="font-mono text-[11px]">{g.handbook_ref}</Badge>
                        <Cite kind="guardrails" name={g.guardrail} citations={citations} />
                      </div>
                      <p className="mt-1 text-[12px] leading-relaxed text-ink-muted">{g.why}</p>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h4 className="mb-2 text-[12px] font-semibold text-ink-muted">
                  Metrics ({a.recommended_metrics.length})
                </h4>
                <ul className="flex flex-wrap gap-1.5">
                  {a.recommended_metrics.map((m) => (
                    <li key={m} className="flex items-center gap-1">
                      <Badge>{m}</Badge>
                      <Cite kind="metrics" name={m} citations={citations} />
                    </li>
                  ))}
                </ul>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <h4 className="mb-2 text-[12px] font-semibold text-ink-muted">
                    ABS top-10 flags
                  </h4>
                  <ul className="flex flex-wrap gap-1.5">
                    {a.top_10_flags.length === 0 ? (
                      <li className="text-[12px] text-ink-subtle">None apply.</li>
                    ) : (
                      a.top_10_flags.map((f) => (
                        <li key={f}>
                          <Badge variant="medium">{f}</Badge>
                        </li>
                      ))
                    )}
                  </ul>
                </div>
                <div>
                  <h4 className="mb-2 text-[12px] font-semibold text-ink-muted">
                    Relevant Considerations
                  </h4>
                  <ul className="flex flex-wrap gap-1.5">
                    {a.relevant_considerations.map((n) => (
                      <li key={n} className="flex items-center gap-1">
                        <Badge variant="accent" className="tabular-nums">
                          #{n}
                        </Badge>
                        <Cite kind="considerations" name={n} citations={citations} />
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card data-print-block>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Info className="size-4 text-ink-muted" aria-hidden />
                Assessor notes
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="whitespace-pre-line text-[13px] leading-relaxed text-ink-muted">
                {a.assessor_notes}
              </p>
            </CardContent>
          </Card>
        </>
      )}

      <div className="flex flex-wrap gap-2 pb-2 print:hidden">
        <Button variant="outline" size="sm" onClick={() => window.print()}>
          <Printer aria-hidden /> Export PDF
        </Button>
        <Button variant="outline" size="sm" onClick={copyJson}>
          <Copy aria-hidden /> Copy JSON
        </Button>
        <Button variant="outline" size="sm" onClick={downloadJson}>
          <Download aria-hidden /> Download JSON
        </Button>
        <span className="ml-auto self-center text-[11px] text-ink-subtle">
          Saved to history · {response.assessment_id}
        </span>
      </div>
    </div>
  );
}
