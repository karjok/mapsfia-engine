from dataclasses import asdict, dataclass, field
from typing import Optional
import json

@dataclass
class Suggestion:
    name:Optional[str] = None
    fid:Optional[str] = None
    gmid:Optional[str] = None
    label:Optional[str] = None
    code:Optional[int] = None
    lat:Optional[float] = None
    lng:Optional[float] = None
    address:Optional[str] = None
    kind:Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)
    def to_json(self) -> str:
        return json.dumps(asdict(self))
    
@dataclass
class Suggestions:
    query: Optional[str] = None
    sugestions: list[Suggestion] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
    def to_json(self) -> str:
        return json.dumps(asdict(self))