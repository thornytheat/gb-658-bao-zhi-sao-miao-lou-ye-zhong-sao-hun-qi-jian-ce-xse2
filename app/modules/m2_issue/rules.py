from datetime import datetime
import re

def normalize_issue(value: str) -> str:
    value = value.strip().replace("/", "-")
    return datetime.strptime(value, "%Y-%m-%d").date().isoformat()

def normalize_edition(value: str) -> str:
    token = value.strip().upper()
    if token.startswith("S"):
        return token
    if not token.isdigit() or int(token) < 1:
        raise ValueError("BAD_EDITION")
    return f"{int(token):02d}"

def normalize_page(value: str) -> str:
    token = value.strip()
    if not re.fullmatch(r"\d+", token) or int(token) < 1:
        raise ValueError("BAD_PAGE")
    return f"{int(token):03d}"

def expected_pages(count: int) -> list[str]:
    if count < 1:
        raise ValueError("BAD_COUNT")
    return [f"{n:03d}" for n in range(1, count + 1)]

