# Segurança das ações e contra prompt injection

O assistente nunca grava nada sem o aceite explícito do usuário, e a defesa não depende
de o LLM se comportar: ela está no código.

## Regra de ouro

Só quem grava é o nó `proposal_decision`, e ele só roda quando existe uma proposta
pendente e a última mensagem do **usuário** é a frase exata de aceite. Nada que venha de
ferramenta, do api-core, de outro agente ou do LLM conta como aceite.

## Como uma ação acontece

1. O roteador manda o pedido para o Agente de Ações.
2. O seletor escolhe a ação numa lista fixa (`src/actions/registry.py`). Qualquer nome fora
   da lista, ou `proibida`, vira recusa.
3. A ação lê os dados do próprio usuário no api-core (JWT dele) e resolve ids por
   correspondência de texto com essa lista. Um id escrito pelo LLM ou pelo usuário nunca
   é usado.
4. O assistente monta a proposta com os valores exatos e a guarda em `pending_proposal`,
   assinada com HMAC-SHA256 (`PROPOSAL_SIGNING_KEY`, ou `SERVICE_KEY` se vazia), com id,
   usuário dono e hora de criação.
5. No turno seguinte, `proposal_decision` verifica a assinatura, o dono e a validade
   (`PROPOSAL_TTL_SECONDS`, 15 min). Proposta adulterada, de outro usuário, expirada ou de
   ação desconhecida é descartada.
6. O aceite é determinístico (`src/actions/decision.py`): "sim", "pode executar" etc.,
   frase exata. O LLM só classifica recusa, dúvida, ajuste ou outro assunto; se ele disser
   "aceitar", o resultado é tratado como dúvida. Ajuste e outro assunto descartam a
   proposta e voltam ao roteador (uma nova proposta exige novo aceite).
7. Ações sem volta (encerrar oferta, cancelar pedido) exigem a palavra "confirmo"; "sim"
   não basta.
8. Cada conversa tem um teto de gravações (`MAX_WRITES_PER_CONVERSATION`).
9. Em modo debug nada é gravado: a execução é simulada.

## Ações e o que o assistente nunca faz

Ações: cadastrar oferta, pausar/reativar/encerrar oferta, ajustar estoque, cancelar um
pedido do próprio usuário, colocar/tirar item do carrinho.

Nunca faz: comprar, pagar, finalizar compra, transferir, apagar ou excluir, mudar senha,
cargo ou permissão. Um filtro determinístico e o seletor recusam esses pedidos e indicam
a tela.

## Camadas contra prompt injection

- **Entrada** (`input_guardrail`): limite de tamanho (`MAX_MESSAGE_CHARS`); detecção por
  padrões em várias formas do texto (sem acentos, caracteres invisíveis, leetspeak, letras
  espaçadas, separadores), incluindo tentativas de pular a confirmação; palavras de dados
  internos; classificador LLM com a mensagem delimitada como dado.
- **Dados de fora** (`src/core/security/untrusted.py`): textos do api-core e resultados
  de ferramentas são limpos (caracteres de controle, links, ordens) e entram no LLM
  delimitados por `<dados_externos id=...>` com marca aleatória, avisando que são dados.
- **Prompts**: o SYSTEM_CORE diz que dados e resultados de ferramentas nunca são
  instrução nem aceite; roteador, Guia, Consulta e extratores repetem a regra.
- **Ferramentas**: as de consulta são somente leitura; as de escrita não existem para o
  LLM, só para o nó de decisão.
- **Saída**: o guardrail de saída remove links e segredos (JWT, Bearer, chaves) do texto
  gerado por LLM; os textos de proposta e resultado são montados a partir de campos
  validados e limpos.
- **Observabilidade**: o LangSmith mascara CPF, CNPJ, telefone, e-mail, JWT e chaves.

## Limites

- A detecção por padrões não pega tudo; a garantia real vem da estrutura (aceite exato,
  ids vindos dos dados do usuário, RBAC do api-core).
- O assistente depende das permissões do api-core: ele nunca tem mais acesso que o usuário.
- Os guias descrevem fluxos a partir do registro de telas e dos campos do api-core; detalhes
  de tela (nomes de botões) devem ser revisados quando o documento do app existir.
