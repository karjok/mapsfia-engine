"""Pure-Python Google Maps region polygon extractor.

Reproduces the production client's tile flow from a Google Maps place URL:

  1. parse      place URL -> feature id, mid, centroid, camera zoom
  2. region tile GET /maps/vt/pb=...!2sspotlit!...        -> region outline (field f8)
     the request carries a "spotlit" block built from the parsed URL:
       - feature id halves (uint64)
       - /m/ mid
       - centroid as int32(lat*1e7), int32(lng*1e7)
       - a bbox (any sane extent; used to trigger server-side outline lookup)
  3. decode      gzip -> XOR 0x9B -> protobuf -> delta-zigzag -> /16 -> tile-local pts
  4. project     Web-Mercator tile-local -> lon/lat
  5. stitch      merge tile-clipped pieces from all tiles covering the bbox

Tile requests are fetched asynchronously through the shared curl_cffi session
with a semaphore-bounded connection pool; results are cached per tile so the
adaptive radius expansion never refetches a tile.
"""
from __future__ import annotations

import asyncio
import base64
import glob
import gzip
import json
import math
import re
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Optional

from shapely.geometry import shape, mapping
from shapely.ops import unary_union

XOR = 0x9B
DEFAULT_ZOOM_RANGE = (6, 11)
MAX_CONCURRENCY = 10
HTTP_TIMEOUT = 30
_XOR_TABLE = bytes(i ^ XOR for i in range(256))

_FID_RE = re.compile(r"!1s(0x[0-9a-fA-F]+:0x[0-9a-fA-F]+)")
_COORD_RE = re.compile(r"!3d(-?[\d.]+)!4d(-?[\d.]+)")
_CAMERA_RE = re.compile(r"/@(-?[\d.]+),(-?[\d.]+),([\d.]+)z")
_QMID_RE = re.compile(r"!16s([^!?&#]+)")
_BMID_RE = re.compile(r"!16z([^!?&#]+)")
_QCOORD_RE = re.compile(r"^-?[\d.]+,-?[\d.]+$")
_DEFAULT_ZOOM_RE = re.compile(b"/staticmap.*center=([-0-9.]+)(?:%2C|,)([-0-9.]+).*zoom=([0-9.]+)")


@dataclass
class _TileContext:
    """Per-extraction state shared by the tile fetch/decode helpers."""

    session: Any = None
    sem: Any = None
    cache: dict = field(default_factory=dict)
    hi: int = 0
    lo: int = 0
    mid: str = ""
    lat: float = 0.0
    lng: float = 0.0
    hl: str = "en"
    gl: str = "us"
    debug: bool = False
    timeout: float = HTTP_TIMEOUT
    concurrency: int = MAX_CONCURRENCY


