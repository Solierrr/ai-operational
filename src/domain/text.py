import re
import unicodedata


def normalize(text: str) -> str:
    """Minúsculas, sem acentos e só com letras, números e espaços."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9 ]+", " ", plain)


STOPWORDS = frozenset(
    [
        "onde",
        "como",
        "quero",
        "para",
        "uma",
        "uns",
        "umas",
        "meu",
        "minha",
        "meus",
        "minhas",
        "que",
        "com",
        "dos",
        "das",
        "por",
        "fazer",
        "ver",
        "tela",
        "telas",
        "pagina",
        "paginas",
        "achar",
        "acho",
        "encontrar",
        "preciso",
        "posso",
        "qual",
        "quais",
        "aonde",
        "fica",
        "ficam",
        "esta",
        "estao",
        "nao",
        "sei",
        "gostaria",
        "queria",
        "mostrar",
        "abrir",
        "ir",
        "levar",
    ]
)


def stems(text: str) -> set[str]:
    """Radicais de 4 letras das palavras relevantes (cadastro, cadastrar -> cada)."""
    return {
        token[:4]
        for token in normalize(text).split()
        if len(token) > 2 and token not in STOPWORDS
    }
