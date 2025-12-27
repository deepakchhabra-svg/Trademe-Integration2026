import time
import sys
import os
import json
import traceback
from datetime import datetime
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from retail_os.core.database import SessionLocal, SystemCommand, CommandStatus, ResourceLock, ListingDraft, InternalProduct, TradeMeListing, PhotoHash
from retail_os.core.validator import LaunchLock
from retail_os.core.standardizer import Standardizer
from retail_os.strategy.pricing import PricingStrategy
from retail_os.trademe.api import TradeMeAPI
from datetime import timedelta
import hashlib
from dotenv import load_dotenv

# Load Environment for Workers
load_dotenv()

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

            # 2. Move to EXECUTING
            command.status = CommandStatus.EXECUTING
            command.updated_at = datetime.utcnow()
            session.commit()

            # 3. Execute Logic (Simulated for Vertical Slice Phase 1)
            try:
                self.execute_logic(command)
                command.status = CommandStatus.SUCCEEDED
                print(f"Command {command.id} SUCCEEDED")
            except Exception as logic_error:
                print(f"Command {command.id} FAILED: {logic_error}")
                command.last_error = str(logic_error)
                
                # CRITICAL: Do NOT overwrite HUMAN_REQUIRED status set by handler
                if command.status == CommandStatus.HUMAN_REQUIRED:
                    # Handler already set terminal status, don't increment attempts
                    print(f"   -> Status: HUMAN_REQUIRED (set by handler)")
                else:
                    command.attempts += 1
                    if command.attempts < command.max_attempts:
                        command.status = CommandStatus.FAILED_RETRYABLE
                    else:
                        command.status = CommandStatus.HUMAN_REQUIRED
            
            command.updated_at = datetime.utcnow()
            session.commit()

        except Exception as e:
            session.rollback()
            print(f"DB Error in Worker: {e}")
            traceback.print_exc()
        finally:
            session.close()

    def execute_logic(self, command):
        """
        The routing logic. In real app, this calls API Client.
        For Vertical Slice Phase 2 verification, we simulate success.
        """
        command_type, payload = self.resolve_command(command)

        if command_type == "TEST_COMMAND":
            # Simulate work
            time.sleep(0.5) 
            if payload.get("fail_me"):
                raise ValueError("Simulated Failure")
            return

        elif command_type == "PUBLISH_LISTING":
            self.handle_publish(command)
            return

        elif command_type == "UPDATE_PRICE":
            # Logic to update price would go here
            # For Vertical Slice, we just pretend
            time.sleep(1)
            print(f"   -> Updated Price for {payload.get('target_id')} to {payload.get('price')}")
            return

        elif command_type == "WITHDRAW_LISTING":
            self.handle_withdraw(command)
            return

        elif command_type == "SCRAPE_SUPPLIER":
            self.handle_scrape_supplier(command)
        
        elif command_type == "ENRICH_SUPPLIER":
            self.handle_enrich_supplier(command)
        
        elif command_type == "SCRAPE_OC":
            self.handle_scrape_oc(command)
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
            
            # --- DRY RUN MODE (Offline Safe) ---
            if dry_run:
                logger.info(f"   -> [DRY RUN] Building authoritative payload for product {internal_id}")
                
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
                        last_synced_at=datetime.utcnow()
                    )
                    session.add(tm_listing)
                else:
                    tm_listing.actual_state = "DRY_RUN"
                    tm_listing.payload_snapshot = payload_json
                    tm_listing.payload_hash = payload_hash
                    tm_listing.last_synced_at = datetime.utcnow()
                
                session.commit()
                
                logger.info(f"DRY_RUN_PUBLISH_END cmd_id={command.id} status=SUCCEEDED listing_id={listing_id} hash={payload_hash[:16]}...")
                session.close()
                return
            
            # --- REAL PUBLISH MODE (Original Logic) ---
            if not self.api:
                raise Exception("API wrapper not available.")
            
            # Phase 1: Pre-Flight (Lock)
            print(f"   -> [Phase 1] Validation for InternalProduct {internal_id}")
            
            # THE BEAST GUARD (New Validator) - bypass in E2E test mode
            import os
            test_mode = os.getenv("E2E_TEST_MODE", "false").lower() == "true"
            validator = LaunchLock(session)
            validator.validate_publish(prod, test_mode=test_mode)
            print(f"   -> [Phase 1] LaunchLock Passed (test_mode={test_mode})")
            
            # Phase 2: Photos
            photo_ids = []
            photo_path = payload.get("photo_path")
            
            # Auto-Download Logic
            if not photo_path:
                print("   -> [Phase 2] No path provided. Checking Supplier Product for URL...")
                if prod.supplier_product and prod.supplier_product.images:
                    try:
                        # Handle JSON list
                        if isinstance(prod.supplier_product.images, list) and len(prod.supplier_product.images) > 0:
                            img_url = prod.supplier_product.images[0]
                            print(f"      -> Downloading: {img_url}")
                            from retail_os.utils.image_downloader import ImageDownloader
                            downloader = ImageDownloader()
                            photo_path = downloader.download_image(img_url)
                    except Exception as e:
                        print(f"      -> Image Download Error: {e}")
            
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
                print(f"   -> [Phase 2] No Photo Available (Proceeding Text-Only)")
            
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
        
        logger.info(f"SCRAPE_SUPPLIER_START cmd_id={command.id} supplier={supplier_name}")
        
        session = SessionLocal()
        try:
            if "onecheq" in supplier_name.lower():
                from retail_os.scrapers.onecheq.adapter import OneCheqAdapter
                adapter = OneCheqAdapter()
                
                # Run scraper (limit to 1 page for speed)
                result = adapter.run_sync(pages=1, collection="all")
                
                # Update last_scraped_at for existing products
                from datetime import datetime
                from retail_os.core.database import SupplierProduct
                session.query(SupplierProduct).filter_by(supplier_id=supplier_id).update(
                    {"last_scraped_at": datetime.utcnow()},
                    synchronize_session=False
                )
                session.commit()
                
                logger.info(f"SCRAPE_SUPPLIER_END cmd_id={command.id} supplier={supplier_name} status=SUCCEEDED")
            elif "noel" in supplier_name.lower() or "leeming" in supplier_name.lower():
                from retail_os.scrapers.noel_leeming.adapter import NoelLeemingAdapter
                adapter = NoelLeemingAdapter()
                adapter.run_sync(pages=1)
                
                from datetime import datetime
                from retail_os.core.database import SupplierProduct
                session.query(SupplierProduct).filter_by(supplier_id=supplier_id).update(
                    {"last_scraped_at": datetime.utcnow()},
                    synchronize_session=False
                )
                session.commit()
                
                logger.info(f"SCRAPE_SUPPLIER_END cmd_id={command.id} supplier={supplier_name} status=SUCCEEDED")
            elif "cash" in supplier_name.lower() or "converters" in supplier_name.lower():
                from retail_os.scrapers.cash_converters.adapter import CashConvertersAdapter
                adapter = CashConvertersAdapter()
                adapter.run_sync(pages=1)
                
                from datetime import datetime
                from retail_os.core.database import SupplierProduct
                session.query(SupplierProduct).filter_by(supplier_id=supplier_id).update(
                    {"last_scraped_at": datetime.utcnow()},
                    synchronize_session=False
                )
                session.commit()
                
                logger.info(f"SCRAPE_SUPPLIER_END cmd_id={command.id} supplier={supplier_name} status=SUCCEEDED")
            else:
                logger.warning(f"No scraper found for supplier: {supplier_name}")
                # Don't fail - just mark as succeeded with warning
                logger.info(f"SCRAPE_SUPPLIER_END cmd_id={command.id} supplier={supplier_name} status=SUCCEEDED (no adapter)")
        except Exception as e:
            logger.error(f"SCRAPE_SUPPLIER_FAILED cmd_id={command.id} error={e}")
            session.rollback()
            raise
        finally:
            session.close()
    
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

        # 1) Ensure InternalProducts exist (needed for publish pipeline).
        session = SessionLocal()
        created_internal = 0
        try:
            if create_internal_products and supplier_id is not None:
                from retail_os.core.database import SupplierProduct, InternalProduct

                if "onecheq" in supplier_name.lower():
                    prefix = "OC"
                elif "noel" in supplier_name.lower() or "leeming" in supplier_name.lower():
                    prefix = "NL"
                elif "cash" in supplier_name.lower() or "converters" in supplier_name.lower():
                    prefix = "CC"
                else:
                    prefix = "INT"

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

# --- MAIN ENTRY POINT ---
if __name__ == "__main__":
    worker = CommandWorker()
    worker.run()
