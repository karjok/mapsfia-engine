import time
import random
import string
from mapsfiacore.utils import utils
from mapsfiacore.utils.field_parser import parse_suggestion_field
from mapsfiacore.models.suggestion import Suggestion, Suggestions
import re


def build_suggestion_pb(sess, query=None):
    _SUGGEST_PB = (
        '!2i12!4m12!1m3!1d27168336.765021317!2d-95.677068!3d37.06250000000001'
        '!2m3!1f0!2f0!3f0!3m2!1i1280!2i800!4f13.1!7i20!10b1!12m25!1m5!18b1!30b1'
        '!31m1!1b1!34e1!2m4!5m1!6e2!20e3!39b1!10b1!12b1!13b1!16b1!17m1!3e1'
        '!20m3!5e2!6b1!14b1!46m1!1b0!96b1!99b1!19m4!2m3!1i360!2i120!4i8'
        '!20m57!2m2!1i203!2i100!3m2!2i4!5b1!6m6!1m2!1i86!2i86!1m2!1i408!2i240'
        '!7m33!1m3!1e1!2b0!3e3!1m3!1e2!2b1!3e2!1m3!1e2!2b0!3e3!1m3!1e8!2b0'
        '!3e3!1m3!1e10!2b0!3e3!1m3!1e10!2b1!3e2!1m3!1e10!2b0!3e4!1m3!1e9!2b1'
        '!3e2!2b1!9b0!15m8!1m7!1m2!1m1!1e2!2m2!1i195!2i195!3i20!22m3'
        '!1s0--7apyNAaSq4-EP64axsQ4!7e81!17s0--7apyNAaSq4-EP64axsQ4:93!23m2'
        '!4b1!10b1!24m109!1m27!13m9!2b1!3b1!4b1!6i1!8b1!9b1!14b1!20b1!25b1'
        '!18m16!3b1!4b1!5b1!6b1!9b1!13b1!14b1!17b1!20b1!21b1!22b1!32b1!33m1'
        '!1b1!34b1!36e2!10m1!8e3!11m1!3e1!17b1!20m2!1e3!1e6!24b1!25b1!26b1'
        '!27b1!29b1!30m1!2b1!36b1!37b1!39m3!2m2!2i1!3i1!43b1!52b1!54m1!1b1'
        '!55b1!56m1!1b1!61m2!1m1!1e1!65m5!3m4!1m3!1m2!1i224!2i298!72m22!1m8'
        '!2b1!5b1!7b1!12m4!1b1!2b1!4m1!1e1!4b1!8m10!1m6!4m1!1e1!4m1!1e3!4m1'
        '!1e4!3sother_user_google_review_posts__and__hotel_and_vr_partner_review_posts'
        '!6m1!1e1!9b1!89b1!90m2!1m1!1e2!98m3!1b1!2b1!3b1!103b1!113b1!114m3!1b1'
        '!2m1!1b1!117b1!122m1!1b1!126b1!127b1!128m1!1b1!26m4!2m3!1i80!2i92!4i8'
        '!34m19!2b1!3b1!4b1!6b1!8m6!1b1!3b1!4b1!5b1!6b1!7b1!9b1!12b1!14b1!20b1'
        '!23b1!25b1!26b1!31b1!37m1!1e81!47m0!49m10!3b1!6m2!1b1!2b1!7m2!1e3!2b1'
        '!8b1!9b1!10e2!61b1!67m5!7b1!10b1!14b1!15m1!1b0!69i797!77b1'
    )
    pb = _SUGGEST_PB.replace("!2i12!", "!2i1!", 1)
    if query:
        pb = pb.replace("!2i1!", "!2i%d!" % len(query), 1)
    pb = re.sub(r"(!22m3!1s)[^!]+", r"\g<1>" + sess, pb)
    pb = re.sub(r"(!17s)[^!]+", r"\g<1>" + sess + "%3A1", pb)
    return pb

def build_suggestion_params(query, pb=None, hl="id", gl="id"):
    ts = int(time.time() * 1000)
    sess = "".join(random.choices(string.ascii_letters + string.digits, k=26))
    pb = pb if pb else build_suggestion_pb(sess, query=query)
    params = {
                "tbm": "map",
                "gs_ri": "maps",
                "suggest": "p",
                "hl": hl,
                "gl": gl or hl,
                "psi": f"{sess}.{ts}.1",
                "q": query,
                "pb": pb,
                "authuser": 0,
                "ech": 1,
            }
    return params
def parse_suggestion_response(data:list) -> list[Suggestion]:
    suggestions = []
    for sug in data:
        sug_field = sug[22]
        sug_data = parse_suggestion_field(sug_field)
        suggestions.append(sug_data)
    return suggestions

def fetch_suggestion_response(query, hl="id", gl="id"):
    url = "https://www.google.com/s"
    params = build_suggestion_params(query, hl=hl, gl=gl)
    sess = utils.get_browser_session()
    response = sess.get(url, params=params)
    norm = utils.normalize_raw_response(response)
    return norm

def get_suggestions(query, hl="id", gl="id"):
    response = fetch_suggestion_response(query, hl=hl, gl=gl)
    suggestion_response_list = utils.get_candidate_from_data(response, 2)
    sugg_query = response[0][0]
    suggestions = parse_suggestion_response(suggestion_response_list)
    list_suggestions = Suggestions(query=sugg_query, sugestions=suggestions)
    return list_suggestions
    
if __name__ == "__main__":
    sugg = get_suggestions("bal", hl="id")
    print(sugg.to_json())