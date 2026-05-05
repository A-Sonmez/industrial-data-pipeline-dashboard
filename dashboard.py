import streamlit as st
import pandas as pd
import pg8000.dbapi as psycopg2
import altair as alt 
import time
from typing import Optional

# --- 1. GLOBAL YAPILANDIRMA & GÜVENLİK ---
# Bu tablo adı senin Redshift üzerindeki ana tablon.
TARGET_TABLE = "schema_f540_fst_ohd_camera_results.material_processes_count_test"

st.set_page_config(
    page_title="Industrial Production Analytics",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Secrets Kontrolü
try:
    DB_HOST = st.secrets["redshift"]["host"]
    DB_NAME = st.secrets["redshift"]["dbname"]
    DB_USER = st.secrets["redshift"]["user"]
    DB_PASS = st.secrets["redshift"]["password"]
    DB_PORT = st.secrets["redshift"]["port"]
except KeyError:
    st.error("❌ Kritik Hata: .streamlit/secrets.toml dosyası bulunamadı veya eksik!")
    st.stop()

# --- 2. VERİ TABANI BAĞLANTI MOTORU ---
@st.cache_resource(show_spinner="Veri ambarına bağlanılıyor...")
def get_redshift_connection():
    """Redshift bağlantısını kurar ve uygulama boyunca önbelleğe alır."""
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
        st.error(f"❌ Bağlantı Hatası: {e}")
        return None

# --- 3. VERİ ÇEKME VE İŞLEME (ETL KATMANI) ---
@st.cache_data(ttl=1800, show_spinner="Veriler güncelleniyor...")
def fetch_and_clean_data(_conn, table_name):
    """Veriyi çeker, temizler ve analize hazır hale getirir."""
    if _conn is None:
        return pd.DataFrame()
    
    query = f"""
    SELECT part_number, production_variant, development_variant, production_step, quantity 
    FROM {table_name}
    """
    try:
        df = pd.read_sql_query(query, _conn)
        
        # Veri Temizleme (Data Cleaning)
        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0)
        df['production_step'] = df['production_step'].replace('', 'Unknown')
        
        return df
    except Exception as e:
        st.error(f"❌ Sorgu Hatası: {e}")
        return pd.DataFrame()

# --- 4. ANA UYGULAMA DÖNGÜSÜ ---
def main():
    st.title("🏭 Smart Factory: Material Process & Variant Analysis")
    st.caption(f"Veri Kaynağı: AWS Redshift Cluster | Tablo: {TARGET_TABLE}")
    
    conn = get_redshift_connection()
    if conn is None:
        st.warning("Veri tabanı bağlantısı kurulamadığı için analiz başlatılamıyor.")
        return

    raw_data = fetch_and_clean_data(conn, TARGET_TABLE)
    
    if raw_data.empty:
        st.info("Tablo boş veya erişim izni yok.")
        return

    # --- SIDEBAR: GELİŞMİŞ FİLTRELEME ---
    st.sidebar.header("🛠️ Analiz Araçları")
    
    # Çoklu Seçim Filtreleri
    with st.sidebar.expander("Varyant ve Adım Seçimi", expanded=True):
        prod_variants = st.multiselect(
            "Production Variant",
            options=sorted(raw_data['production_variant'].unique()),
            default=raw_data['production_variant'].unique()[:5] # Varsayılan ilk 5
        )
        
        steps = st.multiselect(
            "Production Step",
            options=sorted(raw_data['production_step'].unique()),
            default=raw_data['production_step'].unique()
        )

    # Veriyi Filtrele
    df_filtered = raw_data[
        (raw_data['production_variant'].isin(prod_variants)) &
        (raw_data['production_step'].isin(steps))
    ]

    # Güncelleme Butonu (Cache Temizleme)
    if st.sidebar.button("🔄 Verileri Yenile", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # --- ANA EKRAN: METRİKLER (KPI) ---
    st.markdown("### 📊 Anahtar Performans Göstergeleri (KPI)")
    k1, k2, k3, k4 = st.columns(4)
    
    with k1:
        st.metric("Toplam İşlem", f"{len(df_filtered):,}")
    with k2:
        st.metric("Tekil Parça Sayısı", df_filtered['part_number'].nunique())
    with k3:
        st.metric("Toplam Stok (Adet)", f"{int(df_filtered['quantity'].sum()):,}")
    with k4:
        st.metric("Aktif Varyant", len(df_filtered['production_variant'].unique()))

    st.divider()

    # --- GÖRSELLEŞTİRME ---
    st.subheader("📈 Üretim Adımlarına Göre Stok Dağılımı")
    
    # Grafik Hazırlığı
    chart_data = df_filtered.groupby('production_step')['quantity'].sum().reset_index()
    
    base_chart = alt.Chart(chart_data).mark_bar(
        cornerRadiusTopLeft=5,
        cornerRadiusTopRight=5,
        color='#0078D4'
    ).encode(
        x=alt.X('quantity:Q', title="Toplam Miktar"),
        y=alt.Y('production_step:N', title="Üretim Adımı", sort='-x'),
        tooltip=['production_step', alt.Tooltip('quantity', format=',')]
    ).properties(height=400).interactive()

    st.altair_chart(base_chart, use_container_width=True)

    # --- TABLO GÖRÜNÜMÜ (DUAL LAYOUT) ---
    st.subheader("🔍 Veri Detayları")
    tab1, tab2 = st.tabs(["📄 Filtrelenmiş Liste", "📉 İstatistiksel Özet"])
    
    with tab1:
        st.dataframe(
            df_filtered, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "quantity": st.column_config.NumberColumn("Miktar", format="%d")
            }
        )
    
    with tab2:
        col_a, col_b = st.columns(2)
        with col_a:
            st.write("**Varyant Bazlı Özet**")
            st.table(df_filtered.groupby('production_variant')['quantity'].sum().sort_values(ascending=False).head(10))
        with col_b:
            st.write("**Adım Bazlı Özet**")
            st.table(df_filtered.groupby('production_step')['quantity'].mean().reset_index().rename(columns={'quantity': 'Ortalama Miktar'}))

    st.success(f"✅ Analiz Başarılı: {len(df_filtered)} kayıt başarıyla işlendi.")

if __name__ == "__main__":
    main()
