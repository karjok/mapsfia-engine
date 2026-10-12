"""Shared configuration, logging, HTTP sessions and async helpers.

Every capability class (Search, Suggestions, Geojson, MapsFia) builds on
``MapsFiaBase``:

* **config** - each class owns a :class:`MapsFiaConfig`. When the class is
  created by :class:`~mapsfiacore.mapsfia.MapsFia` (or any class with children)
  the parent's config is passed down as ``config=``, otherwise the class falls
  back to its own defaults.
* **logging** - each class owns a logger named ``MapsFia.<ClassName>``. When a
  parent is given, the child logger is nested under the parent logger
  (``MapsFia.Geojson`` or ``MapsFia.Search.Geojson``) and inherits its level
  and handlers, so a single ``logging.getLogger("MapsFia")`` setup controls the
  whole tree.
* **async** - ``Search``/``Suggestions`` are natively async (``asearch`` /
  ``aget_suggestions``) with sync wrappers, ``Geojson`` runs its aiohttp tile
  pool internally and exposes both ``extract``/``extract_async``. All classes
  share one curl_cffi session: a process-wide ``Session`` for sync calls and
  one ``AsyncSession`` per running event loop (curl_cffi binds async sessions
  to the loop that created them). Pass an explicit session through the config
  to override.
"""
from __future__ import annotations

import asyncio
import logging
import random
import string
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, suppress
from dataclasses import dataclass, replace
from typing import Any, Optional

try:
    from curl_cffi.requests import AsyncSession, Session
except ImportError:  # pragma: no cover - import error surfaces on first use
    AsyncSession = Session = None

DEFAULT_HL = "en"
DEFAULT_GL = "us"
DEFAULT_MAX_CONCURRENCY = 10
DEFAULT_TIMEOUT = 30.0
DEFAULT_IMPERSONATE = "chrome131"

_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

LOG_FORMAT = "%(asctime)s %(name)s.%(levelname)s %(message)s"
LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"
ROOT_LOGGER_NAME = "MapsFia"

# curl_cffi's AsyncSession is bound to the event loop that first used it, so a
# single async singleton breaks on a second ``asyncio.run``. We keep one
# private session per running loop instead.
_loop_sessions: dict[int, Any] = {}
_shared_sync_session: Any = None


async def _run_and_cleanup(coro: Any) -> Any:
    """Await ``coro`` then close the session bound to this event loop."""
    try:
        return await coro
    finally:
        await _close_current_loop_session()


def run_sync(coro: Any) -> Any:
    """Run a coroutine from sync code, even inside a running event loop."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        try:
            import uvloop
            return uvloop.run(_run_and_cleanup(coro))
        except ImportError:
            return asyncio.run(_run_and_cleanup(coro))
    with ThreadPoolExecutor(max_workers=1) as ex:
        return ex.submit(asyncio.run, _run_and_cleanup(coro)).result()


def _prune_dead_loop_sessions() -> None:
    """Drop sessions whose event loop is already closed (cannot be closed now)."""
    for key, sess in list(_loop_sessions.items()):
        loop = getattr(sess, "_loop", None)
        if loop is not None and loop.is_closed():
            _loop_sessions.pop(key, None)


def _current_loop_session() -> Any:
    """Return the AsyncSession bound to the running loop (created on demand)."""
    if AsyncSession is None:
        return None
    _prune_dead_loop_sessions()
    loop = asyncio.get_running_loop()
    sess = _loop_sessions.get(id(loop))
    if (sess is None or getattr(sess, "_closed", False)
            or getattr(sess, "_loop", None) is not loop):
        sess = AsyncSession(impersonate=DEFAULT_IMPERSONATE)
        _loop_sessions[id(loop)] = sess
    return sess


def _shared_session() -> Any:
    """Return the process-wide sync Session (created on demand)."""
    global _shared_sync_session
    if Session is None:
        return None
    if _shared_sync_session is None or getattr(_shared_sync_session, "_closed", False):
        _shared_sync_session = Session(impersonate=DEFAULT_IMPERSONATE)
    return _shared_sync_session


async def _close_current_loop_session() -> None:
    """Close the session bound to the running loop, if any."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    sess = _loop_sessions.pop(id(loop), None)
    if sess is not None:
        with suppress(Exception):
            await sess.close()


