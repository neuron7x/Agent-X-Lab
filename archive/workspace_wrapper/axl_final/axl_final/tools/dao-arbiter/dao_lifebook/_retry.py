"""
DAO-LIFEBOOK — Retry & Resilience.

Exponential backoff with jitter, circuit breaker, and rate-limit awareness.
Designed for GitHub API but generic enough for any HTTP backend.
"""

from __future__ import annotations

import time
import random
import logging
from dataclasses import dataclass, field
from typing import TypeVar, Callable, Any

from ._types import Result, Ok, Err, DAOError, ErrorSeverity, EC

logger = logging.getLogger("dao.retry")

T = TypeVar("T")


@dataclass(slots=True)
class RetryConfig:
    """Retry policy configuration."""
    max_attempts: int = 3
    base_delay: float = 1.0       # seconds
    max_delay: float = 30.0       # seconds
    jitter_factor: float = 0.25   # ±25% random jitter
    retryable_status_codes: frozenset[int] = field(
        default_factory=lambda: frozenset({408, 429, 500, 502, 503, 504})
    )


@dataclass(slots=True)
class CircuitBreaker:
    """
    Simple circuit breaker.

    CLOSED → OPEN after `failure_threshold` consecutive failures.
    OPEN → HALF_OPEN after `recovery_timeout` seconds.
    HALF_OPEN → CLOSED on success, OPEN on failure.
    """
    failure_threshold: int = 5
    recovery_timeout: float = 60.0

    _failures: int = field(default=0, init=False)
    _last_failure_time: float = field(default=0.0, init=False)
    _state: str = field(default="closed", init=False)

    @property
    def state(self) -> str:
        if self._state == "open":
            if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                self._state = "half_open"
        return self._state

    def record_success(self) -> None:
        self._failures = 0
        self._state = "closed"

    def record_failure(self) -> None:
        self._failures += 1
        self._last_failure_time = time.monotonic()
        if self._failures >= self.failure_threshold:
            self._state = "open"

    def allow_request(self) -> bool:
        s = self.state
        return s in ("closed", "half_open")


def retry_with_backoff(
    fn: Callable[..., T],
    *args: Any,
    config: RetryConfig | None = None,
    breaker: CircuitBreaker | None = None,
    **kwargs: Any,
) -> Result[T, DAOError]:
    """
    Execute `fn` with retry, backoff, jitter, and optional circuit breaker.

    Returns Result — never raises for expected failure modes.
    """
    cfg = config or RetryConfig()

    for attempt in range(1, cfg.max_attempts + 1):
        # Circuit breaker check
        if breaker and not breaker.allow_request():
            return Err(DAOError(
                code=EC.API_TIMEOUT,
                message="Circuit breaker open — too many consecutive failures",
                severity=ErrorSeverity.RETRY,
                context={"breaker_state": breaker.state},
                source="retry",
            ))

        try:
            result = fn(*args, **kwargs)

            if breaker:
                breaker.record_success()

            return Ok(result)

        except Exception as exc:
            if breaker:
                breaker.record_failure()

            is_last = attempt == cfg.max_attempts
            exc_str = str(exc)

            # Check if retryable
            retryable = _is_retryable(exc, cfg)

            if is_last or not retryable:
                error = _classify_error(exc)
                logger.warning(
                    "Request failed (attempt %d/%d, final=%s): %s",
                    attempt, cfg.max_attempts, is_last, exc_str,
                )
                return Err(error)

            # Calculate delay with jitter
            delay = min(
                cfg.base_delay * (2 ** (attempt - 1)),
                cfg.max_delay,
            )
            jitter = delay * cfg.jitter_factor * (2 * random.random() - 1)
            actual_delay = max(0, delay + jitter)

            # Respect Retry-After header if present
            retry_after = _extract_retry_after(exc)
            if retry_after is not None:
                actual_delay = max(actual_delay, retry_after)

            logger.info(
                "Retrying in %.1fs (attempt %d/%d): %s",
                actual_delay, attempt, cfg.max_attempts, exc_str[:100],
            )
            time.sleep(actual_delay)

    # Should not reach here, but fail-closed
    return Err(DAOError(
        code=EC.API_TIMEOUT,
        message="Exhausted all retry attempts",
        severity=ErrorSeverity.HALT,
        source="retry",
    ))


def _is_retryable(exc: Exception, cfg: RetryConfig) -> bool:
    """Determine if an exception warrants retry."""
    import httpx

    if isinstance(exc, httpx.TimeoutException):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in cfg.retryable_status_codes
    if isinstance(exc, (ConnectionError, OSError)):
        return True
    return False


def _extract_retry_after(exc: Exception) -> float | None:
    """Extract Retry-After header value if present."""
    import httpx

    if isinstance(exc, httpx.HTTPStatusError):
        val = exc.response.headers.get("retry-after")
        if val:
            try:
                return float(val)
            except ValueError:
                pass
    return None


def _classify_error(exc: Exception) -> DAOError:
    """Classify exception into structured DAOError."""
    import httpx

    if isinstance(exc, httpx.TimeoutException):
        return DAOError(
            code=EC.API_TIMEOUT,
            message=f"Request timed out: {exc}",
            severity=ErrorSeverity.RETRY,
            source="http",
        )
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status == 401:
            return DAOError(
                code=EC.API_AUTH_FAILED,
                message="Authentication failed — check GITHUB_TOKEN",
                severity=ErrorSeverity.HALT,
                source="http",
            )
        if status == 403:
            return DAOError(
                code=EC.API_RATE_LIMITED,
                message="Rate limited or forbidden",
                severity=ErrorSeverity.RETRY,
                context={"status": status},
                source="http",
            )
        if status == 404:
            return DAOError(
                code=EC.API_NOT_FOUND,
                message=f"Resource not found: {exc.request.url}",
                severity=ErrorSeverity.HALT,
                source="http",
            )
        return DAOError(
            code=EC.API_SERVER_ERROR,
            message=f"HTTP {status}: {exc}",
            severity=ErrorSeverity.RETRY if status >= 500 else ErrorSeverity.HALT,
            context={"status": status},
            source="http",
        )
    return DAOError(
        code=EC.API_SERVER_ERROR,
        message=f"Unexpected error: {exc}",
        severity=ErrorSeverity.HALT,
        source="http",
    )
