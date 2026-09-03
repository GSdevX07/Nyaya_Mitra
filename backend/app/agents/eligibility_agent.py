"""
eligibility_agent.py - Deterministic Versioned Section 479 BNSS Rule Engine.

╔══════════════════════════════════════════════════════════════════════════╗
║  CRITICAL LEGAL & ARCHITECTURAL PRINCIPLES                              ║
║  1. Pure deterministic arithmetic - NEVER an LLM decision.               ║
║  2. Versioned Rule System: BNSS_479_RULESET_V1_2023                      ║
║  3. Distinguishes total elapsed calendar days from countable custody      ║
║     (accounting for accused-attributable delay periods).                ║
║  4. Checks statutory exclusions (death/life imprisonment, multiple       ║
║     pending proceedings condition).                                      ║
║  5. Outputs an eligibility signal for human legal review, NOT an         ║
║     automatic release entitlement or judicial prediction.                ║
║  6. Documented Rounding Rule: Computes threshold precisely according to   ║
║     the validated statutory interpretation (using math.ceil as the       ║
║     documented threshold integer rule).                                  ║
║  7. Legal validation requirement: Subject to validation by counsel.     ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations
import math
from typing import Dict, Any

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List

from app.models.schemas import CaseRecord


@dataclass
class StatutoryRuleConfig:
    version_id: str
    statute_name: str
    section: str
    effective_date: str
    description: str
    first_time_offender_fraction: float
    general_undertrial_fraction: float
    excludes_capital_or_life: bool = True
    excludes_multiple_proceedings: bool = True
    rounding_rule: str = "math.ceil"
    is_active: bool = True


class StatutoryRuleRegistry:
    """Versioned registry for statutory bail eligibility rules."""

    def __init__(self):
        self._rules: Dict[str, StatutoryRuleConfig] = {}
        self._active_version: str = "BNSS_479_RULESET_V1_2023"
        self._register_default_rules()

    def _register_default_rules(self):
        self.register_rule(StatutoryRuleConfig(
            version_id="BNSS_479_RULESET_V1_2023",
            statute_name="Bharatiya Nagarik Suraksha Sanhita, 2023",
            section="Section 479",
            effective_date="2024-07-01",
            description="First-time undertrials eligible at 1/3 maximum imprisonment; others at 1/2 maximum imprisonment.",
            first_time_offender_fraction=1 / 3,
            general_undertrial_fraction=1 / 2,
            excludes_capital_or_life=True,
            excludes_multiple_proceedings=True,
            rounding_rule="math.ceil",
            is_active=True,
        ))
        self.register_rule(StatutoryRuleConfig(
            version_id="CRPC_436A_RULESET_V1_1973",
            statute_name="Code of Criminal Procedure, 1973",
            section="Section 436A",
            effective_date="2005-06-23",
            description="Historic regime: Undertrials eligible at 1/2 maximum imprisonment without 1/3 first-time offender proviso.",
            first_time_offender_fraction=1 / 2,
            general_undertrial_fraction=1 / 2,
            excludes_capital_or_life=True,
            excludes_multiple_proceedings=False,
            rounding_rule="math.ceil",
            is_active=False,
        ))

    def register_rule(self, config: StatutoryRuleConfig):
        self._rules[config.version_id] = config

    def get_rule(self, version_id: Optional[str] = None) -> StatutoryRuleConfig:
        vid = version_id or self._active_version
        if vid not in self._rules:
            # Fallback to active version if unknown
            return self._rules.get(self._active_version) or list(self._rules.values())[0]
        return self._rules[vid]

    def list_rules(self) -> List[Dict[str, Any]]:
        return [
            {
                "version_id": r.version_id,
                "statute_name": r.statute_name,
                "section": r.section,
                "effective_date": r.effective_date,
                "description": r.description,
                "first_time_offender_fraction": r.first_time_offender_fraction,
                "general_undertrial_fraction": r.general_undertrial_fraction,
                "rounding_rule": r.rounding_rule,
                "is_active": (r.version_id == self._active_version),
            }
            for r in self._rules.values()
        ]

    def set_active_version(self, version_id: str):
        if version_id not in self._rules:
            raise KeyError(f"Cannot activate unregistered rule version: {version_id}")
        self._active_version = version_id


RULE_REGISTRY = StatutoryRuleRegistry()
RULE_ENGINE_VERSION = RULE_REGISTRY._active_version


def evaluate_eligibility(case: CaseRecord, rule_version: Optional[str] = None) -> Dict[str, Any]:
    """
    Evaluate whether documented case facts appear to satisfy statutory criteria
    using the Stage 8 Deterministic Versioned Legal Rules Framework.
    """
    from app.rules.service import evaluate_eligibility as _engine_evaluate
    return _engine_evaluate(case=case, rule_version=rule_version)
