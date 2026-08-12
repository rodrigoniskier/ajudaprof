from __future__ import annotations

import json
import random
import time
from typing import Any

from pydantic import ValidationError

from ..errors import ConfigurationError, GenerationError
from .file_processor import SourceDocument
from .prompts import SYSTEM_INSTRUCTION, build_prompt
from .schemas import SCHEMAS

# Uma única retentativa curta, e só para falhas de rede/servidor claramente
# transitórias. Timeout não é retentado: a chamada já consumiu quase todo o
# orçamento de tempo do worker do PythonAnywhere. 429 e 4xx também não, pois
# não são passageiros (Protocolo RN, seção 9).
_TRANSIENT_STATUS_CODES = {500, 502, 503}
_TRANSIENT_EXCEPTION_NAMES = {"ServiceUnavailable", "InternalServerError", "APIConnectionError", "ConnectionError"}
_NON_TRANSIENT_STATUS_CODES = {400, 401, 403, 404, 408, 422, 429, 504}
_NON_TRANSIENT_EXCEPTION_NAMES = {
    "ResourceExhausted", "TooManyRequests", "Unauthorized", "PermissionDenied",
    "InvalidArgument", "FailedPrecondition",
}


class GeminiService:
    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        apostila_model: str | None = None,
        avaliacao_model: str | None = None,
        timeout_seconds: int = 180,
        apostila_max_input_chars: int = 160_000,
        avaliacao_max_input_chars: int = 240_000,
    ):
        self.api_key = api_key
        self.model = model
        self.apostila_model = apostila_model or model
        self.avaliacao_model = avaliacao_model or model
        self.timeout_seconds = max(30, min(int(timeout_seconds), 240))
        self.apostila_max_input_chars = max(20_000, int(apostila_max_input_chars))
        self.avaliacao_max_input_chars = max(40_000, int(avaliacao_max_input_chars))
        self._client = None

    def _get_client(self):
        if not self.api_key or self.api_key in {"cole-a-chave-aqui", "sua-chave-aqui"}:
            raise ConfigurationError(
                "A chave da API Gemini ainda não foi configurada no servidor. Consulte o guia de instalação."
            )
        if self._client is None:
            try:
                from google import genai
                from google.genai import types
            except ImportError as exc:
                raise ConfigurationError("O pacote google-genai não está instalado no ambiente virtual.") from exc
            http_options_kwargs: dict[str, Any] = {"timeout": self.timeout_seconds * 1000}
            # Evita que retentativas internas ultrapassem o limite do worker do
            # PythonAnywhere. O usuário poderá tentar novamente conscientemente.
            if hasattr(types, "HttpRetryOptions"):
                http_options_kwargs["retry_options"] = types.HttpRetryOptions(attempts=1)
            self._client = genai.Client(
                api_key=self.api_key,
                http_options=types.HttpOptions(**http_options_kwargs),
            )
        return self._client

    @staticmethod
    def output_token_limit(document_type: str, form_data: dict[str, Any]) -> int:
        if document_type == "avaliacao":
            try:
                total_questions = int(form_data.get("numero_questoes", 10))
            except (TypeError, ValueError):
                total_questions = 10
            return min(18_000, max(4_000, 1_500 + total_questions * 550))

        if document_type != "apostila":
            return {"planos-aula": 48_000}.get(document_type, 24_000)

        requested_length = str(form_data.get("extensao_desejada", "")).casefold()
        if "breve" in requested_length:
            return 4_500
        if "ampliada" in requested_length:
            return 12_000
        return 8_000

    def _source_text(
        self,
        document_type: str,
        source: SourceDocument,
        consumed_chars: int,
        *,
        per_source_limit: int | None = None,
    ) -> tuple[str, int]:
        text = source.text
        document_limits = {
            "apostila": self.apostila_max_input_chars,
            "avaliacao": self.avaliacao_max_input_chars,
        }
        document_limit = document_limits.get(document_type)
        if document_limit is None or not text:
            return text, consumed_chars + len(text)

        remaining = document_limit - consumed_chars
        if remaining <= 0:
            return "[ANEXO OMITIDO DO PROMPT POR LIMITE DE TAMANHO; REVISE AS FONTES ENVIADAS.]", consumed_chars
        allowed = min(remaining, per_source_limit) if per_source_limit else remaining
        if len(text) <= allowed:
            return text, consumed_chars + len(text)
        clipped = text[:allowed].rstrip()
        clipped += "\n\n[CONTEÚDO TRUNCADO PARA MANTER A GERAÇÃO DENTRO DO TEMPO DO SERVIDOR.]"
        return clipped, consumed_chars + allowed

    @staticmethod
    def _is_transient(exc: Exception) -> bool:
        name = type(exc).__name__
        status_code = getattr(exc, "code", None)
        if name in _NON_TRANSIENT_EXCEPTION_NAMES or status_code in _NON_TRANSIENT_STATUS_CODES:
            return False
        if "timeout" in name.casefold() or "deadline" in name.casefold():
            return False
        return status_code in _TRANSIENT_STATUS_CODES or name in _TRANSIENT_EXCEPTION_NAMES

    @staticmethod
    def _timeout_message(document_type: str) -> str:
        if document_type == "apostila":
            return (
                "A apostila ultrapassou o limite de tempo seguro. Use a extensão Breve, envie o plano em "
                "DOCX ou PDF com texto selecionável e remova referências opcionais muito extensas."
            )
        if document_type == "avaliacao":
            return (
                "A avaliação ultrapassou o limite de tempo seguro. Reduza a quantidade de questões e envie "
                "somente as apostilas e os planos diretamente relacionados aos conteúdos avaliados, de "
                "preferência em DOCX ou PDF com texto selecionável."
            )
        return "A geração ultrapassou o limite de tempo seguro. Reduza os anexos e tente novamente."

    def generate(
        self,
        document_type: str,
        form_data: dict[str, Any],
        sources: list[SourceDocument],
        *,
        metrics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Gera o documento. Se `metrics` for passado, é preenchido com model,
        retry_count e tokens de entrada/saída para fins de log estruturado
        (Protocolo RN, seção 16.1) — nunca com conteúdo de formulários/anexos."""
        if document_type not in SCHEMAS:
            raise GenerationError("Tipo de documento não reconhecido.")

        try:
            from google.genai import types
        except ImportError as exc:
            raise ConfigurationError("O pacote google-genai não está instalado no ambiente virtual.") from exc

        schema = SCHEMAS[document_type]
        contents: list[Any] = [build_prompt(document_type, form_data, sources)]
        consumed_chars = 0
        text_source_count = sum(1 for source in sources if source.text)
        evaluation_per_source_limit = None
        if document_type == "avaliacao" and text_source_count:
            # Divide o orçamento entre todas as apostilas e planos, evitando
            # que o primeiro arquivo consuma todo o contexto disponível.
            evaluation_per_source_limit = max(8_000, self.avaliacao_max_input_chars // text_source_count)
        for source in sources:
            marker = f"\n\n--- ANEXO: {source.label} | {source.filename} ---\n"
            contents.append(marker)
            if source.inline_bytes is not None:
                contents.append(types.Part.from_bytes(data=source.inline_bytes, mime_type=source.mime_type))
            else:
                source_text, consumed_chars = self._source_text(
                    document_type,
                    source,
                    consumed_chars,
                    per_source_limit=evaluation_per_source_limit,
                )
                contents.append(source_text)

        temperatures = {"apostila": 0.35, "avaliacao": 0.25}
        max_tokens = self.output_token_limit(document_type, form_data)
        selected_model = {
            "apostila": self.apostila_model,
            "avaliacao": self.avaliacao_model,
        }.get(document_type, self.model)
        if metrics is not None:
            metrics["model"] = selected_model

        attempt = 0
        max_attempts = 2  # geração original + no máximo 1 retentativa transitória
        while True:
            try:
                response = self._get_client().models.generate_content(
                    model=selected_model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        temperature=temperatures.get(document_type, 0.2),
                        max_output_tokens=max_tokens,
                        response_mime_type="application/json",
                        response_json_schema=schema.model_json_schema(),
                    ),
                )
                if not getattr(response, "text", None):
                    raise GenerationError("O Gemini não devolveu conteúdo utilizável. Tente novamente.")
                usage = getattr(response, "usage_metadata", None)
                if metrics is not None:
                    metrics["retry_count"] = attempt
                    if usage is not None:
                        metrics["tokens_input"] = getattr(usage, "prompt_token_count", None)
                        metrics["tokens_output"] = getattr(usage, "candidates_token_count", None)
                parsed = json.loads(response.text)
                validated = schema.model_validate(parsed)
                return validated.model_dump()
            except ConfigurationError:
                raise
            except GenerationError:
                raise
            except (json.JSONDecodeError, ValidationError) as exc:
                if metrics is not None:
                    metrics["retry_count"] = attempt
                    metrics["error_type"] = "AI_OUTPUT_SCHEMA_ERROR"
                raise GenerationError(
                    "A IA devolveu uma estrutura incompleta. Tente novamente; se persistir, reduza os anexos."
                ) from exc
            except Exception as exc:
                if attempt + 1 < max_attempts and self._is_transient(exc):
                    attempt += 1
                    time.sleep(random.uniform(0.4, 1.2))
                    continue
                # Não expor resposta, chave, prompt ou dados anexados.
                name = type(exc).__name__
                status_code = getattr(exc, "code", None)
                timeout_error = (
                    "timeout" in name.casefold()
                    or "deadline" in name.casefold()
                    or status_code in {408, 504}
                )
                if name in {"ResourceExhausted", "TooManyRequests"} or status_code == 429:
                    message = "O limite temporário da API Gemini foi atingido. Aguarde e tente novamente."
                elif timeout_error:
                    message = self._timeout_message(document_type)
                elif name in {"Unauthorized", "PermissionDenied"} or status_code in {401, 403}:
                    message = "A API Gemini recusou a solicitação. Verifique a chave, o modelo e o faturamento."
                else:
                    message = "Não foi possível concluir a geração na API Gemini. Tente novamente."
                if metrics is not None:
                    metrics["retry_count"] = attempt
                    metrics["error_type"] = name
                raise GenerationError(message) from exc


class FakeGeminiService:
    """Dados determinísticos para testes locais; não chama serviços externos."""

    def generate(
        self,
        document_type: str,
        form_data: dict[str, Any],
        sources: list[SourceDocument],
        *,
        metrics: dict[str, Any] | None = None,
    ):
        if metrics is not None:
            metrics.update({"model": "fake", "retry_count": 0, "tokens_input": 0, "tokens_output": 0})
        fixtures = {
            "ementa": {
                "ementa": (
                    "Fundamentos conceituais e aplicados do componente curricular. Integração entre bases "
                    "científicas, raciocínio crítico, tomada de decisão e atuação ética, em consonância com "
                    "o projeto pedagógico do curso e com as diretrizes curriculares nacionais."
                ),
                "bibliografia_basica": [
                    "SOBRENOME, Nome. Título da obra básica. 1. ed. Cidade: Editora, 2025.",
                    "SOBRENOME, Nome. Fundamentos da área. 2. ed. Cidade: Editora, 2024.",
                ],
                "bibliografia_complementar": [
                    "SOBRENOME, Nome. Estudos aplicados. Cidade: Editora, 2023.",
                    "[SUGESTÃO — CONFERIR] Diretriz profissional atualizada da área.",
                ],
                "notas_para_revisao": ["Conferir a edição e a disponibilidade das referências na biblioteca."],
            },
            "plano-ensino": {
                "ementa": "Estudo integrado dos fundamentos, aplicações e implicações profissionais do componente.",
                "objetivos": {
                    "cognitivos": ["Analisar os fundamentos do componente em situações acadêmicas e profissionais."],
                    "habilidades": ["Aplicar conceitos na resolução de problemas contextualizados."],
                    "atitudes": ["Atuar com responsabilidade, colaboração e compromisso ético."],
                },
                "unidades": [
                    {"unidade": "I", "carga_horaria": "30 h", "topicos": form_data.get("topicos", ["Tópico 1"])[:3]},
                    {"unidade": "II", "carga_horaria": "30 h", "topicos": form_data.get("topicos", ["Tópico 2"])[3:] or ["Integração e aplicação"]},
                ],
                "estrategia_ensino": ["Aula expositivo-dialogada", "Estudo de caso", "Aprendizagem baseada em problemas"],
                "recursos_disponiveis": ["Quadro", "Projetor multimídia", "Ambiente virtual de aprendizagem"],
                "avaliacao": ["Avaliação diagnóstica inicial.", "Atividades formativas com feedback.", "Avaliação somativa contextualizada."],
                "bibliografia_basica": ["SOBRENOME, Nome. Obra básica. Cidade: Editora, 2025."],
                "bibliografia_complementar": ["SOBRENOME, Nome. Obra complementar. Cidade: Editora, 2024."],
                "notas_para_revisao": ["Adequar o sistema de notas ao regulamento institucional vigente."],
            },
            "cronograma": {
                "aulas": [
                    {
                        "numero": index,
                        "data": f"{3 + (index - 1) * 7:02d}/08/2026",
                        "dia_semana": "Segunda-feira",
                        "horario": "13:00–15:30",
                        "carga_horaria": "3 h/a",
                        "natureza": "Teórica",
                        "topico": topic,
                        "docente": (form_data.get("docentes") or ["Docente responsável"])[0],
                        "observacoes": "",
                    }
                    for index, topic in enumerate(form_data.get("topicos", ["Tópico 1", "Tópico 2", "Tópico 3"]), 1)
                ],
                "carga_horaria_teorica_planejada": form_data.get("ch_teorica", "9 h/a"),
                "carga_horaria_pratica_planejada": form_data.get("ch_pratica", "0 h/a"),
                "alertas_calendario": [],
                "notas_para_revisao": ["Datas de demonstração: substituir após analisar o calendário oficial."],
            },
            "planos-aula": {
                "planos": [
                    {
                        "numero": 1,
                        "data": "03/08/2026",
                        "tema": form_data.get("aula_alvo") or "Fundamentos do componente",
                        "atividade": "TEÓRICA",
                        "duracao": "3 h/a",
                        "conhecimentos": ["Compreender os conceitos essenciais do tema."],
                        "habilidades": ["Analisar uma situação contextualizada e propor uma solução fundamentada."],
                        "atitudes": ["Demonstrar postura ética, colaborativa e responsável."],
                        "metodologia": ["Problematização inicial", "Exposição dialogada", "Estudo de caso em pequenos grupos"],
                        "recursos_didaticos": ["Projetor multimídia", "Quadro", "Ambiente virtual"],
                        "procedimento_avaliativo": ["Questões diagnósticas", "Feedback formativo ao final da atividade"],
                        "bibliografia": ["SOBRENOME, Nome. Obra de referência. Cidade: Editora, 2025."],
                        "notas_para_revisao": [],
                    }
                ],
                "notas_gerais": [],
            },
            "apostila": {
                "titulo": form_data.get("titulo_aula") or "Fundamentos do componente",
                "apresentacao": "Esta apostila organiza os conceitos essenciais da aula e propõe conexões com a prática profissional.",
                "objetivos_aprendizagem": ["Explicar os conceitos centrais.", "Aplicar o conteúdo a uma situação contextualizada."],
                "secoes": [
                    {
                        "titulo": "1. Conceitos fundamentais",
                        "paragrafos": [
                            "O estudo do tema exige a integração entre conceitos, evidências e contexto profissional. A compreensão começa pela definição dos elementos centrais e de suas relações.",
                            "A análise deve distinguir informações essenciais de aspectos acessórios, permitindo decisões justificadas e comunicação clara.",
                        ],
                        "pontos_chave": ["Conceito", "Relação", "Aplicação"],
                        "exemplo_aplicado": "Analise uma situação profissional e identifique quais conceitos explicam o problema apresentado.",
                    },
                    {
                        "titulo": "2. Aplicação e tomada de decisão",
                        "paragrafos": ["A aplicação do conhecimento depende da interpretação do contexto e da comparação de alternativas plausíveis."],
                        "pontos_chave": ["Contextualização", "Raciocínio crítico", "Justificativa"],
                        "exemplo_aplicado": "Compare duas condutas e justifique a alternativa mais coerente com os dados disponíveis.",
                    },
                ],
                "sintese": ["Defina o problema.", "Relacione conceitos e evidências.", "Justifique a decisão."],
                "questoes_revisao": ["Qual é o conceito central da aula?", "Como ele se aplica à prática?"],
                "orientacoes_respostas": ["A resposta deve definir o conceito e apresentar uma aplicação coerente."],
                "referencias": ["SOBRENOME, Nome. Obra de referência. Cidade: Editora, 2025."],
                "avisos_validacao": ["Conteúdo de demonstração; revisar antes do uso acadêmico."],
            },
            "avaliacao": {
                "titulo": form_data.get("titulo_avaliacao") or "Avaliação da aprendizagem",
                "instrucoes": ["Leia atentamente cada questão.", "Responda com clareza e apresente justificativa quando solicitado."],
                "questoes": [
                    {
                        "numero": 1,
                        "tipo": "Múltipla escolha — resposta única",
                        "nivel_bloom": "Aplicar",
                        "dificuldade": "Média",
                        "valor": "1,0 ponto",
                        "enunciado": "Diante de uma situação contextualizada, qual alternativa aplica corretamente o conceito estudado?",
                        "alternativas": [
                            {"letra": "A", "texto": "Aplicar o conceito sem considerar o contexto."},
                            {"letra": "B", "texto": "Relacionar conceito, evidências e contexto antes de decidir."},
                            {"letra": "C", "texto": "Escolher a alternativa mais longa."},
                            {"letra": "D", "texto": "Desconsiderar dados que contradizem a hipótese inicial."},
                        ],
                        "resposta_correta": "B",
                        "justificativa": "A aplicação adequada integra o conceito às evidências e ao contexto apresentado.",
                        "rubrica": [],
                    },
                    {
                        "numero": 2,
                        "tipo": "Discursiva",
                        "nivel_bloom": "Analisar",
                        "dificuldade": "Difícil",
                        "valor": "2,0 pontos",
                        "enunciado": "Analise o problema apresentado, proponha uma solução e justifique-a com os conteúdos estudados.",
                        "alternativas": [],
                        "resposta_correta": "Resposta autoral fundamentada nos conceitos da aula.",
                        "justificativa": "A questão avalia integração conceitual, análise e argumentação.",
                        "rubrica": ["0,5: identifica o problema", "0,5: aplica conceitos", "0,5: justifica", "0,5: comunica com clareza"],
                    },
                ],
                "observacoes_revisao_docente": ["Validar enunciados, gabarito e pontuação antes da aplicação."],
            },
        }
        return fixtures[document_type]
