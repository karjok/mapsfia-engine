import asyncio
import json
from dataclasses import asdict
from urllib.parse import urlencode

from curl_cffi.requests import AsyncSession

from mapsfiacore.models.rating import Review
from mapsfiacore.utils import field_parser, utils

BATCHEXECUTE_URL = "https://www.google.com/maps/_/MapsWizUi/data/batchexecute"
RPC_ID = "qv9Egd"
PER_PAGE = 10
EMPTY_MARKER = "[null,null,null,null,null,true,[true]]"

HEADERS = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/x-www-form-urlencoded;charset=utf-8",
    "origin": "https://www.google.com",
    "priority": "u=1, i",
    "referer": "https://www.google.com/maps/",
    "sec-ch-ua": '"Not=A?Brand";v="99", "Brave";v="151", "Chromium";v="151"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Linux"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "sec-gpc": "1",
    "user-agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
    ),
    "x-maps-diversion-context-bin": "CAE=",
    "x-same-domain": "1",
}


# --------------------------------------------------------------------------
# Request building
# --------------------------------------------------------------------------
def generate_freq(fid, place_id, pagination_token="", rpcid=RPC_ID, perpage=PER_PAGE):
    """Build the url-encoded `f.req` body for a reviews batchexecute call."""
    inner = [
        [[fid], None, None, None, None, [None, None, None, [[1], [3]]]],
        [perpage, pagination_token or ""],
        None,
        None,
        [place_id, None, None, None, None, None, 81],
        None,
        None,
        [None, 1, 1, None, 1, None, 1, None, None, None, None, [1, 1, None, [[1]]]],
        None,
        None,
        [3, 1, None, None, None, [2]],
        None,
        [1],
    ]
    inner_json = json.dumps(inner, separators=(",", ":"))
    outer_json = json.dumps([[[rpcid, inner_json, None, "generic"]]], separators=(",", ":"))
    return urlencode({"f.req": outer_json})


def generate_bgkey_header(fid, place_id):
    return utils.get_bgkey(fid, place_id)


# --------------------------------------------------------------------------
# Response parsing
# --------------------------------------------------------------------------
def parse_review_item(raw_review: list) -> Review:
    item = utils.get_candidate_from_data(raw_review)

    return Review(
        rating=field_parser.parse_rating_field(item[2]),
        user=field_parser.parse_user_field(item[1][4]),
        timestamp=item[1][2],
        relative_time=item[1][6],
    )


def parse_reviews_data(data: list) -> dict:
    """Return {"reviews": [...], "pagination_token": str}, or {} when empty."""
    payload = utils.get_candidate_from_data(data, 1)
    raw = payload[2]
    if not isinstance(raw, str) or raw == EMPTY_MARKER:
        return {}

    decoded = json.loads(raw)
    pagination_token = decoded[1]
    items = utils.get_candidate_from_data(decoded)
    return {
        "reviews": [parse_review_item(i) for i in items],
        "pagination_token": pagination_token,
    }


# --------------------------------------------------------------------------
# Fetching
# --------------------------------------------------------------------------
async def get_reviews_data(
    fid, place_id, session, gkey,
    source_path="", pagination_token="", perpage=PER_PAGE, hl="id", gl="id",
) -> dict:
    session.headers.update({**HEADERS, "x-maps-bgkey": gkey})

    params = {"rpcids": RPC_ID, "source-path": source_path, "hl": hl, "gl": gl}
    body = generate_freq(
        fid, place_id,
        pagination_token=pagination_token, rpcid=RPC_ID, perpage=perpage,
    )

    response = await session.post(BATCHEXECUTE_URL, params=params, data=body)
    return parse_reviews_data(utils.normalize_raw_response(response))


async def _ensure_session(sess):
    if not sess.cookies.get("NID"):
        print("Opening session..")
        await sess.get("https://www.google.com/maps/")
        await asyncio.sleep(3)


def _ensure_gkey(sess, fid, place_id, gkey=None):
    gkey = gkey or getattr(sess, "_maps_gkey", None)
    if not gkey:
        print("Generating gkey..")
        gkey = generate_bgkey_header(fid, place_id)
        try:
            sess._maps_gkey = gkey
        except Exception:
            pass
    return gkey


async def get_reviews(
    fid, place_id, gkey=None, sess=None, max_count=10, pagination_token=None,
) -> list[Review]:
    pages = -(-max_count // PER_PAGE)  # ceil division
    if pages <= 0:
        return []

    owns_session = sess is None
    sess = sess or AsyncSession(impersonate="chrome146")

    try:
        await _ensure_session(sess)
        gkey = _ensure_gkey(sess, fid, place_id, gkey)

        reviews: list[Review] = []
        token = pagination_token

        # Each page's token unlocks the next one, so pages must be sequential.
        for _ in range(pages):
            data = await get_reviews_data(
                fid, place_id, sess, gkey, pagination_token=token
            )
            if not data:
                break
            reviews.extend(data.get("reviews", []))
            token = data.get("pagination_token")
            if not token:
                break

        return reviews
    finally:
        if owns_session:
            await sess.close()

