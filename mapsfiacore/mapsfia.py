"""``MapsFia`` - one class exporting search, suggestions and GeoJSON.

The three capability classes are created as children, so a single ``MapsFia``
instance shares one config and one logger tree with them::

    maps = MapsFia(hl="id", gl="id", max_concurrency=20)
    maps.configure_logging(logging.INFO)
    maps.search("warung kopi")            # -> maps.parser (Search)
    maps.get_suggestions("warung kopi")   # -> maps.suggestions
    maps.get_geojson(url)                 # -> maps.geojson

Log lines are emitted as ``MapsFia.Search.INFO``, ``MapsFia.Suggestions.INFO``
and ``MapsFia.Geojson.INFO`` because each child logger is nested under the
parent logger name.
"""
from __future__ import annotations

import logging
from typing import Any, List, Optional

from mapsfiacore.base import MapsFiaBase, MapsFiaConfig
from mapsfiacore.cores.get_geojson import Geojson
from mapsfiacore.search import Search
from mapsfiacore.suggestions import Suggestions
from mapsfiacore.models.models import Place, Suggestion


class MapsFia(MapsFiaBase):
    """Facade over :class:`Search`, :class:`Suggestions` and :class:`Geojson`.

    Args:
        config:           explicit :class:`~mapsfiacore.base.MapsFiaConfig`.
        logger:           explicit logger (defaults to ``MapsFia``).
        **config_overrides: any config field, e.g. ``hl``, ``gl``,
                          ``max_concurrency``, ``session``, ``async_session``,
                          ``debug``, ``timeout``.
    """

    name = "MapsFia"

    def __init__(self, config: Optional[MapsFiaConfig] = None,
                 logger: Optional[logging.Logger] = None, **config_overrides: Any):
        super().__init__(config=config, parent=None, logger=logger, **config_overrides)
        # Children inherit config + logger from this instance.
        self.parser = Search(parent=self)          # search + response parser
        self.suggestions = Suggestions(parent=self)
        self.geojson = Geojson(parent=self)

    # ------------------------------------------------------------ search
    @property
    def search_client(self) -> Search:
        return self.parser

    def search(self, query: Optional[str] = None, pb: Optional[str] = None,
               lat: Optional[float] = None, lon: Optional[float] = None,
               lang: Optional[str] = None, gl: Optional[str] = None,
               session: Optional[str] = None) -> List[Place]:
        """Run a Google Maps search and return :class:`mapsfiacore.models.Place` objects."""
        return self.parser.search(query=query, pb=pb, lat=lat, lon=lon,
                                  lang=lang, gl=gl, session=session)

    async def asearch(self, query: Optional[str] = None, pb: Optional[str] = None,
                      lat: Optional[float] = None, lon: Optional[float] = None,
                      lang: Optional[str] = None, gl: Optional[str] = None,
                      session: Optional[str] = None, http: Any = None) -> List[Place]:
        """Async search; safe to gather() many queries at once."""
        return await self.parser.asearch(query=query, pb=pb, lat=lat, lon=lon,
                                         lang=lang, gl=gl, session=session, http=http)

    def prepare_search(self, query: Optional[str] = None, pb: Optional[str] = None,
                       lat: Optional[float] = None, lon: Optional[float] = None,
                       lang: Optional[str] = None, gl: Optional[str] = None,
                       session: Optional[str] = None) -> Any:
        """Build the search request without sending it."""
        return self.parser.prepare_search(query=query, pb=pb, lat=lat, lon=lon,
                                          lang=lang, gl=gl, session=session)

    # ------------------------------------------------------------ suggestions
    def get_suggestions(self, query: str, hl: Optional[str] = None,
                        gl: Optional[str] = None,
                        session: Optional[str] = None) -> List[Suggestion]:
        """Fetch autocomplete suggestions for a query."""
        return self.suggestions.get_suggestions(query, hl=hl, gl=gl, session=session)

    async def aget_suggestions(self, query: str, hl: Optional[str] = None,
                               gl: Optional[str] = None, session: Optional[str] = None,
                               http: Any = None) -> List[Suggestion]:
        """Async suggestions; safe to gather() many queries at once."""
        return await self.suggestions.aget_suggestions(query, hl=hl, gl=gl,
                                                       session=session, http=http)

    def prepare_suggestions(self, query: str, hl: Optional[str] = None,
                            gl: Optional[str] = None,
                            session: Optional[str] = None) -> Any:
        """Build the suggestions request without sending it."""
        return self.suggestions.prepare_suggestions(query, hl=hl, gl=gl, session=session)

    # ------------------------------------------------------------ geojson
    def get_geojson(self, url: Optional[str] = None, zoom: Optional[int] = None,
                    hl: Optional[str] = None, gl: Optional[str] = None,
                    out_path: Optional[str] = None, debug: Optional[bool] = None,
                    concurrency: Optional[int] = None,
                    timeout: Optional[float] = None) -> dict:
        """Extract a region outline as a GeoJSON FeatureCollection."""
        return self.geojson.get_geojson(url=url, zoom=zoom, hl=hl, gl=gl,
                                        out_path=out_path, debug=debug,
                                        concurrency=concurrency, timeout=timeout)

    async def get_geojson_async(self, url: Optional[str] = None, zoom: Optional[int] = None,
                                hl: Optional[str] = None, gl: Optional[str] = None,
                                out_path: Optional[str] = None,
                                debug: Optional[bool] = None,
                                concurrency: Optional[int] = None,
                                timeout: Optional[float] = None) -> dict:
        """Async extraction; safe to gather() many URLs at once."""
        return await self.geojson.get_geojson_async(
            url=url, zoom=zoom, hl=hl, gl=gl, out_path=out_path, debug=debug,
            concurrency=concurrency, timeout=timeout)