async def close_loop_sessions() -> None:
    """Close the current loop's session and the shared sync session (best effort).

    Sessions bound to other, already-closed loops are dropped without touching
    them (closing them would wake curl_cffi on a dead loop).
    """
    global _shared_sync_session
    _prune_dead_loop_sessions()
    await _close_current_loop_session()
    if _shared_sync_session is not None:
        with suppress(Exception):
            _shared_sync_session.close()
        _shared_sync_session = None


@dataclass
class MapsFiaConfig:
    """Runtime knobs shared by every MapsFia class.

    ``session``/``async_session`` default to the process-wide curl_cffi
    sessions; pass an explicit session object to use your own, or ``False`` to
    create a private one per call.
    """

    max_concurrency: int = DEFAULT_MAX_CONCURRENCY
    timeout: float = DEFAULT_TIMEOUT
    hl: str = DEFAULT_HL
    gl: str = DEFAULT_GL
    debug: bool = False
    pb:Optional[str] = None
    log_level: Optional[int] = None
    session: Any = None
    async_session: Any = None

    def merged(self, **overrides: Any) -> "MapsFiaConfig":
        """Return a copy with ``overrides`` applied (``None`` values ignored)."""
        clean = {k: v for k, v in overrides.items() if v is not None}
        return replace(self, **clean) if clean else self


@dataclass
class HttpSpec:
    """A method/path/params triple ready to be sent through a session."""

    method: str = "GET"
    path: str = ""
    params: Optional[dict] = None
    headers: Optional[dict] = None
    timeout: Optional[float] = None
    kind: str = "html"


