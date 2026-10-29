from src.actions import cart, inventory, offer, offer_status, order
from src.actions.base import ActionSpec

ACTIONS: dict[str, ActionSpec] = {
    spec.name: spec
    for spec in (
        offer.SPEC,
        offer_status.SPEC,
        inventory.SPEC,
        order.SPEC,
        cart.SPEC,
    )
}

ACAO_PROIBIDA = "proibida"
NENHUMA_ACAO = "nenhuma"


def describe_actions() -> str:
    return "\n".join(f"- {spec.descricao}" for spec in ACTIONS.values())


def get_action(name: object) -> ActionSpec | None:
    return ACTIONS.get(name) if isinstance(name, str) else None
