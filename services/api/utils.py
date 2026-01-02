from datetime import datetime
from pathlib import Path
from typing import Any
from retail_os.core.category_mapper import CategoryMapper
from retail_os.core.database import SupplierProduct, InternalProduct, TradeMeListing

# Repo-root anchored media dir (ImageDownloader writes to data/media).
_REPO_ROOT = Path(__file__).resolve().parents[2]
_MEDIA_ROOT = (_REPO_ROOT / "data" / "media").resolve()

def _public_image_urls(images: Any) -> list[str]:
    """
    Normalize DB-stored image paths into URLs a browser can fetch.
    - Remote URLs: returned as-is.
    - Local paths under data/media: returned as /media/<relpath>.
    """
    if not images:
        return []
    if not isinstance(images, list):
        return []

    out: list[str] = []
    for raw in images:
        if not raw or not isinstance(raw, str):
            continue
        if raw.startswith("http://") or raw.startswith("https://"):
            out.append(raw)
            continue

        norm = raw.replace("\\", "/")
        lower = norm.lower()

        # Common cases: "data/media/x.jpg" (relative) or "C:/.../data/media/x.jpg" (absolute)
        if lower.startswith("data/media/"):
            rel = norm[len("data/media/") :]
            out.append(f"/media/{rel}")
            continue
        idx = lower.rfind("/data/media/")
        if idx != -1:
            rel = norm[idx + len("/data/media/") :]
            out.append(f"/media/{rel}")
            continue

        # As a last resort: if it is an absolute file inside media root, serve it.
        try:
            p = Path(raw).expanduser().resolve()
            if _MEDIA_ROOT in p.parents:
                rel = p.relative_to(_MEDIA_ROOT).as_posix()
                out.append(f"/media/{rel}")
                continue
        except Exception:
            pass

    return out

def _dt(v: Any) -> Any:
    if isinstance(v, datetime):
        return v.isoformat()
    return v

def _serialize_supplier_product(sp: SupplierProduct) -> dict[str, Any]:
    return {
        "id": sp.id,
        "supplier_id": sp.supplier_id,
        "supplier_name": sp.supplier.name if getattr(sp, "supplier", None) else None,
        "external_sku": sp.external_sku,
        "title": sp.title,
        "description": sp.description,
        "brand": sp.brand,
        "condition": sp.condition,
        "cost_price": float(sp.cost_price) if sp.cost_price is not None else None,
        "stock_level": sp.stock_level,
        "product_url": sp.product_url,
        "images": _public_image_urls(sp.images or []),
        "specs": sp.specs or {},
        "enrichment_status": sp.enrichment_status,
        "enrichment_error": sp.enrichment_error,
        "enriched_title": sp.enriched_title,
        "enriched_description": sp.enriched_description,
        "last_scraped_at": _dt(sp.last_scraped_at),
        "snapshot_hash": sp.snapshot_hash,
        "sync_status": sp.sync_status,
        "source_category": getattr(sp, "source_category", None),
        "source_categories": getattr(sp, "source_categories", None),
        "collection_rank": sp.collection_rank,
        "collection_page": sp.collection_page,
        "internal_product_id": sp.internal_product.id if getattr(sp, "internal_product", None) else None,
    }

def _serialize_internal_product(ip: InternalProduct) -> dict[str, Any]:
    sp = ip.supplier_product
    final_category_id = None
    final_category_name = None
    final_category_is_default = None
    if sp:
        try:
            final_category_id = CategoryMapper.map_category(
                getattr(sp, "source_category", "") or "",
                sp.title or "",
                (getattr(sp, "enriched_description", None) or getattr(sp, "description", None) or ""),
            )
            final_category_name = CategoryMapper.get_category_name(final_category_id) if final_category_id else None
            final_category_is_default = bool(final_category_id == getattr(CategoryMapper, "DEFAULT_CATEGORY", None))
        except Exception:
            final_category_id = None
            final_category_name = None
            final_category_is_default = None
    return {
        "id": ip.id,
        "sku": ip.sku,
        "title": ip.title,
        "primary_supplier_product_id": ip.primary_supplier_product_id,
        "supplier_product": _serialize_supplier_product(sp) if sp else None,
        "final_category_id": final_category_id,
        "final_category_name": final_category_name,
        "final_category_is_default": final_category_is_default,
    }

def _serialize_listing(l: TradeMeListing) -> dict[str, Any]:
    ip = l.product
    sp = ip.supplier_product if ip else None
    return {
        "id": l.id,
        "tm_listing_id": l.tm_listing_id,
        "internal_product_id": l.internal_product_id,
        "actual_state": l.actual_state,
        "desired_state": l.desired_state,
        "lifecycle_state": str(l.lifecycle_state) if l.lifecycle_state is not None else None,
        "is_locked": l.is_locked,
        "desired_price": float(l.desired_price) if l.desired_price is not None else None,
        "actual_price": float(l.actual_price) if l.actual_price is not None else None,
        "view_count": l.view_count,
        "watch_count": l.watch_count,
        "category_id": l.category_id,
        "payload_snapshot": l.payload_snapshot,
        "payload_hash": l.payload_hash,
        "last_synced_at": _dt(l.last_synced_at),
        "internal_product": _serialize_internal_product(ip) if ip else None,
        "supplier_product": _serialize_supplier_product(sp) if sp else None,
    }
