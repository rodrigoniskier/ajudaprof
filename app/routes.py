from __future__ import annotations

from datetime import date
from time import monotonic
from typing import Any

from flask import Blueprint, current_app, jsonify, render_template, request, send_file

from .errors import AppError
from .observability import log_event, new_request_id
from .security import create_csrf_token, rate_limiter, validate_csrf_token
from .services.docx_builder import build_artifact
from .services.file_processor import collect_sources
from .services.output_validation import validate_generated_output
from .services.prompts import PROMPT_VERSIONS


bp = Blueprint("main", __name__)
DOCUMENT_TYPES = {"ementa", "plano-ensino", "cronograma", "planos-aula", "apostila", "avaliacao"}


def _text(name: str, label: str, *, required: bool = True, max_length: int = 5000) -> str:
    value = (request.form.get(name) or "").strip()
    if required and not value:
        raise AppError(f"Preencha o campo “{label}”.")
    if len(value) > max_length:
        raise AppError(f"O campo “{label}” ultrapassa o limite de {max_length} caracteres.")
    return value


def _list(name: str, label: str, *, required: bool = False, max_items: int = 250) -> list[str]:
    values = [value.strip() for value in request.form.getlist(name) if value and value.strip()]
    if required and not values:
        raise AppError(f"Inclua ao menos um item em “{label}”.")
    if len(values) > max_items:
        raise AppError(f"“{label}” aceita no máximo {max_items} itens.")
    return values


def _integer(name: str, label: str, *, minimum: int = 0, maximum: int = 1000) -> int:
    raw = _text(name, label)
    try:
        value = int(raw)
    except ValueError as exc:
        raise AppError(f"Informe um número inteiro em “{label}”.") from exc
    if not minimum <= value <= maximum:
        raise AppError(f"“{label}” deve estar entre {minimum} e {maximum}.")
    return value


def _validate_consent_and_csrf() -> None:
    validate_csrf_token(request.form.get("csrf_token"))
    if request.form.get("privacy_consent") != "yes":
        raise AppError("Confirme a ciência sobre o processamento temporário e a revisão docente.")


def _files(name: str, label: str, *, required: bool = False):
    files = [item for item in request.files.getlist(name) if item and item.filename]
    if required and not files:
        raise AppError(f"Anexe “{label}”.")
    return files


def _parse_ementa() -> tuple[dict[str, Any], list[tuple[str, list]]]:
    form = {
        "curso": _text("ementa_curso", "Curso"),
        "componente": _text("ementa_componente", "Componente curricular"),
        "carga_horaria": _text("ementa_carga_horaria", "Carga horária"),
        "periodo": _text("ementa_periodo", "Período recomendado", required=False),
        "observacoes": _text("ementa_observacoes", "Orientações adicionais", required=False, max_length=4000),
    }
    groups = [
        ("Projeto Pedagógico do Curso (PPC)", _files("ementa_ppc", "o PPC do curso", required=True)),
        ("Diretrizes Curriculares Nacionais (DCNs)", _files("ementa_dcns", "as DCNs", required=True)),
    ]
    return form, groups


def _parse_plano_ensino() -> tuple[dict[str, Any], list[tuple[str, list]]]:
    form = {
        "curso": _text("pe_curso", "Curso"),
        "componente": _text("pe_componente", "Componente curricular"),
        "periodo": _text("pe_periodo", "Período"),
        "turno": _text("pe_turno", "Turno"),
        "modalidade": _text("pe_modalidade", "Modalidade"),
        "semestre_letivo": _text("pe_semestre", "Semestre letivo"),
        "professor_responsavel": _text("pe_professor", "Professor responsável"),
        "ch_semanal": _text("pe_ch_semanal", "Carga horária semanal"),
        "ch_semestral": _text("pe_ch_semestral", "Carga horária semestral"),
        "topicos": _list("pe_topicos[]", "Tópicos das aulas", required=True),
        "orientacoes": _text("pe_orientacoes", "Orientações adicionais", required=False, max_length=4000),
    }
    groups = [
        ("Ementa vigente", _files("pe_ementa", "a ementa", required=False)),
        ("Projeto Pedagógico do Curso (PPC)", _files("pe_ppc", "o PPC", required=False)),
        ("Diretrizes Curriculares Nacionais (DCNs)", _files("pe_dcns", "as DCNs", required=False)),
    ]
    return form, groups


