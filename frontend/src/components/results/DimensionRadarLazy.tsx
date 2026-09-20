import { Suspense, lazy } from "react";
import type { Assessment } from "@/lib/api";

/** Recharts is ~500 kB of the bundle, and nothing renders it until an assessment comes
 *  back. Splitting it out keeps it off the critical path: the app shell and the input
 *  panel load without it, and the chart's chunk is fetched while the model is working.
 */
const DimensionRadar = lazy(() =>
  import("./DimensionRadar").then((module) => ({ default: module.DimensionRadar })),
);

export function DimensionRadarLazy({
  dimensions,
}: {
  dimensions: Assessment["risk_dimensions"];
}) {
  return (
    <Suspense fallback={<RadarSkeleton />}>
      <DimensionRadar dimensions={dimensions} />
    </Suspense>
  );
}

function RadarSkeleton() {
  return (
    <div
      className="flex h-64 w-full items-center justify-center rounded-lg border border-dashed border-line"
      aria-hidden="true"
    >
      <span className="text-[12px] text-ink-subtle">Drawing chart…</span>
    </div>
  );
}
