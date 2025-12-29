from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, text

from retail_os.core.database import (
    AuditLog,
    CommandLog,
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


app = FastAPI(title="RetailOS API", version="0.1.0")

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


@app.on_event("startup")
def _startup_init_db() -> None:
    """
    Ensure DB schema exists on fresh machines (especially local Windows dev).
    Without this, list endpoints (e.g. /vaults/raw) can 500 if tables don't exist yet.
    """
    try:
        from retail_os.core.database import init_db

        init_db()
    except Exception as e:
        # Don't crash the API process; surface errors through endpoints/logs instead.
        print(f"API startup: init_db failed: {e}")

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
    db: str | None = None
    db_error: str | None = None


Role = str


ROLE_RANK: dict[Role, int] = {
    "listing": 10,
    "fulfillment": 20,
    "power": 80,
    "root": 100,
}


def _role_rank(role: Optional[str]) -> int:
    if not role:
        return 0
    return ROLE_RANK.get(role.strip().lower(), 0)


def get_request_role(request: Request) -> Role:
    """
    Minimal RBAC without interactive login (by design for now).
    - Set `X-RetailOS-Role` header from the web app (cookie-backed).
    - If a token is configured, it overrides the claimed role (identity-based).
      This fixes "can't go back to root" by making the token authoritative.
    """
    claimed_role = (request.headers.get("X-RetailOS-Role") or os.getenv("RETAIL_OS_DEFAULT_ROLE") or "root").lower()
    supplied = request.headers.get("X-RetailOS-Token")

    # Token-based identity overrides role claims.
    # Configure per-role tokens via env vars.
    token_map: dict[str, str | None] = {
        "root": os.getenv("RETAIL_OS_ROOT_TOKEN"),
        "power": os.getenv("RETAIL_OS_POWER_TOKEN"),
        "fulfillment": os.getenv("RETAIL_OS_FULFILLMENT_TOKEN"),
        "listing": os.getenv("RETAIL_OS_LISTING_TOKEN"),
    }
    if supplied:
        for r, t in token_map.items():
            if t and supplied == t:
                return r

    # Backwards compatibility: if root token is configured, do not allow claiming root without it.
    if token_map.get("root") and claimed_role == "root":
        return "power"

    if claimed_role not in ROLE_RANK:
        return "listing"
    return claimed_role


def require_role(min_role: Role):
    def _dep(role: Role = Depends(get_request_role)) -> Role:
        if _role_rank(role) < _role_rank(min_role):
            raise HTTPException(status_code=403, detail=f"Forbidden (requires {min_role})")
        return role

    return _dep


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    # Include DB probe so local env issues are obvious.
    try:
        with get_db_session() as session:
            session.execute(text("SELECT 1"))
        return HealthResponse(status="ok", utc=datetime.utcnow(), db="ok", db_error=None)
    except Exception as e:
        return HealthResponse(status="degraded", utc=datetime.utcnow(), db="error", db_error=str(e)[:200])


@app.get("/media/{rel_path:path}")
def media(rel_path: str) -> FileResponse:
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
    return {"role": role, "rank": _role_rank(role)}


@app.get("/ops/inbox")
def ops_inbox(_role: Role = Depends(require_role("power"))) -> dict[str, Any]:
    """
    Operator Inbox: everything needing attention without checking external systems.
    """
    try:
        with get_db_session() as session:
            # True counts (not capped by UI sample limits).
            human_total = (
                session.query(func.count(SystemCommand.id)).filter(SystemCommand.status == CommandStatus.HUMAN_REQUIRED).scalar()
                or 0
            )
            retry_total = (
                session.query(func.count(SystemCommand.id))
                .filter(SystemCommand.status.in_([CommandStatus.FAILED_RETRYABLE, CommandStatus.EXECUTING]))
                .scalar()
                or 0
            )
            failed_jobs_total = (
                session.query(func.count(JobStatus.id)).filter(JobStatus.status == "FAILED").scalar() or 0
            )
            pending_orders_total = (
                session.query(func.count(Order.id)).filter(Order.fulfillment_status == "PENDING").scalar() or 0
            )

            # Grouped rollups so the inbox stays usable at scale.
            # (Link from UI to Commands filtered by `type` + `status`.)
            human_groups_raw = (
                session.query(
                    SystemCommand.type.label("type"),
                    func.coalesce(SystemCommand.error_code, "NONE").label("error_code"),
                    func.count(SystemCommand.id).label("count"),
                    func.max(SystemCommand.updated_at).label("latest_updated_at"),
                )
                .filter(SystemCommand.status == CommandStatus.HUMAN_REQUIRED)
                .group_by(SystemCommand.type, func.coalesce(SystemCommand.error_code, "NONE"))
                .order_by(func.count(SystemCommand.id).desc(), func.max(SystemCommand.updated_at).desc())
                .limit(25)
                .all()
            )
            retry_groups_raw = (
                session.query(
                    SystemCommand.type.label("type"),
                    SystemCommand.status.label("status"),
                    func.count(SystemCommand.id).label("count"),
                    func.max(SystemCommand.updated_at).label("latest_updated_at"),
                )
                .filter(SystemCommand.status.in_([CommandStatus.FAILED_RETRYABLE, CommandStatus.EXECUTING]))
                .group_by(SystemCommand.type, SystemCommand.status)
                .order_by(func.count(SystemCommand.id).desc(), func.max(SystemCommand.updated_at).desc())
                .limit(25)
                .all()
            )

            human_cmds = (
                session.query(SystemCommand)
                .filter(SystemCommand.status == CommandStatus.HUMAN_REQUIRED)
                .order_by(SystemCommand.updated_at.desc())
                .limit(60)
                .all()
            )
            retry_cmds = (
                session.query(SystemCommand)
                .filter(SystemCommand.status.in_([CommandStatus.FAILED_RETRYABLE, CommandStatus.EXECUTING]))
                .order_by(SystemCommand.updated_at.desc())
                .limit(60)
                .all()
            )
            failed_jobs = (
                session.query(JobStatus).filter(JobStatus.status == "FAILED").order_by(JobStatus.start_time.desc()).limit(100).all()
            )
            pending_orders = (
                session.query(Order).filter(Order.fulfillment_status == "PENDING").order_by(Order.created_at.desc()).limit(200).all()
            )

            return {
                "counts": {
                    "commands_human_required": human_total,
                    "commands_retrying": retry_total,
                    "jobs_failed": failed_jobs_total,
                    "orders_pending": pending_orders_total,
                },
                "groups_human_required": [
                    {
                        "type": str(g.type),
                        "error_code": str(g.error_code) if g.error_code is not None else "NONE",
                        "count": int(g.count) if g.count is not None else 0,
                        "latest_updated_at": _dt(g.latest_updated_at),
                    }
                    for g in human_groups_raw
                ],
                "groups_retrying": [
                    {
                        "type": str(g.type),
                        "status": g.status.value if hasattr(g.status, "value") else str(g.status),
                        "count": int(g.count) if g.count is not None else 0,
                        "latest_updated_at": _dt(g.latest_updated_at),
                    }
                    for g in retry_groups_raw
                ],
                "commands_human_required": [
                    {
                        "id": c.id,
                        "type": c.type,
                        "status": c.status.value if hasattr(c.status, "value") else str(c.status),
                        "error_code": c.error_code,
                        "error_message": c.error_message,
                        "last_error": c.last_error,
                        "updated_at": _dt(c.updated_at),
                    }
                    for c in human_cmds
                ],
                "jobs_failed": [
                    {
                        "id": j.id,
                        "job_type": j.job_type,
                        "status": j.status,
                        "start_time": _dt(j.start_time),
                        "end_time": _dt(j.end_time),
                        "summary": j.summary,
                    }
                    for j in failed_jobs
                ],
                "commands_retrying": [
                    {
                        "id": c.id,
                        "type": c.type,
                        "status": c.status.value if hasattr(c.status, "value") else str(c.status),
                        "attempts": c.attempts,
                        "max_attempts": c.max_attempts,
                        "last_error": c.last_error,
                        "updated_at": _dt(c.updated_at),
                    }
                    for c in retry_cmds
                ],
                "orders_pending": [
                    {
                        "id": o.id,
                        "tm_order_ref": o.tm_order_ref,
                        "buyer_name": o.buyer_name,
                        "sold_price": float(o.sold_price) if o.sold_price is not None else None,
                        "created_at": _dt(o.created_at),
                    }
                    for o in pending_orders
                ],
            }
    except Exception as e:
        # Keep UI functional even if the DB is mid-migration or the API is restarting.
        return {
            "offline": True,
            "error": str(e)[:300],
            "counts": {"commands_human_required": 0, "commands_retrying": 0, "jobs_failed": 0, "orders_pending": 0},
            "groups_human_required": [],
            "groups_retrying": [],
            "commands_human_required": [],
            "commands_retrying": [],
            "jobs_failed": [],
            "orders_pending": [],
        }


@app.get("/ops/summary")
def ops_summary(_role: Role = Depends(require_role("power"))) -> dict[str, Any]:
    """
    High-signal operational rollup for the Ops Workbench.
    Prevents needing to dig through Commands/Audits for day-to-day operation.
    """
    with get_db_session() as session:
        cmd_total = session.query(func.count(SystemCommand.id)).scalar() or 0
        cmd_pending = session.query(func.count(SystemCommand.id)).filter(SystemCommand.status == CommandStatus.PENDING).scalar() or 0
        cmd_executing = (
            session.query(func.count(SystemCommand.id)).filter(SystemCommand.status == CommandStatus.EXECUTING).scalar() or 0
        )
        cmd_human = (
            session.query(func.count(SystemCommand.id)).filter(SystemCommand.status == CommandStatus.HUMAN_REQUIRED).scalar() or 0
        )
        cmd_failed = (
            session.query(func.count(SystemCommand.id))
            .filter(SystemCommand.status.in_([CommandStatus.FAILED_RETRYABLE, CommandStatus.FAILED_FATAL]))
            .scalar()
            or 0
        )

        raw_total = session.query(func.count(SupplierProduct.id)).scalar() or 0
        raw_present = session.query(func.count(SupplierProduct.id)).filter(SupplierProduct.sync_status == "PRESENT").scalar() or 0

        enriched_total = session.query(func.count(InternalProduct.id)).scalar() or 0
        enriched_ready = (
            session.query(func.count(InternalProduct.id))
            .join(SupplierProduct, InternalProduct.primary_supplier_product_id == SupplierProduct.id)
            .filter(SupplierProduct.enriched_description.isnot(None))
            .scalar()
            or 0
        )

        listings_total = session.query(func.count(TradeMeListing.id)).scalar() or 0
        listings_dry = session.query(func.count(TradeMeListing.id)).filter(TradeMeListing.actual_state == "DRY_RUN").scalar() or 0
        listings_live = session.query(func.count(TradeMeListing.id)).filter(TradeMeListing.actual_state == "Live").scalar() or 0

        orders_total = session.query(func.count(Order.id)).scalar() or 0
        orders_pending = session.query(func.count(Order.id)).filter(Order.fulfillment_status == "PENDING").scalar() or 0

        return {
            "commands": {
                "total": cmd_total,
                "pending": cmd_pending,
                "executing": cmd_executing,
                "human_required": cmd_human,
                "failed": cmd_failed,
            },
            "vaults": {
                "raw_total": raw_total,
                "raw_present": raw_present,
                "enriched_total": enriched_total,
                "enriched_ready": enriched_ready,
                "listings_total": listings_total,
                "listings_dry_run": listings_dry,
                "listings_live": listings_live,
            },
            "orders": {"total": orders_total, "pending_fulfillment": orders_pending},
        }


@app.get("/trademe/account_summary")
def trademe_account_summary(_role: Role = Depends(require_role("power"))) -> dict[str, Any]:
    """
    Trade Me account health for ops decisions (balance, reputation signals).
    """
    try:
        api = TradeMeAPI()
        return api.get_account_summary()
    except Exception as e:
        # Keep ops UI functional even when credentials are not configured in this environment.
        return {"offline": True, "error": str(e)[:200]}


@app.get("/ops/alerts")
def ops_alerts(_role: Role = Depends(require_role("power"))) -> dict[str, Any]:
    """
    Lightweight alert surface (computed from DB + optional Trade Me health).
    This avoids introducing a new alerts table while still making issues visible.
    """
    alerts: list[dict[str, Any]] = []

    # 1) DB-backed alerts
    with get_db_session() as session:
        human_count = session.query(SystemCommand).filter(SystemCommand.status == CommandStatus.HUMAN_REQUIRED).count()
        if human_count:
            alerts.append(
                {
                    "severity": "high",
                    "code": "COMMANDS_HUMAN_REQUIRED",
                    "title": "Commands need human attention",
                    "detail": f"{human_count} commands are HUMAN_REQUIRED",
                }
            )

        failed_jobs = session.query(JobStatus).filter(JobStatus.status == "FAILED").count()
        if failed_jobs:
            alerts.append(
                {
                    "severity": "high",
                    "code": "JOBS_FAILED",
                    "title": "Jobs failed",
                    "detail": f"{failed_jobs} jobs are FAILED",
                }
            )

        pending_orders = session.query(Order).filter(Order.fulfillment_status == "PENDING").count()
        if pending_orders:
            alerts.append(
                {
                    "severity": "medium",
                    "code": "ORDERS_PENDING",
                    "title": "Pending fulfillment",
                    "detail": f"{pending_orders} orders pending fulfillment",
                }
            )

        # Supplier removals that still appear live on marketplace (withdraw should be queued)
        try:
            removed_live = (
                session.query(SupplierProduct)
                .join(InternalProduct, InternalProduct.primary_supplier_product_id == SupplierProduct.id)
                .join(TradeMeListing, TradeMeListing.internal_product_id == InternalProduct.id)
                .filter(SupplierProduct.sync_status == "REMOVED")
                .filter(TradeMeListing.actual_state == "Live")
                .count()
            )
            if removed_live:
                alerts.append(
                    {
                        "severity": "high",
                        "code": "REMOVED_ITEMS_STILL_LIVE",
                        "title": "Removed supplier items still live",
                        "detail": f"{removed_live} supplier-REMOVED items are still Live on Trade Me (withdraw should run)",
                    }
                )
        except Exception:
            pass

    # 2) Trade Me balance alert (best-effort)
    try:
        api = TradeMeAPI()
        summary = api.get_account_summary()
        balance = float(summary.get("account_balance") or 0.0)

        # Default threshold can be overridden by setting: ops.balance_min
        min_balance = float(os.getenv("RETAIL_OS_MIN_BALANCE") or 20.0)
        if balance < min_balance:
            alerts.append(
                {
                    "severity": "high",
                    "code": "LOW_BALANCE",
                    "title": "Trade Me account balance low",
                    "detail": f"Balance ${balance:.2f} is below ${min_balance:.2f}",
                }
            )
    except Exception as e:
        alerts.append(
            {
                "severity": "medium",
                "code": "TRADEME_HEALTH_UNAVAILABLE",
                "title": "Trade Me health unavailable",
                "detail": str(e)[:200],
            }
        )

    return {"alerts": alerts, "count": len(alerts)}


class EnqueueRequest(BaseModel):
    type: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: int = 50


class CommandCreateResponse(BaseModel):
    id: str
    status: str


@app.post("/ops/enqueue", response_model=CommandCreateResponse)
def ops_enqueue(req: EnqueueRequest, _role: Role = Depends(require_role("power"))) -> CommandCreateResponse:
    """
    Power-user enqueue endpoint for bulk operations (scrape/enrich/sync).
    """
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


class BulkDryRunPublishRequest(BaseModel):
    supplier_id: Optional[int] = None
    source_category: Optional[str] = None
    limit: int = 50
    priority: int = 60


@app.post("/ops/bulk/dryrun_publish", response_model=dict[str, Any])
def bulk_dryrun_publish(req: BulkDryRunPublishRequest, _role: Role = Depends(require_role("power"))) -> dict[str, Any]:
    """
    Creates PUBLISH_LISTING commands in DRY RUN mode for review at scale.
    Safe defaults:
    - skips products already Live
    - skips products already DRY_RUN
    - skips products that already have a pending PUBLISH_LISTING command
    """
    if req.limit < 1 or req.limit > 1000:
        raise HTTPException(status_code=400, detail="Invalid limit")

    import uuid

    with get_db_session() as session:
        q = session.query(InternalProduct).join(SupplierProduct, InternalProduct.primary_supplier_product_id == SupplierProduct.id)
        if req.supplier_id is not None:
            q = q.filter(SupplierProduct.supplier_id == int(req.supplier_id))
        if req.source_category:
            q = q.filter(SupplierProduct.source_category == req.source_category)

        # Skip anything already Live or DRY_RUN
        q = q.outerjoin(TradeMeListing, TradeMeListing.internal_product_id == InternalProduct.id).filter(
            (TradeMeListing.id.is_(None)) | (~TradeMeListing.actual_state.in_(["Live", "DRY_RUN"]))
        )

        # newest-ish first
        q = q.order_by(SupplierProduct.last_scraped_at.desc())

        candidates = q.limit(int(req.limit)).all()

        enqueued = 0
        skipped_existing_cmd = 0
        skipped_already_listed = 0

        for ip in candidates:
            # Defensive: double-check listings
            already = False
            for l in (ip.listings or []):
                if l.actual_state in ["Live", "DRY_RUN"]:
                    already = True
                    break
            if already:
                skipped_already_listed += 1
                continue

            # Skip if a PUBLISH_LISTING is already pending for this internal product
            existing_cmd = None
            for c in (
                session.query(SystemCommand)
                .filter(SystemCommand.type == "PUBLISH_LISTING")
                .filter(SystemCommand.status.in_([CommandStatus.PENDING, CommandStatus.EXECUTING, CommandStatus.FAILED_RETRYABLE]))
                .order_by(SystemCommand.created_at.desc())
                .limit(500)
                .all()
            ):
                try:
                    if (c.payload or {}).get("internal_product_id") == ip.id:
                        existing_cmd = c
                        break
                except Exception:
                    continue
            if existing_cmd:
                skipped_existing_cmd += 1
                continue

            session.add(
                SystemCommand(
                    id=str(uuid.uuid4()),
                    type="PUBLISH_LISTING",
                    payload={"internal_product_id": ip.id, "dry_run": True},
                    status=CommandStatus.PENDING,
                    priority=int(req.priority),
                )
            )
            enqueued += 1

        session.commit()
        return {
            "enqueued": enqueued,
            "skipped_existing_cmd": skipped_existing_cmd,
            "skipped_already_listed": skipped_already_listed,
            "requested_limit": req.limit,
        }


class BulkApprovePublishRequest(BaseModel):
    supplier_id: Optional[int] = None
    source_category: Optional[str] = None
    limit: int = 50
    priority: int = 60


@app.post("/ops/bulk/approve_publish", response_model=dict[str, Any])
def bulk_approve_publish(req: BulkApprovePublishRequest, _role: Role = Depends(require_role("power"))) -> dict[str, Any]:
    """
    Turns reviewed DRY_RUN items into real PUBLISH_LISTING commands, with a strict drift check:
    - the SupplierProduct.snapshot_hash must match the snapshot captured at DRY_RUN generation time.

    Safety:
    - disabled when store.mode is HOLIDAY or PAUSED (publishing costs money)
    - skips if a real publish command is already pending
    """
    if req.limit < 1 or req.limit > 2000:
        raise HTTPException(status_code=400, detail="Invalid limit")

    import uuid
    from retail_os.core.database import SystemSetting

    with get_db_session() as session:
        store_mode = "NORMAL"
        s = session.query(SystemSetting).filter(SystemSetting.key == "store.mode").first()
        if s and isinstance(s.value, str) and s.value.strip():
            store_mode = s.value.strip().upper()
        if store_mode in ["HOLIDAY", "PAUSED"]:
            raise HTTPException(status_code=409, detail=f"Publishing disabled in store.mode={store_mode}")

        # Enforce publishing policy quotas to avoid runaway spend
        pub = session.query(SystemSetting).filter(SystemSetting.key == "publishing.policy").first()
        pub_cfg: dict[str, Any] = pub.value if pub and isinstance(pub.value, dict) else {}
        max_per_day = int(pub_cfg.get("max_publishes_per_day") or 0)
        if max_per_day:
            from datetime import date

            today = date.today()
            rows_today = (
                session.query(SystemCommand)
                .filter(SystemCommand.type == "PUBLISH_LISTING")
                .filter(SystemCommand.status == CommandStatus.SUCCEEDED)
                .filter(SystemCommand.updated_at.isnot(None))
                .all()
            )
            published_today = 0
            for c in rows_today:
                try:
                    if c.updated_at and c.updated_at.date() == today and not bool((c.payload or {}).get("dry_run", False)):
                        published_today += 1
                except Exception:
                    continue
            remaining = max(0, max_per_day - published_today)
            if remaining <= 0:
                raise HTTPException(status_code=409, detail=f"Daily publish quota reached ({published_today}/{max_per_day})")
            # Hard cap this enqueue to remaining quota
            req.limit = min(int(req.limit), int(remaining))

        q = session.query(TradeMeListing).join(InternalProduct).join(SupplierProduct)
        q = q.filter(TradeMeListing.actual_state == "DRY_RUN")
        if req.supplier_id is not None:
            q = q.filter(SupplierProduct.supplier_id == int(req.supplier_id))
        if req.source_category:
            q = q.filter(SupplierProduct.source_category == req.source_category)
        q = q.order_by(TradeMeListing.last_synced_at.desc().nullslast())

        rows = q.limit(int(req.limit)).all()

        enqueued = 0
        skipped_existing_cmd = 0
        skipped_drift = 0
        skipped_missing_metadata = 0
        skipped_bad_dryrun_id = 0

        for l in rows:
            tm_id = str(l.tm_listing_id or "")
            if not tm_id.startswith("DRYRUN-"):
                skipped_bad_dryrun_id += 1
                continue

            dryrun_cmd_id = tm_id.replace("DRYRUN-", "", 1)
            dryrun_cmd = session.query(SystemCommand).filter(SystemCommand.id == dryrun_cmd_id).first()
            if not dryrun_cmd:
                skipped_missing_metadata += 1
                continue

            snap = None
            try:
                snap = (dryrun_cmd.payload or {}).get("supplier_snapshot_hash")
            except Exception:
                snap = None
            if not snap:
                skipped_missing_metadata += 1
                continue

            # Drift check: refuse to publish if supplier truth changed since DRY_RUN
            try:
                current_snap = l.internal_product.supplier_product.snapshot_hash  # type: ignore[union-attr]
            except Exception:
                current_snap = None
            if not current_snap or str(current_snap) != str(snap):
                skipped_drift += 1
                continue

            # Skip if a real publish is already pending for this internal product
            existing_cmd = None
            for c in (
                session.query(SystemCommand)
                .filter(SystemCommand.type == "PUBLISH_LISTING")
                .filter(SystemCommand.status.in_([CommandStatus.PENDING, CommandStatus.EXECUTING, CommandStatus.FAILED_RETRYABLE]))
                .order_by(SystemCommand.created_at.desc())
                .limit(500)
                .all()
            ):
                try:
                    p = c.payload or {}
                    if p.get("internal_product_id") == l.internal_product_id and not bool(p.get("dry_run", False)):
                        existing_cmd = c
                        break
                except Exception:
                    continue
            if existing_cmd:
                skipped_existing_cmd += 1
                continue

            session.add(
                SystemCommand(
                    id=str(uuid.uuid4()),
                    type="PUBLISH_LISTING",
                    payload={
                        "internal_product_id": l.internal_product_id,
                        "dry_run": False,
                        "approved_from_dryrun": dryrun_cmd_id,
                        "approved_at": datetime.utcnow().isoformat(),
                    },
                    status=CommandStatus.PENDING,
                    priority=int(req.priority),
                )
            )
            enqueued += 1

        session.commit()
        return {
            "enqueued": enqueued,
            "skipped_existing_cmd": skipped_existing_cmd,
            "skipped_drift": skipped_drift,
            "skipped_missing_metadata": skipped_missing_metadata,
            "skipped_bad_dryrun_id": skipped_bad_dryrun_id,
            "requested_limit": req.limit,
            "store_mode": store_mode,
            "quota_max_per_day": int(pub_cfg.get("max_publishes_per_day") or 0),
        }


class BulkResetEnrichmentRequest(BaseModel):
    supplier_id: Optional[int] = None
    source_category: Optional[str] = None
    limit: int = 200
    priority: int = 60


@app.post("/ops/bulk/reset_enrichment", response_model=dict[str, Any])
def bulk_reset_enrichment(req: BulkResetEnrichmentRequest, _role: Role = Depends(require_role("power"))) -> dict[str, Any]:
    """
    Enqueues RESET_ENRICHMENT commands for supplier products in scope.
    Uses a hard limit to prevent queue explosions.
    """
    if req.limit < 1 or req.limit > 2000:
        raise HTTPException(status_code=400, detail="Invalid limit")

    import uuid

    with get_db_session() as session:
        q = session.query(SupplierProduct)
        if req.supplier_id is not None:
            q = q.filter(SupplierProduct.supplier_id == int(req.supplier_id))
        if req.source_category:
            q = q.filter(SupplierProduct.source_category == req.source_category)

        # Only reset those that were attempted previously
        q = q.filter(SupplierProduct.enrichment_status.in_(["FAILED", "SUCCESS"]))
        q = q.order_by(SupplierProduct.last_scraped_at.desc())

        rows = q.limit(int(req.limit)).all()
        enqueued = 0

        for sp in rows:
            session.add(
                SystemCommand(
                    id=str(uuid.uuid4()),
                    type="RESET_ENRICHMENT",
                    payload={"supplier_product_id": sp.id},
                    status=CommandStatus.PENDING,
                    priority=int(req.priority),
                )
            )
            enqueued += 1

        session.commit()
        return {"enqueued": enqueued, "requested_limit": req.limit}


class BulkScanCompetitorsRequest(BaseModel):
    supplier_id: Optional[int] = None
    source_category: Optional[str] = None
    status: str = "Live"  # Live | DRY_RUN
    limit: int = 100
    priority: int = 40


@app.post("/ops/bulk/scan_competitors", response_model=dict[str, Any])
def bulk_scan_competitors(req: BulkScanCompetitorsRequest, _role: Role = Depends(require_role("power"))) -> dict[str, Any]:
    """
    Enqueues SCAN_COMPETITORS commands for listings in scope.
    """
    if req.limit < 1 or req.limit > 2000:
        raise HTTPException(status_code=400, detail="Invalid limit")

    import uuid

    with get_db_session() as session:
        q = session.query(TradeMeListing).join(InternalProduct).join(SupplierProduct)
        if req.supplier_id is not None:
            q = q.filter(SupplierProduct.supplier_id == int(req.supplier_id))
        if req.source_category:
            q = q.filter(SupplierProduct.source_category == req.source_category)
        if req.status:
            q = q.filter(TradeMeListing.actual_state == req.status)

        q = q.order_by(TradeMeListing.last_synced_at.desc().nullslast())
        rows = q.limit(int(req.limit)).all()

        enqueued = 0
        for l in rows:
            session.add(
                SystemCommand(
                    id=str(uuid.uuid4()),
                    type="SCAN_COMPETITORS",
                    payload={"listing_db_id": l.id, "tm_listing_id": l.tm_listing_id, "internal_product_id": l.internal_product_id},
                    status=CommandStatus.PENDING,
                    priority=int(req.priority),
                )
            )
            enqueued += 1

        session.commit()
        return {"enqueued": enqueued, "requested_limit": req.limit}


class PageResponse(BaseModel):
    items: list[dict[str, Any]]
    total: int


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
        "collection_rank": sp.collection_rank,
        "collection_page": sp.collection_page,
    }


