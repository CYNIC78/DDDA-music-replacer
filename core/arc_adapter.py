"""ARC discovery/adapter primitives for Music Replacer.

The actual ARC format remains delegated to ARCtool.exe. This module owns the
safe policy around it: locate known game archives, use a temporary workspace,
and identify the expected STQ after extraction.
"""
from __future__ import annotations
import subprocess
from pathlib import Path
from typing import Optional

ARC_FLAGS = ("-xfs", "-dd", "-texRE6", "-alwayscomp", "-pc", "-txt", "-v", "7")
ARCHIVES = {
    "title.arc": {
        "stq_name": "Tittle_bgm.stq",
        "expected_counts": (2,),
        "relative_stq": Path("title/sound/stream/bgm/Tittle_bgm.stq"),
    },
    "bbs_rpg.arc": {
        "stq_name": "bgm.stq",
        "expected_counts": (125,),
        "relative_stq": Path("bbs_rpg/sound/bgm/bgm.stq"),
    },
}

class ArcError(RuntimeError):
    pass

def discover_game_root(root: Path):
    root = Path(root)
    rom = root / "nativePC" / "rom"
    stream = root / "nativePC" / "sound" / "stream"
    if not root.is_dir(): raise ArcError("game root is not a directory")
    if not rom.is_dir(): raise ArcError("nativePC/rom was not found")
    return {"root": root, "rom": rom, "stream": stream,
            "title": rom / "title.arc", "bbs_rpg": rom / "bbs_rpg.arc"}

def find_arctool(explicit: Optional[str] = None, beside: Optional[Path] = None):
    candidates = []
    if explicit: candidates.append(Path(explicit))
    if beside: candidates.append(Path(beside) / "ARCtool.exe")
    candidates.append(Path(__file__).resolve().parent / "ARCtool.exe")
    for p in candidates:
        if p.is_file(): return p.resolve()
    raise ArcError("ARCtool.exe was not found; choose its location first")

def unpack(arc: Path, work_dir: Path, arctool: Path):
    arc = Path(arc).resolve(); work_dir = Path(work_dir).resolve(); work_dir.mkdir(parents=True, exist_ok=True)
    if not arc.is_file(): raise ArcError(f"archive not found: {arc}")
    # ARCtool writes its extracted result beside the input. We copy the input
    # into an isolated workspace so the user's archive is never modified.
    isolated = work_dir / arc.name
    isolated.write_bytes(arc.read_bytes())
    proc = subprocess.run([str(arctool), *ARC_FLAGS, str(isolated)], cwd=str(work_dir), capture_output=True, text=True)
    if proc.returncode != 0: raise ArcError(f"ARCtool unpack failed ({proc.returncode}): {proc.stderr[-1000:]}")
    return work_dir

def pack(extracted_root: Path, work_dir: Path, arctool: Path):
    extracted_root = Path(extracted_root).resolve(); work_dir = Path(work_dir).resolve()
    if not extracted_root.is_dir(): raise ArcError(f"extracted ARC folder not found: {extracted_root}")
    before = {p.resolve() for p in work_dir.glob("*.arc")}
    proc = subprocess.run([str(arctool), *ARC_FLAGS, str(extracted_root)], cwd=str(work_dir), capture_output=True, text=True)
    if proc.returncode != 0: raise ArcError(f"ARCtool pack failed ({proc.returncode}): {proc.stderr[-1000:]}")
    expected = work_dir / (extracted_root.name + ".arc")
    if expected.is_file(): return expected
    candidates = [p for p in work_dir.glob("*.arc") if p.resolve() not in before]
    if len(candidates) == 1: return candidates[0]
    if not candidates: raise ArcError("ARCtool reported success but produced no .arc")
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]

def locate_stq(extracted_root: Path, archive_name: str):
    info = ARCHIVES.get(archive_name)
    if not info: raise ArcError(f"unsupported archive kind: {archive_name}")
    expected = Path(extracted_root) / info["relative_stq"]
    if expected.is_file(): return expected
    matches = list(Path(extracted_root).rglob(info["stq_name"]))
    if len(matches) == 1: return matches[0]
    if not matches: raise ArcError(f"{info['stq_name']} was not found after unpack")
    raise ArcError(f"multiple {info['stq_name']} files found; archive identity is ambiguous")

def inspect_stq(stq: Path, archive_name: str):
    # Imported lazily so the adapter stays usable as a small standalone module.
    from patch_stq import read_stq
    _, rows = read_stq(Path(stq))
    expected = ARCHIVES[archive_name]["expected_counts"]
    warning = None if len(rows) in expected else f"expected slot count {expected}, found {len(rows)}"
    return {"path": str(stq), "count": len(rows), "rows": rows, "warning": warning}
