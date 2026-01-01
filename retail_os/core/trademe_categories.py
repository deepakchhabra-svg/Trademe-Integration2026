"""
Trade Me categories (official taxonomy).

Source: Trade Me Categories.xlsx (exported to JSON at build-time).
Used for:
- ID -> human path lookup (no more "Unknown Category" for valid IDs)
- deterministic best-effort mapping from product text -> category ID

Operator-grade rule: no hardcoded account-specific values, and no fake defaults.
If we can't map with enough confidence, callers should treat the result as blocked.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable, Optional


_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(s: str) -> list[str]:
    raw = " ".join((s or "").lower().split())
    toks = _TOKEN_RE.findall(raw)
    stop = {
        "and",
        "or",
        "the",
        "a",
        "an",
        "with",
        "for",
        "to",
        "of",
        "in",
        "on",
        "by",
        "from",
        "new",
        "used",
        "refurbished",
        "bundle",
        "pack",
    }
    out: list[str] = []
    for t in toks:
        if len(t) < 3 or t in stop:
            continue
        out.append(t)
        # tiny stemming for pluralization (laptop vs laptops, etc.)
        if len(t) >= 4 and t.endswith("s") and not t.endswith("ss"):
            out.append(t[:-1])
    return out


@dataclass(frozen=True)
class Category:
    api_id: str
    full_code: str
    path: str
    name: str


@lru_cache(maxsize=1)
def _load() -> dict[str, Category]:
    here = os.path.dirname(__file__)
    path = os.path.join(here, "trademe_categories.json")
    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    out: dict[str, Category] = {}
    for r in doc.get("categories", []) or []:
        api_id = str(r.get("api_id") or "").strip()
        if not api_id:
            continue
        out[api_id] = Category(
            api_id=api_id,
            full_code=str(r.get("full_code") or "").strip(),
            path=str(r.get("path") or "").strip(),
            name=str(r.get("name") or "").strip(),
        )
    return out


@lru_cache(maxsize=1)
def _token_index() -> dict[str, list[str]]:
    """
    Inverted index: token -> [api_id...]
    """
    idx: dict[str, list[str]] = {}
    cats = _load()
    for api_id, c in cats.items():
        # index both path and leaf name (keeps mapping stable)
        for t in set(_tokens(f"{c.path} {c.name}")):
            idx.setdefault(t, []).append(api_id)
    return idx


class TradeMeCategories:
    @staticmethod
    def get(api_id: str) -> Optional[Category]:
        return _load().get((api_id or "").strip())

    @staticmethod
    def name(api_id: str) -> Optional[str]:
        c = TradeMeCategories.get(api_id)
        if not c:
            return None
        # Prefer full path for operator clarity.
        return c.path

    @staticmethod
    def best_effort_map(text: str, *, min_score: float = 1.6) -> Optional[str]:
        """
        Deterministic best-effort mapping from free-text to a Trade Me leaf category id.

        This is intentionally conservative:
        - Returns None if not enough signal (so callers can block rather than mislist)
        """
        # NOTE:
        # This helper exists for future "suggested category" UX, but is intentionally
        # not used by the publish gate/mapping flow (CategoryMapper.map_category),
        # because fuzzy mapping can mislist items.
        toks = _tokens(text)
        if not toks:
            return None

        idx = _token_index()
        cats = _load()
        text_tokens = set(toks)

        # Token weights: downweight very common tokens (e.g. "cordless").
        def weight(token: str) -> float:
            n = len(idx.get(token, []))
            if n >= 500:
                return 0.10
            if n >= 200:
                return 0.20
            if n >= 80:
                return 0.35
            if n >= 30:
                return 0.55
            return 1.0

        accessory_tokens = {
            "accessor",
            "accessories",
            "accessorie",
            "battery",
            "batteries",
            "batteri",
            "adaptor",
            "adaptors",
            "adapter",
            "adapters",
            "charger",
            "chargers",
            "cable",
            "cables",
            "case",
            "cases",
            "cover",
            "covers",
            "screen",
            "screens",
            "protector",
            "protectors",
            "dock",
            "docks",
            "bag",
            "bags",
            "pouch",
            "pouches",
            "sleeve",
            "sleeves",
        }

        scores: dict[str, float] = {}
        for t in toks:
            w = weight(t)
            for api_id in idx.get(t, []):
                c = cats.get(api_id)
                if not c:
                    continue
                # Exclude non-product verticals (jobs) from listing mapping.
                if c.path.startswith("Trade-Me-Jobs"):
                    continue
                scores[api_id] = scores.get(api_id, 0.0) + w

        if not scores:
            return None

        # Apply accessory penalties unless the title explicitly contains those tokens.
        for api_id, sc in list(scores.items()):
            c = cats.get(api_id)
            if not c:
                continue
            c_toks = set(_tokens(c.path))
            penalty = 0.0
            for at in accessory_tokens:
                if at in c_toks and at not in text_tokens:
                    penalty += 1.0
            scores[api_id] = sc - penalty

        # Pick highest score; tie-break by longer path (usually more specific).
        best_id, best_score = None, -1.0
        best_path_len = -1
        for api_id, sc in scores.items():
            if sc < min_score:
                continue
            plen = len((cats.get(api_id).path if cats.get(api_id) else "") or "")
            if sc > best_score or (sc == best_score and plen > best_path_len):
                best_id, best_score, best_path_len = api_id, sc, plen

        return best_id

