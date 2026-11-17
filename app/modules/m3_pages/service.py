from .sequence import inspect_pages, select_versions
from .reconcile import page_accounts

def run(pages: list[dict] | None = None) -> dict:
    pages = pages or [{"page": "001", "version": 1, "clarity": 80}, {"page": "002", "version": 1, "clarity": 70}, {"page": "002", "version": 2, "clarity": 90}, {"page": "004", "version": 1, "clarity": 88}]
    selected = select_versions(pages)
    status = inspect_pages([x["page"] for x in selected], 4)
    return {**status, **page_accounts(len(pages), selected, status)}

def demo():
    return run()

