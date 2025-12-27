import os
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, event, ForeignKey, Enum as SQLEnum, JSON, UniqueConstraint, Numeric
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.sql import func
from datetime import datetime
from pathlib import Path
import enum
from contextlib import contextmanager
from typing import Iterable

Base = declarative_base()

# --- Enums ---
class CommandStatus(str, enum.Enum):
    PENDING = "PENDING"
    EXECUTING = "EXECUTING"
    SUCCEEDED = "SUCCEEDED"
    FAILED_RETRYABLE = "FAILED_RETRYABLE"
    FAILED_FATAL = "FAILED_FATAL"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"
    CANCELLED = "CANCELLED"

class ListingState(str, enum.Enum):
    NEW = "NEW"
    PROVING = "PROVING"
    STABLE = "STABLE"
    FADING = "FADING"
    KILL = "KILL"
    QUARANTINED = "QUARANTINED"

# --- Tables ---

class Supplier(Base):
    __tablename__ = 'suppliers'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    base_url = Column(String)
    is_active = Column(Boolean, default=True)
    
    products = relationship("SupplierProduct", back_populates="supplier")

class SupplierProduct(Base):
    """External Reality: What the supplier has."""
    __tablename__ = 'supplier_products'
    
    id = Column(Integer, primary_key=True)
    supplier_id = Column(Integer, ForeignKey('suppliers.id'))
    external_sku = Column(String, nullable=False) # Supplier's ID
    
    # Scraped Data
    title = Column(String)
    description = Column(Text)
    brand = Column(String)  # Product brand
    condition = Column(String)  # New, Used, Refurbished
    cost_price = Column(Numeric(10, 2))  # Changed from Float to Numeric for precision
    stock_level = Column(Integer)
    product_url = Column(String)
    images = Column(JSON) # Added in Phase 3.5
    specs = Column(JSON) # Product specifications (Model, Condition, etc.)
    
    # Enrichment Status (for background processing)
    enrichment_status = Column(String, default="PENDING")  # PENDING, SUCCESS, FAILED
    enrichment_error = Column(Text)  # Error reason if FAILED
    enriched_title = Column(String)  # Cleaned/enriched title
    enriched_description = Column(Text)  # Cleaned/enriched description
    
    # Evidence
    last_scraped_at = Column(DateTime)
    snapshot_hash = Column(String) # For Variant Drift detection
    sync_status = Column(String, default="PRESENT") # PRESENT, MISSING_ONCE, REMOVED

    # Categorization (for scaling to 20k+ listings)
    # Supplier-native category/collection path or identifier.
    source_category = Column(String)
    
    # Ranking Data (Added for Noel Leeming prioritization)
    collection_rank = Column(Integer)
    collection_page = Column(Integer)
    
    supplier = relationship("Supplier", back_populates="products")
    # One SupplierProduct should map to one InternalProduct (canonical).
    # Enforce scalar relationship to match pipeline expectations.
    internal_product = relationship("InternalProduct", back_populates="supplier_product", uselist=False)

    __table_args__ = (
        UniqueConstraint('supplier_id', 'external_sku', name='uix_supplier_sku'),
    )

class InternalProduct(Base):
    """The God Item (Canonical). You own this."""
    __tablename__ = 'internal_products'
    
    id = Column(Integer, primary_key=True)
    sku = Column(String, unique=True, nullable=False) # Your SKU: "MY-LED-001"
    title = Column(String) # Canonical Title
    
    # Linkage to Source
    primary_supplier_product_id = Column(Integer, ForeignKey('supplier_products.id'))
    
    supplier_product = relationship("SupplierProduct", back_populates="internal_product")
    listings = relationship("TradeMeListing", back_populates="product")

class TradeMeListing(Base):
    """The Platform Reality: An instance on TradeMe."""
    __tablename__ = 'trademe_listings'
    
    id = Column(Integer, primary_key=True)
    internal_product_id = Column(Integer, ForeignKey('internal_products.id'))
    tm_listing_id = Column(String, unique=True) # TradeMe's ID. Null if not listed yet.
    
    # State Triad (The Truth)
    desired_price = Column(Float)
    actual_price = Column(Float)
    
    desired_state = Column(String) # "Live", "Withdrawn"
    actual_state = Column(String)
    
    last_synced_at = Column(DateTime)
    
    # Strategic Fields
    lifecycle_state = Column(SQLEnum(ListingState), default=ListingState.NEW)
    is_locked = Column(Boolean, default=False) # "Trust Optimization" Lock
    
    # Velocity Metrics (Added Phase 5)
    view_count = Column(Integer, default=0)
    watch_count = Column(Integer, default=0)
    category_id = Column(String)
    
    # Payload Tracking (Spectator Mode Phase 3)
    payload_snapshot = Column(Text)  # JSON snapshot of listing payload
    payload_hash = Column(String)  # SHA256 hash for comparison
    
    product = relationship("InternalProduct", back_populates="listings")
    metrics = relationship("ListingMetricSnapshot", back_populates="listing")
    orders = relationship("Order", back_populates="listing")  # NEW: Track sales
    price_history = relationship("PriceHistory", back_populates="listing")

