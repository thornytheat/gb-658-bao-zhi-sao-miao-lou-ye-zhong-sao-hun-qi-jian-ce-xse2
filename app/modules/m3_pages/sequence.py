from collections import Counter

def inspect_pages(values: list[str], expected_count: int) -> dict:
    numbers = [int(value) for value in values]
    counts = Counter(numbers)
    expected = set(range(1, expected_count + 1))
    present = set(numbers)
    return {"missing": sorted(expected - present), "duplicates": sorted(n for n, count in counts.items() if count > 1), "unexpected": sorted(present - expected)}

def select_versions(rows: list[dict]) -> list[dict]:
    selected = {}
    for row in rows:
        page = row["page"]
        score = (int(row.get("version", 0)), int(row.get("clarity", 0)), str(row.get("file_name", "")))
        current = selected.get(page)
        if current is None or score > current[0]:
            selected[page] = (score, row)
    return [selected[key][1] for key in sorted(selected, key=int)]

