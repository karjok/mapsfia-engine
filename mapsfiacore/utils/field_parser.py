from mapsfiacore.models.models import User
from mapsfiacore.models.models import Photo, Video
from mapsfiacore.models.models import Aspect, AspectOption
from mapsfiacore.models.models import Rating, Review
from mapsfiacore.models.models import Suggestion
from mapsfiacore.models.models import (
    Place, Website, Phone, Accessibility,
    OpeningHours, OpeningHoursStatus, AddressComponents, StreetView, Owner,
)
from mapsfiacore.models.models import (
    PlaceReview, PlaceReviewOverview, PlaceReviewPhoto,
    PlaceReviewUserProfile, PlaceReviewAspectOption,
    PlaceReviewAspect, PhotoUrls
)
from mapsfiacore.utils import utils
from mapsfiacore.utils import vars
from datetime import datetime

from typing import Optional
import json
import re

# Canonical English weekday names keyed by Google's ISO-style day index
# (1=Monday .. 7=Sunday). The response's `day` string is localized to `hl`, so
# this numeric mapping is the only language-independent way to name the day.
WEEKDAY_BY_INDEX = {
    1: "Monday", 2: "Tuesday", 3: "Wednesday", 4: "Thursday",
    5: "Friday", 6: "Saturday", 7: "Sunday",
}
WEEKDAYS = tuple(WEEKDAY_BY_INDEX.values())

# Google's numeric open/closed status codes are language independent (observed
# across en/id responses). The display text ("Open"/"Buka") is localized.
STATUS_OPEN_CODES = frozenset({1})
STATUS_CLOSED_CODES = frozenset({4, 6})


def _is_num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)

def _dig(node, *path, default=None):
    """Walk a nested list by integer indices; return ``default`` on any miss."""
    for key in path:
        try:
            node = node[key]
        except (IndexError, KeyError, TypeError):
            return default
        if node is None:
            return default
    return node

def parse_user_field(data:list) -> Optional[User]:

    user_filed = utils.scan_signature(data, *vars.AUTHOR_SIGN)
    if not user_filed:
        return None
    data = user_filed[0]
    user_data = {
            "name": data[0],
            "id": int(data[3]),
            "review_count": data[5],
            "photo_count": data[6],
            "rating_count": data[9],
            "local_guide_level": data[8][1],
            "profile_picture": _generate_photo_urls(data[1]),
            "photos_contributions_url": data[2][0],
            "contributions_url": data[2][0],
        }
    user = User(**user_data)
    return user
def parse_place_thumbnail_field(data:list) -> list[Photo]:
    photos = []
    if isinstance(data, list):
        for img in data:
            photos.append(parse_photo_filed(img))
    return photos

def parse_video_field(data:list):
    if len(data) not in [32, 44]:
        return None
    try:
        caption = data[21][3][5][0]
    except:
        caption = None
    try:
        video_source = data[21][6][5][2]
        if video_source:
            video_source = video_source.split("_")[1]
    except:
        video_source = None

    try:
        date = data[21][6][8]
        dy = date[0]
        dm = date[1]
        dd = date[2]
        try:
            date_relative = data[21][6][8][8][0]
            
        except:
            date_relative = None
    except:
        dd = None
        dm = None
        dy = None
        date_relative = None
        dmy = None
    if dd and dm and dy:
        dmy = f"{dd:02d}/{dm:02d}/{dy}"
    else:
        dmy = None

    video_thumb_url = data[6][0] if utils.has_index(data, 6) and isinstance(data[6], list) else None
    video_urls = data[26][1]
    res = max([i[0] for i in video_urls if i[0]])
    video_url = video_urls[-1][3].split("=")[0] + f"=m{res}"
    video_data = {
        "video_id": data[0],
        "video_thumb_url": video_thumb_url,
        "video_url": video_url,
        "video_width": data[8][2][0],
        "video_hight": data[8][2][1],
        "video_longitude": data[8][0][1],
        "video_latitude": data[8][0][2],
        "video_year": dy,
        "video_month": dm,
        "video_day": dd,
        "video_date": dmy,
        "video_relative_time": date_relative,
        "video_caption": caption,
        "video_source": video_source
    }
    video = Video(**video_data)
    return video
    
