import { useQuery } from "@tanstack/react-query";
import { ArrowRight, FileCheck2, FlaskConical, Shield } from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export function AboutPage() {
  const health = useQuery({ queryKey: ["health"], queryFn: api.health });
  const provenance = useQuery({
    queryKey: ["provenance"],
    queryFn: api.provenance,
    staleTime: Infinity,
  });
  const verification = provenance.data?.verification as
    | {
        quotes_checked: number;
        quotes_failed: number;
        extractors_passed: number;
        extractors_total: number;
      }
    | undefined;

  return (
    <div className="mx-auto max-w-[900px] px-5 py-6">
      <h2 className="text-lg font-semibold tracking-tight">About this tool</h2>
      <p className="mt-1 text-[13px] text-ink-muted">
        A risk materiality assessor for the MindForge AI Risk Management Operationalisation
        Handbook (January 2026). It reads a described AI use case and classifies it against the
        framework.
      </p>

      <Section
        icon={<Shield className="size-4 text-accent" />}
        title="What it assesses, and what it does not"
      >
        <p>
          This tool assesses <strong className="text-ink">inherent</strong> risk materiality:
          the risk a use case carries before controls. It deliberately does not lower a rating
          because a control was described. Under Figure 2.4.3 controls bear on <em>residual</em>{" "}
          risk, and residual risk needs real evaluation evidence — test results, monitoring
          data, review findings — which a paragraph of description cannot provide.
        </p>
        <p>
          It is a triage aid for a human reviewer, not a decision. Every answer names what the
          description failed to say rather than guessing, and every citation can be opened to
          the handbook page it came from.
        </p>
      </Section>

      <Section
        icon={<FileCheck2 className="size-4 text-accent" />}
        title="How the handbook got in here"
      >
        <p>
          The handbook exists only as a 166-page PDF. Nothing local parses it: no pdftotext, no
          PyMuPDF, no OCR. Claude reads the PDF itself through the Files API, and the whole
          pipeline runs <strong className="text-ink">offline</strong>, before the app ever
          starts.
        </p>
        <ol className="ml-4 list-decimal space-y-1.5">
          <li>
            <strong className="text-ink">Calibrate.</strong> The page numbers printed on the
            page differ from the PDF's own indices. A first pass reads the contents and footers
            and derives the offset — here a constant{" "}
            <Badge>+{String(provenance.data?.printed_to_pdf_offset ?? "?")}</Badge> — then
            confirms it against known anchors.
          </li>
          <li>
            <strong className="text-ink">Extract.</strong> Nine extractors pull the definitions,
            materiality factors, risk taxonomy, oversight modes, metrics, guardrails,
            Considerations, agentic guidance and worked illustrations. Every item carries a{" "}
            <code className="text-ink">source</code> with the <em>printed</em> page, the section
            and a verbatim quote.
          </li>
          <li>
            <strong className="text-ink">Verify.</strong> A second pass re-reads the same pages
            and checks each quote against them. Ingestion fails if an appendix table came back
            shorter than the verifier counted, which is how silently dropped rows get caught.
          </li>
          <li>
            <strong className="text-ink">Freeze.</strong> The result is a versioned pack with a
            provenance block. The assessor, this page and every API response read the pack —
            never the PDF.
          </li>
        </ol>
        {verification && (
          <div className="grid gap-2 sm:grid-cols-3">
            <Stat
              value={`${verification.extractors_passed}/${verification.extractors_total}`}
              label="extractors verified"
            />
            <Stat value={String(verification.quotes_checked)} label="quotes re-checked" />
            <Stat value={String(verification.quotes_failed)} label="quotes failed" />
          </div>
        )}
      </Section>

      <Section
        icon={<ArrowRight className="size-4 text-accent" />}
        title="What happens when you press Run"
      >
        <p>
          One request to Claude, forced to answer by calling a single tool with a strict schema.
          The answer is never parsed out of free text. The ~6k-token system prompt is generated
          from the pack and cached, so every request after the first reads it at a tenth of the
          price.
        </p>
        <p>
          The schema's field order is deliberate: materiality factors are rated <em>before</em>{" "}
          the tier is chosen, so the tier follows from the factors rather than being picked
          first and justified afterwards. The seven risk dimensions are fixed object keys rather
          than a list, because a strict schema can require keys but cannot require a list to
          have seven entries — with a list, the model returned one dimension in about a third of
          runs.
        </p>
        <p>
          Then a deterministic policy layer runs <strong className="text-ink">in code</strong>.
          It floors inherent risk at high for credit, insurance underwriting, employment,
          biometrics and autonomous transactions; it requires interruption controls and
          never-delegate boundaries for agents with consequential tools; and it withholds the
          risk analysis entirely for systems that are not AI under Section 1.1. Every adjustment
          is shown as "the model said X, the policy layer said Y" rather than applied silently.
        </p>
      </Section>

      <Section
        icon={<FlaskConical className="size-4 text-accent" />}
        title="How it is known to work"
      >
        <p>
          Ten hand-written use cases, each run three times, graded only on what the handbook
          settles — scope, type, tier, oversight mode, and whether the risks and Considerations
          that apply were cited. Judgement calls are left ungraded rather than scored against
          one analyst's opinion. Accuracy and run-to-run consistency are reported separately,
          because these models reject a <code className="text-ink">temperature</code> setting
          and variance is a real property of the system.
        </p>
        <p>
          The eval found three defects on its first run that manual testing had not: dimensions
          silently collapsing to one, responses truncated at{" "}
          <code className="text-ink">max_tokens</code> being read as valid, and computer vision
          classified as generative AI. See the Evals page for current numbers.
        </p>
      </Section>

      <Card className="mt-5">
        <CardHeader>
          <CardTitle>This instance</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-1.5 text-[13px] sm:grid-cols-2">
          <Row label="Assessor model" value={health.data?.assess_model ?? "—"} />
          <Row label="Framework pack" value={`v${health.data?.pack_version ?? "—"}`} />
          <Row label="Ingested by" value={String(provenance.data?.model ?? "—")} />
          <Row
            label="Ingested at"
            value={
              provenance.data?.extracted_at
                ? new Date(String(provenance.data.extracted_at)).toLocaleDateString("en-GB")
                : "—"
            }
          />
          <Row
            label="Handbook sha256"
            value={String(health.data?.pdf_sha256 ?? "—").slice(0, 16)}
          />
          <Row label="API key present" value={health.data?.api_key_present ? "yes" : "no"} />
        </CardContent>
      </Card>
    </div>
  );
}

function Section({
  icon,
  title,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="mt-6">
      <h3 className="flex items-center gap-2 text-sm font-semibold tracking-tight text-ink">
        {icon}
        {title}
      </h3>
      <div className="mt-2 space-y-3 text-[13px] leading-relaxed text-ink-muted">
        {children}
      </div>
    </section>
  );
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div className="rounded-lg border border-line bg-surface px-3 py-2">
      <div className="text-lg font-semibold tabular-nums text-ink">{value}</div>
      <div className="text-[12px] text-ink-subtle">{label}</div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-line/60 pb-1 last:border-0">
      <span className="text-ink-muted">{label}</span>
      <span className="tabular-nums text-ink">{value}</span>
    </div>
  );
}
