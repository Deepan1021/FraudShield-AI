import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, ErrorState, Field, PageHeader } from '../components/ui';
import { ApiError, api } from '../services/api';
import type { TransactionInput } from '../types/api';
import { newTransactionId } from '../utils/format';

export interface FormValues {
  transaction_id: string; user_id: string; amount: string; transaction_time: string; device_trust: string; location: string;
  login_behavior: string; transaction_frequency: string; account_activity: string; device_id: string; channel: string;
}

export const DEVICE_TRUST = ['TRUSTED', 'KNOWN', 'UNTRUSTED', 'UNKNOWN'];
export const LOGIN = ['NORMAL', 'UNUSUAL', 'FAILED_ATTEMPTS', 'SUSPICIOUS', 'HIGH_RISK'];
export const ACCOUNT = ['ACTIVE', 'NORMAL', 'SUSPICIOUS', 'DORMANT', 'RECENTLY_REACTIVATED', 'UNUSUAL'];
const CHANNELS = ['UPI', 'WALLET', 'ONLINE_BANKING', 'CARD', 'OTHER'];

const label = (s: string) => s.charAt(0) + s.slice(1).toLowerCase().replace(/_/g, ' ');

export function emptyForm(): FormValues {
  return { transaction_id: newTransactionId(), user_id: '', amount: '', transaction_time: '', device_trust: 'TRUSTED', location: '',
    login_behavior: 'NORMAL', transaction_frequency: '', account_activity: 'ACTIVE', device_id: '', channel: '' };
}

export const PRESETS: { key: string; title: string; values: Omit<FormValues, 'transaction_id'> }[] = [
  { key: 'normal', title: 'Normal payment', values: { user_id: 'USER002', amount: '2500', transaction_time: '14:30', device_trust: 'TRUSTED', location: 'Chennai', login_behavior: 'NORMAL', transaction_frequency: '2', account_activity: 'ACTIVE', device_id: 'DEV002', channel: 'UPI' } },
  { key: 'moderate', title: 'Moderate anomaly', values: { user_id: 'USER001', amount: '12000', transaction_time: '11:00', device_trust: 'TRUSTED', location: 'Mumbai', login_behavior: 'NORMAL', transaction_frequency: '3', account_activity: 'ACTIVE', device_id: 'DEV001', channel: 'UPI' } },
  { key: 'high', title: 'High-risk pattern', values: { user_id: 'USER001', amount: '85000', transaction_time: '14:00', device_trust: 'UNTRUSTED', location: 'Chennai', login_behavior: 'NORMAL', transaction_frequency: '3', account_activity: 'ACTIVE', device_id: 'DEV-X92', channel: 'ONLINE_BANKING' } },
  { key: 'critical', title: 'Critical composite', values: { user_id: 'USER001', amount: '85000', transaction_time: '02:15', device_trust: 'UNTRUSTED', location: 'Delhi', login_behavior: 'SUSPICIOUS', transaction_frequency: '12', account_activity: 'ACTIVE', device_id: 'DEV-X91', channel: 'UPI' } },
];