def parse_photo_filed(data:list) -> Optional[Photo]:
    if len(data) not in [32, 44]:
        return None
    try:
        caption = data[21][3][5][0]
    except:
        caption = None
    try:
        photo_source = data[21][6][5][2]
        if photo_source:
            photo_source = photo_source.split("gmm_")[1]
    except:
        photo_source = None

    try:
        date = data[21][6][8]
        dy = date[0]
        dm = date[1]
        dd = date[2]
        try:
            date_relative = data[21][6][8][8][0]
        except:
            date_relative = None
    except:
        dd = None
        dm = None
        dy = None
        date_relative = None
        dmy = None
    if dd and dm and dy:
        dmy = f"{dd:02d}/{dm:02d}/{dy}"
    else:
        dmy = None
    photo_url = data[6][0] if utils.has_index(data, 6) and isinstance(data[6], list) else ""
    photo_urls = _generate_photo_urls(photo_url)
    photo_data = {
        "photo_id": data[0],
        "photo_url": photo_urls,
        "photo_width": data[8][2][0],
        "photo_hight": data[8][2][1],
        "photo_longitude": data[8][0][1],
        "photo_latitude": data[8][0][2],
        "photo_year": dy,
        "photo_month": dm,
        "photo_day": dd,
        "photo_date": dmy,
        "photo_relative_time": date_relative,
        "photo_caption": caption,
        "photo_source": photo_source
    }
    photo = Photo(**photo_data)
    return photo

def parse_medias(data:list):
    medias = []
    if isinstance(data, list):
        for media in data:
            if media[20]  and isinstance(media[20], str) and media[20].lower() == "video":
                media_data = parse_video_field(media)
                medias.append(media_data)
            elif media[20] and isinstance(media[20], str) and media[20].lower() in ["photo", "foto", "streetview"]:
                media_data = parse_photo_filed(media)
                medias.append(media_data)
    return medias

def _all_strings(node):
    """Yield every string in a nested list/tree."""
    if isinstance(node, str):
        yield node
    elif isinstance(node, list):
        for item in node:
            yield from _all_strings(item)

def _generate_photo_urls(raw_url) -> PhotoUrls:
    if not "https://" in raw_url:
        return None
    url = re.sub(r"=.*", "", raw_url) + "=k-no"
    urls = {
        "thumb": url,
        "hd": url.replace("=k-no","=s1280-k-no"),
        "fhd": url.replace("=k-no","=s1920-k-no"),
        "uhd": url.replace("=k-no","=s3840-k-no")
    }
    urls = PhotoUrls(**urls)
    return urls

