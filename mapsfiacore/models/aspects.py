from dataclasses import dataclass, field, asdict
from typing import Optional
import json


@dataclass
class AspectOption:
    option_key: Optional[str] = None
    option_label: Optional[str] = None
    option_score: Optional[int | float] = None
    option_description: Optional[str] = None
    def to_dict(self):
       return asdict(self)
    def to_json(self):
        return json.dumps(asdict(self))


@dataclass
class Aspect:
    aspect_key: Optional[str] = None
    aspect_question: Optional[str] = None
    aspect_options: list[AspectOption] = field(default_factory=list)
    aspect_title: Optional[str] = None
    aspect_rating: Optional[int | float] = None
    def to_dict(self):
       return asdict(self)
    def to_json(self):
        return json.dumps(asdict(self))