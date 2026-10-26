from pydantic import BaseModel, Field

from src.workflow.outcome import Outcome, Reason


class ChatRequest(BaseModel):
    """O que o cliente envia no POST /chat."""

    conversation_id: str = Field(
        ...,
        description="Identificador da conversa, escolhido pelo cliente e reaproveitado a cada turno.",
        examples=["b2b-empresa-42"],
    )
    message: str = Field(
        ...,
        min_length=1,
        description="Mensagem do usuário.",
        examples=["Onde cadastro uma oferta de placa?"],
    )


class ChatResponse(BaseModel):
    """O que a API devolve no POST /chat."""

    response: str = Field(
        ...,
        description="Resposta do assistente para mostrar ao usuário.",
        examples=["A tela de ofertas fica em Fornecedor > Ofertas."],
    )
    outcome: Outcome = Field(
        Outcome.ANSWERED,
        description=(
            "Resultado do turno: ANSWERED (respondido), REFUSED (o guardrail recusou), "
            "DEGRADED (houve fallback e a resposta é genérica) ou TOOL_FAILED (uma "
            "ferramenta falhou e a resposta saiu sem ela)."
        ),
    )
    reason: Reason | None = Field(
        None,
        description="Código do motivo, no catálogo de erros, quando outcome não é ANSWERED.",
        examples=["OUT_OF_SCOPE"],
    )
    specialists_used: list[str] = Field(
        default_factory=list,
        description="Especialistas consultados no turno.",
        examples=[["screen_finder"]],
    )
    workflow_steps: list[str] = Field(
        default_factory=list,
        description="Etapas do grafo percorridas no turno.",
        examples=[["input_guardrail_approved", "router", "screen_finder"]],
    )