class MapsFiaBase:
    """Base for every MapsFia capability class.

    Args:
        config:  explicit config; takes priority over ``parent``.
        parent:  another :class:`MapsFiaBase` (e.g. ``MapsFia``). Its config is
                 inherited and this logger is nested under the parent's.
        logger:  explicit logger override.
        config_overrides: per-instance tweaks merged over the inherited config
                 (useful when a parent config is shared).
    """

    name = "Base"

    def __init__(self, config: Optional[MapsFiaConfig] = None,
                 parent: Optional["MapsFiaBase"] = None,
                 logger: Optional[logging.Logger] = None,
                 **config_overrides: Any):
        if config is not None:
            self.config = config
        elif parent is not None:
            self.config = parent.config.merged(**config_overrides)
        else:
            self.config = MapsFiaConfig().merged(**config_overrides)
        self.parent = parent
        self.children: list[MapsFiaBase] = []
        if logger is not None:
            self.logger = logger
        else:
            root = getattr(parent, "logger", None)
            if root is not None:
                self.logger = logging.getLogger(f"{root.name}.{self.name}")
            elif self.name == ROOT_LOGGER_NAME:
                self.logger = logging.getLogger(ROOT_LOGGER_NAME)
            else:
                self.logger = logging.getLogger(f"{ROOT_LOGGER_NAME}.{self.name}")
        if parent is not None:
            parent.children.append(self)
        if self.config.log_level is not None:
            self.logger.setLevel(self.config.log_level)

    # ------------------------------------------------------------ logging
    def configure_logging(self, level: int = logging.INFO,
                          handler: Optional[logging.Handler] = None,
                          fmt: str = LOG_FORMAT,
                          datefmt: str = LOG_DATEFMT,
                          propagate: Optional[bool] = None) -> logging.Logger:
        """Configure this class' logger and cascade the level to descendants.

        When ``self`` is the ``MapsFia`` root the logger tree looks like
        ``MapsFia.Search`` / ``MapsFia.Suggestions`` / ``MapsFia.Geojson``.
        """
        self.logger.setLevel(level)
        if handler is None:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
        if not any(getattr(h, "_mapsfia", False) for h in self.logger.handlers):
            handler._mapsfia = True
            self.logger.addHandler(handler)
        if propagate is None:
            # A nested class configured on its own must not also write through
            # an ancestor's handler (that would duplicate every line).
            propagate = not self.logger.name.startswith(ROOT_LOGGER_NAME + ".")
        self.logger.propagate = propagate
        for child in self.children:
            # The child only needs its level; it writes through this logger's
            # handler (or propagates to the "MapsFia" root).
            child.set_log_level(level)
        return self.logger

    def set_log_level(self, level: int) -> None:
        """Set the level on this class and every child class."""
        self.logger.setLevel(level)
        for child in self.children:
            child.set_log_level(level)

    @property
    def log(self) -> logging.Logger:
        return self.logger

    # ------------------------------------------------------------ sessions
    def _shared_async_session(self) -> Any:
        return _current_loop_session()

    def _own_session(self) -> Any:
        if Session is None:
            raise RuntimeError("curl_cffi is required for HTTP requests")
        return Session(impersonate=DEFAULT_IMPERSONATE)

    def _own_async_session(self) -> Any:
        if AsyncSession is None:
            raise RuntimeError("curl_cffi is required for async HTTP requests")
        return AsyncSession(impersonate=DEFAULT_IMPERSONATE)

    def get_session(self, config: Optional[MapsFiaConfig] = None) -> Any:
        """Sync curl_cffi session honoring the config's ``session`` setting."""
        cfg = config or self.config
        if cfg.session is not None and cfg.session is not False:
            return cfg.session
        if cfg.session is False:
            return self._own_session()
        sess = _shared_session()
        return sess if sess is not None else self._own_session()

    async def aget_session(self, config: Optional[MapsFiaConfig] = None) -> Any:
        """Async curl_cffi session honoring the config's ``async_session`` setting."""
        cfg = config or self.config
        if cfg.async_session is not None and cfg.async_session is not False:
            return cfg.async_session
        if cfg.async_session is False:
            return self._own_async_session()
        sess = self._shared_async_session()
        if sess is not None:
            return sess
        # No shared session available (curl_cffi missing): let the caller
        # fall back to its own transport (e.g. the aiohttp tile pool).
        return self._own_async_session() if AsyncSession is not None else None

    @contextmanager
    def session(self, **overrides: Any):
        """Context manager yielding a session (private sessions are closed).

        Does not mutate the instance config, so it is safe to use concurrently.
        """
        cfg = self.config.merged(**overrides)
        private = None
        if cfg.session is False:
            private = self._own_session()
            sess = private
        else:
            sess = self.get_session(cfg)
        try:
            yield sess
        finally:
            if private is not None:
                with suppress(Exception):
                    private.close()

    class _AsyncSessionScope:
        def __init__(self, owner: "MapsFiaBase", overrides: dict):
            self.owner = owner
            self.overrides = overrides
            self.private = None
            self.sess = None

        async def __aenter__(self):
            cfg = self.owner.config.merged(**self.overrides)
            if cfg.async_session is False:
                self.private = self.owner._own_async_session()
                self.sess = self.private
            elif cfg.async_session is not None:
                self.sess = cfg.async_session
            else:
                self.sess = self.owner._shared_async_session()
                if self.sess is None:
                    self.private = self.owner._own_async_session()
                    self.sess = self.private
            return self.sess

        async def __aexit__(self, *exc):
            if self.private is not None:
                with suppress(Exception):
                    await self.private.close()
            return False

    def async_session(self, **overrides: Any):
        """``async with client.async_session() as session: ...``."""
        return self._AsyncSessionScope(self, overrides)

    # ------------------------------------------------------------ helpers
    def _diag(self, msg: str, *args: Any) -> None:
        """Per-tile style diagnostics: DEBUG when enabled, else INFO if debug."""
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(msg, *args)
        elif self.config.debug:
            self.logger.info(msg, *args)

    def _session_id(self) -> str:
        sid = getattr(self, "maps_session", None)
        if not sid:
            sid = "".join(random.choices(string.ascii_letters + string.digits, k=26))
            self.maps_session = sid
        return sid

    @staticmethod
    def _default_user_agent() -> str:
        return _UA

    def __repr__(self) -> str:
        return (f"<{type(self).__name__} concurrency={self.config.max_concurrency} "
                f"hl={self.config.hl!r} gl={self.config.gl!r}>")
