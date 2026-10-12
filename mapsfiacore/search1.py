"""Place search and Google Maps response parsing.

``Search`` owns the tolerant JSON/protobuf-ish parser that turns raw Google
Maps responses into :class:`mapsfiacore.models.Place` objects, plus ``search`` /
``asearch`` for running a text query. The parsing helpers are shared with
:class:`~mapsfiacore.suggestions.Suggestions` via the ``parser`` attribute on
:class:`~mapsfiacore.mapsfia.MapsFia`.
"""
from __future__ import annotations

import json
import math
import random
import re
import string
import time
from datetime import datetime, timezone
from typing import Any, Callable, Iterator, Optional, Sequence, Union

from mapsfiacore.base import HttpSpec, MapsFiaBase, MapsFiaConfig, run_sync
from mapsfiacore.models.models import Photo, Place, RelatedPlace

URL = "https://www.google.com"
FID_RE = re.compile(r"^0x[0-9a-f]+:0x[0-9a-f]+$")
PLACE_ID_RE = re.compile(r"^(?:ChIJ|GhIJ)[\w-]{10,}$")
KGMID_RE = re.compile(r"^/[gm]/[\w]+$")
TZ_RE = re.compile(r"^[A-Z][A-Za-z_]+/[A-Za-z_]+(?:/[A-Za-z_]+)?$")
POSTAL_RE = re.compile(r"^\d{4,6}$")
COUNTRY_RE = re.compile(r"^[A-Z]{2}$")
_OLC = "23456789CFGHJMPQRVWX"
_COUNTRY_NAMES = {"Indonesia": "ID", "Malaysia": "MY", "Singapore": "SG", "India": "IN"}
_REVIEWS_LABEL_RE = re.compile(r"^[\d.,]+\s?[KkMm]?\s+reviews?$")
PLUS_RE = re.compile(rf"^([{_OLC}]{{2,8}}\+[{_OLC}]{{2,3}})(?=[\s,]|$)")
PHONE_RE = re.compile(r"^\+?[\d][\d\s\-().]{6,22}$")
GOOGLE_HOST_RE = re.compile(
    r"https?://[^/]*(google|gstatic|googleusercontent|ggpht|googleapis|youtube)\.", re.I
)
# In the known layout the feature id sits at index 10 of a place record. Every other
# "core" field is read at (usual_index + anchor - 10) so a shift of the whole record
# (extra leading elements) does not break anything.
_FID_INDEX = 10
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
MEDIA_LABELS = ("Photo", "Video", "Street View")
XSSI_RE = re.compile(r"^\s*\)\s*\]\s*\}\s*'?\s*")  # tolerates ")]}'" split over lines
TYPE_KIND = {
    445: "country",
    446: "state/province",
    444: "city/town",
    429: "district",
    426: "place",
    384: "village",
    72:  "poi",
}


