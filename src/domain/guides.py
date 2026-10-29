from dataclasses import dataclass

from src.domain.screens import DEFAULT_LANG, SCREENS
from src.domain.text import stems

_TELAS = {screen.id: screen for screen in SCREENS}
MIN_SCORE = 2


@dataclass(frozen=True)
class Step:
    texto: str
    tela: str | None = None


@dataclass(frozen=True)
class Guide:
    id: str
    titulo: str
    resumo: str
    keywords: tuple[str, ...]
    passos: tuple[Step, ...]
    para_quem: str = "qualquer usuário autenticado"
    requisitos: tuple[str, ...] = ()
    dicas: tuple[str, ...] = ()
    acao_do_assistente: str | None = None


GUIDES: tuple[Guide, ...] = (
    Guide(
        "cadastrar_empresa",
        "Cadastrar a sua empresa",
        "Cria a empresa na plataforma e envia o cadastro para análise.",
        (
            "cadastrar empresa",
            "criar empresa",
            "registrar empresa",
            "cnpj",
            "nova empresa",
        ),
        (
            Step("Abra o formulário de cadastro de empresa.", "register_company"),
            Step(
                "Preencha os dados da empresa (CNPJ, endereço e contato) direto no formulário."
            ),
            Step(
                "Envie o cadastro. Ele passa por uma análise antes de a empresa ser liberada."
            ),
            Step(
                "Acompanhe o andamento na tela de status do cadastro.",
                "registration_status",
            ),
        ),
        requisitos=("Estar logado na plataforma.",),
        dicas=(
            "Nunca digite CNPJ, telefone ou e-mail aqui no chat: use só o formulário.",
        ),
    ),
    Guide(
        "entrar_em_empresa",
        "Entrar em uma empresa com código de acesso",
        "Usa o código que a empresa gerou para você ser vinculado a ela.",
        (
            "codigo de acesso",
            "convite da empresa",
            "entrar na empresa",
            "ativar acesso",
            "resgatar codigo",
        ),
        (
            Step("Peça a um administrador da empresa o código de acesso."),
            Step("Abra a tela de ativação de código de acesso.", "activate_access"),
            Step("Informe o código e confirme."),
            Step("Confira se a empresa aparece na sua conta."),
        ),
        requisitos=(
            "Ter uma conta e receber um código de um administrador da empresa.",
        ),
    ),
    Guide(
        "gerar_codigo_acesso",
        "Convidar alguém para a sua empresa",
        "O administrador gera um código de acesso e define o cargo de cada pessoa da equipe.",
        (
            "convidar funcionario",
            "gerar codigo de acesso",
            "adicionar funcionario",
            "equipe",
            "cargos",
            "permissoes",
        ),
        (
            Step("Abra a tela de funcionários da empresa.", "employees"),
            Step("Gere um código de acesso e escolha o cargo da pessoa."),
            Step(
                "Envie o código para a pessoa. Ela o ativa na tela de ativação de código.",
                "activate_access",
            ),
            Step("Ajuste cargos e remova acessos pela mesma tela, quando precisar."),
        ),
        para_quem="administrador da empresa",
    ),
    Guide(
        "cadastrar_modelo",
        "Cadastrar um modelo de placa solar",
        "Inclui no catálogo um modelo de placa que depois poderá virar oferta.",
        (
            "cadastrar modelo",
            "novo modelo",
            "modelo de placa",
            "adicionar modelo",
            "modelo nao existe",
        ),
        (
            Step("Abra a tela de modelos de placa solar.", "panel_models"),
            Step(
                "Escolha a marca. Se ela não existir, peça a marca na tela de solicitações de marca.",
                "brand_requests",
            ),
            Step(
                "Preencha as características técnicas do modelo (potência, eficiência, dimensões e peso)."
            ),
            Step("Salve. O modelo só pode receber ofertas depois de aprovado."),
        ),
        para_quem="fornecedor",
        requisitos=("Empresa fornecedora aprovada.",),
    ),
    Guide(
        "cadastrar_oferta",
        "Cadastrar uma oferta de placa",
        "Publica uma placa à venda com preço e quantidade.",
        (
            "cadastrar oferta",
            "criar oferta",
            "nova oferta",
            "vender placa",
            "anunciar placa",
            "cadastrar placa",
        ),
        (
            Step(
                "Confirme que o modelo da placa já existe e está aprovado. Se não existir, cadastre-o primeiro.",
                "panel_models",
            ),
            Step("Abra a tela de ofertas da sua empresa.", "offers_management"),
            Step(
                "Escolha o modelo, defina o preço unitário e a quantidade disponível."
            ),
            Step(
                "Revise e salve. A oferta nasce ativa e aparece na vitrine de placas.",
                "solar_panels",
            ),
        ),
        para_quem="fornecedor",
        requisitos=("Empresa fornecedora aprovada.", "Modelo de placa aprovado."),
        dicas=(
            "Se preferir, eu cadastro para você: me diga modelo, preço e quantidade e eu peço o seu aceite antes de gravar.",
        ),
        acao_do_assistente="create_offer",
    ),
    Guide(
        "pausar_encerrar_oferta",
        "Pausar, reativar ou encerrar uma oferta",
        "Controla se a oferta aparece para compra.",
        (
            "pausar oferta",
            "reativar oferta",
            "encerrar oferta",
            "suspender oferta",
            "desativar oferta",
            "situacao da oferta",
        ),
        (
            Step("Abra a tela de ofertas da sua empresa.", "offers_management"),
            Step("Localize a oferta e mude a situação: ativa, pausada ou encerrada."),
            Step("Pausar e reativar podem ser feitos quantas vezes quiser."),
            Step("Encerrar é definitivo: uma oferta encerrada não pode ser reaberta."),
        ),
        para_quem="fornecedor",
        acao_do_assistente="set_offer_status",
    ),
    Guide(
        "ajustar_estoque",
        "Ajustar o estoque",
        "Atualiza a quantidade total disponível de um modelo.",
        (
            "ajustar estoque",
            "atualizar estoque",
            "quantidade em estoque",
            "mudar estoque",
            "estoque",
        ),
        (
            Step("Abra a tela de ofertas da sua empresa.", "offers_management"),
            Step(
                "Localize o modelo e informe a nova quantidade total (não a diferença)."
            ),
            Step("Salve."),
        ),
        para_quem="fornecedor",
        acao_do_assistente="set_inventory_quantity",
    ),
    Guide(
        "comprar",
        "Comprar placas",
        "Do carrinho ao pedido pago.",
        (
            "comprar placa",
            "fazer pedido",
            "finalizar compra",
            "adicionar ao carrinho",
            "checkout",
            "como comprar",
        ),
        (
            Step("Escolha a oferta na vitrine de placas.", "solar_panels"),
            Step("Adicione a quantidade desejada ao carrinho.", "cart"),
            Step("Revise itens, valores e taxas no carrinho."),
            Step(
                "Escolha a forma de pagamento e finalize a compra você mesmo: o assistente nunca paga nem finaliza compras."
            ),
            Step("Acompanhe o pedido na tela de pedidos.", "orders"),
        ),
        dicas=(
            "Posso colocar ou tirar itens do seu carrinho, mas a finalização é sempre sua.",
        ),
        acao_do_assistente="update_cart",
    ),
    Guide(
        "acompanhar_pedido",
        "Acompanhar ou cancelar um pedido seu",
        "Mostra o andamento das suas compras e permite cancelar.",
        (
            "acompanhar pedido",
            "meus pedidos",
            "cancelar pedido",
            "status do pedido",
            "minhas compras",
        ),
        (
            Step("Abra a tela de pedidos.", "orders"),
            Step("Selecione o pedido para ver itens, valores e pagamento."),
            Step(
                "Para cancelar, use a opção de cancelamento do pedido. O cancelamento não pode ser desfeito."
            ),
        ),
        acao_do_assistente="cancel_order",
    ),
    Guide(
        "acompanhar_vendas",
        "Acompanhar as vendas da empresa",
        "Lista os pedidos recebidos pela sua empresa.",
        ("minhas vendas", "pedidos recebidos", "acompanhar vendas", "quem comprou"),
        (
            Step("Abra a tela de vendas.", "sales"),
            Step("Veja cada venda com comprador, oferta, quantidade e valor."),
            Step("Para visão geral, use os indicadores.", "analytics"),
        ),
        para_quem="fornecedor",
    ),
    Guide(
        "plano_assinatura",
        "Ver o plano e as cobranças",
        "Mostra o plano da empresa, a situação da assinatura e as cobranças.",
        (
            "plano",
            "assinatura",
            "cobranca",
            "fatura",
            "pagamento do plano",
            "renovacao",
        ),
        (
            Step("Abra a tela do plano.", "plan"),
            Step("Confira o plano, o ciclo, a situação da assinatura e as cobranças."),
            Step("O pagamento das cobranças é feito por você na própria tela."),
        ),
        para_quem="fornecedor",
    ),
    Guide(
        "cadastrar_unidade",
        "Cadastrar uma unidade",
        "Registra locais da empresa e seus dados.",
        (
            "cadastrar unidade",
            "nova unidade",
            "filial",
            "local de instalacao",
            "conta de energia",
        ),
        (
            Step("Abra a tela de unidades.", "units"),
            Step("Crie a unidade e preencha o endereço e os dados pedidos."),
            Step(
                "Se for o caso, informe as contas de energia e as especificações da unidade."
            ),
        ),
    ),
    Guide(
        "criar_projeto",
        "Criar um projeto de instalação",
        "Organiza uma instalação para buscar fornecedores e profissionais.",
        ("criar projeto", "novo projeto", "projeto de instalacao", "cadastrar projeto"),
        (
            Step("Abra a tela de projetos.", "projects"),
            Step("Inicie um novo projeto.", "new_project"),
            Step("Preencha os dados do projeto e salve."),
        ),
    ),
    Guide(
        "cadastrar_profissional",
        "Cadastrar-se como profissional",
        "Envia seus dados e documentos para análise como técnico ou instalador.",
        (
            "cadastrar profissional",
            "virar tecnico",
            "sou instalador",
            "registro profissional",
            "cadastro de tecnico",
        ),
        (
            Step("Abra o cadastro de profissional.", "register_professional"),
            Step(
                "Preencha os dados e anexe os documentos pedidos para a sua profissão."
            ),
            Step("Envie para análise e acompanhe o resultado.", "registration_status"),
        ),
    ),
    Guide(
        "solicitar_marca",
        "Solicitar uma nova marca",
        "Pede a inclusão de uma marca que não está no catálogo.",
        ("solicitar marca", "nova marca", "marca nao existe", "cadastrar marca"),
        (
            Step("Abra a tela de solicitações de marca.", "brand_requests"),
            Step("Crie a solicitação com o nome da marca."),
            Step(
                "Acompanhe a decisão. Aprovada a marca, cadastre o modelo.",
                "panel_models",
            ),
        ),
    ),
    Guide(
        "trocar_senha",
        "Trocar ou recuperar a senha",
        "Altera a senha logado ou recupera o acesso.",
        (
            "trocar senha",
            "alterar senha",
            "esqueci a senha",
            "recuperar senha",
            "redefinir senha",
        ),
        (
            Step("Logado: abra a tela de segurança e troque a senha.", "security"),
            Step(
                "Sem acesso: use a tela de recuperação de senha e siga o link enviado ao seu e-mail.",
                "forgot_password",
            ),
        ),
        dicas=("Nunca digite sua senha aqui no chat.",),
    ),
    Guide(
        "mensagens",
        "Conversar com empresas e profissionais",
        "Troca mensagens dentro da plataforma.",
        (
            "mensagens",
            "conversar com empresa",
            "falar com fornecedor",
            "caixa de entrada",
        ),
        (
            Step("Abra a tela de mensagens.", "messages"),
            Step(
                "Escolha a conversa ou inicie uma a partir do perfil da empresa ou do profissional."
            ),
        ),
    ),
)