def _parse_opening_hours(block) -> tuple:
    """Parse ``data[203]`` into ``(list[OpeningHours], OpeningHoursStatus|None)``.

    Shape: ``[ weekly_days, current_status, ... ]`` where each weekly day is
    ``[day_name, day_num, [Y,M,D], [[label, [[open_min],[close_min]]], ...], ...]``.
    Google is inconsistent about this block (sometimes null, sometimes only the
    current day), so every step is defensive.
    """
    if not isinstance(block, list):
        return [], None

    days = []
    weekly = block[0] if block and isinstance(block[0], list) else []
    for entry in weekly:
        if not isinstance(entry, list) or not entry:
            continue
        day_name = entry[0] if isinstance(entry[0], str) else None
        day_index = entry[1] if len(entry) > 1 and isinstance(entry[1], int) else None
        date = None
        d = _dig(entry, 2)
        if isinstance(d, list) and len(d) == 3 and all(_is_num(x) for x in d):
            date = f"{int(d[0]):04d}-{int(d[1]):02d}-{int(d[2]):02d}"
        intervals = []
        label = None
        has_empty_range = False
        has_hours_entry = False
        hours_entries = entry[3] if len(entry) > 3 and isinstance(entry[3], list) else []
        for h in hours_entries:
            text = _dig(h, 0)
            if isinstance(text, str) and label is None:
                label = text
            has_hours_entry = True
            open_raw = _dig(h, 1, 0)
            close_raw = _dig(h, 1, 1)
            # A present entry with both ranges empty means "Open 24 hours"
            # (language independent). A missing entry means closed for the day.
            if isinstance(open_raw, list) or isinstance(close_raw, list):
                opening = _dig(open_raw, 0)
                closing = _dig(close_raw, 0)
                if _is_num(opening) or _is_num(closing):
                    intervals.append((int(opening) if _is_num(opening) else None,
                                      int(closing) if _is_num(closing) else None))
                else:
                    has_empty_range = True
        is_24h = has_empty_range and not intervals
        # Derive open/closed from numbers, never from the localized label.
        if not has_hours_entry:
            closed = True
        elif intervals:
            closed = False
        else:
            # No numeric intervals: only 24h or a localized "closed" label.
            closed = not is_24h
        days.append(OpeningHours(day=day_name, day_index=day_index,
                                 weekday=WEEKDAY_BY_INDEX.get(day_index),
                                 date=date, label=label, intervals=intervals,
                                 closed=closed, is_24h=is_24h))

    status = None
    cur = _dig(block, 1)
    if isinstance(cur, list) and cur:
        status_text = _dig(cur, 4, 0) if isinstance(_dig(cur, 4), list) else None
        if not isinstance(status_text, str):
            status_text = _dig(cur, 8, 0) if isinstance(_dig(cur, 8), list) else None
        status_code = cur[2] if len(cur) > 2 and isinstance(cur[2], int) else None
        is_open = None
        if status_code in STATUS_OPEN_CODES:
            is_open = True
        elif status_code in STATUS_CLOSED_CODES:
            is_open = False
        state = None
        if isinstance(status_text, str):
            # localized first word before the separator; kept for display only
            state = re.split(r"[\u00b7\u00a0]", status_text)[0].strip() or None
        if status_text or state or is_open is not None:
            status = OpeningHoursStatus(is_open=is_open, state=state, label=status_text)
    return days, status


def _parse_address_components(data) -> AddressComponents:
    """Parse ``data[183]``: scan sub-lists for the flat component array.

    The flat array looks like ``[neighborhood, street, street, city, postal,
    province, country]`` (Indonesian layout) and lives at a varying sub-index
    (``[1]`` in detail records, elsewhere in search records), so we search for
    the sub-list that actually matches the shape instead of assuming a slot.
    """
    comp = AddressComponents()
    block = data[183] if len(data) > 183 and isinstance(data[183], list) else None
    if not block:
        return comp

    flat = None
    for candidate in block:
        if (isinstance(candidate, list) and len(candidate) >= 4
                and all(isinstance(x, str) for x in candidate)):
            flat = candidate
            break
    if flat is None:
        return comp

    values = flat
    last = values[-1]
    has_country = len(last) <= 3 and last.isupper()
    if has_country:
        comp.country_code = values[-1]
        comp.province = values[-2] if len(values) >= 2 else None
        comp.postal_code = values[-3] if len(values) >= 3 and re.fullmatch(r"\d{4,6}", values[-3]) else None
        comp.city = values[-4] if len(values) >= 4 else None
    else:
        comp.postal_code = values[-1] if re.fullmatch(r"\d{4,6}", values[-1]) else None
        comp.city = values[-2] if len(values) >= 2 else None
    comp.neighborhood = values[0] if values else None
    comp.street = values[1] if len(values) > 1 else None
    comp.lines = values
    return comp
def _parse_description(data:list):
    if utils.has_index(data, 0) and isinstance(data[0], list):
        description = data[0][0]
    elif utils.has_index(data, 2) and isinstance(data[2], list):
        description = data[2][0][0]
    else:
        return None
    return description


def _parse_street_view(data) -> Optional[StreetView]:
    block = data[37] if len(data) > 37 and isinstance(data[37], list) else None
    if not block:
        return None
    pano = _dig(block, 0, 0, 0)
    url = _dig(block, 0, 0, 6, 0)
    lat = _dig(block, 0, 0, 8, 0, 2)
    lng = _dig(block, 0, 0, 8, 0, 1)
    if not isinstance(pano, str):
        return None
    return StreetView(
        pano_id=pano,
        thumbnail_url=url if isinstance(url, str) else None,
        lat=lat if _is_num(lat) else None,
        lng=lng if _is_num(lng) else None,
    )


