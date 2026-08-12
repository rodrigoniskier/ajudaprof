from __future__ import annotations

import hashlib
import hmac
import io
import time
from collections import defaultdict, deque
from threading import Lock

from flask import Request, current_app, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from .errors import AppError


class InMemoryRequest(Request):
    """Mantém uploads na memória e evita criar arquivos temporários no servidor.

    O limite global MAX_CONTENT_LENGTH protege o processo contra envios grandes.
    """

    def _get_file_stream(self, total_content_length, content_type, filename=None, content_length=None):
        return io.BytesIO()


def create_csrf_token() -> str:
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="documenta-csrf")
    # O token não contém identificação do usuário e não exige cookie/sessão.
    return serializer.dumps({"purpose": "generate-document"})


def validate_csrf_token(token: str | None, max_age: int = 7200) -> None:
    if not token:
        raise AppError("A página expirou. Recarregue-a e tente novamente.", 400, "csrf_missing")
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="documenta-csrf")
    try:
        payload = serializer.loads(token, max_age=max_age)
    except SignatureExpired as exc:
        raise AppError("A página expirou. Recarregue-a e tente novamente.", 400, "csrf_expired") from exc
    except BadSignature as exc:
        raise AppError("Não foi possível validar a solicitação.", 400, "csrf_invalid") from exc
    if payload.get("purpose") != "generate-document":
        raise AppError("Não foi possível validar a solicitação.", 400, "csrf_invalid")


class MemoryRateLimiter:
    """Limitador transitório, em memória, sem banco de dados.

    O identificador técnico é HMAC do endereço de rede e expira junto com a
    janela. Ele não é incluído em mensagens nem persistido em arquivo.
    """

    def __init__(self, max_requests: int = 12, window_seconds: int = 600):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def _key(self) -> str:
        remote = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
        secret = current_app.config["SECRET_KEY"].encode("utf-8")
        return hmac.new(secret, remote.encode("utf-8"), hashlib.sha256).hexdigest()

    def check(self) -> None:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        key = self._key()
        with self._lock:
            bucket = self._buckets[key]
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= self.max_requests:
                raise AppError(
                    "Muitas gerações em pouco tempo. Aguarde alguns minutos e tente novamente.",
                    429,
                    "rate_limited",
                )
            bucket.append(now)


rate_limiter = MemoryRateLimiter()


def apply_security_headers(response):
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "img-src 'self' data:; "
        "style-src 'self'; "
        "script-src 'self'; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'"
    )
    if request.path.startswith("/gerar/"):
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
    return response
