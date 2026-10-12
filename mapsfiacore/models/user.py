import json
from typing import Optional
from dataclasses import dataclass, asdict

@dataclass
class User:
    id: Optional[int] = None
    name: Optional[str] = None
    review_count: Optional[int] = None
    photo_count: Optional[int] = None
    rating_count: Optional[int] = None
    local_guide_level: Optional[int] = None
    profile_picture: Optional[str] = None
    contributions_url: Optional[str] = None
    photos_contributions_url: Optional[str] = None
    def to_dict(self):
       return asdict(self)
    def to_json(self):
        return json.dumps(asdict(self))