class ListingMetricSnapshot(Base):
    """Time-Series data for Velocity Calculation."""
    __tablename__ = 'listing_metrics'
    
    id = Column(Integer, primary_key=True)
    listing_id = Column(Integer, ForeignKey('trademe_listings.id'))
    captured_at = Column(DateTime, default=datetime.utcnow)
    
    view_count = Column(Integer)
    watch_count = Column(Integer)
    is_sold = Column(Boolean, default=False)
    
    listing = relationship("TradeMeListing", back_populates="metrics")

class PriceHistory(Base):
    """Track price changes for Panic Undo support."""
    __tablename__ = 'price_history'
    
    id = Column(Integer, primary_key=True)
    listing_id = Column(Integer, ForeignKey('trademe_listings.id'))
    price = Column(Float, nullable=False)
    change_type = Column(String) # "MANUAL", "PANIC", "STRATEGY"
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    listing = relationship("TradeMeListing", back_populates="price_history")

class Order(Base):
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True)
    tm_order_ref = Column(String, unique=True) # Trade Me order reference (idempotency)
    tm_listing_id = Column(Integer, ForeignKey('trademe_listings.id'))  # Which listing sold
    
    # Sale Details
    sold_price = Column(Numeric(10, 2))  # Final sale price
    sold_date = Column(DateTime)  # When it sold
    
    # Buyer Info
    buyer_name = Column(String)
    buyer_email = Column(String)
    shipping_address = Column(Text)
    
    # Order Status
    order_status = Column(String, default="PENDING")  # PENDING, CONFIRMED, CANCELLED
    payment_status = Column(String, default="PENDING")  # PENDING, PAID, REFUNDED
    fulfillment_status = Column(String, default="PENDING")  # PENDING, PICKED, PACKED, SHIPPED, DELIVERED
    
    # Logistics
    tracking_reference = Column(String)
    carrier = Column(String)
    shipped_date = Column(DateTime)
    delivered_date = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    listing = relationship("TradeMeListing", back_populates="orders")

class SystemCommand(Base):
    """The Command Engine Logic."""
    __tablename__ = 'system_commands'
    
    id = Column(String, primary_key=True) # UUID (Idempotency Key)
    type = Column(String, nullable=False) # UPDATE_PRICE, PUBLISH
    payload = Column(JSON) # {"target_id": 1, "price": 50.0}
    
    status = Column(SQLEnum(CommandStatus), default=CommandStatus.PENDING)
    
    priority = Column(Integer, default=10)
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    last_error = Column(Text)
    error_code = Column(String)  # INSUFFICIENT_BALANCE, MISSING_CREDS, etc
    error_message = Column(Text)  # User-facing error message
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True)
    entity_type = Column(String) # Listing, Order
    entity_id = Column(String)
    action = Column(String)
    old_value = Column(Text)
    new_value = Column(Text)
    user = Column(String) # "System" or "Admin"
    timestamp = Column(DateTime, default=datetime.utcnow)

class ResourceLock(Base):
    """Application-Level Locks for Concurrency Safety."""
    __tablename__ = 'resource_locks'
    
    id = Column(Integer, primary_key=True)
    entity_type = Column(String, nullable=False) # "IP", "LISTING"
    entity_id = Column(String, nullable=False)   # "101", "456"
    owner_cmd_id = Column(String, nullable=False) # Command UUID owning this lock
    
    acquired_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    
    # Composite Unique Index ensures 1 global owner per entity
    # (entity_type, entity_id) must be unique

