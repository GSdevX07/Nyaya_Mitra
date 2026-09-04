import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./lib/auth";
import { ProtectedRoute } from "./components/ProtectedRoute";
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
import { IngestionDashboard } from "./pages/IngestionDashboard";

import { CitizenPortal } from "./pages/CitizenPortal";
import { AdminConsole } from "./pages/AdminConsole";
import { AuditorConsole } from "./pages/AuditorConsole";
import { JailWorkspace } from "./pages/JailWorkspace";
import { AdvocateWorkspace } from "./pages/AdvocateWorkspace";
import { GovAdminOverview } from "./pages/GovAdminOverview";
import { AccusedProfilePage } from "./pages/AccusedProfilePage";
import { IdentityResolutionPage } from "./pages/IdentityResolutionPage";
import { PoliceWorkspace } from "./pages/PoliceWorkspace";
import { DocumentAssessmentPage } from "./pages/DocumentAssessmentPage";
import { LegalSourcesAdmin } from "./pages/LegalSourcesAdmin";
import { ErrorBoundary } from "./components/ErrorBoundary";

function App() {

  return (
    <ErrorBoundary fallbackTitle="Nyaya Mitra Legal Operations Portal Error">
      <AuthProvider>
        <Router>
          <Routes>
          {/* Public Unauthenticated Routes */}
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/how-it-works" element={<HowItWorks />} />
          <Route path="/features" element={<FeaturesPage />} />

          {/* Protected Institutional Routes Group */}
          <Route element={<ProtectedRoute />}>
            <Route element={<AppLayout />}>
              {/* Citizen Portal Routes (Plain-Language & Isolated) */}
              <Route
                path="/my-case"
                element={
                  <ProtectedRoute allowedRoles={["ACCUSED_USER"]}>
                    <CitizenPortal mode="accused" />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/family/status"
                element={
                  <ProtectedRoute allowedRoles={["FAMILY_GUARDIAN"]}>
                    <CitizenPortal mode="family" />
                  </ProtectedRoute>
                }
              />

              {/* Dedicated Specialized Workspaces */}
              <Route
                path="/admin"
                element={
                  <ProtectedRoute allowedRoles={["PLATFORM_ADMIN"]}>
                    <AdminConsole />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/audit"
                element={
                  <ProtectedRoute
                    allowedRoles={[
                      "READ_ONLY_AUDITOR",
                      "PLATFORM_ADMIN",
                      "GOV_ADMIN",
                      "SUPERVISING_LEGAL_OFFICER",
                    ]}
                  >
                    <AuditorConsole />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/gov"
                element={
                  <ProtectedRoute allowedRoles={["GOV_ADMIN"]}>
                    <GovAdminOverview />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/jail"
                element={
                  <ProtectedRoute
                    allowedRoles={[
                      "JAIL_OFFICER",
                    ]}
                  >
                    <JailWorkspace />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/advocate"
                element={
                  <ProtectedRoute
                    allowedRoles={[
                      "DEFENSE_ADVOCATE",
                      "CONTROLLED_EXTERNAL_ADVOCATE",
                    ]}
                  >
                    <AdvocateWorkspace />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/police"
                element={
                  <ProtectedRoute
                    allowedRoles={[
                      "POLICE_OFFICER",
                    ]}
                  >
                    <PoliceWorkspace />
                  </ProtectedRoute>
                }
              />

              {/* Institutional Core Modules */}
              <Route
                path="/dashboard"
                element={
                  <ProtectedRoute
                    allowedRoles={[
                      "DLSA_OFFICER",
                      "SUPERVISING_LEGAL_OFFICER",
                      "PLATFORM_ADMIN",
                      "GOV_ADMIN",
                    ]}
                  >
                    <CommandCenter />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/case/:id"
                element={
                  <ProtectedRoute
                    allowedRoles={[
                      "DLSA_OFFICER",
                      "SUPERVISING_LEGAL_OFFICER",
                      "PLATFORM_ADMIN",
                      "GOV_ADMIN",
                      "JAIL_OFFICER",
                      "POLICE_OFFICER",
                      "DEFENSE_ADVOCATE",
                      "CONTROLLED_EXTERNAL_ADVOCATE",
                      "READ_ONLY_AUDITOR",
                    ]}
                  >
                    <CaseIntelligence />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/cases/:id"
                element={
                  <ProtectedRoute
                    allowedRoles={[
                      "DLSA_OFFICER",
                      "SUPERVISING_LEGAL_OFFICER",
                      "PLATFORM_ADMIN",
                      "GOV_ADMIN",
                      "JAIL_OFFICER",
                      "POLICE_OFFICER",
                      "DEFENSE_ADVOCATE",
                      "CONTROLLED_EXTERNAL_ADVOCATE",
                      "READ_ONLY_AUDITOR",
                    ]}
                  >
                    <CaseIntelligence />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/accused/:id"
                element={
                  <ProtectedRoute
                    allowedRoles={[
                      "DLSA_OFFICER",
                      "SUPERVISING_LEGAL_OFFICER",
                      "PLATFORM_ADMIN",
                      "GOV_ADMIN",
                      "JAIL_OFFICER",
                      "POLICE_OFFICER",
                      "DEFENSE_ADVOCATE",
                      "CONTROLLED_EXTERNAL_ADVOCATE",
                      "READ_ONLY_AUDITOR",
                    ]}
                  >
                    <AccusedProfilePage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/identity-review"
                element={
                  <ProtectedRoute
                    allowedRoles={[
                      "SUPERVISING_LEGAL_OFFICER",
                      "GOV_ADMIN",
                      "PLATFORM_ADMIN",
                      "DLSA_OFFICER",
                    ]}
                  >
                    <IdentityResolutionPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/legal-sources"
                element={
                  <ProtectedRoute
                    allowedRoles={[
                      "GOV_ADMIN",
                      "SUPERVISING_LEGAL_OFFICER",
                      "DLSA_OFFICER",
                      "DEFENSE_ADVOCATE",
                      "CONTROLLED_EXTERNAL_ADVOCATE",
                      "READ_ONLY_AUDITOR",
                    ]}
                  >
                    <LegalSourcesAdmin />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/radar"

                element={
                  <ProtectedRoute
                    allowedRoles={[
                      "DLSA_OFFICER",
                      "SUPERVISING_LEGAL_OFFICER",
                      "PLATFORM_ADMIN",
                      "GOV_ADMIN",
                      "DEFENSE_ADVOCATE",
                    ]}
                  >
                    <EligibilityRadar />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/cases"
                element={
                  <ProtectedRoute
                    allowedRoles={[
                      "DLSA_OFFICER",
                      "SUPERVISING_LEGAL_OFFICER",
                      "PLATFORM_ADMIN",
                      "GOV_ADMIN",
                      "JAIL_OFFICER",
                      "POLICE_OFFICER",
                      "READ_ONLY_AUDITOR",
                    ]}
                  >
                    <CasesPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/documents"
                element={
                  <ProtectedRoute
                    allowedRoles={[
                      "DLSA_OFFICER",
                      "SUPERVISING_LEGAL_OFFICER",
                      "PLATFORM_ADMIN",
                      "GOV_ADMIN",
                      "JAIL_OFFICER",
                      "POLICE_OFFICER",
                      "DEFENSE_ADVOCATE",
                      "CONTROLLED_EXTERNAL_ADVOCATE",
                      "READ_ONLY_AUDITOR",
                    ]}
                  >
                    <DocumentsPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/document-assessment"
                element={
                  <ProtectedRoute
                    allowedRoles={[
                      "PLATFORM_ADMIN",
                    ]}
                  >
                    <DocumentAssessmentPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/evidence"
                element={
                  <ProtectedRoute
                    allowedRoles={[
                      "DLSA_OFFICER",
                      "SUPERVISING_LEGAL_OFFICER",
                      "PLATFORM_ADMIN",
                      "GOV_ADMIN",
                      "READ_ONLY_AUDITOR",
                    ]}
                  >
                    <EvidencePage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/actions"
                element={
                  <ProtectedRoute
                    allowedRoles={[
                      "DLSA_OFFICER",
                      "SUPERVISING_LEGAL_OFFICER",
                      "DEFENSE_ADVOCATE",
                    ]}
                  >
                    <ActionsPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/hearings"
                element={
                  <ProtectedRoute
                    allowedRoles={[
                      "DLSA_OFFICER",
                      "SUPERVISING_LEGAL_OFFICER",
                      "PLATFORM_ADMIN",
                      "GOV_ADMIN",
                      "DEFENSE_ADVOCATE",
                      "CONTROLLED_EXTERNAL_ADVOCATE",
                      "JAIL_OFFICER",
                      "POLICE_OFFICER",
                    ]}
                  >
                    <HearingsPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/reports"
                element={
                  <ProtectedRoute
                    allowedRoles={[
                      "DLSA_OFFICER",
                      "SUPERVISING_LEGAL_OFFICER",
                      "GOV_ADMIN",
                      "READ_ONLY_AUDITOR",
                    ]}
                  >
                    <ReportsPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/ingestion"
                element={
                  <ProtectedRoute
                    allowedRoles={[
                      "PLATFORM_ADMIN",
                    ]}
                  >
                    <IngestionDashboard />
                  </ProtectedRoute>
                }
              />
            </Route>
          </Route>
        </Routes>
      </Router>
    </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;
