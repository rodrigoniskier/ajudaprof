#!/usr/bin/env python3
"""Confirma que os arquivos críticos pertencem ao mesmo pacote, sem chamar a API."""

from __future__ import annotations

import inspect
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.services.gemini_service import GeminiService  # noqa: E402
from app.services.prompts import build_prompt  # noqa: E402


def main() -> None:
    constructor_parameters = inspect.signature(GeminiService).parameters
    brief_prompt = build_prompt(
        "apostila",
        {"extensao_desejada": "Breve — 4 a 6 páginas"},
        [],
    )

    checks = {
        "método de orçamento dinâmico": hasattr(GeminiService, "output_token_limit"),
        "limite de entrada de apostila": "apostila_max_input_chars" in constructor_parameters,
        "limite de entrada de avaliação": "avaliacao_max_input_chars" in constructor_parameters,
        "orçamento da apostila breve": GeminiService.output_token_limit(
            "apostila", {"extensao_desejada": "Breve — 4 a 6 páginas"}
        )
        == 4_500,
        "orçamento da avaliação": GeminiService.output_token_limit(
            "avaliacao", {"numero_questoes": 10}
        )
        == 7_000,
        "meta de palavras da apostila": "1.600 a 2.400 palavras" in brief_prompt,
    }

    failed = [name for name, passed in checks.items() if not passed]
    version = (ROOT / "VERSAO.txt").read_text(encoding="utf-8").splitlines()[0]
    print(f"Pacote: {version}")
    print(f"GeminiService carregado de: {inspect.getfile(GeminiService)}")
    if failed:
        for name in failed:
            print(f"FALHA: {name}", file=sys.stderr)
        raise SystemExit("Instalação contém arquivos de versões diferentes.")

    print("OK: arquivos críticos pertencem à versão corrigida.")


if __name__ == "__main__":
    main()

