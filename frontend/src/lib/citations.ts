import { useQuery } from "@tanstack/react-query";
import { z } from "zod";
import { request } from "@/lib/api";

/** Name -> citable id, so an assessment's names can be turned back into a page
 *  reference. The assessor grounds every name against these same libraries before the
 *  response leaves the server, so an exact lookup is the right one. */
const indexSchema = z.object({
  items: z.record(z.string(), z.object({ label: z.string(), page: z.number().nullable() })),
  guardrails: z.record(z.string(), z.string()),
  metrics: z.record(z.string(), z.string()),
  dimensions: z.record(z.string(), z.string()),
  factors: z.record(z.string(), z.string()),
  oversight_modes: z.record(z.string(), z.string()),
  considerations: z.record(z.string(), z.string()),
});

export type CitationIndex = z.infer<typeof indexSchema>;

export function useCitations() {
  const { data } = useQuery({
    queryKey: ["framework", "index"],
    queryFn: () => request("/api/framework/index", indexSchema),
    staleTime: Infinity,
  });

  return {
    /** The item id for a name, or null when the pack has nothing by that name. */
    lookup(kind: keyof Omit<CitationIndex, "items">, name: string | number): string | null {
      return data?.[kind][String(name)] ?? null;
    },
    page(itemId: string | null): number | null {
      return itemId ? (data?.items[itemId]?.page ?? null) : null;
    },
    ready: data !== undefined,
  };
}
