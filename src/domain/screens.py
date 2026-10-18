"""Registro das telas do web-app, para o agente achar e indicar onde fica cada uma.

Espelha `src/config/i18n/paths.ts` e `src/config/i18n/locales/*/routes.json` do
`web-app`: cada tela é uma sequência de chaves de segmento, traduzida por idioma. Se
uma rota nova nascer no web-app, acrescente-a aqui (`SCREENS`) e, se ela usar um
segmento novo, em `ROUTE_SEGMENTS`.
"""

from dataclasses import dataclass

from src.domain.text import normalize

DEFAULT_LANG = "pt-BR"

ROUTE_SEGMENTS: dict[str, dict[str, str]] = {
    "pt-BR": {
        "brands": "marcas",
        "solarPanels": "placas-solares",
        "professionals": "profissionais",
        "companies": "empresas",
        "search": "buscar",
        "solarPanel": "placa-solar",
        "company": "empresa",
        "professional": "profissional",
        "about": "sobre",
        "designSystem": "design-system",
        "login": "login",
        "register": "cadastro",
        "forgotPassword": "esqueci-senha",
        "verifyEmail": "verificar-email",
        "profileSetup": "personalizar-perfil",
        "user": "usuario",
        "admin": "admin",
        "supplier": "fornecedor",
        "demandant": "demandante",
        "solarPanelModels": "modelos-de-placa-solar",
        "messages": "mensagens",
        "chatbot": "chatbot",
        "settings": "configuracoes",
        "security": "seguranca",
        "access": "acesso",
        "dashboard": "painel",
        "employees": "funcionarios",
        "offers": "ofertas",
        "units": "unidades",
        "registrations": "cadastros",
        "resetPassword": "redefinir-senha",
        "privacy": "privacidade",
        "sessions": "sessoes",
        "registrationStatus": "status-cadastro",
        "analytics": "indicadores",
        "policy": "politicas",
        "terms": "termos",
        "cookies": "cookies",
        "brandRequests": "solicitacoes",
        "projects": "projetos",
        "newProject": "novo",
        "editProject": "editar",
        "infrastructure": "infraestrutura",
        "cart": "carrinho",
        "orders": "pedidos",
        "sales": "vendas",
        "plan": "plano",
    },
    "en-US": {
        "brands": "brands",
        "solarPanels": "solar-panels",
        "professionals": "professionals",
        "companies": "companies",
        "search": "search",
        "solarPanel": "solar-panel",
        "company": "company",
        "professional": "professional",
        "about": "about",
        "designSystem": "design-system",
        "login": "login",
        "register": "register",
        "forgotPassword": "forgot-password",
        "verifyEmail": "verify-email",
        "profileSetup": "profile-setup",
        "user": "user",
        "admin": "admin",
        "supplier": "supplier",
        "demandant": "demandant",
        "solarPanelModels": "solar-panel-models",
        "messages": "messages",
        "chatbot": "chatbot",
        "settings": "settings",
        "security": "security",
        "access": "access",
        "dashboard": "dashboard",
        "employees": "employees",
        "offers": "offers",
        "units": "units",
        "registrations": "registrations",
        "resetPassword": "reset-password",
        "privacy": "privacy",
        "sessions": "sessions",
        "registrationStatus": "registration-status",
        "analytics": "analytics",
        "policy": "policies",
        "terms": "terms",
        "cookies": "cookies",
        "brandRequests": "requests",
        "projects": "projects",
        "newProject": "new",
        "editProject": "edit",
        "infrastructure": "infrastructure",
        "cart": "cart",
        "orders": "orders",
        "sales": "sales",
        "plan": "plan",
    },
    "es-ES": {
        "brands": "marcas",
        "solarPanels": "paneles-solares",
        "professionals": "profesionales",
        "companies": "empresas",
        "search": "buscar",
        "solarPanel": "panel-solar",
        "company": "empresa",
        "professional": "profesional",
        "about": "acerca-de",
        "designSystem": "sistema-de-diseno",
        "login": "iniciar-sesion",
        "register": "registro",
        "forgotPassword": "olvide-mi-contrasena",
        "verifyEmail": "verificar-correo",
        "profileSetup": "personalizar-perfil",
        "user": "usuario",
        "admin": "admin",
        "supplier": "proveedor",
        "demandant": "demandante",
        "solarPanelModels": "modelos-de-panel-solar",
        "messages": "mensajes",
        "chatbot": "chatbot",
        "settings": "configuracion",
        "security": "seguridad",
        "access": "acceso",
        "dashboard": "panel",
        "employees": "empleados",
        "offers": "ofertas",
        "units": "unidades",
        "registrations": "registros",
        "resetPassword": "restablecer-contrasena",
        "privacy": "privacidad",
        "sessions": "sesiones",
        "registrationStatus": "estado-registro",
        "analytics": "indicadores",
        "policy": "politicas",
        "terms": "terminos",
        "cookies": "cookies",
        "brandRequests": "solicitudes",
        "projects": "proyectos",
        "newProject": "nuevo",
        "editProject": "editar",
        "infrastructure": "infraestructura",
        "cart": "carrito",
        "orders": "pedidos",
        "sales": "ventas",
        "plan": "plan",
    },
}