def _serialize_internal_product(ip: InternalProduct) -> dict[str, Any]:
    sp = ip.supplier_product
    return {
        "id": ip.id,
        "sku": ip.sku,
        "title": ip.title,
        "primary_supplier_product_id": ip.primary_supplier_product_id,
        "supplier_product": _serialize_supplier_product(sp) if sp else None,
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


@app.get("/vaults/raw", response_model=PageResponse)
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
                    "product_url": sp.product_url,
                    "images": _public_image_urls(sp.images or []),
                    "specs": sp.specs or {},
                    "last_scraped_at": _dt(sp.last_scraped_at),
                    "enrichment_status": sp.enrichment_status,
                    "enriched_title": sp.enriched_title,
                }
            )

        return PageResponse(items=items, total=total)


@app.get("/vaults/enriched", response_model=PageResponse)
def vault_enriched(
    q: Optional[str] = None,
    supplier_id: Optional[int] = None,
    source_category: Optional[str] = None,
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
                    "images": _public_image_urls((sp.images if sp else None) or []),
                    "source_category": getattr(sp, "source_category", None) if sp else None,
                    "product_url": sp.product_url if sp else None,
                    "sync_status": sp.sync_status if sp else None,
                    "enrichment_status": sp.enrichment_status if sp else None,
                }
            )

        return PageResponse(items=items, total=total)