class Search(MapsFiaBase):
    """Search Google Maps and parse responses into :class:`mapsfiacore.models.Place` lists."""

    name = "Search"

    def __init__(self, config: Optional[MapsFiaConfig] = None, parent: Optional[MapsFiaBase] = None,
                 logger: Any = None, **config_overrides: Any):
        super().__init__(config=config, parent=parent, logger=logger, **config_overrides)
        self.maps_session = "".join(random.choices(string.ascii_letters + string.digits, k=26))

    # ================================================================ parsing
    def _decode_json_text(self, text: str) -> Any:
        text = XSSI_RE.sub("", text, count=1)
        starts = [i for i in (text.find("["), text.find("{")) if i >= 0]
        if not starts:
            raise ValueError("No JSON payload found in response")
        obj, _ = json.JSONDecoder().raw_decode(text[min(starts):])
        return obj

    def _load_response(self, raw: Union[str, bytes, list, dict]) -> Any:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", "replace")
        obj = raw if isinstance(raw, (list, dict)) else self._decode_json_text(raw)
        if isinstance(obj, dict) and isinstance(obj.get("d"), str):
            obj = self._decode_json_text(obj["d"])
        return obj

    def _walk(self, node: Any, path: tuple = ()) -> Iterator[tuple[tuple, Any]]:
        yield path, node
        if isinstance(node, list):
            for i, child in enumerate(node):
                yield from self._walk(child, path + (i,))
        elif isinstance(node, dict):
            for k, child in node.items():
                yield from self._walk(child, path + (k,))

    def _anchor(self, rec: Any) -> int:
        if isinstance(rec, list):
            for i, c in enumerate(rec):
                if isinstance(c, str) and FID_RE.match(c):
                    return i - _FID_INDEX
        return 0

    def _has_fid(self, node: Any) -> bool:
        return bool(
            isinstance(node, list)
            and any(
                isinstance(c, str) and FID_RE.match(c) and not c.startswith("0x0:")
                for c in node
            )
        )

    def _is_photo_node(self, n: Any) -> bool:
        return (
            isinstance(n, list)
            and len(n) >= 9
            and isinstance(n[0], str)
            and isinstance(self._dig(n, 6, 0), str)
            and self._dig(n, 6, 0).startswith("http")
            and bool(re.search(r"googleusercontent|streetviewpixels|ggpht", self._dig(n, 6, 0)))
        )

    def _find_place_record(self, root: Any) -> Optional[list]:
        best: Optional[list] = None
        for _, node in self._walk(root):
            if self._has_fid(node) and (best is None or len(node) > len(best)):
                best = node
        return best

    def _is_place_record(self, rec: Any) -> bool:
        """A record list for a real, fully specified place: feature id + place id."""
        return bool(
            isinstance(rec, list)
            and self._has_fid(rec)
            and any(isinstance(c, str) and PLACE_ID_RE.match(c) for c in rec)
        )

    def _is_num(self, x: Any) -> bool:
        return isinstance(x, (int, float)) and not isinstance(x, bool)

    def _find_place_wrappers(self, root: Any) -> list[list]:
        out: list[list] = []
        for _, node in self._walk(root):
            if not isinstance(node, list) or not node or node[0] is not None:
                continue
            for child in node:
                if self._is_place_record(child):
                    out.append(child)
        return out

    def _locate_records(self, root: Any) -> list[list]:
        records = self._find_place_wrappers(root)
        if not records:
            # Last resort: any fully specified record anywhere in the tree.
            records = [node for _, node in self._walk(root) if self._is_place_record(node)]
        if records:
            seen: set = set()
            uniq: list[list] = []
            for rec in records:
                fid = next((c for c in rec if isinstance(c, str) and FID_RE.match(c)), None)
                key = fid if fid else id(rec)
                if key in seen:
                    continue
                seen.add(key)
                uniq.append(rec)
            return uniq
        rec = self._find_place_record(root)
        return [rec] if rec else []

    def _dig(self, node: Any, *path: Any, default: Any = None) -> Any:
        for key in path:
            try:
                node = node[key]
            except (IndexError, KeyError, TypeError):
                return default
            if node is None:
                return default
        return node

    def _first(self, *getters: Callable[[], Any]) -> Any:
        for g in getters:
            try:
                v = g()
            except Exception:
                v = None
            if v not in (None, "", [], {}):
                return v
        return None

    def _at(self, rec: Any, anchor: int, idx: int, *sub: Any) -> Any:
        return self._dig(rec, idx + anchor, *sub)

    @staticmethod
    def _clean(s: str) -> str:
        return s.replace("\u202f", " ").replace("\u00a0", " ").strip()

    def _strs(self, x: Any) -> list[str]:
        return [s for s in x if isinstance(s, str)] if isinstance(x, list) else []

    def _full_address(self, strings: Sequence[str]) -> Optional[str]:
        best: Optional[str] = None
        for s in strings:
            if len(s) >= 20 and s.count(",") >= 3 and re.search(r"\d{4,6}$", s):
                best = s if best is None or len(s) > len(best) else best
        return best

    def _iter_strings(self, node: Any) -> Iterator[str]:
        for _, v in self._walk(node):
            if isinstance(v, str):
                yield v

    def _find_response_meta(self, root: Any) -> dict:
        """[ '<13-digit ms timestamp>', [[ 'Asia/Jakarta', [abbr, long, ...], offset_min, ...]] ]."""
        for _, n in self._walk(root):
            if isinstance(n, list) and len(n) >= 2 and isinstance(n[0], str) and re.fullmatch(r"\d{13}", n[0]):
                tz = self._dig(n, 1, 0)
                if isinstance(tz, list) and isinstance(tz[0], str) and TZ_RE.match(tz[0]):
                    ts = datetime.fromtimestamp(int(n[0]) / 1000, tz=timezone.utc).isoformat()
                    return {"timezone": tz[0], "tz_abbr": self._dig(tz, 1, 0),
                            "utc_offset_minutes": tz[2] if isinstance(self._dig(tz, 2), int) else None,
                            "fetched_at": ts}
        tz = next((s for s in self._iter_strings(root) if TZ_RE.match(s)), None)
        # some layouts carry only a one-element list: ["<13-digit ms timestamp>"]
        ts = next((datetime.fromtimestamp(int(n[0]) / 1000, tz=timezone.utc).isoformat()
                   for _, n in self._walk(root)
                   if isinstance(n, list) and len(n) == 1 and isinstance(n[0], str)
                   and re.fullmatch(r"\d{13}", n[0])), None)
        out: dict = {}
        if tz:
            out["timezone"] = tz
        if ts:
            out["fetched_at"] = ts
        return out

    def _parse_places(self, raw: Union[str, bytes, list, dict]) -> list[Place]:
        root = self._load_response(raw)
        records = self._locate_records(root)
        if not records:
            return []
        meta = self._find_response_meta(root)
        return [self._place_from_record(rec, meta) for rec in records]

    # ------------------------------------------------------------- photos
    def _find_date(self, node: Any) -> Optional[str]:
        """Best-effort capture/upload date: the first YYYY-MM-DD looking string."""
        for _, v in self._walk(node):
            if isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
                return v
        return None

    def _find_streams(self, photo_node: Any) -> list[dict]:
        """Best-effort video stream descriptors from a photo node."""
        streams: list[dict] = []
        for _, n in self._walk(photo_node):
            if (isinstance(n, list) and len(n) >= 3 and isinstance(n[0], str)
                    and n[0].startswith("http") and isinstance(n[1], (int, float))
                    and isinstance(n[2], (int, float))):
                streams.append({"url": n[0], "width": n[1], "height": n[2]})
        seen: set = set()
        out: list[dict] = []
        for s in streams:
            if s["url"] in seen:
                continue
            seen.add(s["url"])
            out.append(s)
        return out

    def _parse_photos(self, root: Any) -> list[Photo]:
        seen: dict[str, Photo] = {}
        for _, n in self._walk(root):
            if not self._is_photo_node(n) or n[0] in seen:
                continue
            url = n[6][0]
            label = next((x for x in n[10:] if isinstance(x, str) and x in MEDIA_LABELS), None)
            if label is None:
                label = "Street View" if "streetviewpixels" in url else "Photo"
            size = self._first(lambda: self._dig(n, 8, 2), lambda: self._dig(n, 6, 2)) or [None, None]
            w, h = (size + [None, None])[:2] if isinstance(size, list) else (None, None)
            lng = self._dig(n, 8, 0, 1)   # NB: photo geo block is [type, LNG, LAT]
            lat = self._dig(n, 8, 0, 2)
            seen[n[0]] = Photo(
                id=n[0], kind=label, url=url, width=w, height=h,
                lat=lat if self._is_num(lat) else None, lng=lng if self._is_num(lng) else None,
                date=self._find_date([x for x in n[10:] if isinstance(x, list)]),
                video_streams=self._find_streams(n) if label == "Video" else [],
            )
        return list(seen.values())

    # ------------------------------------------------------------- records
    def _place_core(self, rec: Any) -> dict:
        if not isinstance(rec, list):
            return {}
        f = next((i for i, c in enumerate(rec) if isinstance(c, str) and FID_RE.match(c)), None)
        if f is None:
            return {}
        anchor = f - _FID_INDEX

        def cand(*idxs: Any) -> list[str]:
            for i in idxs:
                if 0 <= i < len(rec) and isinstance(rec[i], list) and self._strs(rec[i]):
                    return self._strs(rec[i])
            return []

        name = self._dig(rec, f + 1)
        if not isinstance(name, str):
            name = None
        categories = cand(f + 3, f + 2)  # preview: fid+3, search: fid+2

        rating, count = self._at(rec, anchor, 4, 7), self._at(rec, anchor, 4, 8)
        if not (self._is_num(rating) and 0 < rating <= 5):
            score, n = self._dig(rec, f + 3), self._dig(rec, f + 5)
            if self._is_num(score) and 0 < score <= 5:
                rating = score
                if isinstance(n, int):
                    count = n
        lat, lng = self._at(rec, anchor, 9, 2), self._at(rec, anchor, 9, 3)
        return {
            "name": name,
            "fid": rec[f],
            "categories": categories,
            "rating": rating if self._is_num(rating) else None,
            "review_count": count if isinstance(count, int) else None,
            "lat": lat if self._is_num(lat) else None,
            "lng": lng if self._is_num(lng) else None,
        }

    def _find_latlng(self, node: Any) -> Optional[tuple[float, float]]:
        for _, v in self._walk(node):
            if (isinstance(v, list) and len(v) == 4 and v[0] is None and v[1] is None
                    and self._is_num(v[2]) and self._is_num(v[3])
                    and -90 <= v[2] <= 90 and -180 <= v[3] <= 180 and (v[2], v[3]) != (0, 0)):
                return v[2], v[3]
        return None

    def _find_admin_list(self, root: Any) -> dict:
        for _, n in self._walk(root):
            if isinstance(n, list) and len(n) >= 5 and all(isinstance(x, str) for x in n):
                for i, s in enumerate(n):
                    if (POSTAL_RE.match(s) and i >= 1 and i + 2 < len(n)
                            and COUNTRY_RE.match(n[i + 2])):
                        return {"locality": n[0], "city": n[i - 1], "postal_code": s,
                                "state": n[i + 1], "country_code": n[i + 2]}
        return {}

    @staticmethod
    def _encode_plus_code(lat: float, lng: float, digits: int = 10) -> str:
        """Global Open Location Code. digits=10 -> 'XXXXXXXX+XX', digits=11 -> 'XXXXXXXX+XXX'."""
        lat = min(max(lat, -90.0), 90.0) + 90.0
        lng = (lng + 180.0) % 360.0
        refine = digits > 10
        la = math.floor(lat * (40000 if refine else 8000) + 1e-7)
        lo = math.floor(lng * (32000 if refine else 8000) + 1e-7)
        extra = ""
        if refine:
            extra = _OLC[(la % 5) * 4 + (lo % 4)]
            la //= 5
            lo //= 4
        pairs = []
        for _ in range(5):
            pairs.append((la % 20, lo % 20))
            la //= 20
            lo //= 20
        code = "".join(_OLC[a] + _OLC[b] for a, b in reversed(pairs))
        return code[:8] + "+" + code[8:] + extra

    def _plus_codes(self, strings: Sequence[str], lat: Optional[float], lng: Optional[float],
                    city: Optional[str]) -> tuple[Optional[str], Optional[str]]:
        """-> (global, local). Global is computed from coordinates; local = short code + city."""
        short = None
        for s in strings:
            m = PLUS_RE.match(s.strip())
            if m and len(m.group(1).split("+")[0]) % 2 == 0:   # valid area length: 2/4/6/8
                short = m.group(1)
                break
        area = len(short.split("+")[0]) if short else 0

        if short and area == 8:                       # the data already carries a global code
            return short, None
        glob = None
        if lat is not None and lng is not None:
            digits = 11 if short and len(short.split("+")[1]) == 3 else 10
            glob = self._encode_plus_code(lat, lng, digits)
        local = (f"{short} {city}" if city else short) if short else None
        return glob, local

    def _category_ids(self, rec: Any) -> list[str]:
        """In-record category ids: [["coffee_shop", None, 2], ["coffee_store", None, 2]]."""
        for _, n in self._walk(rec):
            if (isinstance(n, list) and n
                    and all(isinstance(e, list) and len(e) == 3 and isinstance(e[0], str)
                            and re.fullmatch(r"[a-z][a-z0-9_]+", e[0])
                            and e[1] is None and isinstance(e[2], int) for e in n)):
                return [e[0] for e in n]
        return []

    def _find_attributes(self, rec: Any) -> dict[str, list[str]]:
        """{'Service options': ['Dine-in', ...], 'Amenities': ['Toilet'], ...} (available only)."""
        attrs: dict[str, list[str]] = {}
        for _, n in self._walk(rec):
            if not (isinstance(n, list) and len(n) >= 3 and isinstance(n[0], str)
                    and not n[0].startswith("/") and isinstance(n[1], str)
                    and isinstance(n[2], list) and n[2]
                    and all(isinstance(i, list) and isinstance(self._dig(i, 0), str)
                            and i[0].startswith("/geo/type/") for i in n[2])):
                continue
            for item in n[2]:
                label = self._dig(item, 1)
                if self._dig(item, 2, 1, 0, 0) == 1 and isinstance(label, str):  # [1,[[1,"Label"]]] = present
                    bucket = attrs.setdefault(n[1], [])
                    if label not in bucket:
                        bucket.append(label)
        return attrs

    def _find_rating_block(self, rec: Any) -> tuple[Optional[float], Optional[int]]:
        """Locate the block that carries a '<n> reviews' label, then read (rating, count) from it."""
        for _, n in self._walk(rec):
            if (isinstance(n, list) and len(n) >= 5
                    and _REVIEWS_LABEL_RE.match(str(self._dig(n, 3, 1, default="")))):
                for i in range(4, len(n) - 1):
                    if self._is_num(n[i]) and 0 < n[i] <= 5 and isinstance(n[i + 1], int):
                        return n[i], n[i + 1]
        return None, None

    def _find_hours(self, rec: Any) -> dict[str, list[str]]:
        """Best-effort: a list of entries whose first item is a weekday name."""
        for _, n in self._walk(rec):
            if (isinstance(n, list) and len(n) >= 5
                    and sum(1 for e in n if isinstance(e, list) and e and e[0] in WEEKDAYS) >= 5):
                hours: dict[str, list[str]] = {}
                for e in n:
                    if isinstance(e, list) and e and e[0] in WEEKDAYS:
                        vals = [self._clean(s) for s in self._iter_strings(e[1:])
                                if re.search(r"\d|closed|24 hours", s, re.I)]
                        hours[e[0]] = list(dict.fromkeys(vals))
                return hours
        return {}

    def _find_phone(self, strings: Sequence[str]) -> Optional[str]:
        def ok(s: str) -> bool:
            digits = re.sub(r"\D", "", s)
            return bool(PHONE_RE.match(s)) and 8 <= len(digits) <= 15 and bool(re.search(r"[\s\-+().]", s))
        return next((s for s in strings if ok(s)), None)

    def _find_website(self, strings: Sequence[str]) -> Optional[str]:
        return next((s for s in strings
                    if s.startswith(("http://", "https://")) and not GOOGLE_HOST_RE.match(s)), None)

    def _admin_from_address(self, address: str) -> dict:
        out: dict = {}
        tokens = address.split()
        if tokens and POSTAL_RE.match(tokens[-1]):
            out["postal_code"] = tokens[-1]
        for name, code in _COUNTRY_NAMES.items():
            if name in address:
                out["country_code"] = code
                break
        return out

    def _parse_related(self, root: Any) -> tuple[Optional[str], list[RelatedPlace]]:
        for _, n in self._walk(root):
            if (
                isinstance(n, list) and len(n) >= 2 and isinstance(n[0], str)
                and isinstance(n[1], list) and n[1]
                and all(isinstance(e, list) and e and isinstance(e[0], str) and FID_RE.match(e[0])
                        for e in n[1])
            ):
                out = []
                for e in n[1]:
                    rec = self._dig(e, 1)
                    core = self._place_core(rec) if isinstance(rec, list) else {}
                    out.append(RelatedPlace(
                        fid=e[0], name=core.get("name"), categories=core.get("categories", []),
                        rating=core.get("rating"), review_count=core.get("review_count"),
                        lat=core.get("lat"), lng=core.get("lng"),
                    ))
                return n[0], out
        return None, []

    def _admin_from_flat(self, rec: Any) -> dict:
        """Search replies flatten the admin chain at the end of the record.

        Pattern (Indonesian layout seen): [... district, kecamatan, city, state,
        country] -> {locality, city, state, country_code}. Only used when the
        standard admin list is absent.
        """
        names = _COUNTRY_NAMES  # country name -> ISO code
        for i, c in enumerate(rec):
            if isinstance(c, str) and c in names and i >= 4 \
                    and all(isinstance(x, str) for x in rec[i - 4:i]):
                return {"locality": rec[i - 4],
                        "city": rec[i - 2], "state": rec[i - 1],
                        "country_code": names[c]}
        return {}

    def _place_from_record(self, rec: list, meta: dict) -> Place:
        core = self._place_core(rec)
        anchor = self._anchor(rec)
        strings = list(self._iter_strings(rec))
        p = Place(fid=core["fid"], categories=core["categories"])

        # --- photos first: their titles are a fallback source for the name
        p.photos = self._parse_photos(rec)

        p.name = self._first(
            lambda: core["name"],
            lambda: max((self._dig(ph, 6, 1) for _, ph in self._walk(rec) if self._is_photo_node(ph)),
                        key=lambda s: isinstance(s, str) and len(s), default=None),
        )

        # --- identity
        if p.fid:
            p.cid = str(int(p.fid.split(":")[1], 16))
        p.place_id = next((s for s in strings if PLACE_ID_RE.match(s)), None)
        p.kgmid = next((s for s in strings if KGMID_RE.match(s)), None)
        p.category_ids = list(dict.fromkeys(
            s.split(":", 1)[1] for s in strings if s.startswith("gcid:")))
        if not p.category_ids:
            p.category_ids = self._category_ids(rec)
        p.place_type = next((s for s in strings if s.startswith("SearchResult.TYPE_")), None)
        # --- address
        admin = self._find_admin_list(rec) or self._admin_from_flat(rec)

        def _addr_from_label() -> Optional[str]:
            # any "<name>, <address>" string, wherever it lives
            if not p.name:
                return None
            pref = p.name + ", "
            cands = [s for s in strings if s.startswith(pref)]
            return cands[0][len(pref):] if cands else None

        p.address = self._first(
            lambda: self._at(rec, anchor, 39) if isinstance(self._at(rec, anchor, 39), str) and "," in self._at(rec, anchor, 39) else None,
            _addr_from_label,
            lambda: self._full_address(strings),
            lambda: ", ".join(self._strs(self._at(rec, anchor, 2))),
        )

        def _lines_by_shape() -> Optional[list[str]]:
            # the address split in chunks: ", ".join(chunks) == full address
            for _, n in self._walk(rec):
                if (isinstance(n, list) and 2 <= len(n) <= 6 and all(isinstance(x, str) for x in n)
                        and p.address and ", ".join(n) == p.address):
                    return n
            return None

        p.address_lines = self._first(
            lambda: self._strs(self._at(rec, anchor, 2)),
            _lines_by_shape) or []
        p.locality = self._first(
            lambda: admin.get("locality"),
            lambda: self._at(rec, anchor, 14) if isinstance(self._at(rec, anchor, 14), str)
                    and not re.fullmatch(r"[\d.,/]+", self._at(rec, anchor, 14)) else None)
        admin2 = self._admin_from_address(p.address) if p.address else {}
        p.city = admin.get("city")
        p.postal_code = admin.get("postal_code") or admin2.get("postal_code")
        p.state = admin.get("state")
        p.country_code = admin.get("country_code") or admin2.get("country_code")
        if not p.country_code:
            for s in strings:
                if s in _COUNTRY_NAMES:
                    p.country_code = _COUNTRY_NAMES[s]
                    break

        ll = None
        if self._is_num(core["lat"]) and self._is_num(core["lng"]):
            ll = (core["lat"], core["lng"])
        ll = ll or self._find_latlng(rec)
        if ll:
            p.lat, p.lng = ll
        p.plus_code, p.plus_code_local = self._plus_codes(
            strings, ll[0] if ll else None, ll[1] if ll else None, p.city)

        # --- reputation
        p.rating, p.review_count = core["rating"], core["review_count"]
        if p.rating is None:
            p.rating, p.review_count = self._find_rating_block(rec)
        p.reviews_url = self._first(
            lambda: self._at(rec, anchor, 4, 3, 0),
            lambda: next((s for s in strings if "search.google.com/local/reviews" in s), None),
        )

        # --- contact & hours (best effort)
        p.website = self._first(
            lambda: self._at(rec, anchor, 7, 0) if str(self._at(rec, anchor, 7, 0)).startswith("http") else None,
            lambda: self._find_website(strings))
        p.phone = self._first(
            lambda: self._at(rec, anchor, 178, 0, 0) if isinstance(self._at(rec, anchor, 178, 0, 0), str) else None,
            lambda: self._find_phone(strings))
        p.hours = self._find_hours(rec)

        p.price_range = self._first(
            lambda: self._at(rec, anchor, 4, 2) if isinstance(self._at(rec, anchor, 4, 2), str) else None)
        p.attributes = self._find_attributes(rec)

        # --- meta
        p.timezone, p.tz_abbr = meta.get("timezone"), meta.get("tz_abbr")
        p.utc_offset_minutes, p.fetched_at = meta.get("utc_offset_minutes"), meta.get("fetched_at")
        if "Claim this business" in strings:
            p.claimed = False
        p.missing_fields = [s for s in ("Add hours", "Add phone number", "Add website") if s in strings]
        if p.place_id:
            p.maps_url = f"https://www.google.com/maps/place/?q=place_id:{p.place_id}"
        elif p.cid:
            p.maps_url = f"https://www.google.com/maps?cid={p.cid}"

        # --- related
        p.related_title, p.related = self._parse_related(rec)
        return p

    # ================================================================ search
    def build_search_params(self, query: Optional[str] = None, pb: Optional[str] = None,
                            lat: Optional[float] = None, lon: Optional[float] = None,
                            hl: Optional[str] = None, gl: Optional[str] = None,
                            session: Optional[str] = None) -> dict:
        cfg = self.config
        sess = session or self._session_id()
        ts = int(time.time() * 1000)
        params = {
            "tbm": "map",
            "authuser": 0,
            # legacy behavior: a bare ``lang`` sets both hl and gl
            "hl": hl or cfg.hl,
            "gl": gl or hl or cfg.gl,
            "tch": 1,
            "psi": f"{sess}.{ts}.1",
        }
        if pb or cfg.pb:
            params["pb"] = pb or cfg.pb
        if query:
            params["q"] = query
        if lat is not None and lon is not None:
            params["near"] = f"{lat},{lon}"
        return params

    def _parse_search_response(self, text: str) -> list[Place]:
        return self._parse_places(text)

    async def asearch(self, query: Optional[str] = None, pb: Optional[str] = None,
                      lat: Optional[float] = None, lon: Optional[float] = None,
                      lang: Optional[str] = None, gl: Optional[str] = None,
                      session: Optional[str] = None,
                      http: Any = None) -> list[Place]:
        """Async search. Uses the shared curl_cffi session (one per event loop).

        Args:
            query: text query.
            pb:    raw protobuf-ish parameter (overrides the default request).
            lat/lon: optional "near" hint.
            lang/gl: language / country overrides for this call.
            session: maps session id to embed in ``psi`` (defaults to the
                     instance's persistent session id).
            http:  a prepared :class:`~mapsfiacore.base.HttpSpec` (from
                   ``prepare_search``) to send instead of building params here.
        """
        cfg = self.config
        params = (http.params if http is not None and http.params is not None
                  else self.build_search_params(query, pb, lat, lon, lang, gl, session))
        url = (URL + http.path) if http is not None and http.path else (URL + "/search")
        timeout = (http.timeout if http is not None and http.timeout is not None
                   else cfg.timeout)
        headers = http.headers if http is not None else None
        try:
            http_session = await self.aget_session()
            resp = await http_session.get(url, params=params, timeout=timeout, headers=headers)
            resp.raise_for_status()
            text = resp.text if isinstance(resp.text, str) else resp.text()
            return self._parse_search_response(text)
        except Exception as exc:
            self.logger.warning("search failed for %r: %s", query, exc)
            return []

    def prepare_search(self, query: Optional[str] = None, pb: Optional[str] = None,
                       lat: Optional[float] = None, lon: Optional[float] = None,
                       lang: Optional[str] = None, gl: Optional[str] = None,
                       session: Optional[str] = None) -> HttpSpec:
        """Build the request as an :class:`~mapsfiacore.base.HttpSpec` (no I/O).

        ``MapsFia.prepare_search`` returns this so callers can inspect or send
        the request themselves (``asearch(http=spec)``).
        """
        return HttpSpec(method="GET", path="/search",
                        params=self.build_search_params(query, pb, lat, lon, lang, gl, session),
                        timeout=self.config.timeout, kind="html")

    def search(self, query: Optional[str] = None, pb: Optional[str] = None,
               lat: Optional[float] = None, lon: Optional[float] = None,
               lang: Optional[str] = None, gl: Optional[str] = None,
               session: Optional[str] = None) -> list[Place]:
        """Sync search: returns a list of :class:`mapsfiacore.models.Place` (empty on failure)."""
        return run_sync(self.asearch(query=query, pb=pb, lat=lat, lon=lon,
                                     lang=lang, gl=gl, session=session))
