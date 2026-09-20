import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-[12px] font-medium",
  {
    variants: {
      variant: {
        default: "border-line bg-raised text-ink-muted",
        accent: "border-accent/25 bg-accent-soft text-accent",
        low: "border-low-line bg-low-soft text-low",
        medium: "border-medium-line bg-medium-soft text-medium",
        high: "border-high-line bg-high-soft text-high",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

export function Badge({
  className,
  variant,
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
