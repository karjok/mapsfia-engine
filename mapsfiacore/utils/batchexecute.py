import json
from urllib.parse import urlencode
from curl_cffi.requests import AsyncSession
from mapsfiacore.utils import utils

def generate_headers(gkey=None) -> dict:
    default_header = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        'cache-control': 'no-cache',
        'content-type': 'application/x-www-form-urlencoded;charset=utf-8',
        'origin': 'https://www.google.com',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'sec-ch-ua': '"Not=A?Brand";v="99", "Brave";v="151", "Chromium";v="151"',
        'sec-ch-ua-arch': '"x86"',
        'sec-ch-ua-bitness': '"64"',
        'sec-ch-ua-full-version-list': '"Not=A?Brand";v="99.0.0.0", "Brave";v="151.0.0.0", "Chromium";v="151.0.0.0"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-model': '""',
        'sec-ch-ua-platform': '"Linux"',
        'sec-ch-ua-platform-version': '""',
        'sec-ch-ua-wow64': '?0',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'sec-gpc': '1',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36',
        'x-same-domain': '1',
    }
    if gkey:
        default_header['x-maps-bgkey'] = gkey
    return default_header
def get_place_rpc(fid, place_id, pagination_token="") -> list:
    place_rpc = [
        [
            [fid],
            None,
            None,
            None,
            None,
            [None, None, None, [[1], [3]]],
        ],
        [10, f"{pagination_token or ''}"],
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
    return place_rpc

def get_place_review_overview_rpc(fid:str)->list:
    rpc = [[fid],1,0]
    return rpc

def get_freq(payload:list, rpcid=""):
    freq_payloads_json = json.dumps(payload, separators=(",",":"))
    freq_data = [[[
        rpcid,
        freq_payloads_json,
        None,
        "generic"
    ]]]
    freq_data_json = json.dumps(freq_data, separators=(",",":"))
    freq = {
        "f.req": freq_data_json
    }
    return urlencode(freq)

async def fetch_batchexecute(url:str, freq:str, params:dict, gkey:str=None, sess:AsyncSession=None):
    sess = sess if sess else AsyncSession()
    headers = generate_headers(gkey=gkey)
    sess.headers.update(headers)

    data = await sess.post(url, params=params, data=freq)
    norm = utils.normalize_raw_response(data)
    return norm