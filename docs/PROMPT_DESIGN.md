# Prompt design

The system prompt is not a file someone wrote. It is generated from the framework pack
by `prompts/build_system_prompt.py`, and the generated text is checked in at
`prompts/system.rendered.md` so that what you diff is exactly what runs.

```bash
make prompt          # regenerate from the pack
make lint            # fails if the checked-in prompt is stale
```

## Why generate it

The prompt's job is to put the handbook's own vocabulary in front of the model: the
seven dimension names, the 38 guardrails, the 53 metrics, the 17 Considerations, the
Section 2.4 factors, the Figure 2.4.3 matrix. All of that already exists, extracted and
verified, in `framework/pack.v1.json`.

Hand-writing it would mean maintaining a second copy of the framework that silently
drifts from the first. Generating it means a re-ingestion updates the prompt, `make lint`
fails if someone forgets to regenerate, and the prompt can never name a guardrail the
pack does not have — which matters because the assessor grounds every name the model
returns against those same libraries.

## The cache is the constraint

Prompt caching bills a write at 1.25× input and a read at 0.1×. The cached prefix runs
**tools → system → messages**, so the breakpoint sits at the end of the system prompt
and covers both the tool schema and the framework prose. Everything that varies per
request — the description, the declared metadata — comes after it.

That fixes two rules the generator enforces:

1. **The prefix must be byte-stable.** Nothing per-request, no timestamps, no shuffling.
   The assessor reads the checked-in file rather than regenerating at import, so two
   processes cannot disagree about a single character and each pay for their own cache.
2. **It has a budget.** `TOKEN_BUDGET = 6000`. The rendered prompt is currently 16,843
   characters, about 5,900 tokens measured with `count_tokens`. The generator trims each
   definition to a word count rather than dropping whole sections, so the shape of the
   framework survives the budget.

A note on estimating: `CHARS_PER_TOKEN = 2.9`, not the usual 4. This text is dense with
proper nouns, slashes and parenthetical citations, and the conventional divisor was 28%
low against the real tokeniser. The generator prints both the estimate and, when an API
key is present, the exact count.

## Structure, and why it is in that order

| Section | Doing what |
| --- | --- |
| Role | Establishes inherent-not-residual, and the order of work. |
| What counts as AI (1.1) | The in-scope and out-of-scope lists verbatim, plus the `ai_type` distinction. |
| Materiality factors (2.4) | Every factor, with its handbook wording, to be rated. |
| Choosing the tier | Three tier descriptions, then the Figure 2.4.3 matrix. |
| The seven dimensions (App B) | Names for `key_risks`, and which risks are ABS top-10. |
| Oversight modes (3.1) | The three modes and the rule that high should not be out-of-the-loop. |
| Libraries you must cite from | Appendix G and F names, and the Consideration numbers. |
| Worked examples | Four calibration points. |
| Calibration | Do not inflate; confidence reflects the description. |

**The tier comes after the factors, deliberately.** The instruction says so and the tool
schema enforces it: `materiality_factors` is declared before `inherent_risk_tier`, and a
tool call is generated in field order, so the model has written out its rating of each
factor before it names a tier. The alternative — tier first, justification after — is
exactly the failure mode that makes a risk tool feel like a rubber stamp.

**The Figure 2.4.3 matrix is included even though this tool does not assess residual
risk.** It is what makes "controls do not lower the inherent tier" mean something
concrete rather than sounding like a technicality: a low-inherent use case cannot become
high however well it evaluates, and a high-inherent one stays high unless it reaches best
practice.

## The four worked examples

Few-shot examples here are calibration anchors, not format demonstrations — the schema
handles format. Each one pins a point on the scale and names the reasoning that gets you
there:

| Example | Tier | What it anchors |
| --- | --- | --- |
| Internal knowledge chatbot | low | That **low is a real answer**. Without a low anchor everything drifts up, and a tool that says "high" to everything is useless. |
| Insurance claims triage with a human decision-maker | medium | The middle of the scale, and why a human in the path bounds it. |
| Credit underwriting | high | The handbook's own example, and the explicit note that human review of declines does **not** lower the inherent tier. |
| Agentic RM assistant with trade execution | high | That agenticness, tool access and irreversibility compound. |

## What is deliberately not in the prompt

The conservative defaults — the high-risk domain floor, the agentic interruption and
never-delegate requirements, the out-of-scope short circuit — are **not** instructions.
They live in `policy.py`, in code, and run after the model answers.

A prompt instruction is a request. These rules have to hold on the runs where the model
is wrong, which is precisely when an instruction has already failed. Putting them in code
also makes them testable without an API key, and it lets the UI show "the model said X,
the policy layer said Y" instead of quietly presenting one number.

## What the schema does that the prompt cannot

- **Structured output comes from tool use**, one tool, `strict: true`, forced with
  `tool_choice`. Nothing is parsed out of free text.
- **The seven dimensions are fixed object keys, not an array.** A strict schema can
  require object keys but will not accept a `minItems` above 1, and with an array the
  model returned a single dimension in roughly a third of runs. The named risks live in a
  separate flat `key_risks` array because seven nested arrays exceed the API's compiled
  grammar limit; the assessor merges them back.
- **`temperature` does not exist here.** It returns a 400 on these models. The schema and
  forced tool choice are the only things constraining the answer's shape, which is why
  run-to-run consistency is measured rather than assumed.

## Changes are measured, not asserted

Every eval results file records the SHA-256 of the prompt that produced it, alongside the
tool schema's hash and the pack version. An old run therefore cannot be mistaken for a
current one, and a prompt change that improves one case and quietly breaks another shows
up in the next run.

One change has been made this way so far. The eval found `ai_type` coming back as
`gen_ai` for a face-matching use case on all three runs. The fix was a single sentence —
computer vision, OCR and classification models are `traditional` however severe the risk
— and the next run measured it at 100%. See [EVALS.md](EVALS.md).
