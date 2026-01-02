from datetime import datetime, date
from typing import Any, Optional
from collections import Counter
import uuid
import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, or_

from retail_os.core.database import (
    CommandStatus,
    CommandProgress,
    SystemCommand,
    JobStatus,
    Order,
    Supplier,
    SupplierProduct,
    InternalProduct,
    TradeMeListing,
    SystemSetting,
    get_db_session,
)
from retail_os.core.category_mapper import CategoryMapper
from retail_os.core.validator import LaunchLock
from retail_os.core.inventory_ops import InventoryOperations
from retail_os.trademe.api import TradeMeAPI
from retail_os.analysis.profitability import ProfitabilityAnalyzer
from retail_os.core.llm_enricher import enricher as _llm_enricher

from ..dependencies import Role, require_role
from ..utils import _dt

router = APIRouter(prefix="/ops", tags=["ops"])

@router.get("/inbox")
def ops_inbox(_role: Role = Depends(require_role("power"))) -> dict[str, Any]:
    try:
        with get_db_session() as session:
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

@router.get("/summary")
def ops_summary(_role: Role = Depends(require_role("power"))) -> dict[str, Any]:
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
            "utc": datetime.utcnow().isoformat(),
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

@router.get("/pipeline_summary")
def ops_pipeline_summary(
    supplier_id: int,
    _role: Role = Depends(require_role("power")),
) -> dict[str, Any]:
    with get_db_session() as session:
        sup = session.query(Supplier).filter(Supplier.id == int(supplier_id)).first()
        if not sup:
            raise HTTPException(status_code=404, detail="Supplier not found")

        raw_total = session.query(func.count(SupplierProduct.id)).filter(SupplierProduct.supplier_id == sup.id).scalar() or 0
        raw_present = (
            session.query(func.count(SupplierProduct.id))
            .filter(SupplierProduct.supplier_id == sup.id, SupplierProduct.sync_status == "PRESENT")
            .scalar()
            or 0
        )
        raw_removed = (
            session.query(func.count(SupplierProduct.id))
            .filter(SupplierProduct.supplier_id == sup.id, SupplierProduct.sync_status == "REMOVED")
            .scalar()
            or 0
        )

        has_local = or_(
            SupplierProduct.images.like("%data/media/%"),
            SupplierProduct.images.like(r"%data\\media\\%"),
        )
        images_missing = (
            session.query(func.count(SupplierProduct.id))
            .filter(SupplierProduct.supplier_id == sup.id)
            .filter((SupplierProduct.images.is_(None)) | (~has_local))
            .scalar()
            or 0
        )

        enrich_ready = (
            session.query(func.count(SupplierProduct.id))
            .filter(SupplierProduct.supplier_id == sup.id)
            .filter(SupplierProduct.enriched_title.isnot(None))
            .filter(SupplierProduct.enriched_description.isnot(None))
            .filter((SupplierProduct.sync_status.is_(None)) | (SupplierProduct.sync_status == "PRESENT"))
            .scalar()
            or 0
        )

        drafts = (
            session.query(func.count(TradeMeListing.id))
            .join(InternalProduct, TradeMeListing.internal_product_id == InternalProduct.id)
            .join(SupplierProduct, InternalProduct.primary_supplier_product_id == SupplierProduct.id)
            .filter(SupplierProduct.supplier_id == sup.id)
            .filter(TradeMeListing.actual_state == "DRY_RUN")
            .scalar()
            or 0
        )
        live = (
            session.query(func.count(TradeMeListing.id))
            .join(InternalProduct, TradeMeListing.internal_product_id == InternalProduct.id)
            .join(SupplierProduct, InternalProduct.primary_supplier_product_id == SupplierProduct.id)
            .filter(SupplierProduct.supplier_id == sup.id)
            .filter(TradeMeListing.actual_state == "Live")
            .scalar()
            or 0
        )

        q = session.query(SupplierProduct).filter(SupplierProduct.supplier_id == sup.id)
        q = q.filter((SupplierProduct.sync_status.is_(None)) | (SupplierProduct.sync_status == "PRESENT"))
        rows = q.limit(20000).all()
        reasons: Counter[str] = Counter()
        for sp in rows:
            if sp.cost_price is None or float(sp.cost_price or 0) <= 0:
                reasons["Missing/invalid cost price"] += 1
                continue
            if not (sp.enriched_title or "").strip():
                reasons["Missing enriched title"] += 1
                continue
            if not (sp.enriched_description or "").strip():
                reasons["Missing enriched description"] += 1
                continue
            imgs = sp.images or []
            has_local = any(isinstance(x, str) and x.replace("\\", "/").startswith("data/media/") for x in (imgs if isinstance(imgs, list) else []))
            if not has_local:
                reasons["Missing images (local)"] += 1
                continue
            if not CategoryMapper.map_category(
                getattr(sp, "source_category", "") or "",
                sp.title or "",
                (getattr(sp, "enriched_description", None) or getattr(sp, "description", None) or ""),
            ):
                reasons["Missing category mapping"] += 1
                continue

        return {
            "utc": datetime.utcnow().isoformat(),
            "supplier": {"id": sup.id, "name": sup.name},
            "counts": {
                "raw_total": raw_total,
                "raw_present": raw_present,
                "raw_removed": raw_removed,
                "images_missing": images_missing,
                "enrich_ready": enrich_ready,
                "drafts_dry_run": drafts,
                "live": live,
            },
            "top_blockers": reasons.most_common(10),
        }

