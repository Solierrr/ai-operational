<p align="center">
  <img src="../assets/readme/banners/fastapi.png" alt="FastAPI" width="100%">
</p>

# Deploy

O processo compartilhado está em [QA_RENDER.md](https://github.com/Solierrr/docs-warehouse/blob/main/readme/deploy/QA_RENDER.md) e [PROD_GKE_ARGOCD.md](https://github.com/Solierrr/docs-warehouse/blob/main/readme/deploy/PROD_GKE_ARGOCD.md). Os arquivos do serviço descrevem os destinos, mas não comprovam disponibilidade no momento da leitura.

## Ambientes

Os endereços abaixo vêm do contrato HTTP e dos manifestos.

| Ambiente | Destino | Endereço |
|---|---|---|
| Local | Uvicorn | [API local](http://localhost:8000) |
| QA | Render | [API de QA](https://ai-operational.onrender.com) |
| Produção | GKE, com ingresso Kong declarado | [API de produção declarada](https://operational.solarianetwork.site) |

O QA está publicado no Render, no endereço acima, e a main analisada não contém `render.yaml` nem `render-entrypoint.sh`, porque a configuração é injetada pela plataforma.

Os manifestos de produção são o [Deployment](https://github.com/Solierrr/infra-gitops/blob/main/services/ai-operational/deployment.yaml), o [Service](https://github.com/Solierrr/infra-gitops/blob/main/services/ai-operational/service.yaml), o [Ingress](https://github.com/Solierrr/infra-gitops/blob/main/services/ai-operational/ingress.yaml) e a [aplicação do Argo CD](https://github.com/Solierrr/infra-gitops/blob/main/apps/ai/ai-operational.yaml), e o serviço está em operação no cluster de produção.

## Particularidades

O Dockerfile instala `requirements.txt` sobre `python:latest`, expõe a porta 8000 e executa Uvicorn em `0.0.0.0`. Não há leitura do Infisical no comando da imagem. As variáveis precisam chegar ao processo pelo ambiente.

O workflow `environment-status.yml` consulta `/ready` no QA. A verificação de produção consulta a existência do cluster e não faz uma chamada de prontidão específica deste serviço. No Render, o caminho de prontidão a configurar é `/ready`.

O Deployment usa uma réplica, `envFrom` com `ai-operational-secrets`, acesso interno ao `api-core` e URL A2A interna, com readiness e liveness ainda apontando para `/health`. A imagem ainda usa a tag `latest`, em desacordo com o padrão de versão imutável, e o manifesto não desliga explicitamente a documentação HTTP, embora o segredo possa conter essa configuração.

`A2A_PUBLIC_URL` precisa corresponder ao endereço que o chamador consegue acessar. O padrão local em `settings.py` anuncia a porta 8003, enquanto `make dev` escuta na 8000. Ajuste a configuração do ambiente antes de usar descoberta A2A.

## Publicação e configuração

O push na main chama o workflow compartilhado `docker-publish.yml`, e o release-please atualiza a versão, inclusive em `version.txt` e no `openapi.yaml`. O fluxo entre os repositórios está em [RELEASE_AND_DEPLOY.md](https://github.com/Solierrr/docs-warehouse/blob/main/docs/flows/RELEASE_AND_DEPLOY.md).

O MongoDB deve aceitar criação de índices na partida e gravação dos checkpoints. O JWT depende de JWKS e emissor configurados. O histórico precisa de URL do `api-messenger` e da chave de serviço. Para manter propostas verificáveis após reinícios, configure uma chave de assinatura estável. Isso não substitui controle de concorrência entre réplicas.

O tracing LangSmith é opcional. Suas variáveis próprias ficam em `settings.py` e o Makefile importa `/observability` apenas em QA. O código avisa sobre tracing global ativado, mas não o desativa. A lista `DEBUG_ADMIN_SUBS` controla o acesso ao debug inclusive em produção.
