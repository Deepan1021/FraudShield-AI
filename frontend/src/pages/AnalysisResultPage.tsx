import { Link, useParams } from 'react-router-dom';
import { TraceGraph } from '../components/TraceGraph';
import {
  BehaviourTable, DriversPanel, ExecutiveBanner, ExecutionTable, FactsPanel, InputSnapshot, LogicalInference,
  MetadataPanel, NarrativePanel, PipelinePanel, RecommendationCard, SeverityMeter, TriggeredRulesTable, EvidenceSeparation,
} from '../components/ResultPanels';
import { Card, ErrorState, Loading, PageHeader } from '../components/ui';
import { useAsync } from '../hooks/useAsync';
import { api } from '../services/api';

export function AnalysisResultPage() {
  const { id = '' } = useParams();
  const q = useAsync(() => api.transaction(id), [id]);
  if (q.loading && !q.data) return <Loading label="Loading analysis result" />;
  if (q.error && !q.data) return <ErrorState error={q.error} onRetry={q.reload} />;
  const { result, transaction } = q.data!;

  return (
    <div className="space-y-5">
      <PageHeader
        title="Analysis Result"
        subtitle="Complete decision with the evidence and reasoning behind it"
        actions={<>
          <Link className="btn-secondary" to="/analyze">Analyze another</Link>
          <Link className="btn-secondary" to={`/reports?transaction=${result.transaction_id}`}>Generate report</Link>
          <Link className="btn-primary" to={`/transactions/${result.transaction_id}`}>Forensic view</Link>
        </>}
      />
      <ExecutiveBanner result={result} />
      <div className="grid gap-5 lg:grid-cols-3">
        <RecommendationCard rec={result.recommendation} status={transaction.status} />
        <SeverityMeter index={result.severity_index} />
        <div className="rounded-lg border border-line bg-white p-4 text-sm">
          <div className="card-title">Inference summary</div>
          <dl className="mt-1 space-y-1">
            <div className="flex justify-between"><dt className="text-slate-500">Facts generated</dt><dd className="font-bold">{result.initial_facts.length}</dd></div>
            <div className="flex justify-between"><dt className="text-slate-500">Facts derived</dt><dd className="font-bold">{result.derived_facts.length}</dd></div>
            <div className="flex justify-between"><dt className="text-slate-500">Rules triggered</dt><dd className="font-bold">{result.triggered_rules.length} of {result.rules_evaluated.length}</dd></div>
            <div className="flex justify-between"><dt className="text-slate-500">Rule firings</dt><dd className="font-bold">{result.inference.firings}</dd></div>
          </dl>
        </div>
      </div>
      <div className="grid gap-5 lg:grid-cols-2">
        <DriversPanel explanation={result.explanation} />
        <NarrativePanel explanation={result.explanation} />
      </div>
      <EvidenceSeparation explanation={result.explanation} />
      <Card title="Inference trace graph"><TraceGraph graph={result.explanation.graph} /></Card>
      <Card title="Rules triggered" pad={false}><TriggeredRulesTable rules={result.triggered_rules} /></Card>
      <Card title="Logical inference chain"><LogicalInference steps={result.explanation.logical_inference} /></Card>
      <Card title="Rule execution trace (forward chaining)" pad={false}><ExecutionTable executions={result.reasoning_trace} /></Card>
      <Card title="Generated facts"><FactsPanel facts={result.facts} /></Card>
      <Card title="Behavioural deviations (baseline comparison)" pad={false}><BehaviourTable behaviour={result.behavioural_analysis} /></Card>
      <div className="grid gap-5 lg:grid-cols-2">
        <Card title="Input snapshot"><InputSnapshot snapshot={result.input_snapshot} /></Card>
        <Card title="Audit metadata"><MetadataPanel result={result} /></Card>
      </div>
      <Card title="Pipeline execution"><PipelinePanel stages={result.pipeline} /></Card>
    </div>
  );
}
