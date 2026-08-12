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
