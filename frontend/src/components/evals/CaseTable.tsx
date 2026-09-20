import { Fragment, useState } from "react";
import { ChevronRight } from "lucide-react";
import type { EvalSummary, GoldCase } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { cn, tierLabel, type Tier } from "@/lib/utils";

type Row = EvalSummary["per_case"][number];

/** `high ×2, medium ×1` -- the repeats are the run-to-run variance, so they stay. */
function tally(tiers: Tier[]): { tier: Tier; count: number }[] {
  const order: Tier[] = ["low", "medium", "high"];
  return order
    .map((tier) => ({ tier, count: tiers.filter((t) => t === tier).length }))
    .filter((entry) => entry.count > 0);
}

function TierChips({ tiers, expected }: { tiers: Tier[]; expected: Tier | null }) {
  if (tiers.length === 0) return <span className="text-ink-subtle">—</span>;
  return (
    <span className="inline-flex flex-wrap gap-1">
      {tally(tiers).map(({ tier, count }) => (
        <Badge
          key={tier}
          variant={tier}
          className={cn(expected && tier !== expected && "opacity-100 ring-1 ring-high-line")}
        >
          {tierLabel[tier]}
          {count > 1 && <span className="tabular-nums opacity-70">×{count}</span>}
        </Badge>
      ))}
    </span>
  );
}

export function CaseTable({ rows, gold }: { rows: Row[]; gold: Record<string, GoldCase> }) {
  const [open, setOpen] = useState<string | null>(null);

  return (
    <div className="overflow-hidden rounded-card border border-line bg-surface">
      <table className="w-full text-[13px]">
        <thead className="border-b border-line bg-raised/60 text-[11px] uppercase tracking-wide text-ink-subtle">
          <tr>
            <th className="w-8" />
            <th className="px-3 py-2 text-left font-medium">Case</th>
            <th className="px-3 py-2 text-left font-medium">Gold</th>
            <th className="px-3 py-2 text-left font-medium">Returned</th>
            <th className="px-3 py-2 text-left font-medium">Model alone</th>
            <th className="px-3 py-2 text-right font-medium">Checks</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const expanded = open === row.case_id;
            const allPassed = row.checks_passed === row.checks_graded;
            const clean = allPassed && row.missing.length === 0;
            const floored =
              row.model_tiers.some((t, i) => t !== row.tiers[i]) && row.model_tiers.length > 0;
            return (
              <Fragment key={row.case_id}>
                <tr
                  className={cn(
                    "cursor-pointer border-b border-line/70 align-middle hover:bg-raised/50",
                    expanded && "bg-raised/50",
                  )}
                  onClick={() => setOpen(expanded ? null : row.case_id)}
                >
                  <td className="pl-3">
                    <ChevronRight
                      className={cn(
                        "size-3.5 text-ink-subtle transition-transform",
                        expanded && "rotate-90",
                      )}
                    />
                  </td>
                  <td className="px-3 py-2.5">
                    <div className="font-medium text-ink">{row.title}</div>
                    <code className="text-[11px] text-ink-subtle">{row.case_id}</code>
                  </td>
                  <td className="px-3 py-2.5">
                    {row.expected_tier ? (
                      <Badge variant={row.expected_tier}>{tierLabel[row.expected_tier]}</Badge>
                    ) : (
                      <span className="text-ink-subtle">out of scope</span>
                    )}
                  </td>
                  <td className="px-3 py-2.5">
                    <TierChips tiers={row.tiers} expected={row.expected_tier} />
                  </td>
                  <td className="px-3 py-2.5">
                    {floored ? (
                      <TierChips tiers={row.model_tiers} expected={row.expected_tier} />
                    ) : (
                      <span className="text-[12px] text-ink-subtle">same</span>
                    )}
                  </td>
                  <td className="px-3 py-2.5 text-right tabular-nums">
                    {/* A failed assertion and an uncited risk are different failures and
                        must not read as the same one. */}
                    <span className={allPassed ? "text-low" : "text-high"}>
                      {row.checks_passed}/{row.checks_graded}
                    </span>
                    {row.missing.length > 0 && (
                      <div className="text-[12px] text-medium">
                        {row.missing.length} not cited
                      </div>
                    )}
                    {row.errors > 0 && (
                      <div className="text-[12px] text-high">{row.errors} failed to run</div>
                    )}
                  </td>
                </tr>
                {expanded && (
                  <tr className="border-b border-line/70 bg-raised/30">
                    <td />
                    <td colSpan={5} className="px-3 pb-4 pt-1">
                      <p className="max-w-[70ch] text-[13px] italic text-ink-muted">
                        {row.tests}
                      </p>
                      {gold[row.case_id] && (
                        <p className="mt-2 max-w-[80ch] rounded-md border border-line bg-surface px-3 py-2 text-[12px] leading-relaxed text-ink-muted">
                          {gold[row.case_id].description}
                        </p>
                      )}
                      {Object.keys(row.failed_fields).length > 0 && (
                        <div className="mt-3">
                          <div className="text-[11px] font-medium uppercase tracking-wide text-ink-subtle">
                            Wrong
                          </div>
                          <ul className="mt-1 space-y-0.5">
                            {Object.entries(row.failed_fields).map(([field, count]) => (
                              <li key={field} className="text-[13px] text-ink">
                                <code className="text-high">{field}</code>{" "}
                                <span className="text-ink-muted">
                                  in {count} of {row.runs} run{row.runs === 1 ? "" : "s"}
                                </span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {row.missing.length > 0 && (
                        <div className="mt-3">
                          <div className="text-[11px] font-medium uppercase tracking-wide text-ink-subtle">
                            Not cited
                          </div>
                          <ul className="mt-1 space-y-0.5">
                            {row.missing.map((item) => (
                              <li key={item} className="text-[13px] text-ink-muted">
                                {item}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {clean && (
                        <p className="mt-3 text-[13px] text-low">
                          Every graded assertion passed on every run.
                        </p>
                      )}
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
