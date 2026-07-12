import { Navigate, Route, Routes } from "react-router-dom";
import { useAuthStore } from "./stores/useAuthStore";
import AppLayout from "./layouts/AppLayout";
import Landing from "./pages/Landing";
import Auth from "./pages/Auth";
import GitHubCallback from "./pages/GitHubCallback";
import Dashboard from "./pages/Dashboard";
import NewAnalysis from "./pages/NewAnalysis";
import AnalysisProgress from "./pages/AnalysisProgress";
import RepositoryReport from "./pages/RepositoryReport";

function RequireAuth({ children }: { children: JSX.Element }) {
  const token = useAuthStore((s) => s.token);
  if (!token) return <Navigate to="/auth" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/auth" element={<Auth />} />
      <Route path="/auth/github/callback" element={<GitHubCallback />} />

      <Route
        element={
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        }
      >
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/analyses/new" element={<NewAnalysis />} />
        <Route path="/analyses/:analysisId/progress" element={<AnalysisProgress />} />
        <Route path="/analyses/:analysisId/report" element={<RepositoryReport />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
