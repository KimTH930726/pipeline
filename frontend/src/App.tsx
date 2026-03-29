import { BrowserRouter, Routes, Route } from 'react-router-dom';
import MainLayout from './components/layout/MainLayout';
import DashboardPage from './pages/DashboardPage';
import ReviewPage from './pages/ReviewPage';
import DeployPage from './pages/DeployPage';
import SandboxPage from './pages/SandboxPage';
import AuditPage from './pages/AuditPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<MainLayout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/review" element={<ReviewPage />} />
          <Route path="/deploy" element={<DeployPage />} />
          <Route path="/sandbox" element={<SandboxPage />} />
          <Route path="/audit" element={<AuditPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
