from __future__ import annotations
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError


class ModelNotSupportedError(Exception):
    def __init__(self, model_id: str) -> None:
        self.model_id = model_id
        super().__init__(f"Model '{model_id}' is not supported")


class TokenizerNotAvailableError(Exception):
    def __init__(self, tokenizer_name: str) -> None:
        self.tokenizer_name = tokenizer_name
        super().__init__(f"Tokenizer '{tokenizer_name}' is not available")


class InvalidCompareRequestError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def _error_response(code: str, message: str, details=None, status_code: int = 400) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details}},
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ModelNotSupportedError)
    async def model_not_supported_handler(request: Request, exc: ModelNotSupportedError):
        return _error_response(
            "MODEL_NOT_SUPPORTED",
            str(exc),
            status_code=404,
        )

    @app.exception_handler(TokenizerNotAvailableError)
    async def tokenizer_not_available_handler(request: Request, exc: TokenizerNotAvailableError):
        return _error_response(
            "TOKENIZER_NOT_AVAILABLE",
            str(exc),
            status_code=503,
        )

    @app.exception_handler(InvalidCompareRequestError)
    async def invalid_compare_handler(request: Request, exc: InvalidCompareRequestError):
        return _error_response(
            "INVALID_COMPARE_REQUEST",
            exc.message,
            status_code=400,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return _error_response(
            "VALIDATION_ERROR",
            "Request validation failed",
            details=exc.errors(),
            status_code=422,
        )

    @app.exception_handler(Exception)
    async def generic_handler(request: Request, exc: Exception):
        return _error_response(
            "INTERNAL_ERROR",
            "An internal error occurred",
            status_code=500,
        )