def _parse_owner(data) -> Optional[Owner]:
    block = data[57] if len(data) > 57 and isinstance(data[57], list) else None
    if not block:
        return None
    label = block[1] if len(block) > 1 and isinstance(block[1], str) else None
    owner_id = block[8] if len(block) > 8 and isinstance(block[8], str) else None
    if not label and not owner_id:
        return None
    return Owner(label=label, owner_id=owner_id)


def _parse_languages(data) -> list:
    langs = []
    for i in (112, 113):
        v = data[i] if len(data) > i else None
        if isinstance(v, str) and v not in langs:
            langs.append(v)
    return langs


def _parse_type_key(data):
    """Best-effort place-type key from the ``data[88]`` block.

    The block shifts between responses: the type string can be at index 1
    (place detail) or the type codes live at 3/4 (search tiles). Scan the
    block for the first string that is not the place name.
    """
    block = data[88] if len(data) > 88 else None
    if not isinstance(block, list):
        return None
    name = data[11] if len(data) > 11 else None
    for item in block:
        if isinstance(item, str) and item.startswith("SearchResult.TYPE_"):
            return item
    for item in block:
        if isinstance(item, str) and item and item != name:
            return item
    return None

def parse_place_field(data:list):
    if len(data) not in [260, 177]:
        raise ValueError(f'invalid place data format: {json.dumps(data)}')
    place_id = data[0]
    fid = data[10]
    rating = data[4][7] if data[4] else None
    review_count = data[4][8] if (
        isinstance(data[4], list) and len(data[4]) > 8
        and isinstance(data[4][8], (int, float)) and not isinstance(data[4][8], bool)
    ) else None
    if review_count is not None:
        review_count = int(review_count)
    if review_count is None:
        # Fallback: some shapes carry a "<n> reviews" label at data[4][3][1]
        # instead of (or alongside) the raw count at data[4][8].
        reviews_label = None
        if isinstance(data[4], list) and len(data[4]) > 3 and isinstance(data[4][3], list) and len(data[4][3]) > 1:
            reviews_label = data[4][3][1]
        if isinstance(reviews_label, str):
            match = re.match(r"\s*([\d.,]+)\s*([KkMm])?", reviews_label)
            if match:
                number = float(match.group(1).replace(",", ""))
                suffix = (match.group(2) or "").upper()
                factor = 1_000 if suffix == "K" else 1_000_000 if suffix == "M" else 1
                review_count = int(number * factor)
    website = parse_web_field(data[7])
    name = data[11]
    place_type_labels:list = data[13]
    full_addr = data[18]
    lat, lng = data[9][-2:] if data[9] else [None, None]
    timezone = data[30]
    addr = data[39]
    is_claimed = True if data[49] is None else False
    plus_code = utils._encode_plus_code(lat, lng) if lat and lng else None
    maps_url = f"https://www.google.com/maps?ftid={fid}"
    place_type_id = data[76]
    place_type_key = _parse_type_key(data)
    kgmid = data[89]
    media_filters = data[171][0] if utils.has_index(data, 171) and isinstance(data[171], list) else []
    media_filters = [{"filter_id": i[0], "filter_label": i[2]} for i in media_filters]
    accessibilities = parse_accessibility_field(data[100][1][0]) if isinstance(data[100], list) and len(data[100]) == 2 else []
    description = _parse_description(data[154] if utils.has_index(data, 154) and isinstance(data[54], list) else  data[44] if utils.has_index(data, 44) and isinstance(data[44], list) else [])
    phones = parse_phone_field(data[178][0]) if utils.has_index(data, 178) and isinstance(data[178], list) else None
    thumb_img = parse_place_thumbnail_field(data[72][0]) if utils.has_index(data,72) and isinstance(data[72], list) else None
    medias = parse_medias(data[51][0]) if utils.has_index(data, 52) and isinstance(data[51], list) else None


    # --- extended / best-effort fields (shape varies between responses) ----
    address_components = _parse_address_components(data)
    opening_hours, opening_hours_status = _parse_opening_hours(data[203]) if utils.has_index(data, 203) else (None, None)
    street_view = _parse_street_view(data)
    owner = _parse_owner(data)
    languages = _parse_languages(data)
    precise = _dig(data, 208, 0)
    precise_lat = precise[2] if isinstance(precise, list) and len(precise) > 2 and _is_num(precise[2]) else None
    precise_lng = precise[3] if isinstance(precise, list) and len(precise) > 3 and _is_num(precise[3]) else None

    # place_id / kgmid can also be recovered from the [227] tuple when the
    # primary slots are empty, which happens on skeleton search records.
    tuple_block = _dig(data, 227, 0)
    if not place_id and isinstance(tuple_block, list) and len(tuple_block) > 4 and isinstance(tuple_block[4], str):
        place_id = tuple_block[4]
    if not kgmid and isinstance(tuple_block, list) and len(tuple_block) > 3 and isinstance(tuple_block[3], str):
        kgmid = tuple_block[3]

    reviews_url = None
    if isinstance(data[4], list) and len(data[4]) > 3 and isinstance(data[4][3], list):
        candidate = _dig(data, 4, 3, 0)
        if isinstance(candidate, str) and "reviews" in candidate:
            reviews_url = candidate

    category_ids = []
    for s in _all_strings(data):
        if s.startswith("gcid:") and s.split(":", 1)[1] not in category_ids:
            category_ids.append(s.split(":", 1)[1])

    missing_fields = [s for s in ("Add hours", "Add phone number", "Add website")
                      if s in set(_all_strings(data))]
    reviews = utils.scan_signature(data, [str, list, ..., list, str], ln=6)
    reviews = parse_place_review_front_page(reviews)
    place_data = {
        "place_id": place_id,
        "fid": fid,
        "rating": rating,
        "review_count": review_count,
        "website": website,
        "name": name,
        "place_type_labels": place_type_labels,
        "full_address": full_addr,
        "address": addr,
        "lat": lat,
        "lng": lng,
        "timezone": timezone,
        "is_claimed": is_claimed,
        "plus_code": plus_code,
        "maps_url": maps_url,
        "place_type_id": place_type_id,
        "place_type_key": place_type_key,
        "kgmid": kgmid,
        "accessibilities": accessibilities,
        "description": description,
        "phone": phones,
        "banner": thumb_img,
        "review_overviews": reviews,
        "medias": medias,
        "media_filters": media_filters,
        "neighborhood": address_components.neighborhood,
        "city": address_components.city,
        "province": address_components.province,
        "postal_code": address_components.postal_code,
        "country_code": address_components.country_code,
        "address_components": address_components,
        "opening_hours": opening_hours,
        "opening_hours_status": opening_hours_status,
        "street_view": street_view,
        "owner": owner,
        "languages": languages,
        "precise_lat": precise_lat,
        "precise_lng": precise_lng,
        "category_ids": category_ids,
        "reviews_url": reviews_url,
        "missing_fields": missing_fields,
    }

    return Place(**place_data)

