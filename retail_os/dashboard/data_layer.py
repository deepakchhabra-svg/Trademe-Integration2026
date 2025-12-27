import streamlit as st
from sqlalchemy import func
from sqlalchemy.orm import Session
from retail_os.core.database import (
    SupplierProduct, InternalProduct, TradeMeListing, 
    JobStatus, Order, SystemCommand, CommandStatus,
    AuditLog
)

def log_audit(session, action, entity_type, entity_id, old_val=None, new_val=None):
    """Helper to write audit log entry."""
    entry = AuditLog(
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        old_value=str(old_val) if old_val else None,
        new_value=str(new_val) if new_val else None,
        user="SYSTEM"
    )
    session.add(entry)

# === VALIDATOR RELOCATION (User Request) ===
from retail_os.core.validator import LaunchLock as _LaunchLock
# We alias it to avoid confusion, but we essentially just re-export the functionality 
# so the UI and Worker can import it from here if they wish, 
# OR we implement a helper that does the validation and logging in one step.

def validate_product_for_launch(session, product_id):
    """
    Centralized validation gate.
    Returns: (bool, reasons)
    """
    from retail_os.core.database import InternalProduct
    product = session.query(InternalProduct).get(product_id)
    if not product:
        return False, ["Product not found"]
        
    validator = _LaunchLock(session)
    try:
         validator.validate_publish(product)
         
         # LOG SUCCESS AUDIT (User Request: "save why it was considered safe")
         from retail_os.core.trust import TrustEngine, TrustReport
         from retail_os.strategy.pricing import PricingStrategy
         
         sp = product.supplier_product
         cost = float(sp.cost_price or 0)
         price = PricingStrategy.calculate_price(cost, supplier_name=sp.supplier.name if sp.supplier else None)
         report = validator.trust_engine.get_product_trust_report(product)
         
         log_audit(session, "VALIDATION_PASS", "InternalProduct", product_id, 
                   new_val=f"Score:{report.score}, Price:{price}")
         return True, []
    except ValueError as e:
         log_audit(session, "VALIDATION_FAIL", "InternalProduct", product_id, 
                   new_val=str(e))
         return False, [str(e)]

def submit_publish_command(session, product_id):
    """
    INVIOLABLE GATEWAY: Creates PUBLISH command ONLY if validation passes.
    Returns: (bool, message, command_id)
    """
    is_valid, reasons = validate_product_for_launch(session, product_id)
    if not is_valid:
        return False, f"Validation Failed: {', '.join(reasons)}", None
        
    # Proceed to create command
    from retail_os.core.database import SystemCommand, CommandStatus
    import uuid
    cmd_id = str(uuid.uuid4())
    cmd = SystemCommand(
        id=cmd_id,
        type="PUBLISH_LISTING",  # Use 'type' field (DB schema)
        payload={"internal_product_id": product_id},
        status=CommandStatus.PENDING
    )
    session.add(cmd)
    session.commit()  # Commit so command is immediately observable
    return True, "Listing queued for publication!", cmd_id
    
# REPOSITORY PATTERN & CACHING
# We use st.cache_data to cache the RESULTS of these queries.
# TTL=60 means data refreshes every minute, making the UI feel "instant" 
# during navigation while remaining relatively fresh.

@st.cache_data(ttl=60)
def fetch_vault_metrics(_session_maker):
    """Fetch high-level counts for the dashboard metrics cards."""
    # Note: We pass a session_maker or handle session internally to avoid threading issues with caching
    # However, since we can't pickle the session easily, a common pattern with st.cache_data 
    # is to accept data params and return simple python objects (dicts/lists).
    # For simplicity here, we'll assume the session is managed or we use a fresh one.
    
    # BETTER APPROACH FOR CACHING: Create a local session just for this read
    # or rely on the fact that we return simple types (ints).
    # To be safe and properly cached, we should pass the session factory or nothing 
    # and create the session inside, OR assume the user handles cache invalidation.
    # Given the architecture, we'll strip the session from the cache key using `_` prefix if passed,
    # OR better: instantiate a fresh session here.
    
    from retail_os.core.database import get_db_session, SystemCommand, CommandStatus
    
    with get_db_session() as session:
        metrics = {
            "vault1_count": session.query(SupplierProduct).count(),
            "vault1_active": session.query(SupplierProduct).filter(SupplierProduct.sync_status == 'PRESENT').count(),
            "vault2_count": session.query(InternalProduct).count(),
            "vault3_count": session.query(TradeMeListing).count(),
            "pending_jobs": session.query(SystemCommand).filter(
                SystemCommand.status.in_([CommandStatus.PENDING, CommandStatus.EXECUTING, CommandStatus.FAILED_RETRYABLE])
            ).count()
        }
        return metrics

