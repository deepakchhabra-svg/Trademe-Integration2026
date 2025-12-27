def render_orders_tab(session):
    """Orders & Sales Management - Trade Me Admin Module"""
    st.markdown("## 📦 Orders & Sales Management")
    st.markdown("**Trade Me Order Tracking** - View and manage sold items, fulfillment, and revenue")
    
    st.markdown("---")
    
    # Fetch orders from data layer
    from retail_os.dashboard.data_layer import fetch_orders
    orders = fetch_orders(limit=100)
    
    if orders:
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📊 Total Orders", len(orders))
        with col2:
            pending = sum(1 for o in orders if o.get('status') == 'PENDING')
            st.metric("⏳ Pending", pending)
        with col3:
            shipped = sum(1 for o in orders if o.get('status') == 'SHIPPED')
            st.metric("📮 Shipped", shipped)
        with col4:
            # Calculate total revenue
            total_revenue = 0  # Would need sold_price in fetch_orders
            st.metric("💰 Revenue", f"${total_revenue:,.2f}")
        
        st.markdown("---")
        
        # Filters
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            status_filter = st.selectbox("Status", ["All", "PENDING", "CONFIRMED", "SHIPPED", "DELIVERED"], key="order_status_filter")
        with col_f2:
            date_filter = st.selectbox("Period", ["Today", "Last 7 Days", "Last 30 Days", "All Time"], key="order_date_filter")
        with col_f3:
            search_order = st.text_input("🔍 Search", placeholder="Order ref, buyer name...", key="order_search")
        
        # Build order table
        order_data = []
        for o in orders:
            order_data.append({
                "Order Ref": o.get('ref', 'N/A'),
                "Buyer": o.get('buyer', 'Unknown'),
                "Status": o.get('status', 'PENDING'),
                "Date": o.get('date').strftime('%d/%m/%Y %H:%M') if o.get('date') else 'N/A'
            })
        
        df_orders = pd.DataFrame(order_data)
        
        # Display table
        st.dataframe(
            df_orders,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Order Ref": st.column_config.TextColumn("Order Ref", width="medium"),
                "Buyer": st.column_config.TextColumn("Buyer", width="medium"),
                "Status": st.column_config.TextColumn("Status", width="small"),
                "Date": st.column_config.TextColumn("Date", width="medium"),
            }
        )
        
        st.markdown("---")
        st.caption("💡 Tip: Click on an order to view full details and manage fulfillment")
        
    else:
        st.markdown("""
        <div class="empty-state">
            <h3>No orders yet</h3>
            <p>Orders will appear here when items are sold on Trade Me</p>
        </div>
        """, unsafe_allow_html=True)