def _parse_cronograma() -> tuple[dict[str, Any], list[tuple[str, list]]]:
    weekdays = _list("cr_dia[]", "Dias de aula", required=True, max_items=7)
    starts = _list("cr_inicio[]", "Horários iniciais", required=True, max_items=7)
    ends = _list("cr_fim[]", "Horários finais", required=True, max_items=7)
    day_teachers = request.form.getlist("cr_docente_dia[]")
    if not (len(weekdays) == len(starts) == len(ends)):
        raise AppError("Complete dia, início e término em cada encontro semanal.")
    meetings = []
    for index, weekday in enumerate(weekdays):
        teacher = day_teachers[index].strip() if index < len(day_teachers) else ""
        meetings.append({"dia": weekday, "inicio": starts[index], "fim": ends[index], "docente_preferencial": teacher})

    start_date = _text("cr_data_inicio", "Data inicial")
    end_date = _text("cr_data_fim", "Data final")
    try:
        parsed_start = date.fromisoformat(start_date)
        parsed_end = date.fromisoformat(end_date)
    except ValueError as exc:
        raise AppError("Informe datas inicial e final válidas.") from exc
    if parsed_end < parsed_start:
        raise AppError("A data final deve ser posterior à data inicial.")

    docentes = [line.strip() for line in _text("cr_docentes", "Docentes").splitlines() if line.strip()]
    form = {
        "curso": _text("cr_curso", "Curso"),
        "componente": _text("cr_componente", "Componente curricular"),
        "docentes": docentes,
        "coordenador": _text("cr_coordenador", "Coordenador do componente"),
        "periodo": _text("cr_periodo", "Período"),
        "semestre_letivo": _text("cr_semestre", "Semestre letivo"),
        "turma": _text("cr_turma", "Turma"),
        "ch_teorica": _text("cr_ch_teorica", "Carga horária teórica"),
        "ch_pratica": _text("cr_ch_pratica", "Carga horária prática"),
        "data_inicio": start_date,
        "data_fim": end_date,
        "encontros_semanais": meetings,
        "topicos": _list("cr_topicos[]", "Tópicos das aulas", required=True),
        "orientacoes": _text("cr_orientacoes", "Orientações adicionais", required=False, max_length=4000),
    }
    groups = [("Calendário acadêmico oficial da IES", _files("cr_calendario", "o calendário oficial", required=False))]
    return form, groups


def _parse_planos_aula() -> tuple[dict[str, Any], list[tuple[str, list]]]:
    form = {
        "curso": _text("pa_curso", "Curso"),
        "componente": _text("pa_componente", "Componente curricular"),
        "modalidade": _text("pa_modalidade", "Modalidade"),
        "semestre_letivo": _text("pa_semestre", "Semestre letivo"),
        "periodo": _text("pa_periodo", "Período"),
        "turmas": _text("pa_turmas", "Turma(s)"),
        "coordenador": _text("pa_coordenador", "Coordenador"),
        "aula_alvo": _text("pa_aula_alvo", "Aula ou intervalo desejado", required=False),
        "orientacoes": _text("pa_orientacoes", "Orientações adicionais", required=False, max_length=4000),
    }
    groups = [
        ("Cronograma de aulas", _files("pa_cronograma", "o cronograma", required=True)),
        ("Diretrizes Curriculares Nacionais (DCNs)", _files("pa_dcns", "as DCNs", required=True)),
        ("Ementa do componente", _files("pa_ementa", "a ementa", required=True)),
    ]
    return form, groups


def _parse_apostila() -> tuple[dict[str, Any], list[tuple[str, list]]]:
    form = {
        "curso": _text("ap_curso", "Curso"),
        "componente": _text("ap_componente", "Componente curricular"),
        "titulo_aula": _text("ap_titulo", "Título da aula", required=False),
        "publico_alvo": _text("ap_publico", "Público-alvo"),
        "nivel_profundidade": _text("ap_nivel", "Nível de profundidade"),
        "extensao_desejada": _text("ap_extensao", "Extensão desejada"),
        "orientacoes": _text("ap_orientacoes", "Orientações adicionais", required=False, max_length=5000),
    }
    groups = [
        ("Plano individual da aula", _files("ap_plano", "o plano individual da aula", required=True)),
        ("Materiais de referência opcionais", _files("ap_referencias", "os materiais de referência", required=False)),
    ]
    return form, groups


