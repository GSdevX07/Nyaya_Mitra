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
    """Compatibility adapter delegating to the unified Stage 8 LegalRuleRegistry."""

    def __init__(self):
        self._active_version: str = "BNSS_479_RULESET_V1_2023"

    def get_rule(self, version_id: Optional[str] = None) -> StatutoryRuleConfig:
        from app.rules.registry import RULE_REGISTRY as rreg
        vid = version_id or self._active_version
        r = rreg.get_rule(vid)
        return StatutoryRuleConfig(
            version_id=r.rule_version,
            statute_name=r.statutory_source,
            section="Section 479" if "479" in r.rule_id else "Section 436A",
            effective_date=r.effective_date,
            description=r.title,
            first_time_offender_fraction=1.0 / 3.0 if "479" in r.rule_id else 0.5,
            general_undertrial_fraction=0.5,
            rounding_rule="math.ceil",
            is_active=(r.lifecycle_state.value == "ACTIVE" if hasattr(r.lifecycle_state, "value") else r.lifecycle_state == "ACTIVE"),
        )

    def list_rules(self) -> List[Dict[str, Any]]:
        from app.rules.registry import RULE_REGISTRY as rreg
        rules = rreg.list_rules()
        return [
            {
                "version_id": r["rule_version"],
                "statute_name": r.get("statutory_source", ""),
                "section": "Section 479" if "479" in r.get("rule_id", "") else "Section 436A",
                "effective_date": r.get("effective_date", ""),
                "description": r.get("title", ""),
                "first_time_offender_fraction": 1.0 / 3.0 if "479" in r.get("rule_id", "") else 0.5,
                "general_undertrial_fraction": 0.5,
                "rounding_rule": "math.ceil",
                "is_active": r.get("lifecycle_state") == "ACTIVE",
            }
            for r in rules
        ]

    def register_rule(self, config: StatutoryRuleConfig):
        pass

    def set_active_version(self, version_id: str):
        from app.rules.registry import RULE_REGISTRY as rreg
        rreg.get_rule(version_id)
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