@st.cache_data(ttl=60)
def fetch_vault1_data(search_term=None, supplier_id=None, sync_status=None, page=1, per_page=50):
    """Fetch raw supplier products for Vault 1."""
    from retail_os.core.database import get_db_session
    
    with get_db_session() as session:
        query = session.query(SupplierProduct)
        
        if search_term:
            term = f"%{search_term}%"
            query = query.filter(
                (SupplierProduct.title.ilike(term)) |
                (SupplierProduct.external_sku.ilike(term))
            )

        if supplier_id:
            query = query.filter(SupplierProduct.supplier_id == int(supplier_id))

        if sync_status and sync_status != "All":
            query = query.filter(SupplierProduct.sync_status == sync_status)
            
        total = query.count()
        offset = (page - 1) * per_page
        # Eager load supplier to avoid N+1
        from sqlalchemy.orm import joinedload
        items = query.options(joinedload(SupplierProduct.supplier))\
            .order_by(SupplierProduct.last_scraped_at.desc()).offset(offset).limit(per_page).all()
        
        # Convert to list of dicts for caching/rendering
        data = []
        for item in items:
            data.append({
                "id": item.id,
                "img": item.images[0] if item.images and len(item.images) > 0 else None,
                "sku": item.external_sku,
                "title": item.title,
                "price": float(item.cost_price) if item.cost_price else 0.0,
                "stock": item.stock_level,
                "supplier": item.supplier.name if item.supplier else "Unknown",
                "status": item.sync_status,
                "last_scraped": item.last_scraped_at
            })
            
        return data, total

@st.cache_data(ttl=60)
def fetch_vault2_data(search_term=None, supplier_id=None, enrichment_filter="All", page=1, per_page=50):
    """Fetch sanitized internal products for Vault 2."""
    from retail_os.core.database import get_db_session
    
    with get_db_session() as session:
        query = session.query(InternalProduct).join(SupplierProduct)
        
        if search_term:
            term = f"%{search_term}%"
            query = query.filter(
                (InternalProduct.title.ilike(term)) |
                (SupplierProduct.enriched_description.ilike(term))
            )

        if supplier_id:
            query = query.filter(SupplierProduct.supplier_id == int(supplier_id))

        if enrichment_filter == "Enriched":
            query = query.filter(SupplierProduct.enriched_description.isnot(None))
        elif enrichment_filter == "Not Enriched":
            query = query.filter(SupplierProduct.enriched_description.is_(None))
            
        total = query.count()
        offset = (page - 1) * per_page
        from sqlalchemy.orm import joinedload
        items = query.options(
            joinedload(InternalProduct.supplier_product).joinedload(SupplierProduct.supplier)
        ).offset(offset).limit(per_page).all()
        
        data = []
        # PERFORMANCE FIX: Don't calculate trust scores in table view
        # Trust scores are only shown in the inspector pane
        
        for item in items:
            sp = item.supplier_product
            
            data.append({
                "id": item.id,
                "sku": item.sku,
                "title": item.title or sp.title,
                "supplier": sp.supplier.name if sp and sp.supplier else "Unknown",
                "cost": float(sp.cost_price) if sp.cost_price else 0.0,
                "stock": sp.stock_level,
                "enriched": bool(sp.enriched_description),
                "trust_score": None,  # Calculated on-demand in inspector only # FIXED: Real Score
                "sp_title": sp.title, # For comparison
                "sp_desc": sp.description,
                "enriched_desc": sp.enriched_description,
                "images": sp.images or [],
            })
            
        return data, total