def parse_phone_field(data:list):
    local_fmt = data[0]
    global_fmt = data[1][1][0]
    uri = data[5][0]
    phone_data = {"local_fmt": local_fmt, "global_fmt": global_fmt, "uri_fmt": uri}
    return Phone(**phone_data)

def parse_web_field(data:list):
    try:
        website = {
            "url": data[0],
            "domain": data[1]
        }
        website = Website(**website)
    except:
        website = None
    return website

def parse_accessibility_field(data:list) -> list[Accessibility]:
    field = data[2]
    access_lists = []
    for access in field:
        label = access[1]
        status = access[2][2][0]
        status_label = access[2][2][1]
        status = True if status else False
        acc_data = {"accessibility": label, "status": status, "label": status_label}
        acc_data = Accessibility(**acc_data)
        access_lists.append(acc_data)
    return access_lists

def parse_top_review_keyword_field(data:list):
    top_keywords = []
    for keyword in data:
        kw = keyword[1]
        kw_count = keyword[3][4]
        top_keywords.append({"keyword": kw, "count": kw_count})
    return top_keywords


def parse_aspect_filed(data:list) -> Optional[Aspect]:
    aspect = {
        "aspect_key": data[0][0],
        "aspect_question": data[1],
        "aspect_options": [],
        "aspect_title": data[5],
        "aspect_rating": None,
    }
    # Options
    if data[2] is not None:
        for option in data[2][0]:
            options = {
                "option_key": option[0][0],
                "option_label": option[1],
                "option_score": option[2],
                "option_description": option[4]
            }
            aspect["aspect_options"].append(AspectOption(**options))
    # Rating untuk FOOD/SERVICE/ATMOSPHERE
    try:
        aspect["aspect_rating"] = data[11][0]
    except:
        pass

    aspect_data = Aspect(**aspect)

    return aspect_data
