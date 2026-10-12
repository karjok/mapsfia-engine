from mapsfiacore.utils.batchexecute import get_freq, fetch_batchexecute
import asyncio
from mapsfiacore.utils.utils import get_browser_asyncsession
from mapsfiacore.utils.field_parser import parse_photo_filed, parse_video_field
import json
from typing import Literal, Optional

def parse_media_response(data:list):
    if len(data) != 14:
        raise ValueError(f"{json.dumps(data)}: Invalid media response data. media filed must have 14 items")
    pagination = data[5]
    medias = data[0] if data[0] else []
    medias_data = []
    for media in medias:
        if media[26]:
            file = parse_video_field(media)
        else:
            file = parse_photo_filed(media)
        medias_data.append(file)
    return {"p": pagination, "medias": medias_data, "c": len(medias_data)}


async def get_medias(fid, kgmid, place_id, pagination_token=None, perpage=10, filter_type="CgIgAQ==", sess=None, hl="id", gl="id"):
    sess = await get_browser_asyncsession("https://www.google.com/maps/")
    rpcids = "hspqX"
    params = {
        "hl": hl,
        "rpcids": rpcids
    }
    payload = [
        2, None, 
        [fid, None, None, None, None, None, None, None, 0, None, None, None, None, None, 
            [
                [None, None, None, kgmid]
            ]
        ], 
        None, [None, [203, 100], [None, perpage, pagination_token, None, 1], None, None, None, [[[1, 0, 3], [2, 1, 2], [2, 0, 3], [8, 0, 3], [10, 0, 3], [10, 1, 2], [10, 0, 4], [9, 1, 2]], 1], None, 0, None, None, None, None, None, [[[[[[2]]], [195, 195], 20]]]], 
        [place_id, None, None, None, None, None, 81, None, None, None, None, None, None, None, 16698], None, None, None, None, None, None, None, None, None, [[filter_type], 1, None, 1]]
    freq = get_freq(payload, rpcid=rpcids)
    resp = await fetch_batchexecute(
        url="https://www.google.com/maps/_/MapsWizUi/data/batchexecute",
        freq=freq,
        params=params,
        sess=sess
        )
    d = resp[0][2]
    d = json.loads(d)
    medias = parse_media_response(d)
    # print(json.dumps(d))
    return medias

def medias(fid, kgmid, place_id, filter_type:Optional[Literal["all", "newest", "video"]] = "all", sess=None, hl="id", gl="id", perpage=10):
    filters = {
        "all": "CgIgAQ==",
        "newest": "CgIgARICGAI=",
        "video": "CgIgARICCAQ="
    }
    filter_type = filters[filter_type]
    medias = asyncio.run(get_medias(fid, kgmid, place_id, filter_type=filter_type, sess=sess, hl=hl, gl=gl, perpage=perpage)
    )
    return medias

if __name__ == "__main__":
    pos = ("0x2e69f5cc097e35db:0x7302b729335a095b",
    "/g/121g1wcx",
    "ZHvKavrsG_j0juMP96LE6As")

    d = medias(*pos, filter_type="all")
    print(d)