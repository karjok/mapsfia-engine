"""
Native-Python interface to the x-maps-bgkey generator.

Why a subprocess: the key is computed by Google's BotGuard VM (the obfuscated
interpreter at //www.google.com/js/bg/*.js). It is environment-sensitive and
only produces a correct key under Node's V8 with the exact call path. QuickJS
and py_mini_racer were both tested and return a degraded/blank payload.

This module boots `node bgkey.js --stdio` once and speaks a line-delimited
JSON protocol, so you call it like a normal Python function while the real
work runs in Node.

Usage:
    from bgkey_client import BgkeyClient
    with BgkeyClient() as c:
        key = c.bgkey("0x2e7a15ca78f42c63:0xdc8077d4d6be4249",
                      "It7CatX8G7qd4-EPj_fXyQE")
        # next page:
        key2 = c.bgkey(fid, place_id, pagination="CjEIARIp...:10")
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
from typing import Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_SCRIPT = os.path.join(_HERE, "bgkey.js")


class BgkeyError(RuntimeError):
    pass


class BgkeyClient:
    """Persistent client over `node bgkey.js --stdio`."""

    def __init__(
        self,
        script_path: str = _DEFAULT_SCRIPT,
        node: Optional[str] = None,
        timeout: float = 60.0,
        env: Optional[dict] = None,
        cwd: Optional[str] = None,
    ) -> None:
        self._node = node or shutil.which("node") or "node"
        self._script = script_path
        self._timeout = timeout
        self._lock = threading.Lock()
        run_env = os.environ.copy()
        if env:
            run_env.update(env)
        self._proc = subprocess.Popen(
            [self._node, self._script, "--stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=run_env,
            cwd=cwd or _HERE,
        )

    # -- lifecycle ---------------------------------------------------------

    def __enter__(self) -> "BgkeyClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        proc = getattr(self, "_proc", None)
        if proc and proc.poll() is None:
            try:
                proc.stdin.close()
            except Exception:
                pass
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()

    # -- internal RPC ------------------------------------------------------

    def _call(self, payload: dict) -> dict:
        if self._proc.poll() is not None:
            err = self._proc.stderr.read() if self._proc.stderr else ""
            raise BgkeyError(f"node subprocess exited: {err.strip()[:500]}")

        line = json.dumps(payload, ensure_ascii=False)
        with self._lock:
            try:
                self._proc.stdin.write(line + "\n")
                self._proc.stdin.flush()
            except BrokenPipeError as e:
                raise BgkeyError("node subprocess pipe closed") from e

            out = self._proc.stdout.readline()
        if not out:
            err = self._proc.stderr.read() if self._proc.stderr else ""
            raise BgkeyError(f"no response from node subprocess: {err.strip()[:500]}")

        try:
            resp = json.loads(out)
        except json.JSONDecodeError as e:
            raise BgkeyError(f"bad response: {out[:200]!r}") from e

        if "error" in resp:
            raise BgkeyError(resp["error"])
        return resp

    # -- public API --------------------------------------------------------

    def ping(self) -> bool:
        return bool(self._call({"cmd": "ping"}).get("ok"))

    def bgkey(
        self,
        fid: Optional[str] = None,
        place_id: Optional[str] = None,
        pagination: str = "",
        *,
        request_data: Optional[str] = None,
    ) -> str:
        """
        Generate x-maps-bgkey.

        Either:
          * pass fid + place_id (+ optional pagination token), or
          * pass request_data (the raw payload string Ggb extracts).
        """
        if request_data is not None:
            return self._call({"requestData": request_data})["key"]
        if not fid or not place_id:
            raise ValueError("provide either request_data, or both fid and place_id")
        return self._call(
            {"fid": fid, "placeId": place_id, "pagination": pagination}
        )["key"]


# -- module-level convenience (one-shot) -----------------------------------

def bgkey(fid: str, place_id: str, pagination: str = "", **kw) -> str:
    """One-shot helper: spawn, generate, close."""
    with BgkeyClient(**kw) as c:
        return c.bgkey(fid, place_id, pagination)


if __name__ == "__main__":
    import sys

    fid = "0x2e7a15ca78f42c63:0xdc8077d4d6be4249"
    place_id = "It7CatX8G7qd4-EPj_fXyQE"
    pagination = sys.argv[1] if len(sys.argv) > 1 else ""

    with BgkeyClient() as c:
        print("ping:", c.ping())
        k = c.bgkey(fid, place_id, pagination)
        print("x-maps-bgkey:", k[:70], "... (len", len(k), ")")
