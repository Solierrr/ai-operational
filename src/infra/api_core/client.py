"""Cliente do api-core: lê o contexto do usuário e executa as ações aprovadas por ele.

Todas as chamadas levam o JWT do próprio usuário, então o RBAC do api-core vale
como em qualquer outra tela: o agente nunca tem mais permissão do que quem pediu."""

from dataclasses import dataclass

import httpx

from src.core.config.settings import settings
from src.core.security.untrusted import sanitize_field

_TIMEOUT_SEGUNDOS = 20.0


class ApiCoreError(Exception):
    """Falha ao falar com o api-core. `message` já vem em português, para o usuário."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


@dataclass(frozen=True)
class SupplierRef:
    supplier_id: str
    company_id: str
    company_name: str


def _mensagem_http(resposta: httpx.Response) -> str:
    if resposta.status_code in (401, 403):
        return "Você não tem permissão para fazer isso nesta empresa."
    if resposta.status_code == 404:
        return "Não encontrei o que era necessário no sistema."
    try:
        corpo = resposta.json()
    except ValueError:
        corpo = {}
    detalhe = corpo.get("detail") or corpo.get("message") or corpo.get("title")
    if resposta.status_code in (400, 409, 422) and isinstance(detalhe, str) and detalhe:
        return f"O sistema recusou o pedido: {sanitize_field(detalhe, 200)}"
    return "O sistema não conseguiu concluir o pedido agora."


class ApiCoreClient:
    def __init__(
        self,
        token: str,
        base_url: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._token = token
        self._base_url = (base_url or settings.API_CORE_URL).rstrip("/")
        self._transport = transport

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=_TIMEOUT_SEGUNDOS,
                headers={"Authorization": f"Bearer {self._token}"},
                transport=self._transport,
            ) as client:
                resposta = await client.request(method, path, **kwargs)
        except httpx.HTTPError as erro:
            raise ApiCoreError("O sistema está indisponível no momento.") from erro
        if resposta.status_code >= 400:
            raise ApiCoreError(_mensagem_http(resposta), resposta.status_code)
        return resposta

    async def profile(self) -> dict:
        return (await self._request("GET", "/users/me")).json()

    async def memberships(self) -> list[dict]:
        perfil = await self.profile()
        return [m for m in perfil.get("companyMemberships") or [] if m.get("companyId")]

    async def my_suppliers(self) -> list[SupplierRef]:
        refs: list[SupplierRef] = []
        for membership in await self.memberships():
            company_id = membership["companyId"]
            suppliers = (
                await self._request("GET", f"/suppliers/company/{company_id}")
            ).json()
            for supplier in suppliers:
                name = membership.get("companyName") or "Sua empresa"
                refs.append(SupplierRef(supplier["id"], company_id, name))
        return refs

    async def _per_company(self, path: str) -> list[dict]:
        itens: list[dict] = []
        consultadas = 0
        primeiro_erro: ApiCoreError | None = None
        for membership in await self.memberships():
            company_id = membership["companyId"]
            name = membership.get("companyName") or "Sua empresa"
            try:
                resposta = (
                    await self._request("GET", path.format(company_id=company_id))
                ).json()
            except ApiCoreError as erro:
                if erro.status not in (403, 404):
                    raise
                primeiro_erro = primeiro_erro or erro
                continue
            consultadas += 1
            itens.extend({**item, "_empresa": name} for item in resposta)
        if primeiro_erro and not consultadas:
            raise primeiro_erro
        return itens

    async def approved_models(self) -> list[dict]:
        return (await self._request("GET", "/models/status/APPROVED")).json()

    async def my_offers(self) -> list[dict]:
        return await self._per_company("/offers/company/{company_id}")

    async def my_inventories(self) -> list[dict]:
        return await self._per_company("/inventories/company/{company_id}")

    async def catalog_offers(self) -> list[dict]:
        return (await self._request("GET", "/offers/catalog")).json()

    async def my_orders(self) -> list[dict]:
        return (await self._request("GET", "/orders")).json()

    async def my_sales(self) -> list[dict]:
        return (await self._request("GET", "/sales")).json()

    async def cart(self) -> dict:
        return (await self._request("GET", "/cart")).json()

    async def subscription(self) -> dict:
        return (await self._request("GET", "/subscription")).json()

    async def create_offer(self, payload: dict) -> dict:
        return (await self._request("POST", "/offers", json=payload)).json()

    async def change_offer_status(self, offer_id: str, status: str) -> dict:
        return (
            await self._request(
                "PATCH", f"/offers/{offer_id}/status", json={"status": status}
            )
        ).json()

    async def update_inventory_quantity(self, inventory_id: str, quantity: int) -> dict:
        return (
            await self._request(
                "PATCH",
                f"/inventories/{inventory_id}/quantity",
                json={"quantity": quantity},
            )
        ).json()

    async def cancel_order(self, order_id: str) -> dict:
        return (await self._request("PATCH", f"/orders/{order_id}/cancel")).json()

    async def put_cart_item(self, offer_id: str, quantity: int) -> dict:
        return (
            await self._request(
                "PUT", f"/cart/items/{offer_id}", json={"quantity": quantity}
            )
        ).json()

    async def remove_cart_item(self, offer_id: str) -> dict:
        return (await self._request("DELETE", f"/cart/items/{offer_id}")).json()
