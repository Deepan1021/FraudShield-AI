import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { DASHBOARD, RESULT, ROWS } from '../test/fixtures';

vi.mock('../services/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../services/api')>();
  return {
    ...actual,
    api: {
      dashboard: vi.fn(), health: vi.fn(), analyze: vi.fn(), transactions: vi.fn(), transaction: vi.fn(),
      rules: vi.fn(), seedDemo: vi.fn(),
    },
  };
});

import { api, ApiError } from '../services/api';
import { AnalysisResultPage } from './AnalysisResultPage';
import { AnalyzePage, validateForm, emptyForm, toInput, PRESETS } from './AnalyzePage';
import { DashboardPage } from './DashboardPage';
import { HistoryPage } from './HistoryPage';

const mocked = api as unknown as Record<string, ReturnType<typeof vi.fn>>;
beforeEach(() => { Object.values(mocked).forEach((m) => m.mockReset()); localStorage.clear(); });

describe('form validation', () => {
  const ok = { ...emptyForm(), ...PRESETS[3].values };
  it('accepts the critical preset', () => expect(validateForm(ok)).toEqual({}));
  it('rejects non-positive and malformed amounts', () => {
    expect(validateForm({ ...ok, amount: '0' }).amount).toBe('Transaction amount must be greater than zero.');
    expect(validateForm({ ...ok, amount: '' }).amount).toBe('Amount is required.');
    expect(validateForm({ ...ok, amount: 'abc' }).amount).toBeTruthy();
    expect(validateForm({ ...ok, amount: '-5' }).amount).toBeTruthy();
  });
  it('validates times, frequency and location', () => {
    expect(validateForm({ ...ok, transaction_time: '25:00' }).transaction_time).toBeTruthy();
    expect(validateForm({ ...ok, transaction_time: '02:15 AM' }).transaction_time).toBeUndefined();
    expect(validateForm({ ...ok, transaction_frequency: '-1' }).transaction_frequency).toBeTruthy();
    expect(validateForm({ ...ok, location: "Delhi'; DROP" }).location).toBeTruthy();
  });
  it('builds the API payload with only supplied optional fields', () => {
    const p = toInput({ ...ok, device_id: '', channel: '' });
    expect(p).toMatchObject({ amount: 85000, transaction_frequency: 12, device_trust: 'UNTRUSTED' });
    expect('device_id' in p).toBe(false);
  });
});

describe('AnalyzePage', () => {
  const renderPage = () => render(
    <MemoryRouter initialEntries={['/analyze']}>
      <Routes><Route path="/analyze" element={<AnalyzePage />} /><Route path="/analysis/:id" element={<div>RESULT PAGE</div>} /></Routes>
    </MemoryRouter>);

  it('shows field errors and does not call the API for an invalid form', async () => {
    renderPage();
    await userEvent.click(screen.getByTestId('analyze-submit'));
    expect(await screen.findByText('Amount is required.')).toBeInTheDocument();
    expect(mocked.analyze).not.toHaveBeenCalled();
  });

  it('submits a preset to the backend and navigates to the result', async () => {
    mocked.analyze.mockResolvedValue({ ...RESULT, transaction_id: 'TXNNEW1' });
    renderPage();
    await userEvent.click(screen.getByTestId('preset-critical'));
    await userEvent.click(screen.getByTestId('analyze-submit'));
    await waitFor(() => expect(mocked.analyze).toHaveBeenCalledTimes(1));
    expect(mocked.analyze.mock.calls[0][0]).toMatchObject({ amount: 85000, location: 'Delhi', login_behavior: 'SUSPICIOUS' });
    expect(await screen.findByText('RESULT PAGE')).toBeInTheDocument();
  });

  it('maps a structured server error onto the field', async () => {
    mocked.analyze.mockRejectedValue(new ApiError(422, 'VALIDATION_ERROR', 'location must be text', 'location', [{ field: 'location', message: 'location must be text' }]));
    renderPage();
    await userEvent.click(screen.getByTestId('preset-normal'));
    await userEvent.click(screen.getByTestId('analyze-submit'));
    expect((await screen.findAllByText('location must be text')).length).toBeGreaterThan(0);
    expect(screen.getByTestId('server-error')).toBeInTheDocument();
  });
});

