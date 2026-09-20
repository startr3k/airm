import { useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { AlertCircle, ClipboardCheck, RotateCcw } from "lucide-react";
import { streamAssessment, type AssessResponse, type StreamStatus } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { InputPanel } from "@/components/assess/InputPanel";
import { INITIAL_FORM, type AssessFormState } from "@/components/assess/form";
import { Stepper } from "@/components/results/Stepper";
import { ResultsView } from "@/components/results/ResultsView";

export function AssessPage() {
  const [form, setForm] = useState<AssessFormState>(INITIAL_FORM);
  const [steps, setSteps] = useState<StreamStatus[]>([]);
  const [result, setResult] = useState<AssessResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const queryClient = useQueryClient();

  const run = async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setRunning(true);
    setSteps([]);
    setResult(null);
    setError(null);

    try {
      await streamAssessment(
        {
          description: form.description,
          deployment_pattern: form.deploymentPattern,
          is_agentic: form.isAgentic,
          tools_accessible: form.toolsAccessible,
          customer_facing: form.customerFacing,
          model: form.model,
        },
        {
          onStatus: (status) => setSteps((prev) => [...prev, status]),
          onResult: (response) => {
            setResult(response);
            void queryClient.invalidateQueries({ queryKey: ["assessments"] });
          },
          onError: setError,
        },
        controller.signal,
      );
    } catch (cause) {
      if (!controller.signal.aborted) {
        setError(cause instanceof Error ? cause.message : "The assessment failed.");
      }
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="mx-auto h-full max-w-[1400px] px-5 py-6">
      <div className="grid h-full gap-5 lg:grid-cols-[minmax(340px,420px)_minmax(0,1fr)] print:block">
        {/* Each column scrolls on its own, so reading a long result never moves the
            input panel, and the page itself never scrolls. */}
        <div className="lg:h-full lg:overflow-y-auto lg:pr-1 print:hidden">
          <InputPanel form={form} setForm={setForm} onSubmit={run} running={running} />
        </div>

        <div className="min-h-[70dvh] lg:h-full lg:overflow-y-auto lg:pr-1">
          {error && (
            <div
              role="alert"
              className="mb-4 flex items-start gap-2.5 rounded-card border border-high-line bg-high-soft p-4 text-[13px] text-high"
            >
              <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden />
              <div className="min-w-0 flex-1">
                <p className="font-semibold">The assessment did not complete</p>
                <p className="mt-1 leading-relaxed opacity-90">{error}</p>
              </div>
              <Button variant="outline" size="sm" onClick={run} disabled={running}>
                <RotateCcw aria-hidden /> Retry
              </Button>
            </div>
          )}

          {running && steps.length > 0 && !result && <Stepper steps={steps} />}

          {result && <ResultsView response={result} />}

          {!running && !result && !error && (
            <Card className="h-full">
              <CardContent className="flex h-full min-h-[60dvh] flex-col items-center justify-center px-8 py-12 text-center">
                <div className="mb-5 rounded-2xl border border-line bg-raised p-4">
                  <ClipboardCheck className="size-7 text-ink-subtle" aria-hidden />
                </div>
                <h2 className="text-sm font-semibold text-ink">No assessment yet</h2>
                <p className="mt-2 max-w-md text-[13px] leading-relaxed text-ink-muted">
                  Describe an AI use case and it will be classified against the MindForge
                  handbook: what counts as AI in scope, how each Section 2.4 materiality factor
                  rates, the inherent risk tier, the seven Appendix B dimensions, and the
                  guardrails and metrics that fit.
                </p>
                <p className="mt-4 max-w-md text-[12px] leading-relaxed text-ink-subtle">
                  This assesses <strong className="font-medium text-ink-muted">inherent</strong>{" "}
                  risk — the risk before controls. Residual risk needs real evaluation evidence,
                  which a description cannot provide.
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
