import { Card, PageHeader } from '../components/ui';

const FLOW = ['Transaction', 'Validation', 'Constraints', 'Behaviour baseline', 'Features', 'Facts', 'Knowledge base', 'Rule matching', 'Forward chaining', 'Conflict resolution', 'Risk classification', 'Recommendation', 'Explanation and trace', 'Audit and storage'];

export function AboutPage() {
  return (
    <div className="space-y-5">
      <PageHeader title="About FraudShield AI" subtitle="Intelligent Digital Payment Risk Assessment System" />
      <Card title="Product">
        <p className="max-w-3xl leading-relaxed">FraudShield AI evaluates digital payment activity across seven security dimensions instead of relying on the amount alone. It converts each transaction into structured logical facts, reasons over a versioned production-rule base with forward chaining, and returns a risk level, a recommended action and a complete, inspectable explanation.</p>
      </Card>
      <Card title="Reasoning architecture">
        <ol className="flex flex-wrap items-center gap-2 text-sm" aria-label="Processing pipeline">
          {FLOW.map((s, i) => (
            <li key={s} className="flex items-center gap-2"><span className="rounded-md border border-line bg-slate-50 px-2.5 py-1 font-medium">{s}</span>{i < FLOW.length - 1 && <span aria-hidden="true" className="text-slate-400">→</span>}</li>
          ))}
        </ol>
        <div className="mt-4 grid gap-4 text-sm md:grid-cols-3">
          <div><div className="card-title">Knowledge representation</div><p className="mt-1 text-slate-600">Facts are structured predicates such as HighAmount(TXN001) with source, derivation rule and parent facts. Rules are data: antecedents, consequent, priority, severity, category and version.</p></div>
          <div><div className="card-title">Inference</div><p className="mt-1 text-slate-600">A forward-chaining engine matches rules by unification, resolves conflicts deterministically (priority, specificity, severity, id), fires each instantiation once and stops at a fixpoint.</p></div>
          <div><div className="card-title">Explainability</div><p className="mt-1 text-slate-600">Every decision separates observed evidence, derived evidence, logical inference and the final decision, and exposes the reasoning chain as a graph. There is no black box.</p></div>
        </div>
      </Card>
      <div className="grid gap-5 md:grid-cols-2">
        <Card title="Risk levels and actions">
          <table className="w-full text-sm"><tbody>
            {[['LOW', 'Approve'], ['MEDIUM', 'Request additional identity verification (MFA)'], ['HIGH', 'Temporarily block'], ['CRITICAL', 'Flag for cyber analyst review']].map(([l, a]) => <tr key={l}><td className="td font-bold">{l}</td><td className="td">{a}</td></tr>)}
          </tbody></table>
        </Card>
        <Card title="Limitations">
          <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
            <li>A decision-support demonstrator, not a certified banking control or a payment processor.</li>
            <li>Rules and thresholds are illustrative and are not calibrated on real fraud data.</li>
            <li>The Rule-based Risk Severity Index is a transparent weighted count, not a probability.</li>
            <li>Demonstration data is synthetic and clearly labelled.</li>
            <li>Machine learning is a designed extension point (additional facts); the core stays symbolic.</li>
          </ul>
        </Card>
      </div>
      <Card title="Project background">
        <p className="max-w-3xl text-sm leading-relaxed text-slate-700">FraudShield AI was developed as an engineering project demonstrating knowledge representation, predicate logic, production rules, forward chaining and explainable AI applied to digital payment fraud. It is built to professional engineering standards: layered architecture, versioned rule base, audit trail and automated tests.</p>
      </Card>
    </div>
  );
}
