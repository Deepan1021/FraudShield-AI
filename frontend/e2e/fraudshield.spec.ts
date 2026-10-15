import { expect, test } from '@playwright/test';

const uid = () => 'E2E' + Date.now().toString(36).toUpperCase().slice(-6);

test.describe('FraudShield AI console', () => {
  test('dashboard loads real metrics and status', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('heading', { name: 'Risk Intelligence Dashboard' })).toBeVisible();
    await expect(page.getByTestId('stat-transactions-evaluated')).not.toHaveText('0');
    await expect(page.getByTestId('risk-distribution')).toBeVisible();
    await expect(page.getByTestId('status-bar')).toContainText('ONLINE');
    await expect(page.getByTestId('system-status')).toContainText('READY');
    await expect(page.getByText('Synthetic Demonstration Data').first()).toBeVisible();
  });

  test('critical transaction flow produces an explainable CRITICAL decision', async ({ page }) => {
    await page.goto('/analyze');
    await page.getByTestId('preset-critical').click();
    const id = uid();
    await page.getByLabel('Transaction ID').fill(id);
    await page.getByTestId('analyze-submit').click();
    await expect(page).toHaveURL(new RegExp(`/analysis/${id}`));
    await expect(page.getByTestId('executive-decision')).toContainText('CRITICAL');
    await expect(page.getByTestId('recommendation-label')).toContainText('Flag for cyber analyst review');
    await expect(page.getByTestId('drivers')).toContainText('Untrusted device');
    await expect(page.getByTestId('triggered-rules')).toContainText('R40');
    await expect(page.getByTestId('trace-graph')).toBeVisible();
    await expect(page.getByTestId('audit-metadata')).toContainText('1.0.0');
  });

  test('normal transaction is approved', async ({ page }) => {
    await page.goto('/analyze');
    await page.getByTestId('preset-normal').click();
    await page.getByLabel('Transaction ID').fill(uid());
    await page.getByTestId('analyze-submit').click();
    await expect(page.getByTestId('executive-decision')).toContainText('LOW');
    await expect(page.getByTestId('recommendation-label')).toContainText('Approve');
  });

  test('form validation blocks invalid input and the backend rejects duplicates', async ({ page }) => {
    await page.goto('/analyze');
    await page.getByTestId('preset-high').click();
    await page.getByLabel(/payment amount/i).fill('0');
    await page.getByTestId('analyze-submit').click();
    await expect(page.getByText('Transaction amount must be greater than zero.')).toBeVisible();
    await page.getByLabel(/payment amount/i).fill('85000');
    await page.getByLabel('Transaction ID').fill('TXN001'); // already seeded
    await page.getByTestId('analyze-submit').click();
    await expect(page.getByTestId('server-error')).toContainText('DUPLICATE_TRANSACTION');
  });

  test('history search and risk filter', async ({ page }) => {
    await page.goto('/history');
    await expect(page.getByTestId('history-table')).toBeVisible();
    await page.getByLabel(/transaction or user id/i).fill('TXN001');
    await expect(page.getByTestId('history-table')).toContainText('TXN001');
    await expect(page.getByTestId('history-table').locator('tbody tr')).toHaveCount(1);
    await page.getByLabel(/transaction or user id/i).fill('');
    await page.getByTestId('filter-CRITICAL').click();
    await expect(page.getByTestId('history-table')).toContainText('CRITICAL');
    await expect(page.getByTestId('history-table')).not.toContainText('LOW');
  });

  test('transaction details expose the reasoning', async ({ page }) => {
    await page.goto('/transactions/TXN001');
    await expect(page.getByRole('heading', { name: 'Transaction TXN001' })).toBeVisible();
    await page.getByRole('tab', { name: 'Reasoning' }).click();
    await expect(page.getByTestId('execution-trace')).toContainText('CriticalRisk(TXN001)');
    await page.getByRole('tab', { name: 'Audit trail' }).click();
    await expect(page.getByTestId('audit-table')).toContainText('ANALYSIS_COMPLETED');
  });

  test('rule explorer shows rule logic', async ({ page }) => {
    await page.goto('/rules');
    await page.getByRole('row', { name: /R30/ }).click();
    await expect(page.getByTestId('rule-detail')).toContainText('HighAmount(x)');
    await expect(page.getByTestId('rule-detail')).toContainText('HighRisk(x)');
  });

  test('report generation and in-app viewer', async ({ page }) => {
    await page.goto('/reports?transaction=TXN001');
    await expect(page.getByTestId('report-viewer')).toContainText('Forward-Chaining Trace');
    await page.getByLabel('Export format').selectOption('json');
    await page.getByTestId('generate-report').click();
    await expect(page.getByTestId('report-generated')).toContainText('RPT-');
    await expect(page.getByTestId('reports-table')).toContainText('TXN001');
  });

  test('audit log lists events and filters by event', async ({ page }) => {
    await page.goto('/audit');
    await expect(page.getByTestId('audit-table')).toContainText('TRANSACTION_RECEIVED');
    await page.getByLabel('Event').selectOption('HIGH_RISK_ALERT');
    await expect(page.getByTestId('audit-table')).toContainText('HIGH_RISK_ALERT');
  });

  test('analytics and knowledge base render', async ({ page }) => {
    await page.goto('/analytics');
    await expect(page.getByText('Total evaluations')).toBeVisible();
    await page.goto('/knowledge-base');
    await expect(page.getByTestId('predicates-table')).toContainText('HighAmount');
  });
});
