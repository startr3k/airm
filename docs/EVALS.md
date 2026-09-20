# How the assessor is evaluated

The hard part of this tool is not calling the model. It is knowing whether the answer is
any good, on a framework where "good" is partly a matter of judgement. This is how that
question is made answerable.

## What is graded, and what is not

`backend/evals/gold.jsonl` holds ten hand-written use cases. Each one carries an
`expect` block, and **every key in it is optional**. A case grades only the things the
handbook settles:

| Graded | Why it can be graded |
| --- | --- |
| `ai_in_scope` | Section 1.1 draws a hard line: learns or infers, versus predefined logic. |
| `ai_type` | Three named categories. |
| `inherent_risk_tier` | Section 2.4 plus the worked examples the handbook itself gives. |
| `recommended_oversight_mode` | Section 3.1; a set of acceptable modes, not one. |
| `confidence` | Capped, not fixed: a one-line description cannot support high confidence. |
| dimension floors | "Fairness & Bias must be at least high for a credit model" is defensible; "exactly medium for Ethics" is not. |
| ABS top-10 risks | Named risks from the taxonomy — recall, not precision. |
| Appendix H Considerations | Numbered and finite. |
| policy rules that must fire | Deterministic code, so this is a property of the system, not the model. |

Nobody can write the one true list of guardrails for a use case, so `recommended_guardrails`,
`recommended_metrics`, all the rationales and the notes are **not graded**. Scoring them
against one analyst's opinion would produce a confident number that means nothing.

Expectations that are absent produce no check at all, rather than a silent pass. Adding a
new expectation to one case therefore never changes the other nine.

## The gold set is validated against the pack

`validate_gold()` checks every dimension name, Consideration number, ABS top-10 risk name
and oversight mode in the gold set against `framework/pack.v1.json`. A typo like
`"Fairness and Bias"` (the pack uses `&`) would otherwise score zero forever without
anyone noticing. This runs in `make lint`, in `make evals-check` and in the test suite,
none of which touch the API.

## Accuracy and consistency are measured separately

These models reject `temperature`, so there is no knob to pin the output. Run-to-run
variance is a real property of the system and the only honest way to handle it is to
measure it: every case runs **N=3** times and the report gives both

* **accuracy** — did a run get a field right, and
* **tier consistency** — did the three runs of a case agree *with each other*.

A run can be perfectly consistent and consistently wrong; the report never collapses the
two into one number.

## The model's own tier is kept separate from the policy layer's

The policy layer floors the tier at `high` for credit, insurance underwriting,
employment, biometrics and autonomous transactions. If the report only showed the final
tier, those cases would score 100% regardless of what the model said — which would make
the eval useless exactly where the stakes are highest.

Every override records its `before` value, so the harness recovers the model's own answer
and reports both. The "Model alone" column on the Evals page is that number.

## The cases

Four are ordinary. Six are chosen to break something:

| Case | What it is designed to catch |
| --- | --- |
| `rpa-invoice-reconciliation` | Sold internally as "AI-powered", mechanically a spreadsheet of rules. Reading the label instead of the mechanism fails. |
| `underspecified-login-invoice` | One sentence. Claiming high confidence from it is a calibration failure, not a tier failure. |
| `cv-screening-shortlist` | Deliberately downplayed ("never rejects anyone outright"). The employment floor must hold the final tier at high. |
| `vendor-procurement-copilot` | Third-party AI the firm cannot see inside. Opacity must not read as low risk, and Considerations 4 and 10 are the discriminator. |
| `agentic-rm-assistant` | Tool access compounds: trades settle, emails cannot be unsent. |
| `autonomous-refund-chatbot` | Customer-facing, moves money, no human. Oversight must not come back as out-of-the-loop. |

The other four (`internal-policy-rag`, `credit-underwriting`, `biometric-onboarding`,
`marketing-copy-generator`) pin the low, high and middle of the scale so the tool cannot
score well by inflating everything.

## Running it

```bash
make evals                      # Sonnet 5, 10 cases x 3 runs
make evals MODEL=claude-opus-5  # the same set on Opus 5
make evals-check                # validate the gold set; no API calls
python backend/evals/run_evals.py --case credit-underwriting -n 1   # one case
```

