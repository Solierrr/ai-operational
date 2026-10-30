import re

from pydantic import BaseModel

from src.actions import base
from src.agents.specialist.action_proposer.action_proposer_prompt import (
    ORDER_EXTRACTION_PROMPT,
)
from src.infra.api_core.client import ApiCoreClient

ACTION = "cancel_order"


class OrderDraft(BaseModel):
    pedido: str | None = None
    referencia: str | None = None


def order_line(order: dict) -> str:
    itens = order.get("items") or []
    nomes = ", ".join(
        f"{base.safe(i.get('modelName'), 40)} x{i.get('quantity')}" for i in itens[:3]
    )
    total = order.get("total")
    total_txt = base.brl(float(total)) if total is not None else "valor indisponível"
    data = str(order.get("createdAt") or "")[:10]
    return f"{base.short_id(order.get('id'))} - {data} - {total_txt} - {nomes}"


def _cancelable(orders: list[dict]) -> list[dict]:
    return [o for o in orders if o.get("status") == "PAID"]


def _by_code(orders: list[dict], code: str) -> list[dict]:
    limpo = re.sub(r"[^0-9a-f]", "", code.lower())
    if len(limpo) < 4:
        return []
    return [
        o for o in orders if str(o.get("id", "")).replace("-", "").startswith(limpo)
    ]


async def prepare(draft: OrderDraft, client: ApiCoreClient) -> base.Ask | base.Ready:
    pedidos = _cancelable(await client.my_orders())
    if not pedidos:
        return base.Ask("Você não tem pedidos que possam ser cancelados.")

    if draft.pedido:
        escolhidos = _by_code(pedidos, draft.pedido)
        if not escolhidos:
            opcoes = base.options_text([order_line(o) for o in pedidos])
            return base.Ask(
                f'Não achei o pedido "{base.safe(draft.pedido, 20)}". '
                f"Pedidos que podem ser cancelados (código - data - total):\n{opcoes}"
            )
    elif draft.referencia == "ultimo":
        escolhidos = sorted(
            pedidos, key=lambda o: str(o.get("createdAt")), reverse=True
        )[:1]
    elif len(pedidos) == 1:
        escolhidos = pedidos
    else:
        opcoes = base.options_text([order_line(o) for o in pedidos])
        return base.Ask(
            "Qual pedido devo cancelar? Me diga o código "
            f"(código - data - total):\n{opcoes}"
        )

    if len(escolhidos) > 1:
        opcoes = base.options_text([order_line(o) for o in escolhidos])
        return base.Ask(
            f"Esse código serve para mais de um pedido. Qual deles?\n{opcoes}"
        )

    pedido = escolhidos[0]
    codigo = base.short_id(pedido["id"])
    resumo = (
        "Posso cancelar este pedido, mas só depois da sua confirmação:\n\n"
        f"- Pedido: {codigo}\n"
        f"- Detalhes: {order_line(pedido)}"
    )
    return base.Ready(
        {"orderId": pedido["id"], "rotulo": codigo}, resumo, irreversible=True
    )


async def execute(client: ApiCoreClient, payload: dict) -> dict:
    return await client.cancel_order(payload["orderId"])


def success(resultado: dict, payload: dict) -> str:
    return f"Pronto, o pedido {payload['rotulo']} foi cancelado."


SPEC = base.ActionSpec(
    name=ACTION,
    descricao="cancel_order: cancelar um pedido de compra que o próprio usuário fez.",
    prompt=ORDER_EXTRACTION_PROMPT,
    draft_model=OrderDraft,
    prepare=prepare,
    execute=execute,
    success=success,
    recusado="Tudo bem, não cancelei nada.",
)
