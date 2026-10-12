from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Callable, TypeAlias


# ============================================================
# Generic JSON types
# ============================================================

JSONScalar: TypeAlias = str | int | float | bool | None
JSONValue: TypeAlias = JSONScalar | list["JSONValue"]


# ============================================================
# Small helpers
# ============================================================

def get(value: Any, index: int, default: Any = None) -> Any:
    if isinstance(value, list) and 0 <= index < len(value):
        return value[index]
    return default


def as_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def as_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def as_float(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value

    if value == 1:
        return True

    if value == 0:
        return False

    return None


def strings(value: Any) -> list[str]:
    """
    Recursively collect strings.

    This is deliberately structural traversal.
    No regex/pattern matching is used.
    """
    result: list[str] = []

    if isinstance(value, str):
        result.append(value)

    elif isinstance(value, list):
        for item in value:
            result.extend(strings(item))

    return result


def first_string(value: Any) -> str | None:
    values = strings(value)
    return values[0] if values else None


# ============================================================
# Core types
# ============================================================

@dataclass(slots=True)
class Coordinates:
    latitude: float | None = None
    longitude: float | None = None

    @classmethod
    def from_google(cls, value: Any) -> Coordinates | None:
        if not isinstance(value, list):
            return None

        # Known root representation:
        # [None, None, latitude, longitude]
        if len(value) >= 4:
            lat = as_float(value[2])
            lon = as_float(value[3])

            if lat is not None and lon is not None:
                return cls(
                    latitude=lat,
                    longitude=lon,
                )

        return None


@dataclass(slots=True)
class RatingInfo:
    rating: float | None = None
    rating_count: int | None = None
    histogram: list[int] = field(default_factory=list)

    @classmethod
    def from_field_4(cls, value: Any) -> RatingInfo | None:
        if not isinstance(value, list):
            return None

        # Field 4 contains a nested rating structure.
        #
        # In the supplied dataset the actual rating appears at
        # nested index 7.
        rating = None
        rating_count = None
        histogram: list[int] = []

        if len(value) > 7:
            rating = as_float(value[7])

        if len(value) > 8:
            histogram_value = value[8]

            if isinstance(histogram_value, list):
                histogram = [
                    x for x in histogram_value
                    if isinstance(x, int)
                ]

        # Fallback structural extraction for the count.
        # This does not use regex or string matching.
        for item in value:
            if isinstance(item, int) and item > 10:
                rating_count = item
                break

        return cls(
            rating=rating,
            rating_count=rating_count,
            histogram=histogram,
        )


@dataclass(slots=True)
class Address:
    display: str | None = None
    short: str | None = None
    street: str | None = None
    locality: str | None = None
    administrative_area: str | None = None
    postal_code: str | None = None
    region: str | None = None
    country_code: str | None = None
    components: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Website:
    url: str | None = None
    domain: str | None = None
    label: str | None = None


@dataclass(slots=True)
class PhoneNumber:
    raw: str | None = None
    international: str | None = None
    normalized: str | None = None
    uri: str | None = None


@dataclass(slots=True)
class PhoneInfo:
    primary: PhoneNumber | None = None
    numbers: list[PhoneNumber] = field(default_factory=list)


@dataclass(slots=True)
class Photo:
    url: str | None = None
    width: int | None = None
    height: int | None = None
    reference: str | None = None
    metadata: list[Any] = field(default_factory=list)


@dataclass(slots=True)
class Category:
    name: str
    id: str | None = None


@dataclass(slots=True)
class BusinessIdentifier:
    plus_code: str | None = None
    google_entity_id: str | None = None
    place_id: str | None = None
    cid: str | None = None
    numeric_id: str | None = None
    alternate_id: str | None = None


@dataclass(slots=True)
class OpeningPeriod:
    text: str | None = None
    open_hour: int | None = None
    open_minute: int | None = None
    close_hour: int | None = None
    close_minute: int | None = None


@dataclass(slots=True)
class OpeningDay:
    name: str | None = None
    day_of_week: int | None = None
    date: tuple[int, int, int] | None = None
    periods: list[OpeningPeriod] = field(default_factory=list)
    status: str | None = None


@dataclass(slots=True)
class OpeningHours:
    current_day: OpeningDay | None = None
    days: list[OpeningDay] = field(default_factory=list)
    raw: Any = None


@dataclass(slots=True)
class ReviewAuthor:
    name: str | None = None
    source: str | None = None
    profile_url: str | None = None
    rating: float | None = None


@dataclass(slots=True)
class Review:
    review_id: str | None = None
    author: ReviewAuthor | None = None
    rating: float | None = None
    text: str | None = None
    relative_time: str | None = None
    timestamp_ms: int | None = None
    language: str | None = None
    source: str | None = None
    review_url: str | None = None
    reply_url: str | None = None
    raw: Any = None


@dataclass(slots=True)
class ExternalReview:
    url: str | None = None
    relative_time: str | None = None
    author: str | None = None
    text: str | None = None
    rating: float | None = None
    timestamp_ms: int | None = None
    source: str | None = None


@dataclass(slots=True)
class NearbyPlace:
    name: str | None = None
    cid: str | None = None
    place_id: str | None = None
    request_token: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    category: str | None = None
    raw: Any = None


@dataclass(slots=True)
class Topic:
    topic_id: str | None = None
    name: str | None = None
    statistics: list[int | float | None] = field(default_factory=list)
    encoded_id: str | None = None
    request_token: str | None = None
    score_data: list[Any] = field(default_factory=list)


@dataclass(slots=True)
class GeographicEntity:
    entity_id: str | None = None
    secondary_id: str | None = None
    confidence: float | None = None
    names: list[str] = field(default_factory=list)


@dataclass(slots=True)
class TravelTime:
    mode: int | None = None
    duration_seconds: int | None = None
    duration_text: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    distance_factor: float | None = None
    request_token: str | None = None


@dataclass(slots=True)
class BookingLink:
    url: str | None = None
    label: str | None = None
    type: int | None = None
    source: str | None = None


@dataclass(slots=True)
class LocalPost:
    post_id: str | None = None
    business_id: str | None = None
    date_text: str | None = None
    text: str | None = None
    image_urls: list[str] = field(default_factory=list)
    booking_url: str | None = None
    delete_url: str | None = None
    edit_url: str | None = None
    search_url: str | None = None
    raw: Any = None


@dataclass(slots=True)
class ContributionPolicy:
    title: str | None = None
    message: str | None = None
    learn_more_url: str | None = None
    learn_more_text: str | None = None
    locale: str | None = None
    flags: list[int] = field(default_factory=list)


@dataclass(slots=True)
class HotelInfo:
    check_in: str | None = None
    check_out: str | None = None
    raw: Any = None


# ============================================================
# Field containers
# ============================================================

@dataclass(slots=True)
class AddressData:
    field_2: list[str] = field(default_factory=list)
    field_18: str | None = None
    field_39: str | None = None
    field_82: list[str] = field(default_factory=list)
    field_183: Address | None = None


@dataclass(slots=True)
class MediaData:
    photos: list[Photo] = field(default_factory=list)
    street_view: Any = None
    owner_photo_url: str | None = None


@dataclass(slots=True)
class ReviewData:
    reviews: list[Review] = field(default_factory=list)
    external_reviews: list[ExternalReview] = field(default_factory=list)
    review_ui: Any = None


@dataclass(slots=True)
class BusinessData:
    cid: str | None = None
    place_id: str | None = None
    google_entity_id: str | None = None
    identifiers: list[BusinessIdentifier] = field(default_factory=list)
    claimed: bool | None = None
    verified: bool | None = None
    claim_urls: list[str] = field(default_factory=list)


# ============================================================
# Complete Place
# ============================================================

@dataclass(slots=True)
class Place:
    # --------------------------------------------------------
    # Primary identity
    # --------------------------------------------------------

    search_id: str | None = None
    request_token: str | None = None
    name: str | None = None
    alternate_name: str | None = None

    cid: str | None = None
    place_id: str | None = None
    google_entity_id: str | None = None

    # --------------------------------------------------------
    # Location
    # --------------------------------------------------------

    coordinates: Coordinates | None = None
    coordinates_secondary: Coordinates | None = None

    address: AddressData = field(default_factory=AddressData)
    locality: str | None = None
    region: str | None = None
    timezone: str | None = None
    country_code: str | None = None
    language: str | None = None
    language_name: str | None = None
    language_code: str | None = None

    geographic_entities: list[GeographicEntity] = field(
        default_factory=list
    )

    # --------------------------------------------------------
    # Classification
    # --------------------------------------------------------

    categories: list[Category] = field(default_factory=list)
    rating: RatingInfo | None = None

    # --------------------------------------------------------
    # Contact
    # --------------------------------------------------------

    phone: PhoneInfo | None = None
    website: Website | None = None

    # --------------------------------------------------------
    # Business information
    # --------------------------------------------------------

    business: BusinessData = field(default_factory=BusinessData)

    description: str | None = None
    editorial_description: str | None = None
    owner: Any = None
    amenities: list[int] = field(default_factory=list)
    accessibility: Any = None

    # --------------------------------------------------------
    # Opening / hotel
    # --------------------------------------------------------

    opening_hours: OpeningHours | None = None
    hotel: HotelInfo | None = None

    # --------------------------------------------------------
    # Media / reviews
    # --------------------------------------------------------

    media: MediaData = field(default_factory=MediaData)
    review_data: ReviewData = field(default_factory=ReviewData)

    # --------------------------------------------------------
    # Other rich data
    # --------------------------------------------------------

    nearby_places: list[NearbyPlace] = field(default_factory=list)
    topics: list[Topic] = field(default_factory=list)
    travel_times: list[TravelTime] = field(default_factory=list)
    bookings: list[BookingLink] = field(default_factory=list)
    local_posts: list[LocalPost] = field(default_factory=list)
    contribution_policies: list[ContributionPolicy] = field(
        default_factory=list
    )

    maps_url: str | None = None
    formatted_address: str | None = None
    status: int | None = None

    # --------------------------------------------------------
    # ALL 260 fields
    # --------------------------------------------------------

    fields: dict[int, Any] = field(default_factory=dict)

    # --------------------------------------------------------
    # Original record
    # --------------------------------------------------------

    raw: list[Any] = field(default_factory=list)

    def to_dict(self):
            return asdict(self)
    def to_json(self):
            return json.dumps(asdict(self))


# ============================================================
# Root field names
# ============================================================

FIELD_NAMES: dict[int, str] = {
    0: "search_id",
    1: "request_token",
    2: "address_components",
    3: "field_003",
    4: "rating",
    5: "field_005",
    6: "field_006",
    7: "website",
    8: "field_008",
    9: "coordinates",
    10: "cid",
    11: "name",
    12: "field_012",
    13: "categories",
    14: "locality",
    15: "field_015",
    16: "field_016",
    17: "field_017",
    18: "full_address",
    19: "field_019",
    20: "field_020",
    21: "field_021",
    22: "field_022",
    23: "field_023",
    24: "field_024",
    25: "saved_places",
    26: "field_026",
    27: "field_027",
    28: "field_028",
    29: "field_029",
    30: "timezone",
    31: "contributor_data",
    32: "editorial_data",
    33: "field_033",
    34: "field_034",
    35: "hotel_data",
    36: "field_036",
    37: "street_view",
    38: "field_038",
    39: "formatted_address",
    40: "field_040",
    41: "field_041",
    42: "maps_url",
    43: "status",
    44: "field_044",
    45: "field_045",
    46: "booking_links",
    47: "field_047",
    48: "field_048",
    49: "business_claim",
    50: "field_050",
    51: "place_metadata",
    52: "field_052",
    53: "field_053",
    54: "field_054",
    55: "field_055",
    56: "field_056",
    57: "owner_data",
    58: "field_058",
    59: "field_059",
    60: "field_060",
    61: "business_verified",
    62: "field_062",
    63: "field_063",
    64: "amenities",
    65: "field_065",
    66: "field_066",
    67: "flag_067",
    68: "field_068",
    69: "field_069",
    70: "field_070",
    71: "field_071",
    72: "photos",
    73: "field_073",
    74: "field_074",
    75: "reservation_data",
    76: "field_076",
    77: "field_077",
    78: "place_id",
    79: "field_079",
    80: "field_080",
    81: "field_081",
    82: "address_summary",
    83: "field_083",
    84: "field_084",
    85: "field_085",
    86: "field_086",
    87: "field_087",
    88: "search_result_data",
    89: "google_entity_id",
    90: "field_090",
    91: "field_091",
    92: "field_092",
    93: "field_093",
    94: "field_094",
    95: "field_095",
    96: "edit_links",
    97: "field_097",
    98: "field_098",
    99: "field_099",
    100: "accessibility",
    101: "alternate_name",
    102: "field_102",
    103: "field_103",
    104: "field_104",
    105: "field_105",
    106: "field_106",
    107: "field_107",
    108: "field_108",
    109: "field_109",
    110: "language",
    111: "country_code",
    112: "language_name",
    113: "language_code",
    114: "field_114",
    115: "field_115",
    116: "field_116",
    117: "field_117",
    118: "field_118",
    119: "field_119",
    120: "field_120",
    121: "flag_121",
    122: "related_content",
    123: "field_123",
    124: "field_124",
    125: "field_125",
    126: "field_126",
    127: "field_127",
    128: "field_128",
    129: "field_129",
    130: "flag_130",
    131: "field_131",
    132: "field_132",
    133: "field_133",
    134: "nearby_places",
    135: "field_135",
    136: "flag_136",
    137: "field_137",
    138: "field_138",
    139: "field_139",
    140: "field_140",
    141: "field_141",
    142: "field_142",
    143: "field_143",
    144: "field_144",
    145: "field_145",
    146: "attribute_flags",
    147: "field_147",
    148: "field_148",
    149: "field_149",
    150: "field_150",
    151: "field_151",
    152: "field_152",
    153: "topics",
    154: "description",
    155: "field_155",
    156: "field_156",
    157: "owner_photo",
    158: "field_158",
    159: "field_159",
    160: "field_160",
    161: "editorial_description",
    162: "field_162",
    163: "field_163",
    164: "field_164",
    165: "feature_flags",
    166: "region",
    167: "field_167",
    168: "field_168",
    169: "field_169",
    170: "field_170",
    171: "field_171",
    172: "field_172",
    173: "field_173",
    174: "field_174",
    175: "review_ui",
    176: "field_176",
    177: "field_177",
    178: "phone",
    179: "field_179",
    180: "field_180",
    181: "business_identifiers",
    182: "field_182",
    183: "address_data",
    184: "field_184",
    185: "field_185",
    186: "nearby_search",
    187: "field_187",
    188: "field_188",
    189: "field_189",
    190: "field_190",
    191: "field_191",
    192: "field_192",
    193: "field_193",
    194: "field_194",
    195: "field_195",
    196: "schedule_metadata",
    197: "field_197",
    198: "field_198",
    199: "field_199",
    200: "field_200",
    201: "field_201",
    202: "field_202",
    203: "opening_hours",
    204: "reviews",
    205: "flag_205",
    206: "field_206",
    207: "field_207",
    208: "secondary_coordinates",
    209: "encoded_place_data",
    210: "field_210",
    211: "field_211",
    212: "field_212",
    213: "field_213",
    214: "flag_214",
    215: "field_215",
    216: "field_216",
    217: "field_217",
    218: "field_218",
    219: "field_219",
    220: "field_220",
    221: "field_221",
    222: "field_222",
    223: "field_223",
    224: "field_224",
    225: "field_225",
    226: "business_claim",
    227: "business_identifiers_2",
    228: "field_228",
    229: "travel_times",
    230: "field_230",
    231: "field_231",
    232: "field_232",
    233: "field_233",
    234: "field_234",
    235: "field_235",
    236: "field_236",
    237: "field_237",
    238: "field_238",
    239: "field_239",
    240: "field_240",
    241: "contribution_policies",
    242: "field_242",
    243: "country",
    244: "field_244",
    245: "geographic_entities",
    246: "field_246",
    247: "field_247",
    248: "field_248",
    249: "field_249",
    250: "field_250",
    251: "field_251",
    252: "field_252",
    253: "field_253",
    254: "field_254",
    255: "field_255",
    256: "field_256",
    257: "field_257",
    258: "flag_258",
    259: "flag_259",
}


# ============================================================
# Individual parsers
# ============================================================

def parse_coordinates(value: Any) -> Coordinates | None:
    return Coordinates.from_google(value)


def parse_categories(value: Any) -> list[Category]:
    if not isinstance(value, list):
        return []

    result: list[Category] = []

    for item in value:
        if isinstance(item, str):
            result.append(Category(name=item))

        elif isinstance(item, list):
            for x in item:
                if isinstance(x, str):
                    result.append(Category(name=x))

    return result


def parse_website(value: Any) -> Website | None:
    if not isinstance(value, list):
        return None

    urls = [
        x for x in value
        if isinstance(x, str)
        and (
            x.startswith("http://")
            or x.startswith("https://")
        )
    ]

    if not urls:
        return None

    url = urls[0]

    domain = None

    if "://" in url:
        domain = url.split("://", 1)[1].split("/", 1)[0]

    return Website(
        url=url,
        domain=domain,
    )


def parse_phone(value: Any) -> PhoneInfo | None:
    if not isinstance(value, list):
        return None

    numbers: list[PhoneNumber] = []

    for item in value:
        if not isinstance(item, list):
            continue

        raw = as_str(get(item, 0))

        if raw is None:
            continue

        variants = get(item, 1, [])

        if isinstance(variants, list):
            for variant in variants:
                if not isinstance(variant, list):
                    continue

                number = as_str(get(variant, 0))

                if number:
                    numbers.append(
                        PhoneNumber(
                            raw=number,
                            normalized=number,
                        )
                    )

        normalized = as_str(get(item, 3))

        uri = None

        links = get(item, 5)

        if isinstance(links, list):
            uri = as_str(get(links, 0))

        numbers.append(
            PhoneNumber(
                raw=raw,
                normalized=normalized or raw,
                uri=uri,
            )
        )

    # Remove duplicates while preserving order.
    unique: list[PhoneNumber] = []
    seen: set[tuple[str | None, str | None]] = set()

    for number in numbers:
        key = (number.raw, number.normalized)

        if key not in seen:
            seen.add(key)
            unique.append(number)

    if not unique:
        return None

    return PhoneInfo(
        primary=unique[0],
        numbers=unique,
    )


def parse_photos(value: Any) -> list[Photo]:
    if not isinstance(value, list):
        return []

    result: list[Photo] = []

    def walk_photo(node: Any) -> None:
        if not isinstance(node, list):
            return

        first = get(node, 0)

        if isinstance(first, str) and first.startswith("http"):
            width = as_int(get(node, 1))

            # Some Google structures store additional image
            # dimensions in a nested list.
            dimensions = get(node, 4)

            height = None

            if isinstance(dimensions, list):
                width = as_int(get(dimensions, 0)) or width
                height = as_int(get(dimensions, 1))

            result.append(
                Photo(
                    url=first,
                    width=width,
                    height=height,
                    reference=as_str(get(node, 4)),
                    metadata=node,
                )
            )
            return

        for child in node:
            if isinstance(child, list):
                walk_photo(child)

    walk_photo(value)

    # Deduplicate URLs.
    unique: list[Photo] = []
    seen: set[str] = set()

    for photo in result:
        if photo.url and photo.url not in seen:
            seen.add(photo.url)
            unique.append(photo)

    return unique


def parse_opening_day(value: Any) -> OpeningDay | None:
    if not isinstance(value, list):
        return None

    name = as_str(get(value, 0))
    day = as_int(get(value, 1))

    date_value = get(value, 2)
    date = None

    if (
        isinstance(date_value, list)
        and len(date_value) >= 3
        and all(isinstance(x, int) for x in date_value[:3])
    ):
        date = (
            date_value[0],
            date_value[1],
            date_value[2],
        )

    periods: list[OpeningPeriod] = []

    period_data = get(value, 3)

    if isinstance(period_data, list):
        for period in period_data:
            if not isinstance(period, list):
                continue

            text = as_str(get(period, 0))
            time_range = get(period, 1)

            open_hour = None
            open_minute = None
            close_hour = None
            close_minute = None

            if isinstance(time_range, list) and len(time_range) >= 2:
                start = get(time_range, 0)
                end = get(time_range, 1)

                if isinstance(start, list):
                    open_hour = as_int(get(start, 0))
                    open_minute = as_int(get(start, 1))

                if isinstance(end, list):
                    close_hour = as_int(get(end, 0))
                    close_minute = as_int(get(end, 1))

            periods.append(
                OpeningPeriod(
                    text=text,
                    open_hour=open_hour,
                    open_minute=open_minute,
                    close_hour=close_hour,
                    close_minute=close_minute,
                )
            )

    return OpeningDay(
        name=name,
        day_of_week=day,
        date=date,
        periods=periods,
    )


def parse_opening_hours(value: Any) -> OpeningHours | None:
    if not isinstance(value, list):
        return None

    days: list[OpeningDay] = []

    # Field 203:
    #
    # [
    #   [
    #       ["Sunday", 7, [2026,10,4], ...],
    #       ...
    #   ],
    #   [...]
    # ]
    #
    first_group = get(value, 0)

    if isinstance(first_group, list):
        for item in first_group:
            parsed = parse_opening_day(item)

            if parsed:
                days.append(parsed)

    current_day = days[0] if days else None

    return OpeningHours(
        current_day=current_day,
        days=days,
        raw=value,
    )


def parse_address(value: Any) -> Address | None:
    if not isinstance(value, list):
        return None

    # Field 183 has:
    #
    # [
    #   structured_address,
    #   compact_address,
    #   plus_code_data
    # ]

    compact = get(value, 1)

    if isinstance(compact, list):
        return Address(
            short=as_str(get(compact, 0)),
            street=as_str(get(compact, 1)),
            locality=as_str(get(compact, 2)),
            administrative_area=as_str(get(compact, 3)),
            postal_code=as_str(get(compact, 4)),
            region=as_str(get(compact, 5)),
            country_code=as_str(get(compact, 6)),
            components=[
                x for x in compact
                if isinstance(x, str)
            ],
        )

    return Address()


def parse_identifiers(value: Any) -> list[BusinessIdentifier]:
    if not isinstance(value, list):
        return []

    result: list[BusinessIdentifier] = []

    def parse_item(item: Any) -> None:
        if not isinstance(item, list):
            return

        # Field 227 observed:
        #
        # [
        #   [
        #       cid,
        #       None,
        #       None,
        #       /g/...
        #       ChIJ...
        #       numeric_id,
        #       another_numeric_id
        #   ]
        # ]

        cid = as_str(get(item, 0))
        entity = as_str(get(item, 3))
        place_id = as_str(get(item, 4))
        numeric_id = as_str(get(item, 5))
        alternate_id = as_str(get(item, 6))

        if any(
            x is not None
            for x in (
                cid,
                entity,
                place_id,
                numeric_id,
                alternate_id,
            )
        ):
            result.append(
                BusinessIdentifier(
                    cid=cid,
                    google_entity_id=entity,
                    place_id=place_id,
                    numeric_id=numeric_id,
                    alternate_id=alternate_id,
                )
            )

    for item in value:
        parse_item(item)

    return result


def parse_topics(value: Any) -> list[Topic]:
    if not isinstance(value, list):
        return []

    result: list[Topic] = []

    def parse_topic(item: Any) -> None:
        if not isinstance(item, list):
            return

        topic_ids = get(item, 0)

        topic_id = None

        if isinstance(topic_ids, list):
            topic_id = as_str(get(topic_ids, 0))

        name = as_str(get(item, 1))
        statistics = get(item, 3)
        encoded_id = as_str(get(item, 4))
        request_token = as_str(get(item, 5))

        result.append(
            Topic(
                topic_id=topic_id,
                name=name,
                statistics=(
                    statistics
                    if isinstance(statistics, list)
                    else []
                ),
                encoded_id=encoded_id,
                request_token=request_token,
                score_data=[],
            )
        )

    for item in value:
        if isinstance(item, list):
            for nested in item:
                if isinstance(nested, list):
                    parse_topic(nested)

    return result


def parse_geographic_entities(value: Any) -> list[GeographicEntity]:
    if not isinstance(value, list):
        return []

    result: list[GeographicEntity] = []

    def parse_entity(item: Any) -> None:
        if not isinstance(item, list):
            return

        ids = get(item, 0)
        confidence = as_float(get(item, 1))
        names_container = get(item, 2)

        entity_id = None
        secondary_id = None

        if isinstance(ids, list):
            entity_id = as_str(get(ids, 0))
            secondary_id = as_str(get(ids, 1))

        names: list[str] = []

        if isinstance(names_container, list):
            for group in names_container:
                if isinstance(group, list):
                    names.extend(
                        x for x in group
                        if isinstance(x, str)
                    )

        result.append(
            GeographicEntity(
                entity_id=entity_id,
                secondary_id=secondary_id,
                confidence=confidence,
                names=names,
            )
        )

    for group in value:
        if isinstance(group, list):
            for item in group:
                parse_entity(item)

    return result


def parse_travel_times(value: Any) -> list[TravelTime]:
    if not isinstance(value, list):
        return []

    # Field 229:
    #
    # [
    #   request_token,
    #   [
    #       [
    #           mode,
    #           [seconds, "15 min"],
    #           coordinates,
    #           ...
    #       ]
    #   ]
    # ]

    result: list[TravelTime] = []

    request_token = as_str(get(value, 0))
    entries = get(value, 1)

    if not isinstance(entries, list):
        return result

    for entry in entries:
        if not isinstance(entry, list):
            continue

        mode_data = get(entry, 0)
        duration_data = get(entry, 0)
        coords_data = get(entry, 1)

        mode = None
        seconds = None
        duration_text = None

        if isinstance(mode_data, list):
            mode = as_int(get(mode_data, 0))

        if isinstance(duration_data, list):
            duration = get(duration_data, 1)

            if isinstance(duration, list):
                seconds = as_int(get(duration, 0))
                duration_text = as_str(get(duration, 1))

        coordinates = Coordinates.from_google(coords_data)

        result.append(
            TravelTime(
                mode=mode,
                duration_seconds=seconds,
                duration_text=duration_text,
                latitude=(
                    coordinates.latitude
                    if coordinates
                    else None
                ),
                longitude=(
                    coordinates.longitude
                    if coordinates
                    else None
                ),
                request_token=request_token,
            )
        )

    return result


def parse_booking_links(value: Any) -> list[BookingLink]:
    if not isinstance(value, list):
        return []

    result: list[BookingLink] = []

    def walk(node: Any) -> None:
        if not isinstance(node, list):
            return

        url = None
        label = None
        link_type = None

        for item in node:
            if isinstance(item, str) and item.startswith("http"):
                url = item

            elif isinstance(item, int):
                if link_type is None:
                    link_type = item

            elif isinstance(item, str):
                if label is None:
                    label = item

        if url:
            result.append(
                BookingLink(
                    url=url,
                    label=label,
                    type=link_type,
                )
            )

        for child in node:
            if isinstance(child, list):
                walk(child)

    walk(value)

    return result


def parse_contribution_policies(
    value: Any,
) -> list[ContributionPolicy]:

    if not isinstance(value, list):
        return []

    result: list[ContributionPolicy] = []

    def walk(node: Any) -> None:
        if not isinstance(node, list):
            return

        # Known policy structure:
        #
        # [
        #   flag,
        #   [
        #       title,
        #       message,
        #       [[url, label]],
        #       message,
        #       ...
        #       locale
        #   ],
        #   ...
        # ]

        if (
            len(node) >= 2
            and isinstance(node[1], list)
        ):
            body = node[1]

            title = as_str(get(body, 0))
            message = as_str(get(body, 1))

            learn_more_url = None
            learn_more_text = None

            learn_more = get(body, 2)

            if isinstance(learn_more, list):
                first = get(learn_more, 0)

                if isinstance(first, list):
                    learn_more_url = as_str(get(first, 0))
                    learn_more_text = as_str(get(first, 1))

            locale = as_str(get(body, 7))

            flags = [
                x for x in node
                if isinstance(x, int)
            ]

            if title or message:
                result.append(
                    ContributionPolicy(
                        title=title,
                        message=message,
                        learn_more_url=learn_more_url,
                        learn_more_text=learn_more_text,
                        locale=locale,
                        flags=flags,
                    )
                )

        for child in node:
            if isinstance(child, list):
                walk(child)

    walk(value)

    return result


# ============================================================
# Field parser registry
# ============================================================

Parser: TypeAlias = Callable[[Any], Any]


def identity(value: Any) -> Any:
    return value


FIELD_PARSERS: dict[int, Parser] = {
    0: as_str,
    1: as_str,
    2: lambda x: [
        v for v in x
        if isinstance(v, str)
    ] if isinstance(x, list) else [],
    4: RatingInfo.from_field_4,
    7: parse_website,
    9: parse_coordinates,
    10: as_str,
    11: as_str,
    13: parse_categories,
    14: as_str,
    18: as_str,
    30: as_str,
    35: lambda x: HotelInfo(raw=x) if x is not None else None,
    37: identity,
    39: as_str,
    42: as_str,
    43: as_int,
    46: parse_booking_links,
    49: identity,
    51: identity,
    57: identity,
    61: as_bool,
    64: lambda x: (
        [v for v in x if isinstance(v, int)]
        if isinstance(x, list)
        else []
    ),
    67: as_int,
    72: parse_photos,
    75: identity,
    78: as_str,
    82: lambda x: (
        [v for v in x if isinstance(v, str)]
        if isinstance(x, list)
        else []
    ),
    88: identity,
    89: as_str,
    96: identity,
    100: identity,
    101: as_str,
    110: as_str,
    111: as_str,
    112: as_str,
    113: as_str,
    121: as_int,
    122: identity,
    130: as_int,
    134: identity,
    136: as_int,
    146: identity,
    153: parse_topics,
    154: identity,
    157: as_str,
    161: identity,
    165: identity,
    166: as_str,
    175: identity,
    178: parse_phone,
    181: identity,
    183: parse_address,
    186: identity,
    196: identity,
    203: parse_opening_hours,
    204: identity,
    205: as_int,
    208: lambda x: (
        Coordinates.from_google(get(x, 0))
        if isinstance(x, list)
        else None
    ),
    209: as_str,
    214: as_int,
    226: identity,
    227: parse_identifiers,
    229: parse_travel_times,
    241: parse_contribution_policies,
    243: as_str,
    245: parse_geographic_entities,
    258: as_int,
    259: as_int,
}


# ============================================================
# Parse ALL 260 root fields
# ============================================================

def parse_all_fields(record: list[Any]) -> dict[int, Any]:
    """
    Parse every one of the 260 root fields.

    Known fields use their dedicated parser.
    Unknown fields remain structurally untouched.

    Nothing is discarded.
    """

    if len(record) != 260:
        raise ValueError(
            f"Expected 260 fields, got {len(record)}"
        )

    result: dict[int, Any] = {}

    for index in range(260):
        value = record[index]

        parser = FIELD_PARSERS.get(index, identity)

        try:
            result[index] = parser(value)
        except Exception:
            # Preserve data even if a future Google schema variant
            # breaks one specialized parser.
            result[index] = value

    return result


# ============================================================
# Main Place parser
# ============================================================

def parse_place(record: list[Any]) -> Place:
    if not isinstance(record, list):
        raise TypeError(
            f"Place must be list, got {type(record).__name__}"
        )

    if len(record) != 260:
        raise ValueError(
            f"Place must contain 260 fields, got {len(record)}"
        )

    fields = parse_all_fields(record)

    place = Place(
        search_id=fields.get(0),
        request_token=fields.get(1),

        name=fields.get(11),
        alternate_name=fields.get(101),

        cid=fields.get(10),
        place_id=fields.get(78),
        google_entity_id=fields.get(89),

        coordinates=fields.get(9),
        coordinates_secondary=fields.get(208),

        locality=fields.get(14),
        timezone=fields.get(30),
        country_code=fields.get(111),
        language=fields.get(110),
        language_name=fields.get(112),
        language_code=fields.get(113),
        region=fields.get(166),

        categories=fields.get(13, []),
        rating=fields.get(4),

        phone=fields.get(178),
        website=fields.get(7),

        description=first_string(
            fields.get(154)
        ),
        editorial_description=(
            first_string(fields.get(161))
        ),

        amenities=fields.get(64, []),

        opening_hours=fields.get(203),

        media=MediaData(
            photos=fields.get(72, []),
            street_view=fields.get(37),
            owner_photo_url=fields.get(157),
        ),

        business=BusinessData(
            cid=fields.get(10),
            place_id=fields.get(78),
            google_entity_id=fields.get(89),
            identifiers=fields.get(227, []),
            verified=fields.get(61),
            claim_urls=[],
        ),

        nearby_places=[],
        topics=fields.get(153, []),
        travel_times=fields.get(229, []),
        bookings=fields.get(46, []),
        contribution_policies=fields.get(241, []),

        maps_url=fields.get(42),
        formatted_address=fields.get(39),
        status=fields.get(43),

        address=AddressData(
            field_2=fields.get(2, []),
            field_18=fields.get(18),
            field_39=fields.get(39),
            field_82=fields.get(82, []),
            field_183=fields.get(183),
        ),

        fields=fields,
        raw=record,
    )

    return place


def parse_places(data: list[Any]) -> list[Place]:
    return [
        parse_place(record)
        for record in data
        if isinstance(record, list)
    ]

if __name__ == "__main__":
    import json
    d = json.load(open("places.json","r"))
    places = parse_places(d)[0].to_json()
    print(places)