Results land in `backend/evals/results/<model>/<timestamp>.json` with a Markdown summary
beside them, and `results/comparison.md` is rewritten after every run. Each results file
records the model, the pack version and the SHA-256 of the system prompt that produced
it, so an old run can never be mistaken for a current one.

Transient upstream 5xx responses are retried with backoff (four attempts). A call that
still fails is recorded as an **error** against that run, never scored as a wrong answer.

## What it has caught

The harness paid for itself on its first run. Three defects, none of which showed up in
manual testing:

**1. Six of the seven risk dimensions going missing.** Dimension-floor recall came back
at 46%, with "got absent" against dimension after dimension. The cause: `risk_dimensions`
was an array, and in roughly a third of runs the model emitted a single element and
closed it. A strict schema cannot forbid that — the API rejects a `minItems` above 1
("For 'array' type, 'minItems' values other than 0 or 1 are not supported"). The fix was
to make the seven dimensions **fixed object keys**, which `required` *can* enforce, so
the decoding grammar has no way to emit fewer than seven.

That change alone would not compile: seven copies of a nested array pushed the request
past "The compiled grammar is too large". So the named risks moved into one flat
`key_risks` array, and the assessor merges the two halves back into the shape the rest of
the app already used. Nothing downstream of `assessor.py` knows about the split.

**2. Truncated answers being read as valid ones.** Two runs failed schema validation with
`top_10_flags` arriving as the string `'["'` and every later field missing. Every request
here is streamed, and a streamed tool input is reassembled client-side by a *tolerant*
JSON parser — so a response cut off at `max_tokens` does not raise, it returns a
plausible dict. The streaming endpoint already checked `stop_reason`; the plain one did
not. It does now, `max_tokens` went from 16k to 32k (adaptive thinking is billed from the
same budget), and a truncated run is retried.

**3. Computer vision being classified as generative AI.** `ai_type` came back as `gen_ai`
for the face-matching case on all three runs. One clarifying sentence in the system
prompt — classification and vision models are `traditional` however severe the risk —
fixed it without touching anything else.

A fourth finding needed no fix, only honesty: on the deliberately vague
`underspecified-login-invoice` case the tier moves between runs. That is what a
one-sentence description deserves, and it is why consistency is reported separately.

## Where it stands

Both models, the same ten cases, three runs each, `effort=medium`, pack v1.

| | `claude-sonnet-5` | `claude-opus-5` |
| --- | --- | --- |
| Overall check accuracy | **99.4%** (168 assertions) | 97.6% |
| Inherent tier exactly right | 96% | 93% |
| Tier within tolerance | 100% | 93% |
| Scope, AI type, oversight mode | 100% each | 100% each |
| Dimension floors met | 100% (57/57) | 100% (57/57) |
| ABS top-10 recall | 90% | 100% |
| Consideration recall | 93% | 96% |
| Run-to-run tier agreement | 97% (9/10 unanimous) | 97% (9/10 unanimous) |
| Median latency | 31.9s (p95 46.0s) | 43.0s (p95 63.8s) |
| Cost per assessment | $0.032 | $0.105 |
| Runs with no answer | 0 of 30 (5 retried) | 0 of 30 |

Sonnet 5 is the better choice here, and not marginally: it is more accurate on the field
that matters most, a third of the cost and a third faster. Opus's two losses are both the
same case — it rates the one-sentence `underspecified-login-invoice` as **high** in two of
three runs, which is over-caution rather than a misreading, and exactly the behaviour
that makes a triage tool useless. Opus is better at naming risks (top-10 recall 100% vs
90%), so the gap is about calibration, not comprehension.

The one case neither model gets consistently right is the vague one. That is the honest
answer: three sentences of context cannot settle a tier, and the tool says so through a
capped `confidence` rather than by guessing well.

## Cost

Each assessment is one request against a cached ~6k-token system prompt. The first call
of a run writes the cache and the rest read it, which is why the harness runs the first
case alone before parallelising: firing everything off cold would have every worker write
its own cache entry, inflating both the bill and the cache-hit number.
