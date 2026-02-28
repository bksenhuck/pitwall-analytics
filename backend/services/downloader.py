"""
FastF1 Downloader Service

Wraps all FastF1 API calls with automatic retry and exponential backoff
when rate limits (HTTP 429) are hit.
"""
import logging
import time
from pathlib import Path
from typing import Any, Callable, Optional

import fastf1 as ff1

logger = logging.getLogger(__name__)

# Keywords that indicate a rate-limit or transient network error
_RATE_LIMIT_KEYWORDS = (
    "rate limit",
    "too many requests",
    "429",
    "ratelimit",
    "quota",
    "throttl",
    "connection",
    "timeout",
)


class FastF1Downloader:
    """
    Thin wrapper around the FastF1 library that retries on rate-limit errors.

    All public methods mirror their fastf1 counterparts but will block and
    retry (with exponential backoff) instead of crashing when the API limit
    is reached.

    Args:
        cache_dir: Path to the FastF1 local cache directory. If None, caching
                   is not configured (uses whatever was set externally).
        between_calls_delay: Seconds to wait between successful API calls as
                             proactive rate-limit avoidance (default: 10).
        initial_retry_wait: Seconds to wait after the first rate-limit hit
                            (doubles on every subsequent hit, max 1 h).
        max_retries: Maximum number of retry attempts per call before raising.
    """

    DEFAULT_BETWEEN_CALLS_DELAY = 10
    DEFAULT_INITIAL_RETRY_WAIT = 60
    DEFAULT_MAX_RETRIES = 20

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        between_calls_delay: int = DEFAULT_BETWEEN_CALLS_DELAY,
        initial_retry_wait: int = DEFAULT_INITIAL_RETRY_WAIT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        if cache_dir is not None:
            cache_dir.mkdir(parents=True, exist_ok=True)
            ff1.Cache.enable_cache(str(cache_dir))

        self.between_calls_delay = between_calls_delay
        self.initial_retry_wait = initial_retry_wait
        self.max_retries = max_retries
        self.api_calls = 0

    # ------------------------------------------------------------------
    # Public FastF1 wrappers
    # ------------------------------------------------------------------

    def get_event_schedule(self, season: int) -> Any:
        """Fetch the full event schedule for a season."""
        return self._with_retry(ff1.get_event_schedule, season)

    def get_event(self, season: int, event_name: str) -> Any:
        """Fetch a single event."""
        return self._with_retry(ff1.get_event, season, event_name)

    def get_session(self, season: int, event_name: str, session_type: str) -> Any:
        """Fetch a session object (does not load data yet)."""
        return self._with_retry(ff1.get_session, season, event_name, session_type)

    def load_session(self, session: Any, **load_kwargs) -> Any:
        """Load all requested data into a session object."""

        def _load():
            session.load(**load_kwargs)
            return session

        return self._with_retry(_load)

    # ------------------------------------------------------------------
    # Retry core
    # ------------------------------------------------------------------

    def _with_retry(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        Call *func* with *args*/*kwargs*, retrying on rate-limit / transient
        errors with exponential backoff.

        Between successful calls a fixed delay is applied to stay below the
        FastF1 API limit proactively.
        """
        wait = self.initial_retry_wait
        attempt = 0

        while True:
            try:
                result = func(*args, **kwargs)
                self.api_calls += 1
                if self.between_calls_delay > 0:
                    time.sleep(self.between_calls_delay)
                return result

            except Exception as exc:
                error_lower = str(exc).lower()
                is_retryable = any(kw in error_lower for kw in _RATE_LIMIT_KEYWORDS)

                if is_retryable and attempt < self.max_retries:
                    attempt += 1
                    logger.warning(
                        "Retryable error on attempt %d/%d (%s). Waiting %ds.",
                        attempt,
                        self.max_retries,
                        exc,
                        wait,
                    )
                    print(
                        f"\n  ⏳ Erro temporario (tentativa {attempt}/{self.max_retries}). "
                        f"Aguardando {wait}s antes de tentar novamente..."
                    )
                    time.sleep(wait)
                    wait = min(wait * 2, 3600)  # exponential backoff, cap at 1 h
                else:
                    raise