@router.get("/suppliers/{supplier_id}/pipeline")
def ops_supplier_pipeline(
    supplier_id: int,
    _role: Role = Depends(require_role("power")),
) -> dict[str, Any]:
    with get_db_session() as session:
        sup = session.query(Supplier).filter(Supplier.id == int(supplier_id)).first()
        if not sup:
            raise HTTPException(status_code=404, detail="Supplier not found")

        summary = ops_pipeline_summary(supplier_id=int(supplier_id), _role=_role)

        pat_a = f'%\"supplier_id\": {int(supplier_id)}%'
        pat_b = f'%\"supplier_id\":{int(supplier_id)}%'
        q = (
            session.query(SystemCommand)
            .filter(SystemCommand.status.in_([CommandStatus.PENDING, CommandStatus.EXECUTING]))
            .filter(or_(SystemCommand.payload.like(pat_a), SystemCommand.payload.like(pat_b)))
            .order_by(SystemCommand.updated_at.desc())
            .limit(50)
        )
        cmds = q.all()

        progresses = {
            p.command_id: p
            for p in session.query(CommandProgress)
            .filter(CommandProgress.command_id.in_([c.id for c in cmds] or ["__none__"]))
            .all()
        }

        items: list[dict[str, Any]] = []
        for c in cmds:
            p = progresses.get(c.id)
            items.append(
                {
                    "id": c.id,
                    "type": c.type,
                    "status": c.status.value if hasattr(c.status, "value") else str(c.status),
                    "priority": c.priority,
                    "attempts": c.attempts,
                    "max_attempts": c.max_attempts,
                    "error_code": c.error_code,
                    "error_message": c.error_message,
                    "payload": c.payload or {},
                    "created_at": _dt(c.created_at),
                    "updated_at": _dt(c.updated_at),
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
            )

        return {
            "utc": datetime.utcnow().isoformat(),
            "supplier": {"id": sup.id, "name": sup.name, "base_url": sup.base_url, "is_active": sup.is_active},
            "summary": summary,
            "active_commands": items,
        }

@router.get("/alerts")
def ops_alerts(_role: Role = Depends(require_role("power"))) -> dict[str, Any]:
    alerts: list[dict[str, Any]] = []
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

    try:
        api = TradeMeAPI()
        summary = api.get_account_summary()
        balance_raw = summary.get("account_balance")

        min_balance = float(os.getenv("RETAIL_OS_MIN_BALANCE") or 20.0)
        if balance_raw is None:
            note = summary.get("balance_error") or "Balance not returned by Trade Me API for this account/app"
            alerts.append(
                {
                    "severity": "medium",
                    "code": "TRADEME_BALANCE_UNAVAILABLE",
                    "title": "Trade Me balance unavailable",
                    "detail": str(note)[:200],
                }
            )
        else:
            balance = float(balance_raw)
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

@router.post("/enqueue", response_model=CommandCreateResponse)
def ops_enqueue(req: EnqueueRequest, _role: Role = Depends(require_role("power"))) -> CommandCreateResponse:
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
    limit: int = 200
    priority: int = 60
    stop_on_failure: bool = True

@router.post("/bulk/dryrun_publish", response_model=dict[str, Any])
def bulk_dryrun_publish(req: BulkDryRunPublishRequest, _role: Role = Depends(require_role("power"))) -> dict[str, Any]:
    if req.limit < 1 or req.limit > 1000:
        raise HTTPException(status_code=400, detail="Invalid limit")

    with get_db_session() as session:
        q = session.query(InternalProduct).join(SupplierProduct, InternalProduct.primary_supplier_product_id == SupplierProduct.id)
        if req.supplier_id is not None:
            q = q.filter(SupplierProduct.supplier_id == int(req.supplier_id))
        if req.source_category:
            q = q.filter(SupplierProduct.source_category == req.source_category)
        q = q.filter((SupplierProduct.sync_status.is_(None)) | (SupplierProduct.sync_status == "PRESENT"))

        q = q.outerjoin(TradeMeListing, TradeMeListing.internal_product_id == InternalProduct.id).filter(
            (TradeMeListing.id.is_(None)) | (~TradeMeListing.actual_state.in_(["Live", "DRY_RUN"]))
        )

        q = q.order_by(SupplierProduct.last_scraped_at.desc())

        candidates = q.limit(int(req.limit)).all()

        enqueued = 0
        skipped_existing_cmd = 0
        skipped_already_listed = 0
        skipped_blocked = 0
        blocked_reasons: dict[str, int] = {}

        def _b(reason: str):
            nonlocal skipped_blocked
            skipped_blocked += 1
            blocked_reasons[reason] = int(blocked_reasons.get(reason, 0) + 1)

        def _precheck(ip: InternalProduct) -> tuple[bool, str | None]:
            sp = ip.supplier_product
            if not sp:
                return False, "Missing supplier link"
            if str(sp.sync_status or "").upper() == "REMOVED":
                return False, "Removed from supplier"
            if not (sp.product_url or "").strip():
                return False, "Missing source URL"
            if sp.cost_price is None or float(sp.cost_price or 0) <= 0:
                return False, "Missing/invalid source price"
            if not (sp.enriched_title or "").strip():
                return False, "Missing enriched title"
            if not (sp.enriched_description or "").strip():
                return False, "Missing enriched description"
            imgs = sp.images or []
            try:
                import os as _os
                if isinstance(imgs, list):
                    if not any(isinstance(x, str) and _os.path.exists(x) for x in imgs):
                        return False, "Images unavailable for upload (no local images)"
            except Exception:
                return False, "Images unavailable for upload (check local media folder)"

            try:
                cat = CategoryMapper.map_category(
                    getattr(sp, "source_category", "") or "",
                    sp.title or "",
                    (getattr(sp, "enriched_description", None) or getattr(sp, "description", None) or ""),
                )
                if not cat:
                    return False, "Unmapped Trade Me category"
                if getattr(CategoryMapper, "DEFAULT_CATEGORY", None) and cat == CategoryMapper.DEFAULT_CATEGORY:
                    return False, "Unmapped Trade Me category"
            except Exception:
                return False, "Unmapped Trade Me category"
            return True, None

        for ip in candidates:
            ok, reason = _precheck(ip)
            if not ok:
                _b(reason or "Blocked")
                continue

            already = False
            for l in (ip.listings or []):
                if l.actual_state in ["Live", "DRY_RUN"]:
                    already = True
                    break
            if already:
                skipped_already_listed += 1
                continue

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
            if req.stop_on_failure and enqueued >= 1:
                break

        session.commit()
        return {
            "enqueued": enqueued,
            "skipped_existing_cmd": skipped_existing_cmd,
            "skipped_already_listed": skipped_already_listed,
            "skipped_blocked": skipped_blocked,
            "top_blockers": sorted(blocked_reasons.items(), key=lambda x: x[1], reverse=True)[:10],
            "requested_limit": req.limit,
            "stop_on_failure": bool(req.stop_on_failure),
        }

class BulkWithdrawRemovedRequest(BaseModel):
    supplier_id: Optional[int] = None

@router.post("/bulk/withdraw_removed", response_model=dict[str, Any])
def bulk_withdraw_removed(req: BulkWithdrawRemovedRequest, _role: Role = Depends(require_role("power"))) -> dict[str, Any]:
    with get_db_session() as session:
        ops = InventoryOperations(session)
        enqueued = ops.withdraw_unavailable_items(supplier_id=req.supplier_id)
        return {"enqueued": enqueued}

class BulkApprovePublishRequest(BaseModel):
    supplier_id: Optional[int] = None
    source_category: Optional[str] = None
    limit: int = 50
    priority: int = 60
    stop_on_failure: bool = True

@router.post("/bulk/approve_publish", response_model=dict[str, Any])
def bulk_approve_publish(req: BulkApprovePublishRequest, _role: Role = Depends(require_role("power"))) -> dict[str, Any]:
    if req.limit < 1 or req.limit > 2000:
        raise HTTPException(status_code=400, detail="Invalid limit")

    with get_db_session() as session:
        try:
            _ = TradeMeAPI()
        except Exception:
            raise HTTPException(status_code=409, detail="Trade Me is not configured/auth failed. Publishing disabled.")

        store_mode = "NORMAL"
        s = session.query(SystemSetting).filter(SystemSetting.key == "store.mode").first()
        if s and isinstance(s.value, str) and s.value.strip():
            store_mode = s.value.strip().upper()
        if store_mode in ["HOLIDAY", "PAUSED"]:
            raise HTTPException(status_code=409, detail=f"Publishing disabled in store.mode={store_mode}")

        pub = session.query(SystemSetting).filter(SystemSetting.key == "publishing.policy").first()
        pub_cfg: dict[str, Any] = pub.value if pub and isinstance(pub.value, dict) else {}
        max_per_day = int(pub_cfg.get("max_publishes_per_day") or 0)
        if max_per_day:
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
            req.limit = min(int(req.limit), int(remaining))

        q = session.query(TradeMeListing).join(InternalProduct).join(SupplierProduct)
        q = q.filter(TradeMeListing.actual_state == "DRY_RUN")
        q = q.filter((SupplierProduct.sync_status.is_(None)) | (SupplierProduct.sync_status == "PRESENT"))
        if req.supplier_id is not None:
            q = q.filter(SupplierProduct.supplier_id == int(req.supplier_id))
        if req.source_category:
            q = q.filter(SupplierProduct.source_category == req.source_category)
        q = q.order_by(TradeMeListing.last_synced_at.desc().nullslast())

        limit_effective = 1 if req.stop_on_failure else int(req.limit)
        rows = q.limit(int(limit_effective)).all()

        enqueued = 0
        skipped_existing_cmd = 0
        skipped_drift = 0
        skipped_missing_metadata = 0
        skipped_bad_dryrun_id = 0
        skipped_not_ready = 0
        not_ready_reasons: dict[str, int] = {}

        def _nr(reason: str):
            nonlocal skipped_not_ready
            skipped_not_ready += 1
            not_ready_reasons[reason] = int(not_ready_reasons.get(reason, 0) + 1)

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

            try:
                current_snap = l.internal_product.supplier_product.snapshot_hash
            except Exception:
                current_snap = None
            if not current_snap or str(current_snap) != str(snap):
                skipped_drift += 1
                continue

            try:
                ip = l.product
                if not ip:
                    _nr("Missing internal product")
                    continue
                LaunchLock(session).validate_publish(ip, test_mode=False)
            except Exception as e:
                _nr(str(e)[:200] or "Blocked")
                continue

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
            "skipped_not_ready": skipped_not_ready,
            "top_not_ready": sorted(not_ready_reasons.items(), key=lambda x: x[1], reverse=True)[:10],
            "requested_limit": req.limit,
            "stop_on_failure": bool(req.stop_on_failure),
            "store_mode": store_mode,
            "quota_max_per_day": int(pub_cfg.get("max_publishes_per_day") or 0),
        }