@st.cache_data(ttl=60)
def fetch_vault3_data(search_term=None, status_filter="All", page=1, per_page=50):
    """Fetch active marketplace listings for Vault 3."""
    from retail_os.core.database import get_db_session
    
    with get_db_session() as session:
        query = session.query(TradeMeListing)
        
        if status_filter != "All":
            # Fix Emoji/Formatting gap: Status in DB is likely "Live", "Withdrawn".
            # UI filter might send "Active", "Sold".
            # Map standard statuses
            db_status = status_filter
            if status_filter == "Active": db_status = "Live"
            
            query = query.filter_by(actual_state=db_status)
        
        if search_term:
            term = f"%{search_term}%"
            query = query.join(InternalProduct).filter(
                (InternalProduct.title.ilike(term)) |
                (TradeMeListing.tm_listing_id.ilike(term))
            )
        
        # Ensure we have access to cost price for profit calcs
        query = query.join(InternalProduct, TradeMeListing.internal_product_id == InternalProduct.id).join(
            SupplierProduct, InternalProduct.primary_supplier_product_id == SupplierProduct.id
        )
            
        total = query.count()
        offset = (page - 1) * per_page
        # Eager load metrics for sparklines
        from sqlalchemy.orm import joinedload
        from retail_os.core.database import ListingMetricSnapshot
        
        items = query.options(
            joinedload(TradeMeListing.metrics),
            joinedload(TradeMeListing.product).joinedload(InternalProduct.supplier_product)
        ).order_by(TradeMeListing.last_synced_at.desc()).offset(offset).limit(per_page).all()
        
        data = []
        for item in items:
            # Build Sparkline (Last 7 snapshots)
            # Ideally we'd filter by date, but taking last 7 records is a fast proxy
            metrics = sorted(item.metrics, key=lambda x: x.captured_at) if item.metrics else []
            sparkline_data = [m.view_count for m in metrics[-7:]] if metrics else [0]*7
            
            data.append({
                "tm_id": item.tm_listing_id,
                "title": item.product.title if item.product else "Unknown",
                "price": float(item.actual_price) if item.actual_price else 0.0,
                "views": item.view_count or 0,
                "watchers": item.watch_count or 0,
                "status": item.actual_state, # Raw state (Live/Withdrawn)
                "lifecycle": item.lifecycle_state, # Strategy State (NEW/PROVING...)
                "sparkline": sparkline_data,
                "listed_date": item.last_synced_at,
                "category": item.category_id or "N/A",
                "profit_potential": 0.0
            })
            
            # Calculate Profit Momentum
            # (Price - Cost) * Views
            if item.product and item.product.supplier_product:
                cost = float(item.product.supplier_product.cost_price or 0)
                price = float(item.actual_price or 0)
                margin = price - cost
                views = item.view_count or 0
                if margin > 0:
                    data[-1]["profit_potential"] = margin * (views + 1) # +1 to avoid zeroing out
                    data[-1]["margin"] = margin
            
        return data, total

def fetch_recent_jobs(limit=10):
    """Fetch recent job history. NOT cached to show live status."""
    from retail_os.core.database import get_db_session
    
    with get_db_session() as session:
        jobs = session.query(JobStatus).order_by(JobStatus.start_time.desc()).limit(limit).all()
        data = []
        for job in jobs:
            data.append({
                "id": job.id,
                "type": job.job_type,
                "status": job.status,
                "start": job.start_time,
                "end": job.end_time,
                "processed": job.items_processed,
                "created": job.items_created,
                "updated": job.items_updated,
                "failed": job.items_failed
            })
        return data

def fetch_orders(limit=50):
    """Fetch recent orders. NOT cached."""
    from retail_os.core.database import get_db_session
    
    with get_db_session() as session:
        orders = session.query(Order).order_by(Order.created_at.desc()).limit(limit).all()
        return [
            {
                "ref": o.tm_order_ref,
                "buyer": o.buyer_name,
                "sold_price": float(o.sold_price) if o.sold_price is not None else None,
                "sold_date": o.sold_date,
                "order_status": o.order_status,
                "payment_status": o.payment_status,
                "fulfillment_status": o.fulfillment_status,
                "tracking_reference": o.tracking_reference,
                "carrier": o.carrier,
                "created_at": o.created_at,
                "updated_at": o.updated_at,
            }
            for o in orders
        ]

