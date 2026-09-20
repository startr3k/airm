import { useCallback, useMemo, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import * as Dialog from "@radix-ui/react-dialog";
import { BookOpen, ExternalLink, Loader2, X } from "lucide-react";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { SourceContext } from "./context";

export function SourceProvider({ children }: { children: ReactNode }) {
  const [itemId, setItemId] = useState<string | null>(null);
  const open = useCallback((next: string) => setItemId(next), []);
  const value = useMemo(() => open, [open]);

  return (
    <SourceContext.Provider value={value}>
      {children}
      <SourceSheet itemId={itemId} onClose={() => setItemId(null)} />
    </SourceContext.Provider>
  );
}

function SourceSheet({ itemId, onClose }: { itemId: string | null; onClose: () => void }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["source", itemId],
    queryFn: () => api.source(itemId as string),
    enabled: itemId !== null,
    staleTime: Infinity,
  });

  return (
    <Dialog.Root open={itemId !== null} onOpenChange={(next) => !next && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-ink/25 backdrop-blur-[1px]" />
        <Dialog.Content
          className="fixed inset-y-0 right-0 z-50 flex w-full max-w-[620px] flex-col border-l border-line bg-surface shadow-xl outline-none"
          aria-describedby={undefined}
        >
          <div className="flex items-start justify-between gap-4 border-b border-line px-5 py-4">
            <div className="min-w-0">
              {/* Some labels are a whole Consideration; the full text is in the quote
                  below, so the title is clamped rather than allowed to fill the sheet. */}
              <Dialog.Title className="line-clamp-3 text-sm font-semibold tracking-tight text-ink">
                {data?.label ?? "Source"}
              </Dialog.Title>
              <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                {data?.kind && <Badge>{data.kind.replace(/_/g, " ")}</Badge>}
                {data?.section && <Badge variant="accent">{data.section}</Badge>}
                {data?.page != null && (
                  <Badge>
                    printed p.{data.page}
                    <span className="text-ink-subtle">· PDF p.{data.pdf_page}</span>
                  </Badge>
                )}
              </div>
            </div>
            <Dialog.Close
              className="rounded-md p-1 text-ink-subtle hover:bg-raised hover:text-ink"
              aria-label="Close"
            >
              <X className="size-4" />
            </Dialog.Close>
          </div>

          <div className="flex-1 overflow-y-auto px-5 py-4">
            {isLoading && (
              <p className="flex items-center gap-2 text-[13px] text-ink-muted">
                <Loader2 className="size-3.5 animate-spin" /> Looking it up…
              </p>
            )}
            {error && (
              <p className="text-[13px] text-high">This item has no recorded source.</p>
            )}

            {data?.quote && (
              <figure className="border-l-2 border-accent pl-3">
                <blockquote className="text-[13px] leading-relaxed text-ink">
                  “{data.quote}”
                </blockquote>
                <figcaption className="mt-1.5 text-[12px] text-ink-subtle">
                  Verbatim from the handbook, recorded at ingestion and checked by a second
                  pass.
                </figcaption>
              </figure>
            )}

            {data?.image_url && (
              <div className="mt-5">
                <div className="mb-2 flex items-center justify-between">
                  <h4 className="flex items-center gap-1.5 text-[12px] font-medium uppercase tracking-wide text-ink-subtle">
                    <BookOpen className="size-3.5" /> The page itself
                  </h4>
                  <a
                    href={data.image_url}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1 text-[12px] text-accent hover:underline"
                  >
                    Full size <ExternalLink className="size-3" />
                  </a>
                </div>
                <img
                  src={data.image_url}
                  alt={`Handbook printed page ${data.page}`}
                  loading="lazy"
                  className="w-full rounded-lg border border-line bg-white"
                />
                <p className="mt-2 text-[12px] text-ink-subtle">
                  Rendered from the PDF for display only. Nothing the tool asserts about the
                  handbook is read from here — that all came from the offline ingestion run.
                </p>
              </div>
            )}

            {data && !data.image_url && !isLoading && (
              <p className="mt-4 text-[13px] text-ink-muted">
                The handbook PDF is not available on this server, so the page cannot be shown.
                The citation above still comes from the framework pack.
              </p>
            )}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
