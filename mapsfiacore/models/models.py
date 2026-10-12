from dataclasses import asdict, dataclass, field
from typing import Optional

@dataclass
class Suggestion:
    feature_id:str
    label:str
    mid:str
    lat:float
    lng:float
    type_code:int
    kind:Optional[str] = None
    name:Optional[str] = None
    address:Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class Photo:
    id: str
    kind: str                       # Photo | Video | Street View
    url: str
    width: Optional[int] = None     # original size (not the thumbnail size)
    height: Optional[int] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    date: Optional[str] = None      # YYYY-MM-DD (upload / capture date)
    video_streams: list[dict] = field(default_factory=list)


@dataclass
class RelatedPlace:
    fid: str
    name: Optional[str] = None
    categories: list[str] = field(default_factory=list)
    rating: Optional[float] = None
    review_count: Optional[int] = None
    lat: Optional[float] = None
    lng: Optional[float] = None


@dataclass
class Place:
    # identity
    name: Optional[str] = None
    fid: Optional[str] = None               # "0x2e69...:0x9171..."
    cid: Optional[str] = None               # decimal CID (2nd half of fid, unsigned)
    place_id: Optional[str] = None          # ChIJ...
    kgmid: Optional[str] = None             # /g/11y2cxztdx
    categories: list[str] = field(default_factory=list)
    category_ids: list[str] = field(default_factory=list)   # e.g. massage_therapist
    place_type: Optional[str] = None        # SearchResult.TYPE_...
    # location
    address: Optional[str] = None
    address_lines: list[str] = field(default_factory=list)
    locality: Optional[str] = None          # "Jatimurni, Pondok Melati"
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country_code: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    plus_code: Optional[str] = None         # global code, e.g. 6P58MWCJ+C2
    plus_code_local: Optional[str] = None   # e.g. "MWCJ+C2 Jatimurni, Bekasi, West Java"
    # reputation
    rating: Optional[float] = None
    review_count: Optional[int] = None
    reviews_url: Optional[str] = None
    # contact / hours (best-effort: absent in many listings)
    phone: Optional[str] = None
    website: Optional[str] = None
    hours: dict[str, list[str]] = field(default_factory=dict)
    # meta
    timezone: Optional[str] = None
    tz_abbr: Optional[str] = None
    utc_offset_minutes: Optional[int] = None
    fetched_at: Optional[str] = None        # ISO-8601 UTC, from server timestamp
    claimed: Optional[bool] = None          # False when "Claim this business" is offered
    missing_fields: list[str] = field(default_factory=list)  # from "Add hours/phone/website"
    maps_url: Optional[str] = None
    # media / related
    photos: list[Photo] = field(default_factory=list)
    related_title: Optional[str] = None
    related: list[RelatedPlace] = field(default_factory=list)
    price_range: Optional[str] = None
    attributes: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)