import streamlit as st
import pandas as pd
from retail_os.quality.rebuilder import ContentRebuilder
from retail_os.quality.content import verify_images

def render_quality_tab():
    st.header("🧪 Content Quality Lab (Strict Rebuild)")
    st.markdown("Verify the **Hard Reset** logic: Input -> Reconstruct -> Output.")

    # INITIALIZE STATE (Critical - must be first)
    if 'scraped_data' not in st.session_state:
        st.session_state.scraped_data = {}

    # 1. Description Rebuilder
    st.subheader("1. Reconstructive Sanitization")
    
    # Input Mode Selection
    input_mode = st.radio("Input Mode", ["Simulation (Manual)", "Import via URL (Live)"], horizontal=True)
    
    if input_mode == "Import via URL (Live)":
        url_input = st.text_input("Cash Converters URL", placeholder="https://shop.cashconverters.co.nz/Listing/Details/...")
        
        # HARD-LINK THE BUTTON
        if url_input and st.button("Fetch Data"):
            from retail_os.scrapers.cash_converters.scraper import scrape_single_item
            from retail_os.utils.image_downloader import ImageDownloader
            
            with st.spinner("Fetching data..."):
                # ACTUAL SCRAPER CALL
                data = scrape_single_item(url_input)
                
                # DOWNLOAD IMAGE PHYSICALLY
                downloader = ImageDownloader()
                sku = data.get('source_id', 'TEMP')
                img_url = data.get('photo1', '')
                
                local_img_path = img_url
                if img_url and not img_url.startswith("https://placehold.co"):
                    result = downloader.download_image(img_url, sku)
                    if result["success"]:
                        local_img_path = result["path"]
                        st.success(f"✅ Image downloaded: {result['size']} bytes")
                    else:
                        st.warning(f"⚠️ Image download failed: {result['error']}")
                
                # Store image path in data
                data['local_image'] = local_img_path
                
                # HARD-LINK TO SESSION STATE
                st.session_state.scraped_data = data
            
            st.success(f"✅ Loaded: {data.get('title')}")
            st.rerun()
    
    # IMAGE FORCE (Display above form)
    if st.session_state.scraped_data.get('local_image') or st.session_state.scraped_data.get('photo1'):
        st.subheader("📷 Source Image")
        img_path = st.session_state.scraped_data.get('local_image') or st.session_state.scraped_data.get('photo1')
        
        import os
        if os.path.exists(img_path):
            st.image(img_path, width=400, caption=f"Local: {os.path.basename(img_path)}")
            file_size = os.path.getsize(img_path)
            st.caption(f"✅ File size: {file_size} bytes | Path: `{img_path}`")
        else:
            st.image(img_path, width=400, caption="Source Image (URL)")
    
    # Input Block - HARD-LINKED TO STATE
    with st.container(border=True):
        st.markdown("#### Input Data")
        c1, c2 = st.columns(2)
        with c1:
            # HARD-LINK THE FIELDS
            raw_title = st.text_input(
                "Title", 
                value=st.session_state.scraped_data.get('title', 'Sony Playstation 5 Disc Edition - Great Condition')
            )
            raw_specs = st.text_area(
                "Specs (JSON/Dict format)", 
                value=str(st.session_state.scraped_data.get('specs', {'Model': 'CFI-1215A', 'Storage': '825GB'})),
                height=100
            )
        with c2:
            raw_condition = st.selectbox("Condition", ["Used", "New", "Mint", "Fair"], index=0)
            raw_desc = st.text_area(
                "Raw Description (Store Input)", 
                value=st.session_state.scraped_data.get('description', "WE BUY GOLD! VISIT CASH CONVERTERS TODAY.\\n\\nPs5 in box. works good.\\nRefer to pics.\\n\\nPayment required within 24 hours.\\nPick up Auckland Central."),
                height=150
            )
    
    if st.button("🔨 Rebuild Content"):
        rebuilder = ContentRebuilder()
        # Parse specs safely
        try:
            import ast
            specs_dict = ast.literal_eval(raw_specs)
        except:
            specs_dict = {}

        result = rebuilder.rebuild(
            title=raw_title,
            specs=specs_dict,
            condition=raw_condition,
            warranty_months=0
        )
        
        st.divider()
        
        # Split View: Raw vs Rebuilt
        col_raw, col_rebuilt = st.columns(2)
        
        with col_raw:
            st.markdown("### 📥 Raw Input")
            st.text_area("Original Description", value=raw_desc, height=200, disabled=True)
            
        with col_rebuilt:
            st.markdown("### ✨ Rebuilt Output")
            st.text_area("Clean Description", value=result.final_text, height=200, disabled=True)
            
            # Trust Indicator
            if result.is_clean:
                st.success("✅ PASS: No prohibited content detected")
            else:
                st.error(f"❌ BLOCKED: {', '.join(result.blockers)}")
        
        st.divider()
        
        # Trade Me Buyer Preview
        st.subheader("👁️ Trade Me Buyer Preview")
        with st.container(border=True):
            st.markdown(f"### {raw_title}")
            st.markdown(result.final_text)
            st.caption("Fast Dispatch | 🛡️ Trusted NZ Seller")
