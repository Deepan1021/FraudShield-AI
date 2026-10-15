"""End-to-end analysis pipeline. Usable without the web layer:

    from app.pipeline import analyze_transaction
    result = analyze_transaction({...})
"""
from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from functools import lru_cache
from typing import List, Mapping, Optional, Sequence

from app.core.version import APP_VERSION, ENGINE_VERSION
from app.domain.enums import RiskLevel
from app.domain.models import BaselineProfile
from app.expert_system.classification.classifier import classify
from app.expert_system.classification.recommendation import recommend
from app.expert_system.explainability.explainer import build_explanation
from app.expert_system.extensions import FactProvider
from app.expert_system.inference.conflict_resolution import STRATEGY_DESCRIPTION
from app.expert_system.inference.forward_chaining import ForwardChainingEngine
from app.expert_system.knowledge_base.kb import KnowledgeBase
from app.expert_system.predicates.registry import PredicateRegistry, default_registry
from app.expert_system.rules.rulebase import RuleBase, default_rulebase
from app.preprocessing.behavior import analyze_behaviour
from app.preprocessing.constraints import evaluate_constraints
from app.preprocessing.fact_generator import generate_facts
from app.preprocessing.features import FeatureConfig, extract_features
from app.preprocessing.validation import validate_transaction
from app.utils.timeutil import utc_now_iso


