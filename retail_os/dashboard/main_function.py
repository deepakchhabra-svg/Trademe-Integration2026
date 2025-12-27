
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
        # Optional: st.exception(e) for debug mode

if __name__ == "__main__":
    main()
