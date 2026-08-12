#!/usr/bin/env python3
"""Gera amostras locais sem chamar a API Gemini.

Uso:
    python scripts/smoke_generate.py --output generated_demo
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.docx_builder import build_artifact  # noqa: E402
from app.services.gemini_service import FakeGeminiService  # noqa: E402


FORMS = {
    "ementa": {"curso": "Medicina", "componente": "Componente Demonstrativo", "carga_horaria": "60 h/a", "periodo": "4º"},
    "plano-ensino": {
        "curso": "Medicina", "componente": "Componente Demonstrativo", "periodo": "4º",
        "turno": "Vespertino", "modalidade": "Presencial", "semestre_letivo": "2026.2",
        "professor_responsavel": "Professor Responsável", "ch_semanal": "3 h/a", "ch_semestral": "60 h/a",
        "topicos": ["Fundamentos", "Aplicação", "Integração", "Avaliação"],
    },
    "cronograma": {
        "curso": "Medicina", "componente": "Componente Demonstrativo", "periodo": "4º", "turma": "A",
        "semestre_letivo": "2026.2", "coordenador": "Coordenação", "docentes": ["Docente A", "Docente B"],
        "ch_teorica": "30 h/a", "ch_pratica": "30 h/a", "topicos": ["Fundamentos", "Aplicação", "Integração"],
    },
    "planos-aula": {
        "curso": "Medicina", "componente": "Componente Demonstrativo", "modalidade": "Presencial",
        "semestre_letivo": "2026.2", "periodo": "4º", "turmas": "A, B", "coordenador": "Coordenação",
        "aula_alvo": "Aula 1",
    },
    "apostila": {
        "curso": "Medicina", "componente": "Componente Demonstrativo", "titulo_aula": "Fundamentos do componente",
        "publico_alvo": "Estudantes do 4º período", "nivel_profundidade": "Intermediário",
        "extensao_desejada": "Regular — 7 a 12 páginas",
    },
    "avaliacao": {
        "curso": "Medicina", "componente": "Componente Demonstrativo", "titulo_avaliacao": "Avaliação 1",
        "professor": "Docente", "turma": "A", "data_avaliacao": "01/09/2026", "duracao_avaliacao": "90 minutos",
        "valor_total": "10,0 pontos",
    },
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="generated_demo")
    args = parser.parse_args()

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parent.parent
    config = {
        "LOGO_PATH": root / "app" / "static" / "img" / "logo.png",
        "INSTITUTION_NAME": "Centro Universitário de João Pessoa",
        "INSTITUTION_UNIT": "Pró-Reitoria Acadêmica / Coordenação do Curso",
        "INSTITUTION_WEBSITE": "www.unipe.edu.br",
        "INSTITUTION_ADDRESS": "João Pessoa — PB",
        "INSTITUTION_FOOTER": "Documento demonstrativo sujeito à revisão docente.",
    }
    service = FakeGeminiService()
    for document_type, form in FORMS.items():
        generated = service.generate(document_type, form, [])
        artifact = build_artifact(document_type, generated, form, config)
        path = output / artifact.filename
        path.write_bytes(artifact.content.getvalue())
        print(path)


if __name__ == "__main__":
    main()