class BulkResetEnrichmentRequest(BaseModel):
    supplier_id: Optional[int] = None
    source_category: Optional[str] = None
    limit: int = 200
    priority: int = 60

@router.post("/bulk/reset_enrichment", response_model=dict[str, Any])
def bulk_reset_enrichment(req: BulkResetEnrichmentRequest, _role: Role = Depends(require_role("power"))) -> dict[str, Any]:
    if req.limit < 1 or req.limit > 2000:
        raise HTTPException(status_code=400, detail="Invalid limit")

    with get_db_session() as session:
        q = session.query(SupplierProduct)
        if req.supplier_id is not None:
            q = q.filter(SupplierProduct.supplier_id == int(req.supplier_id))
        if req.source_category:
            q = q.filter(SupplierProduct.source_category == req.source_category)

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

class BulkRepriceRequest(BaseModel):
    supplier_id: Optional[int] = None
    category_id: Optional[str] = None
    rule_type: str = "percentage"
    rule_value: float = 0.0
    min_margin: float = 0.10
    dry_run: bool = True
    limit: int = 50

@router.post("/bulk/reprice")
def bulk_reprice(req: BulkRepriceRequest, _role: Role = Depends(require_role("power"))):
    with get_db_session() as session:
        q = session.query(TradeMeListing).join(InternalProduct).join(SupplierProduct)
        q = q.filter(TradeMeListing.actual_state == "Live")
        
        if req.supplier_id:
            q = q.filter(SupplierProduct.supplier_id == int(req.supplier_id))
        if req.category_id:
            q = q.filter(SupplierProduct.source_category == req.category_id)
            
        listings = q.limit(req.limit).all()
        
        results = []
        enqueued_count = 0
        
        for l in listings:
            try:
                sp = l.internal_product.supplier_product
                cost = float(sp.cost_price or 0)
                if cost <= 0:
                    continue
                    
                current_price = float(l.actual_price or 0)
                
                new_price = current_price
                if req.rule_type == "percentage":
                    target_price = cost * (1 + req.rule_value)
                    new_price = target_price
                elif req.rule_type == "fixed_markup":
                    new_price = cost + req.rule_value
                
                prof = ProfitabilityAnalyzer.predict_profitability(new_price, cost)
                is_safe = True
                safety_reason = None
                
                if prof["net_profit"] < 0:
                    is_safe = False
                    safety_reason = "Negative Profit"
                elif (prof["net_profit"] / new_price) < req.min_margin:
                    is_safe = False
                    safety_reason = f"Margin < {req.min_margin:.0%}"
                
                item = {
                    "listing_id": l.id,
                    "tm_listing_id": l.tm_listing_id,
                    "title": l.internal_product.enriched_title or sp.product_name,
                    "cost": cost,
                    "current_price": current_price,
                    "new_price": round(new_price, 2),
                    "net_profit": prof["net_profit"],
                    "roi": prof["roi_percent"],
                    "is_safe": is_safe,
                    "safety_reason": safety_reason
                }
                
                if not req.dry_run and is_safe:
                    cmd = SystemCommand(
                        id=str(uuid.uuid4()),
                        type="UPDATE_PRICE",
                        payload={"listing_id": l.id, "new_price": item["new_price"]},
                        status=CommandStatus.PENDING,
                        priority=60
                    )
                    session.add(cmd)
                    enqueued_count += 1
                
                results.append(item)
                
            except Exception:
                continue

        if not req.dry_run:
            session.commit()
            return {"enqueued": enqueued_count, "items": results}
        
        return {"dry_run": True, "items": results}

