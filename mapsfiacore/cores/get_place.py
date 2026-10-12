import random
import string
import time
from urllib.parse import quote, quote_plus, unquote
from curl_cffi import Session
from mapsfiacore.utils import utils
from mapsfiacore.utils import field_parser
import json
import re
import html

URL = "https://www.google.com/maps/preview/place"

_HEADERS = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "referer": "https://www.google.com/",
    "sec-ch-ua": '"Not=A?Brand";v="99", "Brave";v="151", "Chromium";v="151"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Linux"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "sec-gpc": "1",
    "x-maps-diversion-context-bin": "CAE=",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
}


def random_session_token():
    return "".join(random.choices(string.ascii_letters + string.digits, k=23))


def build_place_pb(fid, lat=None, lng=None, gmid="", query="", label="", session_token=None,
                   distance=2000.0, width=713, height=933):
    if not lat and not lng and not gmid:
        raise KeyError("build place pb need lat,lng or gmid")
    token = session_token or random_session_token()
    if lat and lng:
        place_identifiers = f"!4m2!3d{lat}!4d{lng}"
    if gmid:
        place_identifiers = f"!5e1!9e0!11s{gmid}"
    if query:
        place_identifiers += f"!6s{query}"
        # f"!3m12!1m3!1d{distance}!2d{lng}!3d{lat}"
    body = (
        f"!1m17"
        f"!1s{fid}"
        f"!2m3!1f0!2f0!3f0"
        f"!3m2!1i{width}!2i{height}!4f13.1"
        f"{place_identifiers}"
        f"!12m4!2m3!1i360!2i120!4i8"
        f"!13m57!2m2!1i203!2i100!3m2!2i4!5b1!6m6!1m2!1i86!2i86!1m2!1i408!2i240"
        f"!7m33!1m3!1e1!2b0!3e3!1m3!1e2!2b1!3e2!1m3!1e2!2b0!3e3!1m3!1e8!2b0!3e3"
        f"!1m3!1e10!2b0!3e3!1m3!1e10!2b1!3e2!1m3!1e10!2b0!3e4!1m3!1e9!2b1!3e2"
        f"!2b1!9b0!15m8!1m7!1m2!1m1!1e2!2m2!1i195!2i195!3i20"
        f"!14m2!1s{token}!7e81"
        f"!15m111!1m29!4e2!13m9!2b1!3b1!4b1!6i1!8b1!9b1!14b1!20b1!25b1!18m17"
        f"!3b1!4b1!5b1!6b1!9b1!13b1!14b1!17b1!20b1!21b1!22b1!30b1!32b1!33m1!1b1"
        f"!34b1!36e2!10m1!8e3!11m1!3e1!17b1!20m2!1e3!1e6!24b1!25b1!26b1!27b1!29b1"
        f"!30m1!2b1!36b1!37b1!39m3!2m2!2i1!3i1!43b1!52b1!54m1!1b1!55b1!56m1!1b1"
        f"!61m2!1m1!1e1!65m5!3m4!1m3!1m2!1i224!2i298!72m22!1m8!2b1!5b1!7b1!12m4"
        f"!1b1!2b1!4m1!1e1!4b1!8m10!1m6!4m1!1e1!4m1!1e3!4m1!1e4"
        f"!3sother_user_google_review_posts__and__hotel_and_vr_partner_review_posts"
        f"!6m1!1e1!9b1!89b1!90m2!1m1!1e2!98m3!1b1!2b1!3b1!103b1!113b1!114m3!1b1"
        f"!2m1!1b1!117b1!122m1!1b1!126b1!127b1!128m1!1b1!21m0!22m2!1e81!8e4!29m0"
        f"!30m6!3b1!6m1!2b1!7m1!2b1!9b1!34m5!7b1!10b1!14b1!15m1!1b0!37i797"
    )
    if label:
        body += f"!39s{quote_plus(label)}"
    return body


def build_place_url(fid=None, lat=None, lng=None, gmid=None, query="", label="", hl="id", gl="id", **kw):
    """Build the full /maps/preview/place URL for a place."""
    pb = build_place_pb(fid=fid, lat=lat, lng=lng, gmid=gmid, query=query, label=label, **kw)
    q = query or label
    return (f"{URL}?authuser=0&hl={hl}&gl={gl}"
            f"&pb={quote(pb, safe='!~()*')}"
            f"&q={quote(q)}")


def _has_rich_reviews(norm) -> bool:
    can = utils.get_candidate_from_data(norm)
    block = can[4] if isinstance(can, list) and len(can) > 4 else None
    return bool(isinstance(block, list) and len(block) > 8
                and (isinstance(block[8], int) or (len(block) > 3 and block[3])))


def fetch_place_response(fid, lat=None, lng=None, gmid=None, query="", label="", hl="id", gl="id",
                         sess=None, retries=4, retry_delay=0.6, **kw):
    if sess is None:
        sess = utils.get_browser_session("https://www.google.com/maps/")
    if not lng and not lat:
        source = sess.get(f"https://www.google.com/maps?ftid={fid}")
        url = re.search(r'(?:html .*<head>.*<link.*href="(/maps/preview/place\?.*?)")', source.text)
        if url:
            escaped = url.group(1)
            unescaped = html.unescape(escaped)
            url = f"https://www.google.com{unescaped}"
            print(url)
        else:
            url = build_place_url(fid, lat=lat, lng=lng, gmid=gmid, query=query, label=label,
                          hl=hl, gl=gl, **kw)
    else:
            url = build_place_url(fid, lat=lat, lng=lng, gmid=gmid, query=query, label=label,
                          hl=hl, gl=gl, **kw)
    norm = None
    response = sess.get(url, headers=_HEADERS)
    norm = utils.normalize_raw_response(response)
    # for attempt in range(max(1, retries)):
    #     if _has_rich_reviews(norm):
    #         break
    #     if attempt + 1 < retries:
    #         print(f"retries {attempt}")
    #         time.sleep(retry_delay)
    return norm


def get_place_data(fid, lat=None, lng=None, gmid=None, query="", label="", hl="id", gl="id",
                         sess=None, **kw):
    norm = fetch_place_response(fid, lat=lat, lng=lng, gmid=gmid, query=query, label=label, gl=gl, sess=sess, **kw)
    can = utils.get_candidate_from_data(norm)
    return field_parser.parse_place_field(can)
