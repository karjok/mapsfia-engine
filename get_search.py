from mapsfiacore.utils import utils
from mapsfiacore.utils import pb_nested
from mapsfiacore.models.places import Place
from mapsfiacore.utils.field_parser import parse_place_field
from urllib.parse import unquote, urlencode
from curl_cffi.requests import AsyncSession
import asyncio
import json
import math
import time
import random
import string

EARTH_M_PER_DEG = 111320
RAD = math.pi / 180

# A place record is a list of exactly 260 fields. It can appear:
#   * in the ``data[64]`` result slot (multi-result queries), or
#   * nested under the query wrapper at ``data[0][1][...][14]`` (single entity
#     queries such as a district name), or anywhere else Google decides.
# So we never trust a fixed index; we walk for the shape.
PLACE_RECORD_LEN = 260

def random_session_token():
    return "".join(random.choices(string.ascii_letters + string.digits, k=23))

def _field(nodes, num):
    for n in nodes:
        if n[0] == num:
            return n
    return None

def _insert_after(nodes, num, node):
    for i, n in enumerate(nodes):
        if n[0] == num:
            nodes.insert(i + 1, node)
            return
    nodes.append(node)

def build_pb(lat, lng, perpage:int=20, limit:int=None, next_session=None, ppk=None, offset:int=0):
    c_lat, c_lng, rng = utils.calculate_camera(lat, lng)
    sess = utils.generate_random_session_token()

    w,h = [1920,933]
    
    PB_PARTS = (
        # viewport
        f"!4m12!1m3!1d{rng}!2d{c_lng:.9f}!3d{c_lat:.9f}"
        "!2m3!1f0!2f0!3f0!3m2!1i1121!2i933!4f13.1",

        # paging
        f"!7i{perpage}!10b1",

        # 12m26
        "!12m26!1m5!18b1!30b1!31m1!1b1!34e1!2m4!5m1!6e2!20e3!39b1!10b1!12b1!13b1"
        "!16b1!17m1!3e1!20m4!5e2!6b1!8b1!14b1!46m1!1b0!96b1!99b1",

        # 19m4
        "!19m4!2m3!1i360!2i120!4i8",

        # 20m65 (starts here, continues through the 22m6 group)
        f"!20m65!2m2!1i203!2i100!3m2!2i4!5b1!6m6!1m2!1i86!2i86!1m2!1i{w}!2i{h}",

        # 7m33
        "!7m33!1m3!1e1!2b0!3e3!1m3!1e2!2b1!3e2!1m3!1e2!2b0!3e3!1m3!1e8!2b0!3e3"
        "!1m3!1e10!2b0!3e3!1m3!1e10!2b1!3e2!1m3!1e10!2b0!3e4!1m3!1e9!2b1!3e2!2b1!9b0",

        # 15m16
        "!15m16!1m7!1m2!1m1!1e2!2m2!1i195!2i195!3i20"
        "!1m7!1m2!1m1!1e2!2m2!1i195!2i195!3i20",

        # 22m6 (place/session ids)
        f"!22m6!1s{sess}:6"
        f"!2s1i:0,t:11886,p:{sess}:6"
        f"!7e81!12e5!17s{sess}:223!18e15",

        # 24m109 (first half)
        "!24m109!1m27!13m9!2b1!3b1!4b1!6i1!8b1!9b1!14b1!20b1!25b1"
        "!18m16!3b1!4b1!5b1!6b1!9b1!13b1!14b1!17b1!20b1!21b1!22b1!32b1!33m1!1b1"
        "!34b1!36e2!10m1!8e3!11m1!3e1!17b1!20m2!1e3!1e6!24b1!25b1!26b1!27b1!29b1"
        "!30m1!2b1!36b1!37b1!39m3!2m2!2i1!3i1!43b1!52b1!54m1!1b1!55b1!56m1!1b1"
        "!61m2!1m1!1e1!65m5!3m4!1m3!1m2!1i224!2i298",

        # 24m109 (second half: 72m22)
        "!72m22!1m8!2b1!5b1!7b1!12m4!1b1!2b1!4m1!1e1!4b1"
        "!8m10!1m6!4m1!1e1!4m1!1e3!4m1!1e4"
        "!3sother_user_google_review_posts__and__hotel_and_vr_partner_review_posts"
        "!6m1!1e1!9b1!89b1!90m2!1m1!1e2!98m3!1b1!2b1!3b1!103b1!113b1!114m3!1b1"
        "!2m1!1b1!117b1!122m1!1b1!126b1!127b1!128m1!1b1",

        # 26m4
        "!26m4!2m3!1i80!2i92!4i8",

        # 30m28
        "!30m28!1m6!1m2!1i0!2i0!2m2!1i530!2i933"
        "!1m6!1m2!1i1071!2i0!2m2!1i1121!2i933"
        "!1m6!1m2!1i0!2i0!2m2!1i1121!2i20"
        "!1m6!1m2!1i0!2i913!2m2!1i1121!2i933",

        # 34m19
        "!34m19!2b1!3b1!4b1!6b1!8m6!1b1!3b1!4b1!5b1!6b1!7b1!9b1!12b1!14b1!20b1"
        "!23b1!25b1!26b1!31b1!37m1!1e81!42b1!47m0"
        "!49m10!3b1!6m2!1b1!2b1!7m2!1e3!2b1!8b1!9b1!10e2!50m4!2e2!3m2!1b1!3b1",

        # tail
        "!67m5!7b1!10b1!14b1!15m1!1b0!69i798!77b1",
    )

    pb = "".join(PB_PARTS)
    j = pb_nested.decode_tree(pb)

    # Offset pagination: an extra top-level !8i<offset> field between the
    # page-size field (7) and the "10b1" marker selects the result window.
    # offset 0 -> first page, offset == perpage -> second page, etc.
    if offset:
        _insert_after(j, 7, [8, "i", int(offset)])

    # Continuation tokens: the search reply hands back a session token
    # (data[66]) and a ppk (data[35]). They go into field 50 (sub-field 1)
    # and field 59 respectively.
    if next_session:
        f50 = _field(j, 50)
        session_group = [
            1, "m", [
                [2, "m", [
                    [1, "u", 3],
                    [4, "s", "Buka sekarang"],
                    [5, "e", 1],
                    [9, "s", next_session],
                    [10, "m", [[3, "m", [[1, "e", 1]]]]],
                ]],
                [3, "m", [[1, "u", 3]]],
                [4, "B", "IAE"],
            ],
        ]
        if f50 is not None:
            f50[2].insert(0, session_group)
        else:
            j.append([50, "m", [
                session_group,
                [2, "e", 2],
                [3, "m", [[1, "b", 1], [3, "b", 1]]],
            ]])
        if ppk:
            _insert_after(j, 50, [59, "B", ppk])
    elif ppk:
        _insert_after(j, 50, [59, "B", ppk])

    return pb_nested.encode(j)

