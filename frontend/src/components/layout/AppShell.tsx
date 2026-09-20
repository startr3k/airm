import { NavLink, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  BookOpen,
  ClipboardCheck,
  FlaskConical,
  History,
  Info,
  Moon,
  ShieldCheck,
  Sun,
} from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useTheme } from "./theme";

const NAV = [
  { to: "/", label: "Assess", icon: ClipboardCheck, end: true },
  { to: "/history", label: "History", icon: History },
  { to: "/evals", label: "Evals", icon: FlaskConical },
  { to: "/framework", label: "Framework", icon: BookOpen },
  { to: "/about", label: "About", icon: Info },
];

/**
 * The shell owns the viewport: the sidebar and the main region scroll independently,
 * so a long result never pushes the nav or the input panel off screen.
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  const { theme, toggle } = useTheme();
  const location = useLocation();
  const { data: health } = useQuery({ queryKey: ["health"], queryFn: api.health });

  const keyMissing = health && !health.api_key_present;

  return (
    <div className="flex h-dvh flex-col overflow-hidden bg-canvas">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-surface focus:px-3 focus:py-2 focus:text-sm"
      >
        Skip to content
      </a>

      <div className="flex min-h-0 flex-1">
        <aside className="hidden h-full w-56 shrink-0 overflow-y-auto border-r border-line bg-surface md:flex md:flex-col print:hidden">
          <div className="flex h-14 items-center gap-2 border-b border-line px-5">
            <ShieldCheck className="size-5 text-accent" aria-hidden />
            <span className="text-[13px] font-semibold tracking-tight">MindForge</span>
          </div>
          <nav className="flex flex-col gap-0.5 p-3" aria-label="Main">
            {NAV.map(({ to, label, icon: Icon, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] font-medium transition-colors",
                    isActive
                      ? "bg-accent-soft text-accent"
                      : "text-ink-muted hover:bg-raised hover:text-ink",
                  )
                }
              >
                <Icon className="size-4" aria-hidden />
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="mt-auto border-t border-line p-4">
            <p className="text-[11px] leading-relaxed text-ink-subtle">
              Inherent risk only. Residual risk needs real evaluation evidence.
            </p>
          </div>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
          <header className="z-30 flex h-14 shrink-0 items-center gap-3 border-b border-line bg-surface px-5 print:hidden">
            <ShieldCheck className="size-5 text-accent md:hidden" aria-hidden />
            <h1 className="text-sm font-semibold tracking-tight">MindForge Risk Assessor</h1>
            <div className="ml-auto flex items-center gap-2">
              {health?.assess_model && (
                <Badge variant="accent" title="Assessor model">
                  {health.assess_model}
                </Badge>
              )}
              {health?.pack_version != null && (
                <Badge
                  title={`Framework pack v${health.pack_version}`}
                  className="hidden sm:inline-flex"
                >
                  pack v{health.pack_version}
                </Badge>
              )}
              <Button
                variant="ghost"
                size="icon"
                onClick={toggle}
                aria-label={`Switch to ${theme === "light" ? "dark" : "light"} theme`}
              >
                {theme === "light" ? <Moon aria-hidden /> : <Sun aria-hidden />}
              </Button>
            </div>
          </header>

          {keyMissing && (
            <div
              role="alert"
              className="flex shrink-0 items-center gap-2 border-b border-medium-line bg-medium-soft px-5 py-2.5 text-[13px] text-medium"
            >
              <AlertTriangle className="size-4 shrink-0" aria-hidden />
              <span>
                <strong className="font-semibold">No API key.</strong> Set{" "}
                <code className="rounded bg-medium-line/40 px-1 py-0.5 text-[12px]">
                  ANTHROPIC_API_KEY
                </code>{" "}
                in{" "}
                <code className="rounded bg-medium-line/40 px-1 py-0.5 text-[12px]">
                  backend/.env
                </code>{" "}
                — assessments will fail until you do.
              </span>
            </div>
          )}

          <nav
            className="flex shrink-0 gap-1 overflow-x-auto border-b border-line bg-surface px-3 py-2 md:hidden"
            aria-label="Main"
          >
            {NAV.map(({ to, label, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  cn(
                    "rounded-lg px-3 py-1.5 text-[13px] font-medium whitespace-nowrap",
                    isActive ? "bg-accent-soft text-accent" : "text-ink-muted",
                  )
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>

          <main
            id="main"
            key={location.pathname}
            className="min-h-0 min-w-0 flex-1 overflow-y-auto"
          >
            {children}
          </main>
        </div>
      </div>
    </div>
  );
}
