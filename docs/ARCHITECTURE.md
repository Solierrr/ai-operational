<p align="center">
  <img src="../assets/readme/banners/fastapi.png" alt="FastAPI" width="100%">
</p>

# Arquitetura

A API FastAPI atende turnos HTTP e delegações A2A. O LangGraph aplica o guardrail de entrada, resume o histórico e escolhe especialistas. Consultas e instruções passam pela composição e revisão da resposta. Propostas e resultados de ações encerram o grafo diretamente, para preservar o texto montado com os campos validados.

```mermaid
flowchart LR
    Cliente[web-sandbox] -->|HTTP + JWT| API[FastAPI]
    Assist[ai-assistant] -->|A2A sobre HTTP + JWT| API
    API --> Grafo[LangGraph]
    API -->|HTTP público, JWKS| Auth[api-auth]
    Grafo -->|HTTP + JWT da pessoa| Core[api-core]
    Grafo -->|HTTP + JWT ou X-Service-Key| Msg[api-messenger]
    Grafo -->|driver MongoDB| Mongo[(MongoDB)]
    Grafo -->|HTTPS + chave do provedor| Gemini[Gemini]
    Grafo -->|HTTPS + chave do provedor| Groq[Groq]
    Grafo -->|HTTPS opcional + chave| Smith[LangSmith]
```

## Organização do código

As responsabilidades ficam separadas entre entrada, execução e acesso aos serviços.

| Caminho | Papel |
|---|---|
| `src/api/` | rotas, schemas, erros HTTP e health checks |
| `src/a2a/` | Agent Card e adaptação da delegação para um turno |
| `src/workflow/graph/`, `nodes/`, `edges/` | grafo, especialistas e decisões de caminho |
| `src/workflow/runner.py` | contexto de autenticação, bloqueio por conversa e histórico |
| `src/actions/` | registro de ações, rascunhos, propostas assinadas e execução |
| `src/agents/` | prompts e construção dos agentes |
| `src/domain/`, `src/tools/` | catálogo de telas, guias e ferramentas de consulta |
| `src/infra/` | clientes HTTP, MongoDB, MCP e Redis |
| `src/memory/` | checkpointer do LangGraph |
| `src/core/` | configuração, JWT, proteção de entrada e observabilidade |
| `tests/` | testes de API, ações, infraestrutura e workflow |

## Integrações

O código atual usa o `api-core` para os dados operacionais, e os clientes MCP e Redis permanecem na infraestrutura, sem chamada no grafo ativo, embora o mapa central ainda descreva o MCP como dependência da delegação.

| Com quem | Direção | Protocolo | Autenticação |
|---|---|---|---|
| `web-sandbox` | chama este serviço | HTTP em `/chat` e `/debug/chat` | JWT, com lista de administradores no debug |
| `ai-assistant` | chama este serviço | A2A sobre HTTP, montado pela biblioteca compartilhada | JWT da pessoa |
| `api-auth` | este serviço consulta | HTTP para JWKS | chave pública, validação local RS256 |
| `api-core` | este serviço chama | HTTP REST | JWT da pessoa, inclusive para gravações |
| `api-messenger` | este serviço chama | HTTP REST | JWT para conversa e mensagem da pessoa, `X-Service-Key` para resposta e observabilidade |
| Gemini e Groq | este serviço chama | HTTPS pelos SDKs de LLM | chave do provedor |
| LangSmith | este serviço envia traces opcionais | HTTPS | credencial própria |
| `mcp-database` | cliente presente, sem uso no grafo | MCP Streamable HTTP | `X-Service-Key`, com `x-api-key` legado se configurado |
| Redis | cliente presente, sem uso no grafo | Redis com TLS | usuário e senha |

