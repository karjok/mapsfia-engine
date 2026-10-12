#!/usr/bin/env python3
"""
Decode & encode parameter pb Google Maps.

DECODE
  python pbtool.py decode '!4m9!1m3!1d19275.6!2d106.83!3d-6.17...' -i 1
  python pbtool.py decode --url 'https://www.google.com/maps/...?pb=!4m9...'
  python pbtool.py decode --file pb.txt --tree      # tree lossless (untuk encode ulang)
  python pbtool.py decode --file pb.txt --wrap      # [[["hspqX","<json>",null,"generic"]]]

ENCODE
  python pbtool.py encode --file tree.json          # tree -> pb (round-trip persis)
  python pbtool.py encode --file list.json --plain  # nested list biasa -> pb (best effort)
  python pbtool.py decode --file pb.txt --tree | python pbtool.py encode
"""
import argparse
import json
import re
import sys
from urllib.parse import unquote, urlparse, parse_qs

TOKEN_RE = re.compile(r"^(\d+)([a-zA-Z])(.*)$", re.S)
INT_TYPES = set("iujexynt")
FLOAT_TYPES = set("dfg")
STR_TYPES = set("sBzaho r".replace(" ", ""))


# ---------------------------------------------------------------- escape
def unescape(s: str) -> str:
    return re.sub(r"\*(21|2[Aa])", lambda m: "!" if m.group(1) == "21" else "*", s)


def escape(s: str) -> str:
    return s.replace("*", "*2A").replace("!", "*21")


# ---------------------------------------------------------------- decode
def extract_pb(text: str) -> str:
    text = text.strip()
    if text.startswith("http"):
        qs = parse_qs(urlparse(text).query)
        if "pb" in qs:
            return qs["pb"][0]
        m = re.search(r"[?&]pb=([^&#]+)", text)
        if m:
            return unquote(m.group(1))
        raise ValueError("Parameter pb tidak ditemukan di URL")
    if text.startswith("pb="):
        text = text[3:]
    return unquote(text) if "%" in text else text


def tokenize(pb: str):
    parts = pb.split("!")
    if parts and parts[0] == "":
        parts = parts[1:]
    out = []
    for p in parts:
        m = TOKEN_RE.match(p)
        if not m:
            raise ValueError(f"Token tidak valid: {p!r}")
        f, t, v = m.groups()
        out.append((int(f), t, v))
    return out


def convert(typ, val):
    if typ in INT_TYPES or typ == "b":
        return int(val)
    if typ in FLOAT_TYPES:
        return float(val)
    return unescape(val)


def parse_tree(tokens, pos, count):
    """Return (list of [field, type, value], pos). Lossless: urutan & tipe terjaga."""
    nodes, end = [], pos + count
    while pos < end:
        f, t, v = tokens[pos]
        pos += 1
        if t == "m":
            sub, pos = parse_tree(tokens, pos, int(v))
            nodes.append([f, "m", sub])
        else:
            nodes.append([f, t, convert(t, v)])
    return nodes, pos


def decode_tree(pb: str):
    tokens = tokenize(pb)
    tree, _ = parse_tree(tokens, 0, len(tokens))
    return tree


def tree_to_list(nodes):
    """Tree -> nested list (indeks = field-1, field berulang -> list)."""
    grouped = {}
    for f, t, v in nodes:
        val = tree_to_list(v) if t == "m" else v
        grouped.setdefault(f, []).append(val)
    if not grouped:
        return []
    out = [None] * max(grouped)
    for f, vals in grouped.items():
        out[f - 1] = vals[0] if len(vals) == 1 else vals
    return out


def tree_to_dict(nodes):
    grouped = {}
    for f, t, v in nodes:
        val = tree_to_dict(v) if t == "m" else v
        grouped.setdefault(f, []).append(val)
    return {str(k): (v[0] if len(v) == 1 else v) for k, v in sorted(grouped.items())}


# ---------------------------------------------------------------- encode
def fmt_value(typ, val) -> str:
    if typ == "b":
        return "1" if val else "0"
    if typ in INT_TYPES:
        return str(int(val))
    if typ in FLOAT_TYPES:
        return repr(float(val))
    return escape(str(val))


def encode_tree(nodes):
    """Tree [[field,type,value],...] -> list token (tanpa '!' depan)."""
    toks = []
    for f, t, v in nodes:
        if t == "m":
            sub = encode_tree(v)
            toks.append(f"{f}m{len(sub)}")
            toks.extend(sub)
        else:
            toks.append(f"{f}{t}{fmt_value(t, v)}")
    return toks