class ListingDraft(Base):
    """Wait-Room for Publish Payloads. Single Source of Truth."""
    __tablename__ = 'listing_drafts'
    
    id = Column(Integer, primary_key=True)
    command_id = Column(String, ForeignKey('system_commands.id'), unique=True)
    
    payload_json = Column(JSON, nullable=False) # The FINAL payload sent to validation
    validation_results = Column(JSON) # Store API response
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
class PhotoHash(Base):
    """Idempotency Cache for Photos."""
    __tablename__ = 'photo_hashes'
    
    hash = Column(String, primary_key=True) # xxhash
    tm_photo_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class JobStatus(Base):
    """
    Tracks the execution status of background jobs (Scraping, Enrichment).
    """
    __tablename__ = "job_status"
    
    id = Column(Integer, primary_key=True, index=True)
    job_type = Column(String) # 'SCRAPE_OC', 'SCRAPE_CC', 'ENRICHMENT'
    status = Column(String)   # 'RUNNING', 'COMPLETED', 'FAILED'
    start_time = Column(DateTime)
    end_time = Column(DateTime, nullable=True)
    items_processed = Column(Integer, default=0)
    items_created = Column(Integer, default=0) # New products found
    items_updated = Column(Integer, default=0) # Existing products changed
    items_deleted = Column(Integer, default=0) # Products removed/withdrawn
    items_failed = Column(Integer, default=0)
    summary = Column(Text, nullable=True) # JSON summary of the run

class SystemSetting(Base):
    """Global Configuration (Scheduler, Toggles)."""
    __tablename__ = 'system_settings'
    
    key = Column(String, primary_key=True)
    value = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# --- Database Engine ---
# Single source of truth database (configurable by env var)
#
# Prefer DATABASE_URL if set:
# - sqlite:////app/data/retail_os.db (docker)
# - sqlite:///data/retail_os.db (local)
#
# We keep sqlite check_same_thread=False for Streamlit/scheduler/worker usage.
#
# Default to a repo-root anchored DB path so scripts work from any cwd.
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_default_db_path = os.path.join(_repo_root, "data", "retail_os.db")
os.makedirs(os.path.dirname(_default_db_path), exist_ok=True)

# Windows-safe sqlite URL: ensure forward slashes (e.g. sqlite:///C:/path/to/db)
_default_db_path_uri = Path(_default_db_path).as_posix()
DATABASE_URL = os.getenv("DATABASE_URL") or f"sqlite:///{_default_db_path_uri}"

# Normalize user-provided sqlite URL on Windows (common pitfall: backslashes break sqlite URL parsing).
if DATABASE_URL.startswith("sqlite") and "\\" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("\\", "/")

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL, echo=False)

# Enable WAL Mode
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()

SessionLocal = sessionmaker(bind=engine)

def _sqlite_table_columns(conn, table_name: str) -> set[str]:
    """
    Returns column names for a sqlite table. If table doesn't exist, returns empty set.
    Uses PRAGMA table_info which is sqlite-specific.
    """
    rows = conn.exec_driver_sql(f"PRAGMA table_info({table_name})").fetchall()
    # PRAGMA table_info columns: cid, name, type, notnull, dflt_value, pk
    return {r[1] for r in rows} if rows else set()


def _sqlite_ensure_columns(conn, table_name: str, columns: dict[str, str]) -> list[str]:
    """
    Ensure sqlite table has the given columns; add any missing columns via ALTER TABLE.
    Returns list of columns added.
    """
    existing = _sqlite_table_columns(conn, table_name)
    added: list[str] = []
    for col, col_sql in columns.items():
        if col in existing:
            continue
        conn.exec_driver_sql(f"ALTER TABLE {table_name} ADD COLUMN {col} {col_sql}")
        added.append(col)
    return added


def _auto_migrate_sqlite_schema() -> None:
    """
    Minimal, safe schema drift fix for sqlite in local dev.
    SQLAlchemy create_all() won't add columns to existing tables, so older DBs can 500.
    """
    if not DATABASE_URL.startswith("sqlite"):
        return

    with engine.begin() as conn:
        # Additive migrations only (safe). Keep this list small and focused.
        _sqlite_ensure_columns(
            conn,
            "supplier_products",
            {
                # Added for category-based scaling.
                "source_category": "VARCHAR",
                # Added for Noel Leeming ranking support.
                "collection_rank": "INTEGER",
                "collection_page": "INTEGER",
                # Evidence fields used by pipeline guardrails.
                "snapshot_hash": "VARCHAR",
                "last_scraped_at": "DATETIME",
                "sync_status": "VARCHAR",
            },
        )

def init_db():
    Base.metadata.create_all(engine)
    _auto_migrate_sqlite_schema()
    print("Strict Schema Initialized (WAL Mode ON).")

@contextmanager
def get_db_session():
    """Context manager for database sessions."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
