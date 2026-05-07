import streamlit as st
import pandas as pd
import pg8000.dbapi as psycopg2
import altair as alt 
import time
from typing import Optional

# --- 1. GLOBAL CONFIGURATION & SECURITY ---
# This is your primary table name on Redshift.
TARGET_TABLE = "schema_f540_fst_ohd_camera_results.material_processes_count_test"

st.set_page_config(
    page_title="Industrial Production Analytics",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Secrets Validation
try:
    DB_HOST = st.secrets["redshift"]["host"]
    DB_NAME = st.secrets["redshift"]["dbname"]
    DB_USER = st.secrets["redshift"]["user"]
    DB_PASS = st.secrets["redshift"]["password"]
    DB_PORT = st.secrets["redshift"]["port"]
except KeyError:
    st.error("❌ Critical Error: .streamlit/secrets.toml file not found or incomplete!")
    st.stop()

# --- 2. DATABASE CONNECTION ENGINE ---
@st.cache_resource(show_spinner="Connecting to Data Warehouse...")
def get_redshift_connection():
    """Establishes Redshift connection and caches it for the application session."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            port=int(DB_PORT),
            timeout=10
        )
        return conn
    except Exception as e:
        st.error(f"❌ Connection Error: {e}")
        return None

# --- 3. DATA EXTRACTION AND PROCESSING (ETL LAYER) ---
@st.cache_data(ttl=1800, show_spinner="Syncing data from warehouse...")
def fetch_and_clean_data(_conn, table_name):
    """Extracts, cleans, and prepares data for analysis."""
    if _conn is None:
        return pd.DataFrame()
    
    query = f"""
    SELECT part_number, production_variant, development_variant, production_step, quantity 
    FROM {table_name}
    """
    try:
        df = pd.read_sql_query(query, _conn)
        
        # Data Cleaning
        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0)
        df['production_step'] = df['production_step'].replace('', 'Unknown')
        
        return df
    except Exception as e:
        st.error(f"❌ Query Error: {e}")
        return pd.DataFrame()

# --- 4. MAIN APPLICATION LOOP ---
def main():
    st.title("🏭 Smart Factory: Material Process & Variant Analysis")
    st.caption(f"Data Source: AWS Redshift Cluster | Table: {TARGET_TABLE}")
    
    conn = get_redshift_connection()
    if conn is None:
        st.warning("Analysis cannot be initiated: Database connection failed.")
        return

    raw_data = fetch_and_clean_data(conn, TARGET_TABLE)
    
    if raw_data.empty:
        st.info("The table is empty or access permissions are missing.")
        return

    # --- SIDEBAR: ADVANCED FILTERING ---
    st.sidebar.header("🛠️ Analysis Toolkit")
    
    # Multi-Select Filters
    with st.sidebar.expander("Variant & Step Selection", expanded=True):
        prod_variants = st.multiselect(
            "Production Variant",
            options=sorted(raw_data['production_variant'].unique()),
            default=raw_data['production_variant'].unique()[:5] # Default to first 5
        )
        
        steps = st.multiselect(
            "Production Step",
            options=sorted(raw_data['production_step'].unique()),
            default=raw_data['production_step'].unique()
        )

    # Filtering Logic
    df_filtered = raw_data[
        (raw_data['production_variant'].isin(prod_variants)) &
        (raw_data['production_step'].isin(steps))
    ]

    # Refresh Button (Cache Clear)
    if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # --- MAIN DISPLAY: METRICS (KPIs) ---
    st.markdown("### 📊 Key Performance Indicators (KPI)")
    k1, k2, k3, k4 = st.columns(4)
    
    with k1:
        st.metric("Total Transactions", f"{len(df_filtered):,}")
    with k2:
        st.metric("Unique Parts", df_filtered['part_number'].nunique())
    with k3:
        st.metric("Total Stock (Units)", f"{int(df_filtered['quantity'].sum()):,}")
    with k4:
        st.metric("Active Variants", len(df_filtered['production_variant'].unique()))

    st.divider()

    # --- VISUALIZATION ---
    st.subheader("📈 Stock Distribution by Production Step")
    
    # Chart Preparation
    chart_data = df_filtered.groupby('production_step')['quantity'].sum().reset_index()
    
    base_chart = alt.Chart(chart_data).mark_bar(
        cornerRadiusTopLeft=5,
        cornerRadiusTopRight=5,
        color='#0078D4'
    ).encode(
        x=alt.X('quantity:Q', title="Total Quantity"),
        y=alt.Y('production_step:N', title="Production Step", sort='-x'),
        tooltip=['production_step', alt.Tooltip('quantity', format=',')]
    ).properties(height=400).interactive()

    st.altair_chart(base_chart, use_container_width=True)

    # --- DATA TABLE VIEW (DUAL LAYOUT) ---
    st.subheader("🔍 Data Insights")
    tab1, tab2 = st.tabs(["📄 Filtered Dataset", "📉 Statistical Summary"])
    
    with tab1:
        st.dataframe(
            df_filtered, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "quantity": st.column_config.NumberColumn("Quantity", format="%d")
            }
        )
    
    with tab2:
        col_a, col_b = st.columns(2)
        with col_a:
            st.write("**Summary by Variant**")
            st.table(df_filtered.groupby('production_variant')['quantity'].sum().sort_values(ascending=False).head(10))
        with col_b:
            st.write("**Summary by Step**")
            st.table(df_filtered.groupby('production_step')['quantity'].mean().reset_index().rename(columns={'quantity': 'Avg. Quantity'}))

    st.success(f"✅ Analysis Complete: {len(df_filtered)} records processed successfully.")

if __name__ == "__main__":
    main()
