import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from './components/layout/MainLayout';
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';
import DashboardPage from './pages/DashboardPage';
import ReviewPage from './pages/ReviewPage';
import DeployPage from './pages/DeployPage';
import SandboxPage from './pages/SandboxPage';
import AuditPage from './pages/AuditPage';
import BranchPage from './pages/BranchPage';
import AdminPage from './pages/AdminPage';
import SettingsPage from './pages/SettingsPage';
import GuidePage from './pages/GuidePage';

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('access_token');
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route element={<RequireAuth><MainLayout /></RequireAuth>}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/branches" element={<BranchPage />} />
          <Route path="/review" element={<ReviewPage />} />
          <Route path="/deploy" element={<DeployPage />} />
          <Route path="/sandbox" element={<SandboxPage />} />
          <Route path="/audit" element={<AuditPage />} />
          <Route path="/admin" element={<AdminPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/guide" element={<GuidePage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
