from __future__ import annotations

import os
from pathlib import Path


def _as_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _as_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "sim", "on"}


class Config:
    BASE_DIR = Path(__file__).resolve().parent.parent

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    # A apostila é o fluxo mais longo. O Flash-Lite reduz a latência e mantém
    # suporte a PDFs e saída JSON estruturada.
    GEMINI_APOSTILA_MODEL = os.getenv("GEMINI_APOSTILA_MODEL", "gemini-3.5-flash-lite")
    GEMINI_AVALIACAO_MODEL = os.getenv("GEMINI_AVALIACAO_MODEL", "gemini-3.5-flash-lite")
    GEMINI_TIMEOUT_SECONDS = _as_int("GEMINI_TIMEOUT_SECONDS", 180)
    APOSTILA_MAX_INPUT_CHARS = _as_int("APOSTILA_MAX_INPUT_CHARS", 160_000)
    AVALIACAO_MAX_INPUT_CHARS = _as_int("AVALIACAO_MAX_INPUT_CHARS", 240_000)
    GEMINI_DATA_MODE = os.getenv("GEMINI_DATA_MODE", "unpaid").strip().lower()
    USE_FAKE_GEMINI = _as_bool("USE_FAKE_GEMINI", False)

    MAX_REQUEST_MB = _as_int("MAX_REQUEST_MB", 30)
    MAX_FILE_MB = _as_int("MAX_FILE_MB", 15)
    MAX_FILES_PER_REQUEST = _as_int("MAX_FILES_PER_REQUEST", 20)
    MAX_CONTENT_LENGTH = MAX_REQUEST_MB * 1024 * 1024

    INSTITUTION_NAME = os.getenv("INSTITUTION_NAME", "Instituição de Ensino Superior")
    INSTITUTION_UNIT = os.getenv("INSTITUTION_UNIT", "Pró-Reitoria Acadêmica / Coordenação do Curso")
    INSTITUTION_WEBSITE = os.getenv("INSTITUTION_WEBSITE", "")
    INSTITUTION_ADDRESS = os.getenv("INSTITUTION_ADDRESS", "")
    INSTITUTION_FOOTER = os.getenv("INSTITUTION_FOOTER", "")
    PRIVACY_CONTACT_EMAIL = os.getenv("PRIVACY_CONTACT_EMAIL", "privacidade@exemplo.edu.br")
    LOGO_PATH = BASE_DIR / "app" / "static" / "img" / "logo.png"

    # Nenhuma sessão de usuário é necessária. Estes parâmetros ficam definidos
    # por segurança caso uma extensão futura passe a usar cookies de sessão.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = True
    PERMANENT_SESSION_LIFETIME = 1800

    JSON_SORT_KEYS = False
    PROPAGATE_EXCEPTIONS = False


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret"
    GEMINI_API_KEY = "test-key"
    GEMINI_TIMEOUT_SECONDS = 30
    USE_FAKE_GEMINI = True
    SESSION_COOKIE_SECURE = False
