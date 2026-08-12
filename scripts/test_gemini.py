#!/usr/bin/env python3
"""Confere chave, modelo e conectividade sem enviar documentos reais."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai


ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

api_key = os.getenv("GEMINI_API_KEY", "").strip()
model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash").strip()

if not api_key or api_key == "cole-a-chave-aqui":
    raise SystemExit("GEMINI_API_KEY não configurada no arquivo .env.")

client = genai.Client(api_key=api_key)
response = client.models.generate_content(
    model=model,
    contents="Responda apenas com a palavra OK.",
)

if "OK" not in (response.text or "").upper():
    raise SystemExit("A API respondeu, mas o teste não retornou o conteúdo esperado.")

print(f"Conexão com a API Gemini confirmada. Modelo: {model}")

