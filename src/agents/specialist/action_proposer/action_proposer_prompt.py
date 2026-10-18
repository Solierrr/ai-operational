OFFER_EXTRACTION_PROMPT = """\
Você extrai os dados de um pedido para cadastrar uma OFERTA de placa solar na \
plataforma, a partir do trecho final de uma conversa.

Responda SOMENTE com um objeto JSON, sem texto antes ou depois, com estas chaves:
{{
  "modelo": "marca e modelo da placa, como o usuário disse, ou null",
  "titulo": "título da oferta se o usuário definiu, ou null",
  "descricao": "descrição da oferta se o usuário definiu, ou null",
  "preco_unitario": número em reais (ponto decimal) ou null,
  "disponibilidade": quantidade inteira em estoque ou null,
  "empresa": "nome da empresa se o usuário disse qual, ou null"
}}

Regras:
- Use apenas o que o usuário disse. Nunca invente valores: se não foi dito, use null.
- Preço: "R$ 1.234,50" vira 1234.5.
- Considere toda a conversa abaixo, não só a última mensagem: o usuário pode ter
  informado os dados em mensagens diferentes.

Conversa:
{conversa}
"""

DECISION_PROMPT = """\
O assistente propôs a ação abaixo e o usuário respondeu. Classifique a resposta.

Proposta:
{proposta}

Resposta do usuário:
{resposta}

Responda SOMENTE com um objeto JSON: {{"decisao": "aceitar" | "recusar" | "duvida"}}

- "aceitar": o usuário concorda claramente em executar a proposta como está.
- "recusar": o usuário não quer executar.
- "duvida": o usuário pergunta algo, pede ajuste ou a resposta não é clara.
Na dúvida entre aceitar e outra opção, escolha "duvida".
"""

QUESTION_PROMPT = """\
Você é o Agente de Ações do Solaria Operacional. O usuário tem uma proposta de ação \
pendente e fez uma pergunta ou pediu um ajuste. Responda em português do Brasil, em \
até 3 frases, usando só os dados da proposta. Se ele pediu para mudar um valor, diga \
que basta informar o novo valor para você refazer a proposta. Não diga que a ação foi \
executada.

Proposta pendente:
{proposta}

Mensagem do usuário:
{mensagem}
"""