@dataclass(frozen=True)
class Screen:
    id: str
    title: str
    description: str
    segments: tuple[str, ...]
    keywords: tuple[str, ...]
    audience: str = "qualquer usuário autenticado"

    def path(self, lang: str = DEFAULT_LANG) -> str:
        table = ROUTE_SEGMENTS.get(lang, ROUTE_SEGMENTS[DEFAULT_LANG])
        lang = lang if lang in ROUTE_SEGMENTS else DEFAULT_LANG
        parts = [table[segment] for segment in self.segments]
        return "/" + "/".join([lang, *parts])


SCREENS: tuple[Screen, ...] = (
    Screen(
        "home",
        "Página inicial",
        "Início da plataforma.",
        (),
        ("inicio", "home", "principal"),
    ),
    Screen(
        "solar_panels",
        "Placas solares",
        "Vitrine com as ofertas de placas solares.",
        ("solarPanels",),
        ("placas", "paineis", "ofertas de placas", "catalogo de placas"),
    ),
    Screen(
        "infrastructure",
        "Infraestrutura",
        "Vitrine de itens de fixação e infraestrutura.",
        ("infrastructure",),
        ("infraestrutura", "fixacao", "estrutura", "trilho", "suporte"),
    ),
    Screen(
        "professionals",
        "Profissionais",
        "Vitrine de profissionais cadastrados.",
        ("professionals",),
        ("profissionais", "tecnicos", "instaladores", "engenheiros"),
    ),
    Screen(
        "companies",
        "Empresas",
        "Vitrine de empresas fornecedoras.",
        ("companies",),
        ("empresas", "fornecedores", "fornecedoras"),
    ),
    Screen(
        "search_panels",
        "Buscar placas solares",
        "Busca de placas solares.",
        ("search", "solarPanels"),
        ("buscar placas", "pesquisar placas", "procurar placa"),
    ),
    Screen(
        "search_professionals",
        "Buscar profissionais",
        "Busca de profissionais.",
        ("search", "professionals"),
        ("buscar profissionais", "procurar tecnico", "procurar instalador"),
    ),
    Screen(
        "search_companies",
        "Buscar empresas",
        "Busca de empresas.",
        ("search", "companies"),
        ("buscar empresas", "procurar fornecedor"),
    ),
    Screen(
        "login",
        "Entrar",
        "Login na plataforma.",
        ("login",),
        ("login", "entrar", "acessar conta"),
    ),
    Screen(
        "register",
        "Criar conta",
        "Cadastro de uma nova conta.",
        ("register",),
        ("criar conta", "cadastro", "registrar usuario"),
    ),
    Screen(
        "register_company",
        "Cadastrar empresa",
        "Formulário para cadastrar a sua empresa (CNPJ, endereço e contato).",
        ("register", "company"),
        (
            "cadastrar empresa",
            "registrar empresa",
            "criar empresa",
            "nova empresa",
            "cnpj",
        ),
    ),
    Screen(
        "register_professional",
        "Cadastrar como profissional",
        "Cadastro de profissional (registro, conselho e documentos).",
        ("register", "professional"),
        (
            "cadastrar profissional",
            "virar tecnico",
            "registro profissional",
            "sou instalador",
        ),
    ),
    Screen(
        "activate_access",
        "Ativar código de acesso",
        "Resgate de um código de acesso para entrar em uma empresa.",
        ("register", "access"),
        ("codigo de acesso", "ativar acesso", "convite da empresa"),
    ),
    Screen(
        "forgot_password",
        "Esqueci minha senha",
        "Recuperação de senha.",
        ("forgotPassword",),
        ("esqueci a senha", "recuperar senha", "redefinir senha"),
    ),
    Screen(
        "own_company",
        "Perfil da minha empresa",
        "Dados e perfil público da sua empresa.",
        ("company",),
        ("minha empresa", "perfil da empresa", "dados da empresa"),
    ),
    Screen(
        "own_profile",
        "Meu perfil",
        "Seus dados pessoais.",
        ("user",),
        ("meu perfil", "meus dados", "minha conta", "foto de perfil"),
    ),
    Screen(
        "dashboard",
        "Painel",
        "Painel operacional com o resumo da sua atuação.",
        ("dashboard",),
        ("painel", "dashboard", "resumo"),
    ),
    Screen(
        "operational_chatbot",
        "Assistente operacional",
        "Chat do assistente operacional dentro do painel.",
        ("dashboard", "chatbot"),
        ("assistente operacional", "chat operacional"),
    ),
    Screen(
        "chatbot",
        "Assistente de IA",
        "Chat do assistente que recomenda produtos, profissionais e empresas.",
        ("chatbot",),
        ("assistente", "chatbot", "recomendar", "ia"),
    ),
    Screen(
        "supplier_dashboard",
        "Painel do fornecedor",
        "Visão do fornecedor.",
        ("supplier",),
        ("painel do fornecedor", "area do fornecedor"),
        "fornecedor",
    ),
    Screen(
        "demandant_dashboard",
        "Painel do demandante",
        "Visão do demandante.",
        ("demandant",),
        ("painel do demandante", "area do demandante"),
        "demandante",
    ),
    Screen(
        "admin_dashboard",
        "Painel administrativo",
        "Administração da plataforma.",
        ("admin",),
        ("administracao", "painel admin"),
        "administrador",
    ),
    Screen(
        "offers_management",
        "Gerenciar ofertas",
        "Cadastro, edição e controle das ofertas de placas da sua empresa.",
        ("admin", "offers"),
        (
            "ofertas",
            "cadastrar placa",
            "criar oferta",
            "nova oferta",
            "cadastrar oferta",
            "minhas ofertas",
            "preco da placa",
            "estoque",
        ),
        "fornecedor",
    ),
    Screen(
        "panel_models",
        "Modelos de placa solar",
        "Catálogo de modelos de placa (marca, potência, eficiência, dimensões).",
        ("admin", "solarPanelModels"),
        ("modelos de placa", "cadastrar modelo", "novo modelo", "modelo de placa"),
        "fornecedor",
    ),
    Screen(
        "brand_requests",
        "Solicitações de marca",
        "Pedidos de novas marcas ao catálogo.",
        ("brandRequests",),
        ("marca", "solicitar marca", "nova marca", "cadastrar marca"),
    ),
    Screen(
        "brands",
        "Marcas",
        "Marcas do catálogo.",
        ("brands",),
        ("marcas", "lista de marcas"),
    ),
    Screen(
        "employees",
        "Funcionários",
        "Equipe da empresa, cargos e permissões.",
        ("admin", "employees"),
        ("funcionarios", "equipe", "cargos", "permissoes", "membros"),
        "administrador da empresa",
    ),
    Screen(
        "units",
        "Unidades",
        "Unidades e locais da empresa.",
        ("admin", "units"),
        ("unidades", "locais", "filiais", "endereco da unidade"),
    ),
    Screen(
        "registrations",
        "Cadastros em análise",
        "Aprovação de cadastros de empresas e profissionais.",
        ("admin", "registrations"),
        ("aprovar cadastro", "cadastros pendentes", "analise de cadastro"),
        "administrador",
    ),
    Screen(
        "registration_status",
        "Status do cadastro",
        "Andamento da análise do seu cadastro.",
        ("registrationStatus",),
        ("status do cadastro", "meu cadastro foi aprovado", "analise do cadastro"),
    ),
    Screen(
        "analytics",
        "Indicadores",
        "Indicadores e gráficos da sua operação.",
        ("analytics",),
        ("indicadores", "graficos", "metricas", "analytics"),
    ),
    Screen(
        "plan",
        "Plano",
        "Plano de assinatura e cobranças.",
        ("admin", "plan"),
        ("plano", "assinatura", "cobranca", "pagamento do plano"),
        "fornecedor",
    ),
    Screen(
        "sales",
        "Vendas",
        "Pedidos recebidos pela sua empresa.",
        ("admin", "sales"),
        ("vendas", "pedidos recebidos"),
        "fornecedor",
    ),
    Screen(
        "orders",
        "Meus pedidos",
        "Pedidos feitos por você.",
        ("orders",),
        ("pedidos", "minhas compras", "compras"),
    ),
    Screen(
        "cart",
        "Carrinho",
        "Itens que você pretende comprar.",
        ("cart",),
        ("carrinho", "finalizar compra", "checkout"),
    ),
    Screen(
        "projects",
        "Projetos",
        "Seus projetos de instalação.",
        ("projects",),
        ("projetos", "meus projetos", "instalacoes"),
    ),
    Screen(
        "new_project",
        "Novo projeto",
        "Criar um projeto de instalação.",
        ("projects", "newProject"),
        ("novo projeto", "criar projeto", "cadastrar projeto"),
    ),
    Screen(
        "messages",
        "Mensagens",
        "Conversas com empresas e profissionais.",
        ("messages",),
        ("mensagens", "conversas", "chat com empresa", "caixa de entrada"),
    ),
    Screen(
        "settings",
        "Configurações",
        "Preferências da conta.",
        ("settings",),
        ("configuracoes", "preferencias", "idioma"),
    ),
    Screen(
        "security",
        "Segurança",
        "Senha e proteção da conta.",
        ("settings", "security"),
        ("seguranca", "trocar senha", "alterar senha", "autenticacao"),
    ),
    Screen(
        "sessions",
        "Sessões",
        "Dispositivos conectados à sua conta.",
        ("settings", "sessions"),
        ("sessoes", "dispositivos", "sair de outros aparelhos"),
    ),
    Screen(
        "privacy",
        "Privacidade",
        "Dados e privacidade da conta.",
        ("settings", "privacy"),
        ("privacidade", "meus dados", "excluir conta"),
    ),
    Screen(
        "terms",
        "Termos de uso",
        "Termos de uso da plataforma.",
        ("policy", "terms"),
        ("termos de uso", "termos"),
    ),
    Screen(
        "privacy_policy",
        "Política de privacidade",
        "Política de privacidade da plataforma.",
        ("policy", "privacy"),
        ("politica de privacidade",),
    ),
    Screen("about", "Sobre", "Sobre a Solaria.", ("about",), ("sobre", "quem somos")),
)


