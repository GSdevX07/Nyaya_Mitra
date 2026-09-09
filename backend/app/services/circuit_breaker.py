"""
Circuit breakers and graceful degradation subsystem for Nyaya Mitra.
Guarantees resilience against external AI provider timeouts and court/prison connector outages.
"""

from __future__ import annotations
import time
import logging
import threading
from enum import Enum
from typing import Callable, Any, Optional, Dict

logger = logging.getLogger("nyaya_mitra.circuit_breaker")


class CircuitState(str, Enum):
    CLOSED = "CLOSED"        # Normal operational mode
    OPEN = "OPEN"            # Tripped mode: reject calls immediately and run fallback
    HALF_OPEN = "HALF_OPEN"  # Probe mode: allow trial call to test upstream recovery


class CircuitBreakerOpenException(Exception):
    """Raised when an operation is attempted while circuit is in OPEN state."""
    pass


class CircuitBreaker:
    """Thread-safe circuit breaker protecting against cascading upstream failures."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
        half_open_trials: int = 1,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_trials = half_open_trials

        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._last_state_change = time.time()
        self._last_failure_time: Optional[float] = None
        self._trial_count = 0
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                if (time.time() - self._last_state_change) >= self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._trial_count = 0
                    self._last_state_change = time.time()
                    logger.info(f"CircuitBreaker '{self.name}' transitioned from OPEN to HALF_OPEN (probing upstream).")
            return self._state

    def can_execute(self) -> bool:
        """Check if call can proceed or if circuit is tripped."""
        current = self.state
        if current == CircuitState.CLOSED:
            return True
        if current == CircuitState.HALF_OPEN:
            with self._lock:
                if self._trial_count < self.half_open_trials:
                    self._trial_count += 1
                    return True
                return False
        return False

    def record_success(self) -> None:
        """Reset failures upon successful response."""
        with self._lock:
            self._consecutive_failures = 0
            if self._state in (CircuitState.HALF_OPEN, CircuitState.OPEN):
                self._state = CircuitState.CLOSED
                self._trial_count = 0
                self._last_state_change = time.time()
                logger.info(f"CircuitBreaker '{self.name}' healed and returned to CLOSED state.")

    def record_failure(self, error: Optional[Exception] = None) -> None:
        """Increment failures and trip if threshold exceeded."""
        with self._lock:
            self._consecutive_failures += 1
            self._last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN or self._consecutive_failures >= self.failure_threshold:
                if self._state != CircuitState.OPEN:
                    self._state = CircuitState.OPEN
                    self._last_state_change = time.time()
                    logger.warning(
                        f"CircuitBreaker '{self.name}' TRIPPED to OPEN state! "
                        f"Failures: {self._consecutive_failures}, Trigger: {error}."
                    )

    def execute(self, func: Callable, fallback: Optional[Callable] = None, *args, **kwargs) -> Any:
        """Execute callable with circuit protection, executing fallback if tripped."""
        if not self.can_execute():
            logger.warning(f"Circuit '{self.name}' is {self.state.value}. Diverting to fallback immediately.")
            if fallback:
                return fallback(*args, **kwargs)
            raise CircuitBreakerOpenException(f"Service '{self.name}' is currently unavailable (circuit open).")

        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as exc:
            self.record_failure(exc)
            if fallback:
                logger.info(f"Circuit '{self.name}' caught error, running graceful fallback: {exc}")
                return fallback(*args, **kwargs)
            raise

    def get_status(self) -> Dict[str, Any]:
        """Status dict for dashboard telemetry."""
        return {
            "name": self.name,
            "state": self.state.value,
            "consecutive_failures": self._consecutive_failures,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout_sec": self.recovery_timeout,
            "seconds_in_current_state": round(time.time() - self._last_state_change, 1),
        }


# Procedural Bail Draft Fallback Generator
def procedural_bail_draft_fallback(case_id: str, applicant_name: str = "Applicant (Undertrial)", **kwargs) -> Dict[str, Any]:
    """
    Standard procedural legal draft template served when external AI models are unreachable.
    Allows defense advocates to draft without stalling on network timeouts.
    """
    draft = f"""BEFORE THE HON'BLE COURT OF SESSIONS / HIGH COURT
[MATTER: BAIL APPLICATION UNDER SECTION 479 OF BHARATIYA NAGARIK SURAKSHA SANHITA, 2023]

IN THE MATTER OF:
State (NCT of Delhi / Prosecution)
VERSUS
{applicant_name} (Accused / Undertrial Prisoner)
Case Reference: {case_id}

MEMORANDUM OF APPLICATION FOR REGULAR BAIL

MOST RESPECTFULLY SHOWETH:
1. That the Applicant has been incarcerated in judicial custody as an undertrial prisoner in connection with the aforementioned case.
2. That the Applicant has completed more than one-third / one-half of the maximum period of imprisonment specified for the alleged offense, rendering them eligible for statutory relief under Section 479 of BNSS, 2023.
3. That the Applicant is not accused of an offense for which the punishment of death or imprisonment for life is specified.
4. That the Applicant undertakes to cooperate fully with the trial proceedings and shall not tamper with evidence or influence witnesses.

PRAYER:
In view of the above facts and circumstances, it is respectfully prayed that this Hon'ble Court may be pleased to:
(a) Grant regular bail to the Applicant on suitable personal bond and sureties;
(b) Pass any other order deemed fit in the interest of justice.

[AI_OFFLINE_FALLBACK: Procedural Template Generated Due to AI Service Degradation]
Generated at: {time.strftime('%Y-%m-%d %H:%M:%SZ', time.gmtime())}
"""
    return {
        "case_id": case_id,
        "draft_text": draft,
        "status": "AI_OFFLINE_FALLBACK",
        "provider_used": "procedural_statutory_fallback",
        "notice": "AI service offline; procedural statutory template provided for manual review and editing.",
    }


# Global Singletons for Subsystems
ai_service_breaker = CircuitBreaker("ai_gateway", failure_threshold=3, recovery_timeout=30.0)
ecourts_breaker = CircuitBreaker("ecourts", failure_threshold=3, recovery_timeout=60.0)
eprisons_breaker = CircuitBreaker("eprisons", failure_threshold=3, recovery_timeout=60.0)
cctns_breaker = CircuitBreaker("cctns", failure_threshold=3, recovery_timeout=60.0)


def get_all_circuit_statuses() -> Dict[str, Dict[str, Any]]:
    """Return map of all active circuit breaker statuses."""
    return {
        "ai_gateway": ai_service_breaker.get_status(),
        "ecourts": ecourts_breaker.get_status(),
        "eprisons": eprisons_breaker.get_status(),
        "cctns": cctns_breaker.get_status(),
    }
