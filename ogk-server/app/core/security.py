import hashlib
import hmac
import math
import secrets
import time
from collections import deque
from collections.abc import Callable, Iterable

from fastapi import Depends, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.errors import AppError

SESSION_COOKIE = "ogk_session"
SESSION_MAX_AGE = 12 * 60 * 60
CSRF_COOKIE = "ogk_csrf"
CSRF_HEADER = "x-csrf-token"
UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def new_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE, token, max_age=SESSION_MAX_AGE, path="/", httponly=True, secure=True, samesite="lax"
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, secure=True, samesite="lax")


def set_csrf_cookie(response: Response, token: str | None = None) -> None:
    response.set_cookie(CSRF_COOKIE, token or new_token(), path="/", httponly=False, secure=True, samesite="lax")


def _sets_cookie(response: Response, name: str) -> bool:
    return any(v.startswith(f"{name}=") for v in response.headers.getlist("set-cookie"))


class CSRFMiddleware(BaseHTTPMiddleware):
    """Double-submit: request ghi dưới /api phải có header X-CSRF-Token bằng cookie ogk_csrf."""

    def __init__(self, app, exempt_prefixes: Iterable[str] = ()) -> None:
        super().__init__(app)
        self.exempt_prefixes = tuple(exempt_prefixes)

    def _needs_check(self, request: Request) -> bool:
        path = request.url.path
        return (
            request.method in UNSAFE_METHODS
            and (path == "/api" or path.startswith("/api/"))
            and not any(path.startswith(prefix) for prefix in self.exempt_prefixes)
        )

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        cookie = request.cookies.get(CSRF_COOKIE)
        if self._needs_check(request):
            header = request.headers.get(CSRF_HEADER)
            if not cookie or not header or not hmac.compare_digest(cookie.encode(), header.encode()):
                return JSONResponse({"detail": "csrf_failed"}, status_code=403)
        response = await call_next(request)
        if not cookie and not _sets_cookie(response, CSRF_COOKIE):
            set_csrf_cookie(response)
        return response


class RateLimiter:
    """Cửa sổ trượt trong bộ nhớ; đủ cho một tiến trình server."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}

    def hit(self, key: str, limit: int, window: float) -> float | None:
        """Ghi một lần gọi. Trả số giây phải chờ nếu vượt giới hạn, ngược lại None."""
        now = self._clock()
        hits = self._hits.setdefault(key, deque())
        while hits and hits[0] <= now - window:
            hits.popleft()
        if len(hits) >= limit:
            return hits[0] + window - now
        hits.append(now)
        return None


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def rate_limit(scope: str, limit: int, window: float = 60):
    async def dependency(request: Request) -> None:
        limiter: RateLimiter = request.app.state.rate_limiter
        retry = limiter.hit(f"{scope}:{client_ip(request)}", limit, window)
        if retry is not None:
            raise AppError(429, "rate_limited", headers={"Retry-After": str(max(1, math.ceil(retry)))})

    return Depends(dependency)