def parse_rating_field_from_place(data:list):
    if not len(data) == 14:
        raise ValueError("review field (place[175]) must exactly 14")
    review_field = data[9]
    if review_field:
        can = utils.get_candidate_from_data(review_field,3)[0]
        user = parse_user_field(can[1][4])
        photos = []
        try:
            imgcan = can[2]
            if imgcan[2]:
                for photo in imgcan[2]:
                    photos.append(parse_photo_filed(photo[1]))
        except:
            pass
        # print(json.dumps(data))
def parse_rating_field(data:list):
    try:
        langcode = re.compile(r"[a-z]+")
        langlabel = re.compile(r"[A-Z].")

        langs = data[14]
        code = [i for i in langs if isinstance(i, str) and re.match(langcode, i)]
        label = [i for i in langs if isinstance(i, str) and re.match(langlabel, i)]

        strings = data[15]

        string = [i[0] for i in strings]
        av_langs = []
        av_strings = []
        for cd, txt in zip(code, string):
            av_strings.append({
                "lang_code": cd,
                "string": txt
            })
            av_langs.append({
                "code": cd,
            })
    except Exception as e:
        av_strings = None
        av_langs = None
    try:
        photos = data[2]
        photos = [parse_photo_filed(i[1]) for i in photos]
    except:
        photos = []
    try:
        aspects = data[6]
        if not aspects:
            aspects = []
        aspects = [parse_aspect_filed(i) for i in aspects]
    except:
        aspects = []

    review_data = {
        "rating_count": data[0][0],
        "rating_media": photos,
        "rating_aspects": aspects,
        "rating_languages": av_langs,
        "rating_strings": av_strings
    }
    review_data = Rating(**review_data)
    return review_data

def parse_suggestion_field(data:list) -> Suggestion:
    # print(data)
    try:
        sug = data[13][0]
    except:
        sug = None
    try:
        addr = data[2][0]
    except:
        addr = None
    try:
        gmid = sug[10] if sug else None
    except:
        gmid = None
    try:
        code = data[7][2][0]
    except:
        code = None
    try:
        lat = sug[3][2] if sug else None
        lng = sug[3][3] if sug else None
    except:
        lat = None
        lng = None
    suggestion_data = {
        "fid": sug[0] if sug else None,
        "gmid": gmid,
        "label": sug[1] if sug else None,
        "name": data[0][0],
        "code": code,
        "lat": lat,
        "lng": lng,
        "address": addr
    }
    sugg_data = Suggestion(**suggestion_data)
    return sugg_data

def parse_place_overview_field(data:list) -> PlaceReviewOverview:
    if len(data) != 6:
        return None
        # raise ValueError(f"Invalid review overview field: {json.dumps(data)}. Overview field must have 6 length.")
    name = data[0]
    address = data[1]
    rating = data[2]
    total_review = data[3]
    review_overviews = data[5]
    ovs = []
    for kw in review_overviews:
        if kw:
            i = kw[0]
            k = kw[1]
            c = kw[2]
            ovs.append({"keyword": k, "count": c, "filter_id": i})
    place_ov = {
        "name": name,
        "address": address,
        "rating": rating,
        "review_count": total_review,
        "keywords": ovs
    }
    place_ov_data = PlaceReviewOverview(**place_ov)
    return place_ov_data

