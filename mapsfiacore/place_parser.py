from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Iterable, Iterator, Mapping, Sequence


JSON = Any


# ============================================================
# 260 ROOT FIELDS
# ============================================================

FIELD_LOOKUP: dict[int, str] = {
    0: "search_id",
    1: "request_token",
    2: "address_components",
    3: "field_003",
    4: "rating_data",
    5: "field_005",
    6: "field_006",
    7: "website_data",
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
    32: "editorial_summary",
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
    43: "place_status",
    44: "field_044",
    45: "field_045",
    46: "external_booking_links",
    47: "field_047",
    48: "field_048",
    49: "claim_business_url",
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
    67: "field_067",
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
    121: "field_121",
    122: "related_content",
    123: "field_123",
    124: "field_124",
    125: "field_125",
    126: "field_126",
    127: "field_127",
    128: "field_128",
    129: "field_129",
    130: "field_130",
    131: "field_131",
    132: "field_132",
    133: "field_133",
    134: "nearby_places",
    135: "field_135",
    136: "field_136",
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
    153: "topic_data",
    154: "description",
    155: "field_155",
    156: "field_156",
    157: "owner_photo_url",
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
    178: "phone_data",
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
    205: "field_205",
    206: "field_206",
    207: "field_207",
    208: "geo",
    209: "encoded_place_data",
    210: "field_210",
    211: "field_211",
    212: "field_212",
    213: "field_213",
    214: "field_214",
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
    227: "identifiers",
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
    241: "policy_messages",
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
    258: "field_258",
    259: "field_259",
}


# ============================================================
# TYPED MODELS
# ============================================================

@dataclass(slots=True)
class Coordinates:
    latitude: float | None = None
    longitude: float | None = None


@dataclass(slots=True)
class Phone:
    raw: str | None = None
    international: str | None = None
    normalized: str | None = None
    tel_uri: str | None = None


@dataclass(slots=True)
class Website:
    url: str | None = None
    domain: str | None = None


@dataclass(slots=True)
class Photo:
    id: str | None = None
    url: str | None = None
    title: str | None = None
    width: int | None = None
    height: int | None = None
    kind: str | None = None
    raw: Any = None


@dataclass(slots=True)
class OpeningHours:
    raw: Any = None
    text: str | None = None
    days: list[Any] = field(default_factory=list)


@dataclass(slots=True)
class Place:
    # canonical fields
    name: str | None = None
    place_id: str | None = None
    cid: str | None = None
    google_entity_id: str | None = None
    google_maps_url: str | None = None

    address: str | None = None
    address_components: list[str] = field(default_factory=list)
    locality: str | None = None
    region: str | None = None
    country: str | None = None
    country_code: str | None = None

    latitude: float | None = None
    longitude: float | None = None
    timezone: str | None = None

    categories: list[str] = field(default_factory=list)

    rating: float | None = None
    review_count: int | None = None

    phone: Phone | None = None
    website: Website | None = None

    description: str | None = None
    editorial_description: str | None = None

    opening_hours: OpeningHours | None = None

    photos: list[Photo] = field(default_factory=list)
    reviews: list[Any] = field(default_factory=list)

    amenities: Any = None
    accessibility: Any = None

    owner_name: str | None = None
    owner_id: str | None = None
    owner_photo_url: str | None = None

    reservation_data: Any = None
    booking_links: list[Any] = field(default_factory=list)
    travel_times: Any = None
    geographic_entities: Any = None

    # ALL 260 original fields
    fields: dict[str, Any] = field(default_factory=dict)

    # Original untouched record.
    raw: list[Any] | None = None

    def get(self, field_name: str, default: Any = None) -> Any:
        return self.fields.get(field_name, default)

    def to_dict(self):
        return asdict(self)
    def to_json(self):
        return json.dumps(asdict(self))


# ============================================================
# GENERIC HELPERS
# ============================================================

def non_null(value: Any) -> bool:
    return value is not None


def first_non_null(values: Iterable[Any]) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def walk(value: Any) -> Iterator[Any]:
    """
    Recursive traversal.

    Tidak pakai regex.
    Semua nested structure Google cukup ditelusuri sebagai list/dict.
    """
    yield value

    if isinstance(value, list):
        for item in value:
            yield from walk(item)

    elif isinstance(value, dict):
        for item in value.values():
            yield from walk(item)


def strings(value: Any) -> Iterator[str]:
    for item in walk(value):
        if isinstance(item, str) and item:
            yield item


def find_strings_containing(value: Any, needle: str) -> list[str]:
    """
    Exact substring lookup, bukan regex.
    """
    return [
        s for s in strings(value)
        if needle in s
    ]


def find_lists(value: Any, length: int | None = None) -> Iterator[list]:
    for item in walk(value):
        if isinstance(item, list):
            if length is None or len(item) == length:
                yield item