def _caminho(tela_id: str, lang: str) -> str | None:
    tela = _TELAS.get(tela_id)
    return tela.path(lang) if tela else None


def _score(guide: Guide, query_stems: set[str]) -> int:
    score = 0
    for keyword in guide.keywords:
        keyword_stems = stems(keyword)
        if keyword_stems and keyword_stems <= query_stems:
            score += 3
    haystack = stems(" ".join([guide.titulo, guide.resumo, *guide.keywords]))
    return score + len(query_stems & haystack)


def render_guide(guide: Guide, lang: str = DEFAULT_LANG) -> dict:
    passos = []
    for numero, passo in enumerate(guide.passos, start=1):
        item = {"n": numero, "passo": passo.texto}
        if passo.tela:
            item["caminho"] = _caminho(passo.tela, lang)
        passos.append(item)
    return {
        "guia": guide.titulo,
        "resumo": guide.resumo,
        "para_quem": guide.para_quem,
        "requisitos": list(guide.requisitos),
        "passos": passos,
        "dicas": list(guide.dicas),
        "o_assistente_pode_fazer": guide.acao_do_assistente is not None,
    }


def find_guides(query: str, lang: str = DEFAULT_LANG, limit: int = 2) -> list[dict]:
    query_stems = stems(query)
    pontuados = [(_score(g, query_stems), g) for g in GUIDES]
    pontuados = [item for item in pontuados if item[0] >= MIN_SCORE]
    pontuados.sort(key=lambda item: (-item[0], item[1].id))
    return [render_guide(guide, lang) for _, guide in pontuados[:limit]]
