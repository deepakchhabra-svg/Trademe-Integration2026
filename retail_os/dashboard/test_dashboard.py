"""
Test Results Dashboard
Real-time visualization of requirement testing progress and results
"""

import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from tests.test_framework import TestDatabase


st.set_page_config(
    page_title="RetailOS Test Results",
    page_icon="🧪",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .pass { color: #10b981; font-weight: bold; }
    .fail { color: #ef4444; font-weight: bold; }
    .partial { color: #f59e0b; font-weight: bold; }
    .blocked { color: #6b7280; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Initialize database
db = TestDatabase()

st.title("🧪 RetailOS Requirements Testing Dashboard")
st.markdown("**Comprehensive validation of all Done/Partial requirements**")

# Sidebar - Test Run Selection
st.sidebar.header("Test Run Selection")

conn = sqlite3.connect(db.db_path)

# Get all test runs
runs_df = pd.read_sql_query("""
    SELECT id, run_name, started_at, completed_at, status,
           total_requirements, total_tests, passed, failed, blocked, partial
    FROM test_runs
    ORDER BY started_at DESC
""", conn)

if len(runs_df) == 0:
    st.info("📋 No test runs yet. Run tests using the test framework to see results here.")
    st.stop()

# Select test run
run_options = {f"{row['run_name']} ({row['started_at']})": row['id'] 
               for _, row in runs_df.iterrows()}
selected_run_name = st.sidebar.selectbox("Select Test Run", list(run_options.keys()))
selected_run_id = run_options[selected_run_name]

# Get selected run details
run_data = runs_df[runs_df['id'] == selected_run_id].iloc[0]

# Main Dashboard
st.header(f"📊 {run_data['run_name']}")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Started", run_data['started_at'])
with col2:
    st.metric("Status", run_data['status'])
with col3:
    if run_data['completed_at']:
        st.metric("Completed", run_data['completed_at'])
    else:
        st.metric("Completed", "In Progress...")

# Summary Metrics
st.subheader("📈 Test Summary")

col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.metric("Requirements Tested", run_data['total_requirements'] or 0)
with col2:
    st.metric("Total Tests", run_data['total_tests'] or 0)
with col3:
    st.metric("✅ Passed", run_data['passed'] or 0)
with col4:
    st.metric("❌ Failed", run_data['failed'] or 0)
with col5:
    st.metric("🟡 Partial", run_data['partial'] or 0)
with col6:
    st.metric("🚫 Blocked", run_data['blocked'] or 0)

# Pass Rate
if run_data['total_tests'] and run_data['total_tests'] > 0:
    pass_rate = (run_data['passed'] / run_data['total_tests']) * 100
    st.progress(pass_rate / 100)
    st.caption(f"Pass Rate: {pass_rate:.1f}%")

# Module Breakdown
st.subheader("📦 Results by Module")

module_stats = pd.read_sql_query("""
    SELECT 
        module,
        COUNT(DISTINCT requirement_id) as requirements,
        COUNT(*) as total_tests,
        SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) as passed,
        SUM(CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END) as failed,
        SUM(CASE WHEN status = 'PARTIAL' THEN 1 ELSE 0 END) as partial,
        SUM(CASE WHEN status = 'BLOCKED' THEN 1 ELSE 0 END) as blocked
    FROM test_results
    WHERE run_id = ?
    GROUP BY module
    ORDER BY module
""", conn, params=(selected_run_id,))

if len(module_stats) > 0:
    # Calculate pass rate for each module
    module_stats['pass_rate'] = (module_stats['passed'] / module_stats['total_tests'] * 100).round(1)
    
    st.dataframe(
        module_stats,
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("No module data available yet.")

# Detailed Test Results
st.subheader("🔍 Detailed Test Results")

# Filter options
col1, col2, col3 = st.columns(3)

with col1:
    module_filter = st.selectbox(
        "Filter by Module",
        ["All"] + list(module_stats['module'].unique()) if len(module_stats) > 0 else ["All"]
    )

with col2:
    status_filter = st.selectbox(
        "Filter by Status",
        ["All", "PASS", "FAIL", "PARTIAL", "BLOCKED"]
    )

with col3:
    search_term = st.text_input("Search Requirement ID")

# Build query
query = """
    SELECT 
        requirement_id,
        module,
        test_case_name,
        category,
        status,
        message,
        executed_at
    FROM test_results
    WHERE run_id = ?
"""
params = [selected_run_id]

if module_filter != "All":
    query += " AND module = ?"
    params.append(module_filter)

if status_filter != "All":
    query += " AND status = ?"
    params.append(status_filter)

if search_term:
    query += " AND requirement_id LIKE ?"
    params.append(f"%{search_term}%")

query += " ORDER BY module, requirement_id, executed_at DESC"

results_df = pd.read_sql_query(query, conn, params=params)

if len(results_df) > 0:
    # Style the dataframe
    def highlight_status(row):
        if row['status'] == 'PASS':
            return ['background-color: #d1fae5'] * len(row)
        elif row['status'] == 'FAIL':
            return ['background-color: #fee2e2'] * len(row)
        elif row['status'] == 'PARTIAL':
            return ['background-color: #fef3c7'] * len(row)
        elif row['status'] == 'BLOCKED':
            return ['background-color: #f3f4f6'] * len(row)
        return [''] * len(row)
    
    st.dataframe(
        results_df.style.apply(highlight_status, axis=1),
        use_container_width=True,
        hide_index=True,
        height=400
    )
    
    # Download results
    csv = results_df.to_csv(index=False)
    st.download_button(
        label="📥 Download Results as CSV",
        data=csv,
        file_name=f"test_results_{run_data['run_name']}.csv",
        mime="text/csv"
    )
else:
    st.info("No test results match the current filters.")

# Defects Section
st.subheader("🐛 Defects Found")

defects_df = pd.read_sql_query("""
    SELECT 
        requirement_id,
        severity,
        description,
        status,
        created_at,
        fixed_at
    FROM defects
    ORDER BY 
        CASE severity
            WHEN 'CRITICAL' THEN 1
            WHEN 'HIGH' THEN 2
            WHEN 'MEDIUM' THEN 3
            WHEN 'LOW' THEN 4
            WHEN 'ENHANCEMENT' THEN 5
        END,
        created_at DESC
""", conn)

if len(defects_df) > 0:
    # Defect summary
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Defects", len(defects_df))
    with col2:
        open_defects = len(defects_df[defects_df['status'] == 'OPEN'])
        st.metric("Open", open_defects)
    with col3:
        fixed_defects = len(defects_df[defects_df['status'] == 'FIXED'])
        st.metric("Fixed", fixed_defects)
    with col4:
        critical_defects = len(defects_df[defects_df['severity'] == 'CRITICAL'])
        st.metric("Critical", critical_defects)
    
    # Defect details
    st.dataframe(
        defects_df,
        use_container_width=True,
        hide_index=True,
        height=300
    )
else:
    st.success("✅ No defects found!")

# Fixes Applied
st.subheader("🔧 Fixes Applied")

fixes_df = pd.read_sql_query("""
    SELECT 
        f.requirement_id,
        f.description,
        f.files_changed,
        f.applied_at,
        d.severity
    FROM fixes f
    LEFT JOIN defects d ON f.defect_id = d.id
    ORDER BY f.applied_at DESC
""", conn)

if len(fixes_df) > 0:
    st.dataframe(
        fixes_df,
        use_container_width=True,
        hide_index=True,
        height=200
    )
else:
    st.info("No fixes applied yet.")

conn.close()

# Footer
st.markdown("---")
st.caption("🥷 Ninja Tester Mode - Nothing escapes validation")
