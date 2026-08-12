import json

from app.services.file_processor import SourceDocument
from app.services.gemini_service import GeminiService
from app.services.prompts import build_prompt


def test_apostila_output_budget_depends_on_requested_length():
    assert GeminiService.output_token_limit("apostila", {"extensao_desejada": "Breve — 4 a 6 páginas"}) == 4_500
    assert GeminiService.output_token_limit("apostila", {"extensao_desejada": "Regular — 7 a 12 páginas"}) == 8_000
    assert GeminiService.output_token_limit("apostila", {"extensao_desejada": "Ampliada — 13 a 20 páginas"}) == 12_000


def test_evaluation_output_budget_depends_on_question_count():
    assert GeminiService.output_token_limit("avaliacao", {"numero_questoes": 2}) == 4_000
    assert GeminiService.output_token_limit("avaliacao", {"numero_questoes": 10}) == 7_000
    assert GeminiService.output_token_limit("avaliacao", {"numero_questoes": 30}) == 18_000


def test_apostila_input_is_capped_without_persistence():
    service = GeminiService("test-key", "model", apostila_max_input_chars=20_000)
    source = SourceDocument(label="Referência", filename="grande.txt", mime_type="text/plain", text="a" * 30_000)
    text, consumed = service._source_text("apostila", source, 0)
    assert consumed == 20_000
    assert text.startswith("a" * 100)
    assert "TRUNCADO" in text


def test_evaluation_input_budget_can_be_balanced_between_sources():
    service = GeminiService("test-key", "model", avaliacao_max_input_chars=40_000)
    source = SourceDocument(label="Apostila", filename="grande.txt", mime_type="text/plain", text="a" * 30_000)
    first, consumed = service._source_text("avaliacao", source, 0, per_source_limit=20_000)
    second, consumed = service._source_text("avaliacao", source, consumed, per_source_limit=20_000)
    assert consumed == 40_000
    assert "TRUNCADO" in first
    assert "TRUNCADO" in second


def test_timeout_messages_are_specific_to_each_generator():
    assert "extensão Breve" in GeminiService._timeout_message("apostila")
    assert "quantidade de questões" in GeminiService._timeout_message("avaliacao")
    assert "extensão Breve" not in GeminiService._timeout_message("avaliacao")


def test_apostila_prompt_contains_explicit_word_budget():
    prompt = build_prompt(
        "apostila",
        {"extensao_desejada": "Breve — 4 a 6 páginas"},
        [],
    )
    assert "1.600 a 2.400 palavras" in prompt
    assert "no máximo 4 questões" in prompt


def test_evaluation_prompt_requests_concise_exact_output():
    prompt = build_prompt("avaliacao", {"numero_questoes": 10}, [])
    assert "exatamente 10 questões" in prompt
    assert "justificativas de gabarito concisas" in prompt


class _FakeUsage:
    def __init__(self, prompt_tokens, output_tokens):
        self.prompt_token_count = prompt_tokens
        self.candidates_token_count = output_tokens


class _FakeResponse:
    def __init__(self, payload, usage=None):
        self.text = json.dumps(payload)
        self.usage_metadata = usage


_VALID_EMENTA = {
    "ementa": "Texto.",
    "bibliografia_basica": [],
    "bibliografia_complementar": [],
    "notas_para_revisao": [],
}


def test_generate_retries_once_on_transient_error(monkeypatch):
    calls = {"n": 0}

    class FakeModels:
        def generate_content(self, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                error = Exception("temporary upstream failure")
                error.code = 503
                raise error
            return _FakeResponse(_VALID_EMENTA, usage=_FakeUsage(120, 340))

    class FakeClient:
        models = FakeModels()

    service = GeminiService("test-key", "model")
    monkeypatch.setattr(service, "_get_client", lambda: FakeClient())
    monkeypatch.setattr("app.services.gemini_service.time.sleep", lambda _seconds: None)

    metrics = {}
    result = service.generate("ementa", {}, [], metrics=metrics)

    assert calls["n"] == 2
    assert result["ementa"] == "Texto."
    assert metrics["retry_count"] == 1
    assert metrics["tokens_input"] == 120
    assert metrics["tokens_output"] == 340


def test_generate_does_not_retry_non_transient_error(monkeypatch):
    from app.errors import GenerationError

    calls = {"n": 0}

    class FakeModels:
        def generate_content(self, **kwargs):
            calls["n"] += 1
            error = Exception("invalid credentials")
            error.code = 403
            raise error

    class FakeClient:
        models = FakeModels()

    service = GeminiService("test-key", "model")
    monkeypatch.setattr(service, "_get_client", lambda: FakeClient())

    metrics = {}
    try:
        service.generate("ementa", {}, [], metrics=metrics)
        raise AssertionError("deveria ter levantado GenerationError")
    except GenerationError as exc:
        assert "recusou a solicitação" in str(exc)
    assert calls["n"] == 1
    assert metrics["retry_count"] == 0
