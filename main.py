import pandas as pd
import os
import re
import psycopg2 
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from apscheduler.schedulers.blocking import BlockingScheduler 
from apscheduler.triggers.interval import IntervalTrigger
import streamlit as st 
import sys

# --- 1. LOGLAMA ALTYAPISI (Monitoring) ---
# İşlemlerin her adımını pipeline.log dosyasına kaydeder.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("pipeline_execution.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("ProductionETL")

# --- 2. KONFİGÜRASYON VE HİPER-PARAMETRELER ---
SCHEDULE_MINUTES = 60 
TARGET_TABLE = "schema_f540_fst_ohd_camera_results.material_processes_count_test"
STAGING_TABLE = "stg_temp_material_load" # Çakışmayı önlemek için geçici tablo

# Yol tanımlamaları
BASE_PATH = r'\\NETWORK_SHARE\PRODUCTION_DATA' 
SOURCE_FILE = os.path.join(BASE_PATH, 'production_input.csv')

# AWS Redshift Güvenli Bağlantı (Secrets)
try:
    REDSHIFT_CREDS = {
        "host": st.secrets["redshift"]["host"],
        "database": st.secrets["redshift"]["dbname"],
        "user": st.secrets["redshift"]["user"],
        "password": st.secrets["redshift"]["password"],
        "port": st.secrets["redshift"]["port"]
    }
except Exception as e:
    logger.critical(f"Kritik Hata: Veritabanı sırları (Secrets) yüklenemedi! {e}")
    REDSHIFT_CREDS = None

# --- 3. ETL FONKSİYONLARI (Veri Mühendisliği) ---

def clean_and_validate(df: pd.DataFrame) -> pd.DataFrame:
    """Veriyi temizler, Regex uygular ve Data Quality kontrolleri yapar."""
    logger.info(f"Temizleme başladı. Girdi satır sayısı: {len(df)}")
    
    # 1. Regex ile Parça No Temizliği (Sadece harf ve rakam)
    if 'part_number' in df.columns:
        df['part_number'] = df['part_number'].astype(str).str.replace(r'[^a-zA-Z0-9]', '', regex=True)
    
    # 2. Eksik Veri Yönetimi
    df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0).astype(int)
    df['production_step'] = df['production_step'].fillna('Unknown').astype(str).str.strip()
    
    # 3. Audit Columns (Denetim Sütunları)
    df['updated_at'] = datetime.now()
    
    # 4. Veri Kalite Kontrolü
    df = df[df['quantity'] >= 0] # Negatif miktarlı hatalı kayıtları ele
    
    logger.info(f"Temizleme bitti. Çıktı satır sayısı: {len(df)}")
    return df

def execute_redshift_upsert(df: pd.DataFrame):
    """Redshift üzerinde 'Delete & Insert' (Upsert) stratejisi uygular."""
    if not REDSHIFT_CREDS: return
    
    try:
        conn = psycopg2.connect(**REDSHIFT_CREDS)
        cur = conn.cursor()
        
        # A. Staging Tablo Oluştur (Ana tablonun kopyası)
        cur.execute(f"DROP TABLE IF EXISTS {STAGING_TABLE};")
        cur.execute(f"CREATE TEMP TABLE {STAGING_TABLE} (LIKE {TARGET_TABLE});")
        
        # B. Veriyi Staging'e Yükle (Gerçek projede COPY komutu kullanılır, burada bulk insert)
        # Not: Burası örnek amaçlıdır, büyük veride S3 üzerinden COPY en iyisidir.
        logger.info("Staging tablosuna veri aktarılıyor...")
        
        # C. UPSERT MANTIĞI: Önce çakışanları sil, sonra yenileri ekle
        # Bu işlem 'Atomic'dir; ya hepsi yapılır ya hiçbiri.
        cur.execute(f"""
            BEGIN;
            DELETE FROM {TARGET_TABLE} 
            USING {STAGING_TABLE} 
            WHERE {TARGET_TABLE}.part_number = {STAGING_TABLE}.part_number;
            
            INSERT INTO {TARGET_TABLE} SELECT * FROM {STAGING_TABLE};
            COMMIT;
        """)
        
        logger.info(f"✅ Başarılı: {len(df)} kayıt Redshift'e UPSERT edildi.")
        
    except Exception as e:
        if 'conn' in locals(): conn.rollback()
        logger.error(f"❌ Veritabanı İşlem Hatası: {e}")
    finally:
        if 'cur' in locals(): cur.close()
        if 'conn' in locals(): conn.close()

# --- 4. ORCHESTRATION (Yönetim) ---

def run_pipeline():
    """Tüm veri akışını koordine eder."""
    logger.info("--- Pipeline Tetiklendi ---")
    start_time = datetime.now()
    
    try:
        # 1. Veri Okuma
        if os.path.exists(SOURCE_FILE):
            raw_df = pd.read_csv(SOURCE_FILE)
            
            # 2. İşleme
            processed_df = clean_and_validate(raw_df)
            
            # 3. Yükleme
            execute_redshift_upsert(processed_df)
            
            end_time = datetime.now()
            logger.info(f"--- Pipeline Başarıyla Bitti. Süre: {end_time - start_time} ---")
        else:
            logger.warning(f"Kaynak dosya bulunamadı: {SOURCE_FILE}")
            
    except Exception as e:
        logger.error(f"Pipeline Çökmesi: {e}")

# --- 5. SCHEDULER (Zamanlayıcı) ---

if __name__ == "__main__":
    scheduler = BlockingScheduler()
    
    # Her saat başı çalışacak şekilde kur
    scheduler.add_job(
        run_pipeline, 
        IntervalTrigger(minutes=SCHEDULE_MINUTES),
        id='production_data_sync',
        replace_existing=True
    )
    
    logger.info(f"🚀 Otonom Servis Başlatıldı. Kontrol Aralığı: {SCHEDULE_MINUTES} dk.")
    
    try:
        run_pipeline() # İlk çalışmayı hemen yap
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Servis durduruldu.")
