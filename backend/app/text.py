import unicodedata


def normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold().strip()
