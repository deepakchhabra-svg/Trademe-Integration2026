"""
Scheduler with auto-enqueue and DB persistence for Spectator Mode.
"""
import os
import json
import time
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from retail_os.core.database import (
    SessionLocal,
    SystemCommand,
    CommandStatus,
    Supplier,
    SupplierProduct,
    JobStatus,
    SystemSetting,
)
import uuid

# Setup logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/scheduler.log', encoding='utf-8', errors='replace'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SpectatorScheduler:
    """Auto-enqueue scheduler for Spectator Mode"""
    
    def __init__(self, dev_mode=True):
        self.scheduler = BackgroundScheduler()
        self.dev_mode = dev_mode
        self.interval_minutes = 1 if dev_mode else 60  # default; can be overridden by DB setting

    def _get_setting(self, session, key: str, default: dict):
        row = session.query(SystemSetting).filter(SystemSetting.key == key).first()
        if not row:
            return default
        if isinstance(row.value, dict):
            return {**default, **row.value}
        return default

    def _enqueue_jobstatus(self, session, job_type: str) -> JobStatus:
        job = JobStatus(
            job_type=job_type,
            status="RUNNING",
            start_time=datetime.utcnow(),
            end_time=None,
            items_processed=0,
            items_created=0,
            items_updated=0,
            items_deleted=0,
            items_failed=0,
            summary=None,
        )
        session.add(job)
        session.commit()
        return job

    def _finish_jobstatus(self, session, job_id: int, status: str, summary: dict):
        job = session.query(JobStatus).get(job_id)
        if not job:
            return
        job.status = status
        job.end_time = datetime.utcnow()
        job.summary = json.dumps(summary, sort_keys=True)
        session.commit()
        
    def scrape_job(self):
        """Auto-enqueue scrape for all suppliers"""
        session = SessionLocal()
        try:
            store_mode = self._get_setting(session, "store.mode", {"mode": "NORMAL"})
            mode = str(store_mode.get("mode", "NORMAL")).upper()
            cfg = self._get_setting(
                session,
                "scheduler.scrape",
                {
                    "enabled": True,
                    "interval_minutes": self.interval_minutes,
                    "priority": 50,
                    "per_category": False,
                    "max_categories_per_supplier": 200,
                    "batch_size": 1,
                },
            )
            self.interval_minutes = int(cfg.get("interval_minutes") or self.interval_minutes)
            # Seasonality / holiday throttling
            if mode in ["HOLIDAY", "PAUSED"]:
                cfg["enabled"] = False
            elif mode in ["SLOW"]:
                cfg["interval_minutes"] = max(int(cfg.get("interval_minutes") or self.interval_minutes), 240)
            if not cfg.get("enabled", True):
                logger.info(f"SCHEDULER: scrape_job disabled (store_mode={mode})")
                return

            suppliers = session.query(Supplier).all()
            logger.info(f"SCHEDULER: Running scrape job for {len(suppliers)} suppliers")

            job = self._enqueue_jobstatus(session, "SCHEDULER_SCRAPE")
            enqueued = 0
            by_supplier = {}
            
            for supplier in suppliers:
                if cfg.get("per_category"):
                    cats = (
                        session.query(SupplierProduct.source_category)
                        .filter(SupplierProduct.supplier_id == supplier.id)
                        .filter(SupplierProduct.source_category.isnot(None))
                        .distinct()
                        .limit(int(cfg.get("max_categories_per_supplier", 200)))
                        .all()
                    )
                    for (cat,) in cats:
                        cmd_id = str(uuid.uuid4())
                        cmd = SystemCommand(
                            id=cmd_id,
                            type="SCRAPE_SUPPLIER",
                            payload={
                                "supplier_id": supplier.id,
                                "supplier_name": supplier.name,
                                "source_category": cat,
                                "pages": int(cfg.get("batch_size", 1)),
                            },
                            status=CommandStatus.PENDING,
                            priority=int(cfg.get("priority", 50)),
                        )
                        session.add(cmd)
                        enqueued += 1
                        by_supplier[str(supplier.id)] = by_supplier.get(str(supplier.id), 0) + 1
                else:
                    cmd_id = str(uuid.uuid4())
                    cmd = SystemCommand(
                        id=cmd_id,
                        type="SCRAPE_SUPPLIER",
                        payload={"supplier_id": supplier.id, "supplier_name": supplier.name, "pages": int(cfg.get("batch_size", 1))},
                        status=CommandStatus.PENDING,
                        priority=int(cfg.get("priority", 50)),
                    )
                    session.add(cmd)
                    enqueued += 1
                    by_supplier[str(supplier.id)] = by_supplier.get(str(supplier.id), 0) + 1
            
            session.commit()

            # Update JobStatus
            job.items_processed = enqueued
            session.commit()
            self._finish_jobstatus(
                session,
                job.id,
                "COMPLETED",
                {
                    "enqueued": enqueued,
                    "per_category": bool(cfg.get("per_category")),
                    "by_supplier": by_supplier,
                    "interval_minutes": self.interval_minutes,
                },
            )
            
        except Exception as e:
            logger.error(f"SCHEDULER: Scrape job failed: {e}")
            session.rollback()
        finally:
            session.close()
    
    def enrich_job(self):
        """Auto-enqueue enrich for all suppliers"""
        session = SessionLocal()
        try:
            store_mode = self._get_setting(session, "store.mode", {"mode": "NORMAL"})
            mode = str(store_mode.get("mode", "NORMAL")).upper()
            cfg = self._get_setting(
                session,
                "scheduler.enrich",
                {
                    "enabled": True,
                    "interval_minutes": self.interval_minutes,
                    "priority": 50,
                    "per_category": True,
                    "max_categories_per_supplier": 200,
                    "batch_size": 25,
                    "delay_seconds": 0,
                },
            )
            self.interval_minutes = int(cfg.get("interval_minutes") or self.interval_minutes)
            # Seasonality / holiday throttling
            if mode in ["HOLIDAY", "PAUSED"]:
                cfg["enabled"] = False
            elif mode in ["SLOW"]:
                cfg["interval_minutes"] = max(int(cfg.get("interval_minutes") or self.interval_minutes), 360)
            if not cfg.get("enabled", True):
                logger.info(f"SCHEDULER: enrich_job disabled (store_mode={mode})")
                return

            suppliers = session.query(Supplier).all()
            logger.info(f"SCHEDULER: Running enrich job for {len(suppliers)} suppliers")

            job = self._enqueue_jobstatus(session, "SCHEDULER_ENRICH")
            enqueued = 0
            by_supplier = {}
            
            for supplier in suppliers:
                if cfg.get("per_category"):
                    cats = (
                        session.query(SupplierProduct.source_category)
                        .filter(SupplierProduct.supplier_id == supplier.id)
                        .filter(SupplierProduct.source_category.isnot(None))
                        .distinct()
                        .limit(int(cfg.get("max_categories_per_supplier", 200)))
                        .all()
                    )
                    for (cat,) in cats:
                        cmd_id = str(uuid.uuid4())
                        cmd = SystemCommand(
                            id=cmd_id,
                            type="ENRICH_SUPPLIER",
                            payload={
                                "supplier_id": supplier.id,
                                "supplier_name": supplier.name,
                                "source_category": cat,
                                "batch_size": int(cfg.get("batch_size", 25)),
                                "delay_seconds": int(cfg.get("delay_seconds", 0)),
                            },
                            status=CommandStatus.PENDING,
                            priority=int(cfg.get("priority", 50)),
                        )
                        session.add(cmd)
                        enqueued += 1
                        by_supplier[str(supplier.id)] = by_supplier.get(str(supplier.id), 0) + 1
                else:
                    cmd_id = str(uuid.uuid4())
                    cmd = SystemCommand(
                        id=cmd_id,
                        type="ENRICH_SUPPLIER",
                        payload={
                            "supplier_id": supplier.id,
                            "supplier_name": supplier.name,
                            "batch_size": int(cfg.get("batch_size", 25)),
                            "delay_seconds": int(cfg.get("delay_seconds", 0)),
                        },
                        status=CommandStatus.PENDING,
                        priority=int(cfg.get("priority", 50)),
                    )
                    session.add(cmd)
                    enqueued += 1
                    by_supplier[str(supplier.id)] = by_supplier.get(str(supplier.id), 0) + 1
            
            session.commit()

            job.items_processed = enqueued
            session.commit()
            self._finish_jobstatus(
                session,
                job.id,
                "COMPLETED",
                {
                    "enqueued": enqueued,
                    "per_category": bool(cfg.get("per_category")),
                    "by_supplier": by_supplier,
                    "interval_minutes": self.interval_minutes,
                },
            )
            
        except Exception as e:
            logger.error(f"SCHEDULER: Enrich job failed: {e}")
            session.rollback()
        finally:
            session.close()

    def orders_job(self):
        """
        Fulfillment-critical: enqueue SYNC_SOLD_ITEMS frequently.
        This should keep running even in HOLIDAY/SLOW modes (only PAUSED disables).
        """
        session = SessionLocal()
        try:
            store_mode = self._get_setting(session, "store.mode", {"mode": "NORMAL"})
            mode = str(store_mode.get("mode", "NORMAL")).upper()
            cfg = self._get_setting(
                session,
                "scheduler.orders",
                {
                    "enabled": True,
                    "interval_minutes": 5 if self.dev_mode else 10,
                    "priority": 80,
                },
            )
            if mode in ["PAUSED"]:
                cfg["enabled"] = False
            if not cfg.get("enabled", True):
                logger.info(f"SCHEDULER: orders_job disabled (store_mode={mode})")
                return

            job = self._enqueue_jobstatus(session, "SCHEDULER_ORDERS")

            cmd_id = str(uuid.uuid4())
            session.add(
                SystemCommand(
                    id=cmd_id,
                    type="SYNC_SOLD_ITEMS",
                    payload={},
                    status=CommandStatus.PENDING,
                    priority=int(cfg.get("priority", 80)),
                )
            )
            session.commit()
            self._finish_jobstatus(
                session,
                job.id,
                "COMPLETED",
                {"enqueued": 1, "interval_minutes": int(cfg.get("interval_minutes") or 0), "store_mode": mode},
            )
        except Exception as e:
            logger.error(f"SCHEDULER: orders job failed: {e}")
            session.rollback()
        finally:
            session.close()
    
    def start(self):
        """Start the scheduler"""
        logger.info(f"SCHEDULER: Starting in {'DEV' if self.dev_mode else 'PROD'} mode (interval={self.interval_minutes} min)")
        
        # Add jobs
        self.scheduler.add_job(
            self.scrape_job,
            trigger=IntervalTrigger(minutes=self.interval_minutes),
            id='scrape_all',
            name='Scrape All Suppliers',
            replace_existing=True
        )
        
        self.scheduler.add_job(
            self.enrich_job,
            trigger=IntervalTrigger(minutes=self.interval_minutes),
            id='enrich_all',
            name='Enrich All Suppliers',
            replace_existing=True
        )

        # Orders job uses its own cadence (default 5–10 minutes)
        self.scheduler.add_job(
            self.orders_job,
            trigger=IntervalTrigger(minutes=5 if self.dev_mode else 10),
            id="sync_orders",
            name="Sync Sold Items",
            replace_existing=True,
        )
        
        self.scheduler.start()
        logger.info("SCHEDULER: Started successfully")
        
        # Run jobs immediately on start
        self.scrape_job()
        self.enrich_job()
        self.orders_job()
    
    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
        logger.info("SCHEDULER: Stopped")


if __name__ == "__main__":
    scheduler = SpectatorScheduler(dev_mode=True)
    scheduler.start()
    
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.stop()