describe('DashboardPage', () => {
  it('shows metrics from the API, the synthetic-data label and an honest empty trend', async () => {
    mocked.dashboard.mockResolvedValue(DASHBOARD);
    mocked.health.mockResolvedValue({ api: 'ONLINE', database: 'CONNECTED', rule_engine: 'READY', knowledge_base: 'LOADED', active_rules: 32, versions: { rulebase: '1.0.0' } });
    render(<MemoryRouter><DashboardPage /></MemoryRouter>);
    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(await screen.findByTestId('stat-transactions-evaluated')).toHaveTextContent('120');
    expect(screen.getByTestId('stat-critical-alerts')).toHaveTextContent('1');
    expect(screen.getByText('Synthetic Demonstration Data')).toBeInTheDocument();
    expect(screen.getByText('Not enough history for a trend')).toBeInTheDocument();
    expect(screen.getByText('TXN777')).toBeInTheDocument();
    expect(await screen.findByTestId('system-status')).toHaveTextContent('READY');
  });

  it('offers to seed demo data when empty', async () => {
    mocked.dashboard.mockResolvedValue({ ...DASHBOARD, total_transactions: 0, synthetic_transactions: 0, risk_distribution: DASHBOARD.risk_distribution.map((d) => ({ ...d, count: 0 })), recent_alerts: [] });
    mocked.health.mockResolvedValue(null);
    render(<MemoryRouter><DashboardPage /></MemoryRouter>);
    expect(await screen.findByText('No transactions have been evaluated yet')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /seed demo data/i })).toBeInTheDocument();
  });

  it('shows a retryable error when the API fails', async () => {
    mocked.dashboard.mockRejectedValue(new ApiError(0, 'NETWORK_ERROR', 'Cannot reach the FraudShield API.'));
    mocked.health.mockRejectedValue(new Error('x'));
    render(<MemoryRouter><DashboardPage /></MemoryRouter>);
    expect(await screen.findByRole('alert')).toHaveTextContent('Cannot reach the FraudShield API.');
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
  });
});

describe('HistoryPage', () => {
  it('lists transactions and sends search and risk filters to the API', async () => {
    mocked.transactions.mockResolvedValue({ items: ROWS, total: 2, page: 1, page_size: 20, pages: 1 });
    render(<MemoryRouter><HistoryPage /></MemoryRouter>);
    const table = await screen.findByTestId('history-table');
    expect(table).toHaveTextContent('TXN001');
    expect(table).toHaveTextContent('TXN002');
    await userEvent.type(screen.getByLabelText(/transaction or user id/i), 'TXN001');
    await waitFor(() => expect(mocked.transactions.mock.calls.some((c) => c[0].q === 'TXN001')).toBe(true), { timeout: 3000 });
    await userEvent.click(screen.getByTestId('filter-CRITICAL'));
    await waitFor(() => expect(mocked.transactions.mock.calls.some((c) => (c[0].risk as string[]).includes('CRITICAL'))).toBe(true));
  });

  it('shows an empty state when nothing matches', async () => {
    mocked.transactions.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20, pages: 1 });
    render(<MemoryRouter><HistoryPage /></MemoryRouter>);
    expect(await screen.findByText('No transactions match these filters')).toBeInTheDocument();
  });
});

describe('AnalysisResultPage', () => {
  it('renders the decision, drivers, rule trace and audit metadata', async () => {
    mocked.transaction.mockResolvedValue({ transaction: { status: 'BLOCKED' }, result: RESULT, audit: [] });
    render(
      <MemoryRouter initialEntries={['/analysis/TXN001']}>
        <Routes><Route path="/analysis/:id" element={<AnalysisResultPage />} /></Routes>
      </MemoryRouter>);
    const banner = await screen.findByTestId('executive-decision');
    expect(banner).toHaveTextContent('HIGH');
    expect(banner).toHaveTextContent('TXN001');
    expect(screen.getByTestId('recommendation-label')).toHaveTextContent('Temporarily block transaction');
    expect(screen.getByTestId('drivers')).toHaveTextContent('Untrusted device');
    expect(screen.getByTestId('triggered-rules')).toHaveTextContent('R30');
    expect(screen.getByTestId('audit-metadata')).toHaveTextContent('EVAL-TEST00000001');
    expect(screen.getByTestId('trace-graph')).toBeInTheDocument();
  });

  it('shows a not-found error from the API', async () => {
    mocked.transaction.mockRejectedValue(new ApiError(404, 'NOT_FOUND', 'Transaction TXN404 was not found.'));
    render(
      <MemoryRouter initialEntries={['/analysis/TXN404']}>
        <Routes><Route path="/analysis/:id" element={<AnalysisResultPage />} /></Routes>
      </MemoryRouter>);
    expect(await screen.findByRole('alert')).toHaveTextContent('TXN404 was not found');
  });
});
