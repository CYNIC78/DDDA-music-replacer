"""STQ-only snapshots and patch ledger support."""
from __future__ import annotations
import hashlib, json, shutil
from datetime import datetime
from pathlib import Path

def sha256(path: Path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def create_snapshot(stq: Path, root: Path, archive_name: str, metadata=None):
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    dest = Path(root) / stamp / archive_name.replace(".arc", "")
    dest.mkdir(parents=True, exist_ok=True)
    copy = dest / Path(stq).name
    shutil.copy2(stq, copy)
    manifest = {"kind": "stq_snapshot", "archive": archive_name,
                "created_at": stamp, "file": copy.name,
                "size": copy.stat().st_size, "sha256": sha256(copy),
                "metadata": metadata or {}}
    (dest / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return dest, manifest

def verify_snapshot(snapshot_dir: Path):
    manifest = json.loads((Path(snapshot_dir) / "manifest.json").read_text(encoding="utf-8"))
    path = Path(snapshot_dir) / manifest["file"]
    return path.is_file() and path.stat().st_size == manifest["size"] and sha256(path) == manifest["sha256"]
