import { cn } from "@/lib/utils";

const TIERS = ["low", "medium", "high"] as const;

/**
 * Gold tier down the side, returned tier across the top. The diagonal is agreement;
 * anything off it is the interesting part, so only off-diagonal cells are tinted.
 */
export function ConfusionMatrix({
  matrix,
}: {
  matrix: Record<string, Record<string, number>>;
}) {
  const total = Object.values(matrix).reduce(
    (sum, row) => sum + Object.values(row).reduce((a, b) => a + b, 0),
    0,
  );
  if (total === 0) {
    return <p className="text-[13px] text-ink-subtle">No graded tiers in this run.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[320px] border-separate border-spacing-1 text-[13px]">
        <thead>
          <tr>
            <th className="w-24" />
            <th
              colSpan={3}
              className="pb-1 text-[11px] font-medium uppercase tracking-wide text-ink-subtle"
            >
              returned
            </th>
          </tr>
          <tr>
            <th />
            {TIERS.map((tier) => (
              <th key={tier} className="px-2 pb-1 text-[12px] font-medium text-ink-muted">
                {tier}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {TIERS.map((gold) => (
            <tr key={gold}>
              <th className="pr-2 text-right text-[12px] font-medium text-ink-muted">
                gold {gold}
              </th>
              {TIERS.map((returned) => {
                const count = matrix[gold]?.[returned] ?? 0;
                const diagonal = gold === returned;
                return (
                  <td
                    key={returned}
                    className={cn(
                      "rounded-md border px-2 py-2.5 text-center tabular-nums",
                      count === 0 && "border-line bg-raised/50 text-ink-subtle",
                      count > 0 &&
                        diagonal &&
                        "border-low-line bg-low-soft font-semibold text-low",
                      count > 0 &&
                        !diagonal &&
                        "border-high-line bg-high-soft font-semibold text-high",
                    )}
                  >
                    {count}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
