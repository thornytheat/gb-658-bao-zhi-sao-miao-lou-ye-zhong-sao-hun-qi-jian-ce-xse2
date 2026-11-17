from .parser import parse_manifest
from .integrity import complete_tail

SAMPLE = "issue,edition,page,file_name,sha256,phash,clarity,header_issue\n2026-11-01,01,001,a.tif,aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa,0f0f,92,2026-11-01\n2026-11-01,01,004,b.tif,bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb,f0f0,81,2026-11-01\n"

def run(text: str = SAMPLE) -> dict:
    rows, quarantine = parse_manifest(text)
    return {"input": len(rows) + len(quarantine), "accepted": len(rows), "quarantined": len(quarantine), "tail_complete": complete_tail(text), "evidence": quarantine}

def demo():
    return run()

