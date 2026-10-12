"""Google Maps autocomplete suggestions.

``Suggestions`` is intentionally small: it builds the ``/s?tbm=map...suggest=p``
request (the ``pb`` blob is the one captured from the real Maps client), sends
it through the shared curl_cffi session and parses the reply into
:class:`mapsfiacore.models.Suggestion` objects.
"""
from __future__ import annotations

import json
import re
import time
from typing import Any, List, Optional

from mapsfiacore.base import HttpSpec, MapsFiaBase, run_sync
from mapsfiacore.search import TYPE_KIND
from mapsfiacore.models.models import Suggestion

URL = "https://www.google.com"

# pb fetched from a real google maps suggestion request using a browser.
_SUGGEST_PB = (
    '!2i12!4m12!1m3!1d27168336.765021317!2d-95.677068!3d37.06250000000001'
    '!2m3!1f0!2f0!3f0!3m2!1i1280!2i800!4f13.1!7i20!10b1!12m25!1m5!18b1!30b1'
    '!31m1!1b1!34e1!2m4!5m1!6e2!20e3!39b1!10b1!12b1!13b1!16b1!17m1!3e1'
    '!20m3!5e2!6b1!14b1!46m1!1b0!96b1!99b1!19m4!2m3!1i360!2i120!4i8'
    '!20m57!2m2!1i203!2i100!3m2!2i4!5b1!6m6!1m2!1i86!2i86!1m2!1i408!2i240'
    '!7m33!1m3!1e1!2b0!3e3!1m3!1e2!2b1!3e2!1m3!1e2!2b0!3e3!1m3!1e8!2b0'
    '!3e3!1m3!1e10!2b0!3e3!1m3!1e10!2b1!3e2!1m3!1e10!2b0!3e4!1m3!1e9!2b1'
    '!3e2!2b1!9b0!15m8!1m7!1m2!1m1!1e2!2m2!1i195!2i195!3i20!22m3'
    '!1s0--7apyNAaSq4-EP64axsQ4!7e81!17s0--7apyNAaSq4-EP64axsQ4:93!23m2'
    '!4b1!10b1!24m109!1m27!13m9!2b1!3b1!4b1!6i1!8b1!9b1!14b1!20b1!25b1'
    '!18m16!3b1!4b1!5b1!6b1!9b1!13b1!14b1!17b1!20b1!21b1!22b1!32b1!33m1'
    '!1b1!34b1!36e2!10m1!8e3!11m1!3e1!17b1!20m2!1e3!1e6!24b1!25b1!26b1'
    '!27b1!29b1!30m1!2b1!36b1!37b1!39m3!2m2!2i1!3i1!43b1!52b1!54m1!1b1'
    '!55b1!56m1!1b1!61m2!1m1!1e1!65m5!3m4!1m3!1m2!1i224!2i298!72m22!1m8'
    '!2b1!5b1!7b1!12m4!1b1!2b1!4m1!1e1!4b1!8m10!1m6!4m1!1e1!4m1!1e3!4m1'
    '!1e4!3sother_user_google_review_posts__and__hotel_and_vr_partner_review_posts'
    '!6m1!1e1!9b1!89b1!90m2!1m1!1e2!98m3!1b1!2b1!3b1!103b1!113b1!114m3!1b1'
    '!2m1!1b1!117b1!122m1!1b1!126b1!127b1!128m1!1b1!26m4!2m3!1i80!2i92!4i8'
    '!34m19!2b1!3b1!4b1!6b1!8m6!1b1!3b1!4b1!5b1!6b1!7b1!9b1!12b1!14b1!20b1'
    '!23b1!25b1!26b1!31b1!37m1!1e81!47m0!49m10!3b1!6m2!1b1!2b1!7m2!1e3!2b1'
    '!8b1!9b1!10e2!61b1!67m5!7b1!10b1!14b1!15m1!1b0!69i797!77b1'
)