def _parse_avaliacao() -> tuple[dict[str, Any], list[tuple[str, list]]]:
    total_questions = _integer("av_numero_questoes", "Número total de questões", minimum=1, maximum=30)
    types = _list("av_tipo[]", "Tipos de questão", required=True, max_items=20)
    quantities = _list("av_quantidade[]", "Quantidades por tipo", required=True, max_items=20)
    values = request.form.getlist("av_valor[]")
    alternatives = request.form.getlist("av_alternativas[]")
    other_types = request.form.getlist("av_outro[]")
    if len(types) != len(quantities):
        raise AppError("Complete o tipo e a quantidade em cada grupo de questões.")
    specs = []
    counted = 0
    for index, question_type in enumerate(types):
        try:
            quantity = int(quantities[index])
        except (ValueError, IndexError) as exc:
            raise AppError("As quantidades por tipo devem ser números inteiros.") from exc
        if quantity < 1 or quantity > 30:
            raise AppError("Cada grupo deve ter entre 1 e 30 questões.")
        counted += quantity
        specs.append(
            {
                "tipo": question_type,
                "quantidade": quantity,
                "valor_por_questao": values[index].strip() if index < len(values) else "",
                "numero_alternativas": alternatives[index].strip() if index < len(alternatives) else "",
                "descricao_outro_tipo": other_types[index].strip() if index < len(other_types) else "",
            }
        )
    if counted != total_questions:
        raise AppError(
            f"A soma das quantidades por tipo ({counted}) deve ser igual ao total de questões ({total_questions})."
        )

    difficulties = {
        "facil_percentual": _integer("av_facil", "Percentual fácil", minimum=0, maximum=100),
        "media_percentual": _integer("av_media", "Percentual médio", minimum=0, maximum=100),
        "dificil_percentual": _integer("av_dificil", "Percentual difícil", minimum=0, maximum=100),
    }
    if sum(difficulties.values()) != 100:
        raise AppError("Os percentuais de dificuldade devem somar 100%.")

    form = {
        "curso": _text("av_curso", "Curso"),
        "componente": _text("av_componente", "Componente curricular"),
        "titulo_avaliacao": _text("av_titulo", "Título da avaliação"),
        "professor": _text("av_professor", "Professor(a)"),
        "turma": _text("av_turma", "Turma"),
        "data_avaliacao": _text("av_data", "Data da avaliação", required=False),
        "duracao_avaliacao": _text("av_duracao", "Duração"),
        "valor_total": _text("av_valor_total", "Valor total"),
        "numero_questoes": total_questions,
        "especificacoes_questoes": specs,
        "taxonomia_bloom": _list("av_bloom[]", "Taxonomia de Bloom", required=True, max_items=6),
        "dificuldade": difficulties,
        "contextualizacao": _text("av_contextualizacao", "Contextualização"),
        "parametros_adicionais": _text("av_parametros", "Parâmetros adicionais", required=False, max_length=5000),
        "usar_exclusivamente_anexos": request.form.get("av_somente_anexos") == "yes",
    }
    groups = [
        ("Apostilas correspondentes", _files("av_apostilas", "as apostilas", required=True)),
        ("Planos individuais correspondentes", _files("av_planos", "os planos individuais", required=True)),
    ]
    return form, groups


PARSERS = {
    "ementa": _parse_ementa,
    "plano-ensino": _parse_plano_ensino,
    "cronograma": _parse_cronograma,
    "planos-aula": _parse_planos_aula,
    "apostila": _parse_apostila,
    "avaliacao": _parse_avaliacao,
}


def _branding_config() -> dict[str, Any]:
    keys = [
        "LOGO_PATH", "INSTITUTION_NAME", "INSTITUTION_UNIT", "INSTITUTION_WEBSITE",
        "INSTITUTION_ADDRESS", "INSTITUTION_FOOTER",
    ]
    return {key: current_app.config.get(key) for key in keys}


@bp.get("/")
def index():
    return render_template(
        "index.html",
        csrf_token=create_csrf_token(),
        max_request_mb=current_app.config["MAX_REQUEST_MB"],
        max_file_mb=current_app.config["MAX_FILE_MB"],
        data_mode=current_app.config.get("GEMINI_DATA_MODE", "unpaid"),
        institution_name=current_app.config.get("INSTITUTION_NAME"),
        logo_exists=current_app.config["LOGO_PATH"].exists(),
    )