def tree_to_pb(nodes) -> str:
    return "".join("!" + t for t in encode_tree(nodes))


def plain_to_tree(data):
    """
    Nested list biasa -> tree (best effort, tipe ditebak):
      None -> dilewati | bool -> b | int -> i | float -> d | str -> s
      list -> message (indeks+1 = nomor field)
    Batasan: field berulang tidak bisa dibedakan dari message bertingkat,
    dan b/e/i tidak bisa dibedakan dari int. Pakai --tree untuk round-trip persis.
    """
    nodes = []
    for idx, v in enumerate(data, start=1):
        if v is None:
            continue
        if isinstance(v, bool):
            nodes.append([idx, "b", v])
        elif isinstance(v, int):
            nodes.append([idx, "i", v])
        elif isinstance(v, float):
            nodes.append([idx, "d", v])
        elif isinstance(v, str):
            nodes.append([idx, "s", v])
        elif isinstance(v, list):
            nodes.append([idx, "m", plain_to_tree(v)])
        else:
            raise ValueError(f"Tipe tidak didukung: {type(v).__name__}")
    return nodes


def looks_like_tree(data) -> bool:
    return (
        isinstance(data, list)
        and all(
            isinstance(n, list) and len(n) == 3
            and isinstance(n[0], int) and isinstance(n[1], str) and len(n[1]) == 1
            for n in data
        )
    )


def encode(data, force_plain=False) -> str:
    if not force_plain and looks_like_tree(data):
        return tree_to_pb(data)
    return tree_to_pb(plain_to_tree(data))


# ---------------------------------------------------------------- CLI
def read_input(args):
    if getattr(args, "file", None):
        return open(args.file, encoding="utf-8").read()
    if getattr(args, "url", None):
        return args.url
    if getattr(args, "text", None):
        return args.text
    return sys.stdin.read()


def dump(obj, indent):
    return json.dumps(obj, indent=indent, ensure_ascii=False,
                      separators=None if indent else (",", ":"))


def main():
    ap = argparse.ArgumentParser(description="Decode/encode Google Maps pb")
    sub = ap.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("decode", help="pb -> nested list / tree / dict")
    d.add_argument("text", nargs="?", help="String pb atau URL")
    d.add_argument("-f", "--file")
    d.add_argument("-u", "--url")
    d.add_argument("-t", "--tree", action="store_true", help="Output tree lossless")
    d.add_argument("-d", "--dict", action="store_true", help="Output dict {field: nilai}")
    d.add_argument("-w", "--wrap", action="store_true", help='Bungkus [[["rpc","<json>",null,"generic"]]]')
    d.add_argument("-r", "--rpc", default="hspqX")
    d.add_argument("-i", "--indent", type=int)

    e = sub.add_parser("encode", help="tree / nested list (JSON) -> pb")
    e.add_argument("text", nargs="?", help="String JSON")
    e.add_argument("-f", "--file")
    e.add_argument("-p", "--plain", action="store_true", help="Paksa anggap nested list biasa")
    e.add_argument("--url-encode", action="store_true", help="Output di-URL-encode")

    args = ap.parse_args()
    try:
        if args.cmd == "decode":
            tree = decode_tree(extract_pb(read_input(args)))
            if args.tree:
                data = tree
            elif args.dict:
                data = tree_to_dict(tree)
            else:
                data = tree_to_list(tree)
            if args.wrap:
                data = [[[args.rpc, json.dumps(data, separators=(",", ":"), ensure_ascii=False),
                          None, "generic"]]]
            print(dump(data, args.indent))
        else:
            raw = json.loads(read_input(args))
            # dukung input terbungkus [[["rpc","<json>",null,"generic"]]]
            if (isinstance(raw, list) and raw and isinstance(raw[0], list) and raw[0]
                    and isinstance(raw[0][0], list) and len(raw[0][0]) == 4
                    and raw[0][0][3] == "generic" and isinstance(raw[0][0][1], str)):
                raw = json.loads(raw[0][0][1])
            pb = encode(raw, force_plain=args.plain)
            if args.url_encode:
                from urllib.parse import quote
                pb = quote(pb, safe="")
            print(pb)
    except Exception as ex:
        sys.exit(f"Error: {ex}")


if __name__ == "__main__":
    main()