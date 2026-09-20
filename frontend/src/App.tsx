import { Suspense, lazy } from "react";
import { Route, Routes } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { ThemeProvider } from "@/components/layout/theme";
import { SourceProvider } from "@/components/source/SourceSheet";
import { AssessPage } from "@/pages/Assess";

// Assess is the landing route and stays in the main chunk. The others are split out:
// the Framework page pulls in the whole pack view and the Evals page its own tables,
// and neither belongs on the critical path for someone who came here to assess one
// use case.
const HistoryPage = lazy(() =>
  import("@/pages/History").then((m) => ({ default: m.HistoryPage })),
);
const EvalsPage = lazy(() => import("@/pages/Evals").then((m) => ({ default: m.EvalsPage })));
const FrameworkPage = lazy(() =>
  import("@/pages/Framework").then((m) => ({ default: m.FrameworkPage })),
);
const AboutPage = lazy(() => import("@/pages/About").then((m) => ({ default: m.AboutPage })));

function RouteFallback() {
  return <p className="px-5 py-6 text-[13px] text-ink-subtle">Loading…</p>;
}

export default function App() {
  return (
    <ThemeProvider>
      <SourceProvider>
        <AppShell>
          <Suspense fallback={<RouteFallback />}>
            <Routes>
              <Route path="/" element={<AssessPage />} />
              <Route path="/history" element={<HistoryPage />} />
              <Route path="/evals" element={<EvalsPage />} />
              <Route path="/framework" element={<FrameworkPage />} />
              <Route path="/about" element={<AboutPage />} />
            </Routes>
          </Suspense>
        </AppShell>
      </SourceProvider>
    </ThemeProvider>
  );
}
