import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, Search } from "lucide-react";
import { api, type Framework } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { SourceChip } from "@/components/source/SourceChip";
import { cn, tierStyles } from "@/lib/utils";

type SectionId =
  | "dimensions"
  | "factors"
  | "oversight"
  | "guardrails"
  | "metrics"
  | "considerations"
  | "illustrations";

const SECTIONS: { id: SectionId; label: string; blurb: string }[] = [
  {
    id: "dimensions",
    label: "Risk dimensions",
    blurb: "Appendix B — seven dimensions and the risks under each.",
  },
  {
    id: "factors",
    label: "Materiality factors",
    blurb: "Section 2.4 — what makes a use case material.",
  },
  {
    id: "oversight",
    label: "Oversight modes",
    blurb: "Section 3.1 — how close the human stays to the decision.",
  },
  {
    id: "guardrails",
    label: "Guardrails",
    blurb: "Appendix G — the named controls this tool may recommend.",
  },
  {
    id: "metrics",
    label: "Metrics",
    blurb: "Appendix F — the named measures this tool may recommend.",
  },
  {
    id: "considerations",
    label: "Considerations",
    blurb: "Appendix H — the 17 things an FI is expected to do.",
  },
  {
    id: "illustrations",
    label: "Illustrations",
    blurb: "Worked examples contributed by member institutions.",
  },
];

