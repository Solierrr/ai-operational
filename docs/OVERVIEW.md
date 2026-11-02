<p align="center">
  <img src="../assets/readme/banners/fastapi.png" alt="FastAPI" width="100%">
</p>

# Visão de produto

O assistente de operações atende quem compra, oferece placas solares ou administra uma empresa na plataforma. Ele explica como realizar uma tarefa, indica a tela correspondente e consulta informações da conta. Pedidos que alteram dados passam por uma proposta antes da confirmação.

## Capacidades

A pessoa pode pedir orientação e realizar operações na mesma conversa.

- Encontrar telas e receber instruções sobre as tarefas da plataforma.
- Consultar empresas vinculadas, ofertas, estoque, pedidos, vendas, carrinho, assinatura e cobranças.
- Cadastrar uma oferta de placa solar com modelo, preço e disponibilidade.
- Pausar, reativar ou encerrar uma oferta da empresa.
- Ajustar a quantidade total em estoque de um modelo.
- Cancelar um pedido de compra próprio que esteja pago.
- Definir a quantidade de uma oferta no carrinho ou retirar o item.

## Regras das alterações

O assistente mostra o que pretende fazer antes de alterar os dados. O aceite deve vir da própria pessoa em uma mensagem posterior. Uma resposta negativa descarta a proposta. Um ajuste ou mudança de assunto também a descarta, e uma nova proposta exige outro aceite.

Encerrar oferta e cancelar pedido são tratados como ações sem volta e exigem confirmação com "confirmo". Uma oferta encerrada não pode ser reaberta. Uma proposta expira após quinze minutos na configuração padrão, para que uma autorização antiga não execute uma alteração depois de muito tempo.

Para cadastrar oferta, a pessoa precisa estar vinculada a uma empresa fornecedora e escolher um modelo aprovado. O preço deve ser positivo e a disponibilidade não pode ser negativa. Quando há mais de uma empresa ou modelo compatível, o assistente pede uma escolha antes de propor a alteração.

O ajuste de estoque recebe o novo total, em vez da diferença. No carrinho, quantidade zero retira o item. A quantidade solicitada é comparada com a disponibilidade informada pelo catálogo. As permissões da conta continuam valendo para consultas e alterações.

O assistente não compra, paga, transfere valores, exclui contas ou empresas, nem muda senha, cargo ou permissão. Para essas tarefas, orienta a pessoa a usar as telas. Cada conversa admite até dez alterações na configuração padrão.

## Onde a pessoa encontra

O assistente principal delega os pedidos operacionais, e o portal de QA permite testar a conversa e, para administradores autorizados, inspecionar as etapas.

## Relação com a plataforma

O cadastro central fornece os dados e aplica as permissões da pessoa. O serviço de mensagens guarda o histórico e os registros de execução. A memória da conversa permite retomar uma proposta pendente e aproveitar preferências aprendidas, sujeita aos limites de retenção e concorrência descritos na documentação técnica.