def parse_search_response(data: list) -> dict:
    if len(data) != 72:
       return None
    places = data[64] if utils.has_index(data, 64) and isinstance(data[64], list) else []
    palces_data = []
    for place in places:
        try:
            pd = place[1]
            place_entry = parse_place_field(pd)
        except (IndexError, TypeError, ValueError):
            # Some slots carry non-place records (street-view / business cards)
            # whose shape is not a 260/177 field place. Skip them.
            continue
        palces_data.append(place_entry)
    next_session = data[66] if utils.has_index(data, 66) else None
    ppk_session = data[35] if utils.has_index(data, 35) else None
    return  {"places": palces_data, "n": next_session, "ppk": ppk_session}


SEARCH_URL = "https://www.google.com/search"


def _search_params(query, pb=None, lat=None, lon=None, lang="id",
                   perpage: int = 20, offset: int = 0,
                   next_session=None, ppk=None) -> dict:
    params = {
        "tbm": "map",
        "authuser": 0,
        "hl": lang,
        "gl": lang,
        "q": query,
        "tch": 1,
    }
    if pb:
        # pb may arrive URL-encoded (contains %3A/%2C). A params dict is
        # serialized once, so decode to avoid double-encoding on the wire.
        params["pb"] = unquote(pb)
    elif lat is not None and lon is not None:
        params["pb"] = build_pb(lat, lon, perpage=perpage, offset=offset,
                                next_session=next_session, ppk=ppk)
    else:
        d_lat, d_lon, _ = utils.get_default_centroid()
        params["pb"] = build_pb(d_lat, d_lon, perpage=perpage, offset=offset,
                                next_session=next_session, ppk=ppk)
    return params


def search(query, pb=None, lat=None, lon=None, lang="id", session=None,
           perpage: int = 20, offset: int = 0, next_session=None, ppk=None,
           retries: int = 3, retry_delay: float = 0.7) -> dict:
    """One `tbm=map` search returning ``{"places", "n", "ppk"}``.

    Pagination is offset based: pass ``offset=perpage`` for the second page,
    ``offset=perpage*2`` for the third, and so on. The reply also carries a
    continuation session token (``n``) and a ppk which, when fed back through
    ``next_session``/``ppk``, reproduce the exact request Google emits for the
    next page.

    Google is non-deterministic: the same request may return a suggestion
    stub, a skeleton result set, or the full result set. We retry while the
    response contains no place records so callers get stable output.

    `session` is an optional ``requests``/``curl_cffi`` session owned by the
    caller; when omitted a fresh browser-impersonating session is used.

    For fetching every page until Google's limit, prefer :func:`search_all`.
    """
    params = _search_params(query, pb, lat, lon, lang, perpage, offset,
                            next_session, ppk)
    sess = utils.get_browser_session("https://www.google.com/maps")
    getter = sess.get if session is None else session.get
    for attempt in range(max(1, retries)):
        resp = getter(SEARCH_URL, params=params)
        norm = utils.normalize_raw_response(resp)
        result = parse_search_response(norm)
        if result and result["places"]:
            return result
        time.sleep(retry_delay)
    return result


