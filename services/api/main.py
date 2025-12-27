from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from retail_os.core.database import (
    CommandStatus,
    InternalProduct,
    Order,
    Supplier,
    SupplierProduct,
    SystemCommand,
    TradeMeListing,
    get_db_session,
)


app = FastAPI(title="RetailOS API", version="0.1.0")

# MVP CORS: allow local dev frontends; tighten in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    status: str
    utc: datetime


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", utc=datetime.utcnow())


class PageResponse(BaseModel):
    items: list[dict[str, Any]]
    total: int


@app.get("/vaults/raw", response_model=PageResponse)
def vault_raw(
    q: Optional[str] = None,
    supplier_id: Optional[int] = None,
    sync_status: Optional[str] = None,
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

        total = query.count()
        rows = (
            query.order_by(SupplierProduct.last_scraped_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        items = []
        for sp in rows:
            items.append(
                {
                    "id": sp.id,
                    "supplier_id": sp.supplier_id,
                    "external_sku": sp.external_sku,
                    "title": sp.title,
                    "cost_price": float(sp.cost_price) if sp.cost_price is not None else None,
                    "stock_level": sp.stock_level,
                    "sync_status": sp.sync_status,
                    "product_url": sp.product_url,
                    "images": sp.images or [],
                    "specs": sp.specs or {},
                    "last_scraped_at": sp.last_scraped_at,
                }
            )

        return PageResponse(items=items, total=total)


@app.get("/vaults/enriched", response_model=PageResponse)
def vault_enriched(
    q: Optional[str] = None,
    supplier_id: Optional[int] = None,
    enrichment: str = "All",  # All | Enriched | Not Enriched
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

        if enrichment == "Enriched":
            query = query.filter(SupplierProduct.enriched_description.isnot(None))
        elif enrichment == "Not Enriched":
            query = query.filter(SupplierProduct.enriched_description.is_(None))

        total = query.count()
        rows = query.offset((page - 1) * per_page).limit(per_page).all()

        items = []
        for ip in rows:
            sp = ip.supplier_product
            items.append(
                {
                    "id": ip.id,
                    "sku": ip.sku,
                    "title": ip.title,
                    "supplier_product_id": ip.primary_supplier_product_id,
                    "supplier_id": sp.supplier_id if sp else None,
                    "cost_price": float(sp.cost_price) if sp and sp.cost_price is not None else None,
                    "enriched_title": sp.enriched_title if sp else None,
                    "enriched_description": sp.enriched_description if sp else None,
                    "images": (sp.images if sp else None) or [],
                }
            )

        return PageResponse(items=items, total=total)


@app.get("/vaults/live", response_model=PageResponse)
def vault_live(
    q: Optional[str] = None,
    status: str = "All",  # All | Live | Withdrawn | DRY_RUN
    page: int = 1,
    per_page: int = 50,
) -> PageResponse:
    if page < 1 or per_page < 1 or per_page > 1000:
        raise HTTPException(status_code=400, detail="Invalid pagination")

    with get_db_session() as session:
        query = session.query(TradeMeListing)

        if status != "All":
            query = query.filter(TradeMeListing.actual_state == status)

        if q:
            term = f"%{q}%"
            query = query.join(InternalProduct, TradeMeListing.internal_product_id == InternalProduct.id).filter(
                (InternalProduct.title.ilike(term)) | (TradeMeListing.tm_listing_id.ilike(term))
            )

        total = query.count()
        rows = (
            query.order_by(TradeMeListing.last_synced_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        items = []
        for l in rows:
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
                    "last_synced_at": l.last_synced_at,
                }
            )

        return PageResponse(items=items, total=total)


@app.get("/orders", response_model=PageResponse)
def orders(page: int = 1, per_page: int = 50) -> PageResponse:
    if page < 1 or per_page < 1 or per_page > 1000:
        raise HTTPException(status_code=400, detail="Invalid pagination")

    with get_db_session() as session:
        query = session.query(Order).order_by(Order.created_at.desc())
        total = query.count()
        rows = query.offset((page - 1) * per_page).limit(per_page).all()
        items = []
        for o in rows:
            items.append(
                {
                    "id": o.id,
                    "tm_order_ref": o.tm_order_ref,
                    "buyer_name": o.buyer_name,
                    "sold_price": float(o.sold_price) if o.sold_price is not None else None,
                    "sold_date": o.sold_date,
                    "order_status": o.order_status,
                    "payment_status": o.payment_status,
                    "fulfillment_status": o.fulfillment_status,
                    "created_at": o.created_at,
                }
            )
        return PageResponse(items=items, total=total)


@app.get("/suppliers", response_model=list[dict[str, Any]])
def suppliers() -> list[dict[str, Any]]:
    with get_db_session() as session:
        rows = session.query(Supplier).order_by(Supplier.name.asc()).all()
        return [{"id": s.id, "name": s.name, "base_url": s.base_url, "is_active": s.is_active} for s in rows]


class CommandCreateRequest(BaseModel):
    type: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: int = 10


class CommandCreateResponse(BaseModel):
    id: str
    status: str


@app.post("/commands", response_model=CommandCreateResponse)
def create_command(req: CommandCreateRequest) -> CommandCreateResponse:
    import uuid

    with get_db_session() as session:
        cmd = SystemCommand(
            id=str(uuid.uuid4()),
            type=req.type,
            payload=req.payload,
            status=CommandStatus.PENDING,
            priority=req.priority,
        )
        session.add(cmd)
        session.commit()
        return CommandCreateResponse(id=cmd.id, status=cmd.status.value if hasattr(cmd.status, "value") else str(cmd.status))


@app.get("/commands", response_model=PageResponse)
def list_commands(page: int = 1, per_page: int = 50) -> PageResponse:
    if page < 1 or per_page < 1 or per_page > 1000:
        raise HTTPException(status_code=400, detail="Invalid pagination")

    with get_db_session() as session:
        query = session.query(SystemCommand).order_by(SystemCommand.created_at.desc())
        total = query.count()
        rows = query.offset((page - 1) * per_page).limit(per_page).all()
        items = []
        for c in rows:
            items.append(
                {
                    "id": c.id,
                    "type": c.type,
                    "status": c.status.value if hasattr(c.status, "value") else str(c.status),
                    "priority": c.priority,
                    "attempts": c.attempts,
                    "max_attempts": c.max_attempts,
                    "last_error": c.last_error,
                    "created_at": c.created_at,
                    "updated_at": c.updated_at,
                }
            )
        return PageResponse(items=items, total=total)

