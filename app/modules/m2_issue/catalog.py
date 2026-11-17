def business_key(item: dict) -> str:
    return "|".join((item["issue"], item["edition"], item["page"]))

def is_supplement(edition: str) -> bool:
    return edition.upper().startswith("S")

def split_key(key: str) -> tuple[str, str, str]:
    parts = key.split("|")
    if len(parts) != 3:
        raise ValueError("BAD_KEY")
    return tuple(parts)

