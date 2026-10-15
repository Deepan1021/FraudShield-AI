import { Component, type ReactNode } from 'react';
import { Link, Route, Routes } from 'react-router-dom';
import { AppLayout } from './layouts/AppLayout';
import { AboutPage } from './pages/AboutPage';
import { AnalysisResultPage } from './pages/AnalysisResultPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { AnalyzePage } from './pages/AnalyzePage';
import { AuditLogsPage } from './pages/AuditLogsPage';
import { DashboardPage } from './pages/DashboardPage';
import { HistoryPage } from './pages/HistoryPage';
import { KnowledgeBasePage } from './pages/KnowledgeBasePage';
import { ReportsPage } from './pages/ReportsPage';
import { RuleExplorerPage } from './pages/RuleExplorerPage';
import { SettingsPage } from './pages/SettingsPage';
import { TransactionDetailsPage } from './pages/TransactionDetailsPage';

/** A rendering error in one page must not take the whole console down or corrupt backend state. */
class ErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null };
  static getDerivedStateFromError(error: Error) {
    return { error };
  }
  render() {
    if (this.state.error) {
      return (
        <div role="alert" className="card m-6 p-6">
          <h1 className="text-lg font-bold">Something went wrong in this view</h1>
          <p className="mt-1 text-sm text-slate-600">{this.state.error.message}</p>
          <Link className="btn-primary mt-4" to="/" onClick={() => this.setState({ error: null })}>Return to dashboard</Link>
        </div>
      );
    }
    return this.props.children;
  }
}

function NotFound() {
  return (
    <div className="card p-6">
      <h1 className="text-lg font-bold">Page not found</h1>
      <Link className="btn-primary mt-3" to="/">Go to dashboard</Link>
    </div>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="analyze" element={<AnalyzePage />} />
          <Route path="analysis/:id" element={<AnalysisResultPage />} />
          <Route path="history" element={<HistoryPage />} />
          <Route path="transactions/:id" element={<TransactionDetailsPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          <Route path="rules" element={<RuleExplorerPage />} />
          <Route path="knowledge-base" element={<KnowledgeBasePage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="audit" element={<AuditLogsPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="about" element={<AboutPage />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </ErrorBoundary>
  );
}
