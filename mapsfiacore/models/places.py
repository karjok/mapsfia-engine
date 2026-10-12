import json
from typing import Optional
from dataclasses import dataclass, field, asdict

@dataclass
class Website:
   url: Optional[str] = None
   domain: Optional[str] = None

@dataclass
class Phone:
   local_fmt: Optional[str] = None
   global_fmt: Optional[str] = None
   uri_fmt: Optional[str] = None

@dataclass
class Accessibility:
   accessibility: Optional[str] = None
   label: Optional[str] = None
   status: Optional[bool] = None

@dataclass
class OpeningHours:
   """One day's opening-hours entry.

   ``day`` and ``label`` are raw strings in the response's language (``hl``),
   so they are NOT language independent. Use ``weekday`` (canonical English,
   derived from the numeric ``day_index``: 1=Monday .. 7=Sunday) and the
   numeric ``intervals`` for language-neutral logic.

   ``intervals`` holds zero or more ``(open, close)`` pairs as 24h integers
   (``None`` when Google only exposes a label such as "Closed"/"Tutup").
   """
   day: Optional[str] = None
   day_index: Optional[int] = None
   weekday: Optional[str] = None
   date: Optional[str] = None
   label: Optional[str] = None
   intervals: Optional[list] = None
   closed: Optional[bool] = None
   is_24h: Optional[bool] = None

@dataclass
class OpeningHoursStatus:
   """Current open/closed state, when Google includes it (often absent).

   ``label`` is localized to ``hl``; ``is_open`` is derived from Google's
   numeric status code and is language independent (None when unknown).
   """
   is_open: Optional[bool] = None
   state: Optional[str] = None
   label: Optional[str] = None
   next_change: Optional[str] = None

@dataclass
class AddressComponents:
   """Structured address pieces. Every field is best-effort and may be None."""
   neighborhood: Optional[str] = None
   street: Optional[str] = None
   district: Optional[str] = None
   city: Optional[str] = None
   postal_code: Optional[str] = None
   province: Optional[str] = None
   country_code: Optional[str] = None
   lines: Optional[list] = None

@dataclass
class StreetView:
   pano_id: Optional[str] = None
   thumbnail_url: Optional[str] = None
   lat: Optional[float] = None
   lng: Optional[float] = None

@dataclass
class Owner:
   label: Optional[str] = None
   owner_id: Optional[str] = None

@dataclass
class Place:
   place_id: Optional[str] = None
   fid: Optional[str] = None
   rating: Optional[float] = None
   review_count: Optional[int] = None
   website: Optional[Website] = None
   name: Optional[str] = None
   place_type_labels: Optional[list] = None
   full_address: Optional[str] = None
   address: Optional[str] = None
   lat: Optional[float] = None
   lng: Optional[float] = None
   timezone: Optional[str] = None
   is_claimed: Optional[bool] = None
   plus_code: Optional[str] = None
   maps_url: Optional[str] = None
   place_type_id: Optional[str] = None
   place_type_key: Optional[str] = None
   kgmid: Optional[str] = None
   accessibilities: Optional[list] = None
   description: Optional[str] = None
   phone: Optional[Phone] = None
   banner: Optional[list] = None
   medias: Optional[list] = None
   media_filters: Optional[dict] = field(default_factory=dict)
   # --- extended / best-effort fields -----------------------------------
   neighborhood: Optional[str] = None
   city: Optional[str] = None
   province: Optional[str] = None
   postal_code: Optional[str] = None
   country_code: Optional[str] = None
   address_components: Optional[AddressComponents] = None
   opening_hours: Optional[list] = None
   opening_hours_status: Optional[OpeningHoursStatus] = None
   street_view: Optional[StreetView] = None
   owner: Optional[Owner] = None
   languages: Optional[list] = None
   precise_lat: Optional[float] = None
   precise_lng: Optional[float] = None
   category_ids: Optional[list] = None
   reviews_url: Optional[str] = None
   missing_fields: Optional[list] = None
   review_overviews: Optional[list] = None