import { useState, type KeyboardEvent } from "react";
import { Loader2, Play, Plus, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { EXAMPLES, type Example } from "./examples";
import { PATTERNS, type AssessFormState } from "./form";

const MAX_CHARS = 20_000;

function Toggle({
  checked,
  onChange,
  label,
  description,
}: {
  checked: boolean;
  onChange: (value: boolean) => void;
  label: string;
  description: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className="flex w-full items-start gap-3 rounded-lg border border-line px-3 py-2.5 text-left transition-colors hover:bg-raised"
    >
      <span
        className={cn(
          "mt-0.5 flex h-5 w-9 shrink-0 items-center rounded-full border transition-colors",
          checked ? "border-accent bg-accent" : "border-line-strong bg-raised",
        )}
      >
        <span
          className={cn(
            "ml-0.5 size-4 rounded-full bg-white shadow-sm transition-transform",
            checked && "translate-x-3.5",
          )}
        />
      </span>
      <span className="min-w-0">
        <span className="block text-[13px] font-medium text-ink">{label}</span>
        <span className="block text-[12px] leading-snug text-ink-muted">{description}</span>
      </span>
    </button>
  );
}

export function InputPanel({
  form,
  setForm,
  onSubmit,
  running,
}: {
  form: AssessFormState;
  setForm: (next: AssessFormState) => void;
  onSubmit: () => void;
  running: boolean;
}) {
  const [toolDraft, setToolDraft] = useState("");

  const applyExample = (example: Example) =>
    setForm({
      ...form,
      description: example.description,
      isAgentic: example.is_agentic,
      customerFacing: example.customer_facing,
      toolsAccessible: example.tools_accessible,
      deploymentPattern: example.deployment_pattern,
    });

  const addTool = () => {
    const value = toolDraft.trim();
    if (value && !form.toolsAccessible.includes(value)) {
      setForm({ ...form, toolsAccessible: [...form.toolsAccessible, value] });
    }
    setToolDraft("");
  };

  const onKeyDown = (event: KeyboardEvent) => {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
      event.preventDefault();
      if (!running && form.description.trim()) onSubmit();
    }
  };

  const tooLong = form.description.length > MAX_CHARS;

  return (
    <Card>
      <CardContent className="space-y-5 pt-5">
        <div>
          <div className="mb-2 flex items-baseline justify-between gap-2">
            <label htmlFor="description" className="text-[13px] font-medium text-ink">
              Describe the AI use case
            </label>
            <span
              className={cn(
                "text-[11px] tabular-nums",
                tooLong ? "text-high" : "text-ink-subtle",
              )}
            >
              {form.description.length.toLocaleString("en-GB")} /{" "}
              {MAX_CHARS.toLocaleString("en-GB")}
            </span>
          </div>
          <Textarea
            id="description"
            rows={9}
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            onKeyDown={onKeyDown}
            aria-describedby="description-hint"
            placeholder="What does the system do, who uses it, what decisions does it influence, and what happens to its output? Say whether a human reviews decisions before they take effect — that changes the oversight mode, though not the inherent tier."
          />
          <p id="description-hint" className="mt-1.5 text-[12px] text-ink-muted">
            The more specific the description, the higher the confidence. Gaps are reported, not
            guessed at.
          </p>
        </div>

        <div>
          <span className="mb-2 block text-[13px] font-medium text-ink">Load an example</span>
          <div className="flex flex-wrap gap-1.5">
            {EXAMPLES.map((example) => (
              <button
                key={example.id}
                type="button"
                onClick={() => applyExample(example)}
                className="rounded-lg border border-line bg-raised px-2.5 py-1.5 text-left text-[12px] text-ink-muted transition-colors hover:border-accent-ring hover:text-ink"
              >
                <span className="block font-medium text-ink">{example.label}</span>
                <span className="block text-[11px] text-ink-subtle">{example.hint}</span>
              </button>
            ))}
          </div>
        </div>

        <fieldset>
          <legend className="mb-2 text-[13px] font-medium text-ink">Deployment pattern</legend>
          <div className="flex rounded-lg border border-line p-0.5" role="radiogroup">
            {PATTERNS.map((pattern) => (
              <button
                key={pattern.value}
                type="button"
                role="radio"
                aria-checked={form.deploymentPattern === pattern.value}
                onClick={() =>
                  setForm({
                    ...form,
                    deploymentPattern:
                      form.deploymentPattern === pattern.value ? null : pattern.value,
                  })
                }
                className={cn(
                  "flex-1 rounded-md px-2 py-1.5 text-[12px] font-medium transition-colors",
                  form.deploymentPattern === pattern.value
                    ? "bg-accent-soft text-accent"
                    : "text-ink-muted hover:text-ink",
                )}
              >
                {pattern.label}
              </button>
            ))}
          </div>
        </fieldset>

        <div className="space-y-2">
          <Toggle
            checked={form.isAgentic}
            onChange={(value) => setForm({ ...form, isAgentic: value })}
            label="Agentic system"
            description="Plans and acts through tools, rather than only producing output."
          />
          {form.isAgentic && (
            <div className="rounded-lg border border-line bg-raised p-3">
              <label htmlFor="tools" className="mb-1.5 block text-[12px] font-medium text-ink">
                Tools the system can call
              </label>
              <div className="flex gap-1.5">
                <input
                  id="tools"
                  value={toolDraft}
                  onChange={(e) => setToolDraft(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      addTool();
                    }
                  }}
                  placeholder="execute_trade"
                  className="h-8 flex-1 rounded-md border border-line-strong bg-surface px-2 text-[12px] text-ink placeholder:text-ink-subtle"
                />
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={addTool}
                  aria-label="Add tool"
                >
                  <Plus aria-hidden />
                </Button>
              </div>
              {form.toolsAccessible.length > 0 && (
                <ul className="mt-2 flex flex-wrap gap-1.5">
                  {form.toolsAccessible.map((tool) => (
                    <li key={tool}>
                      <Badge className="gap-1 pr-1 font-mono text-[11px]">
                        {tool}
                        <button
                          type="button"
                          onClick={() =>
                            setForm({
                              ...form,
                              toolsAccessible: form.toolsAccessible.filter((t) => t !== tool),
                            })
                          }
                          className="rounded p-0.5 hover:bg-line"
                          aria-label={`Remove ${tool}`}
                        >
                          <X className="size-3" aria-hidden />
                        </button>
                      </Badge>
                    </li>
                  ))}
                </ul>
              )}
              <p className="mt-2 text-[11px] leading-snug text-ink-subtle">
                Tools that spend money, message customers or write to production trigger the
                policy layer's interruption and never-delegate rules.
              </p>
            </div>
          )}
          <Toggle
            checked={form.customerFacing}
            onChange={(value) => setForm({ ...form, customerFacing: value })}
            label="Customer-facing"
            description="Customers see its output, directly or indirectly."
          />
        </div>

        <div>
          <label htmlFor="model" className="mb-1.5 block text-[13px] font-medium text-ink">
            Assessor model
          </label>
          <select
            id="model"
            value={form.model}
            onChange={(e) => setForm({ ...form, model: e.target.value })}
            className="h-9 w-full rounded-lg border border-line-strong bg-surface px-2.5 text-[13px] text-ink"
          >
            <option value="claude-sonnet-5">Claude Sonnet 5 — faster, cheaper</option>
            <option value="claude-opus-5">Claude Opus 5 — more capable</option>
          </select>
        </div>

        <div className="flex items-center gap-3 border-t border-line pt-4">
          <Button
            onClick={onSubmit}
            disabled={running || !form.description.trim() || tooLong}
            className="flex-1"
          >
            {running ? <Loader2 className="animate-spin" aria-hidden /> : <Play aria-hidden />}
            {running ? "Assessing…" : "Run assessment"}
          </Button>
          <kbd className="hidden rounded border border-line bg-raised px-1.5 py-1 font-sans text-[11px] text-ink-subtle sm:block">
            ⌘↵
          </kbd>
        </div>
      </CardContent>
    </Card>
  );
}
