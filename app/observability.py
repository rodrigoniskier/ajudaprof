from __future__ import annotations

import json
import uuid
from typing import Any


def new_request_id() -> str:
    return uuid.uuid4().hex[:12]


def log_event(logger, **fields: Any) -> None:
    """Registra uma linha de log estruturada (JSON), uma por evento.

    Nunca deve receber conteúdo de formulários, anexos, prompts ou respostas
    da IA — somente metadados técnicos (Protocolo RN, seção 16.1).
    """
    logger.info(json.dumps(fields, ensure_ascii=False, default=str))