export function FrameworkPage() {
  const framework = useQuery({
    queryKey: ["framework"],
    queryFn: api.framework,
    staleTime: Infinity,
  });
  const provenance = useQuery({
    queryKey: ["provenance"],
    queryFn: api.provenance,
    staleTime: Infinity,
  });
  const [section, setSection] = useState<SectionId>("dimensions");
  const [query, setQuery] = useState("");

  const counts = useMemo(() => countsOf(framework.data), [framework.data]);

  return (
    <div className="mx-auto max-w-[1400px] px-5 py-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">Framework</h2>
          <p className="mt-1 max-w-[76ch] text-[13px] text-ink-muted">
            Everything below was extracted from the handbook PDF by Claude in an offline
            ingestion run, checked by a second pass, and frozen into a versioned pack. Nothing
            here is read from the PDF at request time — but every item can show you the page it
            came from.
          </p>
        </div>
        {provenance.data && <ProvenanceBadge provenance={provenance.data} />}
      </header>

      <div className="mt-5 flex flex-wrap items-center gap-2">
        <div className="relative">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-ink-subtle" />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Filter this section…"
            aria-label="Filter the current section"
            className="h-8 w-56 rounded-lg border border-line bg-surface pl-8 pr-3 text-[13px] text-ink placeholder:text-ink-subtle"
          />
        </div>
        <div className="flex flex-wrap gap-1.5" role="tablist" aria-label="Framework section">
          {SECTIONS.map((entry) => (
            <button
              key={entry.id}
              role="tab"
              aria-selected={entry.id === section}
              onClick={() => setSection(entry.id)}
              className={cn(
                "rounded-lg border px-3 py-1.5 text-[13px] font-medium transition-colors",
                entry.id === section
                  ? "border-accent/30 bg-accent-soft text-accent"
                  : "border-line bg-surface text-ink-muted hover:bg-raised",
              )}
            >
              {entry.label}
              {counts[entry.id] != null && (
                <span className="ml-1.5 tabular-nums text-ink-subtle">{counts[entry.id]}</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {framework.isLoading && (
        <p className="mt-6 text-[13px] text-ink-subtle">Loading the pack…</p>
      )}
      {framework.error && (
        <p className="mt-6 text-[13px] text-high">Could not load the framework.</p>
      )}

      {framework.data && (
        <section className="mt-4">
          <p className="mb-3 text-[13px] text-ink-muted">
            {SECTIONS.find((entry) => entry.id === section)?.blurb}
          </p>
          <Body
            framework={framework.data}
            section={section}
            query={query.trim().toLowerCase()}
          />
        </section>
      )}
    </div>
  );
}

function countsOf(framework?: Framework): Partial<Record<SectionId, number>> {
  if (!framework) return {};
  return {
    dimensions: framework.dimensions.length,
    factors: framework.materiality.factors.length,
    oversight: framework.oversight_modes.length,
    guardrails: framework.guardrails.length,
    metrics: framework.metrics.length,
    considerations: framework.considerations.length,
    illustrations: framework.illustrations.length,
  };
}

function ProvenanceBadge({ provenance }: { provenance: Record<string, unknown> }) {
  const verification = provenance.verification as {
    quotes_checked: number;
    quotes_failed: number;
    extractors_passed: number;
    extractors_total: number;
  };
  return (
    <Card className="min-w-[260px]">
      <CardContent className="space-y-1 py-3 text-[12px]">
        <div className="flex items-center gap-1.5 text-[13px] font-medium text-ink">
          <CheckCircle2 className="size-3.5 text-low" />
          Verified pack
        </div>
        <Row
          label="Extractors passed"
          value={`${verification.extractors_passed}/${verification.extractors_total}`}
        />
        <Row label="Quotes checked" value={`${verification.quotes_checked}`} />
        <Row label="Quotes failed" value={`${verification.quotes_failed}`} />
        <Row label="Ingested by" value={String(provenance.model ?? "—")} />
        <Row
          label="Printed → PDF"
          value={`+${String(provenance.printed_to_pdf_offset ?? "—")}`}
        />
        <Row label="PDF sha256" value={String(provenance.pdf_sha256).slice(0, 12)} />
      </CardContent>
    </Card>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <span className="text-ink-muted">{label}</span>
      <span className="tabular-nums text-ink">{value}</span>
    </div>
  );
}

function matches(query: string, ...fields: (string | null | undefined)[]) {
  if (!query) return true;
  return fields.some((field) => field?.toLowerCase().includes(query));
}

function Item({
  title,
  itemId,
  page,
  meta,
  children,
}: {
  title: string;
  itemId: string;
  page?: number | null;
  meta?: React.ReactNode;
  children?: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-3">
          <CardTitle className="leading-snug">{title}</CardTitle>
          <SourceChip itemId={itemId} page={page} />
        </div>
        {meta && <div className="mt-2 flex flex-wrap gap-1.5">{meta}</div>}
      </CardHeader>
      {children && (
        <CardContent className="pt-0 text-[13px] leading-relaxed text-ink-muted">
          {children}
        </CardContent>
      )}
    </Card>
  );
}

function Body({
  framework,
  section,
  query,
}: {
  framework: Framework;
  section: SectionId;
  query: string;
}) {
  if (section === "dimensions") {
    const rows = framework.dimensions.filter((d) =>
      matches(query, d.dimension, d.definition, ...d.risks.map((r) => r.name)),
    );
    return (
      <div className="grid gap-3 lg:grid-cols-2">
        {rows.map((d) => (
          <Item key={d.item_id} title={d.dimension} itemId={d.item_id} page={d.source?.page}>
            {d.definition && <p>{d.definition}</p>}
            <ul className="mt-2 space-y-1">
              {d.risks.map((risk) => (
                <li key={risk.name} className="flex items-start gap-2">
                  <span className="mt-[7px] size-1 shrink-0 rounded-full bg-line-strong" />
                  <span className="text-ink">
                    {risk.name}
                    {risk.is_abs_top_10 && (
                      <Badge variant="accent" className="ml-1.5 align-middle">
                        ABS top 10
                      </Badge>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          </Item>
        ))}
      </div>
    );
  }

  if (section === "factors") {
    const rows = framework.materiality.factors.filter((f) =>
      matches(query, f.factor, f.description),
    );
    return (
      <div className="grid gap-3">
        {rows.map((f) => (
          <Item key={f.item_id} title={f.factor} itemId={f.item_id} page={f.source?.page}>
            {f.description && <p>{f.description}</p>}
            <dl className="mt-3 grid gap-2 sm:grid-cols-3">
              {(["low", "medium", "high"] as const).map((tier) => {
                const guidance = f[`${tier}_guidance` as const];
                if (!guidance) return null;
                return (
                  <div
                    key={tier}
                    className={cn("rounded-lg border px-3 py-2", tierStyles[tier])}
                  >
                    <dt className="text-[11px] font-semibold uppercase tracking-wide">
                      {tier}
                    </dt>
                    <dd className="mt-0.5 text-[12px] leading-relaxed opacity-90">
                      {guidance}
                    </dd>
                  </div>
                );
              })}
            </dl>
          </Item>
        ))}
      </div>
    );
  }

  if (section === "oversight") {
    const rows = framework.oversight_modes.filter((m) =>
      matches(query, m.printed_name, m.mode, m.definition),
    );
    return (
      <div className="grid gap-3 lg:grid-cols-3">
        {rows.map((m) => (
          <Item
            key={m.item_id}
            title={m.printed_name ?? m.mode}
            itemId={m.item_id}
            page={m.source?.page}
            meta={<Badge>{m.mode}</Badge>}
          >
            {m.definition && <p>{m.definition}</p>}
            {m.when_appropriate && (
              <p className="mt-2 border-l-2 border-line pl-2 text-ink-subtle">
                {m.when_appropriate}
              </p>
            )}
          </Item>
        ))}
      </div>
    );
  }

  if (section === "guardrails" || section === "metrics") {
    // Guardrails and metrics are the same table with a different prose column, so both
    // are normalised to one row shape rather than branching inside the markup.
    const rows =
      section === "guardrails"
        ? framework.guardrails
            .filter((g) => matches(query, g.name, g.description, g.dimension))
            .map((g) => ({
              item_id: g.item_id,
              name: g.name,
              dimension: g.dimension,
              text: g.description,
              page: g.source?.page,
            }))
        : framework.metrics
            .filter((m) => matches(query, m.name, m.definition, m.dimension))
            .map((m) => ({
              item_id: m.item_id,
              name: m.name,
              dimension: m.dimension,
              text: m.definition,
              page: m.source?.page,
            }));

    return (
      <div className="overflow-hidden rounded-card border border-line bg-surface">
        <table className="w-full text-[13px]">
          <thead className="border-b border-line bg-raised/60 text-[11px] uppercase tracking-wide text-ink-subtle">
            <tr>
              <th className="px-3 py-2 text-left font-medium">Name</th>
              <th className="px-3 py-2 text-left font-medium">Dimension</th>
              <th className="hidden px-3 py-2 text-left font-medium md:table-cell">
                {section === "guardrails" ? "What it does" : "What it measures"}
              </th>
              <th className="px-3 py-2 text-right font-medium">Source</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.item_id} className="border-b border-line/70 align-top last:border-0">
                <td className="px-3 py-2.5 font-medium text-ink">{row.name}</td>
                <td className="px-3 py-2.5 text-ink-muted">{row.dimension ?? "—"}</td>
                <td className="hidden max-w-[70ch] px-3 py-2.5 text-ink-muted md:table-cell">
                  {row.text}
                </td>
                <td className="px-3 py-2.5 text-right">
                  <SourceChip itemId={row.item_id} page={row.page} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  if (section === "considerations") {
    const rows = framework.considerations.filter((c) =>
      matches(query, c.title, c.handbook_section),
    );
    return (
      <div className="grid gap-3">
        {rows.map((c) => (
          <Item
            key={c.item_id}
            title={`${c.number}. ${c.title}`}
            itemId={c.item_id}
            page={c.source?.page}
            meta={c.handbook_section ? <Badge>{c.handbook_section}</Badge> : undefined}
          >
            {c.implementation_practices && c.implementation_practices.length > 0 && (
              <p className="text-ink-subtle">
                {c.implementation_practices.length} implementation practice
                {c.implementation_practices.length === 1 ? "" : "s"} recorded.
              </p>
            )}
          </Item>
        ))}
      </div>
    );
  }

  const rows = framework.illustrations.filter((i) =>
    matches(query, i.institution, i.title, i.summary, i.label),
  );
  return (
    <div className="grid gap-3 lg:grid-cols-2">
      {rows.map((i) => (
        <Item
          key={i.item_id}
          title={i.title ?? i.label}
          itemId={i.item_id}
          page={i.source?.page}
          meta={
            <>
              <Badge variant="accent">{i.institution}</Badge>
              <Badge>{i.label}</Badge>
            </>
          }
        >
          {i.summary && <p>{i.summary}</p>}
        </Item>
      ))}
    </div>
  );
}
