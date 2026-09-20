import { FileText } from "lucide-react";
import { useSource } from "./context";
import { cn } from "@/lib/utils";

/** A citation you can actually follow: opens the page it came from. */
export function SourceChip({
  itemId,
  page,
  className,
  label,
}: {
  itemId: string;
  page?: number | null;
  className?: string;
  label?: string;
}) {
  const open = useSource();
  return (
    <button
      type="button"
      onClick={(event) => {
        event.stopPropagation();
        open(itemId);
      }}
      title="Show the handbook page this came from"
      className={cn(
        "inline-flex shrink-0 items-center gap-1 rounded-md border border-line px-1.5 py-0.5 text-[11px] font-medium text-ink-subtle transition-colors hover:border-accent/30 hover:bg-accent-soft hover:text-accent",
        className,
      )}
    >
      <FileText className="size-3" />
      {label ?? (page != null ? `p.${page}` : "source")}
    </button>
  );
}
