from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from typing import Any

from ..errors import GenerationError


WEEKDAYS_PT = {
    0: "Segunda-feira",
    1: "Terça-feira",
    2: "Quarta-feira",
    3: "Quinta-feira",
    4: "Sexta-feira",
    5: "Sábado",
    6: "Domingo",
}


def _validate_cronograma(data: dict[str, Any], form: dict[str, Any]) -> None:
    notes = data.setdefault("notas_para_revisao", [])
    allowed_days = {meeting.get("dia") for meeting in form.get("encontros_semanais", [])}
    start = date.fromisoformat(form["data_inicio"])
    end = date.fromisoformat(form["data_fim"])
    seen_dates: Counter[tuple[str, str]] = Counter()

    for index, item in enumerate(data.get("aulas", []), start=1):
        item["numero"] = index
        raw_date = str(item.get("data", "")).strip()
        try:
            parsed = datetime.strptime(raw_date, "%d/%m/%Y").date()
        except ValueError:
            notes.append(f"A aula {index} contém data inválida ou fora do padrão DD/MM/AAAA: {raw_date or 'em branco'}.")
            continue
        computed_weekday = WEEKDAYS_PT[parsed.weekday()]
        if item.get("dia_semana") != computed_weekday:
            item["dia_semana"] = computed_weekday
            notes.append(f"O dia da semana da aula {index} foi corrigido automaticamente para {computed_weekday}.")
        if parsed < start or parsed > end:
            notes.append(f"A data {raw_date}, da aula {index}, está fora do período informado.")
        nature = item.get("natureza", "")
        if nature not in {"Evento", "Recesso"} and allowed_days and computed_weekday not in allowed_days:
            notes.append(f"A aula {index} caiu em {computed_weekday}, dia não previsto nos encontros semanais.")
        key = (raw_date, str(item.get("horario", "")))
        seen_dates[key] += 1

    for (raw_date, schedule), count in seen_dates.items():
        if raw_date and count > 1:
            notes.append(f"Há {count} registros no mesmo dia e horário: {raw_date}, {schedule}. Confira se são turmas ou atividades distintas.")

    # Preserva a ordem e remove avisos idênticos.
    data["notas_para_revisao"] = list(dict.fromkeys(notes))


def _validate_evaluation(data: dict[str, Any], form: dict[str, Any]) -> None:
    questions = data.get("questoes", [])
    requested_total = int(form.get("numero_questoes", 0))
    if len(questions) != requested_total:
        raise GenerationError(
            f"A IA gerou {len(questions)} questões, mas foram solicitadas {requested_total}. Tente novamente."
        )

    requested: Counter[str] = Counter()
    for specification in form.get("especificacoes_questoes", []):
        requested[specification["tipo"]] += int(specification["quantidade"])
    actual = Counter(question.get("tipo") for question in questions)
    for question_type, quantity in requested.items():
        schema_type = "Outra" if question_type == "Outra" else question_type
        if actual.get(schema_type, 0) != quantity:
            raise GenerationError(
                f"A IA não respeitou a quantidade solicitada para “{question_type}”. Tente novamente."
            )

    spec_by_type = {spec["tipo"]: spec for spec in form.get("especificacoes_questoes", [])}
    for index, question in enumerate(questions, start=1):
        question["numero"] = index
        question_type = question.get("tipo")
        if question_type.startswith("Múltipla escolha") or question_type == "Asserção–razão":
            specification = spec_by_type.get(question_type, {})
            expected_alternatives = specification.get("numero_alternativas")
            if expected_alternatives:
                try:
                    expected = int(expected_alternatives)
                except ValueError:
                    expected = 0
                if expected and len(question.get("alternativas", [])) != expected:
                    raise GenerationError(
                        f"A questão {index} não respeitou o número solicitado de alternativas. Tente novamente."
                    )


def validate_generated_output(document_type: str, data: dict[str, Any], form: dict[str, Any]) -> dict[str, Any]:
    if document_type == "cronograma":
        _validate_cronograma(data, form)
    elif document_type == "avaliacao":
        _validate_evaluation(data, form)
    elif document_type == "planos-aula" and len(data.get("planos", [])) > 80:
        raise GenerationError("O cronograma gerou mais de 80 planos em uma única solicitação. Informe um intervalo menor.")
    return data
