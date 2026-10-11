import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ToastProvider, ConfirmProvider } from './components/ui';
import { ThemeProvider } from './contexts/ThemeContext';
import Layout from './components/layout/Layout';
import ProjectList from './pages/ProjectList';
import NewProject from './pages/NewProject';
import ProjectOverview from './pages/ProjectOverview';
import CrawlerPage from './pages/CrawlerPage';
import ImportPage from './pages/ImportPage';
import EndpointsPage from './pages/EndpointsPage';
import GraphPage from './pages/GraphPage';
import FindingsPage from './pages/FindingsPage';
import AttackPathsPage from './pages/AttackPathsPage';
import TestPlansPage from './pages/TestPlansPage';
import ReportsPage from './pages/ReportsPage';
import AIPage from './pages/AIPage';
import SettingsPage from './pages/SettingsPage';

export default function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
      <ToastProvider>
        <ConfirmProvider>
          <Routes>
            <Route element={<Layout />}>
              <Route path="/" element={<ProjectList />} />
              <Route path="/new" element={<NewProject />} />
              <Route path="/projects/:projectId" element={<ProjectOverview />} />
              <Route path="/projects/:projectId/crawl" element={<CrawlerPage />} />
              <Route path="/projects/:projectId/import" element={<ImportPage />} />
              <Route path="/projects/:projectId/endpoints" element={<EndpointsPage />} />
              <Route path="/projects/:projectId/graph" element={<GraphPage />} />
              <Route path="/projects/:projectId/findings" element={<FindingsPage />} />
              <Route path="/projects/:projectId/attack-paths" element={<AttackPathsPage />} />
              <Route path="/projects/:projectId/test-plans" element={<TestPlansPage />} />
              <Route path="/projects/:projectId/reports" element={<ReportsPage />} />
              <Route path="/projects/:projectId/ai" element={<AIPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Route>
          </Routes>
        </ConfirmProvider>
      </ToastProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}
