<p align="center">
  <img src="../assets/readme/banners/fastapi.png" alt="FastAPI" width="100%">
</p>

# Situação

O estado abaixo foi verificado na main em 2026-10-30. Funcionalidade presente no código não comprova disponibilidade de um ambiente publicado.

## Implementado

- O chat valida JWT, executa o grafo e responde com `outcome` e `reason` (2026-10-30).
- O A2A valida token, recebe delegações e sinaliza `input_required` para proposta pendente (2026-10-30).
- Guias, localização de telas, consultas de conta e cinco tipos de ação estão registrados. O módulo de situação da oferta cobre pausa, reativação e encerramento (2026-10-30).
- Propostas têm assinatura, dono, expiração, aceite determinístico e limite de gravações. O debug simula as escritas no cadastro central (2026-10-30).
- OpenAPI exportado, erros HTTP, `/health`, `/ready`, histórico remoto e tracing estão presentes (2026-10-30).

## Ambientes sem confirmação operacional

- O QA está publicado no Render, com destino no contrato e verificação de readiness (2026-10-30).
- Os manifestos de produção usam `latest` e readiness em `/health`, e o serviço está em operação no cluster (2026-10-30).

## Limitações verificadas

- O bloqueio por conversa é local ao processo. Duas réplicas não compartilham o `asyncio.Lock`, e não há idempotência distribuída para a execução das ações (2026-10-30).
- Sem chave de assinatura configurada, o selo usa uma chave aleatória do processo. Uma proposta persistida deixa de validar depois de reiniciar esse processo (2026-10-30).
- Se a leitura do dono do checkpoint lança exceção, o runner registra o erro e continua. O isolamento depende dessa leitura e das permissões do serviço de destino (2026-10-30).
- A memória durável usa leitura e substituição de fatos em background. Conversas concorrentes da mesma pessoa podem sobrescrever os fatos umas das outras. A exclusão de dados sensíveis depende do prompt de extração, sem validação técnica posterior (2026-10-30).
- O índice único da memória é criado no lifespan da API, e a CLI não executa esse preparo. Os fatos não têm TTL e ficam até a exclusão da conta, e a coleção própria deste agente ainda precisa substituir a chave somente por `user_id` (2026-10-30).
- O vínculo com a conversa do `api-messenger` fica em memória e é perdido no reinício. Falhas na gravação do histórico podem interromper o turno, embora `/ready` continue verificando somente MongoDB (2026-10-30).
- O fallback da cadeia de LLM não cobre todos os nós. Roteamento e resumo usam Groq diretamente. Um health pronto não comprova capacidade de geração de resposta (2026-10-30).
- O Dockerfile usa `python:latest`, e parte das dependências não tem versão fixa. O lint cobre apenas parte da árvore de código (2026-10-30).
- O handler de debug ainda tem respostas 500 com diagnóstico parcial fora do envelope de erro comum. A2A devolve texto para falhas de autenticação tratadas pelo adaptador (2026-10-30).
- O custo por chamada é estimado. Modelo sem preço e chamada com erro ficam com custo zero. O mascaramento de tracing não cobre nomes nem endereços (2026-10-30).
- A main já vai além da criação de ofertas descrita nos metadados do OpenAPI e é a referência funcional do serviço. O catálogo central ainda não lista os motivos de resultado, e o mapa de integrações cita MCP, embora o grafo use consultas HTTP diretas (2026-10-30).
- Os guias dependem de um catálogo estático de telas, mantido junto com a interface (2026-10-30).