# ============================================================
# FIELD LOOKUP
# ============================================================

def extract_root_fields(record: Sequence[Any]) -> dict[str, Any]:
    """
    Root array -> named fields.

    Karena Google mengirim tepat 260 slot pada sample,
    parser tidak perlu nebak berdasarkan bentuk string.
    """
    result: dict[str, Any] = {}

    for index in range(min(260, len(record))):
        name = FIELD_LOOKUP.get(index, f"field_{index:03d}")
        result[name] = record[index]

    return result


# ============================================================
# SPECIALIZED EXTRACTORS
# ============================================================

def parse_coordinates(record: Sequence[Any]) -> Coordinates:
    candidates = []

    for index in (9, 208):
        if index >= len(record):
            continue

        value = record[index]

        if (
            isinstance(value, list)
            and len(value) >= 4
            and isinstance(value[2], (int, float))
            and isinstance(value[3], (int, float))
        ):
            candidates.append(
                Coordinates(
                    latitude=float(value[2]),
                    longitude=float(value[3]),
                )
            )

    return first_non_null(candidates) or Coordinates()


def parse_rating(record: Sequence[Any]) -> tuple[float | None, int | None]:
    rating = None
    review_count = None

    value = record[4] if len(record) > 4 else None

    if isinstance(value, list):
        # sample:
        # [None, None, ..., 4.6, ..., 1]
        for item in value:
            if isinstance(item, float) and 0 <= item <= 5:
                rating = item
                break

    # Review count sering muncul nested.
    # Kita cari integer yang konteksnya dekat dengan rating,
    # tanpa regex.
    if isinstance(value, list):
        for item in value:
            if isinstance(item, int) and item > 5:
                review_count = item
                break

    return rating, review_count


def parse_phone(record: Sequence[Any]) -> Phone | None:
    value = record[178] if len(record) > 178 else None

    if not isinstance(value, list):
        return None

    raw = None
    international = None
    normalized = None
    tel_uri = None

    if value and isinstance(value[0], str):
        raw = value[0]

    if len(value) > 1 and isinstance(value[1], list):
        for item in value[1]:
            if not isinstance(item, list) or not item:
                continue

            if isinstance(item[0], str):
                if len(item) > 1 and item[1] == 2:
                    international = item[0]
                elif len(item) > 1 and item[1] == 1:
                    raw = item[0]

    if len(value) > 3 and isinstance(value[3], str):
        normalized = value[3]

    if len(value) > 5 and isinstance(value[5], list):
        for item in value[5]:
            if isinstance(item, str) and item.startswith("tel:"):
                tel_uri = item

    if not any((raw, international, normalized, tel_uri)):
        return None

    return Phone(
        raw=raw,
        international=international,
        normalized=normalized,
        tel_uri=tel_uri,
    )


def parse_website(record: Sequence[Any]) -> Website | None:
    value = record[7] if len(record) > 7 else None

    if not isinstance(value, list):
        return None

    url = value[0] if len(value) > 0 and isinstance(value[0], str) else None
    domain = value[1] if len(value) > 1 and isinstance(value[1], str) else None

    if not url and not domain:
        return None

    return Website(
        url=url,
        domain=domain,
    )


def parse_photos(record: Sequence[Any]) -> list[Photo]:
    value = record[72] if len(record) > 72 else None

    if not isinstance(value, list):
        return []

    result: list[Photo] = []

    for item in value:
        if not isinstance(item, list):
            continue

        photo = Photo(raw=item)

        if len(item) > 0 and isinstance(item[0], str):
            photo.id = item[0]

        if len(item) > 6 and isinstance(item[6], list):
            media = item[6]

            if len(media) > 0 and isinstance(media[0], str):
                photo.url = media[0]

            if len(media) > 1 and isinstance(media[1], str):
                photo.title = media[1]

            if len(media) > 2 and isinstance(media[2], list):
                size = media[2]

                if len(size) >= 2:
                    if isinstance(size[0], int):
                        photo.width = size[0]

                    if isinstance(size[1], int):
                        photo.height = size[1]

        result.append(photo)

    return result


def parse_owner(record: Sequence[Any]) -> tuple[str | None, str | None]:
    value = record[57] if len(record) > 57 else None

    if not isinstance(value, list):
        return None, None

    owner_name = None
    owner_id = None

    for item in value:
        if isinstance(item, str):
            if owner_name is None and "(Owner)" in item:
                owner_name = item.removesuffix(" (Owner)")

            elif owner_id is None and item.isdigit():
                owner_id = item

    return owner_name, owner_id


def parse_address(record: Sequence[Any]) -> str | None:
    candidates = []

    for index in (18, 39):
        if index < len(record) and isinstance(record[index], str):
            candidates.append(record[index])

    value = record[183] if len(record) > 183 else None

    for item in strings(value):
        if len(item) > 20:
            candidates.append(item)

    return first_non_null(candidates)


