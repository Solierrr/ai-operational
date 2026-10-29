import re
import unicodedata

INJECTION_PATTERNS = [
    r"ignore(?:\s+todas)?\s+as\s+instru[cç][oõ]es",
    r"esque[cç]a\s+(?:as\s+)?instru[cç][oõ]es",
    r"you\s+are\s+now",
    r"ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions",
    r"\[inst\]",
    r"modo\s+(?:irrestrito|desenvolvedor|admin)",
    r"revele\s+(?:seu|o)\s+prompt",
    r"aja\s+como\s+se\s+voc[eê]\s+n[aã]o\s+tivesse\s+regras",
    r"(?:ignor\w+|desconsider\w+|descart\w+|esquec\w+)\s+(?:tudo|todas?|toda|as|os|suas?|seus?)?\s*(?:que\s+)?(?:foi\s+dito|acima|anterior\w*|regras|diretrizes|prompt)",
    r"(?:novas?|outras?)\s+instru[cç][oõ]es\s*:",
    r"a\s+partir\s+de\s+agora\s+(?:voc[eê]|tu)\s+(?:[eé]|ser[aá]|vai\s+ser|age|atua)",
    r"(?:finja|fingir)\s+(?:que\s+)?(?:ser|voc[eê]|[eé])",
    r"fa[cç]a\s+de\s+conta\s+que",
    r"pretend\s+(?:to\s+be|you\s+are|that)",
    r"act\s+as\s+(?:if|an?|the)\b",
    r"disregard\s+(?:all|the|your|any|previous)",
    r"forget\s+(?:all|everything|your|previous|the\s+above)",
    r"override\s+(?:your|the|all)\s+(?:rules|instructions|guidelines|safety)",
    r"developer\s+mode",
    r"jailbreak",
    r"do\s+anything\s+now",
    r"(?:mostre|exiba|imprima|repita|vaze|diga|liste|revele)\s+(?:para\s+mim\s+)?(?:(?:o|a|as|os)\s+)?(?:(?:suas?|seus?)\s+)?(?:system\s+)?(?:prompt|instru[cç][oõ]es\s+(?:internas|iniciais|do\s+sistema)|regras\s+internas)",
    r"(?:repeat|reveal|print|show|leak|output)\s+(?:the\s+|your\s+)?(?:system\s+|initial\s+|hidden\s+)?(?:prompt|instructions)",
    r"<\s*\|?\s*(?:im_start|im_end|system|assistant|endoftext)\s*\|?\s*>",
    r"<\s*/?\s*(?:system|instructions?|developer)\s*>",
    r"<<\s*/?sys\s*>>",
    r"\[/?sys(?:tem)?\]",
    r"(?:^|\n)\s*#{1,4}\s*(?:system|instru[cç][oõ]es?\s+do\s+sistema|new\s+instructions)",
    r"(?:^|\n)\s*(?:system|assistant|developer|sistema)\s*:",
    r"sem\s+(?:pedir|precisar\s+de|exigir)\s+(?:a\s+)?(?:minha\s+)?(?:confirma[cç][aã]o|permiss[aã]o|aceite|autoriza[cç][aã]o|aprova[cç][aã]o)",
    r"sem\s+(?:a\s+)?minha\s+(?:confirma[cç][aã]o|permiss[aã]o|aprova[cç][aã]o|autoriza[cç][aã]o)",
    r"n[aã]o\s+(?:pe[cç]a|pergunte|precisa\s+pedir)\s+(?:a\s+)?(?:confirma[cç][aã]o|permiss[aã]o|aceite|autoriza[cç][aã]o)",
    r"(?:skip|bypass|disable|without)\s+(?:the\s+)?(?:confirmation|approval|asking|permission)",
    r"considere\s+(?:que\s+)?(?:eu\s+)?(?:j[aá]\s+)?(?:aceitei|confirmei|autorizei|aprovei)",
    r"(?:j[aá]\s+)?(?:aceitei|confirmei|autorizei)\s+(?:tudo|antecipadamente|previamente)",
    r"(?:a\s+)?confirma[cç][aã]o\s+j[aá]\s+foi\s+dada",
    r"(?:decodifique|decifre|decode|decrypt)\b.{0,40}\b(?:execute|obede[cç]a|siga|run|follow)",
]

INTERNAL_DATA_KEYWORDS = [
    "system_core",
    "prompt do sistema",
    "system prompt",
    "arquitetura interna",
    "credenciais",
    "chave de api",
    "api key",
    "código-fonte",
    "codigo fonte",
    "codigo-fonte",
    "service_key",
    "service key",
    "variáveis de ambiente",
    "variaveis de ambiente",
    "environment variables",
    "string de conexao",
    "connection string",
]

_LEET = str.maketrans(
    {"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"}
)
_CATEGORIAS_INVISIVEIS = {"Cf", "Cc", "Mn"}


def _sem_invisiveis(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(
        char
        for char in decomposed
        if unicodedata.category(char) not in _CATEGORIAS_INVISIVEIS or char in "\n\t"
    )


_LETRAS_ESPACADAS = re.compile(r"(?:\b\w ){5,}\w\b")
_PADROES_COMPACTOS = [
    re.sub(r"\\s[+*]", r"\\s*", pattern)
    for pattern in INJECTION_PATTERNS
    if "\\n" not in pattern and "^" not in pattern
]


def _base(text: str) -> str:
    base = _sem_invisiveis(unicodedata.normalize("NFKC", text)).lower()
    return re.sub(r"[ \t]+", " ", base)


def detection_variants(text: str) -> list[str]:
    base = _base(text)
    sem_separadores = re.sub(r"(?<=\w)[\-_.*·•](?=\w)", "", base)
    separadores_em_espaco = re.sub(r"(?<=\w)[\-_.*·•]+(?=\w)", " ", base)
    espacado = re.sub(r"\b(?:\w )+\w\b", lambda m: m.group(0).replace(" ", ""), base)
    variantes: list[str] = []
    for variante in (
        base,
        sem_separadores,
        separadores_em_espaco,
        espacado,
        base.translate(_LEET),
    ):
        if variante not in variantes:
            variantes.append(variante)
    return variantes


def matches_injection_pattern(text: str) -> bool:
    if any(
        re.search(pattern, variante)
        for variante in detection_variants(text)
        for pattern in INJECTION_PATTERNS
    ):
        return True
    base = _base(text)
    if _LETRAS_ESPACADAS.search(base):
        compacto = re.sub(r"\s+", "", base)
        return any(re.search(pattern, compacto) for pattern in _PADROES_COMPACTOS)
    return False


def matches_internal_data_keyword(text: str) -> bool:
    lowered = text.lower()
    if any(keyword in lowered for keyword in INTERNAL_DATA_KEYWORDS):
        return True
    return any(
        keyword in variante
        for variante in detection_variants(text)
        for keyword in INTERNAL_DATA_KEYWORDS
    )
