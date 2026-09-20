#!/usr/bin/env python3
"""Music Replacer MVP: patch one extracted STRQ/STQ file.

The MVP deliberately does not repack ARC. It patches the extracted STQ so the
user can put it back into title.arc manually while ARC handling is validated.
"""
from __future__ import annotations
import argparse, hashlib, json, struct, sys
from pathlib import Path

MAGIC = b"STRQ"
VERSION = 0x1B
ENTRY_OFF = 0x3C
ENTRY_SIZE = 24
U32_MAX = 0xFFFFFFFF
HZ_DEFAULT = 48000

def u32(buf, off): return struct.unpack_from("<I", buf, off)[0]
def put_u32(buf, off, val): struct.pack_into("<I", buf, off, val & U32_MAX)

def parse_ogg(path: Path):
    data = path.read_bytes()
    if not data:
        raise ValueError("audio file is empty")
    pos = 0
    pages = 0
    channels = rate = None
    last_granule = None
    while pos + 27 <= len(data):
        if data[pos:pos+4] != b"OggS":
            raise ValueError(f"not an Ogg page at byte {pos}")
        segs = data[pos+26]
        end = pos + 27 + segs
        if end > len(data): raise ValueError("truncated Ogg segment table")
        sizes = data[pos+27:end]
        body_len = sum(sizes)
        body_end = end + body_len
        if body_end > len(data): raise ValueError("truncated Ogg page")
        granule = struct.unpack_from("<q", data, pos+6)[0]
        if granule >= 0: last_granule = granule
        body = data[end:body_end]
        # Vorbis identification packet: \x01vorbis, then version, channels, rate.
        if channels is None:
            i = body.find(b"\x01vorbis")
            if i >= 0 and i + 16 <= len(body):
                channels = body[i+11]
                rate = struct.unpack_from("<I", body, i+12)[0]
        pages += 1
        pos = body_end
    if pos != len(data):
        raise ValueError("trailing non-Ogg data")
    if channels is None or rate is None:
        raise ValueError("Vorbis identification header not found")
    if last_granule is None or last_granule <= 0:
        raise ValueError("Ogg has no usable final granule/sample count")
    return {"size": len(data), "samples": int(last_granule),
            "channels": int(channels), "rate": int(rate), "pages": pages}

def read_stq(path: Path):
    data = bytearray(path.read_bytes())
    if data[:4] != MAGIC: raise ValueError("not STRQ/STQ: missing STRQ magic")
    version, count = struct.unpack_from("<II", data, 4)
    if version != VERSION:
        raise ValueError(f"unsupported STRQ version {version}; expected {VERSION}")
    if ENTRY_OFF + count * ENTRY_SIZE > len(data): raise ValueError("main table exceeds file")
    rows = []
    for i in range(count):
        off = ENTRY_OFF + i * ENTRY_SIZE
        name_off, size, samples, ch, lin, lout = struct.unpack_from("<6I", data, off)
        if name_off >= len(data): raise ValueError(f"record {i}: name offset outside file")
        end = data.find(b"\0", name_off)
        if end < 0: raise ValueError(f"record {i}: unterminated name")
        try: name = bytes(data[name_off:end]).decode("ascii")
        except UnicodeDecodeError: name = bytes(data[name_off:end]).decode("ascii", "replace")
        rows.append({"index": i, "entry_off": off, "name_off": name_off,
                     "name": name, "size": size, "samples": samples, "channels": ch,
                     "loop_in": None if lin == U32_MAX else lin,
                     "loop_out": None if lout == U32_MAX else lout})
    return data, rows

def append_name(data: bytearray, target: str):
    raw = target.encode("ascii") + b"\0"
    off = len(data)
    data.extend(raw)
    return off

