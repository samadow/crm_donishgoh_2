import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { LoadingPanel } from "./components/StatePanel";
import { useAuth } from "./context/AuthContext";
import { DashboardPage } from "./pages/DashboardPage";
import { JournalPage } from "./pages/JournalPage";
import { LoginPage } from "./pages/LoginPage";
import { ProfilePage } from "./pages/ProfilePage";
import { StructurePage } from "./pages/StructurePage";
import { AdmissionsPage } from "./pages/admin/AdmissionsPage";
import { SchedulePage } from "./pages/SchedulePage";
import { ExamsPage } from "./pages/ExamsPage";
import { CampusPage } from "./pages/CampusPage";
import { PlanningPage } from "./pages/admin/PlanningPage";

function ProtectedApp() {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/journal" element={<JournalPage />} />
        <Route path="/admissions" element={user.role === "admin" ? <AdmissionsPage /> : <Navigate to="/" replace />} />
        <Route path="/planning" element={user.role === "admin" ? <PlanningPage /> : <Navigate to="/" replace />} />
        <Route path="/schedule" element={<SchedulePage />} />
        <Route path="/exams" element={<ExamsPage />} />
        <Route path="/campus" element={<CampusPage />} />
        <Route path="/structure" element={user.role === "admin" ? <StructurePage /> : <Navigate to="/" replace />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
}

export default function App() {
  const { user, loading } = useAuth();
  if (loading) return <div className="boot-screen"><LoadingPanel /></div>;
  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <LoginPage />} />
      <Route path="*" element={<ProtectedApp />} />
    </Routes>
  );
}
