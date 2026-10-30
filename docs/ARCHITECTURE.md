# Arquitetura do Repositório

Este serviço segue o mesmo padrão do `ai-assistant`: uma API FastAPI que
expõe um chatbot orquestrado via LangGraph, com guardrails de entrada/saída,
memória de curto prazo (checkpointer Mongo) e memória de longo prazo (perfil
de fatos do usuário), delegando a especialistas de domínio por meio de um
Agente Roteador. Os especialistas são:

- Localizador de Telas (`screen_finder`, ferramenta `buscar_tela` sobre o registro de telas em `src/domain/screens.py`);
- Guia (`how_to_guide`, ferramentas `buscar_guia` e `buscar_tela`): passo a passo das tarefas, a partir do registro `src/domain/guides.py`;
- Consulta (`data_reader`, ferramentas de leitura em `src/tools/account.py`): dados do próprio usuário no `api-core`, sempre com o JWT dele;
- Agente de Ações (`action_proposer`): escolhe a ação numa lista fixa (`src/actions/registry.py`), extrai os dados, resolve os ids nos dados do próprio usuário e monta a proposta, sem gravar.

O nó de decisão (`proposal_decision`) executa no `api-core` depois do aceite. A proposta pendente fica em `pending_proposal` no estado (assinada, com validade e presa ao usuário) e as respostas dos nós de ação seguem direto ao usuário, sem passar pelo orquestrador, pelo juiz e pelo guardrail de saída. As respostas do Guia e da Consulta passam pelo orquestrador, pelo juiz e pelo guardrail de saída. Quando o usuário ajusta a proposta ou muda de assunto, ela é descartada e o turno volta ao roteador.

Para acrescentar uma ação nova: crie um módulo em `src/actions/` com `prepare`, `execute` e um `ActionSpec`, e registre-o em `src/actions/registry.py`. Para acrescentar um guia ou uma tela: `src/domain/guides.py` e `src/domain/screens.py`.

<p>
  <a href="https://github.com/syvixor/skills-icons">
    <img src="https://skills.syvixor.com/api/icons?i=python,fastapi,langchain,mongodb,redis" height="48" alt="Arquitetura">
  </a>
</p>

- Orquestração multiagente via LangGraph (`src/workflow/graph/graph.py`):
  `input_guardrail` → `condense_memory` → `router` → especialista(s) →
  `orchestrator` → `judge` → `output_guardrail`.
- Cada especialista de domínio vive em `src/agents/specialist/<nome>/` (prompt)
  e `src/workflow/nodes/<nome>_node.py` (node).
- Integrações de infraestrutura ficam em `src/infra/` (Mongo, Redis, MCP,
  api-messenger); nenhuma delas depende do domínio específico do assistente.
- Autenticação via JWT emitido pelo `api-auth` (`src/core/security/jwt.py`).

```Tree do Repositório (resumo)
├── .github/
│   └── pull_request_template.md
├── src/
│   ├── agents/       # framework base + especialistas
│   ├── api/          # FastAPI (rotas, schemas)
│   ├── core/         # config, llm, guardrails, logging, security
│   ├── infra/        # clientes de infraestrutura (mongo, redis, mcp, api-messenger)
│   ├── memory/        # checkpointer de sessão
│   └── workflow/     # grafo LangGraph, nodes, state
├── tests/
├── README.md
├── ARCHITECTURE.md
├── RUNNING.md
├── LICENSE
└── ...
```
