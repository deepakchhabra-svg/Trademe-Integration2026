import os
import sys
import time
from datetime import datetime

import pandas as pd
import streamlit as st

# Ensure retail_os is in path (Streamlit runs from repo root in most setups)
sys.path.append(os.getcwd())

from retail_os.core.database import (
    CommandStatus,
    InternalProduct,
    Supplier,
    SupplierProduct,
    SystemCommand,
    SystemSetting,
    TradeMeListing,
    get_db_session,
)
from retail_os.dashboard.data_layer import (
    fetch_orders,
    fetch_price_history,
    fetch_system_health,
    fetch_vault1_data,
    fetch_vault2_data,
    fetch_vault3_data,
    fetch_vault_metrics,
    submit_publish_command,
)


st.set_page_config(
    page_title="RetailOS | Trade Me Intelligence",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def inject_theme() -> None:
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
  font-family: 'Inter', sans-serif;
}

.stApp {
  background-color: #f5f7fb;
}

header { visibility: hidden; }

.block-container { padding-top: 4.5rem !important; }

.top-bar {
  background: #0f172a;
  color: white;
  padding: 0.9rem 1.5rem;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 9999;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 4px 10px rgba(15, 23, 42, 0.18);
}
.app-title { font-size: 1.05rem; font-weight: 700; letter-spacing: -0.02em; }
.app-subtitle { font-size: 0.85rem; color: #94a3b8; }

.main-header {
  background: linear-gradient(135deg, #232f3f 0%, #1a2533 100%);
  color: white;
  padding: 1.25rem 1.25rem;
  border-radius: 14px;
  margin-bottom: 1.25rem;
  box-shadow: 0 10px 22px rgba(15, 23, 42, 0.12);
  border-bottom: 4px solid #eb8f04;
}
.main-header h2 { margin: 0; font-size: 1.6rem; font-weight: 800; }
.main-header p { margin: 0.25rem 0 0 0; color: #e2e8f0; font-weight: 500; }

.empty-state {
  text-align: center;
  padding: 3rem 2rem;
  background: white;
  border-radius: 14px;
  border: 2px dashed #e2e8f0;
}
.empty-state h3 { margin: 0; color: #0f172a; font-weight: 700; }
.empty-state p { margin: 0.35rem 0 0 0; color: #64748b; }

</style>

<div class="top-bar">
  <div class="app-title">📊 RetailOS • Trade Me Intelligence</div>
  <div class="app-subtitle">Navy/Amber Console • DB-backed</div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_global_alerts() -> None:
    try:
        health = fetch_system_health()
    except Exception:
        return

    heartbeats = (health or {}).get("heartbeats", {}) or {}
    failures = [(job_type, info) for job_type, info in heartbeats.items() if info.get("status") == "FAILED"]

    if failures:
        for job_type, info in failures[:3]:
            st.error(f"🚨 {job_type} FAILED (last run: {info.get('last_run')})")


def render_header() -> None:
    render_global_alerts()
    st.markdown(
        """
<div class="main-header">
  <h2>Trade Me Integration Platform</h2>
  <p>Vaults (Raw → Enriched → Live) + Orders + Operations</p>
</div>
""",
        unsafe_allow_html=True,
    )


def paginator(total_count: int, per_page: int, key: str) -> int:
    per_page = max(int(per_page), 1)
    total_pages = max(1, (int(total_count) + per_page - 1) // per_page)
    if key not in st.session_state:
        st.session_state[key] = 1

    # Clamp
    st.session_state[key] = max(1, min(int(st.session_state[key]), total_pages))

    c1, c2, c3, c4 = st.columns([1, 2, 2, 1])
    with c1:
        if st.button("◀", key=f"{key}_prev", use_container_width=True, disabled=st.session_state[key] <= 1):
            st.session_state[key] -= 1
            st.rerun()
    with c2:
        st.caption(f"Page {st.session_state[key]} of {total_pages}")
    with c3:
        page = st.number_input(
            "Go to page",
            min_value=1,
            max_value=total_pages,
            value=int(st.session_state[key]),
            key=f"{key}_input",
            label_visibility="collapsed",
        )
        if int(page) != int(st.session_state[key]):
            st.session_state[key] = int(page)
            st.rerun()
    with c4:
        if st.button("▶", key=f"{key}_next", use_container_width=True, disabled=st.session_state[key] >= total_pages):
            st.session_state[key] += 1
            st.rerun()

    return int(st.session_state[key])


def empty_state(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
<div class="empty-state">
  <h3>{title}</h3>
  <p>{subtitle}</p>
</div>
""",
        unsafe_allow_html=True,
    )


def render_vault1(session) -> None:
    st.subheader("🔴 Vault 1 — Raw Landing")
    st.caption("Scraped supplier products (unprocessed).")

    suppliers = session.query(Supplier).order_by(Supplier.name.asc()).all()
    supplier_opts = [("All Suppliers", None)] + [(s.name, s.id) for s in suppliers]

    f1, f2, f3, f4 = st.columns([2, 1, 1, 1])
    with f1:
        search = st.text_input("Search", placeholder="SKU / title keyword", key="v1_search")
    with f2:
        supplier_name = st.selectbox("Supplier", [x[0] for x in supplier_opts], key="v1_supplier")
        supplier_id = dict(supplier_opts).get(supplier_name)
    with f3:
        sync_status = st.selectbox("Status", ["All", "PRESENT", "MISSING_ONCE", "REMOVED"], key="v1_status")
    with f4:
        per_page = st.selectbox("Per page", [50, 100, 200, 500], index=1, key="v1_per_page")

    # Use data layer for count + page rows (same filters)
    products, total = fetch_vault1_data(
        search_term=search or None,
        supplier_id=supplier_id,
        sync_status=sync_status,
        page=1,
        per_page=per_page,
    )
    page = paginator(total, per_page, "v1_page")
    products, total = fetch_vault1_data(
        search_term=search or None,
        supplier_id=supplier_id,
        sync_status=sync_status,
        page=page,
        per_page=per_page,
    )

    st.markdown(f"**Showing {len(products)} of {total:,}**")
    if not products:
        empty_state("No raw products found", "Adjust filters or run a supplier scrape.")
        return

    df = pd.DataFrame(products)
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
            "price": st.column_config.NumberColumn("Cost", width="small", format="$%.2f"),
            "status": st.column_config.TextColumn("Sync", width="small"),
            "last_scraped": st.column_config.DatetimeColumn("Scraped", width="small"),
        },
    )

    csv = df.to_csv(index=False)
    st.download_button("📥 Download page CSV", data=csv, file_name=f"vault1_page_{page}.csv", mime="text/csv")

    selected_id = None
    if event.selection.rows:
        selected_id = int(df.iloc[event.selection.rows[0]]["id"])

    if not selected_id:
        st.info("Select a row to inspect.")
        return

    product = session.query(SupplierProduct).filter_by(id=selected_id).first()
    if not product:
        st.error("Selected product not found (stale row).")
        return

    st.divider()
    st.subheader(f"📦 {product.title or '(no title)'}")
    st.caption(f"SupplierProduct #{product.id} • SKU {product.external_sku} • Supplier {product.supplier.name if product.supplier else 'Unknown'}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cost", f"${float(product.cost_price):.2f}" if product.cost_price is not None else "N/A")
    c2.metric("Brand", product.brand or "N/A")
    c3.metric("Condition", product.condition or "N/A")
    c4.metric("Images", len(product.images or []))

    if product.images:
        st.markdown("#### Images")
        cols = st.columns(min(4, len(product.images)))
        for idx, img in enumerate(product.images[:4]):
            with cols[idx]:
                if isinstance(img, str) and os.path.exists(img):
                    st.image(img, use_container_width=True)
                else:
                    st.caption(img if isinstance(img, str) else "N/A")

    st.markdown("#### Description")
    st.text_area("Raw description", value=product.description or "", height=160, disabled=True)

    st.markdown("#### Specs")
    if isinstance(product.specs, dict) and product.specs:
        st.json(product.specs, expanded=False)
    else:
        st.caption("No structured specs.")

    if product.product_url:
        st.link_button("🔗 Open source URL", product.product_url)


def render_vault2(session) -> None:
    st.subheader("🟡 Vault 2 — Enriched / Launch Gate")
    st.caption("Internal products + trust/policy checks before publishing.")

    suppliers = session.query(Supplier).order_by(Supplier.name.asc()).all()
    supplier_opts = [("All Suppliers", None)] + [(s.name, s.id) for s in suppliers]

    f1, f2, f3, f4 = st.columns([2, 1, 1, 1])
    with f1:
        search = st.text_input("Search", placeholder="Title / enriched text", key="v2_search")
    with f2:
        supplier_name = st.selectbox("Supplier", [x[0] for x in supplier_opts], key="v2_supplier")
        supplier_id = dict(supplier_opts).get(supplier_name)
    with f3:
        enrichment_filter = st.selectbox("Enrichment", ["All", "Enriched", "Not Enriched"], key="v2_enrich")
    with f4:
        per_page = st.selectbox("Per page", [25, 50, 100, 200], index=1, key="v2_per_page")

    products, total = fetch_vault2_data(
        search_term=search or None,
        supplier_id=supplier_id,
        enrichment_filter=enrichment_filter,
        page=1,
        per_page=per_page,
    )
    page = paginator(total, per_page, "v2_page")
    products, total = fetch_vault2_data(
        search_term=search or None,
        supplier_id=supplier_id,
        enrichment_filter=enrichment_filter,
        page=page,
        per_page=per_page,
    )

    if not products:
        empty_state("No enriched products found", "Run enrichment or broaden your filters.")
        return

    left, right = st.columns([1.7, 1.3])
    with left:
        df = pd.DataFrame(products)
        df_view = df[["id", "title", "supplier", "cost", "enriched"]].copy()
        event = st.dataframe(
            df_view,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            column_config={
                "id": st.column_config.NumberColumn("ID", width="small"),
                "title": st.column_config.TextColumn("Title", width="large"),
                "supplier": st.column_config.TextColumn("Supplier", width="small"),
                "cost": st.column_config.NumberColumn("Cost", width="small", format="$%.2f"),
                "enriched": st.column_config.CheckboxColumn("Enriched", width="small"),
            },
        )

        csv = df.to_csv(index=False)
        st.download_button("📥 Download page CSV", data=csv, file_name=f"vault2_page_{page}.csv", mime="text/csv")

    selected_id = None
    if event.selection.rows:
        selected_id = int(df_view.iloc[event.selection.rows[0]]["id"])

    with right:
        st.markdown("### Inspector")
        if not selected_id:
            st.info("Select a product to inspect.")
            return

        product = session.query(InternalProduct).filter_by(id=selected_id).first()
        if not product or not product.supplier_product:
            st.error("Product missing supplier link (data integrity issue).")
            return
        sp = product.supplier_product

        from retail_os.core.trust import TrustEngine
        from retail_os.strategy.policy import PolicyEngine
        from retail_os.strategy.pricing import PricingStrategy
        from retail_os.core.image_guard import guard

        trust_report = TrustEngine(session).get_product_trust_report(product)
        policy_res = PolicyEngine().evaluate(product)
        cost = float(sp.cost_price or 0)
        calc_price = PricingStrategy.calculate_price(cost, supplier_name=sp.supplier.name if sp.supplier else None)
        margin_check = PricingStrategy.validate_margin(cost, calc_price)

        st.metric("Trust Score", f"{trust_report.score:.0f}%")
        st.caption("Blockers: " + (", ".join(trust_report.blockers) if trust_report.blockers else "None"))

        st.divider()
        st.markdown("**Listing preview**")
        st.write(f"**Title:** {sp.enriched_title or sp.title or product.title}")
        st.write(f"**Price:** ${PricingStrategy.apply_psychological_rounding(calc_price):.2f}")
        st.write(f"**Supplier:** {sp.supplier.name if sp.supplier else 'Unknown'}")

        desc = sp.enriched_description or sp.description or ""
        with st.expander("Description"):
            st.text(desc)

        img_path = None
        if isinstance(sp.images, list) and sp.images:
            img_path = sp.images[0]
        vision_res = {"is_safe": True, "reason": "No Image"}
        if img_path and isinstance(img_path, str) and os.path.exists(img_path):
            vision_res = guard.check_image(img_path)

        st.divider()
        st.markdown("**Gates**")

        # policy_res can be dict or PolicyResult
        policy_passed = policy_res.get("passed", True) if isinstance(policy_res, dict) else bool(policy_res.passed)
        policy_blockers = policy_res.get("blockers", []) if isinstance(policy_res, dict) else list(policy_res.blockers)

        if policy_passed:
            st.success("✅ Policy passed")
        else:
            st.error("⛔ Policy failed: " + ", ".join(policy_blockers))

        if margin_check.get("safe"):
            st.success("✅ Margin safe")
        else:
            st.error(f"⛔ Margin unsafe: {margin_check.get('reason')}")

        if vision_res.get("is_safe"):
            st.success("✅ Vision guard safe")
        else:
            st.error(f"⛔ Vision blocked: {vision_res.get('reason')}")

        is_publishable = bool(trust_report.is_trusted) and policy_passed and bool(margin_check.get("safe")) and bool(vision_res.get("is_safe"))

        st.divider()
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🧪 Enqueue Dry Run Publish", use_container_width=True):
                import uuid

                cmd = SystemCommand(
                    id=str(uuid.uuid4()),
                    type="PUBLISH_LISTING",
                    payload={"internal_product_id": product.id, "dry_run": True},
                    status=CommandStatus.PENDING,
                )
                session.add(cmd)
                session.commit()
                st.success("Dry run queued.")
                time.sleep(0.3)
                st.rerun()

        with col_b:
            if st.button("🚀 Enqueue Publish", use_container_width=True, disabled=not is_publishable):
                ok, msg, _cmd_id = submit_publish_command(session, product.id)
                if ok:
                    st.success(msg)
                    time.sleep(0.3)
                    st.rerun()
                else:
                    st.error(msg)


def render_vault3(session) -> None:
    st.subheader("🟢 Vault 3 — Live Marketplace")
    st.caption("Trade Me listings + lifecycle and basic interventions.")

    f1, f2, f3 = st.columns([2, 1, 1])
    with f1:
        search = st.text_input("Search", placeholder="Title / TM listing ID", key="v3_search")
    with f2:
        status_filter = st.selectbox("Status", ["All", "Live", "Withdrawn", "DRY_RUN"], key="v3_status")
    with f3:
        per_page = st.selectbox("Per page", [25, 50, 100, 200], index=1, key="v3_per_page")

    listings, total = fetch_vault3_data(search_term=search or None, status_filter=status_filter, page=1, per_page=per_page)
    page = paginator(total, per_page, "v3_page")
    listings, total = fetch_vault3_data(search_term=search or None, status_filter=status_filter, page=page, per_page=per_page)

    if not listings:
        empty_state("No listings found", "Publish from Vault 2, or broaden your filters.")
        return

    left, right = st.columns([1.7, 1.3])
    with left:
        df = pd.DataFrame(listings)
        df_view = df[["tm_id", "title", "status", "lifecycle", "price", "views", "watchers"]].copy()
        event = st.dataframe(
            df_view,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            column_config={
                "tm_id": st.column_config.TextColumn("TM ID", width="small"),
                "title": st.column_config.TextColumn("Title", width="large"),
                "status": st.column_config.TextColumn("State", width="small"),
                "lifecycle": st.column_config.TextColumn("Lifecycle", width="small"),
                "price": st.column_config.NumberColumn("Price", width="small", format="$%.2f"),
                "views": st.column_config.NumberColumn("Views", width="small"),
                "watchers": st.column_config.NumberColumn("Watchers", width="small"),
            },
        )
        csv = df.to_csv(index=False)
        st.download_button("📥 Download page CSV", data=csv, file_name=f"vault3_page_{page}.csv", mime="text/csv")

    selected_tm_id = None
    if event.selection.rows:
        selected_tm_id = str(df_view.iloc[event.selection.rows[0]]["tm_id"])

    with right:
        st.markdown("### Listing inspector")
        if not selected_tm_id:
            st.info("Select a listing to inspect.")
            return

        listing = session.query(TradeMeListing).filter_by(tm_listing_id=selected_tm_id).first()
        if not listing:
            st.error("Listing not found (stale row).")
            return

        st.metric("Lifecycle", str(listing.lifecycle_state))
        c1, c2 = st.columns(2)
        c1.metric("Views", int(listing.view_count or 0))
        c2.metric("Watchers", int(listing.watch_count or 0))

        st.divider()
        st.markdown("**Actions**")
        if st.button("❌ Enqueue Withdraw", use_container_width=True):
            import uuid

            cmd = SystemCommand(
                id=str(uuid.uuid4()),
                type="WITHDRAW_LISTING",
                payload={"listing_id": listing.tm_listing_id},
                status=CommandStatus.PENDING,
            )
            session.add(cmd)
            session.commit()
            st.success("Withdraw queued.")
            time.sleep(0.3)
            st.rerun()

        st.divider()
        st.markdown("**Price history**")
        history = fetch_price_history(listing.tm_listing_id)
        if history:
            hist_df = pd.DataFrame(
                [{"price": h["price"], "date": h["date"], "type": h.get("type")} for h in history]
            )
            st.dataframe(hist_df, use_container_width=True, hide_index=True)
        else:
            st.caption("No price history recorded.")


def render_orders_tab() -> None:
    st.subheader("📦 Orders")
    st.caption("Sold items imported from Trade Me.")

    orders = fetch_orders(limit=200)
    if not orders:
        empty_state("No orders yet", "Orders will appear here after sold-items sync runs.")
        return

    total_revenue = sum([o["sold_price"] for o in orders if o.get("sold_price") is not None])
    c1, c2, c3 = st.columns(3)
    c1.metric("Total orders", len(orders))
    c2.metric("Revenue", f"${total_revenue:,.2f}")
    c3.metric("Pending fulfillment", sum(1 for o in orders if o.get("fulfillment_status") == "PENDING"))

    df = pd.DataFrame(orders)
    df_view = df[
        [
            "ref",
            "buyer",
            "sold_price",
            "sold_date",
            "order_status",
            "payment_status",
            "fulfillment_status",
            "carrier",
            "tracking_reference",
            "created_at",
        ]
    ].copy()
    st.dataframe(df_view, use_container_width=True, hide_index=True)
    st.download_button("📥 Download orders CSV", data=df.to_csv(index=False), file_name="orders.csv", mime="text/csv")


def render_quality_tab() -> None:
    st.subheader("🧪 Quality Lab")
    from retail_os.dashboard.tabs.quality import render_quality_tab as _render

    _render()


def render_operations(session) -> None:
    st.subheader("⚙️ Operations")

    # Toggles stored in SystemSetting
    setting = session.query(SystemSetting).filter_by(key="scheduler_config").first()
    default_config = {"enrichment_enabled": False, "repricer_enabled": False, "sync_enabled": True}
    current = (setting.value if setting and setting.value else default_config).copy()

    c1, c2, c3 = st.columns(3)
    with c1:
        e_on = st.toggle("🧠 AI Enrichment", value=bool(current.get("enrichment_enabled", False)))
    with c2:
        r_on = st.toggle("💸 Auto Repricing", value=bool(current.get("repricer_enabled", False)))
    with c3:
        s_on = st.toggle("📦 Order Sync", value=bool(current.get("sync_enabled", True)))

    new_cfg = {"enrichment_enabled": e_on, "repricer_enabled": r_on, "sync_enabled": s_on}
    if new_cfg != current:
        if setting:
            setting.value = new_cfg
        else:
            session.add(SystemSetting(key="scheduler_config", value=new_cfg))
        session.commit()
        st.success("Saved scheduler_config.")

    st.divider()
    st.markdown("### 💓 System health")
    health = fetch_system_health()
    heartbeats = (health or {}).get("heartbeats", {}) or {}
    if heartbeats:
        hb_rows = []
        for job_type, info in heartbeats.items():
            hb_rows.append(
                {
                    "job_type": job_type,
                    "status": info.get("status"),
                    "last_run": info.get("last_run"),
                    "duration_s": info.get("duration"),
                }
            )
        st.dataframe(pd.DataFrame(hb_rows), use_container_width=True, hide_index=True)
    else:
        st.caption("No job runs recorded yet.")

    st.divider()
    st.markdown("### 🔄 Supplier actions (enqueue)")
    suppliers = session.query(Supplier).filter_by(is_active=True).order_by(Supplier.name.asc()).all()
    if not suppliers:
        st.caption("No active suppliers.")
        return

    for supplier in suppliers:
        with st.expander(f"🏪 {supplier.name}", expanded=False):
            a, b = st.columns(2)
            with a:
                if st.button("🔍 Enqueue scrape", key=f"scrape_{supplier.id}", use_container_width=True):
                    import uuid

                    session.add(
                        SystemCommand(
                            id=str(uuid.uuid4()),
                            type="SCRAPE_SUPPLIER",
                            payload={"supplier_id": supplier.id, "supplier_name": supplier.name},
                            status=CommandStatus.PENDING,
                        )
                    )
                    session.commit()
                    st.success("Scrape queued.")
            with b:
                if st.button("✨ Enqueue enrich", key=f"enrich_{supplier.id}", use_container_width=True):
                    import uuid

                    session.add(
                        SystemCommand(
                            id=str(uuid.uuid4()),
                            type="ENRICH_SUPPLIER",
                            payload={"supplier_id": supplier.id, "supplier_name": supplier.name},
                            status=CommandStatus.PENDING,
                        )
                    )
                    session.commit()
                    st.success("Enrich queued.")

    st.divider()
    st.markdown("### 🛠️ Developer controls")
    from retail_os.trademe.worker import CommandWorker

    d1, d2 = st.columns(2)
    with d1:
        if st.button("➕ Enqueue TEST_COMMAND", use_container_width=True):
            import uuid

            session.add(
                SystemCommand(
                    id=str(uuid.uuid4()),
                    type="TEST_COMMAND",
                    payload={"timestamp": datetime.utcnow().isoformat()},
                    status=CommandStatus.PENDING,
                )
            )
            session.commit()
            st.success("TEST_COMMAND queued.")
            st.rerun()

    with d2:
        if st.button("▶ Process next command (in-process)", use_container_width=True):
            worker = CommandWorker()
            worker.process_next_command()
            st.success("Processed one command. Refreshing…")
            time.sleep(0.3)
            st.rerun()

    st.divider()
    st.markdown("### 📋 Recent commands")
    cmds = session.query(SystemCommand).order_by(SystemCommand.created_at.desc()).limit(15).all()
    if cmds:
        rows = []
        for cmd in cmds:
            cmd_type, payload = CommandWorker.resolve_command(cmd)
            rows.append(
                {
                    "id": cmd.id[:12] + "…",
                    "type": cmd_type,
                    "status": cmd.status.value if hasattr(cmd.status, "value") else str(cmd.status),
                    "attempts": cmd.attempts,
                    "created_at": cmd.created_at,
                    "error": (cmd.last_error or "")[:120],
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.caption("No commands yet.")


def main() -> None:
    inject_theme()
    render_header()

    with get_db_session() as session:
        metrics = fetch_vault_metrics(None)

        tab_raw, tab_enriched, tab_live, tab_orders, tab_quality, tab_ops = st.tabs(
            [
                f"🔴 Raw ({metrics['vault1_count']})",
                f"🟡 Enriched ({metrics['vault2_count']})",
                f"🟢 Live ({metrics['vault3_count']})",
                "📦 Orders",
                "🧪 Quality",
                f"⚙️ Ops (Pending {metrics['pending_jobs']})",
            ]
        )

        with tab_raw:
            render_vault1(session)
        with tab_enriched:
            render_vault2(session)
        with tab_live:
            render_vault3(session)
        with tab_orders:
            render_orders_tab()
        with tab_quality:
            render_quality_tab()
        with tab_ops:
            render_operations(session)


if __name__ == "__main__":
    main()

