<p align="center">
  <img src="../assets/readme/banners/fastapi.png" alt="FastAPI" width="100%">
</p>

# Consulta e orientação

A pessoa pede seus dados ou uma instrução de uso. O roteador escolhe consulta de conta, guia ou localização de tela. Consultas usam o JWT da pessoa, enquanto guias e telas vêm dos catálogos do próprio serviço.

```mermaid
sequenceDiagram
    participant Pessoa as Pessoa
    participant Grafo as Grafo operacional
    participant Core as api-core
    participant Catalogo as Catálogo local
    Pessoa->>Grafo: HTTP de chat + JWT, com pergunta
    Grafo->>Grafo: guardrail de entrada e roteador
    alt consulta de conta
        Grafo->>Core: HTTP REST + JWT da pessoa
        alt consulta recusada ou indisponível
            Core-->>Grafo: erro HTTP ou falha de transporte
            Grafo->>Grafo: ferramenta devolve mensagem de falha
        else consulta atendida
            Core-->>Grafo: dados acessíveis da pessoa
            Grafo->>Grafo: selecionar campos e delimitar dados externos
        end
    else orientação de uso
        Grafo->>Catalogo: buscar guia ou tela
        Catalogo-->>Grafo: passos e caminhos encontrados
    end
    Grafo->>Grafo: compor, revisar e filtrar resposta
    Grafo-->>Pessoa: resposta HTTP com outcome e reason
```

As listagens de conta mostram até quinze registros por ferramenta, e o total retornado permite informar que a lista foi reduzida, sem que essas consultas alterem dados. A ampliação documentada aqui usa HTTP direto, embora o [fluxo central](https://github.com/Solierrr/docs-warehouse/blob/main/docs/flows/ASSISTANT_CHAT.md) ainda cite ferramentas MCP.

## Casos de erro

- Sem token no contexto, a ferramenta devolve mensagem de falta de autenticação.
- Permissão negada, recurso ausente e indisponibilidade do cadastro central viram mensagens da ferramenta. Nem toda falha de consulta é marcada como `TOOL_FAILED`.
- Um guia ou uma tela sem correspondência no catálogo estático não autoriza inventar uma operação.
- Recusa de entrada encerra o fluxo antes da consulta. O juiz pode rejeitar a resposta composta.
- Falha do histórico remoto ou do provedor pode impedir a resposta, mesmo com MongoDB pronto.