async def asearch_page(sess, query, pb=None, lat=None, lon=None, lang="id",
                       perpage: int = 20, offset: int = 0, next_session=None,
                       ppk=None, retries: int = 3,
                       retry_delay: float = 0.7) -> dict:
    """Fetch a single result page over an existing :class:`AsyncSession`.

    Retries only malformed replies (a valid 72-field reply with an empty result
    slot is Google's end-of-results marker, not an error).
    """
    params = _search_params(query, pb, lat, lon, lang, perpage, offset,
                            next_session, ppk)
    result = None
    for attempt in range(max(1, retries)):
        resp = await sess.get(SEARCH_URL, params=params)
        result = parse_search_response(utils.normalize_raw_response(resp))
        if result is not None:
            return result
        await asyncio.sleep(retry_delay)
    return result


async def search_all(query, lat=None, lon=None, lang="id", perpage: int = 20,
                     max_results=None, session=None, next_session=None,
                     ppk=None, dedupe: bool = True, concurrency: int = 12,
                     page_delay: float = 0.0, retries: int = 3,
                     retry_delay: float = 0.7, on_page=None) -> list[Place]:
    """Fetch every page of a `tbm=map` search until Google stops returning results.

    Pagination is offset based, so pages are independent and can be fetched in
    parallel. Pages are dispatched in batches of ``concurrency`` over a single
    continuous :class:`curl_cffi.requests.AsyncSession` (one cookie jar, one
    TLS session), which is dramatically faster than fetching them one by one.

    Args:
        query: text query.
        lat/lon: map center for the viewport / result window.
        lang: ``hl``/``gl`` language.
        perpage: results per page (Google honors this up to ~20).
        max_results: hard cap on returned places; ``None`` = Google's limit.
        session: optional pre-existing ``AsyncSession`` (caller owns it);
                 when omitted one is created and closed here.
        next_session/ppk: continuation state to resume from a prior search;
                 applied to the first page only.
        dedupe: drop places already seen (Google repeats results across pages).
        concurrency: number of pages fetched in parallel per batch.
        page_delay: optional sleep between batches (be gentle).
        retries/retry_delay: retry a page while it returns no place records.
        on_page: optional ``fn(offset, added, total)`` progress callback.

    Returns:
        A list of :class:`~mapsfiacore.models.places.Place`.
    """
    owns_session = session is None
    sess = session or AsyncSession(impersonate="chrome146")
    try:
        if owns_session:
            await sess.get("https://www.google.com/maps/")
            await asyncio.sleep(2)

        places: list[Place] = []
        seen: set = set()
        offset = 0

        while max_results is None or len(places) < max_results:
            batch = concurrency
            if max_results is not None:
                remaining = max_results - len(places)
                batch = min(batch, -(-remaining // perpage))
            offsets = [offset + i * perpage for i in range(batch)]
            pages = await asyncio.gather(*[
                asearch_page(
                    sess, query, lat=lat, lon=lon, lang=lang, perpage=perpage,
                    offset=off,
                    next_session=next_session if off == 0 else None,
                    ppk=ppk if off == 0 else None,
                    retries=retries, retry_delay=retry_delay,
                )
                for off in offsets
            ])

            stop = False
            for off, page in zip(offsets, pages):
                if not page or not page["places"]:
                    # Empty page = Google's limit for this offset; later
                    # offsets are beyond it too.
                    stop = True
                    continue

                added = 0
                for place in page["places"]:
                    if max_results is not None and len(places) >= max_results:
                        stop = True
                        break
                    key = place.fid or place.place_id or place.name
                    if dedupe and key in seen:
                        continue
                    seen.add(key)
                    places.append(place)
                    added += 1

                if on_page:
                    on_page(off, added, len(places))
                if stop:
                    break

            if stop:
                break

            offset += concurrency * perpage
            if page_delay:
                await asyncio.sleep(page_delay)

        return places
    finally:
        if owns_session:
            await sess.close()


if __name__ == "__main__":
    places = asyncio.run(search_all("kopi", lat=-6.252849, lon=106.9183385))
    print(f"{'No.':<4} {'Maps URL': <50} {'Place Name': <40} {'Rating': <5} {'Review Count'}")
    for n, place in enumerate(places, 1):
        print(f"{n: <4} {place.maps_url: <50} {place.name: <40} {place.rating: <5} ({place.review_count})")
