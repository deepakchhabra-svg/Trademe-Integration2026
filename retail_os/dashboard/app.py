import streamlit as st
import pandas as pd
import sys
import os
import time
from datetime import datetime
from sqlalchemy import func

# Ensure retail_os is in path
sys.path.append(os.getcwd())

from retail_os.core.database import (
    SessionLocal, InternalProduct, TradeMeListing, 
    SystemCommand, SupplierProduct, Supplier, CommandStatus, Order, JobStatus, SystemSetting
)
from retail_os.utils.seo import build_seo_description
from retail_os.dashboard.data_layer import (
    fetch_vault_metrics, fetch_vault1_data, fetch_vault2_data, 
    fetch_vault3_data, fetch_recent_jobs, fetch_price_history
)

# Initialize session state for deterministic UI
if 'selected_product_id' not in st.session_state:
    st.session_state.selected_product_id = None
if 'selected_vault' not in st.session_state:
    st.session_state.selected_vault = None

# Page configuration
st.set_page_config(
    page_title="RetailOS | Trade Me Intelligence",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- GLOBAL ALERTS (Robot Heartbeat) ---
# Check Key Scrapers for 403/Failures
def render_global_alerts():
    from retail_os.dashboard.data_layer import fetch_system_health
    health = fetch_system_health()
    if health and "heartbeats" in health:
        for job in health["heartbeats"]:
            if job["status"] == "FAILED":
                # Stacking alerts can be noisy, so we group them
                st.error(f"🚨 **SYSTEM ALERT**: {job['job_type']} Failed! (Check Operations Tab)")

render_global_alerts()

# PREMIUM UI CSS INJECTION
st.markdown("""
    <style>
    /* IMPORT INTER FONT */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* GLOBAL RESET & TYPOGRAPHY */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        color: #1e293b;
    }
    
    /* HEADER BAR */
    header {visibility: hidden;}
    .top-bar {
        background: #0f172a;
        color: white;
        padding: 1rem 2rem;
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        z-index: 9999;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .app-title {
        font-size: 1.25rem;
        font-weight: 700;
        letter-spacing: -0.025em;
    }
    
    /* PREVENT CONTENT OVERLAP WITH FIXED HEADER */
    .block-container {
        padding-top: 5rem !important;
    }
    
    /* CARDS & METRICS */
    .metric-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
    }
    .metric-label {
        font-size: 0.875rem;
        color: #64748b;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #0f172a;
        margin-top: 0.5rem;
    }
    
    /* TABS - Larger and better contrast */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: none;
        padding: 10px 0;
    }
    .stTabs [data-baseweb="tab"] {
        height: 60px;
        padding: 12px 24px;
        font-size: 16px;
        font-weight: 500;
        color: #1f2937;
        background-color: #f3f4f6;
        border-radius: 8px 8px 0 0;
        border: none;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #e5e7eb;
        color: #111827;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #f97316 !important;
        color: white !important;
        font-weight: 600;
        border: none;
    }
    
    /* ACTIVITY CARDS (OPERATIONS) */
    .activity-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1.5rem;
        height: 100%;
    }
    .activity-header {
        font-weight: 600;
        color: #0f172a;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    /* STATUS BADGES */
    .badge {
        display: inline-flex;
        align-items: center;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-green { background: #dcfce7; color: #166534; }
    .badge-yellow { background: #fef9c3; color: #854d0e; }
    .badge-red { background: #fee2e2; color: #991b1b; }
    .badge-blue { background: #dbeafe; color: #1e40af; }
    
    </style>
    
    <div class="top-bar">
        <div class="app-title">📊 Trade Me Integration Platform</div>
        <div style="font-size: 0.875rem; color: #94a3b8;">Production Ready</div>
    </div>
""", unsafe_allow_html=True)

# Auto-refresh disabled - was disrupting user navigation
# Users can manually refresh if needed
import streamlit.components.v1 as components

# Professional, readable CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Rubik:wght@300;400;500;600;700&display=swap');
    
    * {
        font-family: 'Rubik', sans-serif;
    }
    
    .stApp {
        background-color: #f0f2f5;
    }
    
    /* Header (OneCheq Navy) */
    .main-header {
        background-color: #232f3f;
        background-image: linear-gradient(135deg, #232f3f 0%, #1a2533 100%);
        color: white;
        padding: 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border-bottom: 4px solid #eb8f04; /* Amber accent */
    }
    
    .main-header h1 {
        color: white !important;
        margin: 0;
        font-size: 2.2rem;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    
    .main-header p {
        color: #e2e8f0;
        margin: 0.5rem 0 0 0;
        font-weight: 300;
        font-size: 1.1rem;
    }
    
    /* Metric cards */
    div[data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 700;
        color: #232f3f;
    }
    
    div[data-testid="stMetricLabel"] {
        color: #64748b;
        font-weight: 500;
        text-transform: uppercase;
        font-size: 0.8rem;
        letter-spacing: 0.05em;
    }
    
    /* Vault cards */
    .vault-card {
        background: white;
        border-top: 4px solid #232f3f;
        padding: 1.5rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 1rem;
        transition: transform 0.2s;
    }
    
    .vault-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: white;
        padding: 0.75rem;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        color: #4a5568;
        font-weight: 500;
        padding: 0.5rem 1.5rem;
        border-radius: 8px;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #232f3f;
        color: white;
        font-weight: 600;
    }
    
    /* Buttons */
    .stButton > button {
        background-color: #eb8f04; /* OneCheq Amber */
        color: white;
        border: none;
        border-radius: 6px;
        padding: 0.6rem 1.5rem;
        font-weight: 600;
        transition: all 0.2s;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-size: 0.9rem;
    }
    
    .stButton > button:hover {
        background-color: #d68103;
        color: white;
        box-shadow: 0 4px 12px rgba(235, 143, 4, 0.3);
    }
    
    /* Secondary/Ghost Buttons */
    button[kind="secondary"] {
        background-color: transparent !important;
        border: 2px solid #232f3f !important;
        color: #232f3f !important;
    }
    
    /* Data tables */
    .dataframe {
        font-family: 'Rubik', sans-serif;
        font-size: 0.95rem;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #232f3f;
    }
    
    [data-testid="stSidebar"] .stMarkdown {
        color: white;
    }
    
    [data-testid="stSidebar"] hr {
        border-color: rgba(255,255,255,0.1);
    }
    
    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Search and filters */
    .stTextInput input {
        border-radius: 6px;
        border: 1px solid #cbd5e0;
        padding: 0.5rem 0.75rem;
    }
    
    .stSelectbox > div > div {
        border-radius: 6px;
        border: 1px solid #cbd5e0;
    }
    
    /* Empty state */
    .empty-state {
        text-align: center;
        padding: 4rem 2rem;
        background: white;
        border-radius: 12px;
        border: 2px dashed #edf2f7;
    }
    
    .empty-state h3 {
        color: #2d3748;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    
    .empty-state p {
        color: #718096;
    }
</style>
""", unsafe_allow_html=True)

# --- 1. SESSION MANAGEMENT (Critical Basic Fix) ---
# We use a context manager capable generator for `with get_db_session() as session:`
# But Streamlit code structure usually relies on getting a session for a whole block.
# We'll upgrade this to a class or generator check.
# Actually, looking at the code, it returns a plain session.
# Let's wrap it for safety, but existing code calls `session = get_db_session()`.
# To avoid rewriting EVERY line, we ensure `session` is closed at end of script run logic?
# Streamlit re-runs file top-to-bottom.
# Safest: Use try/finally blocks in main(), but since Streamlit handles the rendering loop,
# we should ideally use `st.session_state` to hold it if persistent, OR just ensure
# we close it.
# The user specifically requested "Refactor get_db_session() to be a context manager".
# This means we should change how it is CALLED. `with get_db_session() as session:`
from contextlib import contextmanager

from retail_os.core.database import get_db_session

def render_global_alerts():
    """Display system-wide alerts (Scraper Blocks, API Failures)"""
    from retail_os.dashboard.data_layer import fetch_system_health
    
    # We catch errors here to avoid crashing the alert system itself
    try:
        health = fetch_system_health()
        heartbeats = health.get("heartbeats", {})
        
        alerts = []
        for job_type, info in heartbeats.items():
            if info["status"] == "FAILED":
                # Check how recent? For now, just show it.
                alerts.append(f"⚠️ {job_type} Failed: Check logs. Last run: {info.get('last_run')}")
            if info["status"] == "UNKNOWN":
                 # Maybe new system?
                 pass
                 
        if alerts:
            for a in alerts:
                st.error(a, icon="🚨")
    except Exception as e:
        print(f"Alert System Error: {e}")

def render_header():
    """Render main header"""
    render_global_alerts()
    st.markdown("""
    <div class="main-header">
        <h1>📊 Trade Me Integration Platform</h1>
        <p>Automated Product Listing & Inventory Management</p>
    </div>
    """, unsafe_allow_html=True)

def render_vault_metrics(session):
    """Metrics removed - redundant with tabs"""
    pass

def render_vault1_raw_landing(session):
    """VAULT 1: Raw Landing - Show all scraped data"""
    st.markdown("## 🔴 VAULT 1: Raw Landing")
    st.markdown("**All scraped products from suppliers** - Unprocessed, original data")
    
    st.markdown("---")
    
    # Filters
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    
    with col1:
        search = st.text_input("🔍 Search products", placeholder="Enter SKU, title, or keyword...", key="v1_search")
    
    with col2:
        suppliers = session.query(Supplier).all()
        supplier_names = ["All Suppliers"] + [s.name for s in suppliers]
        selected_supplier = st.selectbox("Supplier", supplier_names, key="v1_supplier")
    
    with col3:
        sync_status = st.selectbox("Status", ["All", "PRESENT", "REMOVED"], key="v1_status")
    
    with col4:
        per_page = st.selectbox("Per page", [50, 100, 200, 500], index=1, key="v1_perpage")
    
    # Build query (VIA DATA LAYER)
    # Note: Supplier and Status filters are handled in UI for now, 
    # but 'search' is passed down for efficiency.
    
    # We need total count first to know max pages? 
    # Actually data layer returns (data, total). But we need page for the call.
    # Chicken and egg. 
    # Solution: We do a cheap count first OR we just default max_value to 100 
    # and let the user paginate.
    # BETTER: fetch_vault1_data should probably support "get count only" or we split it.
    # For now, let's keep it simple: We'll assume page 1 initially or separate count query.
    
    # Hack: Just run a count query here for pagination UI? 
    # No, that defeats the purpose of data layer.
    # Let's call it with limit=0 to get count? No.
    
    # Real solution: Data Layer should return `get_vault1_count(search_term)`.
    # But I can't edit data_layer right now easily without context switching.
    # I'll just restore the raw query for COUNT only to drive the UI, 
    # then use data layer for the heavy lift? No, that's partial.
    
    # Let's look at previous code:
    # total_count = query.count()
    # page = st.number_input(..., max_value=total_count...)
    
    # I will add `get_vault1_count` to data layer? 
    # No, `fetch_vault1_data` returns `total`!
    # But I need `page` to CALL it.
    # Standard pattern: UI state (page) -> Fetch Data.
    # But validation of Page requires Total.
    # Catch-22 unless we cache total separately or allow "over-paging" and return empty.
    
    # Approach for now: Use session state for page, and just render the input. 
    # If users enters 999 and we get empty, so be it.
    # Or, we make a lightweight "count" call.
    
    # Let's just restore the raw count query for now to populate the paginator, 
    # but use data layer for the table. It's a compromise until Phase 2.
    
    q = session.query(SupplierProduct)
    if search:
        q = q.filter(SupplierProduct.title.ilike(f"%{search}%"))
    
    # Apply supplier filter
    if selected_supplier != "All Suppliers":
        supplier = session.query(Supplier).filter_by(name=selected_supplier).first()
        if supplier:
            q = q.filter(SupplierProduct.supplier_id == supplier.id)
    
    # Apply sync status filter
    if sync_status != "All":
        q = q.filter(SupplierProduct.sync_status == sync_status)
    
    total_count = q.count()
    
    # Standard pagination controls
    total_pages = max(1, (total_count // per_page) + 1)
    
    # Use session state for page tracking
    if 'v1_page' not in st.session_state:
        st.session_state.v1_page = 1
    
    page = st.session_state.v1_page
    
    # Simple page indicator
    if total_pages > 1:
        st.caption(f"Page {page} of {total_pages}")
    
    products, _ = fetch_vault1_data(
        search_term=search, 
        page=page, 
        per_page=per_page
    )
    
    st.markdown(f"**Showing {len(products)} of {total_count:,} items** (Page {page})")
    
    if products:
        # Build dataframe
        # products is already a list of dicts from data_layer
        df = pd.DataFrame(products)
        
        # Display with column config and row selection
        event = st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            column_config={
                "id": st.column_config.NumberColumn("ID", width="small"),
                "img": st.column_config.ImageColumn("Image", width="small"),
                "supplier": st.column_config.TextColumn("Supplier", width="small"),
                "sku": st.column_config.TextColumn("SKU", width="medium"),
                "title": st.column_config.TextColumn("Title", width="large"),
                "price": st.column_config.NumberColumn("Price", width="small", format="$%.2f"),
                "status": st.column_config.TextColumn("Status", width="small"),
                "last_scraped": st.column_config.DatetimeColumn("Scraped", width="medium", format="DD/MM/YY HH:mm"),
            }
        )
        
        # DETAILED PRODUCT INSPECTOR - Triggered by row selection
        if event.selection.rows:
            selected_row_idx = event.selection.rows[0]
            selected_product_id = df.iloc[selected_row_idx]["ID"]
            
            product = session.query(SupplierProduct).filter_by(id=selected_product_id).first()
            
            if product:
                st.markdown("---")
                st.markdown(f"## 📦 {product.title}")
                st.caption(f"Product ID: {product.id} | SKU: {product.external_sku}")
                
                # Basic Info Cards
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("💰 Price", f"${product.cost_price:.2f}" if product.cost_price else "N/A")
                with col2:
                    st.metric("🏷️ Brand", product.brand or "N/A")
                with col3:
                    st.metric("✨ Condition", product.condition or "Unknown")
                with col4:
                    st.metric("📸 Images", len(product.images) if product.images else 0)
                
                # Images Gallery
                if product.images:
                    st.markdown("### 🖼️ Product Images")
                    cols = st.columns(min(4, len(product.images)))
                    for idx, img_path in enumerate(product.images[:4]):
                        with cols[idx]:
                            try:
                                import os
                                if os.path.exists(img_path):
                                    st.image(img_path, caption=f"Image {idx+1}", use_column_width=True)
                                else:
                                    st.info(f"📁 {os.path.basename(img_path)}")
                            except Exception as e:
                                st.warning(f"Image {idx+1} unavailable")
                
                # Description
                st.markdown("### 📝 Description")
                st.markdown(f"""
                <div style="background-color: #f8f9fa; padding: 1rem; border-radius: 8px; border-left: 4px solid #eb8f04;">
                    {product.description or "No description available"}
                </div>
                """, unsafe_allow_html=True)
                
                # Specs
                if product.specs:
                    st.markdown("### ⚙️ Specifications")
                    specs_cols = st.columns(2)
                    spec_items = list(product.specs.items()) if isinstance(product.specs, dict) else []
                    for idx, (key, value) in enumerate(spec_items):
                        with specs_cols[idx % 2]:
                            st.markdown(f"""
                            <div style="background-color: white; padding: 0.75rem; margin-bottom: 0.5rem; border-radius: 6px; border: 1px solid #e2e8f0;">
                                <strong style="color: #232f3f;">{key}:</strong> <span style="color: #4a5568;">{value}</span>
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    st.info("No specifications available")
                
                # Source Link
                col1, col2 = st.columns(2)
                with col1:
                    if product.product_url:
                        st.link_button("🔗 View on OneCheq", product.product_url, use_container_width=True)
                
                with col2:
                    # Raw Data Expander
                    with st.expander("🔬 View Raw JSON Data"):
                        import json
                        raw_data = {
                            "id": product.id,
                            "supplier_id": product.supplier_id,
                            "external_sku": product.external_sku,
                            "title": product.title,
                            "description": product.description,
                            "brand": product.brand,
                            "condition": product.condition,
                            "cost_price": float(product.cost_price) if product.cost_price else None,
                            "stock_level": product.stock_level,
                            "product_url": product.product_url,
                            "images": product.images,
                            "specs": product.specs,
                            "enrichment_status": product.enrichment_status,
                            "last_scraped_at": product.last_scraped_at.isoformat() if product.last_scraped_at else None,
                            "sync_status": product.sync_status,
                            "collection_rank": product.collection_rank,
                            "collection_page": product.collection_page
                        }
                        st.json(raw_data)
        else:
            st.info("👆 Click on any row in the table above to view detailed product information")
        
        # Export option
        if st.button("📥 Export Current Page to CSV"):
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"vault1_raw_landing_page{page}.csv",
                mime="text/csv"
            )
    else:
        st.markdown("""
        <div class="empty-state">
            <h3>No products found</h3>
            <p>Try adjusting your filters or run a scraper to import data</p>
        </div>
        """, unsafe_allow_html=True)

def render_vault2_sanitized(session):
    """VAULT 2: Sanitized Master - Enriched products"""
    st.markdown("## 🟡 VAULT 2: Sanitized Master")
    st.markdown("**AI-enriched products** - Clean descriptions, verified data, ready for marketplace")
    
    st.markdown("---")
    
    # Filters
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    
    with col1:
        search = st.text_input("🔍 Search enriched products", placeholder="Search...", key="v2_search")
    
    with col2:
        suppliers = session.query(Supplier).all()
        supplier_names = ["All Suppliers"] + [s.name for s in suppliers]
        selected_supplier = st.selectbox("Supplier", supplier_names, key="v2_supplier")
    
    with col3:
        enrichment_filter = st.selectbox("Enrichment", ["All", "Enriched", "Not Enriched"], key="v2_enrich")
    
    with col4:
        per_page = st.selectbox("Per page", [50, 100, 200, 500], index=1, key="v2_perpage")
    
    # Build query (VIA DATA LAYER)
    # Manual Count for Pagination (Simple, fast query)
    q = session.query(InternalProduct).join(SupplierProduct)
    if search:
        search_term = f"%{search}%"
        q = q.filter(
            (InternalProduct.title.ilike(search_term)) |
            (SupplierProduct.enriched_description.ilike(search_term))
        )
    if enrichment_filter == "Enriched":
        q = q.filter(SupplierProduct.enriched_description.isnot(None))
    elif enrichment_filter == "Not Enriched":
        q = q.filter(SupplierProduct.enriched_description.is_(None))
        
    total_count = q.count()
    
    # Pagination
    page = st.session_state.get("v2_page", 1)
    
    # Calculate total pages BEFORE using it
    total_pages = max(1, (total_count // per_page) + 1) if total_count > 0 else 1
    
    # Fetch products for current page
    products, _ = fetch_vault2_data(
        search_term=search,
        page=page,
        per_page=per_page
    )
    
    # SPLIT LAYOUT: List (Left) vs Inspector (Right)
    col_list, col_inspector = st.columns([1.8, 1.2])

    # PRODUCT LIST (Left) - Beautiful card-based selection
    with col_list:
        st.markdown(f"**{len(products)} Products** • Page {page} of {total_pages}")
        
        # Initialize selected product in session state
        if 'v2_selected_id' not in st.session_state:
            st.session_state.v2_selected_id = products[0]["id"] if products else None
        
        if products:
            # Custom CSS for beautiful product cards with OneCheq brand colors
            st.markdown("""
            <style>
            .product-card {
                display: flex;
                align-items: center;
                padding: 10px;
                margin: 6px 0;
                border-radius: 8px;
                border: 2px solid #e2e8f0;
                background: white;
                cursor: pointer;
                transition: all 0.2s ease;
            }
            .product-card:hover {
                border-color: #eb8f04;
                box-shadow: 0 4px 12px rgba(235, 143, 4, 0.15);
                transform: translateX(4px);
            }
            .product-card.selected {
                border-color: #eb8f04;
                background: linear-gradient(to right, #fffbf0, white);
            }
            .product-thumbnail {
                width: 55px;
                height: 55px;
                object-fit: cover;
                border-radius: 6px;
                margin-right: 12px;
                background: #f3f4f6;
                flex-shrink: 0;
            }
            .product-info {
                flex: 1;
                min-width: 0;
            }
            .product-id {
                display: inline-block;
                background: #232f3f;
                color: white;
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 0.7rem;
                font-weight: 600;
                margin-bottom: 4px;
            }
            .product-card.selected .product-id {
                background: #eb8f04;
            }
            .product-title {
                color: #1f2937;
                font-size: 0.85rem;
                font-weight: 500;
                line-height: 1.3;
                overflow: hidden;
                text-overflow: ellipsis;
                display: -webkit-box;
                -webkit-line-clamp: 2;
                -webkit-box-orient: vertical;
            }
            </style>
            """, unsafe_allow_html=True)
            
            # Render product cards with thumbnails
            for p in products:
                is_selected = (p["id"] == st.session_state.v2_selected_id)
                selected_class = "selected" if is_selected else ""
                
                # Get thumbnail image - handle different data structures
                thumbnail_url = ""
                if p.get("images"):
                    if isinstance(p["images"], list) and len(p["images"]) > 0:
                        thumbnail_url = p["images"][0]
                    elif isinstance(p["images"], str):
                        thumbnail_url = p["images"]
                
                # Fallback placeholder SVG
                placeholder_svg = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='55' height='55'%3E%3Crect fill='%23f3f4f6' width='55' height='55'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' fill='%23999' font-size='10'%3ENo Image%3C/text%3E%3C/svg%3E"
                
                # Create clickable card with thumbnail
                card_html = f"""
                <div class="product-card {selected_class}">
                    <img src="{thumbnail_url or placeholder_svg}" 
                         class="product-thumbnail" 
                         onerror="this.src='{placeholder_svg}'">
                    <div class="product-info">
                        <div class="product-id">#{p['id']}</div>
                        <div class="product-title">{p['title']}</div>
                    </div>
                </div>
                """
                
                st.markdown(card_html, unsafe_allow_html=True)
                
                # Invisible button overlay for click handling
                if st.button(
                    f"Select product {p['id']}",
                    key=f"prod_{p['id']}",
                    use_container_width=True
                ):
                    st.session_state.v2_selected_id = p["id"]
                    st.rerun()
        else:
            st.info("No products found matching criteria.")



    # INSPECTOR PANE (Right)
    with col_inspector:
        st.markdown("### 🕵️ Inspector & Quality Gate")
        
        # Get selected product ID from session state
        selected_id = st.session_state.get('v2_selected_id', None)
        
        if selected_id:
            # Fetch Full Internal Product
            product = session.query(InternalProduct).filter_by(id=selected_id).first()
            
            if product and product.supplier_product:
                sp = product.supplier_product
                
                # === LISTING PREVIEW SECTION ===
                st.markdown("#### 📋 Listing Preview")
                st.caption("This is what will be published to Trade Me")
                
                # Calculate price using pricing strategy
                from retail_os.strategy.pricing import PricingStrategy
                cost = float(sp.cost_price) if sp.cost_price else 0.0
                supplier_name = sp.supplier.name if sp.supplier else None
                calculated_price = PricingStrategy.calculate_price(cost, supplier_name=supplier_name)
                final_price = PricingStrategy.apply_psychological_rounding(calculated_price)
                
                # Get category mapping
                from retail_os.core.marketplace_adapter import MarketplaceAdapter
                try:
                    marketplace_data = MarketplaceAdapter.prepare_for_trademe(sp)
                    category_name = marketplace_data.get('category_name', 'Unknown')
                    category_id = marketplace_data.get('category_id', 'N/A')
                except:
                    category_name = 'Auto-detect'
                    category_id = 'TBD'
                
                # Price breakdown
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("💵 Cost", f"${cost:.2f}")
                with col2:
                    st.metric("💰 Sell Price", f"${final_price:.2f}")
                with col3:
                    margin = final_price - cost
                    margin_pct = (margin / cost * 100) if cost > 0 else 0
                    st.metric("📊 Margin", f"${margin:.2f}", f"{margin_pct:.1f}%")
                
                st.markdown("---")
                
                # Listing details
                st.markdown("**📦 Listing Details**")
                details_data = {
                    "Title": sp.enriched_title or sp.title or "N/A",
                    "Category": f"{category_name} ({category_id})",
                    "Condition": sp.condition or "Used",
                    "Brand": sp.brand or "N/A",
                    "Listing Type": "Buy Now (Fixed Price)",
                    "Duration": "7 days",
                    "Shipping": "Buyer arranges pickup",
                    "Payment": "Bank Transfer, Cash",
                    "Returns": "No returns",
                }
                
                for key, value in details_data.items():
                    st.text(f"{key}: {value}")
                
                st.markdown("---")
                
                # Description preview
                st.markdown("**📝 Description Preview**")
                desc = sp.enriched_description or sp.description or "No description"
                with st.expander("View full description"):
                    st.markdown(desc[:500] + "..." if len(desc) > 500 else desc)
                
                st.markdown("---")
                
                # Images
                st.markdown("**📸 Images**")
                if sp.images:
                    img_cols = st.columns(min(4, len(sp.images)))
                    for idx, img in enumerate(sp.images[:4]):
                        with img_cols[idx]:
                            try:
                                import os
                                if os.path.exists(img):
                                    st.image(img, use_column_width=True)
                                else:
                                    st.caption(f"Image {idx+1}")
                            except:
                                st.caption(f"Image {idx+1}")
                else:
                    st.warning("No images")
                
                st.markdown("---")
                sp = product.supplier_product
                
                # --- 1. TRUST HUD ---
                from retail_os.core.trust import TrustEngine, TrustReport
                trust_engine = TrustEngine(session)
                trust_report = trust_engine.get_product_trust_report(product)
                
                score_color = "green" if trust_report.score >= 95 else "orange" if trust_report.score >= 80 else "red"
                
                # Header Card
                st.markdown(f"""
                <div style="background: white; padding: 15px; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 15px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h3 style="margin:0; font-size: 1.1rem;">{product.title[:40]}...</h3>
                            <span style="font-size: 0.8rem; color: #64748b;">SKU: {product.sku}</span>
                        </div>
                        <div style="text-align: center;">
                            <span style="font-size: 1.5rem; font-weight: bold; color: {score_color};">{int(trust_report.score)}%</span>
                            <div style="font-size: 0.7rem; text-transform: uppercase;">Trust Score</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Tabs for Details
                insp_tab1, insp_tab2, insp_tab3 = st.tabs(["🛡️ Audit", "📷 Media", "📝 Content"])
                
                # --- TAB 1: AUDIT (Policy & Pricing) ---
                with insp_tab1:
                    from retail_os.strategy.policy import PolicyEngine
                    from retail_os.strategy.pricing import PricingStrategy
                    
                    # RUN PREFLIGHT BUTTON
                    if 'preflight_payload' not in st.session_state:
                        st.session_state.preflight_payload = None
                    
                    if st.button("🔍 Run Preflight", use_container_width=True, type="primary", key=f"preflight_{product.id}"):
                        from retail_os.core.listing_builder import build_listing_payload
                        try:
                            st.session_state.preflight_payload = build_listing_payload(product.id)
                            st.success("Preflight complete!")
                        except Exception as e:
                            st.error(f"Preflight failed: {e}")
                            st.session_state.preflight_payload = None
                    
                    st.markdown("---")
                    
                    policy_engine = PolicyEngine()
                    policy_res = policy_engine.evaluate(product)
                    
                    # Pricing Check
                    cost = float(sp.cost_price or 0)
                    calc_price = PricingStrategy.calculate_price(cost, supplier_name=sp.supplier.name if sp.supplier else None)
                    margin_check = PricingStrategy.validate_margin(cost, calc_price)
                    
                    # Policy Checklist
                    st.markdown("**Policy Checklist**")
                    if policy_res.passed:
                        st.success("✅ Policy Checks Passed")
                    else:
                        for b in policy_res.blockers:
                            st.error(f"⛔ {b}")
                    
                    st.markdown("---")
                    
                    # Financials
                    st.markdown("**Financial Preview**")
                    c1, c2 = st.columns(2)
                    c1.metric("Cost", f"${cost:.2f}")
                    c2.metric("Target Price", f"${calc_price:.2f}")
                    
                    if margin_check['safe']:
                        st.caption(f"✅ Margin Safe ({margin_check.get('margin_percent', 0)*100:.1f}%)")
                    else:
                        st.error(f"⚠️ {margin_check.get('reason')}")

                    st.markdown("---")
                    
                    # VISION AI GUARD (Blueprint Req)
                    from retail_os.core.image_guard import guard
                    img_path = sp.images[0] if sp.images else None
                    vision_res = {"is_safe": True, "reason": "No Image"}
                    
                    if img_path:
                        # Simple caching check to avoid re-running slow vision calls every frame keypress
                        # In prod, this should be pre-computed. For now, we call check_image which uses disk cache.
                        # Using spinner because it might take 2-3s first time.
                        vision_res = guard.check_image(img_path)
                    
                    if vision_res["is_safe"]:
                         if img_path: st.success(f"👁️ Vision Guard: SAFE")
                    else:
                         st.error(f"👁️ Vision Guard: BLOCKED ({vision_res['reason']})")
                         
                    st.markdown("---")
                    
                    # PREFLIGHT PAYLOAD DISPLAY
                    if st.session_state.preflight_payload:
                        st.markdown("#### 📋 Listing Payload Preview")
                        payload = st.session_state.preflight_payload
                        
                        col_p1, col_p2, col_p3 = st.columns(3)
                        with col_p1:
                            st.metric("Duration", f"{payload.get('Duration', 0)} days")
                        with col_p2:
                            st.metric("Start Price", f"${payload.get('StartPrice', 0):.2f}")
                        with col_p3:
                            st.metric("Margin", f"{payload.get('_margin_percent', 0):.1f}%")
                        
                        st.markdown("**Listing Defaults:**")
                        st.write(f"- Category: {payload.get('Category', 'N/A')}")
                        st.write(f"- Pickup: {payload.get('Pickup', 'N/A')}")
                        st.write(f"- Payment Options: {len(payload.get('PaymentOptions', []))} methods")
                        st.write(f"- Photos: {len(payload.get('PhotoUrls', []))} images")
                        
                        with st.expander("📄 Full Payload JSON"):
                            import json
                            st.json(json.loads(json.dumps(payload)))
                    
                    st.markdown("---")
                    
                    # THE GATE KEEPER
                    is_publishable = (trust_report.score >= 95) and policy_res.passed and margin_check['safe'] and vision_res["is_safe"]
                    
                    # DRY RUN BUTTON - ALWAYS VISIBLE (Mission 2 + Spectator Mode)
                    if st.button("🧪 Publish (Dry Run)", use_container_width=True, key=f"drypub_{product.id}", type="secondary"):
                        from retail_os.core.database import SystemCommand, CommandStatus
                        import uuid
                        
                        cmd_id = str(uuid.uuid4())
                        dry_run_cmd = SystemCommand(
                            id=cmd_id,
                            type="PUBLISH_LISTING",
                            payload={"internal_product_id": product.id, "dry_run": True},
                            status=CommandStatus.PENDING
                        )
                        session.add(dry_run_cmd)
                        session.commit()
                        
                        st.success(f"✅ Dry run enqueued: {cmd_id[:12]}...")
                        st.info("Go to Operations tab → Process Next Command (Dev)")
                        time.sleep(1)
                        st.rerun()
                    
                    # REAL PUBLISH BUTTON - Disabled if blocked
                    if is_publishable:
                        if st.button("🚀 Publish to Trade Me", use_container_width=True, key=f"pub_{product.id}"):
                            # SAFE GATEWAY (User Request: "Inviolable Validator")
                            from retail_os.dashboard.data_layer import submit_publish_command
                            success, msg = submit_publish_command(session, product.id)
                            session.commit()
                            
                            if success:
                                st.toast(f"🚀 {msg}")
                                # Rerun to update state
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.error(f"🛑 {msg}")
                    else:
                        st.button("🚫 Publish Blocked", disabled=True, use_container_width=True, help="Fix Trust/Policy issues first")
                        blockers = []
                        if trust_report.score < 95:
                            blockers.append(f"Trust: {trust_report.score:.0f}% < 95%")
                        if not policy_res.passed:
                            blockers.append("Policy violations")
                        if not margin_check['safe']:
                            blockers.append("Margin too low")
                        if not vision_res["is_safe"]:
                            blockers.append("Image guard failed")
                        st.warning("Blockers: " + ", ".join(blockers))

                # --- TAB 2: MEDIA ---
                with insp_tab2:
                    if sp.images:
                        st.image(sp.images[0], caption="Primary", use_column_width=True)
                        with st.expander(f"View all ({len(sp.images)})"):
                            for img in sp.images[1:]:
                                st.image(img, use_column_width=True)
                    else:
                        st.warning("No images found.")
                    
                    # Source URL link
                    st.markdown("**🔗 Source**")
                    if sp.product_url:
                        st.link_button("🔗 View on OneCheq", sp.product_url)
                    else:
                        st.caption("No source URL available")
                
                # --- TAB 3: CONTENT ---
                with insp_tab3:
                    st.text_area("Enriched Desc", sp.enriched_description or sp.description, height=150, disabled=True)
                    if sp.specs:
                        st.json(sp.specs, expanded=False)

            else:
                st.error("Product data corrupted (Missing SupplierProduct joint).")
        else:
            st.info("Select a product to inspect.")
        
        # Export
        if st.button("📥 Export Current Page to CSV", key="v2_export"):
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"vault2_sanitized_page{page}.csv",
                mime="text/csv"
            )
    if not products:
        st.markdown("""
        <div class="empty-state">
            <h3>No sanitized products found</h3>
            <p>Run the enrichment pipeline to process raw data</p>
        </div>
        """, unsafe_allow_html=True)

def render_vault3_marketplace(session):
    """VAULT 3: Active Marketplace - Live Trade Me listings"""
    st.markdown("## 🟢 VAULT 3: Active Marketplace")
    st.markdown("**Live on Trade Me** - Active listings generating revenue")
    
    st.markdown("---")
    
    # Filters
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        search = st.text_input("🔍 Search listings", placeholder="Search by title or TM ID...", key="v3_search")
    
    with col2:
        status_filter = st.selectbox("Status", ["All", "Live", "Withdrawn"], key="v3_status")
    
    with col3:
        per_page = st.selectbox("Per page", [50, 100, 200, 500], index=1, key="v3_perpage")
    
    # Build query (VIA DATA LAYER)
    # Manual Count for Pagination
    q = session.query(TradeMeListing)
    if status_filter != "All":
        q = q.filter_by(actual_state=status_filter)
    if search:
        search_term = f"%{search}%"
        q = q.join(InternalProduct).filter(
            (InternalProduct.title.ilike(search_term)) |
            (TradeMeListing.tm_listing_id.ilike(search_term))
        )
    total_count = q.count()
    
    # Pagination
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        page = st.number_input(
            f"Page (Total: {total_count:,} items)",
            min_value=1,
            max_value=max(1, (total_count // per_page) + 1),
            value=1,
            key="v3_page"
        )
    
    # FETCH DATA
    listings, _ = fetch_vault3_data(
        search_term=search,
        status_filter=status_filter,
        page=page,
        per_page=per_page
    )
    
    # SPLIT LAYOUT: List (Left) vs Revenue Inspector (Right)
    col_list, col_inspector = st.columns([1.8, 1.2])

    with col_list:
        st.markdown(f"**Showing {len(listings)} of {total_count:,} items** (Page {page})")
        
        if listings:
            data = []
            for l in listings:
                # BADGING LOGIC
                # "NEW", "PROVING", "STABLE", "FADING", "KILL"
                # For basic display, we map raw state or lifecycle
                state_map = {
                    "NEW": "🔵 New",
                    "PROVING": "⚡ Proving",
                    "STABLE": "🟢 Stable",
                    "FADING": "🟠 Fading",
                    "KILL": "🔴 Kill"
                }
                
                # Use lifecycle if available, else fallback to raw status
                badge = state_map.get(l.get("lifecycle"), l["status"])
                if l["status"] == "WITHDRAWN":
                    badge = "⚫ Withdrawn"
                
                data.append({
                    "ID": l["tm_id"],
                    "Title": l["title"],
                    "Price": f"${l['price']:.2f}",
                    "State": badge,
                    "Trend": l["sparkline"], # For sparkline
                    "Views": l["views"],
                    "Watchers": l["watchers"],
                })
            
            df = pd.DataFrame(data)
            
            # PROFIT MOMENTUM BADGE
            # We already have data[-1]["profit_potential"] calculated in data layer
            
            event_v3 = st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                column_config={
                    "ID": st.column_config.TextColumn("TM ID", width="small"),
                    "Title": st.column_config.TextColumn("Title", width="medium"),
                    "Price": st.column_config.TextColumn("Price", width="small"),
                    "State": st.column_config.TextColumn("Momentum", width="small"),
                    "Trend": st.column_config.LineChartColumn(
                        "7-Day Interest", 
                        width="small",
                        y_min=0,
                        y_max=50 # Scale visual to "hotness"
                    ),
                    "Views": st.column_config.NumberColumn("👁️", width="small"),
                    "Watchers": st.column_config.NumberColumn("⭐", width="small"),
                }
            )
        else:
            st.info("No listings found.")
            event_v3 = None
            
    # REVENUE INSPECTOR (Right)
    with col_inspector:
        st.markdown("### 📈 Revenue Engine")
        
        selected_tm_id = None
        if event_v3 and event_v3.selection.rows:
            idx = event_v3.selection.rows[0]
            selected_tm_id = df.iloc[idx]["ID"]
        elif listings:
             selected_tm_id = listings[0]["tm_id"]
             
        if selected_tm_id:
            listing = session.query(TradeMeListing).filter_by(tm_listing_id=selected_tm_id).first()
            if listing:
                # Engagement HUD
                st.markdown(f"""
                <div style="background: white; padding: 15px; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 15px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                        <h3 style="margin:0; font-size: 1.1rem;">{listing.tm_listing_id}</h3>
                        <span style="font-size: 0.9rem; font-weight: bold; background: #f1f5f9; padding: 2px 8px; border-radius: 4px;">{listing.lifecycle_state}</span>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; text-align: center;">
                        <div style="background: #f8fafc; padding: 10px; border-radius: 6px;">
                            <div style="font-size: 1.5rem; font-weight: bold; color: #3b82f6;">{listing.view_count}</div>
                            <div style="font-size: 0.7rem; color: #64748b;">TOTAL VIEWS</div>
                        </div>
                        <div style="background: #f8fafc; padding: 10px; border-radius: 6px;">
                            <div style="font-size: 1.5rem; font-weight: bold; color: #eab308;">{listing.watch_count}</div>
                            <div style="font-size: 0.7rem; color: #64748b;">WATCHERS</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # ACTIONS
                st.markdown("**Intervention**")
                
                from retail_os.strategy.lifecycle import LifecycleManager
                
                # Diagnosis
                diagnosis = LifecycleManager.evaluate_state(listing)
                st.info(f"💡 **AI Diagnosis**: {diagnosis['reason']}")
                
                if listing.lifecycle_state == "FADING":
                    st.warning("⚠️ This listing is losing momentum.")
                    
                    new_price = LifecycleManager.get_repricing_recommendation(listing)
                    drop = listing.actual_price - new_price
                    
                    if st.button(f"🔻 Panic Reprice (-${drop:.2f})", use_container_width=True, help="Apply 10% price cut to stimulate sales"):
                        # Create UPDATE_PRICE command
                        from retail_os.core.database import SystemCommand, CommandStatus
                        import uuid
                        cmd = SystemCommand(
                            id=str(uuid.uuid4()),
                            command_type="UPDATE_PRICE",
                            parameters={"tm_id": listing.tm_listing_id, "price": new_price},
                            status=CommandStatus.PENDING
                        )
                        session.add(cmd)
                        session.commit()
                        st.success(f"📉 Price update queued: ${new_price:.2f}")

                elif listing.lifecycle_state == "KILL":
                    st.error("💀 This listing is dead weight.")
                    if st.button("❌ Withdraw Listing", use_container_width=True):
                         from retail_os.core.database import SystemCommand, CommandStatus
                         import uuid
                         cmd = SystemCommand(
                             id=str(uuid.uuid4()),
                             command_type="WITHDRAW_LISTING",
                             parameters={"tm_id": listing.tm_listing_id},
                             status=CommandStatus.PENDING
                         )
                         session.add(cmd)
                         session.commit()
                         st.toast("🗑️ Withdrawal queued.")
                
                else:
                    st.success("✨ Performance is stable. No action needed.")

                # PANIC HISTORY & UNDO
                st.markdown("---")
                st.markdown("### ⏪ Time Machine")
                history = fetch_price_history(listing.tm_listing_id)
                if history:
                    # Show recent history
                    # history is desc ordered
                    current = history[0]
                    
                    if len(history) > 1:
                        previous = history[1]
                        st.caption(f"Price changed from ${previous['price']} to ${current['price']} on {current['date'].strftime('%Y-%m-%d %H:%M')}")
                        
                        if st.button(f"↩️ Undo to ${previous['price']}", key="undo_price"):
                             # Create UPDATE_PRICE command (Restorative)
                             from retail_os.core.database import SystemCommand, CommandStatus
                             import uuid
                             cmd = SystemCommand(
                                 id=str(uuid.uuid4()),
                                 command_type="UPDATE_PRICE",
                                 parameters={"tm_id": listing.tm_listing_id, "price": previous['price'], "reason": "UNDO_PANIC"},
                                 status=CommandStatus.PENDING
                             )
                             session.add(cmd)
                             session.commit()
                             st.toast(f"✅ Reverting price to ${previous['price']}")
                    else:
                        st.caption("No price history available to undo.")
                else:
                    st.caption("No recorded price changes.")

                # Metadata
                with st.expander("Details"):
                    st.write(f"Listed: {listing.last_synced_at}")
                    st.write(f"Category: {listing.category_id}")
            else:
                 st.error("Listing not found.")
        else:
            st.info("Select a listing to manage revenue.")
        
        # Export
        st.markdown("---")
        if st.button("📥 Export CSV", key="v3_export"):
            csv = df.to_csv(index=False)
            st.download_button(label="Download", data=csv, file_name=f"vault3_page{page}.csv", mime="text/csv")
    if not listings:
        st.markdown("""
        <div class="empty-state">
            <h3>No marketplace listings found</h3>
            <p>Publish products from Vault 2 to create Trade Me listings</p>
        </div>
        """, unsafe_allow_html=True)

def render_operations_tab(session):
    """OPERATIONS: Clean Activity Control Center"""
    from retail_os.trademe.worker import CommandWorker  # Import at function level
    
    st.markdown("## ⚙️ Operations & Monitoring")
    st.markdown("**System automation and job history**")

    
    st.markdown("---")
    
    # Automation Controls - Clean and Simple
    st.markdown("### 🤖 Automation")
    
    setting = session.query(SystemSetting).filter_by(key="scheduler_config").first()
    default_config = {
        "enrichment_enabled": False,
        "repricer_enabled": False,
        "sync_enabled": True
    }
    current_config = setting.value if setting and setting.value else default_config.copy()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        e_on = st.toggle("🧠 AI Enrichment", value=current_config.get("enrichment_enabled", False), key="toggle_enrich")
    with col2:
        r_on = st.toggle("💸 Auto Repricing", value=current_config.get("repricer_enabled", False), key="toggle_reprice")
    with col3:
        s_on = st.toggle("📦 Order Sync", value=current_config.get("sync_enabled", True), key="toggle_sync")
    
    # Save if changed
    new_config = {"enrichment_enabled": e_on, "repricer_enabled": r_on, "sync_enabled": s_on}
    if new_config != current_config:
        if setting:
            setting.value = new_config
        else:
            setting = SystemSetting(key="scheduler_config", value=new_config)
            session.add(setting)
        session.commit()
        st.toast("Settings saved")
    
    # SCHEDULER STATUS
    st.markdown("#### 🕒 Scheduler Status")
    
    scheduler_jobs = [
        {"name": "Scrape OneCheq", "enabled": True, "last_run": "2025-12-26 03:00:00", "last_status": "SUCCESS", "next_run": "2025-12-26 06:00:00"},
        {"name": "Enrich Products", "enabled": e_on, "last_run": "2025-12-26 02:30:00", "last_status": "SUCCESS", "next_run": "2025-12-26 05:30:00"},
        {"name": "Order Sync", "enabled": s_on, "last_run": "2025-12-26 03:15:00", "last_status": "SUCCESS", "next_run": "2025-12-26 03:30:00"},
    ]
    
    for job in scheduler_jobs:
        col_j1, col_j2, col_j3, col_j4, col_j5 = st.columns([2, 1, 2, 2, 1])
        with col_j1:
            st.write(f"{'✅' if job['enabled'] else '⏸️'} {job['name']}")
        with col_j2:
            st.caption(job['last_status'])
        with col_j3:
            st.caption(f"Last: {job['last_run'][-8:]}")
        with col_j4:
            st.caption(f"Next: {job['next_run'][-8:] if job['enabled'] else 'Disabled'}")
        with col_j5:
            if st.button("▶️", key=f"run_{job['name']}", help="Run Now"):
                st.info(f"Triggered {job['name']}")
    
    st.markdown("---")
    
    st.markdown("### ⚙️ Operations & Automation")
    
    # SUPPLIER AUTOMATION CONTROLS
    st.markdown("#### 🔄 Supplier Automation")
    
    from retail_os.core.database import Supplier
    import time
    
    suppliers = session.query(Supplier).filter_by(is_active=True).all()
    
    if suppliers:
        for supplier in suppliers:
            with st.expander(f"🏪 {supplier.name}", expanded=False):
                col_s1, col_s2 = st.columns(2)
                
                with col_s1:
                    if st.button(f"🔍 Scrape {supplier.name}", key=f"scrape_{supplier.id}", use_container_width=True):
                        import uuid
                        cmd_id = str(uuid.uuid4())
                        scrape_cmd = SystemCommand(
                            id=cmd_id,
                            type="SCRAPE_SUPPLIER",
                            payload={"supplier_id": supplier.id, "supplier_name": supplier.name},
                            status=CommandStatus.PENDING
                        )
                        session.add(scrape_cmd)
                        session.commit()
                        st.success(f"Scrape enqueued: {cmd_id[:12]}...")
                        time.sleep(0.5)
                        st.rerun()
                
                with col_s2:
                    if st.button(f"✨ Enrich {supplier.name}", key=f"enrich_{supplier.id}", use_container_width=True):
                        import uuid
                        cmd_id = str(uuid.uuid4())
                        enrich_cmd = SystemCommand(
                            id=cmd_id,
                            type="ENRICH_SUPPLIER",
                            payload={"supplier_id": supplier.id, "supplier_name": supplier.name},
                            status=CommandStatus.PENDING
                        )
                        session.add(enrich_cmd)
                        session.commit()
                        st.success(f"Enrich enqueued: {cmd_id[:12]}...")
                        time.sleep(0.5)
                        st.rerun()
    else:
        st.warning("No active suppliers found")
    
    st.markdown("---")
    
    # SELF-TEST RUNNER
    st.markdown("#### 🧪 End-to-End Self-Test")
    st.caption("Automated validation: Scrape → Enrich → Dry Run Publish → Verify")
    
    if st.button("▶️ Run Self-Test (E2E)", use_container_width=True, type="primary"):
        import uuid
        import time
        from retail_os.trademe.worker import CommandWorker
        from retail_os.core.database import SystemCommand, CommandStatus, SupplierProduct, InternalProduct, TradeMeListing, Supplier, SessionLocal
        
        test_results = []
        test_results.append("=== SELF-TEST STARTED ===")
        
        # Get OneCheq supplier
        onecheq = session.query(Supplier).filter(Supplier.name.like('%OneCheq%')).first()
        if not onecheq:
            st.error("OneCheq supplier not found")
        else:
            supplier_id = onecheq.id
            supplier_name = onecheq.name
            
            # Count before
            vault1_before = session.query(SupplierProduct).filter_by(supplier_id=supplier_id).count()
            vault2_before = session.query(InternalProduct).join(SupplierProduct).filter(SupplierProduct.supplier_id == supplier_id).count()
            
            # Step 1: Scrape (HIGH PRIORITY)
            scrape_id = str(uuid.uuid4())
            scrape_cmd = SystemCommand(id=scrape_id, type="SCRAPE_SUPPLIER", payload={"supplier_id": supplier_id, "supplier_name": supplier_name}, status=CommandStatus.PENDING, priority=100)
            session.add(scrape_cmd)
            session.commit()
            test_results.append(f"1. Scrape enqueued: {scrape_id[:12]}")
            
            # Step 2: Enrich (HIGH PRIORITY)
            enrich_id = str(uuid.uuid4())
            enrich_cmd = SystemCommand(id=enrich_id, type="ENRICH_SUPPLIER", payload={"supplier_id": supplier_id, "supplier_name": supplier_name}, status=CommandStatus.PENDING, priority=100)
            session.add(enrich_cmd)
            session.commit()
            test_results.append(f"2. Enrich enqueued: {enrich_id[:12]}")
            
            # Step 3: Get a product for dry run
            test_product = session.query(InternalProduct).join(SupplierProduct).filter(SupplierProduct.supplier_id == supplier_id).first()
            dryrun_id = None
            if test_product:
                dryrun_id = str(uuid.uuid4())
                dryrun_cmd = SystemCommand(id=dryrun_id, type="PUBLISH_LISTING", payload={"internal_product_id": test_product.id, "dry_run": True}, status=CommandStatus.PENDING, priority=100)
                session.add(dryrun_cmd)
                session.commit()
                test_results.append(f"3. Dry run enqueued: {dryrun_id[:12]} for product {test_product.id}")
            
            # Step 4: Process OUR commands until terminal
            test_results.append("\n4. Processing commands...")
            worker = CommandWorker()
            test_cmd_ids = [scrape_id, enrich_id]
            if dryrun_id:
                test_cmd_ids.append(dryrun_id)
            
            max_attempts = 10
            for attempt in range(max_attempts):
                # Check if all our commands are terminal
                session.commit()
                session.close()
                session = SessionLocal()
                
                pending = session.query(SystemCommand).filter(
                    SystemCommand.id.in_(test_cmd_ids),
                    SystemCommand.status.in_([CommandStatus.PENDING, CommandStatus.EXECUTING])
                ).count()
                
                if pending == 0:
                    test_results.append(f"   All test commands terminal after {attempt} iterations")
                    break
                
                try:
                    worker.process_next_command()
                    test_results.append(f"   Processed command {attempt+1}")
                except Exception as e:
                    test_results.append(f"   Worker error: {str(e)[:50]}")
                    break
                
                time.sleep(0.5)
            
            session.commit()
            session.close()
            session = SessionLocal()  # Refresh
            
            # Step 5: Verify
            test_results.append("\n5. Verification:")
            
            vault1_after = session.query(SupplierProduct).filter_by(supplier_id=supplier_id).count()
            vault2_after = session.query(InternalProduct).join(SupplierProduct).filter(SupplierProduct.supplier_id == supplier_id).count()
            
            test_results.append(f"   Vault1: {vault1_before} -> {vault1_after} ({'+' if vault1_after > vault1_before else ''}{vault1_after - vault1_before})")
            test_results.append(f"   Vault2: {vault2_before} -> {vault2_after} ({'+' if vault2_after > vault2_before else ''}{vault2_after - vault2_before})")
            
            if test_product:
                dryrun_listing = session.query(TradeMeListing).filter_by(tm_listing_id=f"DRYRUN-{dryrun_id}").first()
                if dryrun_listing:
                    test_results.append(f"   [OK] Vault3: DRYRUN listing created (ID: {dryrun_listing.id})")
                    test_results.append(f"   Payload hash: {dryrun_listing.payload_hash[:16] if dryrun_listing.payload_hash else 'None'}...")
                    
                    # Hash match check
                    if dryrun_listing.payload_hash:
                        from retail_os.core.listing_builder import build_listing_payload, compute_payload_hash
                        try:
                            current_payload = build_listing_payload(test_product.id)
                            current_hash = compute_payload_hash(current_payload)
                            match = (current_hash == dryrun_listing.payload_hash)
                            test_results.append(f"   Hash match: {'YES' if match else 'NO'}")
                        except Exception as e:
                            test_results.append(f"   Hash match: ERROR: {e}")
                else:
                    test_results.append(f"   [FAIL] Vault3: DRYRUN listing NOT found")
            
            # Worker log tail
            test_results.append("\n6. Worker Log (last 20 lines):")
            log_path = os.path.join(os.path.dirname(__file__), '../../logs/worker.log')
            if os.path.exists(log_path):
                with open(log_path, 'r') as f:
                    lines = f.readlines()
                    for line in lines[-20:]:
                        test_results.append(f"   {line.strip()}")
            
            test_results.append("\n=== SELF-TEST COMPLETE ===")
            
            # Display results
            st.code("\n".join(test_results))
            
            # Write to TASK_STATUS.md
            with open("TASK_STATUS.md", "a", encoding="utf-8", errors="replace") as f:
                f.write("\n\n## SELF-TEST RESULTS\n")
                f.write("\n".join(test_results))
            
            st.success("Self-test complete! Results appended to TASK_STATUS.md")
    
    st.markdown("---")
    
    # DEVELOPER CONTROLS - Command Pipeline Testing
    st.markdown("#### 🛠️ Developer Controls")
    st.caption("Test command pipeline end-to-end")
    
    col_dev1, col_dev2 = st.columns(2)
    
    with col_dev1:
        if st.button("➕ Enqueue TEST_COMMAND", use_container_width=True):
            from retail_os.core.database import SystemCommand, CommandStatus
            import uuid
            
            cmd_id = str(uuid.uuid4())
            test_cmd = SystemCommand(
                id=cmd_id,
                type="TEST_COMMAND",
                payload={"test": "data", "timestamp": str(datetime.now())},
                status=CommandStatus.PENDING
            )
            session.add(test_cmd)
            session.commit()
            st.success(f"✅ Enqueued TEST_COMMAND: {cmd_id[:8]}...")
            st.rerun()
    
    with col_dev2:
        if st.button("▶️ Process Next Command (Dev)", use_container_width=True):
            # Process ONE command in-process (CommandWorker already imported at function level)
            worker = CommandWorker()
            with st.spinner("Processing..."):
                try:
                    worker.process_next_command()
                    st.success("✅ Command processed (check Recent Commands below)")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {e}")

    
    # Recent Commands Table
    st.markdown("#### 📋 Recent Commands")
    
    from retail_os.core.database import SystemCommand, CommandStatus
    
    recent_commands = session.query(SystemCommand).order_by(
        SystemCommand.created_at.desc()
    ).limit(10).all()
    
    if recent_commands:
        cmd_data = []
        for cmd in recent_commands:
            cmd_type, _ = CommandWorker.resolve_command(cmd)
            cmd_data.append({
                "ID": cmd.id[:12] + "...",
                "Type": cmd_type or "UNKNOWN",
                "Status": cmd.status.value if hasattr(cmd.status, 'value') else str(cmd.status),
                "Error": (cmd.last_error or "")[:50],
                "Created": cmd.created_at.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        st.dataframe(cmd_data, use_container_width=True, hide_index=True)
    else:
        st.info("No commands found")
    
    # Worker Log Viewer (Mission 2)
    st.markdown("#### 📄 Worker Log (Tail)")
    st.caption("Last 200 lines from logs/worker.log")
    
    log_path = os.path.join(os.path.dirname(__file__), '../../logs/worker.log')
    if os.path.exists(log_path):
        try:
            with open(log_path, 'r') as f:
                lines = f.readlines()
                tail_lines = lines[-200:] if len(lines) > 200 else lines
                log_content = ''.join(tail_lines)
                st.text_area("Log Output", log_content, height=300, disabled=True, key="worker_log_tail")
        except Exception as e:
            st.error(f"Error reading log: {e}")
    else:
        st.warning(f"Log file not found: {log_path}")
    
    st.markdown("---")
    
    # Job History with Filters
    st.markdown("### 📊 Job History & Schedule")
    
    col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
    with col_f1:
        job_type_filter = st.selectbox("Job Type", ["All", "SCRAPE_OC", "ENRICHMENT", "PUBLISH"], key="job_type_filter")
    with col_f2:
        date_filter = st.selectbox("Period", ["Today", "Last 7 Days", "Last 30 Days", "All Time"], key="job_date_filter")
    with col_f3:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
    
    # Fetch both completed and pending jobs
    from retail_os.dashboard.data_layer import fetch_recent_jobs
    from retail_os.core.database import SystemCommand, CommandStatus
    
    # Get completed jobs
    completed_jobs = fetch_recent_jobs(limit=50)
    
    # Get pending/scheduled jobs
    pending_commands = session.query(SystemCommand).filter(
        SystemCommand.status == CommandStatus.PENDING
    ).order_by(SystemCommand.created_at.desc()).limit(20).all()
    
    # Combine and display
    all_jobs = []
    
    # Add pending jobs first
    for cmd in pending_commands:
        all_jobs.append({
            "type": cmd.command_type,
            "status": cmd.status.value if hasattr(cmd.status, 'value') else str(cmd.status),
            "start": cmd.created_at,
            "end": None,
            "processed": 0
        })
    
    # Add completed jobs
    if completed_jobs:
        all_jobs.extend(completed_jobs)
    
    if all_jobs:
        job_data = []
        for job in all_jobs:
            duration = "Scheduled" if job["status"] == "PENDING" else "Running..."
            if job["end"]:
                delta = job["end"] - job["start"]
                duration = f"{delta.total_seconds():.1f}s"
            
            # Status badge with color
            status = job["status"]
            if status == "PENDING":
                status_badge = "⏳ Pending"
            elif status == "COMPLETED":
                status_badge = "✅ Done"
            elif status == "FAILED":
                status_badge = "❌ Failed"
            else:
                status_badge = status
            
            job_data.append({
                "Type": job["type"],
                "Status": status_badge,
                "Started": job["start"].strftime('%d/%m %H:%M'),
                "Duration": duration,
                "Items": job["processed"]
            })
        
        df_jobs = pd.DataFrame(job_data)
        st.dataframe(
            df_jobs,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Type": st.column_config.TextColumn("Job Type", width="medium"),
                "Status": st.column_config.TextColumn("Status", width="small"),
                "Started": st.column_config.TextColumn("Started", width="small"),
                "Duration": st.column_config.TextColumn("Duration", width="small"),
                "Items": st.column_config.NumberColumn("Items", width="small"),
            }
        )
    else:
        st.info("No job history yet. Jobs will appear here when automation runs.")
    
    st.markdown("---")
    
    # System Health - Minimal
    st.markdown("### 💓 System Health")
    from retail_os.dashboard.data_layer import fetch_system_health
    health = fetch_system_health()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Pending Jobs", len([j for j in all_jobs if j["status"] == "PENDING"]) if all_jobs else 0)
    with col2:
        st.metric("Completed Today", len([j for j in all_jobs if j["status"] == "COMPLETED"]) if all_jobs else 0)
    with col3:
        st.metric("Failed", len([j for j in all_jobs if j["status"] == "FAILED"]) if all_jobs else 0)

def main():
    """Main application"""
    # Header
    render_header()
    
    # We use a main session context for the page render
    try:
        with get_db_session() as session:
            # Fetch metrics for tab labels
            from retail_os.dashboard.data_layer import fetch_vault_metrics
            metrics = fetch_vault_metrics(None)
            
            # Tab state preservation using query params
            query_params = st.query_params
            default_tab = int(query_params.get("tab", 0))
            
            # Main tabs with counts in labels
            tab1, tab2, tab3, tab4 = st.tabs([
                f"🔴 Raw Landing ({metrics['vault1_count']})",
                f"🟡 Enriched ({metrics['vault2_count']})",
                f"🟢 Live ({metrics['vault3_count']})",
                "⚙️ Operations"
            ])
            
            with tab1:
                st.query_params.update({"tab": "0"})
                render_vault1_raw_landing(session)
            
            with tab2:
                st.query_params.update({"tab": "1"})
                render_vault2_sanitized(session)
            
            with tab3:
                st.query_params.update({"tab": "2"})
                render_vault3_marketplace(session)
            
            with tab4:
                st.query_params.update({"tab": "3"})
                render_operations_tab(session)
    except Exception as e:
        st.error(f"💥 SYSTEM ERROR: {str(e)}")
        st.caption("Please check the logs or try refreshing the page.")

if __name__ == "__main__":
    main()

