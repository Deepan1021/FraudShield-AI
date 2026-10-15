import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { GRAPH, RESULT } from '../test/fixtures';
import { RiskBadge } from './RiskBadge';
import { DriversPanel, ExecutionTable, RecommendationCard, TriggeredRulesTable } from './ResultPanels';
import { TraceGraph } from './TraceGraph';

describe('RiskBadge', () => {
  it.each(['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'] as const)('shows the %s label as text (not colour alone)', (level) => {
    render(<RiskBadge level={level} />);
    expect(screen.getByTestId(`risk-badge-${level}`)).toHaveTextContent(level);
  });
  it('renders a dash when there is no level', () => {
    render(<RiskBadge level={null} />);
    expect(screen.getByText('-')).toBeInTheDocument();
  });
});

describe('result panels', () => {
  it('lists the real drivers from the explanation', () => {
    render(<DriversPanel explanation={RESULT.explanation} />);
    const list = screen.getByTestId('drivers');
    expect(list).toHaveTextContent('High-value transaction');
    expect(list).toHaveTextContent('UntrustedDevice(TXN001)');
  });
  it('shows an empty state when no driver exists', () => {
    render(<DriversPanel explanation={{ ...RESULT.explanation, drivers: [] }} />);
    expect(screen.getByText('No risk drivers')).toBeInTheDocument();
  });
  it('renders the recommendation', () => {
    render(<RecommendationCard rec={RESULT.recommendation} status="BLOCKED" />);
    expect(screen.getByTestId('recommendation-label')).toHaveTextContent('Temporarily block transaction');
    expect(screen.getByTestId('recommendation')).toHaveTextContent('Blocked');
  });
  it('renders triggered rules and the execution trace', () => {
    render(<MemoryRouter><TriggeredRulesTable rules={RESULT.triggered_rules} /><ExecutionTable executions={RESULT.reasoning_trace} /></MemoryRouter>);
    expect(screen.getByTestId('triggered-rules')).toHaveTextContent('R30');
    expect(screen.getByTestId('execution-trace')).toHaveTextContent('UnverifiedDevice(TXN001)');
  });
});

describe('TraceGraph', () => {
  it('draws decisive nodes only by default and all nodes when toggled', async () => {
    render(<TraceGraph graph={GRAPH} />);
    expect(screen.getByTestId('graph-node-R30@2')).toBeInTheDocument();
    expect(screen.queryByTestId('graph-node-NewLocation(TXN001)')).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('checkbox'));
    expect(screen.getByTestId('graph-node-NewLocation(TXN001)')).toBeInTheDocument();
  });
  it('lets a node be selected with the keyboard', async () => {
    render(<TraceGraph graph={GRAPH} />);
    const node = screen.getByTestId('graph-node-R01@1');
    node.focus();
    await userEvent.keyboard('{Enter}');
    expect(node).toHaveAttribute('aria-pressed', 'true');
  });
});
