from mapsfiacore.utils import utils
from mapsfiacore.utils import pb_nested
from mapsfiacore.models.places import Place
from mapsfiacore.utils.field_parser import parse_place_field
from urllib.parse import unquote, urlencode
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

def build_pb(lat, lng, perpage:int=10, limit:int=None, next_session=None, ppk=None):
    c_lat, c_lng, rng = utils.calculate_camera(lat, lng)
    sess = utils.generate_random_session_token()
    rn = utils.generate_random_number(100)
    rnx = utils.generate_random_number(999999)

    yyyymmdd = time.strftime("%Y-%m-%d")
    w,h = [1920,933]
    
    PB_PARTS = (
        # viewport
        f"!4m12!1m3!1d{rng}!2d{c_lng:.9f}!3d{c_lat:.9f}"
        "!2m3!1f0!2f0!3f0!3m2!1i1121!2i933!4f13.1",

        # paging
        "!7i20!10b1",

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
    if next_session and ppk:
        d = [None,[3,None,None,"Buka+sekarang",1,None,None,None,next_session,[None,None,[1]]],[3],"IAE"]
        j[49][0] = d
        j[58] = ppk
    pb = pb_nested.encode(j)
    return pb

def parse_search_response(data: list) -> dict:
    if len(data) != 72:
       return None
    places = data[64] if utils.has_index(data, 64) and isinstance(data[64], list) else []
    palces_data = []
    for place in places:
        pd = place[1]
        place_entry = parse_place_field(pd)
        palces_data.append(place_entry)
    next_session = data[66]
    ppk_session = data[35]
    return  {"places": palces_data, "n": next_session, "ppk": ppk_session}


def search(query, pb=None, lat=None, lon=None, lang="id", session=None,
           retries: int = 3, retry_delay: float = 0.7) -> list[Place]:
    """One `tbm=map` search returning a list of :class:`Place`.

    Google is non-deterministic: the same request may return a suggestion
    stub, a skeleton result set, or the full result set. We retry while the
    response contains no place records so callers get stable output.

    `session` is an optional ``requests``/``curl_cffi`` session owned by the
    caller; when omitted a fresh browser-impersonating session is used.
    """
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
        params["pb"] = build_pb(lat, lon)
    else:
        d_lat, d_lon, _ = utils.get_default_centroid()
        params["pb"] = build_pb(d_lat, d_lon)
    sess = utils.get_browser_session("https://www.google.com/maps")
    getter = sess.get if session is None else session.get
    resp = getter("https://www.google.com/search", params=params)
    norm = utils.normalize_raw_response(resp)
    places = parse_search_response(norm)
    
    print(places)
    # return search_result


if __name__ == "__main__":
    for place in search("kopi"):
        print(place)
