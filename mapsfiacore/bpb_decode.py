#!/usr/bin/env python3
"""
Decode the `bpb` parameter of Google Maps /maps/vt/proto URLs.

Usage:
    python3 bpb_decode.py "<bpb value or full URL>"
    echo "<bpb value or full URL>" | python3 bpb_decode.py

Heuristics (no schema is available, so these are best guesses):
  - length-delimited bytes that are all printable ASCII  -> string
  - otherwise, if they parse cleanly as a protobuf       -> nested message
  - otherwise, if they parse cleanly as varints          -> packed varints
  - otherwise                                            -> raw hex
"""
import base64
import math
import sys
from urllib.parse import urlparse, parse_qs, unquote


# ---------- input handling ----------

def extract_bpb(text: str) -> str:
    text = "".join(text.split())              # drop newlines / spaces from wrapped paste
    if text.startswith("http"):
        qs = parse_qs(urlparse(text).query)
        if "bpb" not in qs:
            sys.exit("No bpb parameter found in that URL.")
        text = qs["bpb"][0]
    text = unquote(text)
    if text.lower().startswith("bpb="):
        text = text[4:]
    return text


def b64_decode(s: str) -> bytes:
    s = s.rstrip("=")
    s += "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s)


# ---------- low-level protobuf reading ----------

class ParseError(Exception):
    pass


def read_varint(b: bytes, i: int):
    v = shift = 0
    while True:
        if i >= len(b) or shift > 63:
            raise ParseError("bad varint")
        c = b[i]
        i += 1
        v |= (c & 0x7F) << shift
        shift += 7
        if c < 0x80:
            return v, i


def is_printable(d: bytes) -> bool:
    return len(d) > 0 and all(32 <= c < 127 for c in d)


def parse_message(b: bytes, depth: int = 0):
    """Strict parse. Returns list of (field, kind, value). Raises ParseError."""
    out, i = [], 0
    while i < len(b):
        key, i = read_varint(b, i)
        field, wire = key >> 3, key & 7
        if field == 0 or field >= (1 << 29):
            raise ParseError("bad field number")
        if wire == 0:
            v, i = read_varint(b, i)
            out.append((field, "varint", v))
        elif wire == 1:
            if i + 8 > len(b):
                raise ParseError("truncated fixed64")
            out.append((field, "fixed64", b[i:i + 8]))
            i += 8
        elif wire == 5:
            if i + 4 > len(b):
                raise ParseError("truncated fixed32")
            out.append((field, "fixed32", b[i:i + 4]))
            i += 4
        elif wire == 2:
            n, i = read_varint(b, i)
            if i + n > len(b):
                raise ParseError("truncated bytes")
            out.append((field, *classify(b[i:i + n], depth)))
            i += n
        else:
            raise ParseError("bad wire type")
    return out


def classify(d: bytes, depth: int):
    if len(d) == 0:
        return ("empty", None)
    if is_printable(d):
        return ("string", d.decode("ascii"))
    if depth < 12:
        try:
            return ("message", parse_message(d, depth + 1))
        except ParseError:
            pass
    try:
        vals, i = [], 0
        while i < len(d):
            v, i = read_varint(d, i)
            vals.append(v)
        return ("packed", vals)
    except ParseError:
        return ("hex", d.hex())


# ---------- pretty printing ----------

def dump(msg, indent=0):
    pad = "  " * indent
    for field, kind, val in msg:
        if kind == "varint":
            print(f"{pad}{field}: {val}")
        elif kind == "string":
            print(f'{pad}{field}: "{val}"')
        elif kind == "empty":
            print(f"{pad}{field}: (empty)")
        elif kind == "message":
            print(f"{pad}{field} {{")
            dump(val, indent + 1)
            print(f"{pad}}}")
        elif kind == "packed":
            print(f"{pad}{field}: packed varints {val}")
        elif kind in ("fixed32", "fixed64"):
            print(f"{pad}{field}: {kind} 0x{val[::-1].hex()}")
        else:
            print(f"{pad}{field}: hex {val}")


# ---------- tile summary ----------

def tile_nw(z, x, y):
    n = 2 ** z
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    lon = x / n * 360 - 180
    return lat, lon


def tiles(msg):
    """Find top-level `1 { 1 { 1:z 2:x 3:y } }` entries."""
    found = []
    for field, kind, val in msg:
        if field == 1 and kind == "message":
            for f2, k2, v2 in val:
                if f2 == 1 and k2 == "message":
                    d = {f: v for f, k, v in v2 if k == "varint"}
                    if {1, 2, 3} <= d.keys():
                        found.append((d[1], d[2], d[3]))
    return found


def summarize_tiles(msg):
    ts = tiles(msg)
    if not ts:
        return
    zs = sorted({t[0] for t in ts})
    print("\n=== Tile summary ===")
    for z in zs:
        sel = [t for t in ts if t[0] == z]
        xs = [t[1] for t in sel]
        ys = [t[2] for t in sel]
        nw = tile_nw(z, min(xs), min(ys))
        se = tile_nw(z, max(xs) + 1, max(ys) + 1)
        print(f"zoom {z}: {len(sel)} tile(s), x {min(xs)}-{max(xs)}, y {min(ys)}-{max(ys)}")
        print(f"  NW corner: lat {nw[0]:.4f}, lon {nw[1]:.4f}")
        print(f"  SE corner: lat {se[0]:.4f}, lon {se[1]:.4f}")


def collect_strings(msg, acc=None):
    acc = [] if acc is None else acc
    for _, kind, val in msg:
        if kind == "string":
            acc.append(val)
        elif kind == "message":
            collect_strings(val, acc)
    return acc


def main():
    raw = sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read()
    data = b64_decode(extract_bpb(raw))
    msg = parse_message(data)
    dump(msg)
    summarize_tiles(msg)
    strs = collect_strings(msg)
    if strs:
        print("\n=== Strings found ===")
        print(", ".join(strs))


if __name__ == "__main__":
    main()