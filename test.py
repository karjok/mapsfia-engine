from mapsfiacore.cores.get_review_2 import get_reviews
from mapsfiacore.cores.get_suggestions import get_suggestions
from mapsfiacore.cores.get_place import get_place_data
from mapsfiacore.cores.get_search import search 
from dataclasses import asdict
from mapsfiacore.utils.utils import get_bgkey, get_browser_session
from mapsfiacore.cores.get_geojson import Geojson
from mapsfiacore.cores.get_place_reviews import get_place_reviews, get_place_review_overview
import json, sys
import asyncio
from mapsfiacore.utils.batchexecute import get_freq, fetch_batchexecute

def test(q):
    s = get_suggestions(q).sugestions
    for n, i in enumerate(s, start=1):
        print(n, f"{i.name}")
    sel = input("Select: ")
    while not sel or not sel.isdigit():
        sel = input("Select: ")
    sel = int(sel)-1
    selected = s[sel]
    sess = get_browser_session(f"https://www.google.com/maps?ftid={selected.fid}")
    print(selected)
    # print(sess.cookies)
    # # place = get_place_data(selected.fid, selected.lat, selected.lng, gmid=selected.gmid, label=selected.label)
    # place = get_place_data(selected.fid, gmid=selected.gmid, label=selected.label, sess=sess)
    if (selected.fid and selected.lat and selected.lng):
        place = get_place_data(selected.fid, selected.lat, selected.lng, gmid=selected.gmid, label=selected.label)
    elif selected.fid and selected.gmid:
        place = get_place_data(selected.fid, gmid=selected.gmid, label=selected.label)
    else:
        place = search(selected.name)
    print(place)

def geo():
    G = Geojson()
    u = input("Maps URL: ")
    poly = G.get_geojson(url=u)
    json.dump(poly, open("poly.gejson","w"))
    print("done:"), poly["properties"]

def rev(fid=None, perpage=1):
    fid = fid or "0x2e69f7ff76b9ec33:0xae1cf5d8abdf9bbb"
    ov = get_place_review_overview(fid)
    d = asyncio.run(get_place_reviews(fid, perpage=perpage, sort_by="newest"))
    print(d)

def pbb():
    params = {
            'rpcids': "Ya3XAc",
            'hl': "id",
            'gl': "id",
            'authuser': '0',
        }
    pb = json.loads('[["0x2e6993a7c57572a1:0xf6d3ef41aaeb0847","Kopi Calf Jatiwarna",[[4816.247134199468,106.9240379,-6.3087699],null,[1024,768],13.1],[null,null,-6.3087699,106.9240379],null,null,null,null,null,null,null,null,null,null,[[null,null,null,"/g/11s5yrq318"]]],null,null,null,null,null,null,null,null,null,null,[null,[360,120,null,8]],[null,[203,100],[null,4,null,null,true],null,null,[[[86,86],[408,240]]],[[[1,false,3],[2,true,2],[2,false,3],[8,false,3],[10,false,3],[10,true,2],[10,false,4],[9,true,2]],true],null,false,null,null,null,null,null,[[[[2]],[195,195],20]]],["uRHIatzMFdGv4-EPtK7R6QY",null,null,null,null,null,81,null,null,null,null,null,null,null,10112],[[null,null,null,null,null,null,null,null,null,null,null,null,[null,true,true,true,null,1,null,true,true,null,null,null,null,true,null,null,null,null,null,true,null,null,null,null,true],null,null,null,null,[null,null,true,true,true,true,null,null,null,null,null,null,true,true,null,null,true,null,null,null,true,true,null,null,null,null,null,null,null,true,null,true,[true],true,null,2]],null,null,null,null,null,null,null,null,[null,null,null,null,null,null,null,3],[null,null,1],null,null,null,null,null,true,null,null,[[3,6]],null,null,null,true,true,true,true,null,true,[null,true],null,null,null,null,null,true,true,null,[null,[null,1,1]],null,null,null,true,null,null,null,null,null,null,null,null,true,null,[true],true,[true],null,null,null,null,[[1]],null,null,null,[null,null,[[[224,298]]]],null,null,null,null,null,null,[[null,true,null,null,true,null,true,null,null,null,null,[true,true,null,[1]]],null,null,true,null,null,null,[[null,null,null,[[1],[3],[4]]],null,"other_user_google_review_posts__and__hotel_and_vr_partner_review_posts",null,null,[1]],true],null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,true,[[2]],null,null,null,null,null,null,null,[true,true,true],null,null,null,null,true,null,null,null,null,null,null,null,null,null,true,[true,[true]],null,null,true,null,null,null,null,[true],null,null,null,true,true,[true]],null,null,null,null,null,[],[81],null,null,null,null,null,null,null,[null,null,true,null,null,[true,true],[3,true],null,true],null,null,null,[null,null,null,null,null,null,true,null,null,true,null,null,null,true,[false]],null,null,798]')
    f = get_freq(pb)
    print(f)
    g = asyncio.run(fetch_batchexecute("https://www.google.com/maps/_/MapsWizUi/data/batchexecute", freq=f, params=params))
if __name__ == "__main__":
    test(sys.argv[1])