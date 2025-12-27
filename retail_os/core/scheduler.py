"""
Scheduler with auto-enqueue and DB persistence for Spectator Mode.
"""
import time
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from retail_os.core.database import SessionLocal, SystemCommand, CommandStatus, Supplier, JobStatus
import uuid

# Setup logging
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
        self.interval_minutes = 1 if dev_mode else 60  # 1 min for DEV, 60 for PROD
        
    def scrape_job(self):
        """Auto-enqueue scrape for all suppliers"""
        session = SessionLocal()
        try:
            suppliers = session.query(Supplier).all()
            logger.info(f"SCHEDULER: Running scrape job for {len(suppliers)} suppliers")
            
            for supplier in suppliers:
                cmd_id = str(uuid.uuid4())
                cmd = SystemCommand(
                    id=cmd_id,
                    type="SCRAPE_SUPPLIER",
                    payload={"supplier_id": supplier.id, "supplier_name": supplier.name},
                    status=CommandStatus.PENDING,
                    priority=50  # Medium priority for scheduled jobs
                )
                session.add(cmd)
                logger.info(f"SCHEDULER: Enqueued SCRAPE_SUPPLIER {cmd_id[:12]} for {supplier.name}")
            
            session.commit()
            
            # Update JobStatus
            job_status = session.query(JobStatus).filter_by(job_name="scrape_all").first()
            if not job_status:
                job_status = JobStatus(job_name="scrape_all")
                session.add(job_status)
            
            job_status.last_run = datetime.utcnow()
            job_status.next_run = datetime.utcnow() + timedelta(minutes=self.interval_minutes)
            job_status.status = "COMPLETED"
            session.commit()
            
        except Exception as e:
            logger.error(f"SCHEDULER: Scrape job failed: {e}")
            session.rollback()
        finally:
            session.close()
    
    def enrich_job(self):
        """Auto-enqueue enrich for all suppliers"""
        session = SessionLocal()
        try:
            suppliers = session.query(Supplier).all()
            logger.info(f"SCHEDULER: Running enrich job for {len(suppliers)} suppliers")
            
            for supplier in suppliers:
                cmd_id = str(uuid.uuid4())
                cmd = SystemCommand(
                    id=cmd_id,
                    type="ENRICH_SUPPLIER",
                    payload={"supplier_id": supplier.id, "supplier_name": supplier.name},
                    status=CommandStatus.PENDING,
                    priority=50
                )
                session.add(cmd)
                logger.info(f"SCHEDULER: Enqueued ENRICH_SUPPLIER {cmd_id[:12]} for {supplier.name}")
            
            session.commit()
            
            # Update JobStatus
            job_status = session.query(JobStatus).filter_by(job_name="enrich_all").first()
            if not job_status:
                job_status = JobStatus(job_name="enrich_all")
                session.add(job_status)
            
            job_status.last_run = datetime.utcnow()
            job_status.next_run = datetime.utcnow() + timedelta(minutes=self.interval_minutes)
            job_status.status = "COMPLETED"
            session.commit()
            
        except Exception as e:
            logger.error(f"SCHEDULER: Enrich job failed: {e}")
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
        
        self.scheduler.start()
        logger.info("SCHEDULER: Started successfully")
        
        # Run jobs immediately on start
        self.scrape_job()
        self.enrich_job()
    
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