@bp.get("/privacidade")
def privacy():
    return render_template(
        "privacy.html",
        institution_name=current_app.config.get("INSTITUTION_NAME"),
        privacy_email=current_app.config.get("PRIVACY_CONTACT_EMAIL"),
        data_mode=current_app.config.get("GEMINI_DATA_MODE", "unpaid"),
        logo_exists=current_app.config["LOGO_PATH"].exists(),
    )


@bp.get("/health")
def health():
    config = current_app.config
    api_key = config.get("GEMINI_API_KEY", "")
    ai_configured = bool(config.get("USE_FAKE_GEMINI")) or bool(
        api_key and api_key not in {"cole-a-chave-aqui", "sua-chave-aqui"}
    )
    return jsonify(
        {
            "status": "ok",
            "service": "ajuda-professores",
            # Nenhum segredo é exposto: apenas booleanos de configuração
            # (Protocolo RN, seção 16.2 — health check por componente).
            "ai_generation_enabled": bool(config.get("AI_GENERATION_ENABLED", True)),
            "ai_configured": ai_configured,
            "fake_mode": bool(config.get("USE_FAKE_GEMINI")),
        }
    )


@bp.post("/gerar/<document_type>")
def generate_document(document_type: str):
    if document_type not in DOCUMENT_TYPES:
        raise AppError("Tipo de documento inválido.", 404, "not_found")

    request_id = new_request_id()
    started = monotonic()
    phase = "validation"
    metrics: dict[str, Any] = {}
    try:
        if not current_app.config.get("AI_GENERATION_ENABLED", True):
            raise AppError(
                "A geração de documentos está temporariamente desativada pelo administrador. Tente novamente mais tarde.",
                503,
                "generation_disabled",
            )

        _validate_consent_and_csrf()
        rate_limiter.check()
        form_data, upload_groups = PARSERS[document_type]()

        phase = "attachments"
        sources = collect_sources(
            upload_groups,
            max_file_bytes=current_app.config["MAX_FILE_MB"] * 1024 * 1024,
            max_files=(
                min(current_app.config["MAX_FILES_PER_REQUEST"], 12)
                if document_type in {"apostila", "avaliacao"}
                else current_app.config["MAX_FILES_PER_REQUEST"]
            ),
            # PDFs textuais são muito menores e mais rápidos que o envio
            # multimodal do PDF completo. PDFs digitalizados seguem inline.
            prefer_pdf_text=document_type in {"apostila", "avaliacao"},
        )

        phase = "gemini"
        generator = current_app.extensions["document_generator"]
        generated_data = generator.generate(document_type, form_data, sources, metrics=metrics)
        generated_data = validate_generated_output(document_type, generated_data, form_data)

        phase = "docx"
        artifact = build_artifact(document_type, generated_data, form_data, _branding_config())

        response = send_file(
            artifact.content,
            as_attachment=True,
            download_name=artifact.filename,
            mimetype=artifact.mimetype,
            max_age=0,
            conditional=False,
        )
        elapsed = monotonic() - started
        response.headers["X-Document-Review"] = "required"
        response.headers["X-Generation-Seconds"] = f"{elapsed:.1f}"
        response.headers["Cache-Control"] = "no-store, max-age=0"
        log_event(
            current_app.logger,
            event="generation_completed",
            request_id=request_id,
            document_type=document_type,
            prompt_version=PROMPT_VERSIONS.get(document_type),
            duration_ms=round(elapsed * 1000),
            model=metrics.get("model"),
            retry_count=metrics.get("retry_count", 0),
            tokens_input=metrics.get("tokens_input"),
            tokens_output=metrics.get("tokens_output"),
        )
        return response
    except AppError as error:
        log_event(
            current_app.logger,
            event="generation_failed",
            request_id=request_id,
            document_type=document_type,
            phase=phase,
            error_code=error.code,
            error_type=metrics.get("error_type"),
            retry_count=metrics.get("retry_count", 0),
            duration_ms=round((monotonic() - started) * 1000),
            http_status=error.status_code,
        )
        raise
    except Exception as error:
        log_event(
            current_app.logger,
            event="generation_failed",
            request_id=request_id,
            document_type=document_type,
            phase=phase,
            error_type=type(error).__name__,
            retry_count=metrics.get("retry_count", 0),
            duration_ms=round((monotonic() - started) * 1000),
        )
        raise
