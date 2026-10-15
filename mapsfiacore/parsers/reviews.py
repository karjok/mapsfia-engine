from mapsfiacore.utils import utils
from mapsfiacore.utils import field_parser
from mapsfiacore.utils import vars
from mapsfiacore.models.globals import PlaceReviewAspect, PlaceReviewAspectOption, PlaceReview
import json


def _parse_photo(data:list):
    return field_parser.parse_photo_filed(data)
def _parse_video(data:list):
    return field_parser.parse_video_field(data)

def _parse_media(data:list):
    medias = utils.scan_signature(data, *vars.MEDIA_SIGN)
    rev_medias = []
    for media in medias:
        if utils.has_index(media, 26) and isinstance(media[26], list):
            md = _parse_video(media)
        else:
            md = _parse_photo(media)
        rev_medias.append(md)
    return rev_medias

def _parse_aspects(data:list):
    data = utils.scan_signature(data, *vars.REVIEW_ASPECTS_SIGN)
    # print(json.dumps(data))
    aspects = []
    for aspect in data:
        key = aspect[0][0]
        question = aspect[1]
        label = aspect[5]
        point = aspect[11][0] if aspect[11] else 0
        options = aspect[2] or aspect[3]
        opts = []
        if options:
            for opt in options[0]:
                option_key = opt[0][0]
                option_label = opt[1]
                option = {
                    "option_key": option_key,
                    "option_label": option_label
                }
                opts.append(PlaceReviewAspectOption(**option))
        aspect_data = {
            "aspect_key": key,
            "aspect_question": question,
            "aspect_label": label,
            "aspect_point": point,
            "aspect_option": opts
        }
        aspect_data = PlaceReviewAspect(**aspect_data)
        aspects.append(aspect_data)
    return aspects


def review_parser(data:list, fid:str):
    reviews_data = utils.scan_signature(data, *vars.REVIEW_SIGN)
    # print(json.dumps(data), reviews_data)
    if not reviews_data:
        return []
    reviews = []
    for review in reviews_data:
        rev_id = review[0]
        rev_time_relative = review[1][6]
        rev_timestamp = int(review[1][2])
        rev_author = field_parser.parse_user_field(review)
        rev_likes = review[4][6][1][0][1] if utils.has_index(review[4], 6) else 0
        rev_rating = review[2][0][0]
        rev_langs = review[2][14] if utils.has_index(review[2], 14) and isinstance(review[2][14], list) else None
        rev_strings = review[2][15] if utils.has_index(review[2], 15) and isinstance(review[2][15], list) else None
        strings = [
            {
                "lang_code": rev_langs[i],
                "lang_label": rev_langs[i + 2],
                "string": rev_strings[i][0]
            }
            for i in range(min(len(rev_strings), len(rev_langs) // 2))
        ] if rev_langs and rev_strings else None

        rev_media = _parse_media(review)
        rev_aspetcs = _parse_aspects(review)
        review_data = {
                "fid": fid,
                "review_id": rev_id,
                "review_timestamp": rev_timestamp,
                "review_time_relative": rev_time_relative,
                "review_rating": rev_rating,
                "review_user": rev_author,
                "review_media": rev_media,
                "review_string": strings,
                "review_like_count": rev_likes,
                "review_aspects": rev_aspetcs
            }
        review_data = PlaceReview(**review_data)
        reviews.append(review_data)
    return reviews
        