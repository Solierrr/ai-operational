# Observabilidade com LangSmith

Rastreamento opcional de cada turno do grafo no LangSmith. Vem desligado por padrão.

## Como ligar

Variáveis do `settings` (no Infisical, pasta `/observability` do ambiente):

| Variável | Padrão | Uso |
|---|---|---|
| `SOLARIA_LANGSMITH_ENABLED` | `false` | Liga o tracing |
| `SOLARIA_LANGSMITH_API_KEY` | | Chave do LangSmith |
| `SOLARIA_LANGSMITH_PROJECT` | `solaria-local` | Projeto (`solaria-qa`, `solaria-prod`) |
| `SOLARIA_LANGSMITH_ENDPOINT` | padrão do SDK | Só para região ou instância própria |
| `SOLARIA_LANGSMITH_SAMPLING_RATE` | `1.0` | Fração dos turnos enviados |

Não use `LANGSMITH_*` nem `LANGCHAIN_*`: ligam o tracing global do LangChain, sem
mascaramento. A subida da API registra um aviso se alguma estiver `true`.

## O que é enviado

- Um trace por turno do `/chat`, `/debug/chat` e do replay de nó, com todos os nós do grafo,
  incluindo as chamadas de ferramentas dos agentes Guia e Consulta.
- Metadata: `conversation_id`, `environment`, `assistant` (`ai-operational`) e `source`
  (`chat`, `debug` ou `debug-replay`). Tag: o ambiente em minúsculas.
- Os projetos e dashboards do sandbox agrupam por `assistant`, então os números do
  ai-operational aparecem ao lado dos do ai-assistant.

## Limites

- Mascaramento por regex: CPF, CNPJ, telefone, e-mail, JWT e chaves. Nome e endereço não
  são mascarados.
- O custo por step e o histórico continuam no `StepTracker` e no `api-messenger`.