class Suggestions(MapsFiaBase):
    """Fetch Google Maps autocomplete suggestions for a query."""

    name = "Suggestions"

    # ================================================================ request
    def build_suggestions_params(self, query: str, hl: Optional[str] = None,
                                 gl: Optional[str] = None,
                                 pb:Optional[str] = None,
                                 session: Optional[str] = None) -> dict:
        cfg = self.config
        sess = session or self._session_id()
        ts = int(time.time() * 1000)
        if not pb and not cfg.pb:
            pb = _SUGGEST_PB
            pb = pb.replace("!2i12!", "!2i1!", 1)
            pb = re.sub(r"(!22m3!1s)[^!]+", r"\g<1>" + sess, pb)
            pb = re.sub(r"(!17s)[^!]+", r"\g<1>" + sess + "%3A1", pb)
        else:
            pb = pb or cfg.pb
        params = {
            "tbm": "map",
            "gs_ri": "maps",
            "suggest": "p",
            "hl": hl or cfg.hl,
            "gl": gl or cfg.gl,
            "psi": f"{sess}.{ts}.1",
            "q": query,
            "pb": pb,
            "authuser": 0,
            "ech": 1,
        }
        return params

    def prepare_suggestions(self, query: str, hl: Optional[str] = None,
                            gl: Optional[str] = None,
                            session: Optional[str] = None) -> HttpSpec:
        """Build the request as an :class:`~mapsfiacore.base.HttpSpec` (no I/O)."""
        return HttpSpec(method="GET", path="/s",
                        params=self.build_suggestions_params(query, hl, gl, session),
                        timeout=self.config.timeout, kind="html")

    # ================================================================ parsing
    def _parse_suggestions(self, text: str) -> List[Suggestion]:
        if text.startswith(")]}"):
            text = text[5:]
        data = json.loads(text)
        block = data[0] if data and isinstance(data[0], list) else None
        entries = block[1] if block and len(block) > 1 and isinstance(block[1], list) else []
        suggestions: List[Suggestion] = []
        for e in entries:
            if not isinstance(e, list) or len(e) < 23 or not isinstance(e[22], list):
                continue
            meta = e[22]
            suggestion = {"label": None, "feature_id": None, "mid": None, "lat": None,
                          "lng": None, "type_code": None, "kind": None}
            try:
                suggestion["label"] = meta[0][0] if meta and isinstance(meta[0], list) else None
            except Exception:
                pass
            fb = meta[13][0] if len(meta) > 13 and isinstance(meta[13], list) and meta[13] else None
            if fb and isinstance(fb[0], str) and fb[0].startswith("0x"):
                suggestion["feature_id"] = fb[0]
                if len(fb) > 10 and isinstance(fb[10], str):
                    suggestion["mid"] = fb[10]
            ll = meta[11] if len(meta) > 11 else None
            if isinstance(ll, list) and len(ll) >= 4:
                suggestion["lat"], suggestion["lng"] = ll[2], ll[3]
            # type code: meta[7] = [None, 38, [<code>]]
            t7 = meta[7] if len(meta) > 7 else None
            if isinstance(t7, list) and len(t7) > 2 and isinstance(t7[2], list) and t7[2]:
                suggestion["type_code"] = t7[2][0]
                suggestion["kind"] = TYPE_KIND.get(t7[2][0], f"type_{t7[2][0]}")
            if suggestion["feature_id"]:
                try:
                    suggestions.append(Suggestion(**suggestion))
                except Exception:
                    pass
        return suggestions

    # ================================================================ fetch
    async def aget_suggestions(self, query: str, hl: Optional[str] = None,
                               gl: Optional[str] = None,
                               pb:Optional[str] = None,
                               session: Optional[str] = None,
                               http: Any = None) -> List[Suggestion]:
        """Async suggestions. Uses the shared curl_cffi session."""
        cfg = self.config
        params = (http.params if http is not None and http.params is not None
                  else self.build_suggestions_params(query, hl, gl, pb, session))
        url = (URL + http.path) if http is not None and http.path else (URL + "/s")
        timeout = (http.timeout if http is not None and http.timeout is not None
                   else cfg.timeout)
        headers = http.headers if http is not None else None
        try:
            http_session = await self.aget_session()
            resp = await http_session.get(url, params=params, timeout=timeout, headers=headers)
            resp.raise_for_status()
            text = resp.text if isinstance(resp.text, str) else resp.text()
            return self._parse_suggestions(text)
        except Exception as exc:
            self.logger.warning("suggestions failed for %r: %s", query, exc)
            return []

    def get_suggestions(self, query: str, hl: Optional[str] = None,
                        gl: Optional[str] = None,
                        pb:Optional[str] = None,
                        session: Optional[str] = None) -> List[Suggestion]:
        """Sync suggestions: returns a list of :class:`mapsfiacore.models.Suggestion`."""
        return run_sync(self.aget_suggestions(query, hl=hl, gl=gl, pb=pb, session=session))
