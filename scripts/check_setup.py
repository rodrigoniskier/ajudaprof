#!/usr/bin/env python3
"""Valida a configuração local sem imprimir segredos nem chamar serviços externos."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

errors: list[str] = []
warnings: list[str] = []

if sys.version_info < (3, 11):
    errors.append("Use Python 3.11 ou superior.")

secret = os.getenv("SECRET_KEY", "").strip()
if not secret or secret == "troque-por-uma-chave-aleatoria-longa" or len(secret) < 32:
    errors.append("SECRET_KEY ausente, ainda igual ao exemplo ou curta demais.")

api_key = os.getenv("GEMINI_API_KEY", "").strip()
if not api_key or api_key == "cole-a-chave-aqui":
    errors.append("GEMINI_API_KEY não configurada.")

if os.getenv("USE_FAKE_GEMINI", "false").strip().lower() in {"1", "true", "yes", "sim", "on"}:
    errors.append("USE_FAKE_GEMINI deve ser false em produção.")

data_mode = os.getenv("GEMINI_DATA_MODE", "unpaid").strip().lower()
if data_mode not in {"paid", "unpaid"}:
    errors.append("GEMINI_DATA_MODE deve ser paid ou unpaid.")
elif data_mode == "unpaid":
    warnings.append("Modo não pago declarado: não envie dados pessoais, sensíveis, confidenciais ou sigilosos.")

logo = ROOT / "app" / "static" / "img" / "logo.png"
if not logo.is_file():
    warnings.append("Logo não encontrada em app/static/img/logo.png; será exibida a marca textual na interface.")

privacy_email = os.getenv("PRIVACY_CONTACT_EMAIL", "").strip()
if not privacy_email or privacy_email == "privacidade@exemplo.edu.br":
    warnings.append("Preencha PRIVACY_CONTACT_EMAIL com o canal real da instituição.")

institution = os.getenv("INSTITUTION_NAME", "").strip()
if not institution or institution == "Nome da Instituição de Ensino Superior":
    warnings.append("Preencha INSTITUTION_NAME com o nome real da instituição.")

for warning in warnings:
    print(f"AVISO: {warning}")

if errors:
    for error in errors:
        print(f"ERRO: {error}", file=sys.stderr)
    raise SystemExit(1)

print("Configuração básica válida.")

