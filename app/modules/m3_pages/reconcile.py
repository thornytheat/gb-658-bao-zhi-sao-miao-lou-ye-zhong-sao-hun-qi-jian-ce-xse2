def page_accounts(input_count: int, selected: list[dict], status: dict) -> dict:
    accepted = len(selected)
    superseded = input_count - accepted
    complete = not status["missing"] and not status["unexpected"]
    return {"input": input_count, "accepted": accepted, "superseded": superseded, "complete": complete, "balanced": input_count == accepted + superseded}

def coverage(selected: list[dict], expected_count: int) -> str:
    if expected_count <= 0:
        return "0.000"
    return f"{len(selected) / expected_count:.3f}"

