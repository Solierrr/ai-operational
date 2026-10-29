from pydantic import BaseModel, Field

from src.actions import base
from src.actions.offer import model_label
from src.agents.specialist.action_proposer.action_proposer_prompt import (
    INVENTORY_EXTRACTION_PROMPT,
)
from src.infra.api_core.client import ApiCoreClient

ACTION = "set_inventory_quantity"


class InventoryDraft(BaseModel):
    modelo: str | None = None
    quantidade: int | None = Field(default=None, ge=0)
    empresa: str | None = None


def inventory_label(item: dict) -> str:
    return model_label(item.get("model") or {})


def inventory_line(item: dict) -> str:
    return f"{base.safe(inventory_label(item))} - {item.get('quantity', 0)} unidades"


async def prepare(
    draft: InventoryDraft, client: ApiCoreClient
) -> base.Ask | base.Ready:
    itens = await client.my_inventories()
    if not itens:
        return base.Ask("Sua empresa ainda não tem estoque cadastrado.")
    itens = base.filter_by_company(itens, draft.empresa)

    if not draft.modelo:
        opcoes = base.options_text([inventory_line(i) for i in itens])
        return base.Ask(f"De qual modelo devo ajustar o estoque?\n{opcoes}")
    if draft.quantidade is None:
        return base.Ask(
            "Qual deve ser a nova quantidade total em estoque? "
            "Diga o total, não a diferença."
        )

    candidatos = [
        i for i in itens if base.label_matches(draft.modelo, inventory_label(i))
    ]
    if not candidatos:
        opcoes = base.options_text([inventory_line(i) for i in itens])
        return base.Ask(
            f'Não encontrei estoque de "{base.safe(draft.modelo)}". Estes são os seus:\n{opcoes}'
        )
    if len(candidatos) > 1:
        opcoes = base.options_text([inventory_line(i) for i in candidatos])
        return base.Ask(f"Encontrei mais de um estoque. Qual deles?\n{opcoes}")

    item = candidatos[0]
    atual = item.get("quantity")
    if atual == draft.quantidade:
        return base.Ask(f"O estoque já é de {atual} unidades.")

    rotulo = base.safe(inventory_label(item))
    resumo = (
        "Posso ajustar este estoque, mas só depois do seu aceite:\n\n"
        f"- Modelo: {rotulo}\n"
        f"- Empresa: {base.safe(item['_empresa'])}\n"
        f"- Quantidade: {atual} -> {draft.quantidade} unidades"
    )
    payload = {
        "inventoryId": item["id"],
        "quantity": draft.quantidade,
        "rotulo": rotulo,
    }
    return base.Ready(payload, resumo)


async def execute(client: ApiCoreClient, payload: dict) -> dict:
    return await client.update_inventory_quantity(
        payload["inventoryId"], payload["quantity"]
    )


def success(resultado: dict, payload: dict) -> str:
    return f'Pronto, o estoque de "{payload["rotulo"]}" agora é de {payload["quantity"]} unidades.'


SPEC = base.ActionSpec(
    name=ACTION,
    descricao="set_inventory_quantity: ajustar a quantidade total em estoque de um modelo da empresa.",
    prompt=INVENTORY_EXTRACTION_PROMPT,
    draft_model=InventoryDraft,
    prepare=prepare,
    execute=execute,
    success=success,
    recusado="Tudo bem, não alterei o estoque.",
)
