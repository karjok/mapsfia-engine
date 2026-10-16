import asyncio
import json

from curl_cffi.requests import AsyncSession

from mapsfiacore.utils import utils
from mapsfiacore.parsers import reviews as parser

# source-path is not required to be exact; a minimal one is enough.
SOURCE_PATH = (
    "/maps/place/WARUNG+KOPI+RAYANA/"
    "@-6.3265096,106.9655632,1106m/data=!3m1!1e3!4m8!3m7!"
    "1s0x2e699300413f358f:0xe29080fa0f4f070f!8m2!3d-6.3265149!4d106.9681381"
    "!9m1!1b1!16s%2Fg%2F11zkmgmcxk"
)

RPCID = "qv9Egd"
URL = "https://www.google.com/maps/_/MapsWizUi/data/batchexecute"
EMPTY_MARKER = "[null,null,null,null,null,true]"


def build_freq(FID, PLACE_ID, pagination_token="", perpage=10):
    payload = [
        [[FID], None, None, None, None, [None, None, None, [[1], [3]]]],
        [perpage, pagination_token or ""],
        None,
        None,
        [PLACE_ID, None, None, None, None, None, 81],
        None,
        None,
        [None, 1, 1, None, 1, None, 1, None, None, None, None, [1, 1, None, [[1]]]],
        None,
        None,
        [3, 1, None, None, None, [2]],
        None,
        [1],
    ]
    return utils.generate_batchexecute_freq(payload, rpcid=RPCID)


def gen_bgkey(FID, PLACE_ID, pagination_token="", tries=8):
    for _ in range(tries):
        try:
            return utils.get_bgkey(FID, PLACE_ID, pagination_token)
        except RuntimeError:
            pass
    raise RuntimeError("could not generate x-maps-bgkey")


async def fetch_nid():
    """NID is the only cookie that matters. 2s settle time after fetching."""
    s = AsyncSession(impersonate="chrome146")
    await s.get("https://www.google.com/")
    nid = s.cookies.get("NID")
    await s.close()
    await asyncio.sleep(2)
    return nid


async def request_page(pagination_token, gkey, nid, perpage=10):
    sess = AsyncSession(impersonate="chrome146")
    sess.cookies.set("NID", nid, domain=".google.com")
    sess.headers.update({
        "content-type": "application/x-www-form-urlencoded;charset=utf-8",
        "x-maps-bgkey": gkey,
    })
    params = {"rpcids": RPCID, "source-path": SOURCE_PATH, "hl": "id", "gl": "id"}
    r = await sess.post(URL, params=params, data=build_freq(pagination_token, perpage))
    await sess.close()
    return r.text


def parse_page(body):
    """Return (reviews_raw_list, next_pagination_token)."""
    can = utils.get_candidate_from_data(utils.normalize_raw_response(body), 1)
    raw = can[2]
    if not isinstance(raw, str) or raw == EMPTY_MARKER:
        return [], None
    inner = json.loads(raw)
    next_token = inner[1]
    items = utils.get_candidate_from_data(inner)
    return items, next_token


async def get_reviews(FID, PLACE_ID, max_pages=None, perpage=10):
    """Fetch all review pages sequentially; each page's token unlocks the next."""
    nid = await fetch_nid()
    token = ""
    all_reviews = []
    page = 0
    gkey = gen_bgkey(FID, PLACE_ID, token)
    while True:
        page += 1
        body = await request_page(token, gkey, nid, perpage)
        items, token = parse_page(body)
        print(f"page {page}: {len(items)} reviews, next={bool(token)}")
        all_reviews.extend(items)
        if not token or not items:
            break
        if max_pages and page >= max_pages:
            break
    return all_reviews


async def main():
    # from mapsfiacore.cores.get_place import get_place_data
    # d = get_place_data(FID)
    # print(d.maps_url)
    reviews = await get_reviews(perpage=10, max_pages=100)
    print(f"\ntotal raw review items: {len(reviews)}")
    user_reviews = []
    if reviews:
        for review in reviews:
            r = parser.review_parser(review, fid="0000000")
            user_reviews.append(r)
    print(user_reviews)
        


if __name__ == "__main__":
    asyncio.run(main())