O JWT no `api-core` preserva as permissões de quem pediu a operação. As chamadas internas ao serviço de mensagens seguem o [fluxo de autenticação entre serviços](https://github.com/Solierrr/docs-warehouse/blob/main/docs/flows/SERVICE_TO_SERVICE_AUTH.md).

## Grafo e decisões

O roteador escolhe `screen_finder`, `how_to_guide`, `data_reader` ou `action_proposer`. Cada especialista é consultado no máximo uma vez por turno, com limite de três especialistas. Os três primeiros voltam ao roteador. O orquestrador compõe a resposta, o juiz pode pedir revisão e o guardrail de saída filtra o texto.

Quando existe uma `pending_proposal`, o roteador envia a mensagem ao nó `proposal_decision`, que limpa a proposta e volta ao roteador se a pessoa pedir ajuste ou mudar de assunto, e encerra o turno no aceite ou na recusa. Os detalhes estão no [fluxo de aprovação](../flows/ACTION_APPROVAL.md).

O registro em [`src/actions/registry.py`](https://github.com/Solierrr/ai-operational/blob/main/src/actions/registry.py) limita as operações possíveis. Cada `ActionSpec` define schema, preparação, execução e resposta. O LLM extrai um rascunho, e a preparação resolve identificadores nas respostas do `api-core`. A proposta recebe HMAC-SHA256, dono e hora de criação. A assinatura usa `PROPOSAL_SIGNING_KEY`, depois `SERVICE_KEY` como alternativa e, sem ambas, uma chave aleatória do processo.

O aceite é reconhecido por frases normalizadas em `strict_decision`. O LLM pode classificar dúvida, recusa, ajuste ou outro assunto, mas não autoriza execução. Encerrar oferta e cancelar pedido exigem uma das fórmulas explícitas com "confirmo". O contador `writes_done` limita as gravações por conversa.

O guardrail de entrada limita o tamanho da mensagem e verifica padrões de manipulação e pedidos de dados internos antes da classificação por LLM. Textos externos passam por limpeza e entram nos prompts delimitados como dados. As ferramentas de conta são somente leitura. A escrita fica no nó de decisão, fora das ferramentas fornecidas ao modelo. O guardrail de saída remove links e padrões de segredos das respostas geradas, mas propostas e resultados usam seu próprio caminho de validação.

## Memória e histórico

O [MongoDB](../database/MONGO.md) guarda checkpoints e fatos por pessoa. A thread recebe o prefixo `operational:` para não colidir com o assistente principal. Com mais de cinco mensagens, o resumo incorpora as antigas e mantém as duas mais recentes no contexto ativo.

O runner cria a conversa no `api-messenger`, grava a mensagem da pessoa antes do grafo e a resposta depois dele. O vínculo entre thread e conversa remota fica em memória do processo. A extração de até vinte fatos acontece em background após a resposta. Uma falha nessa atualização é registrada sem desfazer o turno.

O `asyncio.Lock` serializa turnos da mesma conversa dentro do processo. Não há bloqueio distribuído. A leitura do dono do checkpoint recusa uma conversa de outra pessoa quando encontra o dono, mas uma exceção nessa leitura é registrada e permite continuar. Essas limitações estão em [STATUS.md](./STATUS.md).

## Observabilidade, health e versão

O `StepTracker` envia etapas e chamadas de LLM ao `api-messenger`. O custo por chamada é estimado com tokens e a tabela de `model_pricing.py`. Modelo sem preço e chamada com erro registram custo zero. O histórico enviado passa por anonimização de texto.

O tracing LangSmith é opcional, com amostragem e mascaramento de documentos, telefone, e-mail, JWT e chaves. Nomes e endereços não são mascarados. O tracing global do SDK recebe apenas um aviso de configuração e deve permanecer desligado para usar o caminho com mascaramento.

O OpenTelemetry instrumenta FastAPI, HTTPX, MongoDB e Redis a partir de `OTEL_EXPORTER_OTLP_ENDPOINT`, `SERVICE_VERSION`, `DEPLOYMENT_ENVIRONMENT` e `OTEL_TRACES_SAMPLING_PROBABILITY`, e pode ser desligado com `OTEL_SDK_DISABLED`. As respostas com um span válido levam o cabeçalho `X-Trace-Id`, e a exclusão automática de rastreamento cobre o `/health`, mas não o `/ready`.

O `/health` informa o processo e a versão, e o `/ready` faz apenas um `ping` no MongoDB com limite de dois segundos, sem mudar quando o modelo de linguagem ou o serviço de mensagens falham. O `version.txt` alimenta a API, o OpenAPI, o Agent Card e o health, enquanto a versão enviada à telemetria depende da configuração do ambiente.

A análise usa a main em [`d1a5e666`](https://github.com/Solierrr/ai-operational/commit/d1a5e666df853aba51ab49f190c7c0b631613b80), conferida em 2026-10-30.

## Diagrama de arquitetura

### Onde o serviço se encaixa

O `ai-operational` não recebe conversa direto do usuário: o `ai-assistant` delega a ele por A2A, repassando o JWT do usuário. Tudo que o serviço lê ou grava no `api-core` usa esse JWT.

```mermaid
flowchart LR
    U(["usuário (web)"]) --> ASS["ai-assistant"]
    ASS ==>|"A2A + JWT do usuário<br/>habilidade operar-saas"| OPS

    subgraph OPS["ai-operational (FastAPI + LangGraph)"]
        G["grafo de agentes"]
        ACT["ações e proposta assinada"]
    end

    OPS -->|"lê e grava com o JWT do usuário"| CORE["api-core"]
    OPS --> MONGO[("MongoDB<br/>checkpoints e proposta pendente")]
    OPS --> MSG["api-messenger<br/>passos do turno"]
    OPS --> LLM["Gemini, Groq, OpenAI"]
    OPS -.->|"opcional"| LS["LangSmith<br/>PII mascarada"]
```

### Grafo de um turno

```mermaid
flowchart TD
    START([mensagem]) --> IG["input_guardrail<br/>tamanho, injeção, PII"]
    IG -->|bloqueada| END0([recusa])
    IG --> CM["condense_memory"]
    CM --> R{"router"}

    R --> SF["screen_finder<br/>onde fica a tela"]
    R --> HG["how_to_guide<br/>passo a passo"]
    R --> DR["data_reader<br/>dados do usuário, só leitura"]
    R --> AP["action_proposer<br/>monta a proposta, sem gravar"]
    R -->|"há proposta pendente"| PD["proposal_decision<br/>aceite, recusa, dúvida"]

    SF --> R
    HG --> R
    DR --> R

    R -->|"informação suficiente"| ORQ["orchestrator"]
    ORQ --> J{"judge"}
    J -->|"aprovada"| OG["output_guardrail<br/>remove links e segredos"]
    J -->|"reprovada: 1 nova tentativa"| ORQ
    J -->|"reprovada de novo"| BL["resposta trocada por<br/>pedido de reformulação"]
    BL --> OG
    OG --> END1([resposta])

    AP -->|"proposta, exatamente como montada"| END2([resposta ao usuário])
    PD -->|"executou ou recusou"| END3([resposta ao usuário])
    PD -->|"ajustar ou outro assunto:<br/>descarta a proposta"| R
```

### Ciclo de vida de uma proposta

```mermaid
stateDiagram-v2
    [*] --> Proposta: action_proposer monta e assina
    Proposta --> Executada: aceite exato do usuário<br/>("sim", ou "confirmo" se irreversível)
    Proposta --> Recusada: "não"
    Proposta --> Descartada: ajustar ou mudar de assunto
    Proposta --> Expirada: 15 minutos sem decisão
    Proposta --> Proposta: dúvida: responde e continua pendente
    Executada --> [*]: grava no api-core com o JWT do usuário
    Recusada --> [*]
    Descartada --> [*]
    Expirada --> [*]
```

### O que acontece com a oferta: aceite, recusa, dúvida, ajuste e expiração

Exemplo com o cadastro de uma oferta. As mesmas respostas valem para as outras ações, com a mensagem de recusa própria de cada uma.

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuário
    participant O as ai-operational
    participant C as api-core

    U->>O: "Cadastra uma placa Canadian CS6R 550 Wp, R$ 900, 40 unidades"
    O->>C: lê as empresas do usuário e os modelos aprovados (JWT do usuário)
    C-->>O: dados do próprio usuário
    O->>O: monta o payload, assina e guarda como proposta pendente
    O-->>U: proposta com empresa, placa, título, descrição, preço e quantidade.<br/>"Você aceita?"

    alt aceite exato ("sim", "aceito"...)
        O->>O: confere assinatura, validade e dono da proposta
        O->>C: POST /offers com o JWT do usuário
        alt o api-core aceita
            C-->>O: oferta criada
            O-->>U: "Pronto, a oferta ... foi cadastrada"
        else o api-core recusa
            C-->>O: erro com o motivo
            O-->>U: "Não consegui executar. (motivo)" e a proposta é descartada
        end
    else recusa ("não", "recuso", "cancela")
        O-->>U: "Tudo bem, não cadastrei nada."
        Note over O: proposta descartada, nada foi gravado
    else dúvida ("por que esse preço?")
        O-->>U: explica e lembra que a proposta continua pendente
    else ajuste ("muda o preço para 850")
        Note over O: proposta descartada, a mensagem volta ao roteador
        O-->>U: nova proposta com o valor ajustado
    else outro assunto
        Note over O: proposta descartada, a mensagem é tratada normalmente
    else passaram 15 minutos
        alt a resposta é um sim ou um não
            O-->>U: "Essa proposta expirou por segurança e nada foi feito"
        else qualquer outra mensagem
            Note over O: a proposta vencida é descartada em silêncio
        end
    end
```

Nos dois casos que não executam (recusa e expiração), nada é gravado e a proposta sai do estado. Para uma ação irreversível (encerrar oferta, cancelar pedido) o aceite não é "sim": só vale a palavra "confirmo"; um "sim" recebe de volta o pedido de confirmação e a proposta continua pendente.

### Como o agente monta a proposta

```mermaid
flowchart TD
    M(["pedido de ação do usuário"]) --> T{"tem JWT?"}
    T -->|não| X1(["pede para entrar na conta"])
    T -->|sim| L{"limite de gravações<br/>da conversa atingido?"}
    L -->|sim| X2(["explica o limite e sugere nova conversa"])
    L -->|não| P{"é compra, pagamento, exclusão,<br/>transferência, senha, cargo ou permissão?"}
    P -->|sim| X3(["recusa e indica a tela da plataforma"])
    P -->|não| S["seleciona a ação na lista fixa<br/>(LLM escolhe entre 5 ações ou proibida)"]
    S -->|"nenhuma ou desconhecida"| X4(["não entendi: lista o que sabe fazer"])
    S --> E["extrai os dados do pedido (LLM)"]
    E -->|"saída inválida"| X4
    E --> PR["prepare: confere o pedido nos dados<br/>do próprio usuário no api-core"]
    PR -->|"falta campo, nome ambíguo ou<br/>item não encontrado"| Q(["pergunta ao usuário, com opções"])
    PR -->|pronto| AS["monta o resumo, assina<br/>e grava como proposta pendente"]
    AS --> R(["proposta ao usuário:<br/>você aceita?"])
```

### Ações disponíveis

| Ação | Endpoint no `api-core` | Aceite |
|---|---|---|
| `create_offer`: cadastrar oferta | `POST /offers` | "sim" |
| `set_offer_status`: pausar ou reativar | `PATCH /offers/{id}/status` | "sim" |
| `set_offer_status`: encerrar | `PATCH /offers/{id}/status` | só "confirmo" |
| `set_inventory_quantity`: ajustar estoque | `PATCH /inventories/{id}/quantity` | "sim" |
| `cancel_order`: cancelar pedido | `PATCH /orders/{id}/cancel` | só "confirmo" |
| `update_cart`: mexer no carrinho (não finaliza compra) | `PUT` ou `DELETE /cart/items/{offerId}` | "sim" |

### Camadas de segurança

```mermaid
flowchart LR
    A["mensagem"] --> B["guardrail de entrada<br/>tamanho máximo, regex de injeção<br/>(inclui pedidos de pular o aceite)<br/>e classificador por LLM"]
    B --> C["pedido proibido<br/>recusado por regex e pelo seletor"]
    C --> D["ids só vindos dos dados do próprio<br/>usuário, nunca do texto do modelo"]
    D --> E["proposta assinada (HMAC),<br/>com validade e dona"]
    E --> F["aceite conferido em código:<br/>o LLM não pode aceitar"]
    F --> G["teto de gravações<br/>por conversa"]
    G --> H["grava com o JWT do usuário,<br/>sem credencial de serviço"]
    H --> I["resposta sem links<br/>nem segredos"]
```

Dados lidos do `api-core` e das ferramentas entram nos prompts marcados como dado e com links e instruções neutralizados, nunca como instrução.
