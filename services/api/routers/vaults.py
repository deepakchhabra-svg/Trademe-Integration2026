from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import func, or_

from retail_os.core.database import (
    SupplierProduct,
    InternalProduct,
    TradeMeListing,
    get_db_session,
)
from retail_os.core.category_mapper import CategoryMapper
from retail_os.strategy.pricing import PricingStrategy

from ..schemas import PageResponse
from ..utils import (
    _dt,
    _public_image_urls,
    _serialize_supplier_product,
)

router = APIRouter(prefix="/vaults", tags=["vaults"])

@router.get("/raw", response_model=PageResponse)
def vault_raw(
    q: Optional[str] = None,
    supplier_id: Optional[int] = None,
    sync_status: Optional[str] = None,
    source_category: Optional[str] = None,
    page: int = 1,
    per_page: int = 50,
) -> PageResponse:
    if page < 1 or per_page < 1 or per_page > 1000:
        raise HTTPException(status_code=400, detail="Invalid pagination")

    with get_db_session() as session:
        query = session.query(SupplierProduct)

        if q:
            term = f"%{q}%"
            query = query.filter((SupplierProduct.title.ilike(term)) | (SupplierProduct.external_sku.ilike(term)))

        if supplier_id:
            query = query.filter(SupplierProduct.supplier_id == supplier_id)

        if sync_status and sync_status != "All":
            query = query.filter(SupplierProduct.sync_status == sync_status)

        if source_category:
            query = query.filter(SupplierProduct.source_category == source_category)

        total = query.count()
        rows = (
            query.order_by(SupplierProduct.last_scraped_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        items = []
        for sp in rows:
            final_category_id = CategoryMapper.map_category(
                getattr(sp, "source_category", "") or "",
                sp.title or "",
                (getattr(sp, "enriched_description", None) or getattr(sp, "description", None) or ""),
            )
            final_category_name = CategoryMapper.get_category_name(final_category_id) if final_category_id else None
            final_category_is_default = bool(final_category_id == getattr(CategoryMapper, "DEFAULT_CATEGORY", None))
            items.append(
                {
                    "id": sp.id,
                    "supplier_id": sp.supplier_id,
                    "external_sku": sp.external_sku,
                    "title": sp.title,
                    "cost_price": float(sp.cost_price) if sp.cost_price is not None else None,
                    "stock_level": sp.stock_level,
                    "sync_status": sp.sync_status,
                    "source_category": getattr(sp, "source_category", None),
                    "final_category_id": final_category_id,
                    "final_category_name": final_category_name,
                    "final_category_is_default": final_category_is_default,
                    "product_url": sp.product_url,
                    "images": _public_image_urls(sp.images or []),
                    "specs": sp.specs or {},
                    "last_scraped_at": _dt(sp.last_scraped_at),
                    "enrichment_status": sp.enrichment_status,
                    "enriched_title": sp.enriched_title,
                }
            )

        return PageResponse(items=items, total=total)

@router.get("/enriched", response_model=PageResponse)
def vault_enriched(
    q: Optional[str] = None,
    supplier_id: Optional[int] = None,
    source_category: Optional[str] = None,
    enrichment: str = "All",
    page: int = 1,
    per_page: int = 50,
) -> PageResponse:
    if page < 1 or per_page < 1 or per_page > 1000:
        raise HTTPException(status_code=400, detail="Invalid pagination")

    with get_db_session() as session:
        query = session.query(InternalProduct).join(SupplierProduct, InternalProduct.primary_supplier_product_id == SupplierProduct.id)

        if q:
            term = f"%{q}%"
            query = query.filter((InternalProduct.title.ilike(term)) | (SupplierProduct.enriched_description.ilike(term)))

        if supplier_id:
            query = query.filter(SupplierProduct.supplier_id == supplier_id)

        if source_category:
            query = query.filter(SupplierProduct.source_category == source_category)

        if enrichment == "Enriched":
            query = query.filter(SupplierProduct.enriched_description.isnot(None))
        elif enrichment == "Not Enriched":
            query = query.filter(SupplierProduct.enriched_description.is_(None))

        total = query.count()
        rows = query.offset((page - 1) * per_page).limit(per_page).all()

        items = []
        for ip in rows:
            sp = ip.supplier_product
            final_category_id = (
                CategoryMapper.map_category(
                    getattr(sp, "source_category", "") or "",
                    sp.title or "",
                    (getattr(sp, "enriched_description", None) or getattr(sp, "description", None) or ""),
                )
                if sp
                else None
            )
            final_category_name = CategoryMapper.get_category_name(final_category_id) if final_category_id else None
            final_category_is_default = bool(final_category_id and final_category_id == getattr(CategoryMapper, "DEFAULT_CATEGORY", None))
            source_price = float(sp.cost_price) if sp and sp.cost_price is not None else None
            cost_price = source_price
            sell_price = None
            margin_amount = None
            margin_percent = None
            if cost_price is not None:
                try:
                    supplier_name = sp.supplier.name if sp and getattr(sp, "supplier", None) else None
                    sell_price = float(PricingStrategy.calculate_price(cost_price, supplier_name=supplier_name))
                except Exception:
                    sell_price = None
            if sell_price is not None and cost_price is not None and cost_price:
                margin_amount = float(sell_price - cost_price)
                margin_percent = float(margin_amount / cost_price) if cost_price else None
            items.append(
                {
                    "id": ip.id,
                    "sku": ip.sku,
                    "title": ip.title,
                    "supplier_product_id": ip.primary_supplier_product_id,
                    "supplier_id": sp.supplier_id if sp else None,
                    "source_price": source_price,
                    "cost_price": cost_price,
                    "sell_price": sell_price,
                    "margin_amount": margin_amount,
                    "margin_percent": margin_percent,
                    "raw_title": sp.title if sp else None,
                    "enriched_title": sp.enriched_title if sp else None,
                    "enriched_description": sp.enriched_description if sp else None,
                    "has_raw_description": bool((sp.description or "").strip()) if sp else False,
                    "has_enriched_description": bool((sp.enriched_description or "").strip()) if sp else False,
                    "images": _public_image_urls((sp.images if sp else None) or []),
                    "source_category": getattr(sp, "source_category", None) if sp else None,
                    "final_category_id": final_category_id,
                    "final_category_name": final_category_name,
                    "final_category_is_default": final_category_is_default,
                    "product_url": sp.product_url if sp else None,
                    "sync_status": sp.sync_status if sp else None,
                    "enrichment_status": sp.enrichment_status if sp else None,
                }
            )

        return PageResponse(items=items, total=total)

@router.get("/live", response_model=PageResponse)
def vault_live(
    q: Optional[str] = None,
    status: str = "All",
    supplier_id: Optional[int] = None,
    source_category: Optional[str] = None,
    page: int = 1,
    per_page: int = 50,
) -> PageResponse:
    if page < 1 or per_page < 1 or per_page > 1000:
        raise HTTPException(status_code=400, detail="Invalid pagination")

    with get_db_session() as session:
        query = (
            session.query(TradeMeListing)
            .outerjoin(InternalProduct, TradeMeListing.internal_product_id == InternalProduct.id)
            .outerjoin(SupplierProduct, InternalProduct.primary_supplier_product_id == SupplierProduct.id)
        )

        if status != "All":
            query = query.filter(TradeMeListing.actual_state == status)

        if supplier_id is not None:
            query = query.filter(SupplierProduct.supplier_id == int(supplier_id))
        if source_category:
            query = query.filter(SupplierProduct.source_category == source_category)

        if q:
            term = f"%{q}%"
            query = query.filter((InternalProduct.title.ilike(term)) | (TradeMeListing.tm_listing_id.ilike(term)))

        total = query.count()
        rows = query.order_by(TradeMeListing.last_synced_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

        items = []
        for l in rows:
            ip = l.product
            sp = ip.supplier_product if ip else None
            imgs = _public_image_urls((sp.images if sp else None) or [])
            items.append(
                {
                    "id": l.id,
                    "tm_listing_id": l.tm_listing_id,
                    "internal_product_id": l.internal_product_id,
                    "actual_state": l.actual_state,
                    "lifecycle_state": str(l.lifecycle_state) if l.lifecycle_state is not None else None,
                    "actual_price": float(l.actual_price) if l.actual_price is not None else None,
                    "view_count": l.view_count,
                    "watch_count": l.watch_count,
                    "category_id": l.category_id,
                    "title": (ip.title if ip else None) or (sp.enriched_title if sp else None) or (sp.title if sp else None),
                    "thumb": imgs[0] if imgs else None,
                    "source_category": getattr(sp, "source_category", None) if sp else None,
                    "last_synced_at": _dt(l.last_synced_at),
                }
            )

        return PageResponse(items=items, total=total)
