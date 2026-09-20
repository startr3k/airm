import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Play, TriangleAlert } from "lucide-react";
import { api, ApiError, type EvalStatus } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/**
 * Starting a run costs real money and takes minutes, so the button says what it will
 * do before it does it, and the backend refuses a second concurrent run.
 */
export function RunControl({ model, cases, n }: { model: string; cases: number; n: number }) {
  const queryClient = useQueryClient();
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const status = useQuery({
    queryKey: ["evals", "status"],
    queryFn: api.evalsStatus,
    refetchInterval: (query) =>
      (query.state.data as EvalStatus | undefined)?.state === "running" ? 2000 : false,
  });

  const running = status.data?.state === "running";

  useEffect(() => {
    if (status.data?.state === "done") {
      void queryClient.invalidateQueries({ queryKey: ["evals", "latest"] });
    }
  }, [status.data?.state, status.data?.run_id, queryClient]);

  const start = useMutation({
    mutationFn: () => api.runEvals({ model, n }),
    onSuccess: () => {
      setConfirming(false);
      setError(null);
      void status.refetch();
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : String(err)),
  });

  if (running) {
    const done = status.data?.completed ?? 0;
    const total = status.data?.total || 1;
    return (
      <div className="flex min-w-[260px] flex-col gap-1.5">
        <div className="flex items-center gap-2 text-[13px] text-ink">
          <Loader2 className="size-3.5 animate-spin text-accent" />
          <span className="tabular-nums">
            {done} / {total} assessments
          </span>
          {(status.data?.retries ?? 0) > 0 && (
            <span className="text-[12px] text-medium">{status.data?.retries} retried</span>
          )}
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-raised">
          <div
            className="h-full rounded-full bg-accent transition-[width] duration-500"
            style={{ width: `${Math.round((done / total) * 100)}%` }}
          />
        </div>
        <p className="truncate text-[12px] text-ink-subtle">{status.data?.last_event}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-end gap-1.5">
      <div className="flex items-center gap-2">
        {confirming && (
          <span className="text-[12px] text-ink-muted">
            {cases * n} paid API calls, a few minutes.
          </span>
        )}
        <Button
          size="sm"
          variant={confirming ? "default" : "outline"}
          disabled={start.isPending}
          onClick={() => (confirming ? start.mutate() : setConfirming(true))}
        >
          {start.isPending ? <Loader2 className="animate-spin" /> : <Play />}
          {confirming ? "Yes, run it" : "Run evals"}
        </Button>
        {confirming && (
          <Button size="sm" variant="ghost" onClick={() => setConfirming(false)}>
            Cancel
          </Button>
        )}
      </div>
      {(error || status.data?.state === "error") && (
        <p
          className={cn(
            "flex items-center gap-1.5 text-[12px] text-high",
            "max-w-[420px] text-right",
          )}
        >
          <TriangleAlert className="size-3.5 shrink-0" />
          {error ?? status.data?.detail}
        </p>
      )}
    </div>
  );
}
