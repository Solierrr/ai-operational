"""Contrato de erro HTTP (ProblemDetail): todo 4xx e 5xx sai em
application/problem+json com errorCode estável."""

import logging
from datetime import UTC, datetime, timezone

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException

logger = logging.getLogger(__name__)

PROBLEM_JSON = "application/problem+json"

GENERIC_BY_STATUS = {
    401: "UNAUTHENTICATED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "VALIDATION_FAILED",
    429: "RATE_LIMITED",
    502: "DEPENDENCY_UNAVAILABLE",
    503: "DEPENDENCY_UNAVAILABLE",
}


class ProblemFieldError(BaseModel):
    field: str = Field(..., examples=["message"])
    errorCode: str = Field(..., examples=["VALIDATION_FAILED"])
    detail: str = Field(..., examples=["String should have at least 1 character"])


class ProblemDetail(BaseModel):
    """Corpo de todo erro HTTP do serviço."""

    type: str = Field(..., examples=["about:blank"])
    title: str = Field(..., examples=["UNAUTHENTICATED"])
    status: int = Field(..., examples=[401])
    errorCode: str = Field(..., examples=["UNAUTHENTICATED"])
    detail: str = Field(..., examples=["Token ausente ou inválido."])
    instance: str = Field(..., examples=["/chat"])
    timestamp: datetime
    traceId: str | None = None
    errors: list[ProblemFieldError] | None = None


class ApiError(Exception):
    def __init__(self, status: int, error_code: str, detail: str, **extra):
        self.status = status
        self.error_code = error_code
        self.detail = detail
        self.extra = extra


def problem(
    request: Request, status: int, error_code: str, detail: str, **extra
) -> JSONResponse:
    body = {
        "type": "about:blank",
        "title": error_code,
        "status": status,
        "errorCode": error_code,
        "detail": detail,
        "instance": request.url.path,
        "timestamp": datetime.now(UTC).isoformat(),
        **extra,
    }
    return JSONResponse(body, status_code=status, media_type=PROBLEM_JSON)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error(request: Request, exc: ApiError):
        return problem(request, exc.status, exc.error_code, exc.detail, **exc.extra)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        code = GENERIC_BY_STATUS.get(exc.status_code, "INTERNAL_ERROR")
        response = problem(request, exc.status_code, code, str(exc.detail))
        if exc.headers:
            response.headers.update(exc.headers)
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        errors = [
            {
                "field": ".".join(str(part) for part in error["loc"][1:]),
                "errorCode": "VALIDATION_FAILED",
                "detail": error["msg"],
            }
            for error in exc.errors()
        ]
        return problem(
            request,
            422,
            "VALIDATION_FAILED",
            "Erro de validação nos campos da requisição.",
            errors=errors,
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        logger.exception("Erro inesperado em %s", request.url.path)
        return problem(
            request, 500, "INTERNAL_ERROR", "Ocorreu um erro interno inesperado."
        )


def _is_problem(response: dict) -> bool:
    """Respostas sem corpo próprio, ou com o erro de validação padrão do FastAPI,
    passam a ser ProblemDetail; o 503 do /ready mantém o {"status"} do health."""
    schemas = [
        media.get("schema", {}).get("$ref", "")
        for media in response.get("content", {}).values()
    ]
    return not schemas or all(ref.endswith("/HTTPValidationError") for ref in schemas)


def apply_problem_details(schema: dict) -> dict:
    """Toda resposta 4xx/5xx do contrato aponta para o ProblemDetail e toda
    operação documenta o 500, como o customizer dos serviços Spring."""
    schemas = schema.setdefault("components", {}).setdefault("schemas", {})
    problem_schema = ProblemDetail.model_json_schema(
        ref_template="#/components/schemas/{model}"
    )
    schemas.update(problem_schema.pop("$defs", {}))
    schemas["ProblemDetail"] = problem_schema
    content = {PROBLEM_JSON: {"schema": {"$ref": "#/components/schemas/ProblemDetail"}}}
    for path in schema.get("paths", {}).values():
        for operation in path.values():
            responses = operation.setdefault("responses", {})
            responses.setdefault("500", {"description": "Erro interno inesperado"})
            for code, response in responses.items():
                if code.startswith(("4", "5")) and _is_problem(response):
                    response["content"] = content
    for unused in ("HTTPValidationError", "ValidationError"):
        schemas.pop(unused, None)
    return schema
