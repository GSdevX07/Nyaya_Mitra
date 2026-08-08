import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import { AppLayout } from "./layout/AppLayout";
import { Landing } from "./pages/Landing";
import { Login } from "./pages/Login";
import { CommandCenter } from "./pages/CommandCenter";
import { CaseIntelligence } from "./pages/CaseIntelligence";
import { EligibilityRadar } from "./pages/EligibilityRadar";
import { HowItWorks } from "./pages/HowItWorks";
import { FeaturesPage } from "./pages/FeaturesPage";
import { Activity, ArrowLeft } from "lucide-react";

function FeaturePlaceholder({ title }: { title: string }) {
  return (
    <div className="p-12 text-center space-y-6 max-w-lg mx-auto my-16 bg-white/[0.02] border border-white/5 rounded-2xl shadow-2xl backdrop-blur-md">
      <div className="w-14 h-14 rounded-full bg-accent/10 border border-accent/20 flex items-center justify-center mx-auto text-accent">
        <Activity className="w-7 h-7 animate-pulse" />
      </div>
      <h2 className="text-2xl font-bold text-white tracking-tight">{title} Module</h2>
      <p className="text-sm text-muted-foreground leading-relaxed">
        This legal intelligence module is currently being integrated into the Nyaya Mitra platform pipeline.
      </p>
      <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-4">
        <Link
          to="/dashboard"
          className="w-full sm:w-auto px-6 py-3 bg-white text-black font-semibold rounded-lg hover:bg-white/90 transition-colors text-sm flex items-center justify-center gap-2"
        >
          <ArrowLeft className="w-4 h-4" /> Command Center
        </Link>
        <Link
          to="/"
          className="w-full sm:w-auto px-6 py-3 bg-white/5 border border-white/10 text-white font-medium rounded-lg hover:bg-white/10 transition-colors text-sm"
        >
          Home Page
        </Link>
      </div>
    </div>
  );
}

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
          {/* Sub-routes with rich navigation back */}
          <Route path="/cases" element={<FeaturePlaceholder title="Cases Directory" />} />
          <Route path="/documents" element={<FeaturePlaceholder title="Document Vault" />} />
          <Route path="/evidence" element={<FeaturePlaceholder title="Evidence Verification" />} />
          <Route path="/actions" element={<FeaturePlaceholder title="Automated Actions" />} />
          <Route path="/hearings" element={<FeaturePlaceholder title="Court Hearings Tracker" />} />
          <Route path="/reports" element={<FeaturePlaceholder title="Legal Analytics & Reports" />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