class AnalysisPipeline:
    def __init__(self, rulebase: Optional[RuleBase] = None, registry: Optional[PredicateRegistry] = None,
                 config: Optional[FeatureConfig] = None, fact_providers: Sequence[FactProvider] = ()):
        self.registry = registry or default_registry()
        self.rulebase = rulebase or default_rulebase()
        self.config = config or FeatureConfig()
        self.fact_providers = list(fact_providers)
        self.kb = KnowledgeBase(self.rulebase, self.registry)
        self.engine = ForwardChainingEngine(self.rulebase.rules, self.registry)

    def analyze(self, raw: Mapping, baseline: Optional[BaselineProfile] = None) -> dict:
        started = time.perf_counter()
        stages: List[dict] = []

        @contextmanager
        def stage(key: str, label: str):
            t = time.perf_counter()
            rec = {"key": key, "label": label, "status": "COMPLETED", "duration_ms": 0.0, "detail": ""}
            stages.append(rec)
            try:
                yield rec
            except Exception:
                rec["status"] = "FAILED"
                raise
            finally:
                rec["duration_ms"] = round((time.perf_counter() - t) * 1000, 3)

        with stage("validation", "Validate and normalise input") as s:
            tx, normalisations = validate_transaction(raw)
            s["detail"] = f"{len(normalisations)} field(s) normalised"
        with stage("constraints", "Evaluate constraints") as s:
            constraints = evaluate_constraints(tx, baseline)
            s["detail"] = f"{sum(1 for c in constraints if not c.passed)} of {len(constraints)} constraints violated"
        with stage("baseline", "Load behavioural baseline") as s:
            s["detail"] = "Baseline loaded" if baseline else "No baseline on record for this user"
        with stage("behaviour", "Analyse behaviour") as s:
            behaviour = analyze_behaviour(tx, baseline, self.config.amount_spike_ratio,
                                          self.config.frequency_ratio, self.config.frequency_ratio_min)
            s["detail"] = f"{behaviour.anomaly_count} deviation(s) from baseline"
        with stage("features", "Extract features") as s:
            features = extract_features(tx, behaviour, constraints, self.config)
            s["detail"] = f"{len(features)} features extracted"
        with stage("facts", "Generate logical facts") as s:
            facts = generate_facts(tx, features, self.registry)
            for provider in self.fact_providers:
                for f in provider.provide(tx):
                    if not self.registry.has(f.predicate):
                        raise ValueError(f"Provider {provider.name} produced unregistered predicate {f.predicate}")
                    facts.append(f)
            s["detail"] = f"{len(facts)} initial facts"
        with stage("knowledge_base", "Load knowledge base") as s:
            s["detail"] = f"{len(self.rulebase.active_rules)} active rules, {len(self.registry.all())} predicates"
        with stage("inference", "Match rules, forward chain, resolve conflicts") as s:
            run = self.engine.run(facts)
            s["detail"] = f"{len(run.executions)} rule firings in {run.cycles} cycles"
        # Report the three inference sub-stages with the engine's measured timings.
        inference_stage = stages.pop()
        stages.append({"key": "rule_matching", "label": "Match rules", "status": "COMPLETED", "duration_ms": run.match_ms,
                       "detail": f"{run.rules_evaluated} rules evaluated against working memory"})
        stages.append({"key": "forward_chaining", "label": "Forward chain", "status": "COMPLETED",
                       "duration_ms": round(max(inference_stage["duration_ms"] - run.match_ms - run.resolve_ms, 0), 3),
                       "detail": inference_stage["detail"]})
        stages.append({"key": "conflict_resolution", "label": "Resolve conflicts", "status": "COMPLETED",
                       "duration_ms": run.resolve_ms, "detail": "Priority > specificity > severity > rule id"})
        with stage("classification", "Classify risk") as s:
            assessment = classify(run, tx.transaction_id, self.registry)
            s["detail"] = f"{assessment['risk_level']}"
        executions = [e.to_dict() for e in run.executions]
        with stage("recommendation", "Generate recommendation") as s:
            recommendation = recommend(RiskLevel(assessment["risk_level"]), executions)
            s["detail"] = recommendation["action"]
        constraints_d = [c.to_dict() for c in constraints]
        behaviour_d = behaviour.to_dict()
        with stage("explanation", "Generate explanation and trace") as s:
            explanation = build_explanation(tx.snapshot(), behaviour_d, constraints_d, run, assessment,
                                            recommendation, self.rulebase, self.registry)
            s["detail"] = f"{len(explanation['drivers'])} drivers"

        all_facts = [f.to_dict() for f in run.working_memory]
        triggered: dict = {}
        for e in executions:
            t = triggered.setdefault(e["rule_id"], {
                "rule_id": e["rule_id"], "rule_name": e["rule_name"], "category": e["category"], "priority": e["priority"],
                "severity": e["severity"], "formula": e["formula"], "times_fired": 0, "derived_facts": [], "tags": e["tags"],
                "explanation": (self.rulebase.get(e["rule_id"]).explanation if self.rulebase.get(e["rule_id"]) else ""),
                "rule_version": e["rule_version"]})
            t["times_fired"] += 1
            t["derived_facts"].append(e["derived_fact"])
        total_ms = round((time.perf_counter() - started) * 1000, 3)
        return {
            "evaluation_id": "EVAL-" + uuid.uuid4().hex[:12].upper(),
            "transaction_id": tx.transaction_id,
            "user_id": tx.user_id,
            "risk_level": assessment["risk_level"],
            "recommendation": recommendation,
            "assessment": assessment,
            "severity_index": assessment["severity_index"],
            "input_snapshot": tx.snapshot(),
            "validation": {"passed": True, "errors": [], "normalisations": normalisations},
            "constraints": constraints_d,
            "behavioural_analysis": behaviour_d,
            "features": [f.to_dict() for f in features],
            "facts": all_facts,
            "initial_facts": [f for f in all_facts if f["kind"] not in ("indicator", "risk")],
            "derived_facts": [f for f in all_facts if f["kind"] in ("indicator", "risk")],
            "rules_evaluated": [r.id for r in self.rulebase.active_rules],
            "triggered_rules": list(triggered.values()),
            "reasoning_trace": executions,
            "inference": {"cycles": run.cycles, "firings": len(executions), "terminated_by": run.terminated_by,
                          "conflict_resolution_strategy": STRATEGY_DESCRIPTION},
            "explanation": explanation,
            "pipeline": stages,
            "metadata": {
                "timestamp": utc_now_iso(), "processing_time_ms": total_ms, "engine_version": ENGINE_VERSION,
                "rulebase_version": self.rulebase.version, "rulebase_name": self.rulebase.name,
                "app_version": APP_VERSION, "thresholds": self.config.to_dict(),
            },
        }


@lru_cache(maxsize=1)
def default_pipeline() -> AnalysisPipeline:
    return AnalysisPipeline()


def analyze_transaction(raw: Mapping, baseline: Optional[BaselineProfile] = None) -> dict:
    return default_pipeline().analyze(raw, baseline)
