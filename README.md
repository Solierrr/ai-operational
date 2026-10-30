# ai-operational

Agente que ajuda o usuário a operar o SaaS da Solaria (fornecedores, demandantes e administradores de empresa). Ele explica passo a passo como fazer cada tarefa (Agente Guia), indica a tela certa do web-app (Localizador de Telas), mostra os dados do próprio usuário, só leitura (Agente de Consulta: ofertas, estoque, pedidos, carrinho, vendas e assinatura) e, quando o usuário pede, propõe uma ação (Agente de Ações: cadastrar, pausar, reativar ou encerrar ofertas, ajustar estoque, cancelar pedido e mexer no carrinho) com uma mensagem que explica o que será feito. A ação só é executada no `api-core`, com o JWT do próprio usuário, depois do aceite explícito dele; se ele recusar, nada é gravado. Compras, pagamentos, exclusões e mudanças de senha, cargo ou permissão nunca são feitos pelo assistente. É chamado pelo `ai-assistant` por A2A, onde a proposta pendente vira o estado `input_required`. Detalhes de segurança em [docs/seguranca-das-acoes.md](./docs/seguranca-das-acoes.md) e de rastreamento em [docs/observability-langsmith.md](./docs/observability-langsmith.md).

<p>

[![License](https://img.shields.io/github/license/Solierrr/ai-operational)](https://github.com/Solierrr/ai-operational/blob/main/LICENSE)
[![GitHub Last Commit](https://img.shields.io/github/last-commit/Solierrr/ai-operational)](https://github.com/Solierrr/ai-operational/commits)
[![GitHub Issues](https://img.shields.io/github/issues/Solierrr/ai-operational)](https://github.com/Solierrr/ai-operational/issues)
[![GitHub Pull Requests](https://img.shields.io/github/issues-pr/Solierrr/ai-operational)](https://github.com/Solierrr/ai-operational/pulls)
[![Release](https://img.shields.io/github/v/release/Solierrr/ai-operational)](https://github.com/Solierrr/ai-operational/releases)

</p>

<p>
  <a href="https://github.com/syvixor/skills-icons">
    <img src="https://skills.syvixor.com/api/icons?i=python,fastapi,langchain,mongodb,redis,docker" height="48" alt="Stack">
  </a>
</p>

## API

| O quê | Caminho | Observação |
|---|---|---|
| Swagger UI | `/docs` | desligado com `DOCS_ENABLED=false` (PROD) |
| Contrato OpenAPI | `/openapi.json` | o mesmo contrato fica versionado em `openapi.yaml`, gerado por `make openapi` e conferido no CI |
| Conversa | `POST /chat` | JWT do `api-auth` em `Authorization: Bearer <token>` |
| Vivo | `GET /health` | `{"status":"UP","version":"X.Y.Z"}` |
| Pronto | `GET /ready` | ping no Mongo; 503 com `{"status":"DOWN"}` quando ele não responde |

Todo erro HTTP sai como `application/problem+json`, com `errorCode` do catálogo de erros do `docs-warehouse`. O que acontece dentro da conversa não é erro: a resposta do turno volta 200 com `outcome` (`ANSWERED`, `REFUSED`, `DEGRADED` ou `TOOL_FAILED`) e `reason`, presente quando `outcome` não é `ANSWERED`:

| `reason` | `outcome` | Quando |
|---|---|---|
| `OUT_OF_SCOPE` | `REFUSED` | pedido fora do escopo do agente |
| `MANIPULATION_ATTEMPT` | `REFUSED` | tentativa de manipular as instruções do agente |
| `INTERNAL_DATA_REQUEST` | `REFUSED` | pedido de dados internos da plataforma |
| `FALSE_INFORMATION` | `REFUSED` | mensagem baseada em informação falsa |
| `GUARDRAIL_REFUSED` | `REFUSED` | recusa do guardrail sem categoria conhecida |
| `ANSWER_REJECTED` | `REFUSED` | o juiz reprovou a resposta depois das novas tentativas |
| `GUARDRAIL_UNAVAILABLE` | `DEGRADED` | o guardrail não conseguiu avaliar e a resposta saiu genérica |
| `ACTION_FAILED` | `TOOL_FAILED` | o `api-core` falhou ao montar ou executar a ação proposta |

### Chamadas a outros serviços

- `api-messenger`: rotas `/internal/**` com `X-Service-Key` (`SERVICE_KEY`).
- `mcp-database`: `X-Service-Key` (`SERVICE_KEY`). Enquanto o `mcp-database` ainda aceita a chave antiga, o `MCP_API_KEY`, se definido, segue junto como `x-api-key`.
- `api-core`: ações aprovadas, com o JWT do próprio usuário.

### A2A

O A2A não é OpenAPI e fica fora do contrato. O `ai-assistant` delega a este serviço as ações no SaaS pelo protocolo A2A da `lib-ai`: o Agent Card fica em `/.well-known/agent-card.json` (URL pública em `A2A_PUBLIC_URL`, versão igual à do release) e anuncia a skill `operar-saas`. O JWT do usuário vem na chamada; uma proposta pendente volta no estado `input_required`, à espera do aceite.

## Aprofunde-se no Projeto!

- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [RUNNING.md](./RUNNING.md)

## Contribuindo

- Escreva commits em Conventional Commits, em inglês e minúsculas (`feat:`, `fix:` etc.).
- Todo PR deve usar o `.github/pull_request_template.md` deste repositório.