def fetch_system_health():
    """Fetch aggregated system health metrics (Heartbeat, Locks, Throughput)."""
    from retail_os.core.database import get_db_session
    from retail_os.core.database import ResourceLock
    
    with get_db_session() as session:
        # 1. Heartbeat Grid (Last run of each job type)
        last_runs = session.query(
            JobStatus.job_type,
            func.max(JobStatus.start_time).label('last_run'),
            JobStatus.status,
            JobStatus.end_time
        ).group_by(JobStatus.job_type).all()
        
        heartbeats = {}
        for run in last_runs:
            real_job = session.query(JobStatus).filter_by(start_time=run.last_run, job_type=run.job_type).first()
            if real_job:
                heartbeats[run.job_type] = {
                    "last_run": real_job.start_time,
                    "status": real_job.status,
                    "duration": (real_job.end_time - real_job.start_time).total_seconds() if real_job.end_time else 0
                }
            else:
                 heartbeats[run.job_type] = {"status": "UNKNOWN", "last_run": run.last_run}

        # 2. Active Locks
        locks = session.query(ResourceLock).all()
        active_locks = [{
            "type": l.entity_type,
            "id": l.entity_id,
            "owner": l.owner_cmd_id
        } for l in locks]
        
        # 3. Scraper Throughput (Last 24h)
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(hours=24)
        
        def calc_throughput(job_type):
            runs = session.query(JobStatus).filter(
                JobStatus.job_type == job_type, 
                JobStatus.start_time > cutoff,
                JobStatus.status == 'COMPLETED'
            ).all()
            total_items = sum([r.items_processed for r in runs])
            total_seconds = sum([(r.end_time - r.start_time).total_seconds() for r in runs if r.end_time])
            return (total_items / (total_seconds / 60)) if total_seconds > 0 else 0.0

        throughput = {
            "SCRAPE_OC": calc_throughput("SCRAPE_OC"),
            "SCRAPE_NL": calc_throughput("SCRAPE_NL"),
            "SCRAPE_CC": calc_throughput("SCRAPE_CC"),
            "ENRICHMENT": calc_throughput("ENRICHMENT")
        }
        
        return {
            "heartbeats": heartbeats,
            "locks": active_locks,
            "throughput": throughput
        }

def fetch_price_history(listing_id):
    """Fetch price history for undo functionality."""
    from retail_os.core.database import get_db_session
    from retail_os.core.database import PriceHistory, TradeMeListing
    
    with get_db_session() as session:
        # Get internal ID from TM ID string if needed, but here we assume we might get SQL ID or TM ID
        # Let's handle TM ID string lookup
        listing = session.query(TradeMeListing).filter_by(tm_listing_id=listing_id).first()
        if not listing:
            return []
            
        history = session.query(PriceHistory).filter_by(listing_id=listing.id).order_by(PriceHistory.timestamp.desc()).limit(5).all()
        return [{
            "price": h.price,
            "date": h.timestamp,
            "type": h.change_type
        } for h in history]

@st.cache_data(ttl=60)
def get_account_health():
    """
    Fetch TradeMe account health (balance, ledgers, transactions).
    Returns: dict with status banner, balance, and ledger data.
    """
    try:
        from retail_os.trademe.api import TradeMeAPI
        api = TradeMeAPI()
        
        # Fetch all account data
        summary = api.get_account_summary()
        member_ledger = api.get_member_ledger()
        paynow_ledger = api.get_paynow_ledger()
        ping_txns = api.get_ping_transactions()
        
        # Determine status
        balance = summary.get("account_balance") or 0
        if balance and balance > 0:
            status = "OK_TO_LIST"
        elif balance == 0 or balance is None:
            status = "NEEDS_TOPUP"
        else:
            status = "OK_TO_LIST"  # Assume OK if balance check unclear
        
        return {
            "status": status,
            "balance": balance,
            "summary": summary,
            "member_ledger": member_ledger,
            "paynow_ledger": paynow_ledger,
            "ping_transactions": ping_txns
        }
    except Exception as e:
        return {
            "status": "CREDS_MISSING",
            "balance": None,
            "error": str(e),
            "summary": {},
            "member_ledger": [],
            "paynow_ledger": [],
            "ping_transactions": []
        }
