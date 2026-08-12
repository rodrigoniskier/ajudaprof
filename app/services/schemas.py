from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)


class EmentaOutput(StrictModel):
    ementa: str
    bibliografia_basica: list[str] = Field(default_factory=list)
    bibliografia_complementar: list[str] = Field(default_factory=list)
    notas_para_revisao: list[str] = Field(default_factory=list)


class Objectives(StrictModel):
    cognitivos: list[str] = Field(default_factory=list)
    habilidades: list[str] = Field(default_factory=list)
    atitudes: list[str] = Field(default_factory=list)


class TeachingUnit(StrictModel):
    unidade: str
    carga_horaria: str
    topicos: list[str] = Field(default_factory=list)


class PlanoEnsinoOutput(StrictModel):
    ementa: str
    objetivos: Objectives
    unidades: list[TeachingUnit] = Field(default_factory=list)
    estrategia_ensino: list[str] = Field(default_factory=list)
    recursos_disponiveis: list[str] = Field(default_factory=list)
    avaliacao: list[str] = Field(default_factory=list)
    bibliografia_basica: list[str] = Field(default_factory=list)
    bibliografia_complementar: list[str] = Field(default_factory=list)
    notas_para_revisao: list[str] = Field(default_factory=list)


class ScheduleEntry(StrictModel):
    numero: int
    data: str
    dia_semana: str
    horario: str
    carga_horaria: str
    natureza: Literal["Teórica", "Prática", "Teórico-prática", "Evento", "Recesso", "Avaliação", "Outra"]
    topico: str
    docente: str
    observacoes: str = ""


class CronogramaOutput(StrictModel):
    aulas: list[ScheduleEntry] = Field(default_factory=list)
    carga_horaria_teorica_planejada: str
    carga_horaria_pratica_planejada: str
    alertas_calendario: list[str] = Field(default_factory=list)
    notas_para_revisao: list[str] = Field(default_factory=list)


class LessonPlan(StrictModel):
    numero: int
    data: str = ""
    tema: str
    atividade: Literal["TEÓRICA", "PRÁTICA", "TEÓRICO-PRÁTICA", "OUTRA"]
    duracao: str
    conhecimentos: list[str] = Field(default_factory=list)
    habilidades: list[str] = Field(default_factory=list)
    atitudes: list[str] = Field(default_factory=list)
    metodologia: list[str] = Field(default_factory=list)
    recursos_didaticos: list[str] = Field(default_factory=list)
    procedimento_avaliativo: list[str] = Field(default_factory=list)
    bibliografia: list[str] = Field(default_factory=list)
    notas_para_revisao: list[str] = Field(default_factory=list)


class PlanosAulaOutput(StrictModel):
    planos: list[LessonPlan] = Field(default_factory=list)
    notas_gerais: list[str] = Field(default_factory=list)


class HandoutSection(StrictModel):
    titulo: str
    paragrafos: list[str] = Field(default_factory=list)
    pontos_chave: list[str] = Field(default_factory=list)
    exemplo_aplicado: str = ""


class ApostilaOutput(StrictModel):
    titulo: str
    apresentacao: str
    objetivos_aprendizagem: list[str] = Field(default_factory=list)
    secoes: list[HandoutSection] = Field(default_factory=list)
    sintese: list[str] = Field(default_factory=list)
    questoes_revisao: list[str] = Field(default_factory=list)
    orientacoes_respostas: list[str] = Field(default_factory=list)
    referencias: list[str] = Field(default_factory=list)
    avisos_validacao: list[str] = Field(default_factory=list)


class Alternative(StrictModel):
    letra: str
    texto: str


class EvaluationQuestion(StrictModel):
    numero: int
    tipo: Literal[
        "Múltipla escolha — resposta única",
        "Múltipla escolha — respostas múltiplas",
        "Asserção–razão",
        "Discursiva",
        "Outra",
    ]
    nivel_bloom: str
    dificuldade: Literal["Fácil", "Média", "Difícil"]
    valor: str
    enunciado: str
    alternativas: list[Alternative] = Field(default_factory=list)
    resposta_correta: str
    justificativa: str
    rubrica: list[str] = Field(default_factory=list)


class AvaliacaoOutput(StrictModel):
    titulo: str
    instrucoes: list[str] = Field(default_factory=list)
    questoes: list[EvaluationQuestion] = Field(default_factory=list)
    observacoes_revisao_docente: list[str] = Field(default_factory=list)


SCHEMAS = {
    "ementa": EmentaOutput,
    "plano-ensino": PlanoEnsinoOutput,
    "cronograma": CronogramaOutput,
    "planos-aula": PlanosAulaOutput,
    "apostila": ApostilaOutput,
    "avaliacao": AvaliacaoOutput,
}

