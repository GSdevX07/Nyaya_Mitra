import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { AppLayout } from "./layout/AppLayout";
import { Landing } from "./pages/Landing";
import { Login } from "./pages/Login";
import { CommandCenter } from "./pages/CommandCenter";
import { CaseIntelligence } from "./pages/CaseIntelligence";
import { EligibilityRadar } from "./pages/EligibilityRadar";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route element={<AppLayout />}>
          <Route path="/dashboard" element={<CommandCenter />} />
          <Route path="/case/:id" element={<CaseIntelligence />} />
          <Route path="/radar" element={<EligibilityRadar />} />
          {/* Mock routes for other links */}
          <Route path="/cases" element={<div className="p-8 text-white text-center">Cases coming soon</div>} />
          <Route path="/documents" element={<div className="p-8 text-white text-center">Documents coming soon</div>} />
          <Route path="/evidence" element={<div className="p-8 text-white text-center">Evidence coming soon</div>} />
          <Route path="/actions" element={<div className="p-8 text-white text-center">Actions coming soon</div>} />
          <Route path="/hearings" element={<div className="p-8 text-white text-center">Hearings coming soon</div>} />
          <Route path="/reports" element={<div className="p-8 text-white text-center">Reports coming soon</div>} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
