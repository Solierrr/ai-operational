"""Cliente do api-core: lê o contexto do usuário e executa as ações aprovadas por ele.

Todas as chamadas levam o JWT do próprio usuário, então o RBAC do api-core vale
como em qualquer outra tela: o agente nunca tem mais permissão do que quem pediu."""

from dataclasses import dataclass

import httpx

from src.core.config.settings import settings

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
        return f"O sistema recusou o pedido: {detalhe}"
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

    async def my_suppliers(self) -> list[SupplierRef]:
        """Empresas fornecedoras às quais o usuário pertence."""
        perfil = (await self._request("GET", "/users/me")).json()
        refs: list[SupplierRef] = []
        for membership in perfil.get("companyMemberships") or []:
            company_id = membership["companyId"]
            suppliers = (
                await self._request("GET", f"/suppliers/company/{company_id}")
            ).json()
            for supplier in suppliers:
                name = membership.get("companyName") or "Sua empresa"
                refs.append(SupplierRef(supplier["id"], company_id, name))
        return refs

    async def approved_models(self) -> list[dict]:
        return (await self._request("GET", "/models/status/APPROVED")).json()

    async def create_offer(self, payload: dict) -> dict:
        return (await self._request("POST", "/offers", json=payload)).json()