@router.get("/kpis")
def get_ops_kpis(_role: Role = Depends(require_role("reader"))):
    with get_db_session() as session:
        today = date.today()
        
        sales_today = (
            session.query(func.count(Order.id))
            .filter(func.date(Order.sold_date) == today)
            .scalar()
        ) or 0
        
        listed_today = (
            session.query(func.count(SystemCommand.id))
            .filter(SystemCommand.type == "PUBLISH_LISTING")
            .filter(SystemCommand.status == "SUCCEEDED")
            .filter(func.date(SystemCommand.updated_at) == today)
            .scalar()
        ) or 0
        
        backlog = session.query(func.count(SystemCommand.id)).filter(SystemCommand.status == "PENDING").scalar() or 0
        
        failures_today = (
            session.query(func.count(SystemCommand.id))
            .filter(SystemCommand.status.like("FAILED%"))
            .filter(func.date(SystemCommand.updated_at) == today)
            .scalar()
        ) or 0
        
        return {
            "sales_today": sales_today,
            "listed_today": listed_today,
            "backlog": backlog,
            "failures_today": failures_today
        }

@router.get("/duplicates")
def get_duplicates(_role: Role = Depends(require_role("power"))):
    with get_db_session() as session:
        subq = (
            session.query(TradeMeListing.internal_product_id)
            .filter(TradeMeListing.actual_state == "Live")
            .group_by(TradeMeListing.internal_product_id)
            .having(func.count(TradeMeListing.id) > 1)
        )
        
        dupes = []
        for row in subq:
            ip_id = row[0]
            listings = session.query(TradeMeListing).filter(TradeMeListing.internal_product_id == ip_id, TradeMeListing.actual_state == 'Live').all()
            dupes.append({
                "internal_product_id": ip_id,
                "listings": [
                    {"id": l.id, "tm_id": l.tm_listing_id, "price": l.actual_price, "last_synced": _dt(l.last_synced_at)} 
                    for l in listings
                ]
            })
            
        return {"duplicates": dupes, "count": len(dupes)}
