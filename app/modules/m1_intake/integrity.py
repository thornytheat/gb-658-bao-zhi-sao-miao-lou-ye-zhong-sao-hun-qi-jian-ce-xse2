import re

HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")

def valid_sha256(value: str) -> bool:
    return bool(HEX64.fullmatch(value or ""))

def complete_tail(text: str) -> bool:
    return not text or text.endswith("\n")

def stable_file_key(row: dict) -> str:
    return "{}|{}|{}|{}".format(row.get("issue", ""), row.get("edition", ""), row.get("page", ""), row.get("file_name", ""))

