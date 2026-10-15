# AI engine

A symbolic expert system: structured facts, a versioned production-rule base, forward chaining, deterministic conflict
resolution and an explanation generated from the actual inference record. No machine-learning model is involved.

## Facts and predicates

`Fact(predicate, args, kind, source, value, confidence, derivation_rule, parents, supported_by, seq, created_at)`.
There are 31 predicates (`expert_system/predicates/registry.py`) in five kinds:

| Kind | Meaning | Examples |
|---|---|---|
| observed | taken directly from the input | `HighAmount`, `UntrustedDevice`, `NightTransaction`, `SuspiciousLogin`, `ActiveAccount` |
| behavioural | baseline comparison | `AmountSpike`, `NewDevice`, `NewLocation`, `UnusualHour`, `NoBehaviouralBaseline` |
| constraint | constraint engine | `SessionIntegrityConcern` |
| indicator | derived by rules | `UnverifiedDevice`, `ElevatedValue`, `AuthenticationAnomaly`, `AccountAnomaly`, `OffHoursActivity` |
| risk | derived by rules | `LowRisk`, `MediumRisk`, `HighRisk`, `CriticalRisk` |

Thresholds (`FeatureConfig`): high amount >= 50,000; amount spike >= 3x user average; high frequency >= 10, or >= 3x the
usual level and >= 6; night 00:00-05:59.

## Rules (rule base v1.0.0, 32 rules)

Each rule has `id, name, category, description, explanation, if, then, priority, severity, tags, source, version, status`
and optionally `min_matches` (an m-of-n rule: at least *m* of the listed unary conditions hold).

| Group | Rules | Purpose |
|---|---|---|
| Evidence normalisation (priority 90) | R01-R13 | map equivalent evidence to one indicator (e.g. untrusted *or* unknown device -> `UnverifiedDevice`) |
| Medium (50-55) | R20-R25 | single indicators; `OffHoursActivity ∧ HighFrequency` (neither alone is risky) |
| High (60-72) | R30-R37 | e.g. `HighAmount ∧ UnverifiedDevice -> HighRisk`; `AuthenticationAnomaly ∧ NewLocation -> HighRisk`; session hijack R36; any 3 of 7 indicators (R37) |
| Critical (64-82) | R40-R43 | `HighRisk ∧ OffHoursActivity ∧ NewLocation -> CriticalRisk`; account-takeover pattern R42; any 5 of 7 indicators (R43) |
| Mitigating (30) | R50 | `TrustedDevice ∧ KnownLocation ∧ ActiveAccount -> LowRisk` (never overrides a higher conclusion) |

Rule base loading validates: required fields, unique ids, known predicates and arity, bound variables, derived predicates
being indicator/risk only, `min_matches` sanity, priority range, and **absence of cyclic derivations**. An empty or
all-inactive rule base is a hard error, never a silent zero-rule start.

## Matching and forward chaining

* The matcher unifies each antecedent against working-memory facts (variables start lower-case, constants upper-case or digits) with a backtracking join, so multi-argument predicates work. m-of-n rules count satisfied unary conditions per entity.
* Each cycle builds the **conflict set** (all not-yet-fired instantiations), the resolver selects one, the rule fires and its consequent is added. An instantiation `(rule, bindings)` fires **once** (refraction). If the consequent already exists, no duplicate is added; the firing is recorded as *additional support*.
* The run stops when the conflict set is empty (fixpoint). A cycle limit raises `InferenceError`.
* The trace records for each firing: cycle, rule, bindings, matched facts, derived fact, whether it was new, conflict-set size and why the rule was selected.

## Conflict resolution

1. higher rule **priority**, 2. higher **specificity** (more matched conditions; composite rules first), 3. higher rule **severity**, 4. lower rule **id**, 5. bindings. Evidence normalisation (90) therefore precedes assessment, and escalations (critical 78-82) precede basic conclusions.

## Risk classification (security-first)

The final level is the highest derived risk conclusion; `LowRisk` is mitigating evidence and is overridden by any higher conclusion; with no conclusion the default is `LOW`. Decisive rules are those that derived or re-derived the winning conclusion. The classifier also reports a transparent **Rule-based Risk Severity Index** (sum of fixed weights of observed/behavioural facts, capped at 100) which is explicitly *not* a probability and does not drive the decision.

## Recommendation

A separate policy maps LOW->`APPROVE`, MEDIUM->`REQUEST_MFA`, HIGH->`TEMPORARILY_BLOCK`, CRITICAL->`FLAG_FOR_ANALYST_REVIEW`. A fired rule tagged `analyst_escalation` (R36) upgrades the action to analyst review.

## Explanation

`explanation` contains: narrative; drivers (leaf evidence in the support closure of the decisive conclusion across **all** supporting firings); observed evidence; derived evidence; behavioural deviations; violated constraints; the ordered logical-inference steps; the final decision with resolution rationale; a proof tree ("why chain"); and a layered graph (facts -> rules -> facts) with the decisive chain marked. Everything is produced from the run, never from templates keyed on results.

## Worked example (TXN001 with the demo baseline of USER001)

Initial facts: `HighAmount, UntrustedDevice, NightTransaction, HighFrequency, SuspiciousLogin, ActiveAccount, AmountSpike, NewLocation, UnusualHour`.
R01/R03/R06/R12/R13 derive `UnverifiedDevice`, `ElevatedValue`, `AuthenticationAnomaly`, `OffHoursActivity`; R30 derives `HighRisk`;
R40 (`HighRisk ∧ OffHoursActivity ∧ NewLocation`) derives `CriticalRisk`; R41, R43 etc. re-support it. Final: **CRITICAL -> FLAG_FOR_ANALYST_REVIEW**.

## Extending

* Add rules: edit a copy of `rulebase_v1.json`, bump `rulebase_version`; tests in `test_expert_system.py` validate the structure.
* Add evidence: implement `FactProvider.provide(tx) -> list[Fact]`, register the predicate (`PredicateRegistry.register`), and pass the provider to `AnalysisPipeline(fact_providers=[...])` (see `ExtensionTests`).
