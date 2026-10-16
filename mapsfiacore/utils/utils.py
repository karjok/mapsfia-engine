import json
from curl_cffi.requests import Response
from curl_cffi import Session, AsyncSession
from typing import Union
import subprocess
import re
import math
import time
import random, string
from urllib.parse import urlencode

def has_index(l:list, i:int)-> bool:
    try:
        has_index = l[i]
        return True
    except:
        return False

def get_signature(data:list):
    sig_map = {
        "str": str,
        "int": int,
        "list": list,
        "dict": dict,
        "float": float,
        "NoneType": None,
    }
    sig = [sig_map[type(sig).__name__] for sig in data]
    return sig

def scan_root(d, sign):
    candidate = []

    def rec(o):
        if isinstance(o, list):
            if sign in o:
                candidate.append(o)
            for v in o:
                rec(v)
        elif isinstance(o, dict):
            for v in o.values():
                rec(v)

    rec(d)
    # if len(candidate) == 1:
    #     return candidate[0]
    return candidate

def scan_signature(d, sig, ln=None):
    candidate = []

    def match(node):
        if not isinstance(node, list):
            return False
        if ln is not None and len(node) != ln:
            return False

        def rec_match(i, j):
            if i == len(sig):
                return j == len(node)
            t = sig[i]
            if t is ...:
                for k in range(j, len(node) + 1):
                    if rec_match(i + 1, k):
                        return True
                return False
            if j >= len(node):
                return False
            v = node[j]
            if t is None:
                if v is not None:
                    return False
            elif type(v) is not t:
                return False
            return rec_match(i + 1, j + 1)

        return rec_match(0, 0)

    def rec(o):
        if isinstance(o, list):
            if match(o):
                candidate.append(o)
            for v in o:
                rec(v)
        elif isinstance(o, dict):
            for v in o.values():
                rec(v)

    rec(d)
    # if len(candidate) == 1:
    #     return candidate[0]
    return candidate

def calculate_camera(lat, lng, d_lat=0.1, d_lng=0.1):
    EARTH_M_PER_DEG = 111320
    RAD = math.pi / 180
    c_lat = lat + d_lat / 2
    c_lng = lng + d_lng / 2
    rng = max(
        d_lat * EARTH_M_PER_DEG,
        d_lng * EARTH_M_PER_DEG * math.cos(c_lat * RAD),
    )
    rng = math.floor(rng + 0.5)

    return c_lat, c_lng, rng

def generate_random_session_token():
    return "".join(random.choices(string.ascii_letters + string.digits, k=23))
def generate_random_number(n):
    return random.randint(10,n)
def get_browser_session(init=None):
    s = Session(impersonate="chrome146")
    if init:
        s.get(init)
        time.sleep(2)
    return s
async def get_browser_asyncsession(init=None):
    s = AsyncSession(impersonate="chrome146")
    if init:
        await s.get(init)
        time.sleep(2)
    return s

def encode_plus_code(lat: float, lng: float, digits: int = 10) -> str:
        """Global Open Location Code. digits=10 -> 'XXXXXXXX+XX', digits=11 -> 'XXXXXXXX+XXX'."""
        _OLC = "23456789CFGHJMPQRVWX"
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

def get_default_centroid():
    sess = get_browser_session()
    base = sess.get("https://www.google.com/maps/")
    default = re.search(re.compile(r"/staticmap.*center=([-0-9.]+)(?:%2C|,)([-0-9.]+).*zoom=([0-9.]+)"), base.text)
    if default:
        lat = float(default.group(1))
        lng = float(default.group(2))
        zoom = float(default.group(3))
        return (lat, lng, zoom)
    else:
        # jakarta
        return (-6.3275008, 106.954752, 15.0)
    
def get_bgkey(fid, place_id, pagination=""):
    args = ["node", "mapsfiacore/scripts/bgkey.js", "--place", fid, place_id]
    if pagination:
        args.append(pagination)
    r = subprocess.run(args, capture_output=True, text=True,
                       cwd=".")
    if r.returncode:
        raise RuntimeError(r.stderr.strip())
    return r.stdout.strip()

def gen_bgkey(FID, PLACE_ID, pagination_token="", tries=8):
    for _ in range(tries):
        try:
            return get_bgkey(FID, PLACE_ID, pagination_token)
        except RuntimeError:
            pass
    raise RuntimeError("could not generate x-maps-bgkey")

def normalize_raw_response(response:Union[str, Response])->list:
    resp = []
    text = response.text if isinstance(response, Response) else response
    try:
        if text.endswith('/*""*/'):
            resp = text.replace('/*""*/','')
            d = json.loads(resp)
            text = d["d"]
        resp = text.replace(")]}'\n", "")
        resp = json.loads(resp)
    except Exception as e:
        print(f"{text}: Failed normalize the response: {e}")
    return resp
def normalize_search_raw_response(response:Union[str, Response]):
    if isinstance(response, Response):
        text = response.text
    else:
        text = response

    resp = text.replace('/*""*/','')
    d = json.loads(resp)
    text = d["d"]
    resp = text.replace(")]}'\n", "")
    resp = json.loads(resp)
    print(json.dumps(resp))
    next_u = d["u"]
    return {"response": resp, "next": next_u}


def get_candidate_from_data(data:list, iter_count=1):
    c = data
    state = 0
    while state < iter_count:
        candidates = [(index, len(i) if isinstance(i, list) else 0) for index, i in enumerate(c)]
        candidate = sorted(candidates, key=lambda x: x[1], reverse=True)[0]
        c = c[candidate[0]]
        state += 1
    return c

def generate_batchexecute_freq(payload:list, rpcid=""):
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