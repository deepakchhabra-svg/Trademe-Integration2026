"""
Global outbound HTTP throttling.

Goal:
- Cap total concurrent outbound requests across the whole worker process
- Add simple per-host rate limiting so suppliers aren't overwhelmed

This is intentionally lightweight (threading-based) because the scraper/downloader
currently use synchronous requests + thread pools.
"""

from __future__ import annotations

import os
import threading
import time
from contextlib import contextmanager
from urllib.parse import urlparse


def _env_int(key: str, default: int) -> int:
    try:
        v = int((os.getenv(key) or "").strip() or default)
        return v
    except Exception:
        return default


def _env_float(key: str, default: float) -> float:
    try:
        v = float((os.getenv(key) or "").strip() or default)
        return v
    except Exception:
        return default


class GlobalHTTPThrottle:
    """
    Process-global throttle:
    - max in-flight requests across all threads
    - per-host minimum interval between request starts (simple RPS cap)
    """

    _max_inflight = max(1, min(128, _env_int("RETAILOS_HTTP_MAX_INFLIGHT", 16)))
    _default_rps = max(0.2, min(50.0, _env_float("RETAILOS_HTTP_RPS_DEFAULT", 6.0)))
    _sem = threading.BoundedSemaphore(_max_inflight)
    _lock = threading.Lock()
    _next_allowed_by_host: dict[str, float] = {}

    @classmethod
    def _host_key(cls, url: str) -> str:
        try:
            host = urlparse(url).netloc.lower().strip()
            return host or "unknown"
        except Exception:
            return "unknown"

    @classmethod
    def _rps_for_host(cls, host: str) -> float:
        # Allow per-host overrides, e.g. RETAILOS_HTTP_RPS_ONECHEQ_CO_NZ=3.5
        safe = host.upper().replace(".", "_").replace("-", "_")
        key = f"RETAILOS_HTTP_RPS_{safe}"
        return max(0.2, min(50.0, _env_float(key, cls._default_rps)))

    @classmethod
    @contextmanager
    def request(cls, url: str):
        """
        Context manager around a single outbound request.
        Applies:
        - global concurrency cap
        - per-host spacing (start-time based)
        """
        host = cls._host_key(url)
        rps = cls._rps_for_host(host)
        min_interval = 1.0 / max(rps, 0.2)

        cls._sem.acquire()
        try:
            # Rate limit per host (best-effort)
            with cls._lock:
                now = time.monotonic()
                next_allowed = cls._next_allowed_by_host.get(host, 0.0)
                sleep_for = max(0.0, next_allowed - now)
                cls._next_allowed_by_host[host] = max(next_allowed, now) + min_interval
            if sleep_for > 0:
                time.sleep(min(5.0, sleep_for))
            yield
        finally:
            cls._sem.release()

