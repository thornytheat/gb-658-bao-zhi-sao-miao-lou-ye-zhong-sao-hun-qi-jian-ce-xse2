from app.manifest import build_manifest
from app.store import record_run
from .compare import reconcile

def run(payload: bytes = b"scanfolio-sample") -> dict:
    account = reconcile(input_count=12, accepted=8, rescans=2, mixed=1, quarantined=1)
    manifest = build_manifest(payload, accepted=8, quarantined=1)
    manifest["created"] = record_run(manifest)
    return {**manifest, **account}

def demo():
    return run()

