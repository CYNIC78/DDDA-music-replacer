"""Small per-user settings store; never part of a project or game files."""
from __future__ import annotations
import json, os
from pathlib import Path

def settings_path():
    base = os.environ.get("APPDATA")
    if base: return Path(base) / "DDDA_Music_Replacer" / "settings.json"
    return Path.home() / ".ddda_music_replacer" / "settings.json"

def load():
    p = settings_path()
    try: return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError): return {}

def save(data):
    p = settings_path(); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def existing_dir(value, fallback=None):
    if value:
        p=Path(value)
        if p.is_dir(): return str(p)
        if p.parent.is_dir(): return str(p.parent)
    return fallback or str(Path.home())
