#!/usr/bin/env python3
"""
Decode a saved Google Maps /maps/vt/proto response (the .bin from curl).

Layout observed in the file (each tile response):

    0a <len>                      field 1 = one tile response
      15 <float32>                field 2 = 3600.0 (meaning unknown)
      1a <len> <BODY>             field 3 = tile payload, every byte XOR 0x9B
      30 00                       field 6
      3a <len> "<content-type>"   field 7 (string)
      40 <varint>                 field 8 (798 here; same number as 28:798 in the request BPB)
      4a <len> "<token>"          field 9 (string, looks like a tile/version token)
      68 00 80 01 01 88 01 01     misc flags

Usage:
    python3 vt_decode.py file.bin              # summary + POI table
    python3 vt_decode.py file.bin --dump 0     # full dump of tile #0
    python3 vt_decode.py file.bin --find-key   # brute-force the XOR key
"""
import math
import struct
import sys
import importlib.util
import os

# reuse the protobuf reader from bpb_decode.py (same folder)
_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("bpb_decode", os.path.join(_here, "bpb_decode.py"))
bd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bd)

KEY = 0x9B


def xor(data: bytes, key: int) -> bytes:
    return bytes(b ^ key for b in data)


def split_tiles(data: bytes):
    """Return list of dicts: header float, raw body, trailer fields."""
    tiles, i = [], 0
    while i < len(data):
        key, j = bd.read_varint(data, i)
        assert key == 0x0A, f"expected field 1 at {i}, got key {key:#x}"
        n, j = bd.read_varint(data, j)
        blob = data[j:j + n]
        i = j + n

        t = {"float": None, "body": b"", "trailer": []}
        k = 0
        while k < len(blob):
            key, k = bd.read_varint(blob, k)
            f, w = key >> 3, key & 7
            if w == 5:
                if f == 2:
                    t["float"] = struct.unpack("<f", blob[k:k + 4])[0]
                k += 4
            elif w == 2:
                n2, k = bd.read_varint(blob, k)
                chunk = blob[k:k + n2]
                k += n2
                if f == 3:
                    t["body"] = chunk
                else:
                    t["trailer"].append((f, chunk))
            elif w == 0:
                v, k = bd.read_varint(blob, k)
                t["trailer"].append((f, v))
            else:
                raise ValueError(f"unexpected wire type {w}")
        tiles.append(t)
    return tiles


def find_key(body: bytes):
    """Try all 256 single-byte keys; keep the ones that give a clean protobuf."""
    hits = []
    for k in range(256):
        try:
            m = bd.parse_message(xor(body, k))
            hits.append((k, len(m)))
        except bd.ParseError:
            pass
    return hits


def tile_to_latlon(z, x, y, fx, fy):
    """fx, fy in 0..1 inside tile (fy measured from top)."""
    n = 2 ** z
    lon = (x + fx) / n * 360 - 180
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + fy) / n))))
    return lat, lon


def get(msg, field):
    return [(k, v) for f, k, v in msg if f == field]


def poi_rows(tile_msg):
    hdr = dict((f, v) for f, k, v in get(tile_msg, 1)[0][1])
    z, x, y = hdr[1], hdr[2], hdr[3]
    rows = []
    for _, group in get(tile_msg, 10):          # field 10 = feature group
        for kind, feat in get(group, 1):         # field 10.1 = one feature
            names = []
            for _, names_msg in get(feat, 2):
                for _, nm in get(names_msg, 1):
                    s = [v for f, k, v in nm if f == 1 and k == "string"]
                    if s:
                        names.append(s[0])
            pos = None
            for _, p in get(feat, 3):
                for _, p1 in get(p, 1):
                    xy = [v for f, k, v in p1 if f == 1 and k == "packed"]
                    if xy and len(xy[0]) == 2:
                        pos = xy[0]
            fid = None
            for _, ext in get(feat, 53863091):
                for _, e20 in get(ext, 20):
                    for _, e1 in get(e20, 1):
                        s = [v for f, k, v in e1 if f == 1 and k == "string"]
                        if s:
                            fid = s[0]
            latlon = None
            if pos:
                latlon = tile_to_latlon(z, x, y, pos[0] / 65536, pos[1] / 65536)
            if names or fid:
                rows.append((" / ".join(names), latlon, fid))
    return (z, x, y), rows


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    data = open(sys.argv[1], "rb").read()
    tiles = split_tiles(data)
    print(f"{len(data)} bytes, {len(tiles)} tile response(s)\n")

    if "--find-key" in sys.argv:
        for n, t in enumerate(tiles):
            print(f"tile #{n}: keys giving a clean parse -> {find_key(t['body'])}")
        return

    msgs = [bd.parse_message(xor(t["body"], KEY)) for t in tiles]

    if "--dump" in sys.argv:
        idx = int(sys.argv[sys.argv.index("--dump") + 1])
        bd.dump(msgs[idx])
        return

    for n, (t, m) in enumerate(zip(tiles, msgs)):
        (z, x, y), rows = poi_rows(m)
        print(f"=== tile #{n}: z{z} x{x} y{y}  (body {len(t['body'])} B, float header {t['float']})")
        for f, v in t["trailer"]:
            if isinstance(v, bytes):
                v = v.decode("ascii", "replace")
            print(f"  trailer {f}: {v}")
        for name, ll, fid in rows:
            loc = f"{ll[0]:.5f}, {ll[1]:.5f}" if ll else "-"
            print(f"  {name or '(no name)':<34} {loc:<22} {fid or ''}")
        print()


if __name__ == "__main__":
    main()
