<p align="center">
  <img src="../assets/readme/banners/fastapi.png" alt="FastAPI" width="100%">
</p>

# Execução local

O preparo comum de Python está em [PYTHON.md](https://github.com/Solierrr/docs-warehouse/blob/main/readme/running/PYTHON.md). O entrypoint deste serviço é `src.api.app:app`.

## Pré-requisitos

O CI usa Python 3.14, mas o Dockerfile usa `python:latest` e não fixa a mesma versão, por isso o ambiente local deve seguir a versão do CI.

- Git, Python 3.14, `make` e shell compatível com `sh`, como Git Bash no Windows.
- Infisical CLI autenticado para obter a configuração local.
- MongoDB acessível, com permissão para criar índices e checkpoints.
- `api-auth` para emitir e validar o JWT, `api-core` para consultas e ações e `api-messenger` para o histórico.
- Credenciais dos provedores usados pelos nós. O roteador e o resumo usam Groq diretamente, além da cadeia com fallback usada em outros pontos.

## Configuração

Execute os comandos na raiz do repositório de origem, em um checkout destinado ao desenvolvimento.

```bash
make doctor
make vault
make install
make dev
```

O `make vault` obtém as pastas `/database`, `/redis`, `/llm`, `/service-urls`, `/mcp` e `/service-keys`, e em QA inclui também `/observability`, sem que nenhum valor de segredo seja versionado. O processo de obtenção está no [guia de segredos](https://github.com/Solierrr/docs-warehouse/blob/main/readme/infisical/README.md).

As variáveis são carregadas de `.env`, com as chaves dos provedores expostas ao ambiente pelo carregador de LLM.

| Nomes | Uso |
|---|---|
| `MONGO_URI`, alternativa `MONGODB_URI` | conexão dos checkpoints, memória e readiness |
| `JWT_JWKS_URL`, `JWT_ISSUER` | validação do token RS256 |
| `API_CORE_URL`, `API_MESSENGER_URL` | destinos do cadastro central e do histórico |
| `SERVICE_KEY`, alternativa `SERVICE_KEY_AI_OPERATIONAL` | chamadas internas e alternativa de assinatura de propostas |
| `PROPOSAL_SIGNING_KEY` | assinatura estável das propostas entre reinícios |
| `GEMINI_API_KEY`, `GROQ_API_KEY`, `LLM_PROVIDER_ORDER` | provedores de geração e ordem de fallback |
| `LLM_MODEL_GEMINI`, `LLM_MODEL_GROQ` | seleção de modelo |
| `ENVIRONMENT`, `CORS_ALLOWED_ORIGINS`, `A2A_PUBLIC_URL` | ambiente, acesso pelo navegador e endereço do Agent Card |
| `DEBUG_ADMIN_SUBS`, `DOCS_ENABLED` | acesso ao debug e exposição do Swagger |
| `CHECKPOINT_TTL_DIAS`, `PROPOSAL_TTL_SECONDS`, `MAX_WRITES_PER_CONVERSATION`, `MAX_MESSAGE_CHARS` | retenção e limites |
| `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_SDK_DISABLED` | destino ou desativação da telemetria |

Os clientes MCP e Redis não são requisitos do grafo atual. A configuração deles permanece em `settings.py`.

## Comandos disponíveis

O Makefile usa o Python do ambiente virtual e escolhe o caminho correto para Windows ou Unix.

| Comando | Resultado |
|---|---|
| `make dev` | Uvicorn com reload na porta local 8000 |
| `make test` | pytest com cobertura de `src` |
| `make lint` | Ruff em `main.py`, `src/workflow` e `src/core/llm` |
| `make format` | formata os mesmos caminhos do lint |
| `make build` | compila os módulos Python com `compileall` |
| `make openapi` | exporta o contrato da camada web, sem executar o lifespan |
| `make ci` | lint, testes e build |

Para conversar no terminal, execute `python main.py` com o ambiente virtual ativo. O token obtido no login local é solicitado em entrada oculta. Esse caminho executa operações reais e não passa pelo lifespan que cria o índice da memória. Suba a API ao menos uma vez antes de usar a CLI.

## Verificação local

Abra o [Swagger local](http://localhost:8000/docs), use Authorize com o access token e envie "Onde cadastro uma oferta de placa?". Os exemplos estão em [API.md](./API.md). `/health` deve responder com processo e versão, enquanto `/ready` depende somente do MongoDB.

O banco pode impedir a partida durante a criação do índice. A compilação do grafo também abre o checkpointer na primeira conversa. Sem `JWT_JWKS_URL`, somente `LOCAL` permite seguir sem validar o token. Use o emissor real para testar identidade e permissões.

Sem URL ou credencial válida do `api-messenger`, o turno normal pode falhar antes de gerar uma resposta, pois grava o histórico primeiro. Sem coletor configurado, a instrumentação pode tentar exportar para o destino local padrão. Os testes usam mocks em vários pontos e não substituem uma chamada integrada com essas dependências.