@app.get("/vaults/live", response_model=PageResponse)
def vault_live(
    q: Optional[str] = None,
    status: str = "All",  # All | Live | Withdrawn | DRY_RUN
    supplier_id: Optional[int] = None,
    source_category: Optional[str] = None,
    page: int = 1,
    per_page: int = 50,
) -> PageResponse:
    if page < 1 or per_page < 1 or per_page > 1000:
        raise HTTPException(status_code=400, detail="Invalid pagination")

    with get_db_session() as session:
        # Always join to display listing context (title/thumb/category) without needing extra clicks.
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
        c.updated_at = datetime.utcnow()
        session.commit()
        return CommandActionResponse(id=c.id, status=c.status.value if hasattr(c.status, "value") else str(c.status))


@app.post("/commands/{command_id}/cancel", response_model=CommandActionResponse)
def cancel_command(command_id: str, _role: Role = Depends(require_role("power"))) -> CommandActionResponse:
    with get_db_session() as session:
        c = session.query(SystemCommand).filter(SystemCommand.id == command_id).first()
        if not c:
            raise HTTPException(status_code=404, detail="Command not found")
        c.status = CommandStatus.CANCELLED
        c.updated_at = datetime.utcnow()
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
            # Run full gates, but still bypass "trust score must be >=95" in test_mode.
            LaunchLock(session).validate_publish(ip, test_mode=True)
            return {"internal_product_id": ip.id, "ok": True, "reason": None}
        except Exception as e:
            return {"internal_product_id": ip.id, "ok": False, "reason": str(e)[:2000]}


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

