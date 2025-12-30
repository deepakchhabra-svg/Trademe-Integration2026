import time
import sys
import os
import json
import traceback
import re
import threading
from datetime import datetime, timezone
import logging
from pathlib import Path

# Add repo root to path (robust for different working dirs)
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from retail_os.core.database import (
    SessionLocal,
    SystemCommand,
    CommandStatus,
    ResourceLock,
    ListingDraft,
    InternalProduct,
    TradeMeListing,
    PhotoHash,
    CommandLog,
)
from retail_os.core.database import init_db
from retail_os.core.validator import LaunchLock
from retail_os.core.standardizer import Standardizer
from retail_os.strategy.pricing import PricingStrategy
from retail_os.trademe.api import TradeMeAPI
from datetime import timedelta
import hashlib
from dotenv import load_dotenv

# Load Environment for Workers
load_dotenv()

# Ensure schema exists before the worker starts polling.
# (Playwright/CI can start the worker before any API request hits init_db.)
try:
    init_db()
except Exception as e:
    print(f"Worker startup: init_db failed: {e}")

# Setup Logging
log_dir = os.path.join(os.path.dirname(__file__), '../../logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'worker.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8', errors='replace'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class _DBLogHandler(logging.Handler):
    """
    Capture log lines that include `cmd_id=<uuid>` and persist them to the DB.
    This enables live/persisted per-command logs in the UI.
    """

    _cmd_re = re.compile(r"cmd_id=([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})")
    _lock = threading.Lock()
    _buffer: list[dict] = []
    _last_flush = 0.0

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = record.getMessage()
            m = self._cmd_re.search(msg)
            if not m:
                return
            cmd_id = m.group(1)

            with self._lock:
                self._buffer.append(
                    {
                        "command_id": cmd_id,
                        "created_at": datetime.now(timezone.utc),
                        "level": record.levelname,
                        "logger": record.name,
                        "message": msg,
                        "meta": None,
                    }
                )

                now = time.time()
                # Batch flush for performance.
                if len(self._buffer) >= 25 or (now - self._last_flush) >= 2.0:
                    self._flush_locked(now)
        except Exception:
            # Never allow logging failures to crash the worker.
            return

    def flush(self) -> None:
        with self._lock:
            self._flush_locked(time.time())

    def _flush_locked(self, now: float) -> None:
        if not self._buffer:
            self._last_flush = now
            return
        batch = self._buffer[:]
        self._buffer.clear()
        self._last_flush = now

        session = SessionLocal()
        try:
            # bulk_insert_mappings is fast and avoids ORM overhead.
            session.bulk_insert_mappings(CommandLog, batch)
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()


# Attach DB log handler once.
try:
    # Attach to the *root* logger so logs from scrapers/adapters can be captured too,
    # as long as they include `cmd_id=<uuid>` in the message.
    root_logger = logging.getLogger()
    already = False
    for h in root_logger.handlers:
        if isinstance(h, _DBLogHandler):
            already = True
            break
    if not already:
        root_logger.addHandler(_DBLogHandler())
    # Keep it on this module logger as well (harmless if duplicates are avoided above).
    if not any(isinstance(h, _DBLogHandler) for h in logger.handlers):
        logger.addHandler(_DBLogHandler())
except Exception:
    pass

class CommandWorker:
    def __init__(self):
        self.running = True
        try:
            self.api = TradeMeAPI()
            print("API Client Initialized.")
        except Exception as e:
            print(f"API Client Init Failed (Running in Offline Mode?): {e}")
            self.api = None

    @staticmethod
    def resolve_command(command):
        """
        Compatibility resolver: supports both naming conventions
        - command_type + parameters (new)
        - type + payload (legacy)
        """
        cmd_type = getattr(command, "command_type", None) or getattr(command, "type", None)
        payload = getattr(command, "parameters", None) or getattr(command, "payload", None) or {}
        # Normalize common drift issues: accidental whitespace or non-str types.
        if cmd_type is not None and not isinstance(cmd_type, str):
            cmd_type = str(cmd_type)
        if isinstance(cmd_type, str):
            cmd_type = cmd_type.strip()
        return cmd_type, payload

    def run(self):
        print("Command Worker Started. Polling for PENDING commands...")
        while self.running:
            try:
                self.process_next_command()
            except Exception as e:
                print(f"Worker Crash: {e}")
                time.sleep(5)
            time.sleep(1)

    def process_next_command(self):
        session = SessionLocal()
        try:
            # 1. Fetch Next PENDING Command (Priority Order)
            # We use 'with_for_update' if logic requires skipping locked rows (SQLite doesn't fully support row locking, but WAL helps)
            command = session.query(SystemCommand).filter(
                SystemCommand.status == CommandStatus.PENDING
            ).order_by(SystemCommand.priority.desc()).first()

            if not command:
                return # Sleep and poll again

            cmd_type, payload = self.resolve_command(command)
            
            print(f"Processing Command {command.id} [{cmd_type}]")
            logger.info(f"CMD_START cmd_id={command.id} type={cmd_type}")

            # 2. Move to EXECUTING
            command.status = CommandStatus.EXECUTING
            command.updated_at = datetime.now(timezone.utc)
            session.commit()

            # 3. Execute Logic (Simulated for Vertical Slice Phase 1)
            try:
                self.execute_logic(command)
                # Handlers may mark a command CANCELLED (operator-requested stop).
                # Do not overwrite that with SUCCEEDED.
                if command.status == CommandStatus.CANCELLED:
                    print(f"Command {command.id} CANCELLED")
                    logger.info(f"CMD_CANCELLED cmd_id={command.id} type={cmd_type}")
                else:
                    command.status = CommandStatus.SUCCEEDED
                    print(f"Command {command.id} SUCCEEDED")
                    logger.info(f"CMD_SUCCEEDED cmd_id={command.id} type={cmd_type}")
            except Exception as logic_error:
                print(f"Command {command.id} FAILED: {logic_error}")
                command.last_error = str(logic_error)
                logger.error(f"CMD_FAILED cmd_id={command.id} type={cmd_type} err={logic_error}")
                
                # CRITICAL: Do NOT overwrite HUMAN_REQUIRED status set by handler
                if command.status == CommandStatus.HUMAN_REQUIRED:
                    # Handler already set terminal status, don't increment attempts
                    print(f"   -> Status: HUMAN_REQUIRED (set by handler)")
                    logger.warning(f"CMD_HUMAN_REQUIRED cmd_id={command.id} type={cmd_type}")
                elif command.status == CommandStatus.CANCELLED:
                    # Handler already set terminal status (operator cancelled).
                    print(f"   -> Status: CANCELLED (set by handler)")
                    logger.info(f"CMD_CANCELLED cmd_id={command.id} type={cmd_type}")
                else:
                    command.attempts += 1
                    if command.attempts < command.max_attempts:
                        command.status = CommandStatus.FAILED_RETRYABLE
                    else:
                        command.status = CommandStatus.HUMAN_REQUIRED
            
            command.updated_at = datetime.now(timezone.utc)
            session.commit()
            # Flush any buffered log lines for this command.
            try:
                for h in logger.handlers:
                    if isinstance(h, _DBLogHandler):
                        h.flush()
            except Exception:
                pass

        except Exception as e:
            session.rollback()
            print(f"DB Error in Worker: {e}")
            traceback.print_exc()
        finally:
            session.close()

    def execute_logic(self, command):
        """
        The routing logic. In real app, this calls API Client.
        """
        command_type, payload = self.resolve_command(command)

        if command_type == "PUBLISH_LISTING":
            self.handle_publish(command)
            return

        elif command_type == "UPDATE_PRICE":
            listing_id = payload.get("listing_id") or payload.get("tm_listing_id") or payload.get("target_id")
            new_price = payload.get("new_price") or payload.get("price")
            if not listing_id or new_price is None:
                raise ValueError("UPDATE_PRICE requires listing_id and new_price")
            if not self.api:
                raise Exception("API wrapper not available.")

            print(f"   -> Updating price listing_id={listing_id} new_price={new_price}")
            ok = self.api.update_price(str(listing_id), float(new_price))
            if not ok:
                raise ValueError("Update price returned False")

            # Persist local truth + history
            session = SessionLocal()
            try:
                from retail_os.core.database import TradeMeListing, PriceHistory

                tm = session.query(TradeMeListing).filter(TradeMeListing.tm_listing_id == str(listing_id)).first()
                if tm:
                    tm.actual_price = float(new_price)
                    tm.last_synced_at = datetime.now(timezone.utc)
                    session.add(
                        PriceHistory(
                            listing_id=tm.id,
                            price=float(new_price),
                            change_type="STRATEGY",
                            timestamp=datetime.now(timezone.utc),
                        )
                    )
                session.commit()
            finally:
                session.close()
            return

        elif command_type == "WITHDRAW_LISTING":
            self.handle_withdraw(command)
            return

        elif command_type == "SCRAPE_SUPPLIER":
            self.handle_scrape_supplier(command)
            return
        
        elif command_type == "ENRICH_SUPPLIER":
            self.handle_enrich_supplier(command)
            return
        
        elif command_type == "SCRAPE_OC":
            self.handle_scrape_oc(command)
            return

        elif command_type == "SCAN_COMPETITORS":
            self.handle_scan_competitors(command)
            return

        elif command_type == "SYNC_SOLD_ITEMS":
            self.handle_sync_sold_items(command)
            return

        elif command_type == "SYNC_SELLING_ITEMS":
            self.handle_sync_selling_items(command)
            return

        elif command_type == "RESET_ENRICHMENT":
            self.handle_reset_enrichment(command)
            return

        elif command_type == "ONECHEQ_FULL_BACKFILL":
            self.handle_onecheq_full_backfill(command)
            return

        elif command_type == "BACKFILL_IMAGES_ONECHEQ":
            self.handle_backfill_images_onecheq(command)
            return

        elif command_type == "VALIDATE_LAUNCHLOCK":
            self.handle_validate_launchlock(command)
            return

        else:
            raise ValueError(f"Unknown Command Type: {command_type}")
    
    def handle_scrape_oc(self, command):
        """
        Executes OneCheq Scraper sync.
        """
        print(f"   -> Starting SCRAPE_OC Job...")
        from retail_os.scrapers.onecheq.adapter import OneCheqAdapter
        
        # Parse payload
        pages = command.payload.get("items_limit") or command.payload.get("limit_pages", 1) 
        # Note: 'items_limit' might be misnamed if it means pages. Let's assume pages=1 for lite mode.
        if command.payload.get("lite_mode"):
            pages = 1
            
        collection = command.payload.get("collection", "all")
        
        adapter = OneCheqAdapter()
        adapter.run_sync(pages=int(pages), collection=collection)
        print(f"   -> SCRAPE_OC Job Complete.")
    
    def handle_withdraw(self, command):
        payload = command.payload
        listing_id = payload.get("listing_id")
        
        if not listing_id:
            # Maybe look up via internal_id? For now strict.
            raise ValueError("Withdraw requres 'listing_id'")
            
        print(f"   -> Executing Withdraw for {listing_id}...")
        success = self.api.withdraw_listing(str(listing_id))
        if success:
            print("      -> Withdraw SUCCESS.")
        else:
            raise ValueError("Withdraw Failed (False returned)")

    def handle_publish(self, command):
        """
        Implementation of 'golden_path_publish.md' with DRY RUN support
        """
        cmd_type, payload = self.resolve_command(command)
        internal_id = payload.get("internal_product_id")
        dry_run = bool(payload.get("dry_run", False))
        
        logger.info(f"DRY_RUN_PUBLISH_START cmd_id={command.id} internal_product_id={internal_id} dry_run={dry_run}")
        
        session = SessionLocal()
        
        try:
            prod = session.query(InternalProduct).get(internal_id)
            
            if not prod:
                raise ValueError(f"Product {internal_id} not found")

            # Supplier-removed items must never be listed (draft or live).
            sp0 = prod.supplier_product
            if sp0 and str(getattr(sp0, "sync_status", "") or "").upper() == "REMOVED":
                command.status = CommandStatus.HUMAN_REQUIRED
                command.error_code = "REMOVED_FROM_SUPPLIER"
                last_seen = sp0.last_scraped_at.isoformat() if getattr(sp0, "last_scraped_at", None) else None
                command.error_message = f"Removed from supplier (last seen: {last_seen or 'unknown'}). Blocked from listing."
                session.commit()
                raise ValueError(command.error_message)
            
            # --- DRY RUN MODE (Offline Safe) ---
            if dry_run:
                logger.info(f"   -> [DRY RUN] Building authoritative payload for product {internal_id}")

                # DRY_RUN must still respect strict gates (no fake listing-ready output).
                validator = LaunchLock(session)
                try:
                    validator.validate_publish(prod, test_mode=False)
                except Exception as e:
                    # Create a Vault 3 record so operators can see BLOCKED reasons in one place.
                    try:
                        from retail_os.core.database import TradeMeListing
                        import json as _json

                        listing_id = f"DRYRUN-{command.id}"
                        tm_listing = session.query(TradeMeListing).filter_by(
                            internal_product_id=internal_id,
                            tm_listing_id=listing_id
                        ).first()
                        blocked_snapshot = _json.dumps(
                            {
                                "_blocked": True,
                                "top_blocker": str(e),
                                "blockers": [str(e)],
                                "_internal_product_id": internal_id,
                            },
                            ensure_ascii=True,
                        )
                        if not tm_listing:
                            tm_listing = TradeMeListing(
                                internal_product_id=internal_id,
                                tm_listing_id=listing_id,
                                desired_price=None,
                                actual_price=None,
                                actual_state="BLOCKED",
                                payload_snapshot=blocked_snapshot,
                                payload_hash=None,
                                last_synced_at=datetime.now(timezone.utc),
                            )
                            session.add(tm_listing)
                        else:
                            tm_listing.actual_state = "BLOCKED"
                            tm_listing.payload_snapshot = blocked_snapshot
                            tm_listing.payload_hash = None
                            tm_listing.last_synced_at = datetime.now(timezone.utc)
                        session.commit()
                    except Exception as e2:
                        logger.warning(f"   -> [DRY RUN] Could not persist BLOCKED listing: {e2}")

                    # Mark command as needing attention with a clear reason.
                    command.status = CommandStatus.HUMAN_REQUIRED
                    command.error_code = "LAUNCHLOCK_BLOCKED"
                    command.error_message = str(e)[:2000]
                    session.commit()
                    raise ValueError(command.error_message)
                
                # Use authoritative payload builder
                from retail_os.core.listing_builder import build_listing_payload, compute_payload_hash
                import json
                
                try:
                    payload_dict = build_listing_payload(internal_id)
                    payload_json = json.dumps(payload_dict, sort_keys=True)
                    payload_hash = compute_payload_hash(payload_dict)
                    
                    logger.info(f"   -> [DRY RUN] Payload hash: {payload_hash[:16]}...")
                except Exception as e:
                    logger.error(f"   -> [DRY RUN] Payload build failed: {e}")
                    raise

                # Persist DRY_RUN evidence on the command (for later drift checks / bulk approvals)
                try:
                    cmd_row = session.query(SystemCommand).get(command.id)
                    sp = prod.supplier_product
                    if cmd_row and sp:
                        cmd_payload = cmd_row.payload or {}
                        cmd_payload["dry_run_generated_at"] = datetime.now(timezone.utc).isoformat()
                        cmd_payload["supplier_snapshot_hash"] = sp.snapshot_hash
                        cmd_payload["supplier_last_scraped_at"] = (
                            sp.last_scraped_at.isoformat() if sp.last_scraped_at else None
                        )
                        cmd_row.payload = cmd_payload
                        session.commit()
                except Exception as e:
                    logger.warning(f"   -> [DRY RUN] Could not persist snapshot metadata: {e}")
                
                # Create/update Vault3 listing with DRY RUN marker
                listing_id = f"DRYRUN-{command.id}"
                
                tm_listing = session.query(TradeMeListing).filter_by(
                    internal_product_id=internal_id,
                    tm_listing_id=listing_id
                ).first()
                
                if not tm_listing:
                    tm_listing = TradeMeListing(
                        internal_product_id=internal_id,
                        tm_listing_id=listing_id,
                        desired_price=payload_dict.get("StartPrice", 0),
                        actual_price=payload_dict.get("StartPrice", 0),
                        actual_state="DRY_RUN",
                        payload_snapshot=payload_json,
                        payload_hash=payload_hash,
                        last_synced_at=datetime.now(timezone.utc)
                    )
                    session.add(tm_listing)
                else:
                    tm_listing.actual_state = "DRY_RUN"
                    tm_listing.payload_snapshot = payload_json
                    tm_listing.payload_hash = payload_hash
                    tm_listing.last_synced_at = datetime.now(timezone.utc)

                # ListingDraft is the single source-of-truth review object for payloads
                draft = session.query(ListingDraft).filter_by(command_id=command.id).first()
                if not draft:
                    draft = ListingDraft(command_id=command.id, payload_json=payload_dict, validation_results=None)
                    session.add(draft)
                else:
                    draft.payload_json = payload_dict
                
                session.commit()
                
                logger.info(f"DRY_RUN_PUBLISH_END cmd_id={command.id} status=SUCCEEDED listing_id={listing_id} hash={payload_hash[:16]}...")
                session.close()
                return
            
            # --- REAL PUBLISH MODE (Guardrails + Original Logic) ---
            if not self.api:
                raise Exception("API wrapper not available.")

            # Guardrails (store mode, quotas, rate limits, stale-truth checks)
            from retail_os.core.database import SystemSetting

            def _get_setting(key: str, default: dict) -> dict:
                row = session.query(SystemSetting).filter(SystemSetting.key == key).first()
                if not row:
                    return default
                if isinstance(row.value, dict):
                    return {**default, **row.value}
                return default

            store = _get_setting("store.mode", {"mode": "NORMAL"})
            store_mode = str(store.get("mode", "NORMAL")).upper()
            if store_mode in ["PAUSED", "HOLIDAY"]:
                command.status = CommandStatus.HUMAN_REQUIRED
                command.error_code = "PUBLISH_DISABLED_STORE_MODE"
                command.error_message = f"Publishing disabled in store.mode={store_mode}"
                session.commit()
                raise ValueError(command.error_message)

            policy = _get_setting(
                "publishing.policy",
                {
                    "enabled": True,
                    "max_publishes_per_day": 100,
                    "max_publishes_per_minute": 6,
                    "min_account_balance_nzd": 20.0,
                    "require_recent_scrape_minutes": 1440,
                },
            )
            if not bool(policy.get("enabled", True)):
                command.status = CommandStatus.HUMAN_REQUIRED
                command.error_code = "PUBLISH_DISABLED"
                command.error_message = "Publishing disabled by publishing.policy"
                session.commit()
                raise ValueError(command.error_message)

            # Per-supplier policy gate (publish)
            try:
                sp0 = prod.supplier_product
                supplier_id = sp0.supplier_id if sp0 else None
                if supplier_id is not None:
                    row = session.query(SystemSetting).filter(SystemSetting.key == f"supplier.policy.{int(supplier_id)}").first()
                    if row and isinstance(row.value, dict):
                        pol = row.value
                        if pol.get("enabled") is False or pol.get("publish", {}).get("enabled") is False:
                            command.status = CommandStatus.HUMAN_REQUIRED
                            command.error_code = "SUPPLIER_DISABLED"
                            command.error_message = "Supplier policy disables publishing."
                            session.commit()
                            raise ValueError(command.error_message)
            except Exception as e:
                # If policy read fails, do not block publish for that reason.
                logger.warning(f"PUBLISH_POLICY_CHECK_FAILED cmd_id={command.id} err={e}")

            # Stale truth: enforce fresh supplier scrape + (if approved_from_dryrun exists) hash must match
            sp = prod.supplier_product
            if not sp:
                command.status = CommandStatus.HUMAN_REQUIRED
                command.error_code = "MISSING_SUPPLIER_PRODUCT"
                command.error_message = "Cannot publish: InternalProduct has no linked SupplierProduct"
                session.commit()
                raise ValueError(command.error_message)

            require_minutes = int(policy.get("require_recent_scrape_minutes") or 0)
            if require_minutes and sp.last_scraped_at:
                last_scraped = sp.last_scraped_at
                if last_scraped.tzinfo is None:
                    last_scraped = last_scraped.replace(tzinfo=timezone.utc)
                
                age = datetime.now(timezone.utc) - last_scraped
                if age.total_seconds() > (require_minutes * 60):
                    command.status = CommandStatus.HUMAN_REQUIRED
                    command.error_code = "STALE_SUPPLIER_TRUTH"
                    command.error_message = f"Supplier truth too old ({int(age.total_seconds()/60)}m); scrape before publish"
                    session.commit()
                    raise ValueError(command.error_message)

            # If this publish was approved from a DRY_RUN, require snapshot hash match (drift-safe)
            approved_from = (payload or {}).get("approved_from_dryrun")
            if approved_from:
                dr = session.query(SystemCommand).filter(SystemCommand.id == str(approved_from)).first()
                expected_hash = None
                try:
                    expected_hash = (dr.payload or {}).get("supplier_snapshot_hash") if dr else None
                except Exception:
                    expected_hash = None
                if expected_hash and sp.snapshot_hash and str(expected_hash) != str(sp.snapshot_hash):
                    command.status = CommandStatus.HUMAN_REQUIRED
                    command.error_code = "DRYRUN_DRIFT_DETECTED"
                    command.error_message = "Supplier product changed since DRY_RUN approval; regenerate DRY_RUN"
                    session.commit()
                    raise ValueError(command.error_message)

            # Daily quota check (non-dry-run publishes)
            max_per_day = int(policy.get("max_publishes_per_day") or 0)
            if max_per_day:
                from datetime import date

                today = date.today()
                rows = (
                    session.query(SystemCommand)
                    .filter(SystemCommand.type == "PUBLISH_LISTING")
                    .filter(SystemCommand.status == CommandStatus.SUCCEEDED)
                    .filter(SystemCommand.updated_at.isnot(None))
                    .all()
                )
                published_today = 0
                for r in rows:
                    try:
                        if r.updated_at and r.updated_at.date() == today and not bool((r.payload or {}).get("dry_run", False)):
                            published_today += 1
                    except Exception:
                        continue
                if published_today >= max_per_day:
                    command.status = CommandStatus.HUMAN_REQUIRED
                    command.error_code = "PUBLISH_DAILY_QUOTA_REACHED"
                    command.error_message = f"Daily publish quota reached ({published_today}/{max_per_day})"
                    session.commit()
                    raise ValueError(command.error_message)

            # Per-minute rate limit: sleep if we're at/over limit
            max_per_min = int(policy.get("max_publishes_per_minute") or 0)
            if max_per_min:
                window_start = datetime.now(timezone.utc) - timedelta(seconds=60)
                recent = (
                    session.query(SystemCommand)
                    .filter(SystemCommand.type == "PUBLISH_LISTING")
                    .filter(SystemCommand.status == CommandStatus.SUCCEEDED)
                    .filter(SystemCommand.updated_at >= window_start)
                    .all()
                )
                recent_real = 0
                for r in recent:
                    try:
                        if not bool((r.payload or {}).get("dry_run", False)):
                            recent_real += 1
                    except Exception:
                        continue
                if recent_real >= max_per_min:
                    # Simple deterministic backoff to keep TM happy.
                    time.sleep(12)

            # Balance check (preflight) to prevent fee explosions
            min_bal = float(policy.get("min_account_balance_nzd") or 0.0)
            if min_bal > 0:
                try:
                    summary = self.api.get_account_summary()
                    bal = summary.get("account_balance") or summary.get("balance")
                    bal_f = float(bal) if bal is not None else None
                    if bal_f is not None and bal_f < min_bal:
                        command.status = CommandStatus.HUMAN_REQUIRED
                        command.error_code = "INSUFFICIENT_BALANCE"
                        command.error_message = f"Needs top-up. Current Balance: ${bal_f:.2f} (min ${min_bal:.2f})"
                        session.commit()
                        raise ValueError(command.error_message)
                except Exception as e:
                    command.status = CommandStatus.HUMAN_REQUIRED
                    command.error_code = "BALANCE_CHECK_FAILED"
                    command.error_message = f"Blocked: could not fetch Trade Me balance preflight ({e})"
                    session.commit()
                    raise ValueError(command.error_message)
            
            # Phase 1: Pre-Flight (Lock)
            print(f"   -> [Phase 1] Validation for InternalProduct {internal_id}")
            
            validator = LaunchLock(session)
            validator.validate_publish(prod, test_mode=False)
            print(f"   -> [Phase 1] LaunchLock Passed")
            
            # Phase 2: Photos
            photo_ids = []
            photo_path = payload.get("photo_path")
            
            # Auto-Download Logic
            if not photo_path:
                from retail_os.utils.image_downloader import ImageDownloader
                downloader = ImageDownloader()
                # Check local cache first
                verify = downloader.verify_image(prod.sku)
                if verify["exists"]:
                    photo_path = verify["path"]
                    print(f"   -> [Phase 2] Found local image: {photo_path}")
                
                if not photo_path and prod.supplier_product and prod.supplier_product.images:
                    print("   -> [Phase 2] No local image. Downloading from Supplier URLs...")
                    # Try all available images
                    urls = prod.supplier_product.images
                    if isinstance(urls, str): 
                        try: urls = json.loads(urls)
                        except: urls = [urls]
                    
                    for img_url in urls:
                        if not isinstance(img_url, str) or not img_url.startswith("http"):
                            continue
                        print(f"      -> Trying download: {img_url}")
                        res = downloader.download_image(img_url, prod.sku)
                        if res["success"]:
                            photo_path = res["path"]
                            # Update DB
                            current_images = list(prod.supplier_product.images or [])
                            if photo_path not in current_images:
                                current_images.insert(0, photo_path)
                                prod.supplier_product.images = current_images
                                session.commit()
                                session.refresh(prod.supplier_product)
                                session.refresh(prod)
                            break
                        else:
                            print(f"      -> Failed: {res['error']}")
            
            if photo_path and os.path.exists(photo_path):
                print(f"   -> [Phase 2] Uploading Photo: {photo_path}")
                try:
                    with open(photo_path, "rb") as f:
                        img_bytes = f.read()
                    
                    # Idempotency Check (Blueprint Req)
                    img_hash = hashlib.xxhash64(img_bytes).hexdigest() if hasattr(hashlib, 'xxhash64') else hashlib.md5(img_bytes).hexdigest()
                    existing_hash = session.query(PhotoHash).filter_by(hash=img_hash).first()
                    
                    if existing_hash:
                         p_id = existing_hash.tm_photo_id
                         print(f"      -> Photo HIT Cache: {p_id}")
                    else:
                        # Pass DB session for idempotency cache checks (Legacy check inside api? Doing it explicit here)
                        p_id = self.api.upload_photo_idempotent(session, img_bytes, filename="product.jpg")
                        
                        # Save Hash
                        new_hash = PhotoHash(hash=img_hash, tm_photo_id=p_id)
                        session.add(new_hash)
                        session.commit()
                        print(f"      -> Photo ID: {p_id} (Cached)")
                    
                    photo_ids.append(p_id)
                except Exception as e:
                    print(f"      -> Photo Failed: {e}")
                    raise e
            else:
                command.status = CommandStatus.HUMAN_REQUIRED
                command.error_code = "MISSING_IMAGE"
                command.error_message = "Blocked: no downloadable product image available. Scrape must capture images; image download must succeed."
                session.commit()
                raise ValueError(command.error_message)
            
            # Phase 3: Draft & Validate
            # Construct Description
            real_desc = "Listing created by RetailOS."
            if prod.supplier_product:
                # FIX: Prefer Enriched Description!
                if prod.supplier_product.enriched_description:
                    real_desc = prod.supplier_product.enriched_description
                elif prod.supplier_product.description:
                    # Fallback to raw, but Standardize first! (Blueprint Req)
                    raw = prod.supplier_product.description[:1000]
                    real_desc = Standardizer.polish(raw)
                    print("      -> [Standardizer] Applied polish to raw description.")
            
            footer = "\n\n(Automated Listing via RetailOS Pilot)"
            final_desc = real_desc + footer
            
            # --- USE MARKETPLACE ADAPTER (CRITICAL FIX) ---
            # This applies: Pricing Strategy, Category Mapping, Trust Engine, Image Guard
            from retail_os.core.marketplace_adapter import MarketplaceAdapter
            from retail_os.trademe.config import TradeMeConfig
            
            if not prod.supplier_product:
                raise ValueError("Cannot list product without supplier data")
            
            # Get intelligent listing data
            marketplace_data = MarketplaceAdapter.prepare_for_trademe(prod.supplier_product)
            
            # SEO OPTIMIZATION HOOK (Blueprint Req: "Alphabet Audit")
            # Ensure description is SEO optimized if not already
            from retail_os.utils.seo import build_seo_description
            if not prod.supplier_product.enriched_description:
                 # Optional SEO enrichment - disabled for core publish flow
                 # SEO is optional, not needed for validation
                 pass
            
            # Check trust signal
            if marketplace_data["trust_signal"] == "BANNED_IMAGE":
                raise ValueError(f"BLOCKED: {marketplace_data['audit_reason']}")
            
            # Use calculated price (with margins applied)
            # Blueprint Req: Apply Psychological Rounding here explicitly just in case adapter missed it
            listing_price = PricingStrategy.apply_psychological_rounding(marketplace_data["price"])
            cost_price = prod.supplier_product.cost_price
            
            # --- PROFITABILITY CHECK ---
            from retail_os.analysis.profitability import ProfitabilityAnalyzer
            
            profit_check = ProfitabilityAnalyzer.predict_profitability(listing_price, cost_price)
            
            if not profit_check["is_profitable"]:
                raise ValueError(f"UNPROFITABLE LISTING BLOCKED: Net Profit = ${profit_check['net_profit']:.2f}, ROI = {profit_check['roi_percent']:.1f}%")
            
            print(f"   -> Profitability Check: Net Profit ${profit_check['net_profit']:.2f} (ROI {profit_check['roi_percent']:.1f}%)")
            print(f"   -> Trust Signal: {marketplace_data['trust_signal']}")
            print(f"   -> Category: {marketplace_data['category_name']} ({marketplace_data['category_id']})")
            # ---------------------------
            
            tm_payload = {
                "Category": marketplace_data["category_id"],  # Intelligent mapping
                "Title": marketplace_data["title"][:49],  # Cleaned title
                "Description": [marketplace_data["description"]],  # Enriched description
                "Duration": TradeMeConfig.DEFAULT_DURATION,
                "Pickup": TradeMeConfig.PICKUP_OPTION,
                "StartPrice": listing_price,  # Calculated with margins
                "PaymentOptions": TradeMeConfig.get_payment_methods(),
                "ShippingOptions": TradeMeConfig.DEFAULT_SHIPPING,
                "PhotoIds": photo_ids
            }
            
            # Apply Promo Flags if enabled
            if TradeMeConfig.USE_PROMO_FEATURES:
                tm_payload.update(TradeMeConfig.PROMO_FLAGS)
            else:
                # Always default HasGallery to True if images exist, as it's often free/expected
                if photo_ids:
                    tm_payload["HasGallery"] = True
            
        except Exception as e:
            logger.error(f"Error preparing payload: {e}")
            logger.error(traceback.format_exc())
            raise e
        
        print(f"   -> [Phase 3] Validating Draft...")
        val_res = self.api.validate_listing(tm_payload)
        if not val_res.get("Success"):
             raise ValueError(f"Validation Failed: {val_res}")
             
        # --- Phase 4: Execution ---
        print(f"   -> [Phase 4] Executing Write...")
        
        # Capture account balance before publish (SPECTATOR MODE requirement)
        try:
            account_summary = self.api.get_account_summary()
            command.payload["balance_snapshot"] = account_summary
            balance = account_summary.get("account_balance") or 0
            print(f"      -> Account Balance: ${balance}")
        except Exception as e:
            print(f"      -> Warning: Could not fetch balance: {e}")
            account_summary = {"account_balance": None}
        
        try:
            listing_id = self.api.publish_listing(tm_payload)
            print(f"      -> Created Listing ID: {listing_id}")
        except Exception as e:
            error_str = str(e)
            # Check for insufficient balance
            if "Insufficient balance" in error_str or "insufficient" in error_str.lower():
                command.status = CommandStatus.HUMAN_REQUIRED
                command.error_code = "INSUFFICIENT_BALANCE"
                bal = account_summary.get("account_balance", "N/A")
                command.error_message = f"Needs top-up. Current Balance: ${bal}"
                session.commit()
                raise Exception(command.error_message)
            else:
                # Other publish errors
                raise

        
        # SAVE TO DB (Architecture Correctness)
        tm_listing = session.query(TradeMeListing).filter_by(tm_listing_id=str(listing_id)).first()
        if not tm_listing:
            tm_listing = TradeMeListing(
                internal_product_id=internal_id,
                tm_listing_id=str(listing_id),
                desired_price=tm_payload["StartPrice"],
                actual_price=tm_payload["StartPrice"],
                actual_state="Live",
                last_synced_at=datetime.utcnow()
            )
            session.add(tm_listing)
            session.commit()
            print(f"      -> Saved TradeMeListing record for {listing_id}")
        
        # --- Phase 5: Verification ---
        print(f"   -> [Phase 5] Read-Back Verification...")
        details = self.api.get_listing_details(str(listing_id))
        
        # Check Price (Golden Path Spec)
        actual_price = details.get("ParsedPrice", 0.0)
        expected_price = float(tm_payload["StartPrice"])
        
        if abs(actual_price - expected_price) > 0.1:
            print(f"CRITICAL DRIFT: Expected {expected_price}, Got {actual_price}")
        else:
            print("      -> Verification MATCH.")
        
        session.close()
    
    def handle_scrape_supplier(self, command):
        """Handle SCRAPE_SUPPLIER command"""
        cmd_type, payload = self.resolve_command(command)
        supplier_id = payload.get("supplier_id")
        supplier_name = payload.get("supplier_name", f"Supplier {supplier_id}")
        source_category = payload.get("source_category")
        # IMPORTANT: allow pages=0 to mean "unlimited/full backfill".
        pages_raw = payload.get("pages", 1)
        try:
            pages = int(pages_raw) if pages_raw is not None else 1
        except Exception:
            pages = 1
        if pages < 0:
            pages = 0
        
        logger.info(f"SCRAPE_SUPPLIER_START cmd_id={command.id} supplier={supplier_name}")

        # Pilot scope: ONECHEQ only.
        # Noel Leeming is blocked due to robots/image access (403) — do not pretend it works.
        name_l = str(supplier_name).lower()
        if "noel" in name_l or "leeming" in name_l:
            command.status = CommandStatus.HUMAN_REQUIRED
            command.error_code = "SUPPLIER_NOT_SUPPORTED"
            command.error_message = "NOEL_LEEMING is not supported (robots/image access). Use ONECHEQ."
            return
        if "cash" in name_l or "converters" in name_l:
            command.status = CommandStatus.HUMAN_REQUIRED
            command.error_code = "SUPPLIER_NOT_SUPPORTED"
            command.error_message = "CASH_CONVERTERS is out of scope."
            return
        if "onecheq" not in name_l:
            command.status = CommandStatus.HUMAN_REQUIRED
            command.error_code = "SUPPLIER_NOT_SUPPORTED_PILOT"
            command.error_message = f"Pilot scope supports ONECHEQ only (got {supplier_name})."
            return

        # Per-supplier policy gate (DB-backed)
        try:
            pol = None
            if supplier_id is not None:
                s = SessionLocal()
                try:
                    from retail_os.core.database import SystemSetting

                    row = s.query(SystemSetting).filter(SystemSetting.key == f"supplier.policy.{int(supplier_id)}").first()
                    if row and isinstance(row.value, dict):
                        pol = row.value
                finally:
                    s.close()
            if pol and (pol.get("enabled") is False or pol.get("scrape", {}).get("enabled") is False):
                command.status = CommandStatus.HUMAN_REQUIRED
                command.error_code = "SUPPLIER_DISABLED"
                command.error_message = "Supplier policy disables scraping."
                logger.warning(f"SCRAPE_SUPPLIER_BLOCKED cmd_id={command.id} supplier_id={supplier_id} reason=SUPPLIER_DISABLED")
                return
        except Exception:
            # Never block scraping due to policy read errors; logging is best-effort.
            pass
        
        session = SessionLocal()
        try:
            if "onecheq" in supplier_name.lower():
                # Prefer Shopify JSON endpoint for full-catalog scrape (fast + authoritative).
                try:
                    import os
                    mode = (payload.get("onecheq_source") or payload.get("mode") or "json")
                    os.environ["RETAILOS_ONECHEQ_SOURCE"] = str(mode)
                except Exception:
                    pass

                from retail_os.scrapers.onecheq.adapter import OneCheqAdapter
                adapter = OneCheqAdapter()
                
                # Category-scoped scrape: Shopify collection handle
                collection = source_category or payload.get("collection") or "all"

                def _is_cancelled() -> bool:
                    try:
                        with SessionLocal() as s0:
                            row0 = s0.query(SystemCommand).filter(SystemCommand.id == str(command.id)).first()
                            if not row0:
                                return False
                            return row0.status == CommandStatus.CANCELLED
                    except Exception:
                        return False

                def _progress_hook(info: dict) -> None:
                    try:
                        with SessionLocal() as s2:
                            row = s2.query(SystemCommand).filter(SystemCommand.id == str(command.id)).first()
                            if not row:
                                return
                            p = row.payload or {}
                            p["progress"] = {**(p.get("progress") or {}), **(info or {})}
                            p["progress"]["updated_at"] = datetime.now(timezone.utc).isoformat()
                            row.payload = p
                            row.updated_at = datetime.now(timezone.utc)
                            s2.commit()
                    except Exception:
                        return

                adapter.run_sync(
                    pages=pages,
                    collection=collection,
                    cmd_id=str(command.id),
                    progress_every=50,
                    progress_hook=_progress_hook,
                    should_abort=_is_cancelled,
                )

                # If an operator cancelled while the adapter was running, stop cleanly.
                if _is_cancelled():
                    command.status = CommandStatus.CANCELLED
                    command.error_code = "CANCELLED_BY_OPERATOR"
                    command.error_message = "Cancelled by operator during scrape."
                    logger.info(f"SCRAPE_SUPPLIER_CANCELLED cmd_id={command.id} supplier={supplier_name}")
                    return
                
                # Update last_scraped_at for existing products
                from datetime import datetime
                from retail_os.core.database import SupplierProduct
                session.query(SupplierProduct).filter_by(supplier_id=supplier_id).update(
                    {"last_scraped_at": datetime.utcnow()},
                    synchronize_session=False
                )
                session.commit()
                
                logger.info(f"SCRAPE_SUPPLIER_END cmd_id={command.id} supplier={supplier_name} status=SUCCEEDED")
            else:
                # Should be unreachable due to scope guard above.
                command.status = CommandStatus.HUMAN_REQUIRED
                command.error_code = "SUPPLIER_NOT_SUPPORTED_PILOT"
                command.error_message = f"Pilot scope supports ONECHEQ only (got {supplier_name})."
                return
        except Exception as e:
            logger.error(f"SCRAPE_SUPPLIER_FAILED cmd_id={command.id} error={e}")
            session.rollback()
            raise
        finally:
            session.close()

    def handle_onecheq_full_backfill(self, command):
        """
        One-click OneCheq full backfill:
        - Scrape full catalog (pages=0, collection=all, JSON mode)
        - Backfill local images (loop until done)
        - Enrich all pending (loop until done)
        - Validate LaunchLock (default first 1000; configurable)
        """
        cmd_type, payload = self.resolve_command(command)
        supplier_id = int(payload.get("supplier_id") or 0) if payload.get("supplier_id") is not None else None
        supplier_name = payload.get("supplier_name") or "ONECHEQ"
        validate_n = payload.get("validate_n", 1000)
        validate_all = bool(payload.get("validate_all", False))
        image_batch = int(payload.get("image_batch", 5000) or 5000)
        image_concurrency = int(payload.get("image_concurrency", 24) or 24)
        image_loop_max = int(payload.get("image_loop_max", 50) or 50)
        image_loop_seconds = float(payload.get("image_loop_seconds", 600) or 600)
        enrich_batch_size = int(payload.get("enrich_batch_size", 5000) or 5000)

        logger.info(
            "ONECHEQ_FULL_BACKFILL_START cmd_id=%s supplier=%s supplier_id=%s validate_n=%s validate_all=%s",
            command.id,
            supplier_name,
            supplier_id,
            validate_n,
            validate_all,
        )

        from retail_os.core.database import JobStatus, Supplier, SupplierProduct
        from retail_os.scrapers.onecheq.adapter import OneCheqAdapter
        from scripts.enrich_products import enrich_batch
        from retail_os.core.backfill import backfill_supplier_images_onecheq, validate_launchlock

        # Resolve supplier_id if missing
        with SessionLocal() as s:
            sup = None
            if supplier_id:
                sup = s.query(Supplier).filter(Supplier.id == int(supplier_id)).first()
            if not sup:
                sup = s.query(Supplier).filter(Supplier.name == "ONECHEQ").first()
            if not sup:
                sup = Supplier(name="ONECHEQ", base_url="https://onecheq.co.nz", is_active=True)
                s.add(sup)
                s.commit()
            supplier_id = int(sup.id)

        job_row_id = None
        with SessionLocal() as s:
            job = JobStatus(
                job_type="ONECHEQ_FULL_BACKFILL",
                status="RUNNING",
                start_time=datetime.utcnow(),
                items_processed=0,
                summary=None,
            )
            s.add(job)
            s.commit()
            job_row_id = job.id

        summary: dict[str, Any] = {"phases": [], "supplier_id": supplier_id}
        t0 = time.perf_counter()

        # Phase 1: Scrape full catalog
        try:
            import os as _os
            _os.environ["RETAILOS_ONECHEQ_SOURCE"] = str(payload.get("onecheq_source") or "json")
        except Exception:
            pass

        t_scrape = time.perf_counter()
        OneCheqAdapter().run_sync(pages=0, collection="all")
        scrape_s = time.perf_counter() - t_scrape
        with SessionLocal() as s:
            total = s.query(SupplierProduct).filter(SupplierProduct.supplier_id == supplier_id).count()
        summary["phases"].append({"name": "scrape_full", "seconds": round(scrape_s, 3), "supplier_products_total": total})

        # Phase 2: Backfill images until done (or loop cap)
        t_img = time.perf_counter()
        img_stats = {"loops": 0, "downloaded_ok": 0, "downloaded_failed": 0, "remaining_without_local_images": None, "top_failures": []}
        for _ in range(image_loop_max):
            img_stats["loops"] += 1
            with SessionLocal() as s:
                step = backfill_supplier_images_onecheq(
                    session=s,
                    supplier_id=supplier_id,
                    batch=image_batch,
                    concurrency=image_concurrency,
                    max_seconds=image_loop_seconds,
                )
            img_stats["downloaded_ok"] += int(step.get("downloaded_ok") or 0)
            img_stats["downloaded_failed"] += int(step.get("downloaded_failed") or 0)
            img_stats["remaining_without_local_images"] = step.get("remaining_without_local_images")
            # Merge failures (best-effort)
            img_stats["top_failures"] = step.get("top_failures") or img_stats["top_failures"]
            if step.get("remaining_without_local_images") == 0:
                break
            if step.get("candidates_queued") == 0:
                break
        summary["phases"].append({"name": "backfill_images", "seconds": round(time.perf_counter() - t_img, 3), **img_stats})

        # Phase 3: Enrich all (loop batches until none pending)
        t_enrich = time.perf_counter()
        enriched_total = 0
        enrich_loops = 0
        while True:
            with SessionLocal() as s:
                pending = (
                    s.query(SupplierProduct)
                    .filter(SupplierProduct.supplier_id == supplier_id)
                    .filter(SupplierProduct.enrichment_status == "PENDING")
                    .filter(SupplierProduct.cost_price > 0)
                    .count()
                )
            if pending <= 0:
                break
            enrich_loops += 1
            enrich_batch(batch_size=enrich_batch_size, delay_seconds=0, supplier_id=supplier_id, source_category=None)
            enriched_total += min(pending, enrich_batch_size)
            if enrich_loops >= 500:
                break
        summary["phases"].append(
            {
                "name": "enrich_all",
                "seconds": round(time.perf_counter() - t_enrich, 3),
                "loops": enrich_loops,
                "approx_items_processed": enriched_total,
            }
        )

        # Phase 4: Validate LaunchLock
        t_val = time.perf_counter()
        limit = None if validate_all else (int(validate_n) if validate_n is not None else 1000)
        with SessionLocal() as s:
            val = validate_launchlock(session=s, supplier_id=supplier_id, limit=limit)
        summary["phases"].append({"name": "launchlock_validate", "seconds": round(time.perf_counter() - t_val, 3), **val})

        summary["total_seconds"] = round(time.perf_counter() - t0, 3)

        with SessionLocal() as s:
            job = s.query(JobStatus).get(job_row_id) if job_row_id is not None else None
            if job:
                job.status = "COMPLETED"
                job.end_time = datetime.utcnow()
                job.items_processed = total
                job.summary = json.dumps(summary, ensure_ascii=True)
            s.commit()

        logger.info("ONECHEQ_FULL_BACKFILL_END cmd_id=%s status=SUCCEEDED", command.id)

    def handle_backfill_images_onecheq(self, command):
        cmd_type, payload = self.resolve_command(command)
        supplier_id = int(payload.get("supplier_id") or 0) if payload.get("supplier_id") is not None else None
        batch = int(payload.get("batch", 5000) or 5000)
        concurrency = int(payload.get("concurrency", 16) or 16)
        max_seconds = float(payload.get("max_seconds", 600) or 600)

        from retail_os.core.database import JobStatus, Supplier
        from retail_os.core.backfill import backfill_supplier_images_onecheq

        with SessionLocal() as s:
            sup = None
            if supplier_id:
                sup = s.query(Supplier).filter(Supplier.id == int(supplier_id)).first()
            if not sup:
                sup = s.query(Supplier).filter(Supplier.name == "ONECHEQ").first()
            if not sup:
                raise ValueError("ONECHEQ supplier missing")
            supplier_id = int(sup.id)

        job_row_id = None
        with SessionLocal() as s:
            job = JobStatus(job_type="BACKFILL_IMAGES_ONECHEQ", status="RUNNING", start_time=datetime.utcnow(), summary=None)
            s.add(job)
            s.commit()
            job_row_id = job.id

        with SessionLocal() as s:
            res = backfill_supplier_images_onecheq(
                session=s,
                supplier_id=supplier_id,
                batch=batch,
                concurrency=concurrency,
                max_seconds=max_seconds,
            )

        with SessionLocal() as s:
            job = s.query(JobStatus).get(job_row_id) if job_row_id is not None else None
            if job:
                job.status = "COMPLETED"
                job.end_time = datetime.utcnow()
                job.summary = json.dumps(res, ensure_ascii=True)
            s.commit()

    def handle_validate_launchlock(self, command):
        cmd_type, payload = self.resolve_command(command)
        supplier_id = int(payload.get("supplier_id") or 0) if payload.get("supplier_id") is not None else None
        limit = payload.get("limit", 1000)
        validate_all = bool(payload.get("validate_all", False))
        if validate_all or (isinstance(limit, str) and limit.upper() == "ALL"):
            limit = None
        try:
            if limit is not None:
                limit = int(limit)
        except Exception:
            limit = 1000

        from retail_os.core.database import JobStatus, Supplier
        from retail_os.core.backfill import validate_launchlock

        with SessionLocal() as s:
            sup = None
            if supplier_id:
                sup = s.query(Supplier).filter(Supplier.id == int(supplier_id)).first()
            if not sup:
                # best-effort; validate is typically run per supplier
                sup = s.query(Supplier).filter(Supplier.name == "ONECHEQ").first()
            if not sup:
                raise ValueError("Supplier not found for validation")
            supplier_id = int(sup.id)

        job_row_id = None
        with SessionLocal() as s:
            job = JobStatus(job_type="VALIDATE_LAUNCHLOCK", status="RUNNING", start_time=datetime.utcnow(), summary=None)
            s.add(job)
            s.commit()
            job_row_id = job.id

        with SessionLocal() as s:
            res = validate_launchlock(session=s, supplier_id=supplier_id, limit=limit)

        with SessionLocal() as s:
            job = s.query(JobStatus).get(job_row_id) if job_row_id is not None else None
            if job:
                job.status = "COMPLETED"
                job.end_time = datetime.utcnow()
                job.summary = json.dumps(res, ensure_ascii=True)
            s.commit()
    
    def handle_enrich_supplier(self, command):
        """Handle ENRICH_SUPPLIER command"""
        cmd_type, payload = self.resolve_command(command)
        supplier_id = payload.get("supplier_id")
        supplier_name = payload.get("supplier_name", f"Supplier {supplier_id}")
        source_category = payload.get("source_category")

        batch_size = int(payload.get("batch_size", 25))
        delay_seconds = int(payload.get("delay_seconds", 0))
        create_internal_products = bool(payload.get("create_internal_products", True))

        logger.info(
            "ENRICH_SUPPLIER_START cmd_id=%s supplier=%s supplier_id=%s source_category=%s batch_size=%s delay_seconds=%s",
            command.id,
            supplier_name,
            supplier_id,
            source_category,
            batch_size,
            delay_seconds,
        )

        # Pilot scope: ONECHEQ only.
        name_l = str(supplier_name).lower()
        if "noel" in name_l or "leeming" in name_l:
            command.status = CommandStatus.HUMAN_REQUIRED
            command.error_code = "SUPPLIER_NOT_SUPPORTED"
            command.error_message = "NOEL_LEEMING is not supported (robots/image access)."
            return
        if "cash" in name_l or "converters" in name_l:
            command.status = CommandStatus.HUMAN_REQUIRED
            command.error_code = "SUPPLIER_NOT_SUPPORTED"
            command.error_message = "CASH_CONVERTERS is out of scope."
            return
        if "onecheq" not in name_l:
            command.status = CommandStatus.HUMAN_REQUIRED
            command.error_code = "SUPPLIER_NOT_SUPPORTED_PILOT"
            command.error_message = f"Pilot scope supports ONECHEQ only (got {supplier_name})."
            return

        # Per-supplier policy gate (DB-backed)
        try:
            pol = None
            if supplier_id is not None:
                s = SessionLocal()
                try:
                    from retail_os.core.database import SystemSetting

                    row = s.query(SystemSetting).filter(SystemSetting.key == f"supplier.policy.{int(supplier_id)}").first()
                    if row and isinstance(row.value, dict):
                        pol = row.value
                finally:
                    s.close()
            if pol and (pol.get("enabled") is False or pol.get("enrich", {}).get("enabled") is False):
                command.status = CommandStatus.HUMAN_REQUIRED
                command.error_code = "SUPPLIER_DISABLED"
                command.error_message = "Supplier policy disables enrichment."
                logger.warning(f"ENRICH_SUPPLIER_BLOCKED cmd_id={command.id} supplier_id={supplier_id} reason=SUPPLIER_DISABLED")
                return
        except Exception:
            pass

        # 1) Ensure InternalProducts exist (needed for publish pipeline).
        session = SessionLocal()
        created_internal = 0
        try:
            if create_internal_products and supplier_id is not None:
                from retail_os.core.database import SupplierProduct, InternalProduct

                # Pilot scope: only ONECHEQ is supported.
                prefix = "OC" if "onecheq" in supplier_name.lower() else "INT"

                q = session.query(SupplierProduct).filter(SupplierProduct.supplier_id == int(supplier_id))
                if source_category:
                    q = q.filter(SupplierProduct.source_category == source_category)

                for sp in q.all():
                    existing = session.query(InternalProduct).filter_by(primary_supplier_product_id=sp.id).first()
                    if existing:
                        continue

                    my_sku = f"{prefix}-{sp.external_sku}"
                    session.add(
                        InternalProduct(
                            sku=my_sku,
                            title=sp.title,
                            primary_supplier_product_id=sp.id,
                        )
                    )
                    created_internal += 1

                session.commit()
        except Exception as e:
            logger.warning(
                "ENRICH_SUPPLIER internal_product_bootstrap_failed cmd_id=%s supplier=%s error=%s",
                command.id,
                supplier_name,
                e,
            )
            session.rollback()
        finally:
            session.close()

        # 2) Run actual enrichment batch (writes SupplierProduct.enriched_* and enrichment_status)
        # This reuses the existing worker script logic so UI/API commands are first-class.
        from scripts.enrich_products import enrich_batch

        from retail_os.core.database import JobStatus

        job_row_id = None
        with SessionLocal() as s:
            job = JobStatus(
                job_type="ENRICH_SUPPLIER",
                status="RUNNING",
                start_time=datetime.utcnow(),
                items_processed=0,
                items_created=created_internal,
                summary=None,
            )
            s.add(job)
            s.commit()
            job_row_id = job.id

        try:
            enrich_batch(
                batch_size=batch_size,
                delay_seconds=delay_seconds,
                supplier_id=int(supplier_id) if supplier_id is not None else None,
                source_category=source_category,
            )
            with SessionLocal() as s:
                job = s.query(JobStatus).get(job_row_id) if job_row_id is not None else None
                if job:
                    job.status = "COMPLETED"
                    job.end_time = datetime.utcnow()
                s.commit()

            logger.info(
                "ENRICH_SUPPLIER_END cmd_id=%s supplier=%s created_internal=%s status=SUCCEEDED",
                command.id,
                supplier_name,
                created_internal,
            )
        except Exception as e:
            logger.error("ENRICH_SUPPLIER_FAILED cmd_id=%s supplier=%s error=%s", command.id, supplier_name, e)
            with SessionLocal() as s:
                job = s.query(JobStatus).get(job_row_id) if job_row_id is not None else None
                if job:
                    job.status = "FAILED"
                    job.end_time = datetime.utcnow()
                    job.summary = str(e)[:2000]
                s.commit()
            raise

    def handle_scan_competitors(self, command):
        """
        Creates an auditable market-price snapshot for a listing/product and (optionally)
        enqueues a price update recommendation.
        """
        command.status = CommandStatus.HUMAN_REQUIRED
        command.error_code = "COMPETITOR_SCAN_DISABLED"
        command.error_message = "Competitor scanning is disabled for pilot."
        # Persist and stop.
        s = SessionLocal()
        try:
            row = s.query(SystemCommand).get(command.id)
            if row:
                row.status = command.status
                row.error_code = command.error_code
                row.error_message = command.error_message
                row.updated_at = datetime.now(timezone.utc)
                s.commit()
        finally:
            s.close()
        raise ValueError(command.error_message)

    def handle_sync_sold_items(self, command):
        """
        Pulls sold items/orders from Trade Me and upserts Orders.
        This is fulfillment-critical and should run frequently.
        """
        from retail_os.core.database import JobStatus

        job_row_id = None
        with SessionLocal() as s:
            job = JobStatus(
                job_type="SYNC_SOLD_ITEMS",
                status="RUNNING",
                start_time=datetime.utcnow(),
                items_processed=0,
                items_created=0,
                items_updated=0,
                items_failed=0,
                summary=None,
            )
            s.add(job)
            s.commit()
            job_row_id = job.id

        try:
            from retail_os.core.sync_sold_items import SoldItemSyncer

            syncer = SoldItemSyncer()
            new_orders = syncer.sync_recent_sales()

            with SessionLocal() as s:
                job = s.query(JobStatus).get(job_row_id) if job_row_id is not None else None
                if job:
                    job.status = "COMPLETED"
                    job.end_time = datetime.utcnow()
                    job.items_processed = int(new_orders or 0)
                    job.items_created = int(new_orders or 0)
                    job.summary = f"new_orders={int(new_orders or 0)}"
                s.commit()
        except Exception as e:
            # If credentials are missing or TM is down, make this visible (but don't crash worker loop).
            err = str(e)
            if "Credentials missing" in err or "missing in Environment" in err:
                command.status = CommandStatus.HUMAN_REQUIRED
                command.error_code = "MISSING_CREDS"
                command.error_message = "Trade Me credentials missing for sold-item sync"

            with SessionLocal() as s:
                job = s.query(JobStatus).get(job_row_id) if job_row_id is not None else None
                if job:
                    job.status = "FAILED"
                    job.end_time = datetime.utcnow()
                    job.items_failed = 1
                    job.summary = err[:2000]
                s.commit()
            raise

    def handle_sync_selling_items(self, command):
        """
        Pulls currently-selling items from Trade Me and updates local listing truth.
        Captures ListingMetricSnapshot for velocity calculations.
        """
        from retail_os.core.database import JobStatus

        if not self.api:
            raise Exception("API wrapper not available.")

        cmd_type, payload = self.resolve_command(command)
        limit = int(payload.get("limit", 50) or 50)

        job_row_id = None
        with SessionLocal() as s:
            job = JobStatus(
                job_type="SYNC_SELLING_ITEMS",
                status="RUNNING",
                start_time=datetime.utcnow(),
                items_processed=0,
                items_updated=0,
                items_failed=0,
                summary=None,
            )
            s.add(job)
            s.commit()
            job_row_id = job.id

        updated = 0
        failed = 0

        session = SessionLocal()
        try:
            from retail_os.core.database import TradeMeListing, ListingMetricSnapshot, AuditLog

            selling = self.api.get_all_selling_items()
            selling_ids = [str(i.get("ListingId")) for i in selling if i.get("ListingId") is not None][:limit]

            for tm_id in selling_ids:
                try:
                    details = self.api.get_listing_details(tm_id)
                    if not details:
                        continue

                    tm = session.query(TradeMeListing).filter(TradeMeListing.tm_listing_id == str(tm_id)).first()
                    if not tm:
                        # Not ours (or not yet in DB) - record audit and continue
                        session.add(
                            AuditLog(
                                entity_type="TradeMeListing",
                                entity_id=str(tm_id),
                                action="SELLING_SYNC_MISSING_LOCAL",
                                old_value=None,
                                new_value=str(details)[:2000],
                                user="SellingSyncer",
                                timestamp=datetime.now(timezone.utc),
                            )
                        )
                        session.commit()
                        continue

                    # Update local truth
                    tm.actual_state = "Live"
                    tm.category_id = details.get("Category")
                    tm.view_count = details.get("ViewCount", tm.view_count or 0)
                    tm.watch_count = details.get("WatchCount", tm.watch_count or 0)
                    parsed_price = details.get("ParsedPrice")
                    if parsed_price is not None:
                        tm.actual_price = float(parsed_price)
                    tm.last_synced_at = datetime.now(timezone.utc)

                    # Snapshot metrics
                    session.add(
                        ListingMetricSnapshot(
                            listing_id=tm.id,
                            captured_at=datetime.now(timezone.utc),
                            view_count=tm.view_count,
                            watch_count=tm.watch_count,
                            is_sold=False,
                        )
                    )
                    session.commit()
                    updated += 1
                except Exception as e:
                    failed += 1
                    session.rollback()

            if job_row_id is not None:
                with SessionLocal() as s:
                    job = s.query(JobStatus).get(job_row_id)
                    if job:
                        job.status = "COMPLETED"
                        job.end_time = datetime.utcnow()
                        job.items_processed = len(selling_ids)
                        job.items_updated = updated
                        job.items_failed = failed
                        job.summary = f"selling_ids={len(selling_ids)} updated={updated} failed={failed}"
                    s.commit()
        except Exception as e:
            if job_row_id is not None:
                with SessionLocal() as s:
                    job = s.query(JobStatus).get(job_row_id)
                    if job:
                        job.status = "FAILED"
                        job.end_time = datetime.utcnow()
                        job.items_failed = 1
                        job.summary = str(e)[:2000]
                    s.commit()
            raise
        finally:
            session.close()

    def handle_reset_enrichment(self, command):
        """
        Marks a SupplierProduct back to PENDING enrichment and clears enriched fields.
        This is the operator's "requeue" button.
        """
        cmd_type, payload = self.resolve_command(command)
        sp_id = payload.get("supplier_product_id")
        if sp_id is None:
            raise ValueError("RESET_ENRICHMENT requires supplier_product_id")

        session = SessionLocal()
        try:
            from retail_os.core.database import SupplierProduct, AuditLog

            sp = session.query(SupplierProduct).get(int(sp_id))
            if not sp:
                raise ValueError("SupplierProduct not found")

            old = {
                "enrichment_status": sp.enrichment_status,
                "enriched_title": sp.enriched_title,
                "enriched_description_present": bool(sp.enriched_description),
            }

            sp.enrichment_status = "PENDING"
            sp.enrichment_error = None
            sp.enriched_title = None
            sp.enriched_description = None

            session.add(
                AuditLog(
                    entity_type="SupplierProduct",
                    entity_id=str(sp.id),
                    action="ENRICHMENT_RESET",
                    old_value=str(old),
                    new_value="PENDING",
                    user="Operator",
                    timestamp=datetime.utcnow(),
                )
            )
            session.commit()
        finally:
            session.close()

# --- MAIN ENTRY POINT ---
if __name__ == "__main__":
    worker = CommandWorker()
    worker.run()