class Geojson(MapsFiaBase):
    """Extract Google Maps region outlines as GeoJSON FeatureCollections.

    All parsing, tile math, spotlit-request building, decoding and stitching
    live on this class. The async entrypoint is :meth:`extract_async`; the
    sync ones are :meth:`extract` / :meth:`get_geojson`.
    """

    name = "Geojson"

    # ================================================================ URL parse
    @staticmethod
    def parse_gmaps_url(url: str) -> Optional[dict]:
        """Parse a Google Maps place URL into its components.

        Handles forms like:
          https://www.google.com/maps/place/<Name>/@<lat>,<lng>,<zoom>z/data=!...!1s0x..:0x..!...
          https://www.google.com/maps/place/<Name>/@<lat>,<lng>,<zoom>z
          https://maps.google.com/?q=<lat>,<lng>
        Returns a dict with: query (place name), feature_id, mid, lat, lng, camera_zoom.
        """
        if not url:
            return None
        out = {"url": url, "query": None, "feature_id": None, "mid": None,
               "lat": None, "lng": None, "camera_zoom": None}
        p = urllib.parse.urlparse(url)
        path = p.path or ""
        data = p.fragment or ""

        # place name: /maps/place/<Name>/@...
        m = re.search(r"/maps/place/([^/@]+)", path)
        if m:
            out["query"] = urllib.parse.unquote_plus(m.group(1))

        # camera: /@lat,lng,zoomz  (e.g. .../@3.215997,106.2187135,15.01z/...)
        m = _CAMERA_RE.search(path + "/" + data)
        if m:
            raw_zoom = float(m.group(3))
            out["camera_zoom_raw"] = raw_zoom          # e.g. 15.01
            out["camera_zoom"] = int(round(raw_zoom))  # tile zoom, e.g. 15
            out["cam_lat"], out["cam_lng"] = float(m.group(1)), float(m.group(2))

        # data blob may be in the path or after '#'
        dm = re.search(r"/data=(.*)$", path)
        if dm:
            data = dm.group(1) or data

        # feature id: !1s0x...:0x...
        m = _FID_RE.search(data)
        if m:
            out["feature_id"] = m.group(1)

        # place coordinate: !3d<lat>!4d<lng>
        m = _COORD_RE.search(data)
        if m:
            out["lat"], out["lng"] = float(m.group(1)), float(m.group(2))

        # knowledge-graph mid, two encodings:
        #   !16s%2Fm%2F035bjw   -> percent-encoded literal mid
        #   !16zL20vMDM1Ymp3    -> base64url of the mid
        m = _QMID_RE.search(data)
        if m:
            out["mid"] = urllib.parse.unquote(m.group(1))
        else:
            m = _BMID_RE.search(data)
            if m:
                raw = urllib.parse.unquote(m.group(1))
                try:
                    dec = base64.urlsafe_b64decode(
                        raw + "=" * (-len(raw) % 4)).decode("utf-8", "replace")
                    if dec:
                        out["mid"] = dec
                except Exception:
                    pass

        # fallback coords: @ handled above; also ?q=lat,lng
        if out["lat"] is None:
            qs = urllib.parse.parse_qs(p.query)
            q = (qs.get("q") or [None])[0]
            if q and _QCOORD_RE.match(q):
                a, b = q.split(",")
                out["lat"], out["lng"] = float(a), float(b)

        # camera-only fallback for the anchor point
        if out["lat"] is None and "cam_lat" in out:
            out["lat"], out["lng"] = out["cam_lat"], out["cam_lng"]

        # normalise zoom to int
        if out["camera_zoom"] is not None:
            out["camera_zoom"] = int(round(out["camera_zoom"]))
        return out

    # ============================================================ protobuf bits
    @staticmethod
    def _rv(b: bytes, i: int):
        s = 0
        v = 0
        while True:
            x = b[i]
            i += 1
            v |= (x & 0x7F) << s
            if not (x & 0x80):
                break
            s += 7
            if s > 63:
                raise ValueError
        return v, i

    @staticmethod
    def _pb_fields(b: bytes):
        out = []
        i = 0
        while i < len(b):
            try:
                k, i2 = Geojson._rv(b, i)
                f, wt = k >> 3, k & 7
                if f == 0 or f > 50_000_000:
                    break
                if wt == 0:
                    v, i3 = Geojson._rv(b, i2)
                    out.append((f, 0, v))
                    i = i3
                elif wt == 2:
                    ln, i3 = Geojson._rv(b, i2)
                    if i3 + ln > len(b):
                        break
                    out.append((f, 2, b[i3:i3 + ln]))
                    i = i3 + ln
                elif wt == 1:
                    out.append((f, 1, b[i2:i2 + 8]))
                    i = i2 + 8
                elif wt == 5:
                    out.append((f, 5, b[i2:i2 + 4]))
                    i = i2 + 4
                else:
                    break
            except Exception:
                break
        return out

    @staticmethod
    def _zigzag(u: int) -> int:
        return (u >> 1) ^ -(u & 1)

    @staticmethod
    def _xor9b(b: bytes) -> bytes:
        return b.translate(_XOR_TABLE)

    @staticmethod
    def _i32(v) -> int:
        return int(round(v * 1e7)) & 0xFFFFFFFF

    @staticmethod
    def _fid_halves(fid: str) -> tuple[int, int]:
        a, b = fid.split(":")
        return int(a, 16), int(b, 16)

    # ================================================================ tile math
    @staticmethod
    def _lonlat_to_tile(lng, lat, z):
        n = 2 ** z
        x = (lng + 180.0) / 360.0 * n
        lat = math.radians(max(min(lat, 85.05112878), -85.05112878))
        y = (1 - math.log(math.tan(lat) + 1 / math.cos(lat)) / math.pi) / 2 * n
        return x, y

    @staticmethod
    def _tile_local_to_lonlat(px, py, z, tx, ty):
        n = 2 ** z
        X = (tx + px / 256.0) / n
        Y = (ty + py / 256.0) / n
        lng = X * 360.0 - 180.0
        lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * Y))))
        return lng, lat

    # ============================================================ tile requests
    @staticmethod
    def spotlit_tile_url(z, x, y, fid_hi, fid_lo, mid, lat, lng, gcid="",
                         bbox=None, hl="id", gl="us"):
        """Build the /maps/vt/pb= spotlit tile request.

        fid_hi/fid_lo = the two uint64 halves of the feature id (0x...:0x...).
        bbox = (lat1,lng1,lat2,lng2) - any non-degenerate extent works; the server
        uses it only to size the outline lookup. Default: +-1 degree around centroid.
        """
        if bbox is None:
            bbox = (lat - 1, lng - 1, lat + 1, lng + 1)
        mid_b64 = base64.b64encode(mid.encode()).decode().rstrip("=")
        block = (f"!27m22!299174093m21!14m20!1m16!1m2!1y{fid_hi}!2y{fid_lo}"
                 f"!2z{mid_b64}"
                 f"!4m2!1x{Geojson._i32(lat)}!2x{Geojson._i32(lng)}!8b1"
                 f"!12m6!1m2!1x{Geojson._i32(bbox[0])}!2x{Geojson._i32(bbox[1])}"
                 f"!2m2!1x{Geojson._i32(bbox[2])}!2x{Geojson._i32(bbox[3])}"
                 f"!15sgcid%3A{gcid}!2b0!6b0!8b0")
        return (f"https://www.google.com/maps/vt/pb=!1m4!1m3!1i{z}!2i{x}!3i{y}"
                f"!2m3!1e0!2sm!3i797563078!2m2!1e2!2sspotlit"
                f"!3m8!2s{hl}!3s{gl}!5e1105!12m4!1e68!2m2!1sset!2sRoadmap!4e1"
                f"!6m9!1e12!2i2!26m1!1b1!28e3!39b1!44e2!50e0!71b1"
                f"!23i1368782!23i1368785!23i4861626!23i10211310!23i1381938"
                f"!23i47054629!23i47029525!23i72272233!23i72272234!23i72272236"
                f"!23i94255677!23i72860224!23i100799651!23i72549439"
                f"{block}!28i797")

    @staticmethod
    def _http_sync(url: str, timeout: float = HTTP_TIMEOUT) -> bytes:
        req = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "Referer": "https://www.google.com/maps",
            "Accept-Language": "en-US,en;q=0.9"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()

    @staticmethod
    def _fetch_tiles_sync(reqs, concurrency, timeout):
        def one(req):
            key, url = req
            try:
                return key, Geojson._http_sync(url, timeout), None
            except Exception as e:
                return key, None, e

        with ThreadPoolExecutor(max_workers=max(1, concurrency)) as ex:
            return list(ex.map(one, reqs))

    # ================================================================ tile decode
    @classmethod
    def region_polygons_from_tile(cls, body: bytes) -> list[dict]:
        """Extract f8 (spotlit outline) features from a /maps/vt/pb= response."""
        d = gzip.decompress(body) if body[:2] == b"\x1f\x8b" else body
        pb = cls._xor9b(d)
        out = []
        for f, w, v in cls._pb_fields(pb):
            if f != 8 or w != 2:
                continue
            for f2, w2, v2 in cls._pb_fields(v):
                if f2 != 1 or w2 != 2:
                    continue
                outer = cls._pb_fields(v2)
                geom = next((x[2] for x in outer if x[0] == 1 and x[1] == 2), None)
                cnt = next((x[2] for x in outer if x[0] == 5 and x[1] == 0), None)
                rings = next((x[2] for x in outer if x[0] == 4 and x[1] == 2), None)
                if geom is None:
                    continue
                sub = cls._pb_fields(geom)
                if sub and any(x[0] == 1 and x[1] == 2 for x in sub):
                    geom = next(x[2] for x in sub if x[0] == 1 and x[1] == 2)
                    cnt = next((x[2] for x in sub if x[0] == 5 and x[1] == 0), None) or cnt
                    rings = next((x[2] for x in sub if x[0] == 4 and x[1] == 2), None) or rings
                pts = []
                i = 0
                x = 0
                y = 0
                try:
                    while i < len(geom):
                        k, i = cls._rv(geom, i)
                        x += cls._zigzag(k)
                        k, i = cls._rv(geom, i)
                        y += cls._zigzag(k)
                        pts.append((x / 16.0, y / 16.0))
                except Exception:
                    pass
                # f4 is PACKED varints = ring END indices; JS appends the count.
                ends = None
                if rings is not None:
                    ends = []
                    j = 0
                    try:
                        while j < len(rings):
                            k, j = cls._rv(rings, j)
                            ends.append(k)
                    except Exception:
                        ends = None
                    if ends is not None:
                        ends = ends + [cnt or len(pts)]
                if len(pts) >= 3:
                    out.append({"pts": pts, "cnt": cnt or len(pts), "rings": ends})
        return out

    @staticmethod
    def split_rings(pts, rings):
        """rings = decoded END indices (f4 values + count). Returns list of rings."""
        if rings:
            out = []
            start = 0
            for end in rings:
                end = min(end, len(pts))
                out.append(pts[start:end])
                start = end
            return [r for r in out if r]
        return [pts]

    @staticmethod
    def is_tile_bbox(ring) -> bool:
        if len(ring) != 4:
            return False
        xs = sorted(p[0] for p in ring)
        ys = sorted(p[1] for p in ring)
        return (abs(xs[0] + 1.5) < 1.5 and abs(xs[-1] - 257.5) < 1.5
                and abs(ys[0] + 1.5) < 1.5 and abs(ys[-1] - 257.5) < 1.5)

    @staticmethod
    def _pick_entry(polys):
        """Choose the best f8 entry for a tile: multi-ring > single-ring > flattened."""
        for p in polys:
            if p["rings"] and len(p["rings"]) > 1:
                return p
        for p in polys:
            if p["rings"] and len(p["rings"]) == 1:
                return p
        return next((p for p in polys if p["rings"] is None), None)

    @staticmethod
    def _clipped_at_block_edge(pieces, tx0, ty0, radius) -> bool:
        """True if any piece is clipped on the OUTER boundary of the fetched block
        (meaning more tiles are needed to complete the outline)."""
        for (z, x, y, r) in pieces:
            if x == tx0 - radius and any(px < 2 for px, py in r):
                return True
            if x == tx0 + radius and any(px > 254 for px, py in r):
                return True
            if y == ty0 - radius and any(py < 2 for px, py in r):
                return True
            if y == ty0 + radius and any(py > 254 for px, py in r):
                return True
        return False

    @classmethod
    def _decode_tile(cls, body, z, x, y, diag=None):
        polys = cls.region_polygons_from_tile(body)
        if diag is not None and polys:
            diag("z%s tile(%s,%s): %s", z, x, y,
                 [(p['cnt'], p['rings']) for p in polys])
        chosen = cls._pick_entry(polys)
        if chosen is None:
            return []
        return [(z, x, y, r) for r in cls.split_rings(chosen["pts"], chosen["rings"])
                if len(r) >= 3 and not cls.is_tile_bbox(r)]

    @staticmethod
    def _merge_pieces(features):
        """Union tile-clipped polygons to remove seams. Falls back to raw pieces."""
        try:
            for p in glob.glob("/home/*/.local/share/uv/tools/pip/lib/python3.12/site-packages"):
                if p not in sys.path:
                    sys.path.insert(0, p)
            if not features:
                return features
            merged = unary_union([shape(f["geometry"]) for f in features])
            out = []
            parts = [merged] if merged.geom_type == "Polygon" else list(getattr(merged, "geoms", []))
            parts.sort(key=lambda g: g.area, reverse=True)
            for i, g in enumerate(parts):
                if g.area <= 0:
                    continue
                geom = mapping(g)
                out.append({"type": "Feature",
                            "properties": {"part": i, "area": round(g.area, 8),
                                           "holes": len(getattr(g, "interiors", []))},
                            "geometry": geom})
            return out if out else features
        except Exception:
            return features

    # ============================================================ async fetching
    @staticmethod
    async def _body_bytes(resp) -> bytes:
        """Read a response body from either an aiohttp or curl_cffi response."""
        read = getattr(resp, "read", None)
        if callable(read):
            data = read()
            if asyncio.iscoroutine(data):
                data = await data
            if isinstance(data, bytes):
                return data
        content = getattr(resp, "content", None)
        if callable(content):
            content = content()
            if asyncio.iscoroutine(content):
                content = await content
        if isinstance(content, bytes):
            return content
        raise RuntimeError("cannot read response body")

    async def _fetch_one(self, ctx: _TileContext, key, url):
        try:
            async with ctx.sem:
                resp = await ctx.session.get(url, timeout=ctx.timeout)
                status = getattr(resp, "status_code", None)
                if status is None:
                    status = getattr(resp, "status", 200)
                if status >= 400:
                    raise RuntimeError(f"HTTP {status}")
                return key, await self._body_bytes(resp), None
        except Exception as e:
            return key, None, e

    async def _fill_cache(self, ctx: _TileContext, z, tiles):
        missing = [(x, y) for (x, y) in tiles if (z, x, y) not in ctx.cache]
        if not missing:
            return
        bbox = (ctx.lat - 1, ctx.lng - 1, ctx.lat + 1, ctx.lng + 1)
        reqs = [((z, x, y),
                 self.spotlit_tile_url(z, x, y, ctx.hi, ctx.lo, ctx.mid, ctx.lat,
                                       ctx.lng, bbox=bbox, hl=ctx.hl, gl=ctx.gl))
                for (x, y) in missing]
        if ctx.session is not None:
            results = await asyncio.gather(
                *(self._fetch_one(ctx, key, url) for key, url in reqs))
        else:
            loop = asyncio.get_running_loop()
            results = await loop.run_in_executor(
                None, self._fetch_tiles_sync, reqs, ctx.concurrency, ctx.timeout)
        for key, body, err in results:
            if body is not None:
                ctx.cache[key] = body
            elif ctx.debug and err is not None:
                self._diag("tile %s/%s/%s err: %s", key[0], key[1], key[2], err)

    # ============================================================ adaptive walk
    async def _collect_pieces(self, ctx: _TileContext, zooms):
        """Adaptive zoom walk. Returns (pieces, used_zoom); tiles are fetched
        concurrently and cached across radius/zoom expansions."""
        pieces = []
        used_zoom = None
        for z in zooms:
            N = 2 ** z
            tx0, ty0 = (int(v) for v in self._lonlat_to_tile(ctx.lng, ctx.lat, z))
            local = None
            last_radius = 1
            for radius in (1, 2, 3):
                last_radius = radius
                tiles = [(x, y) for x in range(tx0 - radius, tx0 + radius + 1)
                         for y in range(ty0 - radius, ty0 + radius + 1)
                         if 0 <= x < N and 0 <= y < N]
                await self._fill_cache(ctx, z, tiles)
                acc = []
                for (x, y) in tiles:
                    body = ctx.cache.get((z, x, y))
                    if not body:
                        continue
                    acc.extend(self._decode_tile(body, z, x, y,
                                                 self._diag if ctx.debug else None))
                if acc:
                    local = acc
                    # stop expanding when nothing is clipped at the block boundary
                    if not self._clipped_at_block_edge(acc, tx0, ty0, radius):
                        break
            if not local:
                continue
            npts = sum(len(r) for _, _, _, r in local)
            clipped = self._clipped_at_block_edge(local, tx0, ty0, last_radius)
            if ctx.debug:
                self._diag("  z%s: %s pieces, %s pts, clipped=%s",
                           z, len(local), npts, clipped)
            # Rule: keep the FINEST complete (unclipped) outline.
            #   - unclipped -> remember it and keep walking up for more detail
            #   - clipped   -> too fine for the feature; stop, keep the previous best
            # A coarse unclipped result is kept as a fallback but does NOT stop the
            # walk, so small features still reach their detailed zooms.
            if not clipped:
                pieces = local
                used_zoom = z
            else:
                if pieces:
                    break
                # nothing complete yet: keep this clipped result as a fallback
                pieces = local
                used_zoom = z
                break

        if not pieces:
            # fallback: accept whatever any zoom produced (may be clipped)
            for z in zooms:
                N = 2 ** z
                tx0, ty0 = (int(v) for v in self._lonlat_to_tile(ctx.lng, ctx.lat, z))
                tiles = [(x, y) for x in range(tx0 - 2, tx0 + 3)
                         for y in range(ty0 - 2, ty0 + 3)
                         if 0 <= x < N and 0 <= y < N]
                await self._fill_cache(ctx, z, tiles)
                local = []
                for (x, y) in tiles:
                    body = ctx.cache.get((z, x, y))
                    if not body:
                        continue
                    local.extend(self._decode_tile(body, z, x, y, None))
                if local:
                    pieces = local
                    used_zoom = z
                    break
        return pieces, used_zoom

    # ================================================================ extract
    async def extract_async(self, out_path: Optional[str] = None, debug: Optional[bool] = None,
                            zoom: Optional[int] = None, gl: Optional[str] = None,
                            hl: Optional[str] = None, url: Optional[str] = None,
                            concurrency: Optional[int] = None,
                            timeout: Optional[float] = None) -> dict:
        """Async extraction. See :meth:`get_geojson` for the argument semantics."""
        cfg = self.config
        debug = cfg.debug if debug is None else debug
        gl = gl or cfg.gl
        hl = hl or cfg.hl
        concurrency = max(1, int(concurrency or cfg.max_concurrency))
        timeout = cfg.timeout if timeout is None else timeout

        parsed = self.parse_gmaps_url(url)
        if not parsed or not parsed.get("feature_id") or parsed.get("lat") is None:
            self.logger.warning("no url or url missing feature id/coords")
            return {"error": "no url or url missing feature id/coords", "features": []}
        query = parsed.get("query") or parsed["feature_id"]
        pick = {"label": parsed.get("query"), "feature_id": parsed["feature_id"],
                "mid": parsed.get("mid"), "lat": parsed["lat"], "lng": parsed["lng"],
                "from_url": True}

        # Zoom priority:
        #   1. explicit zoom                 -> use exactly that zoom, no walk
        #   2. zoom parsed from the URL path -> use exactly that zoom, no walk
        #   3. otherwise                     -> walk the default zoom band
        if zoom is None and parsed.get("camera_zoom"):
            zoom = max(1, min(21, parsed["camera_zoom"]))
            if debug:
                self._diag("using zoom %s from url path", zoom)
        if debug:
            self._diag("from url: %s", pick)
        if zoom:
            zooms = [zoom]
            if debug:
                self._diag("using fixed zoom %s (no walk)", zoom)
        else:
            zooms = list(range(DEFAULT_ZOOM_RANGE[0], DEFAULT_ZOOM_RANGE[1] + 1))
            if debug:
                self._diag("walk zoom range %s", DEFAULT_ZOOM_RANGE)

        hi, lo = self._fid_halves(pick["feature_id"])
        session, close_session = await self._resolve_tile_session()
        ctx = _TileContext(
            session=session,
            sem=asyncio.Semaphore(concurrency) if session is not None else None,
            hi=hi, lo=lo, mid=pick.get("mid") or "", lat=pick["lat"], lng=pick["lng"],
            hl=hl, gl=gl, debug=debug, timeout=timeout, concurrency=concurrency)
        try:
            pieces, used_zoom = await self._collect_pieces(ctx, zooms)
        finally:
            if close_session and session is not None:
                await session.close()

        raw = self._project_pieces(pieces)
        # merge tile-clipped pieces into clean outlines (shapely if available)
        merged_feats = self._merge_pieces(raw)
        gj = {"type": "FeatureCollection",
              "features": merged_feats,
              "properties": {"query": query, "picked": pick, "zoom": used_zoom,
                             "tile_pieces": len(raw)}}
        if out_path:
            with open(out_path, "w") as fh:
                json.dump(gj, fh)
        return gj

    async def _resolve_tile_session(self):
        """Pick the curl_cffi session for tile fetches; returns ``(session, close_it)``."""
        cfg = self.config
        if cfg.async_session is False:
            return await self._own_async_session(), True
        if cfg.async_session is not None:
            return cfg.async_session, False
        return await self.aget_session(), False

    def _project_pieces(self, pieces) -> list[dict]:
        """Project tile-local pieces to lon/lat, dropping duplicate rings (same
        tile + same size = the two simplification levels Google returns)."""
        raw = []
        seen = set()
        for (zz, xx, yy, ring) in pieces:
            key = (zz, xx, yy, len(ring), round(sum(p[0] for p in ring), 1))
            if key in seen:
                continue
            seen.add(key)
            coords = [list(self._tile_local_to_lonlat(px, py, zz, xx, yy)) for px, py in ring]
            if coords[0] != coords[-1]:
                coords.append(coords[0])
            raw.append({"type": "Feature",
                        "properties": {"tile": f"{zz}/{xx}/{yy}", "n": len(ring)},
                        "geometry": {"type": "Polygon", "coordinates": [coords]}})
        return raw
    
    def get_default_centroid(self):
        base = self._http_sync("https://www.google.com/maps/")
        default = re.search(_DEFAULT_ZOOM_RE, base)
        if default:
            lat = float(default.group(1).decode("utf-8"))
            lng = float(default.group(2).decode("utf-8"))
            zoom = float(default.group(3).decode("utf-8"))
            return (lat, lng, zoom)
        else:
            return (-6.3275008, 106.954752, 15.0)
        
    def build_pb(
            self,
            lat:float,
            lng:float,
            range_m: Optional[float] = None,
            width: int = 1204,
            height: int = 933,
            page_size: int = 20,
            offset: int = 0,
        ) -> str:
            if range_m is None:
                range_m = 2000.0

            return (
                f"!4m12"
                f"!1m3!1d{range_m:.0f}!2d{lng:.9f}!3d{lat:.9f}"
                f"!2m3!1f0!2f0!3f0"
                f"!3m2!1i{width}!2i{height}"
                f"!4f13.1"
                f"!7i{page_size}!8i{offset}!10b1"
            )

    def extract(self, out_path: Optional[str] = None, debug: Optional[bool] = None,
                zoom: Optional[int] = None, gl: Optional[str] = None,
                hl: Optional[str] = None, url: Optional[str] = None,
                concurrency: Optional[int] = None,
                timeout: Optional[float] = None) -> dict:
        """Extract a region polygon from a Google Maps place URL.

        The URL's feature id, mid, coordinates and camera zoom are parsed and used
        directly to drive the spotlit tile requests.
        """
        return run_sync(self.extract_async(out_path=out_path, debug=debug, zoom=zoom,
                                           gl=gl, hl=hl, url=url,
                                           concurrency=concurrency, timeout=timeout))

    # ============================================================= public API
    def get_geojson(self, url: Optional[str] = None, zoom: Optional[int] = None,
                    hl: Optional[str] = None, gl: Optional[str] = None,
                    out_path: Optional[str] = None, debug: Optional[bool] = None,
                    concurrency: Optional[int] = None,
                    timeout: Optional[float] = None) -> dict:
        """Return a GeoJSON FeatureCollection for a Google Maps place URL.

        Args:
            url:         a Google Maps place URL. Its feature id, mid, coordinates
                         and camera zoom are parsed and used directly.
            zoom:        force an exact tile zoom (int). Highest priority: when set,
                         no automatic zoom walk is performed. When omitted and the
                         URL carries a zoom in its path, that zoom is used exactly.
                         Otherwise the zoom is chosen automatically via an adaptive
                         walk of the default zoom band.
            hl, gl:      language / country hints for the tile request.
            out_path:    optional path; when given the GeoJSON is also written to disk.
            debug:       log per-tile diagnostics.
            concurrency: max simultaneous tile connections (semaphore limit).
            timeout:     per-request timeout in seconds.

        Returns:
            dict: a GeoJSON FeatureCollection, or a dict with "error" and an empty
            "features" list on failure.
        """
        return self.extract(out_path=out_path, debug=debug, zoom=zoom,
                            gl=gl, hl=hl, url=url, concurrency=concurrency,
                            timeout=timeout)

    async def get_geojson_async(self, url: Optional[str] = None, zoom: Optional[int] = None,
                                hl: Optional[str] = None, gl: Optional[str] = None,
                                out_path: Optional[str] = None,
                                debug: Optional[bool] = None,
                                concurrency: Optional[int] = None,
                                timeout: Optional[float] = None) -> dict:
        """Async version of :meth:`get_geojson`. Safe to gather() many URLs at once."""
        return await self.extract_async(out_path=out_path, debug=debug, zoom=zoom,
                                        gl=gl, hl=hl, url=url, concurrency=concurrency,
                                        timeout=timeout)
