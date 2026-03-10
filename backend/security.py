"""
API security utilities: rate limiter and admin key dependency.
"""
import os
import secrets

from fastapi import Header, HTTPException, Request

# ── Rate limit constants (overridable via env) ─────────────────────────────────
RATE_LIMIT_HEAVY = os.getenv("RATE_LIMIT_HEAVY", "20/minute")  # telemetry, session
RATE_LIMIT_LIGHT = os.getenv("RATE_LIMIT_LIGHT", "60/minute")  # seasons, stats, lists

# Loopback IPs are internal calls (Dash → FastAPI in the same process/container)
# They are exempt from rate limiting to avoid self-blocking.
_INTERNAL_IPS = {"127.0.0.1", "::1", "localhost"}


def _rate_limit_key(request: Request) -> str:
    """Return '__internal__' for loopback callers, remote IP otherwise."""
    try:
        from slowapi.util import get_remote_address
        ip = get_remote_address(request)
    except Exception:
        ip = request.client.host if request.client else "unknown"
    return "__internal__" if ip in _INTERNAL_IPS else ip


try:
    from slowapi import Limiter
    limiter = Limiter(key_func=_rate_limit_key)
    SLOWAPI_AVAILABLE = True
except ImportError:
    class _NoOpLimiter:
        def limit(self, *a, **kw):
            def decorator(func):
                return func
            return decorator
    limiter = _NoOpLimiter()  # type: ignore[assignment]
    SLOWAPI_AVAILABLE = False


async def require_admin_key(x_admin_key: str = Header(..., alias="X-Admin-Key")):
    """Validates X-Admin-Key header for destructive endpoints."""
    expected = os.getenv("ADMIN_API_KEY", "").strip()
    if not expected:
        raise HTTPException(503, "Admin endpoints are not configured on this server.")
    if not secrets.compare_digest(x_admin_key, expected):
        raise HTTPException(403, "Invalid admin key.")
