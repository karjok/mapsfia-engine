#!/usr/bin/env python3

import re
import json
import sys
from urllib.parse import urlparse, parse_qs, unquote_plus


TOKEN_RE = re.compile(
    r'!(?P<field>\d+)(?P<type>[a-zA-Z]+)(?P<value>[^!]*)'
)


def convert_value(typ: str, value: str):
    """
    Convert PB scalar values into normal Python values.

    s  -> string
    i  -> integer
    u  -> integer
    d  -> float
    f  -> float
    b  -> boolean
    e  -> integer/enum
    all other types remain strings.

    Empty scalar values become None.
    """

    if value == "":
        return None

    if typ in ("i", "u", "e"):
        try:
            return int(value)
        except ValueError:
            return value

    if typ in ("d", "f"):
        try:
            return float(value)
        except ValueError:
            return value

    if typ == "b":
        if value in ("1", "true", "True"):
            return True
        if value in ("0", "false", "False"):
            return False

    return value


def extract_pb(value: str) -> str:
    """
    Accept:
      - Full Google Maps URL
      - pb parameter
      - URL encoded pb
    """

    value = value.strip()

    if "://" in value:
        parsed = urlparse(value)
        params = parse_qs(parsed.query)

        if "pb" not in params:
            raise ValueError("Parameter 'pb' tidak ditemukan di URL")

        return params["pb"][0]

    if value.startswith("pb="):
        value = value[3:]

    value = unquote_plus(value)

    pos = value.find("!")
    if pos == -1:
        raise ValueError("Input bukan pb yang valid")

    return value[pos:]


def tokenize(pb: str):
    """
    Convert PB string into token tuples:

        (field, type, value)
    """

    matches = list(TOKEN_RE.finditer(pb))

    if not matches:
        raise ValueError("Tidak ada token pb ditemukan")

    return [
        (
            int(match.group("field")),
            match.group("type"),
            match.group("value"),
        )
        for match in matches
    ]


def parse_tokens(tokens, index=0, count=None):
    """
    Parse PB tokens recursively.

    Type 'm' is a container. Its numeric value specifies
    how many immediate child tokens belong to that container.

    Output is a pure nested list. Token metadata such as
    field/type/count is discarded.
    """

    result = []
    consumed = 0

    while index < len(tokens):

        if count is not None and consumed >= count:
            break

        field, typ, value = tokens[index]

        if typ == "m":
            try:
                child_count = int(value)
            except ValueError:
                child_count = 0

            children, next_index = parse_tokens(
                tokens,
                index + 1,
                child_count,
            )

            result.append(children)
            index = next_index

        else:
            result.append(convert_value(typ, value))
            index += 1

        consumed += 1

    return result, index


def decode_pb(pb_input: str):
    pb = extract_pb(pb_input)
    tokens = tokenize(pb)

    nested, _ = parse_tokens(tokens)

    return nested


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print(f"  {sys.argv[0]} '<pb string>'")
        print(f"  {sys.argv[0]} '<google maps URL>'")
        sys.exit(1)

    input_data = sys.argv[1]

    try:
        decoded = decode_pb(input_data)

        print(
            json.dumps(
                decoded,
                indent=2,
                ensure_ascii=False,
                allow_nan=False,
            )
        )

    except Exception as e:
        print(f"[!] Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
