import re
import unicodedata


def normalize(text: str) -> str:
    """Minúsculas, sem acentos e só com letras, números e espaços."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9 ]+", " ", plain)
