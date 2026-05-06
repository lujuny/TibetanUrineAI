import { useEffect, useState } from "react";
import { Dashboard } from "./pages/Dashboard";
import { CaseDetailPage } from "./pages/CaseDetailPage";
import { CasesPage } from "./pages/CasesPage";
import { CapturePage } from "./pages/CapturePage";
import { PlaceholderPage } from "./pages/PlaceholderPage";

interface AppRoute {
  section: string;
  caseId?: string;
  observationId?: string;
}

function parseHash(): AppRoute {
  const hash = window.location.hash.replace(/^#/, "");
  const [section = "dashboard", caseId, observationId] = hash.split("/");
  return { section: section || "dashboard", caseId, observationId };
}

export function App() {
  const [route, setRoute] = useState<AppRoute>(() => parseHash());

  useEffect(() => {
    const handleHashChange = () => setRoute(parseHash());
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  if (route.section === "cases" && route.caseId) {
    return <CaseDetailPage caseId={route.caseId} />;
  }

  if (route.section === "cases") {
    return <CasesPage />;
  }

  if (route.section === "capture") {
    return <CapturePage caseId={route.caseId} observationId={route.observationId} />;
  }

  if (route.section === "reports") {
    return <PlaceholderPage activeRoute="reports" title="报告生成" moduleId="M08" />;
  }

  if (route.section === "knowledge") {
    return <PlaceholderPage activeRoute="knowledge" title="藏医知识库" moduleId="M06" />;
  }

  return <Dashboard />;
}