def patch(args):
    stq = Path(args.stq)
    audio = Path(args.audio)
    data, rows = read_stq(stq)
    matches = [r for r in rows if r["name"].lower() == args.source.lower()]
    if len(matches) != 1:
        names = "\n".join(f"  [{r['index']}] {r['name']}" for r in rows)
        raise ValueError(f"expected exactly one source match, got {len(matches)}:\n{names}")
    r = matches[0]
    meta = parse_ogg(audio)
    if meta["channels"] != r["channels"]:
        raise ValueError(f"channels mismatch: original {r['channels']}, replacement {meta['channels']}")
    if args.rate is not None and meta["rate"] != args.rate:
        raise ValueError(f"sample rate mismatch: replacement {meta['rate']}, required {args.rate}")
    # MVP policy: original/title rate is expected to be 48000 unless overridden.
    expected_rate = args.rate if args.rate is not None else HZ_DEFAULT
    if meta["rate"] != expected_rate:
        raise ValueError(f"sample rate {meta['rate']} Hz is not {expected_rate} Hz")
    if args.loop == "none":
        lin = lout = U32_MAX
    else:
        lin, lout = 0, meta["samples"]
    if args.loop_in is not None: lin = args.loop_in
    if args.loop_out is not None: lout = args.loop_out
    if (lin == U32_MAX) != (lout == U32_MAX): raise ValueError("loop-in and loop-out must be both set or both omitted")
    if lin != U32_MAX and not (0 <= lin < lout <= meta["samples"]):
        raise ValueError(f"invalid loop range {lin}..{lout} for {meta['samples']} samples")
    target = args.target
    if target.lower().endswith(".sngw") or target.lower().endswith(".ogg"):
        target = target.rsplit(".", 1)[0]
    try: target.encode("ascii")
    except UnicodeEncodeError: raise ValueError("target STQ path must be ASCII")
    new_name_off = append_name(data, target)
    eo = r["entry_off"]
    old = {"name": r["name"], "name_off": r["name_off"], "size": r["size"],
           "samples": r["samples"], "channels": r["channels"],
           "loop_in": r["loop_in"], "loop_out": r["loop_out"]}
    put_u32(data, eo + 0x00, new_name_off)
    put_u32(data, eo + 0x04, meta["size"])
    put_u32(data, eo + 0x08, meta["samples"])
    put_u32(data, eo + 0x10, lin)
    put_u32(data, eo + 0x14, lout)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    result = {"source_stq": str(stq), "output_stq": str(out), "audio": str(audio),
              "source_track": old["name"], "target_name": target, "original": old,
              "replacement": meta, "new_loop_in": None if lin == U32_MAX else lin,
              "new_loop_out": None if lout == U32_MAX else lout,
              "original_sha256": hashlib.sha256(stq.read_bytes()).hexdigest(),
              "output_sha256": hashlib.sha256(data).hexdigest(),
              "warning": "MVP patches extracted STQ only; insert it into title.arc manually."}
    report = out.with_suffix(out.suffix + ".report.json")
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))

def main():
    ap = argparse.ArgumentParser(description="Patch one extracted Dragon's Dogma STRQ/STQ record")
    ap.add_argument("stq", help="extracted STQ, e.g. Tittle_bgm.stq")
    ap.add_argument("audio", help="replacement OGG/Vorbis or SNGW")
    ap.add_argument("--source", default=r"bgm\wave2\Tittle_DDN")
    ap.add_argument("--target", default=r"DDDA_AI_Overhaul\music\title\tittleddn_a")
    ap.add_argument("--out", required=True, help="patched extracted STQ")
    ap.add_argument("--loop", choices=("full", "none"), default="full")
    ap.add_argument("--loop-in", type=int)
    ap.add_argument("--loop-out", type=int)
    ap.add_argument("--rate", type=int, help="required sample rate (default 48000)")
    args = ap.parse_args()
    try: patch(args)
    except (OSError, ValueError, struct.error) as e:
        print(f"ERROR: {e}", file=sys.stderr); return 2
    return 0
if __name__ == "__main__": raise SystemExit(main())
