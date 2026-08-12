from __future__ import annotations

import logging
import os

from dotenv import load_dotenv

# Precisa rodar antes de "from .config import Config": os valores de Config
# são lidos com os.getenv() no corpo da classe, ou seja, na importação. Um
# load_dotenv() chamado só dentro de create_app() chegaria tarde demais para
# esses atributos (o WSGI do PythonAnywhere contornava isso carregando o
# .env antes de importar o pacote "app"; "python run.py" não fazia isso).
load_dotenv()

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import RequestEntityTooLarge

from .config import Config
from .errors import AppError
from .security import apply_security_headers


def create_app(config_object=None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_object or Config)

    # Não registrar conteúdo de formulários/anexos. Mensagens técnicas mínimas.
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    app.logger.setLevel(logging.INFO)

    from .routes import bp
    from .security import InMemoryRequest
    from .services.gemini_service import FakeGeminiService, GeminiService

    app.request_class = InMemoryRequest
    app.register_blueprint(bp)
    app.after_request(apply_security_headers)

    @app.context_processor
    def inject_branding():
        # Garante que a logo institucional apareça em toda página, incluindo
        # as renderizadas pelos error handlers abaixo (antes, error.html
        # caía no fallback genérico "DI" por não receber esta variável).
        return {"logo_exists": app.config["LOGO_PATH"].exists()}

    if app.config.get("USE_FAKE_GEMINI"):
        app.extensions["document_generator"] = FakeGeminiService()
    else:
        app.extensions["document_generator"] = GeminiService(
            api_key=app.config.get("GEMINI_API_KEY", ""),
            model=app.config.get("GEMINI_MODEL", "gemini-3.5-flash"),
            apostila_model=app.config.get("GEMINI_APOSTILA_MODEL", "gemini-3.5-flash-lite"),
            avaliacao_model=app.config.get("GEMINI_AVALIACAO_MODEL", "gemini-3.5-flash-lite"),
            timeout_seconds=app.config.get("GEMINI_TIMEOUT_SECONDS", 180),
            apostila_max_input_chars=app.config.get("APOSTILA_MAX_INPUT_CHARS", 160_000),
            avaliacao_max_input_chars=app.config.get("AVALIACAO_MAX_INPUT_CHARS", 240_000),
        )

    @app.errorhandler(AppError)
    def handle_app_error(error: AppError):
        if request.path.startswith("/gerar/") or request.accept_mimetypes.best == "application/json":
            return jsonify({"ok": False, "error": error.code, "message": error.message}), error.status_code
        return render_template("error.html", message=error.message), error.status_code

    @app.errorhandler(RequestEntityTooLarge)
    def handle_large_request(_error):
        message = f"O envio ultrapassou {app.config['MAX_REQUEST_MB']} MB. Reduza ou divida os anexos."
        if request.path.startswith("/gerar/"):
            return jsonify({"ok": False, "error": "request_too_large", "message": message}), 413
        return render_template("error.html", message=message), 413

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", message="Página não encontrada."), 404

    @app.errorhandler(500)
    def internal_error(error):
        # Não serializar a requisição nem o conteúdo do erro da API em produção.
        app.logger.error("Erro interno não tratado: %s", type(error).__name__)
        message = "Ocorreu um erro interno. Nenhum anexo foi mantido. Tente novamente."
        if request.path.startswith("/gerar/"):
            return jsonify({"ok": False, "error": "internal_error", "message": message}), 500
        return render_template("error.html", message=message), 500

    return app
