import json
from collections.abc import Awaitable, Callable

from langchain_core.tools import tool

from src.actions.base import short_id
from src.actions.offer import model_label
from src.core.security.request_context import current_user_token
from src.core.security.untrusted import sanitize_field, sanitize_record, wrap_untrusted
from src.infra.api_core.client import ApiCoreClient, ApiCoreError

MAX_ITENS = 15
SEM_LOGIN = "Não foi possível consultar: o usuário não está autenticado."


def _data(valor: object) -> str | None:
    return str(valor)[:10] if valor else None


def _empresa(item: dict) -> dict:
    return sanitize_record(
        {"empresa": item.get("companyName"), "cargo": item.get("position")}
    )


def _oferta(item: dict) -> dict:
    return sanitize_record(
        {
            "empresa": item.get("_empresa"),
            "placa": model_label(item.get("model") or {}),
            "preco_unitario": item.get("unitPrice"),
            "disponibilidade": item.get("availability"),
            "situacao": item.get("commercialStatus"),
            "validade": _data(item.get("expirationDate")),
            "desconto_percentual": item.get("discountPercentage"),
        }
    )


def _estoque(item: dict) -> dict:
    return sanitize_record(
        {
            "empresa": item.get("_empresa"),
            "placa": model_label(item.get("model") or {}),
            "quantidade": item.get("quantity"),
        }
    )


def _pedido(item: dict) -> dict:
    itens = [
        sanitize_record({"placa": i.get("modelName"), "quantidade": i.get("quantity")})
        for i in (item.get("items") or [])[:5]
    ]
    return {
        **sanitize_record(
            {
                "codigo": short_id(item.get("id")),
                "situacao": item.get("status"),
                "data": _data(item.get("createdAt")),
                "total": item.get("total"),
            }
        ),
        "itens": itens,
    }


def _venda(item: dict) -> dict:
    return sanitize_record(
        {
            "pedido": short_id(item.get("orderId")),
            "situacao": item.get("status"),
            "data": _data(item.get("createdAt")),
            "comprador": item.get("buyerUsername"),
            "placa": item.get("modelName"),
            "quantidade": item.get("quantity"),
            "valor": item.get("lineTotal"),
        }
    )


def _linha_carrinho(item: dict) -> dict:
    return sanitize_record(
        {
            "placa": item.get("modelName"),
            "empresa": item.get("companyName"),
            "quantidade": item.get("quantity"),
            "preco_liquido": item.get("netUnitPrice"),
            "valor": item.get("lineTotal"),
            "disponivel": item.get("availability"),
            "pode_comprar": item.get("purchasable"),
        }
    )


def _cobranca(item: dict) -> dict:
    return sanitize_record(
        {
            "valor": item.get("amount"),
            "situacao": item.get("status"),
            "vencimento": _data(item.get("dueDate")),
            "pago_em": _data(item.get("paymentDate")),
        }
    )


def _filtrar_empresa(itens: list[dict], empresa: str) -> list[dict]:
    if not empresa.strip():
        return itens
    alvo = sanitize_field(empresa, 60).lower()
    return [i for i in itens if alvo in str(i.get("_empresa", "")).lower()]


async def _consultar(
    origem: str,
    buscar: Callable[[ApiCoreClient], Awaitable[list[dict] | dict]],
    formatar: Callable[[dict], dict],
) -> str:
    token = current_user_token.get()
    if not token:
        return SEM_LOGIN
    try:
        dados = await buscar(ApiCoreClient(token))
    except ApiCoreError as erro:
        return erro.message
    registros = [formatar(item) for item in dados[:MAX_ITENS]]
    corpo = json.dumps(
        {"total": len(dados), "mostrando": len(registros), "registros": registros},
        ensure_ascii=False,
        default=str,
    )
    return wrap_untrusted(origem, corpo)


@tool
async def minhas_empresas() -> str:
    """Lista as empresas das quais o usuário faz parte, com o cargo dele em cada uma."""
    return await _consultar("minhas_empresas", lambda c: c.memberships(), _empresa)


@tool
async def minhas_ofertas(empresa: str = "") -> str:
    """Lista as ofertas de placas das empresas do usuário (preço, quantidade e
    situação: ACTIVE, PAUSED ou CLOSED). Filtra por nome de empresa se informado."""

    async def buscar(client: ApiCoreClient) -> list[dict]:
        return _filtrar_empresa(await client.my_offers(), empresa)

    return await _consultar("minhas_ofertas", buscar, _oferta)


@tool
async def meu_estoque(empresa: str = "") -> str:
    """Lista a quantidade em estoque de cada modelo das empresas do usuário."""

    async def buscar(client: ApiCoreClient) -> list[dict]:
        return _filtrar_empresa(await client.my_inventories(), empresa)

    return await _consultar("meu_estoque", buscar, _estoque)


@tool
async def meus_pedidos() -> str:
    """Lista os pedidos de compra feitos pelo usuário, com código curto, situação
    (PAID ou CANCELED), data, total e itens."""
    return await _consultar("meus_pedidos", lambda c: c.my_orders(), _pedido)


@tool
async def minhas_vendas() -> str:
    """Lista as vendas recebidas pelas empresas do usuário."""
    return await _consultar("minhas_vendas", lambda c: c.my_sales(), _venda)


@tool
async def meu_carrinho() -> str:
    """Mostra os itens do carrinho do usuário e o total."""
    token = current_user_token.get()
    if not token:
        return SEM_LOGIN
    try:
        carrinho = await ApiCoreClient(token).cart()
    except ApiCoreError as erro:
        return erro.message
    itens = carrinho.get("items") or []
    corpo = json.dumps(
        {
            "total_de_itens": len(itens),
            "mostrando": min(len(itens), MAX_ITENS),
            "resumo": sanitize_record(
                {
                    "subtotal": carrinho.get("subtotal"),
                    "taxa": carrinho.get("feeAmount"),
                    "total": carrinho.get("total"),
                }
            ),
            "itens": [_linha_carrinho(item) for item in itens[:MAX_ITENS]],
        },
        ensure_ascii=False,
        default=str,
    )
    return wrap_untrusted("meu_carrinho", corpo)


@tool
async def minha_assinatura() -> str:
    """Mostra o plano, a situação da assinatura e as cobranças da empresa do usuário."""

    async def buscar(client: ApiCoreClient) -> list[dict]:
        assinatura = await client.subscription()
        base = sanitize_record(
            {
                "plano": assinatura.get("planName"),
                "valor": assinatura.get("planValue"),
                "ciclo": assinatura.get("planCycle"),
                "situacao": assinatura.get("status"),
                "renovacao_automatica": assinatura.get("autoRenewal"),
                "inicio": _data(assinatura.get("startDate")),
                "fim": _data(assinatura.get("endDate")),
            }
        )
        cobrancas = [_cobranca(c) for c in (assinatura.get("charges") or [])[:10]]
        return [{**base, "cobrancas": cobrancas}]

    return await _consultar("minha_assinatura", buscar, lambda item: item)


READER_TOOLS = [
    minhas_empresas,
    minhas_ofertas,
    meu_estoque,
    meus_pedidos,
    minhas_vendas,
    meu_carrinho,
    minha_assinatura,
]
