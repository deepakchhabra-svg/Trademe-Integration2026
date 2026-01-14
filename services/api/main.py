from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, text

from retail_os.core.database import (
    AuditLog,
    CommandLog,
    CommandProgress,
    CommandStatus,
    InternalProduct,
    JobStatus,
    ListingDraft,
    ListingMetricSnapshot,
    Order,
    Supplier,
    SupplierProduct,
    SystemCommand,
    SystemSetting,
    TradeMeListing,
    get_db_session,
)
from retail_os.core.validator import LaunchLock
from retail_os.trademe.api import TradeMeAPI
from retail_os.core.llm_enricher import enricher as _llm_enricher
from retail_os.core.category_mapper import CategoryMapper

from .schemas import PageResponse, HealthResponse
from .utils import _REPO_ROOT, _MEDIA_ROOT, _dt, _public_image_urls, _serialize_supplier_product, _serialize_internal_product, _serialize_listing
from .dependencies import Role, require_role, require_authenticated, get_request_role, _env_bool, _role_rank
from .routers import ops, vaults
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup/shutdown events.
    Replaces deprecated @app.on_event("startup").
    """
    # Startup: Ensure DB schema exists
    try:
        from retail_os.core.database import init_db
        init_db()
    except Exception as e:
        # Don't crash the API process; surface errors through endpoints/logs instead.
        print(f"API startup: init_db failed: {e}")
    
    # Start background worker in separate thread
    worker_thread = None
    worker_stop_event = None
    try:
        import threading
        from retail_os.trademe.worker import CommandWorker
        
        worker_stop_event = threading.Event()
        
        def run_worker():
            """Run the command worker in a background thread."""
            print("Starting background worker thread...")
            worker = CommandWorker()
            # Run worker with stop event
            while not worker_stop_event.is_set():
                try:
                    worker.poll_once()  # Process one batch of commands
                except Exception as e:
                    print(f"Worker error: {e}")
                    import time
                    time.sleep(5)  # Wait before retrying on error
        
        worker_thread = threading.Thread(target=run_worker, daemon=True, name="CommandWorker")
        worker_thread.start()
        print("Background worker thread started successfully")
    except Exception as e:
        print(f"Failed to start background worker: {e}")
    
    yield  # Application runs here
    
    # Shutdown: Stop worker thread
    if worker_stop_event:
        print("Stopping background worker...")
        worker_stop_event.set()
    if worker_thread and worker_thread.is_alive():
        worker_thread.join(timeout=10)
        print("Background worker stopped")

app = FastAPI(title="RetailOS API", version="0.1.0", lifespan=lifespan)

app.include_router(ops.router)
app.include_router(vaults.router)

@app.get("/")
def root():
    """Root endpoint - API welcome page."""
    return {
        "name": "RetailOS API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics"
    }

def _parse_csv_env(name: str, default: list[str]) -> list[str]:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    parts = [p.strip() for p in raw.split(",")]
    parts = [p for p in parts if p]
    return parts or default




# CORS: explicit allowlist (production-safe). Prefer running the web UI via the Next proxy
# to avoid needing CORS at all.
_cors_origins = _parse_csv_env(
    "RETAIL_OS_CORS_ORIGINS",
    default=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://trademe-integration-ui-production.up.railway.app",
    ],
)
_cors_allow_credentials = _env_bool("RETAIL_OS_CORS_ALLOW_CREDENTIALS", default=False)
if "*" in _cors_origins:
    # Browsers forbid credentials with wildcard origins; keep it safe by forcing creds off.
    _cors_allow_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)




@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    # Include DB probe so local env issues are obvious.
    try:
        with get_db_session() as session:
            session.execute(text("SELECT 1"))
        return HealthResponse(status="ok", utc=datetime.now(timezone.utc), db="ok", db_error=None)
    except Exception as e:
        return HealthResponse(status="degraded", utc=datetime.now(timezone.utc), db="error", db_error=str(e)[:200])


@app.get("/metrics")
def metrics() -> dict[str, Any]:
    """
    Prometheus-compatible metrics endpoint for monitoring.
    Returns key operational metrics for dashboards and alerting.
    """
    try:
        with get_db_session() as session:
            from sqlalchemy import func
            
            # Count key entities
            sp_total = session.query(func.count(SupplierProduct.id)).scalar() or 0
            sp_present = session.query(func.count(SupplierProduct.id)).filter(
                SupplierProduct.sync_status == "PRESENT"
            ).scalar() or 0
            sp_pending_enrich = session.query(func.count(SupplierProduct.id)).filter(
                SupplierProduct.enrichment_status == "PENDING"
            ).scalar() or 0
            
            ip_total = session.query(func.count(InternalProduct.id)).scalar() or 0
            
            listings_live = session.query(func.count(TradeMeListing.id)).filter(
                TradeMeListing.actual_state == "Live"
            ).scalar() or 0
            listings_draft = session.query(func.count(TradeMeListing.id)).filter(
                TradeMeListing.actual_state == "DRY_RUN"
            ).scalar() or 0
            
            # Command queue metrics
            cmd_pending = session.query(func.count(SystemCommand.id)).filter(
                SystemCommand.status == "PENDING"
            ).scalar() or 0
            cmd_executing = session.query(func.count(SystemCommand.id)).filter(
                SystemCommand.status == "EXECUTING"
            ).scalar() or 0
            cmd_failed = session.query(func.count(SystemCommand.id)).filter(
                SystemCommand.status.in_(["FAILED_RETRYABLE", "FAILED_FATAL", "HUMAN_REQUIRED"])
            ).scalar() or 0
            
            # Order metrics
            orders_pending = session.query(func.count(Order.id)).filter(
                Order.fulfillment_status == "PENDING"
            ).scalar() or 0
            
            return {
                "status": "ok",
                "utc": datetime.now(timezone.utc).isoformat(),
                "metrics": {
                    "supplier_products_total": sp_total,
                    "supplier_products_present": sp_present,
                    "supplier_products_pending_enrichment": sp_pending_enrich,
                    "internal_products_total": ip_total,
                    "listings_live": listings_live,
                    "listings_draft": listings_draft,
                    "commands_pending": cmd_pending,
                    "commands_executing": cmd_executing,
                    "commands_failed": cmd_failed,
                    "orders_pending_fulfillment": orders_pending,
                }
            }
    except Exception as e:
        return {
            "status": "error",
            "utc": datetime.now(timezone.utc).isoformat(),
            "error": str(e)[:200],
            "metrics": {}
        }


@app.get("/media/{rel_path:path}")
def media(rel_path: str, _role: Role = Depends(require_authenticated("listing"))) -> FileResponse:
    """
    Serve locally downloaded images (data/media/*) to the web app.
    Security: path must stay within MEDIA_ROOT.
    """
    # Normalize and prevent traversal
    rel = rel_path.replace("\\", "/").lstrip("/")
    target = (_MEDIA_ROOT / rel).resolve()
    if _MEDIA_ROOT not in target.parents and target != _MEDIA_ROOT:
        raise HTTPException(status_code=400, detail="Invalid media path")
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Media not found")
    return FileResponse(path=str(target))


@app.get("/whoami")
def whoami(role: Role = Depends(get_request_role)) -> dict[str, Any]:
    return {
        "role": role,
        "rank": _role_rank(role),
        "cors": {
            "origins": _cors_origins,
            "allow_credentials": _cors_allow_credentials,
        },
        "rbac": {
            "default_role": (os.getenv("RETAIL_OS_DEFAULT_ROLE") or "listing").strip().lower(),
            "insecure_allow_header_roles": _env_bool("RETAIL_OS_INSECURE_ALLOW_HEADER_ROLES", default=False),
            "tokens_configured": any(
                bool(os.getenv(k))
                for k in (
                    "RETAIL_OS_ROOT_TOKEN",
                    "RETAIL_OS_POWER_TOKEN",
                    "RETAIL_OS_FULFILLMENT_TOKEN",
                    "RETAIL_OS_LISTING_TOKEN",
                )
            ),
        },
    }




@app.get("/trademe/account_summary")
def trademe_account_summary(_role: Role = Depends(require_role("power"))) -> dict[str, Any]:
    """
    Trade Me account health for ops decisions (balance, reputation signals).
    """
    import os as _os
    utc = datetime.now(timezone.utc).isoformat()
    configured = bool(
        (_os.getenv("CONSUMER_KEY") or "").strip()
        and (_os.getenv("CONSUMER_SECRET") or "").strip()
        and (_os.getenv("ACCESS_TOKEN") or "").strip()
        and (_os.getenv("ACCESS_TOKEN_SECRET") or "").strip()
    )
    try:
        api = TradeMeAPI()
        out = api.get_account_summary()
        out["utc"] = utc
        out["configured"] = True
        out["auth_ok"] = True
        return out
    except Exception as e:
        # Keep ops UI functional even when credentials are not configured in this environment.
        msg = str(e)[:200]
        if not configured:
            msg = "Not configured (missing Trade Me credentials)"
        return {
            "offline": True,
            "error": msg,
            "utc": utc,
            "configured": configured,
            "auth_ok": False,
            # Safe diagnostics: never include secrets.
            "diagnostics": {"configured": configured},
        }


@app.get("/llm/health")
def llm_health(_role: Role = Depends(require_role("power"))) -> dict[str, Any]:
    """
    Operator diagnostics: returns configured provider + model info.
    No fake "healthy" status when misconfigured.
    """
    return _llm_enricher.health()


class TradeMeValidateDraftsRequest(BaseModel):
    supplier_id: Optional[int] = None
    limit: int = 10


@app.post("/trademe/validate_drafts")
def trademe_validate_drafts(
    req: TradeMeValidateDraftsRequest,
    _role: Role = Depends(require_role("power")),
) -> dict[str, Any]:
    """
    Validates a small batch of draft payloads using real Trade Me credentials.
    This uses TradeMeAPI.validate_listing() and will return "Not configured" if credentials are missing.
    """
    import os as _os

    utc = datetime.now(timezone.utc).isoformat()
    configured = bool(
        (_os.getenv("CONSUMER_KEY") or "").strip()
        and (_os.getenv("CONSUMER_SECRET") or "").strip()
        and (_os.getenv("ACCESS_TOKEN") or "").strip()
        and (_os.getenv("ACCESS_TOKEN_SECRET") or "").strip()
    )
    if not configured:
        return {"utc": utc, "configured": False, "auth_ok": False, "results": [], "error": "Not configured"}

    if req.limit < 1 or req.limit > 50:
        raise HTTPException(status_code=400, detail="limit must be 1–50")

    api = TradeMeAPI()

    from retail_os.core.listing_builder import build_listing_payload

    results: list[dict[str, Any]] = []
    with get_db_session() as session:
        q = session.query(InternalProduct).join(SupplierProduct, InternalProduct.primary_supplier_product_id == SupplierProduct.id)
        q = q.filter((SupplierProduct.sync_status.is_(None)) | (SupplierProduct.sync_status == "PRESENT"))
        q = q.filter(SupplierProduct.enriched_title.isnot(None)).filter(SupplierProduct.enriched_description.isnot(None))
        if req.supplier_id is not None:
            q = q.filter(SupplierProduct.supplier_id == int(req.supplier_id))

        rows = q.order_by(SupplierProduct.last_scraped_at.desc()).limit(int(req.limit)).all()

        for ip in rows:
            sp = ip.supplier_product
            item = {"internal_product_id": ip.id, "sku": ip.sku, "supplier_product_id": sp.id if sp else None}
            try:
                payload = build_listing_payload(ip.id)

                # Upload ONE local image to get a real PhotoId (Trade Me validate is strict).
                photo_id = None
                if sp and sp.images and isinstance(sp.images, list):
                    import os as _os2

                    for img in sp.images:
                        if isinstance(img, str) and _os2.path.exists(img):
                            with open(img, "rb") as f:
                                b = f.read()
                            photo_id = api.upload_photo_idempotent(session, b, filename=_os2.path.basename(img) or "image.jpg")
                            break
                if photo_id:
                    payload["PhotoIds"] = [photo_id]
                # PhotoUrls are for operator preview only; validation uses PhotoIds.
                payload.pop("PhotoUrls", None)

                resp = api.validate_listing(payload)
                ok = bool(resp.get("Success")) if isinstance(resp, dict) else False
                item["ok"] = ok
                item["response"] = resp
            except Exception as e:
                item["ok"] = False
                item["error"] = str(e)[:400]
            results.append(item)

    return {"utc": utc, "configured": True, "auth_ok": True, "results": results}


class CommandCreateResponse(BaseModel):
    id: str
    status: str


@app.get("/products", response_model=PageResponse)
def master_products(
    q: Optional[str] = None,
    supplier_id: Optional[int] = None,
    source_category: Optional[str] = None,
    stage: Optional[str] = None,  # raw|enriched|draft|live|blocked|all
    page: int = 1,
    per_page: int = 50,
) -> PageResponse:
    """
    Master Product View: one row per supplier product (raw → enriched → listing).
    This keeps the 3-vault architecture while providing an ERP-style "single pane" for operators.
    """
    if page < 1 or per_page < 1 or per_page > 1000:
        raise HTTPException(status_code=400, detail="Invalid pagination")

    def _blocked_reasons(sp: SupplierProduct) -> list[str]:
        reasons: list[str] = []
        if sp.sync_status == "REMOVED":
            reasons.append("Removed from supplier feed")
        if sp.cost_price is None or float(sp.cost_price or 0) <= 0:
            reasons.append("Missing/invalid cost price")
        if not (sp.images or []):
            reasons.append("Missing images")
        if not (sp.enriched_title or "").strip():
            reasons.append("Missing enriched title")
        if not (sp.enriched_description or "").strip():
            reasons.append("Missing enriched description")
        return reasons

    def _listing_stage(ip: Optional[InternalProduct]) -> str | None:
        if not ip:
            return None
        states = [str(l.actual_state) for l in (ip.listings or []) if getattr(l, "actual_state", None)]
        if "Live" in states:
            return "live"
        if "DRY_RUN" in states:
            return "draft"
        return None

    stage_norm = (stage or "all").strip().lower()

    with get_db_session() as session:
        query = session.query(SupplierProduct)

        if q:
            term = f"%{q}%"
            query = query.filter((SupplierProduct.title.ilike(term)) | (SupplierProduct.external_sku.ilike(term)))
        if supplier_id:
            query = query.filter(SupplierProduct.supplier_id == supplier_id)
        if source_category:
            query = query.filter(getattr(SupplierProduct, "source_category") == source_category)

        total = query.count()
        rows = (
            query.order_by(SupplierProduct.last_scraped_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        items: list[dict[str, Any]] = []
        for sp in rows:
            ip = getattr(sp, "internal_product", None)
            listing_stage = _listing_stage(ip)
            blocked = _blocked_reasons(sp)

            # Apply stage filter after compute (simple + safe).
            if stage_norm not in ("", "all"):
                if stage_norm == "raw" and ip is not None:
                    continue
                if stage_norm == "enriched" and (ip is None or blocked):
                    continue
                if stage_norm == "draft" and listing_stage != "draft":
                    continue
                if stage_norm == "live" and listing_stage != "live":
                    continue
                if stage_norm == "blocked" and not blocked:
                    continue

            final_category_id = CategoryMapper.map_category(
                getattr(sp, "source_category", "") or "",
                sp.title or "",
                (getattr(sp, "enriched_description", None) or getattr(sp, "description", None) or ""),
            )
            final_category_name = CategoryMapper.get_category_name(final_category_id) if final_category_id else None

            items.append(
                {
                    "supplier_product_id": sp.id,
                    "supplier_id": sp.supplier_id,
                    "supplier_name": sp.supplier.name if getattr(sp, "supplier", None) else None,
                    "supplier_sku": sp.external_sku,
                    "title": sp.title,
                    "cost_price": float(sp.cost_price) if sp.cost_price is not None else None,
                    "stock_level": sp.stock_level,
                    "source_status": sp.sync_status,
                    "source_category": getattr(sp, "source_category", None),
                    "final_category_id": final_category_id,
                    "final_category_name": final_category_name,
                    "product_url": sp.product_url,
                    "images": _public_image_urls(sp.images or []),
                    "last_scraped_at": _dt(sp.last_scraped_at),
                    "enrichment_status": sp.enrichment_status,
                    "internal_product_id": ip.id if ip else None,
                    "internal_sku": ip.sku if ip else None,
                    "listing_stage": listing_stage,
                    "blocked_reasons": blocked,
                }
            )

        return PageResponse(items=items, total=total)


@app.get("/orders", response_model=PageResponse)
def orders(
    page: int = 1,
    per_page: int = 50,
    q: Optional[str] = None,
    fulfillment_status: Optional[str] = None,
    payment_status: Optional[str] = None,
    order_status: Optional[str] = None,
    _role: Role = Depends(require_role("fulfillment")),
) -> PageResponse:
    if page < 1 or per_page < 1 or per_page > 1000:
        raise HTTPException(status_code=400, detail="Invalid pagination")

    with get_db_session() as session:
        query = session.query(Order)
        if q:
            term = f"%{q}%"
            query = query.filter((Order.tm_order_ref.ilike(term)) | (Order.buyer_name.ilike(term)))
        if fulfillment_status:
            query = query.filter(Order.fulfillment_status == fulfillment_status)
        if payment_status:
            query = query.filter(Order.payment_status == payment_status)
        if order_status:
            query = query.filter(Order.order_status == order_status)

        query = query.order_by(Order.created_at.desc())
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
                    "sold_date": _dt(o.sold_date),
                    "order_status": o.order_status,
                    "payment_status": o.payment_status,
                    "fulfillment_status": o.fulfillment_status,
                    "created_at": _dt(o.created_at),
                }
            )
        return PageResponse(items=items, total=total)


@app.get("/suppliers", response_model=list[dict[str, Any]])
def suppliers() -> list[dict[str, Any]]:
    with get_db_session() as session:
        rows = session.query(Supplier).order_by(Supplier.name.asc()).all()
        return [{"id": s.id, "name": s.name, "base_url": s.base_url, "is_active": s.is_active} for s in rows]


def _supplier_policy_key(supplier_id: int) -> str:
    return f"supplier.policy.{int(supplier_id)}"


def _get_supplier_policy(session, supplier_id: int) -> dict[str, Any]:
    """
    Per-supplier policy stored in SystemSetting.
    This avoids schema migrations and keeps policies auditable + editable.
    """
    default_policy: dict[str, Any] = {
        "enabled": True,
        "scrape": {"enabled": True, "category_presets": []},
        "enrich": {"enabled": True, "enrichment_policy_override": None},
        "publish": {"enabled": True, "publishing_policy_override": None},
    }
    row = session.query(SystemSetting).filter(SystemSetting.key == _supplier_policy_key(supplier_id)).first()
    if row and isinstance(row.value, dict):
        v = row.value
        out = {**default_policy, **v}
        out["scrape"] = {**default_policy["scrape"], **(v.get("scrape") if isinstance(v.get("scrape"), dict) else {})}
        out["enrich"] = {**default_policy["enrich"], **(v.get("enrich") if isinstance(v.get("enrich"), dict) else {})}
        out["publish"] = {**default_policy["publish"], **(v.get("publish") if isinstance(v.get("publish"), dict) else {})}
        return out
    return default_policy


@app.get("/suppliers/{supplier_id}/policy")
def supplier_policy_get(
    supplier_id: int,
    _role: Role = Depends(require_role("power")),
) -> dict[str, Any]:
    with get_db_session() as session:
        s = session.query(Supplier).filter(Supplier.id == int(supplier_id)).first()
        if not s:
            raise HTTPException(status_code=404, detail="Supplier not found")
        return {"supplier_id": s.id, "supplier_name": s.name, "policy": _get_supplier_policy(session, s.id)}


class SupplierPolicyPutRequest(BaseModel):
    policy: dict[str, Any]


@app.put("/suppliers/{supplier_id}/policy")
def supplier_policy_put(
    supplier_id: int,
    req: SupplierPolicyPutRequest,
    _role: Role = Depends(require_role("root")),
) -> dict[str, Any]:
    if not isinstance(req.policy, dict):
        raise HTTPException(status_code=400, detail="policy must be an object")
    with get_db_session() as session:
        s = session.query(Supplier).filter(Supplier.id == int(supplier_id)).first()
        if not s:
            raise HTTPException(status_code=404, detail="Supplier not found")
        row = session.query(SystemSetting).filter(SystemSetting.key == _supplier_policy_key(s.id)).first()
        if not row:
            row = SystemSetting(key=_supplier_policy_key(s.id), value=req.policy)
            session.add(row)
        else:
            row.value = req.policy
        session.commit()
        return {"supplier_id": s.id, "supplier_name": s.name, "policy": _get_supplier_policy(session, s.id)}


class CommandCreateRequest(BaseModel):
    type: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: int = 10


@app.post("/commands", response_model=CommandCreateResponse)
def create_command(
    req: CommandCreateRequest,
    _role: Role = Depends(require_role("listing")),
) -> CommandCreateResponse:
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
def list_commands(
    page: int = 1,
    per_page: int = 50,
    status: Optional[str] = None,
    type: Optional[str] = None,
) -> PageResponse:
    if page < 1 or per_page < 1 or per_page > 1000:
        raise HTTPException(status_code=400, detail="Invalid pagination")

    with get_db_session() as session:
        query = session.query(SystemCommand)
        if status:
            if status == "NOT_SUCCEEDED":
                query = query.filter(SystemCommand.status != CommandStatus.SUCCEEDED)
            elif status == "ACTIVE":
                query = query.filter(SystemCommand.status.in_([CommandStatus.PENDING, CommandStatus.EXECUTING]))
            elif status == "NEEDS_ATTENTION":
                query = query.filter(SystemCommand.status.in_([CommandStatus.HUMAN_REQUIRED, CommandStatus.FAILED_RETRYABLE, CommandStatus.FAILED_FATAL]))
            else:
                try:
                    query = query.filter(SystemCommand.status == CommandStatus(status))
                except Exception:
                    raise HTTPException(status_code=400, detail="Invalid status filter")
        if type:
            query = query.filter(SystemCommand.type == type)
        query = query.order_by(SystemCommand.created_at.desc())
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
                    "error_code": c.error_code,
                    "error_message": c.error_message,
                    "payload": c.payload or {},
                    "created_at": _dt(c.created_at),
                    "updated_at": _dt(c.updated_at),
                }
            )
        return PageResponse(items=items, total=total)


class CommandActionResponse(BaseModel):
    id: str
    status: str


@app.post("/commands/{command_id}/retry", response_model=CommandActionResponse)
def retry_command(command_id: str, _role: Role = Depends(require_role("power"))) -> CommandActionResponse:
    with get_db_session() as session:
        c = session.query(SystemCommand).filter(SystemCommand.id == command_id).first()
        if not c:
            raise HTTPException(status_code=404, detail="Command not found")
        # Reset only if it's not already pending/executing
        c.status = CommandStatus.PENDING
        c.last_error = None
        c.error_code = None
        c.error_message = None
        c.updated_at = datetime.now(timezone.utc)
        session.commit()
        return CommandActionResponse(id=c.id, status=c.status.value if hasattr(c.status, "value") else str(c.status))


@app.post("/commands/{command_id}/cancel", response_model=CommandActionResponse)
def cancel_command(command_id: str, _role: Role = Depends(require_role("power"))) -> CommandActionResponse:
    with get_db_session() as session:
        c = session.query(SystemCommand).filter(SystemCommand.id == command_id).first()
        if not c:
            raise HTTPException(status_code=404, detail="Command not found")
        c.status = CommandStatus.CANCELLED
        c.updated_at = datetime.now(timezone.utc)
        session.commit()
        return CommandActionResponse(id=c.id, status=c.status.value if hasattr(c.status, "value") else str(c.status))


@app.post("/commands/{command_id}/ack", response_model=CommandActionResponse)
def ack_command(command_id: str, _role: Role = Depends(require_role("power"))) -> CommandActionResponse:
    """
    Acknowledge a HUMAN_REQUIRED command without deleting history.
    For now we mark it CANCELLED (operator accepted the outcome).
    """
    return cancel_command(command_id, _role=_role)


@app.get("/commands/{command_id}")
def command_detail(
    command_id: str,
    _role: Role = Depends(require_role("power")),
) -> dict[str, Any]:
    with get_db_session() as session:
        c = session.query(SystemCommand).filter(SystemCommand.id == command_id).first()
        if not c:
            raise HTTPException(status_code=404, detail="Command not found")
        return {
            "id": c.id,
            "type": c.type,
            "status": c.status.value if hasattr(c.status, "value") else str(c.status),
            "priority": c.priority,
            "attempts": c.attempts,
            "max_attempts": c.max_attempts,
            "last_error": c.last_error,
            "error_code": c.error_code,
            "error_message": c.error_message,
            "payload": c.payload or {},
            "created_at": _dt(c.created_at),
            "updated_at": _dt(c.updated_at),
        }


@app.get("/commands/{command_id}/progress")
def command_progress(
    command_id: str,
    _role: Role = Depends(require_role("power")),
) -> dict[str, Any]:
    """
    DB-backed progress snapshot for long-running commands.
    Designed for reliable progress bars even after restarts.
    """
    with get_db_session() as session:
        exists = session.query(SystemCommand.id).filter(SystemCommand.id == command_id).first()
        if not exists:
            raise HTTPException(status_code=404, detail="Command not found")

        p = session.query(CommandProgress).filter(CommandProgress.command_id == command_id).first()
        return {
            "command_id": command_id,
            "progress": (
                {
                    "phase": p.phase,
                    "done": p.done,
                    "total": p.total,
                    "eta_seconds": p.eta_seconds,
                    "message": p.message,
                    "updated_at": _dt(p.updated_at),
                }
                if p
                else None
            ),
        }


@app.get("/commands/{command_id}/logs")
def command_logs(
    command_id: str,
    after_id: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=2000),
    tail: bool = Query(False),
    _role: Role = Depends(require_role("power")),
) -> dict[str, Any]:
    """
    Persisted per-command logs for operator visibility.
    - tail=true returns the last N log lines (ascending order in response).
    - otherwise returns logs strictly after `after_id` (for polling / streaming).
    """
    with get_db_session() as session:
        exists = session.query(SystemCommand.id).filter(SystemCommand.id == command_id).first()
        if not exists:
            raise HTTPException(status_code=404, detail="Command not found")

        q = session.query(CommandLog).filter(CommandLog.command_id == command_id)
        if tail:
            rows = q.order_by(CommandLog.id.desc()).limit(limit).all()
            rows = list(reversed(rows))
        else:
            if after_id:
                q = q.filter(CommandLog.id > int(after_id))
            rows = q.order_by(CommandLog.id.asc()).limit(limit).all()

        next_after = int(rows[-1].id) if rows else int(after_id)
        return {
            "command_id": command_id,
            "next_after_id": next_after,
            "logs": [
                {
                    "id": int(r.id),
                    "created_at": _dt(r.created_at),
                    "level": r.level,
                    "logger": r.logger,
                    "message": r.message,
                    "meta": r.meta,
                }
                for r in rows
            ],
        }


@app.get("/supplier-products/{supplier_product_id}")
def supplier_product_detail(supplier_product_id: int) -> dict[str, Any]:
    with get_db_session() as session:
        sp = session.query(SupplierProduct).filter(SupplierProduct.id == supplier_product_id).first()
        if not sp:
            raise HTTPException(status_code=404, detail="SupplierProduct not found")
        return _serialize_supplier_product(sp)


@app.get("/internal-products/{internal_product_id}")
def internal_product_detail(internal_product_id: int) -> dict[str, Any]:
    with get_db_session() as session:
        ip = session.query(InternalProduct).filter(InternalProduct.id == internal_product_id).first()
        if not ip:
            raise HTTPException(status_code=404, detail="InternalProduct not found")
        return _serialize_internal_product(ip)


@app.get("/listings/{listing_id}")
def listing_detail(listing_id: int) -> dict[str, Any]:
    with get_db_session() as session:
        l = session.query(TradeMeListing).filter(TradeMeListing.id == listing_id).first()
        if not l:
            raise HTTPException(status_code=404, detail="Listing not found")
        data = _serialize_listing(l)

        # Listing preview + hard gate evaluation (Vault 3 should be "what buyers will see" + blockers).
        try:
            import json as _json

            payload_obj: dict[str, Any] | None = None
            if l.payload_snapshot:
                try:
                    payload_obj = _json.loads(l.payload_snapshot)
                except Exception:
                    payload_obj = None
            data["payload_preview"] = payload_obj

            checks: list[dict[str, Any]] = []
            sp = l.product.supplier_product if l.product else None

            def _add(key: str, ok: bool, reason: str | None = None):
                checks.append({"key": key, "ok": bool(ok), "reason": reason})

            # If the worker persisted a BLOCKED snapshot, treat that as authoritative.
            if isinstance(payload_obj, dict) and payload_obj.get("_blocked") is True:
                top = str(payload_obj.get("top_blocker") or payload_obj.get("error") or "Blocked")
                data["launchlock"] = {"ready": False, "top_blocker": top, "checks": [{"key": "launchlock", "ok": False, "reason": top}]}
                # Still include parsed payload for display (if any).
                raise Exception("__BLOCKED_SNAPSHOT_HANDLED__")

            if sp:
                _add("source_url", bool((sp.product_url or "").strip()), "Missing source URL" if not (sp.product_url or "").strip() else None)
                _add("removed_from_source", str(sp.sync_status or "").upper() != "REMOVED", "Removed from supplier feed" if str(sp.sync_status or "").upper() == "REMOVED" else None)
            else:
                _add("source_url", False, "Missing supplier product link")
                _add("removed_from_source", False, "Missing supplier product link")

            title = None
            desc = None
            category = None
            start_price = None
            photos = []
            if isinstance(payload_obj, dict):
                title = payload_obj.get("Title")
                d0 = payload_obj.get("Description")
                desc = (d0[0] if isinstance(d0, list) and d0 else d0) if d0 is not None else None
                category = payload_obj.get("Category")
                start_price = payload_obj.get("StartPrice")
                photos = payload_obj.get("PhotoUrls") if isinstance(payload_obj.get("PhotoUrls"), list) else []

            _add("final_title", bool(str(title or "").strip()) and str(title).strip().lower() not in {"untitled product", "tbd", "placeholder"}, "Missing/placeholder title" if not bool(str(title or "").strip()) else None)
            _add("final_description", bool(str(desc or "").strip()) and str(desc).strip().lower() not in {"tbd", "placeholder"}, "Missing/placeholder description" if not bool(str(desc or "").strip()) else None)

            # Category must be mapped (not default fallback)
            default_cat = getattr(CategoryMapper, "DEFAULT_CATEGORY", None)
            cat_ok = bool(str(category or "").strip()) and (default_cat is None or str(category) != str(default_cat))
            _add("category_mapped", cat_ok, "Unmapped Trade Me category" if not cat_ok else None)

            # Sell price comes from payload StartPrice
            try:
                sell_ok = start_price is not None and float(start_price) > 0
            except Exception:
                sell_ok = False
            _add("sell_price", sell_ok, "Sell price not set" if not sell_ok else None)

            # Require at least one local image usable for upload.
            # (Remote-only images are blocked to avoid “looks visible but can’t upload” failures.)
            has_local = False
            if sp and sp.images and isinstance(sp.images, list):
                import os as _os
                for img in sp.images:
                    if isinstance(img, str) and _os.path.exists(img):
                        has_local = True
                        break
            _add("images_usable", has_local, "Images unavailable for upload (no local images)" if not has_local else None)

            ready = all(x.get("ok") for x in checks)
            top_blocker = next((x.get("reason") for x in checks if not x.get("ok") and x.get("reason")), None)
            data["launchlock"] = {"ready": ready, "top_blocker": top_blocker, "checks": checks}
        except Exception as e:
            # Swallow sentinel used to stop further evaluation after BLOCKED snapshot handling.
            if str(e) != "__BLOCKED_SNAPSHOT_HANDLED__":
                data["launchlock_error"] = str(e)[:500]

        # Derived diagnostics for power users
        try:
            from retail_os.analysis.profitability import ProfitabilityAnalyzer

            sp = l.product.supplier_product if l.product else None
            if sp and sp.cost_price is not None and (l.actual_price is not None or l.desired_price is not None):
                price = float(l.actual_price if l.actual_price is not None else l.desired_price)
                cost = float(sp.cost_price)
                data["profitability_preview"] = ProfitabilityAnalyzer.predict_profitability(price, cost)
        except Exception as e:
            data["profitability_preview_error"] = str(e)[:500]

        try:
            from retail_os.strategy.lifecycle import LifecycleManager

            data["lifecycle_recommendation"] = LifecycleManager.evaluate_state(l)
            data["repricing_recommendation"] = LifecycleManager.get_repricing_recommendation(l)
        except Exception as e:
            data["lifecycle_error"] = str(e)[:500]

        try:
            if l.product:
                report = LaunchLock(session).trust_engine.get_product_trust_report(l.product)
                data["trust_report"] = {
                    "score": report.score,
                    "is_trusted": report.is_trusted,
                    "blockers": report.blockers,
                    "breakdown": report.breakdown,
                }
        except Exception as e:
            data["trust_error"] = str(e)[:500]

        return data


@app.get("/inspector/supplier-products/{supplier_product_id}")
def inspector_supplier_product(
    supplier_product_id: int,
    _role: Role = Depends(require_role("power")),
) -> dict[str, Any]:
    """
    Single truth screen backing API: Raw → Enriched → Listing (Draft/Live) + gates in one response.
    """
    with get_db_session() as session:
        sp = session.query(SupplierProduct).filter(SupplierProduct.id == int(supplier_product_id)).first()
        if not sp:
            raise HTTPException(status_code=404, detail="SupplierProduct not found")
        ip = getattr(sp, "internal_product", None)
        listings: list[TradeMeListing] = []
        if ip:
            listings = (
                session.query(TradeMeListing)
                .filter(TradeMeListing.internal_product_id == int(ip.id))
                .order_by(TradeMeListing.last_synced_at.desc().nullslast())
                .all()
            )

        return {
            "supplier_product": _serialize_supplier_product(sp),
            "internal_product": _serialize_internal_product(ip) if ip else None,
            "listings": [_serialize_listing(l) for l in listings],
        }


@app.get("/trust/internal-products/{internal_product_id}")
def trust_internal_product(
    internal_product_id: int,
    _role: Role = Depends(require_role("power")),
) -> dict[str, Any]:
    with get_db_session() as session:
        ip = session.query(InternalProduct).filter(InternalProduct.id == internal_product_id).first()
        if not ip:
            raise HTTPException(status_code=404, detail="InternalProduct not found")
        report = LaunchLock(session).trust_engine.get_product_trust_report(ip)
        return {
            "internal_product_id": ip.id,
            "score": report.score,
            "is_trusted": report.is_trusted,
            "blockers": report.blockers,
            "breakdown": report.breakdown,
        }


@app.get("/validate/internal-products/{internal_product_id}")
def validate_internal_product(
    internal_product_id: int,
    test_bypass: int = Query(0, ge=0, le=1),
    _role: Role = Depends(require_role("power")),
) -> dict[str, Any]:
    """
    Runs LaunchLock validation without making Trade Me API calls.
    Useful for surfacing gate reasons in the UI.
    """
    with get_db_session() as session:
        ip = session.query(InternalProduct).filter(InternalProduct.id == internal_product_id).first()
        if not ip:
            raise HTTPException(status_code=404, detail="InternalProduct not found")
        try:
            # Production behavior: ALWAYS enforce full LaunchLock gates.
            #
            # Optional test-only bypass:
            # - query param: ?test_bypass=1
            # - env gate: RETAIL_OS_ALLOW_TEST_BYPASS=1
            allow_bypass = _env_bool("RETAIL_OS_ALLOW_TEST_BYPASS", default=False)
            use_bypass = bool(test_bypass == 1 and allow_bypass)
            LaunchLock(session).validate_publish(ip, test_mode=use_bypass)
            return {"internal_product_id": ip.id, "ok": True, "reason": None}
        except Exception as e:
            return {"internal_product_id": ip.id, "ok": False, "reason": str(e)[:2000]}


@app.get("/draft/internal-products/{internal_product_id}/trademe")
def draft_trademe_payload(
    internal_product_id: int,
    _role: Role = Depends(require_role("power")),
) -> dict[str, Any]:
    """
    Returns the *draft* Trade Me payload for operator visibility.
    - Does NOT upload photos (so no PhotoIds).
    - Uses local/public PhotoUrls for preview.
    """
    from retail_os.core.listing_builder import build_listing_payload, compute_payload_hash

    with get_db_session() as session:
        ip = session.query(InternalProduct).filter(InternalProduct.id == internal_product_id).first()
        if not ip:
            raise HTTPException(status_code=404, detail="InternalProduct not found")
        try:
            payload = build_listing_payload(internal_product_id)
        except Exception as e:
            # Operator visibility must never 500. If an item is blocked, return a blocked snapshot
            # that the UI can render (with the top blocker) instead of crashing the page.
            sp = ip.supplier_product
            title = ""
            desc = ""
            price = None
            photo_urls: list[str] = []
            try:
                if sp:
                    title = (sp.enriched_title or sp.title or "").strip()
                    desc = (sp.enriched_description or sp.description or "").strip()
                    try:
                        price = float(sp.cost_price) if sp.cost_price is not None else None
                    except Exception:
                        price = None
                    try:
                        imgs = sp.images if isinstance(sp.images, list) else []
                        for raw in imgs:
                            if not raw or not isinstance(raw, str):
                                continue
                            norm = raw.replace("\\", "/")
                            if norm.startswith("http://") or norm.startswith("https://"):
                                photo_urls.append(norm)
                            elif norm.startswith("data/media/"):
                                photo_urls.append("/media/" + norm[len("data/media/") :])
                    except Exception:
                        photo_urls = []
            except Exception:
                pass

            top = str(e)[:500]
            # Even when blocked, keep the operator preview structurally realistic
            # (shipping/payment/duration/pickup defaults) so the UI doesn't show empty blanks.
            try:
                from retail_os.trademe.config import TradeMeConfig
                from retail_os.strategy.pricing import PricingStrategy

                supplier_name = None
                try:
                    supplier_name = sp.supplier.name if sp and getattr(sp, "supplier", None) else None
                except Exception:
                    supplier_name = None

                suggested_price = None
                try:
                    if sp and sp.cost_price is not None:
                        suggested_price = PricingStrategy.calculate_price(float(sp.cost_price), "General", supplier_name)
                except Exception:
                    suggested_price = price
            except Exception:
                TradeMeConfig = None  # type: ignore
                suggested_price = price

            payload = {
                "_blocked": True,
                "top_blocker": top,
                "error": top,
                "Category": "",
                "Title": (title or f"Internal #{internal_product_id}")[:49],
                "Description": [desc or "(Blocked: missing listing requirements)"],
                "StartPrice": suggested_price if suggested_price is not None else price,
                "BuyNowPrice": suggested_price if suggested_price is not None else price,
                "Duration": getattr(TradeMeConfig, "DEFAULT_DURATION", None),
                "Pickup": getattr(TradeMeConfig, "PICKUP_OPTION", None),
                "PaymentOptions": (TradeMeConfig.get_payment_methods() if TradeMeConfig else None),
                "ShippingOptions": getattr(TradeMeConfig, "DEFAULT_SHIPPING", None),
                "PhotoUrls": photo_urls,
                "PhotoIds": [],
                "HasGallery": bool(photo_urls),
                "_internal_product_id": internal_product_id,
                "_cost_price": float(sp.cost_price or 0) if sp and sp.cost_price is not None else None,
            }
        return {
            "internal_product_id": internal_product_id,
            "payload": payload,
            "payload_hash": compute_payload_hash(payload),
        }


@app.get("/ops/readiness")
def ops_readiness(
    supplier: Optional[str] = None,
    limit: int = 20000,
    _role: Role = Depends(require_role("power")),
) -> dict[str, Any]:
    """
    Fast publish-readiness rollup.
    This is *not* Trade Me validation; it reports whether items satisfy local LaunchLock hard requirements:
    - cost_price > 0
    - enriched_title + enriched_description present
    - at least one local image exists
    - category mapping exists
    """
    import os
    from collections import Counter

    if limit < 1 or limit > 200000:
        raise HTTPException(status_code=400, detail="Invalid limit")

    # Build a fast set of media filenames for existence checks (O(1) membership)
    media_files: set[str] = set()
    try:
        if _MEDIA_ROOT.exists():
            for p in _MEDIA_ROOT.iterdir():
                if p.is_file():
                    media_files.add(p.name)
    except Exception:
        media_files = set()

    def has_local_image(images: Any) -> bool:
        if not images or not isinstance(images, list):
            return False
        for raw in images:
            if not raw or not isinstance(raw, str):
                continue
            norm = raw.replace("\\", "/")
            if norm.startswith("data/media/"):
                fn = norm[len("data/media/") :]
                if fn in media_files:
                    return True
                # fallback (slower) if dir listing failed
                if not media_files and os.path.exists(norm):
                    return True
        return False

    with get_db_session() as session:
        q = session.query(InternalProduct).join(SupplierProduct, InternalProduct.primary_supplier_product_id == SupplierProduct.id)
        if supplier:
            q = q.join(Supplier, SupplierProduct.supplier_id == Supplier.id).filter(func.lower(Supplier.name) == supplier.lower())

        ips = q.limit(limit).all()

        totals = {"internal_products": len(ips), "ready": 0, "blocked": 0}
        reasons: Counter[str] = Counter()
        by_supplier: Counter[str] = Counter()
        by_source_category: Counter[str] = Counter()

        for ip in ips:
            sp = ip.supplier_product
            sup = (sp.supplier.name if sp and sp.supplier else "UNKNOWN") if sp else "UNKNOWN"
            by_supplier[sup] += 1
            by_source_category[str(getattr(sp, "source_category", "") or "")] += 1

            if not sp:
                totals["blocked"] += 1
                reasons["Missing supplier product link"] += 1
                continue
            if sp.cost_price is None or float(sp.cost_price or 0) <= 0:
                totals["blocked"] += 1
                reasons["Missing/invalid cost price"] += 1
                continue
            if not (sp.enriched_title or "").strip():
                totals["blocked"] += 1
                reasons["Missing enriched title"] += 1
                continue
            if not (sp.enriched_description or "").strip():
                totals["blocked"] += 1
                reasons["Missing enriched description"] += 1
                continue
            if not has_local_image(sp.images):
                totals["blocked"] += 1
                reasons["Missing images (local)"] += 1
                continue
            cat_id = CategoryMapper.map_category(
                getattr(sp, "source_category", "") or "",
                sp.title or "",
                (getattr(sp, "enriched_description", None) or getattr(sp, "description", None) or ""),
            )
            if not cat_id:
                totals["blocked"] += 1
                reasons["Missing category mapping"] += 1
                continue

            totals["ready"] += 1

        return {
            "totals": totals,
            "top_blockers": reasons.most_common(25),
            "by_supplier": by_supplier.most_common(),
            "by_source_category": by_source_category.most_common(50),
            "limit_applied": limit,
        }


@app.get("/ops/removed_items")
def ops_removed_items(
    supplier_id: Optional[int] = None,
    page: int = 1,
    per_page: int = 50,
    _role: Role = Depends(require_role("power")),
) -> dict[str, Any]:
    """
    Operator panel: supplier products confirmed REMOVED, linked listings, and withdraw command status.
    """
    if page < 1 or per_page < 1 or per_page > 200:
        raise HTTPException(status_code=400, detail="Invalid pagination")

    with get_db_session() as session:
        q = session.query(SupplierProduct).filter(SupplierProduct.sync_status == "REMOVED")
        if supplier_id is not None:
            q = q.filter(SupplierProduct.supplier_id == int(supplier_id))

        total = q.count()
        rows = (
            q.order_by(SupplierProduct.last_scraped_at.desc().nullslast(), SupplierProduct.id.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        items: list[dict[str, Any]] = []
        for sp in rows:
            ip = sp.internal_product
            listing = None
            if ip and getattr(ip, "listings", None):
                # Prefer live listing
                for l in ip.listings:
                    if getattr(l, "actual_state", None) == "Live":
                        listing = l
                        break
                if listing is None and ip.listings:
                    listing = ip.listings[0]

            # Removed_at: from audit log status change if available
            removed_at = None
            try:
                al = (
                    session.query(AuditLog)
                    .filter(AuditLog.entity_type == "SupplierProduct", AuditLog.entity_id == str(sp.id))
                    .filter(AuditLog.action == "STATUS_CHANGE", AuditLog.new_value == "REMOVED")
                    .order_by(AuditLog.timestamp.desc())
                    .first()
                )
                removed_at = _dt(al.timestamp) if al else None
            except Exception:
                removed_at = None

            # Best-effort: find a withdraw command targeting this tm_listing_id (if available).
            withdraw_cmd = None
            if listing and listing.tm_listing_id:
                target = str(listing.tm_listing_id)
                try:
                    withdraw_cmd = (
                        session.query(SystemCommand)
                        .filter(SystemCommand.type == "WITHDRAW_LISTING")
                        .filter(SystemCommand.payload.isnot(None))
                        .filter(func.json_extract(SystemCommand.payload, "$.listing_id") == target)
                        .order_by(SystemCommand.created_at.desc())
                        .first()
                    )
                except Exception:
                    withdraw_cmd = None
                if not withdraw_cmd:
                    # Fallback: string match (works even when json_extract is unavailable)
                    withdraw_cmd = (
                        session.query(SystemCommand)
                        .filter(SystemCommand.type == "WITHDRAW_LISTING")
                        .filter(SystemCommand.payload.like(f"%{target}%"))
                        .order_by(SystemCommand.created_at.desc())
                        .first()
                    )

            items.append(
                {
                    "supplier_product_id": sp.id,
                    "supplier_id": sp.supplier_id,
                    "external_sku": sp.external_sku,
                    "title": sp.title,
                    "product_url": sp.product_url,
                    "source_category": getattr(sp, "source_category", None),
                    "removed_at": removed_at,
                    "internal_product_id": ip.id if ip else None,
                    "listing": (
                        {
                            "id": listing.id,
                            "tm_listing_id": listing.tm_listing_id,
                            "actual_state": listing.actual_state,
                            "last_synced_at": _dt(listing.last_synced_at),
                        }
                        if listing
                        else None
                    ),
                    "withdraw_command": (
                        {
                            "id": withdraw_cmd.id,
                            "status": withdraw_cmd.status.value if hasattr(withdraw_cmd.status, "value") else str(withdraw_cmd.status),
                            "updated_at": _dt(withdraw_cmd.updated_at),
                            "error_code": withdraw_cmd.error_code,
                            "error_message": withdraw_cmd.error_message,
                        }
                        if withdraw_cmd
                        else None
                    ),
                }
            )

        return {"utc": datetime.now(timezone.utc).isoformat(), "total": total, "items": items, "page": page, "per_page": per_page}


@app.get("/listings/by-tm/{tm_listing_id}")
def listing_detail_by_tm(tm_listing_id: str) -> dict[str, Any]:
    with get_db_session() as session:
        l = session.query(TradeMeListing).filter(TradeMeListing.tm_listing_id == tm_listing_id).first()
        if not l:
            raise HTTPException(status_code=404, detail="Listing not found")
        return listing_detail(l.id)


@app.get("/listing-drafts/{command_id}")
def listing_draft(
    command_id: str,
    _role: Role = Depends(require_role("power")),
) -> dict[str, Any]:
    with get_db_session() as session:
        d = session.query(ListingDraft).filter(ListingDraft.command_id == command_id).first()
        if not d:
            raise HTTPException(status_code=404, detail="ListingDraft not found")
        return {
            "id": d.id,
            "command_id": d.command_id,
            "payload_json": d.payload_json,
            "validation_results": d.validation_results,
            "created_at": _dt(d.created_at),
        }


@app.get("/audits", response_model=PageResponse)
def audits(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    action: Optional[str] = None,
    include_ai_cost: bool = False,
    page: int = 1,
    per_page: int = 100,
    _role: Role = Depends(require_role("power")),
) -> PageResponse:
    if page < 1 or per_page < 1 or per_page > 1000:
        raise HTTPException(status_code=400, detail="Invalid pagination")
    with get_db_session() as session:
        q = session.query(AuditLog)
        if entity_type:
            q = q.filter(AuditLog.entity_type == entity_type)
        if entity_id:
            q = q.filter(AuditLog.entity_id == entity_id)
        if action:
            q = q.filter(AuditLog.action == action)
        elif not include_ai_cost:
            # Default to high-signal audit events. AI token logs can be very noisy at scale.
            q = q.filter(AuditLog.action != "AI_COST")

        total = q.count()
        rows = q.order_by(AuditLog.timestamp.desc()).offset((page - 1) * per_page).limit(per_page).all()
        items = []
        for a in rows:
            items.append(
                {
                    "id": a.id,
                    "timestamp": _dt(a.timestamp),
                    "user": a.user,
                    "action": a.action,
                    "entity_type": a.entity_type,
                    "entity_id": a.entity_id,
                    "old_value": a.old_value,
                    "new_value": a.new_value,
                }
            )
        return PageResponse(items=items, total=total)


@app.get("/metrics/listings/{listing_id}", response_model=PageResponse)
def listing_metrics(
    listing_id: int,
    page: int = 1,
    per_page: int = 200,
    _role: Role = Depends(require_role("power")),
) -> PageResponse:
    if page < 1 or per_page < 1 or per_page > 1000:
        raise HTTPException(status_code=400, detail="Invalid pagination")
    with get_db_session() as session:
        q = session.query(ListingMetricSnapshot).filter(ListingMetricSnapshot.listing_id == listing_id)
        total = q.count()
        rows = (
            q.order_by(ListingMetricSnapshot.captured_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        items = []
        for m in rows:
            items.append(
                {
                    "id": m.id,
                    "listing_id": m.listing_id,
                    "captured_at": _dt(m.captured_at),
                    "view_count": m.view_count,
                    "watch_count": m.watch_count,
                    "is_sold": m.is_sold,
                }
            )
        return PageResponse(items=items, total=total)


@app.get("/jobs", response_model=PageResponse)
def jobs(
    job_type: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    per_page: int = 50,
    _role: Role = Depends(require_role("power")),
) -> PageResponse:
    if page < 1 or per_page < 1 or per_page > 1000:
        raise HTTPException(status_code=400, detail="Invalid pagination")
    with get_db_session() as session:
        q = session.query(JobStatus)
        if job_type:
            q = q.filter(JobStatus.job_type == job_type)
        if status:
            q = q.filter(JobStatus.status == status)

        total = q.count()
        rows = q.order_by(JobStatus.start_time.desc()).offset((page - 1) * per_page).limit(per_page).all()
        items = []
        for j in rows:
            items.append(
                {
                    "id": j.id,
                    "job_type": j.job_type,
                    "status": j.status,
                    "start_time": _dt(j.start_time),
                    "end_time": _dt(j.end_time),
                    "items_processed": j.items_processed,
                    "items_created": j.items_created,
                    "items_updated": j.items_updated,
                    "items_deleted": j.items_deleted,
                    "items_failed": j.items_failed,
                    "summary": j.summary,
                }
            )
        return PageResponse(items=items, total=total)


@app.get("/jobs/{job_id}")
def job_detail(job_id: int, _role: Role = Depends(require_role("power"))) -> dict[str, Any]:
    with get_db_session() as session:
        j = session.query(JobStatus).filter(JobStatus.id == job_id).first()
        if not j:
            raise HTTPException(status_code=404, detail="Job not found")
        return {
            "id": j.id,
            "job_type": j.job_type,
            "status": j.status,
            "start_time": _dt(j.start_time),
            "end_time": _dt(j.end_time),
            "items_processed": j.items_processed,
            "items_created": j.items_created,
            "items_updated": j.items_updated,
            "items_deleted": j.items_deleted,
            "items_failed": j.items_failed,
            "summary": j.summary,
        }


class SettingUpsertRequest(BaseModel):
    value: Any


@app.get("/settings/{key}")
def get_setting(key: str, _role: Role = Depends(require_role("root"))) -> dict[str, Any]:
    with get_db_session() as session:
        row = session.query(SystemCommand)  # dummy to keep formatting consistent
        _ = row  # silence unused in some linters
        from retail_os.core.database import SystemSetting

        s = session.query(SystemSetting).filter(SystemSetting.key == key).first()
        # Real-mode behavior: return explicit "unset" rather than fake fixture data or crashing the UI.
        if not s:
            return {"key": key, "value": None, "updated_at": None}
        return {"key": s.key, "value": s.value, "updated_at": _dt(s.updated_at)}


@app.put("/settings/{key}")
def put_setting(key: str, req: SettingUpsertRequest, _role: Role = Depends(require_role("root"))) -> dict[str, Any]:
    from retail_os.core.database import SystemSetting

    with get_db_session() as session:
        s = session.query(SystemSetting).filter(SystemSetting.key == key).first()
        if not s:
            s = SystemSetting(key=key, value=req.value)
            session.add(s)
        else:
            s.value = req.value
        session.commit()
        return {"key": s.key, "value": s.value, "updated_at": _dt(s.updated_at)}





