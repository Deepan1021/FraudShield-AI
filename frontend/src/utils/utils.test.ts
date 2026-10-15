import { cellText, formatAmount, formatMs, humanize, newTransactionId } from './format';
import { ACTION_LABEL, RISK_LEVELS, RISK_STYLE } from './risk';

describe('format utilities', () => {
  it('formats amounts in rupees', () => {
    expect(formatAmount(85000)).toContain('85,000');
  });
  it('formats durations', () => {
    expect(formatMs(0.456)).toBe('0.46 ms');
    expect(formatMs(12.34)).toBe('12.3 ms');
    expect(formatMs(null)).toBe('-');
  });
  it('humanizes enum tokens', () => {
    expect(humanize('RECENTLY_REACTIVATED')).toBe('Recently reactivated');
  });
  it('renders cell values', () => {
    expect(cellText(null)).toBe('-');
    expect(cellText(true)).toBe('Yes');
    expect(cellText(['a', 'b'])).toBe('a, b');
  });
  it('creates well-formed transaction ids', () => {
    expect(newTransactionId()).toMatch(/^TXN[A-Z0-9]+$/);
  });
});

describe('risk presentation', () => {
  it('defines exactly the four risk levels in ascending order', () => {
    expect(RISK_LEVELS).toEqual(['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']);
    expect(RISK_LEVELS.map((l) => RISK_STYLE[l].rank)).toEqual([0, 1, 2, 3]);
  });
  it('labels every recommendation action', () => {
    expect(Object.keys(ACTION_LABEL)).toEqual(['APPROVE', 'REQUEST_MFA', 'TEMPORARILY_BLOCK', 'FLAG_FOR_ANALYST_REVIEW']);
  });
});
