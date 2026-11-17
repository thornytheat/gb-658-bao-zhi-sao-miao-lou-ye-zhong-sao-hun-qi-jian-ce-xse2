def hamming_distance(left: str, right: str) -> int:
    if len(left) != len(right) or not left:
        raise ValueError("BAD_HASH")
    try:
        return (int(left, 16) ^ int(right, 16)).bit_count()
    except ValueError as exc:
        raise ValueError("BAD_HASH") from exc

def is_candidate(left: str, right: str, threshold: int = 3) -> bool:
    return hamming_distance(left, right) <= threshold

def same_digest(left: dict, right: dict) -> bool:
    return bool(left.get("sha256")) and left.get("sha256") == right.get("sha256")

