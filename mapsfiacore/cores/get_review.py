from curl_cffi import Session
from curl_cffi.requests import AsyncSession
from urllib.parse import urlencode
import json
from mapsfiacore.utils import utils
from mapsfiacore.utils import field_parser
from mapsfiacore.models.rating import Review
from dataclasses import asdict
import asyncio
from asyncio import Semaphore
import time
    

def generate_freq(fid, place_id, pagination_token="", rpcid="qv9Egd", perpage=10, page_plus_one=0):
    page = f":{page_plus_one}" if page_plus_one else ""
    freq_payloads = [
            [
                [fid],
                None,
                None,
                None,
                None,
                [None, None, None, [[1], [3]]],
            ],
            [perpage, f"{pagination_token or ''}"],
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
    freq_payloads_json = json.dumps(freq_payloads, separators=(",",":"))
    freq_data = [
        [
            [
                rpcid,
                freq_payloads_json,
                None,
                "generic"
            ]
        ]
    ]
    freq_data_json = json.dumps(freq_data, separators=(",",":"))
    freq = {
        "f.req": freq_data_json
    }
    return urlencode(freq)
def parse_review_item(review:list):
    try:
        review = utils.get_candidate_from_data(review)
    except:
        print(review)
    review_tampstamp = review[1][2]
    review_relative_time = review[1][6]

    ## extract reviewer data
    user_field = review[1][4]
    user = field_parser.parse_user_field(user_field)
    # print(reviewer)

    ## review data
    review_field = review[2]
    review = field_parser.parse_rating_field(review_field)
    rating = {
        "rating": review,
        "user": user,
        "timestamp": review_tampstamp,
        "relative_time": review_relative_time

    }

    rating = Review(**rating)

    return rating


def generate_bgkey_header(fid, place_id, session_id=None):
    gkey = utils.get_bgkey(fid, place_id)
    return gkey

def parse_reviews_data(data:list):
    reviews = utils.get_candidate_from_data(data, 1)
    if isinstance(reviews[2], str) and reviews[2] != '[null,null,null,null,null,true,[true]]':
        reviews = json.loads(reviews[2])
        pagination_session = reviews[1]
        reviews = utils.get_candidate_from_data(reviews)
        reviews_data = {
            "reviews": [parse_review_item(i) for i in reviews],
            "pagination_token": pagination_session
        }
        return reviews_data
    else:
        return {}
async def get_reviews_data(fid, place_id, session, gkey, source_path="", pagination_token="", page=0, perpage=10, hl="id", gl="id"):
    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        'content-type': 'application/x-www-form-urlencoded;charset=utf-8',
        'origin': 'https://www.google.com',
        'priority': 'u=1, i',
        'referer': 'https://www.google.com/maps/',
        'sec-ch-ua': '"Not=A?Brand";v="99", "Brave";v="151", "Chromium";v="151"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'sec-gpc': '1',
        'x-maps-bgkey': gkey,
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36',
        'x-maps-diversion-context-bin': 'CAE=',
        'x-same-domain': '1',
    }
    session.headers.update(headers)

    rpcids = "qv9Egd"
    params = {
        "rpcids": rpcids ,
        "source-path": source_path,
        "hl": hl,
        "gl": gl,
    }
    url = "https://www.google.com/maps/_/MapsWizUi/data/batchexecute"
    payloads = generate_freq(fid, place_id, pagination_token=pagination_token, rpcid=rpcids, page_plus_one=page, perpage=perpage)
    reviews_data_response = await session.post(url, params=params, data=payloads)
    reviews_data_normalized = utils.normalize_raw_response(reviews_data_response)
    print(json.dumps(reviews_data_normalized))
    reviews = parse_reviews_data(reviews_data_normalized)
    return reviews


async def get_reviews(fid, place_id, gkey=None, sess=None, max_count=10, pagination_token=None) -> list[Review]:
    if not sess:
        sess = AsyncSession(impersonate="chrome146")
    if not sess.cookies.get("NID"):
        print("Opening session..")
        await sess.get("https://www.google.com/maps/")
        await asyncio.sleep(3)
    if not gkey:
        gkey = getattr(sess, "_maps_gkey", None)
        if not gkey:
            print("Generating gkey..")
            gkey = generate_bgkey_header(fid, place_id)
            try:
                sess._maps_gkey = gkey
            except Exception:
                pass
    pag_token = pagination_token
    modulo = (max_count % 10)
    page_addition = 1 if modulo else 0
    iteration = int(((max_count - modulo) / 10) + page_addition)
    if iteration <= 0:
        return []

    # First call doubles as the pagination probe: with no token there is
    # nothing left to iterate over, so return its result as-is.
    first = await get_reviews_data(fid, place_id, sess, gkey, pagination_token=pag_token)
    if not first or not first.get("pagination_token"):
        return first.get("reviews", []) if first else []

    reviews = list(first.get("reviews", []))
    sem = Semaphore(10)

    async def fetch_next(prev_task):
        async with sem:
            prev = await prev_task
            if not prev or not prev.get("pagination_token"):
                return None
            return await get_reviews_data(fid, place_id, sess, gkey,
                                          pagination_token=prev.get("pagination_token"))

    # Chain the remaining tasks: each page's token unlocks the next one.
    loop = asyncio.get_running_loop()
    prev = loop.create_future()
    prev.set_result(first)
    tasks = []
    for _ in range(max(iteration - 1, 0)):
        task = asyncio.ensure_future(fetch_next(prev))
        tasks.append(task)
        prev = task

    for data in await asyncio.gather(*tasks):
        if data:
            reviews.extend(data.get("reviews", []))
            print("got reviews: ", data.get("reviews", []))
    return reviews


if __name__ == "__main__":
    fid = "0x2e699300413f358f:0xe29080fa0f4f070f"
    place_id = "ChIJjzU_QQCTaS4RDwdPD_qAkOI"
    result = asyncio.run(get_reviews(fid, place_id, max_count=20))
    result_json = [asdict(i) for i in result]
    json.dump(result_json, open(f"output-{place_id}.json","w"))
    print(len(result_json), "generated !")
    # get_reviews_data("0x2e699300407b14d1:0x5676891878cc8ae1", "oLDCaufRB-2ZhvcPr-ki")
    # get_reviews_data("0x2e7a15ca78f42c63:0xdc8077d4d6be4249", "It7CatX8G7qd4-EPj_fXyQE")
    