_STOPWORDS = frozenset(
    ["onde", "como", "quero", "para", "uma", "uns", "umas", "meu", "minha", "meus", "minhas", "que", "com", "dos", "das", "por", "fazer", "ver", "tela", "telas", "pagina", "paginas", "achar", "acho", "encontrar", "preciso", "posso", "qual", "quais", "aonde", "fica", "ficam", "esta", "estao", "nao", "sei", "gostaria", "queria", "mostrar", "abrir", "ir", "levar"]
)


def _stems(text: str) -> set[str]:
    """Radicais de 4 letras das palavras relevantes (cadastro, cadastrar -> cada)."""
    return {
        token[:4]
        for token in normalize(text).split()
        if len(token) > 2 and token not in _STOPWORDS
    }


def find_screens(query: str, lang: str = DEFAULT_LANG, limit: int = 3) -> list[dict]:
    """Telas que melhor respondem a `query`, da mais para a menos provável.

    Compara radicais de palavras. Uma palavra-chave composta cujos radicais estão
    todos na consulta vale 3 pontos; cada radical em comum com o título, a descrição
    ou as palavras-chave vale 1."""
    query_stems = _stems(query)
    scored: list[tuple[int, Screen]] = []
    for screen in SCREENS:
        score = 0
        for keyword in screen.keywords:
            keyword_stems = _stems(keyword)
            if keyword_stems and keyword_stems <= query_stems:
                score += 3
        haystack = _stems(
            " ".join([screen.title, screen.description, *screen.keywords])
        )
        score += len(query_stems & haystack)
        if score:
            scored.append((score, screen))
    scored.sort(key=lambda item: (-item[0], item[1].id))
    return [
        {
            "tela": screen.title,
            "descricao": screen.description,
            "caminho": screen.path(lang),
            "para_quem": screen.audience,
        }
        for _, screen in scored[:limit]
    ]
