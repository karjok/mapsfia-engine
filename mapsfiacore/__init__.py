"""MapsFia - Google Maps search, suggestions and GeoJSON extraction.

Quick start::

    from mapsfiacore import MapsFia

    maps = MapsFia(hl="id", gl="us", max_concurrency=10)
    places = maps.search("warung kopi")
    ideas = maps.get_suggestions("warung kopi")
    gj = maps.get_geojson(url="https://www.google.com/maps/place/...")

Each capability is also usable standalone::

    from mapsfiacore import Search, Suggestions, Geojson

    search = Search(hl="id", gl="id")
    suggestions = Suggestions(parent=search)   # inherits config + logger
    geojson = Geojson(max_concurrency=20)
"""
from mapsfiacore.base import (
    DEFAULT_GL,
    DEFAULT_HL,
    DEFAULT_MAX_CONCURRENCY,
    DEFAULT_TIMEOUT,
    LOG_DATEFMT,
    LOG_FORMAT,
    MapsFiaBase,
    MapsFiaConfig,
    close_loop_sessions,
    run_sync,
)
from mapsfiacore.cores.get_geojson import Geojson
from mapsfiacore.mapsfia import MapsFia
from mapsfiacore.models.models import Photo, Place, RelatedPlace, Suggestion
from mapsfiacore.search import Search
from mapsfiacore.suggestions import Suggestions

__all__ = [
    "MapsFia",
    "MapsFiaBase",
    "MapsFiaConfig",
    "Search",
    "Suggestions",
    "Geojson",
    "Place",
    "Suggestion",
    "Photo",
    "RelatedPlace",
    "run_sync",
    "close_loop_sessions",
    "DEFAULT_HL",
    "DEFAULT_GL",
    "DEFAULT_MAX_CONCURRENCY",
    "DEFAULT_TIMEOUT",
    "LOG_FORMAT",
    "LOG_DATEFMT",
]