def parse_description(record: Sequence[Any]) -> tuple[str | None, str | None]:
    description = None
    editorial = None

    value = record[154] if len(record) > 154 else None

    for item in strings(value):
        if len(item) > 50:
            description = item
            break

    value = record[161] if len(record) > 161 else None

    for item in strings(value):
        if len(item) > 50:
            editorial = item
            break

    return description, editorial


def parse_opening_hours(record: Sequence[Any]) -> OpeningHours | None:
    value = record[203] if len(record) > 203 else None

    if value is None:
        return None

    text_value = None

    for item in strings(value):
        if (
            "Open" in item
            or "Closed" in item
            or "hours" in item
        ):
            text_value = item
            break

    days = []

    if isinstance(value, list):
        for item in value:
            if isinstance(item, list) and item:
                if isinstance(item[0], str):
                    days.append(item)

    return OpeningHours(
        raw=value,
        text=text_value,
        days=days,
    )


def parse_reviews(record: Sequence[Any]) -> list[Any]:
    value = record[204] if len(record) > 204 else None

    if isinstance(value, list):
        return value

    return []


def parse_categories(record: Sequence[Any]) -> list[str]:
    result = []

    for index in (13,):
        if index >= len(record):
            continue

        value = record[index]

        if isinstance(value, list):
            result.extend(
                item
                for item in value
                if isinstance(item, str)
            )

    return list(dict.fromkeys(result))


# ============================================================
# GLOBAL PARSER
# ============================================================

def parse_place(record: Sequence[Any]) -> Place:
    if not isinstance(record, (list, tuple)):
        raise TypeError(
            f"Expected place record list, got {type(record).__name__}"
        )

    fields = extract_root_fields(record)

    coords = parse_coordinates(record)
    rating, review_count = parse_rating(record)

    owner_name, owner_id = parse_owner(record)
    description, editorial_description = parse_description(record)

    phone = parse_phone(record)
    website = parse_website(record)
    photos = parse_photos(record)
    opening_hours = parse_opening_hours(record)

    name = (
        record[11]
        if len(record) > 11 and isinstance(record[11], str)
        else None
    )

    place_id = (
        record[78]
        if len(record) > 78 and isinstance(record[78], str)
        else None
    )

    google_entity_id = (
        record[89]
        if len(record) > 89 and isinstance(record[89], str)
        else None
    )

    maps_url = (
        record[42]
        if len(record) > 42 and isinstance(record[42], str)
        else None
    )

    timezone = (
        record[30]
        if len(record) > 30 and isinstance(record[30], str)
        else None
    )

    locality = (
        record[14]
        if len(record) > 14 and isinstance(record[14], str)
        else None
    )

    region = (
        record[166]
        if len(record) > 166 and isinstance(record[166], str)
        else None
    )

    country_code = (
        record[243]
        if len(record) > 243 and isinstance(record[243], str)
        else None
    )

    country = country_code

    address_components = []

    if len(record) > 2 and isinstance(record[2], list):
        address_components = [
            x for x in record[2]
            if isinstance(x, str)
        ]

    address = parse_address(record)

    return Place(
        name=name,
        place_id=place_id,
        cid=record[10] if len(record) > 10 else None,
        google_entity_id=google_entity_id,
        google_maps_url=maps_url,

        address=address,
        address_components=address_components,
        locality=locality,
        region=region,
        country=country,
        country_code=country_code,

        latitude=coords.latitude,
        longitude=coords.longitude,
        timezone=timezone,

        categories=parse_categories(record),

        rating=rating,
        review_count=review_count,

        phone=phone,
        website=website,

        description=description,
        editorial_description=editorial_description,

        opening_hours=opening_hours,

        photos=photos,
        reviews=parse_reviews(record),

        amenities=record[64] if len(record) > 64 else None,
        accessibility=record[100] if len(record) > 100 else None,

        owner_name=owner_name,
        owner_id=owner_id,
        owner_photo_url=(
            record[157]
            if len(record) > 157 and isinstance(record[157], str)
            else None
        ),

        reservation_data=(
            record[75]
            if len(record) > 75
            else None
        ),

        booking_links=(
            record[46]
            if len(record) > 46 and isinstance(record[46], list)
            else []
        ),

        travel_times=(
            record[229]
            if len(record) > 229
            else None
        ),

        geographic_entities=(
            record[245]
            if len(record) > 245
            else None
        ),

        fields=fields,
        raw=list(record),
    )


def parse_places(data: Sequence[Sequence[Any]]) -> list[Place]:
    return [
        parse_place(record)
        for record in data
        if isinstance(record, (list, tuple))
    ]
if __name__ == "__main__":
    import json
    d = json.load(open("places.json","r"))
    places = parse_places(d)[2].to_json()
    print(places)