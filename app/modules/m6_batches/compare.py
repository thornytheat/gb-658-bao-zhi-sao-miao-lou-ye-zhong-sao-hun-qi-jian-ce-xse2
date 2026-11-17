def reconcile(input_count: int, accepted: int, rescans: int, mixed: int, quarantined: int) -> dict:
    parts = accepted + rescans + mixed + quarantined
    return {"input": input_count, "accepted": accepted, "rescans": rescans, "mixed": mixed, "quarantined": quarantined, "balanced": input_count == parts, "difference": input_count - parts}

def reason_distribution(rows: list[dict]) -> dict[str, int]:
    result = {}
    for row in rows:
        code = row["reason_code"]
        result[code] = result.get(code, 0) + 1
    return result

