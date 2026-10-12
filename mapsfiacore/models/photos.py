import json
from typing import Optional
from dataclasses import dataclass, asdict

@dataclass
class Photo:
    photo_id: Optional[str] = None
    photo_url: Optional[str] = None
    photo_width: Optional[int] = None
    photo_hight: Optional[int] = None
    photo_latitude: Optional[float] = None
    photo_longitude: Optional[float] = None
    photo_year: Optional[int] = None
    photo_month: Optional[int] = None
    photo_day: Optional[int] = None
    photo_date: Optional[str] = None
    photo_relative_time: Optional[str] = None
    photo_caption: Optional[str] = None
    photo_source: Optional[str] = None
    def to_dict(self):
       return asdict(self)
    def to_json(self):
        return json.dumps(asdict(self))

@dataclass
class Video:
    video_id: Optional[str] = None
    video_thumb_url: Optional[str] = None
    video_url: Optional[str] = None
    video_width: Optional[int] = None
    video_hight: Optional[int] = None
    video_latitude: Optional[float] = None
    video_longitude: Optional[float] = None
    video_year: Optional[int] = None
    video_month: Optional[int] = None
    video_day: Optional[int] = None
    video_date: Optional[str] = None
    video_relative_time: Optional[str] = None
    video_caption: Optional[str] = None
    video_source: Optional[str] = None
    def to_dict(self):
       return asdict(self)
    def to_json(self):
        return json.dumps(asdict(self))