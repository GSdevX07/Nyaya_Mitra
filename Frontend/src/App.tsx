import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { AppLayout } from "./layout/AppLayout";
import { Landing } from "./pages/Landing";
import { Login } from "./pages/Login";
import { CommandCenter } from "./pages/CommandCenter";
import { CaseIntelligence } from "./pages/CaseIntelligence";
import { EligibilityRadar } from "./pages/EligibilityRadar";
import { HowItWorks } from "./pages/HowItWorks";
import { FeaturesPage } from "./pages/FeaturesPage";

import { CasesPage } from "./pages/CasesPage";
import { DocumentsPage } from "./pages/DocumentsPage";
import { EvidencePage } from "./pages/EvidencePage";
import { ActionsPage } from "./pages/ActionsPage";
import { HearingsPage } from "./pages/HearingsPage";
import { ReportsPage } from "./pages/ReportsPage";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/how-it-works" element={<HowItWorks />} />
        <Route path="/features" element={<FeaturesPage />} />
        <Route element={<AppLayout />}>
          <Route path="/dashboard" element={<CommandCenter />} />
          <Route path="/case/:id" element={<CaseIntelligence />} />
          <Route path="/radar" element={<EligibilityRadar />} />
          {/* Sub-routes with rich dedicated pages */}
          <Route path="/cases" element={<CasesPage />} />
          <Route path="/documents" element={<DocumentsPage />} />
          <Route path="/evidence" element={<EvidencePage />} />
          <Route path="/actions" element={<ActionsPage />} />
          <Route path="/hearings" element={<HearingsPage />} />
          <Route path="/reports" element={<ReportsPage />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
