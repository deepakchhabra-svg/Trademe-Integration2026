"""
SEO Formatter Utility.
Generates SEO-friendly listing descriptions for Trade Me uploads.
Cleaned and adapted for Retail OS.
"""

import re
from typing import Any, Dict, List


WHITESPACE_RE = re.compile(r"\s+")
SKIP_PATTERNS = [
    re.compile(r"warranty\s+90\s+days?.*consumer\s+guarantees?\s+act", re.I),
    re.compile(r"consumer\s+guarantees?\s+act", re.I),
    re.compile(r"available\s+from[:\s].*", re.I),
    re.compile(r"source\s+listing\s+id[:\s].*", re.I),
    re.compile(r"source\s+reference[:\s].*", re.I),
    re.compile(r"cash\s+converters?", re.I),
    re.compile(r"noel\s+leeming", re.I),
    # Aggressive Marketing Removal
    re.compile(r"\*\*\*Stock Wanted\*\*\*.*", re.I | re.DOTALL),
    re.compile(r"We are looking for more stock.*", re.I | re.DOTALL),
    re.compile(r"Bring your good quality second hand goods.*", re.I | re.DOTALL),
    re.compile(r"All you need is your item and a valid ID.*", re.I | re.DOTALL),
    re.compile(r"Warranty only valid when.*", re.I | re.DOTALL),
    re.compile(r"Products must be paid within.*", re.I | re.DOTALL),
    re.compile(r"After payment Items must be held.*", re.I | re.DOTALL),
    re.compile(r"ID is required upon collecting.*", re.I | re.DOTALL),
    re.compile(r"If you have any issues please give us.*", re.I | re.DOTALL),
    re.compile(r"If you like our service.*", re.I | re.DOTALL),
    re.compile(r"Pickup is available.*", re.I | re.DOTALL),
    re.compile(r"Items are available for collection.*", re.I | re.DOTALL),
    re.compile(r"WE PAWN CARS.*", re.I | re.DOTALL),
    re.compile(r"We now loan on Vehicles.*", re.I | re.DOTALL),
    re.compile(r"Come instore and speak to our friendly staff.*", re.I | re.DOTALL),
    re.compile(r"Stock Needed!.*", re.I | re.DOTALL),
    re.compile(r"Valid ID is required.*", re.I | re.DOTALL),
    re.compile(r"WE ALSO PAWN ON.*", re.I | re.DOTALL),
    re.compile(r"For more information contact our stores.*", re.I | re.DOTALL),
    re.compile(r"Store Contact.*", re.I | re.DOTALL),
    re.compile(r"Address :.*", re.I | re.DOTALL),
    re.compile(r"If you need any help, please chat.*", re.I | re.DOTALL),
    re.compile(r"Goods are offered for sale.*", re.I | re.DOTALL),
    re.compile(r"Goods must be paid.*", re.I | re.DOTALL),
    re.compile(r"Goods have a 90-days.*", re.I | re.DOTALL),
    re.compile(r"ID Required upon pick up.*", re.I | re.DOTALL),
    re.compile(r"Online payments only.*", re.I | re.DOTALL),
    re.compile(r"No instore payments accepted.*", re.I | re.DOTALL),
    # Identifier & Tracking Garbage
    re.compile(r"Web\s*ID[:\s]*\d+.*", re.I),
    re.compile(r"SKU[:\s]*[A-Z0-9-]{3,}.*", re.I),
    re.compile(r"Product\s+ID[:\s]*\d+.*", re.I),
    re.compile(r"Ref[:\s]*[A-Z0-9-]{3,}.*", re.I),
    # Social/In-store garbage
    re.compile(r"Interested\s+in\s+this\s+item.*", re.I | re.DOTALL),
    re.compile(r"Come\s+and\s+check\s+it\s+out.*", re.I | re.DOTALL),
    re.compile(r"Ask\s+for\s+.*\s+at\s+the\s+counter.*", re.I | re.DOTALL),
]


