import asyncio
from mapsfiacore.utils.utils import get_candidate_from_data
from mapsfiacore.utils import field_parser
import json
from typing import Literal, Optional
from mapsfiacore.utils import batchexecute

def get_place_review_overview(fid:str, hl:str="id", gl:str="id"):
    rpcid = "nz5PNe"
    url = "https://www.google.com/wizrpcui/_/WizRpcUi/data/batchexecute"
    params = {
        'rpcids': rpcid,
        'hl': hl,
        'gl': gl or hl,
        'authuser': '0',
    }
    rpc = batchexecute.get_place_review_overview_rpc(fid)
    freq = batchexecute.get_freq(rpc, rpcid=rpcid)
    data = asyncio.run(batchexecute.fetch_batchexecute(url, freq, params=params))
    can = get_candidate_from_data(data)
    try:
        ov_data = json.loads(can[2])
        parsed = field_parser.parse_place_overview_field(ov_data)
        return parsed
    except Exception as e:
        print(e)
        pass
async def get_place_reviews(fid:str, hl:str="id", gl:str="id", perpage:int=10, pagination_token=None, sess=None, sort_by:Optional[Literal["most_relevant", "newest", "highest_rating", "lowest_rating"]]=None)->dict:
    sort_key = {
        "most_relevant": 1,
        "newest": 2,
        "highest_rating": 3,
        "lowest_rating": 4
    }
    rpcid = "s7jv5e"
    params = {
        'rpcids': rpcid,
        'hl': hl,
        'gl': gl or hl,
        'authuser': '0',
    }
    sort = sort_key[sort_by] if sort_by else 1
    payload = [None,sort,None,None,None,None,None,None,None,perpage,None,[fid],None,None,None,None,[1,1,None,[[3],[4],[5],[6],[7]]],None,None,pagination_token,None,None,None,0]
    f_req = batchexecute.get_freq(payload, rpcid=rpcid)
    url = "https://www.google.com/wizrpcui/_/WizRpcUi/data/batchexecute"
    data = await batchexecute.fetch_batchexecute(url, freq=f_req, params=params, sess=sess)
    can = get_candidate_from_data(data)
    rev_data = json.loads(can[2])
    print(json.dumps(rev_data))
    pagination = rev_data[-1]
    reviews = field_parser.parse_place_reviews(rev_data)
    result = {"reviews": reviews, "np": pagination, "c": len(reviews)}
    return result
