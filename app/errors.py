from __future__ import annotations


class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400, code: str = "validation_error"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


class ConfigurationError(AppError):
    def __init__(self, message: str):
        super().__init__(message, status_code=503, code="configuration_error")


class GenerationError(AppError):
    def __init__(self, message: str):
        super().__init__(message, status_code=502, code="generation_error")