/** Client-side validation mirrors the backend rules for fast feedback; the backend remains authoritative. */
export function validateForm(v: FormValues): Partial<Record<keyof FormValues, string>> {
  const e: Partial<Record<keyof FormValues, string>> = {};
  if (!/^[A-Za-z0-9_-]{3,40}$/.test(v.transaction_id.trim())) e.transaction_id = 'Use 3-40 letters, digits, "-" or "_".';
  if (!/^[A-Za-z0-9_-]{3,40}$/.test(v.user_id.trim())) e.user_id = 'Use 3-40 letters, digits, "-" or "_".';
  if (v.amount.trim() === '') e.amount = 'Amount is required.';
  else if (!/^\d+(\.\d{1,2})?$/.test(v.amount.trim()) || Number(v.amount) <= 0) e.amount = 'Transaction amount must be greater than zero.';
  else if (Number(v.amount) > 10_000_000) e.amount = 'Amount must not exceed 10,000,000.';
  if (!/^(([01]?\d|2[0-3]):[0-5]\d|(0?[1-9]|1[0-2]):[0-5]\d\s*[AaPp][Mm])$/.test(v.transaction_time.trim())) e.transaction_time = 'Enter a time such as 14:30 or 02:15 AM.';
  if (!/^[A-Za-z][A-Za-z .,'-]{1,59}$/.test(v.location.trim())) e.location = 'Enter a location (letters and spaces, 2-60 characters).';
  if (!/^\d+$/.test(v.transaction_frequency.trim()) || Number(v.transaction_frequency) > 1000) e.transaction_frequency = 'Enter a whole number between 0 and 1000.';
  if (v.device_id.trim() !== '' && !/^[A-Za-z0-9_.:-]{1,64}$/.test(v.device_id.trim())) e.device_id = 'Letters, digits and . : - _ only.';
  return e;
}

export function toInput(v: FormValues): TransactionInput {
  const out: TransactionInput = {
    transaction_id: v.transaction_id.trim(), user_id: v.user_id.trim(), amount: Number(v.amount), transaction_time: v.transaction_time.trim(),
    device_trust: v.device_trust, location: v.location.trim(), login_behavior: v.login_behavior,
    transaction_frequency: Number(v.transaction_frequency), account_activity: v.account_activity,
  };
  if (v.device_id.trim()) out.device_id = v.device_id.trim();
  if (v.channel) out.channel = v.channel;
  return out;
}

const STEPS = ['Validation', 'Constraint evaluation', 'Behavioural baseline analysis', 'Feature extraction', 'Fact generation',
  'Knowledge representation', 'Rule matching', 'Forward chaining', 'Conflict resolution', 'Risk classification', 'Recommendation', 'Explainability and audit'];

export function AnalyzePage() {
  const nav = useNavigate();
  const [values, setValues] = useState<FormValues>(emptyForm);
  const [errors, setErrors] = useState<Partial<Record<keyof FormValues, string>>>({});
  const [serverError, setServerError] = useState<Error | null>(null);
  const [busy, setBusy] = useState(false);

  const set = (k: keyof FormValues) => (e: { target: { value: string } }) => {
    setValues((s) => ({ ...s, [k]: e.target.value }));
    if (errors[k]) setErrors((s) => ({ ...s, [k]: undefined }));
  };

  const submit = async (ev: FormEvent) => {
    ev.preventDefault();
    setServerError(null);
    const errs = validateForm(values);
    setErrors(errs);
    if (Object.keys(errs).length) return;
    setBusy(true);
    try {
      const result = await api.analyze(toInput(values));
      nav(`/analysis/${result.transaction_id}`);
    } catch (e) {
      if (e instanceof ApiError && (e.details?.length || e.field)) {
        const mapped: Partial<Record<keyof FormValues, string>> = {};
        (e.details?.length ? e.details : [{ field: e.field ?? '', message: e.message }]).forEach((d) => {
          if (d.field in values) mapped[d.field as keyof FormValues] = d.message;
        });
        setErrors(mapped);
      }
      setServerError(e as Error);
    } finally {
      setBusy(false);
    }
  };

  const cls = (k: keyof FormValues) => `input ${errors[k] ? 'input-error' : ''}`;
  const aria = (k: keyof FormValues) => ({ 'aria-invalid': !!errors[k], 'aria-describedby': errors[k] ? `${k}-error` : undefined });

  return (
    <div>
      <PageHeader title="Transaction Analysis" subtitle="Submit the seven security parameters. The expert system validates, reasons and returns an explainable decision." />
      <div className="grid gap-5 xl:grid-cols-3">
        <form onSubmit={submit} noValidate className="space-y-5 xl:col-span-2" aria-label="Transaction analysis form">
          <Card title="Quick scenarios">
            <div className="flex flex-wrap gap-2">
              {PRESETS.map((p) => (
                <button key={p.key} type="button" className="btn-secondary" data-testid={`preset-${p.key}`}
                  onClick={() => { setValues({ transaction_id: newTransactionId(), ...p.values }); setErrors({}); setServerError(null); }}>
                  {p.title}
                </button>
              ))}
            </div>
            <p className="mt-2 text-xs text-slate-500">Scenarios fill the form with synthetic values (user baselines come from the demonstration data). The risk level is always produced by the rule engine, never by the form.</p>
          </Card>

          <Card title="Transaction">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Transaction ID" htmlFor="transaction_id" error={errors.transaction_id} hint="Synthetic identifier, unique per analysis">
                <input id="transaction_id" className={cls('transaction_id')} value={values.transaction_id} onChange={set('transaction_id')} {...aria('transaction_id')} />
              </Field>
              <Field label="User ID" htmlFor="user_id" error={errors.user_id}>
                <input id="user_id" className={cls('user_id')} value={values.user_id} onChange={set('user_id')} placeholder="USER001" {...aria('user_id')} />
              </Field>
              <Field label="1. Payment amount (INR)" htmlFor="amount" error={errors.amount}>
                <input id="amount" inputMode="decimal" className={cls('amount')} value={values.amount} onChange={set('amount')} placeholder="85000" {...aria('amount')} />
              </Field>
              <Field label="2. Transaction time" htmlFor="transaction_time" error={errors.transaction_time} hint="24-hour (14:30) or 12-hour (02:15 AM)">
                <input id="transaction_time" className={cls('transaction_time')} value={values.transaction_time} onChange={set('transaction_time')} placeholder="02:15" {...aria('transaction_time')} />
              </Field>
            </div>
          </Card>

          <Card title="Security parameters">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="3. Device trust signature" htmlFor="device_trust">
                <select id="device_trust" className="input" value={values.device_trust} onChange={set('device_trust')}>{DEVICE_TRUST.map((o) => <option key={o} value={o}>{label(o)}</option>)}</select>
              </Field>
              <Field label="4. Geographic location" htmlFor="location" error={errors.location}>
                <input id="location" className={cls('location')} value={values.location} onChange={set('location')} placeholder="Delhi" {...aria('location')} />
              </Field>
              <Field label="5. Login behaviour" htmlFor="login_behavior">
                <select id="login_behavior" className="input" value={values.login_behavior} onChange={set('login_behavior')}>{LOGIN.map((o) => <option key={o} value={o}>{label(o)}</option>)}</select>
              </Field>
              <Field label="6. Transaction frequency" htmlFor="transaction_frequency" error={errors.transaction_frequency} hint="Transactions in the relevant period">
                <input id="transaction_frequency" inputMode="numeric" className={cls('transaction_frequency')} value={values.transaction_frequency} onChange={set('transaction_frequency')} placeholder="12" {...aria('transaction_frequency')} />
              </Field>
              <Field label="7. Account activity history" htmlFor="account_activity">
                <select id="account_activity" className="input" value={values.account_activity} onChange={set('account_activity')}>{ACCOUNT.map((o) => <option key={o} value={o}>{label(o)}</option>)}</select>
              </Field>
            </div>
          </Card>

          <Card title="Supporting metadata (optional)">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Device ID" htmlFor="device_id" error={errors.device_id} hint="Compared with the user's known devices">
                <input id="device_id" className={cls('device_id')} value={values.device_id} onChange={set('device_id')} placeholder="DEV001" {...aria('device_id')} />
              </Field>
              <Field label="Payment channel" htmlFor="channel">
                <select id="channel" className="input" value={values.channel} onChange={set('channel')}><option value="">Not specified</option>{CHANNELS.map((o) => <option key={o} value={o}>{label(o)}</option>)}</select>
              </Field>
            </div>
            <p className="mt-3 rounded bg-slate-50 px-3 py-2 text-xs text-slate-600">Never enter card numbers, CVV, PIN, passwords or OTPs. FraudShield AI is a risk-analysis platform, not a payment processor, and rejects credential fields.</p>
          </Card>

          {serverError && <div role="alert" data-testid="server-error"><ErrorState error={serverError} /></div>}
          <div className="flex items-center gap-3">
            <button className="btn-primary" type="submit" disabled={busy} data-testid="analyze-submit">{busy ? 'Running analysis pipeline…' : 'Analyze transaction'}</button>
            {busy && <span className="text-sm text-slate-500" role="status">The result is shown after the backend completes every stage.</span>}
          </div>
        </form>

        <Card title="What the engine does" className="h-fit">
          <ol className="space-y-1.5 text-sm">
            {STEPS.map((s, i) => (
              <li key={s} className="flex items-center gap-2.5"><span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-ink text-[11px] font-bold text-white">{i + 1}</span>{s}</li>
            ))}
          </ol>
          <p className="mt-3 text-xs text-slate-500">Every stage is implemented in the backend; its real duration is reported on the result page.</p>
        </Card>
      </div>
    </div>
  );
}
