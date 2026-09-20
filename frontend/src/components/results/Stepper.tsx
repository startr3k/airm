import { Check, Loader2 } from "lucide-react";
import type { StreamStatus } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";

export function Stepper({ steps }: { steps: StreamStatus[] }) {
  return (
    <Card>
      <CardContent className="pt-5">
        <h2 className="mb-3 text-sm font-semibold">Running assessment</h2>
        <ol className="space-y-2.5">
          {steps.map((step, index) => {
            const isLast = index === steps.length - 1;
            return (
              <li key={step.step} className="flex items-center gap-2.5 text-[13px]">
                {isLast ? (
                  <Loader2 className="size-4 shrink-0 animate-spin text-accent" aria-hidden />
                ) : (
                  <Check className="size-4 shrink-0 text-low" aria-hidden />
                )}
                <span className={isLast ? "text-ink" : "text-ink-muted"}>{step.label}</span>
              </li>
            );
          })}
        </ol>
        <p className="mt-4 text-[12px] text-ink-subtle">
          Steps come from the model's own output as it is generated, not a timer.
        </p>
      </CardContent>
    </Card>
  );
}
