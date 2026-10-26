from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.api.errors import ApiError
from src.api.schemas.chat import ChatRequest, ChatResponse
from src.workflow.outcome import turn_outcome
from src.workflow.runner import execute_turn

router = APIRouter(tags=["Conversa"])
bearer_scheme = HTTPBearer(
    scheme_name="bearerAuth", bearerFormat="JWT", auto_error=False
)


def chat_response(final_state: dict, **extra) -> dict:
    final_message = final_state["messages"][-1]
    metadata = final_message.additional_kwargs
    outcome, reason = turn_outcome(final_state)
    return {
        "response": final_message.content,
        "outcome": outcome,
        "reason": reason,
        "specialists_used": metadata.get("specialists_used", []),
        "workflow_steps": metadata.get(
            "workflow_steps", final_state.get("turn_agents", [])
        ),
        **extra,
    }


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Envia uma mensagem ao agente operacional",
    description=(
        "Roda um turno da conversa com o JWT do usuário. Recusa do guardrail, "
        "fallback e falha de ferramenta não são erro HTTP: voltam 200 com outcome e "
        "reason. Ações que gravam dados são só propostas e dependem do aceite do "
        "usuário no turno seguinte."
    ),
    operation_id="sendChatMessage",
    responses={
        401: {"description": "Token ausente ou inválido"},
        422: {"description": "Corpo da requisição inválido"},
    },
    openapi_extra={
        "x-error-codes": ["UNAUTHENTICATED", "VALIDATION_FAILED", "INTERNAL_ERROR"]
    },
)
async def conversar(
    requisicao: ChatRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> ChatResponse:
    if credentials is None:
        raise ApiError(401, "UNAUTHENTICATED", "Token ausente ou inválido.")

    from src.workflow.graph.graph import compiled_app

    final_state = await execute_turn(
        requisicao.conversation_id,
        requisicao.message,
        compiled_app,
        user_token=credentials.credentials,
    )
    return ChatResponse(**chat_response(final_state))