def _clean_text(text: str) -> str:
    return WHITESPACE_RE.sub(" ", (text or "").strip())


def _sanitize_fragment(text: str) -> str:
    cleaned = text
    for pattern in SKIP_PATTERNS:
        cleaned = pattern.sub("", cleaned)
    cleaned = WHITESPACE_RE.sub(" ", cleaned).strip(" -*•")
    return cleaned.strip()


def _split_points(description: str) -> List[str]:
    if not description:
        return []
    tokens: List[str] = []
    
    # Simple split by newline first
    chunks = re.split(r"[\n\r]+", description)
    
    for chunk in chunks:
        chunk = _sanitize_fragment(chunk)
        if not chunk:
            continue
            
        # If the chunk is very long, try splitting by period
        if len(chunk) > 180 and "." in chunk:
            sentences = re.split(r"(?<=\.)\s+", chunk)
            for sentence in sentences:
                sentence = _sanitize_fragment(sentence)
                if 20 <= len(sentence) <= 180:
                    tokens.append(sentence)
        else:
            tokens.append(chunk)

    # Deduplicate while preserving order
    seen = set()
    ordered: List[str] = []
    for token in tokens:
        key = token.lower()
        if key in seen or not token:
            continue
        seen.add(key)
        ordered.append(token)
    return ordered[:8] # bumped to 8 points


def build_seo_description(row: Dict[str, str]) -> str:
    """
    Construct a consistent, reader-friendly description.

    Rules:
    - Deterministic (no LLM).
    - Prefer structured specs over marketing fluff.
    - Never end mid-sentence with a dangling marketing fragment.
    """
    title = _clean_text(row.get("title") or "")
    description = _clean_text(row.get("description") or "")

    # Optional structured context (Unified schema provides these as dict/str)
    specs: dict[str, Any] = {}
    raw_specs = row.get("specs")  # type: ignore[assignment]
    if isinstance(raw_specs, dict):
        specs = raw_specs

    condition = _clean_text(str(row.get("condition") or specs.get("Condition") or specs.get("condition") or "See details"))
    brand = _clean_text(str(row.get("brand") or specs.get("Brand") or specs.get("brand") or ""))

    # Remove the common truncated Shopify marketing fragment if present
    for frag in ("Discover unbeatable deals on", "Discover the", "Discover unbeatable"):
        if description.endswith(frag) or description.endswith(frag + "."):
            description = description[: -len(frag)].strip(" -•")

    bullet_points = _split_points(description)

    lines: List[str] = []
    if title:
        lines.append(f"**{title}**")
        lines.append("")

    # Summary block (short + factual)
    if brand:
        lines.append(f"Brand: {brand}")
    if condition:
        lines.append(f"Condition: {condition}")
    lines.append("")

    # Specs (top 10 only, stable order by key name)
    if specs:
        lines.append("**Specifications**")
        for k in sorted(list(specs.keys()))[:10]:
            v = specs.get(k)
            if v is None:
                continue
            vv = _clean_text(str(v))
            kk = _clean_text(str(k)).replace("_", " ").strip(":")
            if kk and vv:
                lines.append(f"- {kk}: {vv}")
        lines.append("")

    # Detail bullets (only if they’re meaningful)
    if bullet_points:
        lines.append("**Details**")
        for point in bullet_points:
            lines.append(f"- {point}")
        lines.append("")

    lines.append("---")
    lines.append("Shipping: Standard courier nationwide (rural available). Pickup may be available.")
    lines.append("Payment: Bank deposit or cash on pickup (per Trade Me options).")
    lines.append("Please review photos and specifications carefully before purchase.")

    final = "\n".join(line.rstrip() for line in lines).strip()
    return final or description

def clean_description(text: str) -> str:
    """
    Applies all SKIP_PATTERNS to the text.
    Used for pre-cleaning before AI formatting.
    """
    if not text: return ""
    cleaned = text
    for pattern in SKIP_PATTERNS:
        cleaned = pattern.sub("", cleaned)
    return WHITESPACE_RE.sub(" ", cleaned).strip()