def parse_place_reviews(data:list) -> list[PlaceReview]:
    if len(data) != 7:
        raise ValueError(f"Invalid review filed: {json.dumps(data)}. Review field must have 7 length")
    place_reviews = data[2] if data[2] else []
    reviews = []
    for rev in place_reviews:
        if len(rev) == 49:
            review_id = rev[5]
            time_relative = rev[2][0]
            timestamp = int(rev[2][2])
            user = rev[3]
            user_name = user[0]
            user_image = user[1]
            user_contribution_url = user[2] or ""
            user_google_id = re.search(r"\d+", user_contribution_url)
            user_google_id = user_google_id.group(0) if user_google_id else None
            user_review_count = int(user[3]) if user[3] else 0
            user_photo_count = int(user[4]) if user[4] else 0
            reviewer = {
                    "user_google_id": int(user_google_id),
                    "user_name": user_name,
                    "user_image": _generate_photo_urls(user_image),
                    "user_contribution_url": user_contribution_url,
                    "user_review_count": user_review_count,
                    "user_photo_count": user_photo_count
                }
            reviewer = PlaceReviewUserProfile(**reviewer)
            photos = rev[14] if rev[14] and isinstance(rev[14], list) else []
            review_images = []
            for img in photos:
                img_url = img[0]
                img_caption = img[1]
                img_id = img[3]
                img_time_relative = img[6]
                photo_urls = _generate_photo_urls(img_url)
                photo = {
                    "photo_urls": photo_urls,
                    "photo_caption": img_caption,
                    "photo_id": img_id,
                    "photo_time_relative": img_time_relative
                }
                photo = PlaceReviewPhoto(**photo)
                review_images.append(photo) 

            review_string = rev[27]
            aspects = rev[30] if rev[30] and isinstance(rev[30], list) else []
            aspect_review = []
            for aspect in aspects:
                key = aspect[0][0]
                label = aspect[5]
                point = aspect[11][0] if aspect[11] else 0
                options = aspect[2]
                option = None
                if options:
                    option_key = options[0][0][0][0]
                    option_label = options[0][0][1]
                    option = {
                        "option_key": option_key,
                        "option_label": option_label
                    }
                    option = PlaceReviewAspectOption(**option)
                aspect_data = {
                    "aspect_key": key,
                    "aspect_label": label,
                    "aspect_point": point,
                    "aspect_option": option
                }
                aspect_data = PlaceReviewAspect(**aspect_data)
                aspect_review.append(aspect_data)
            rating_star = float(rev[45])
            review_data = {
                "review_id": review_id,
                "review_timestamp": timestamp,
                "review_time_relative": time_relative,
                "review_rating": rating_star,
                "review_user": reviewer,
                "review_media": review_images,
                "review_string": review_string
            }
            review_data = PlaceReview(**review_data)
            reviews.append(review_data)
    return reviews
def parse_place_review_front_page(data:list):
    # print(json.dumps(data))
    def _parse_medias(medias):
        
        if utils.has_index(medias, 26) and isinstance(medias[26], list):
            md = parse_video_field(medias)
        else:
            md = parse_photo_filed(medias)
        return md
    
    seens = []
    reviews = []
    for review in data:
        if review[0] not in seens:
            seens.append(review[0])
            review_id = review[0]
            review_timestamp = review[1][2]
            review_time_relative = review[1][6]
            review_rating = review[2][0][0] if isinstance(review[2][0], list) else None
            review_user = parse_user_field(review[1][4])
            media_list = utils.scan_signature(review, [str, int, int,..., list], ln=44)
            medias = [_parse_medias(m) for m in media_list]
            review_string = review[2][15][0][0] if utils.has_index(review[2], 15) and isinstance(review[2][15], list) else None           # reviewer = PlaceReviewUserProfile(**reviewer)  
            rating = Rating(
                rating_count=review_rating,
                rating_media=medias,
                rating_strings=review_string
                )
            review_data = Review(
                id=review_id,
                rating=rating,
                user=review_user,
                timestamp=review_timestamp,
                relative_time=review_time_relative
            )
            reviews.append(review_data)
    return reviews