from dataclasses import dataclass, field, asdict
from mapsfiacore.models.photos import Photo, Video
from mapsfiacore.models.aspects import Aspect
from mapsfiacore.models.user import User
from typing import Optional
import json


@dataclass
class Rating:
    rating_count: Optional[int] = None
    rating_media: list[Photo, Video] = field(default_factory=list)
    rating_aspects: list[Aspect] = field(default_factory=list)
    rating_languages: Optional[list] = None
    rating_strings: Optional[list] = None
    def to_dict(self):
       return asdict(self)
    def to_json(self):
        return json.dumps(asdict(self))

@dataclass
class Review:
    id: Optional[str] = None
    rating: Optional[Rating] = None
    user: Optional[User] = None
    timestamp: Optional[int] = None
    relative_time: Optional[str] = None