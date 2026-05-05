import pandas as pd
import os
import re
import psycopg2 
from typing import Dict, Any, List, Tuple 
import numpy as np 
from apscheduler.schedulers.blocking import BlockingScheduler 
from apscheduler.triggers.interval import IntervalTrigger
import time 
from openpyxl import load_workbook
import streamlit as st 

# ******************************************************************************
# --- 0. OTOMASYON AYARLARI ---
# ******************************************************************************
SCHEDULE_INTERVAL_MINUTES = 60 # Varsayılan: Her 60 dakikada bir çalışır

# ******************************************************************************
# --- 1. KURUMSAL AYARLAR VE ANONİM YOLLAR ---
# ******************************************************************************
# Not: Gerçek ağ yolları güvenlik nedeniyle yer tutucularla değiştirilmiştir.
BASE_PATH = r'\\YOUR_NETWORK_PATH\REPORTS' 
RAW_STOCKS_FILE = os.path.join(BASE_PATH, 'production_stocks_daily.csv') 
WIP_PRODUCTION_FILE = os.path.join(BASE_PATH, 'factory_wip_report.xlsx') 
FINAL_REPORT_LOG = os.path.join(BASE_PATH, 'pipeline_execution_log.csv')

# AWS Redshift bağlantı bilgileri st.secrets üzerinden güvenli şekilde çekilir
try:
    DB_CONFIG = {
        "host": st.secrets["redshift"]["host"],
        "database": st.secrets["redshift"]["dbname"],
        "user": st.secrets["redshift"]["user"],
        "password": st.secrets["redshift"]["password"],
        "port": st.secrets["redshift"]["port"]
    }
except Exception as e:
    print(f"CRITICAL ERROR: Secrets loading failed: {e}")
    DB_CONFIG = None

TARGET_TABLE = "production_analytics.material_flow_master"
TEMP_TABLE = "temp_staged_load"

# ******************************************************************************
# --- 2. VERİ MÜHENDİSLİĞİ FONKSİYONLARI ---
# ******************************************************************************

def clean_production_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ham veriyi kurumsal standartlara göre temizler ve valide eder.
    """
    # Regex ile parça numarası temizliği (Sadece alfanumerik karakterler)
    if 'part_number' in df.columns:
        df['part_number'] = df['part_number'].apply(lambda x: re.sub(r'[^a-zA-Z0-9]', '', str(x)))
    
    # Eksik verilerin yönetimi (Data Integrity)
    df.fillna({'quantity': 0, 'status': 'PENDING'}, inplace=True)
    
    # Tarih formatı standardizasyonu
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        
    return df

def execute_redshift_upsert(df: pd.DataFrame, target: str, temp: str):
    """
    AWS Redshift üzerinde yüksek performanslı UPSERT (Merge) işlemi.
    """
    if DB_CONFIG is None: return

    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        # 1. Staging (Hazırlık) alanını oluştur
        cursor.execute(f"DROP TABLE IF EXISTS {temp};")
        cursor.execute(f"CREATE TABLE {temp} (LIKE {target});")
        
        # 2. Veri Yükleme (Simülasyon: Gerçekte S3 COPY kullanılır)
        print(f"📦 {len(df)} kayıt staging tablosuna hazırlanıyor...")
        
        # 3. UPSERT Mantığı: Mevcut olanları sil, güncel olanları ekle
        # Bu işlem veri mükerrerliğini (duplication) %100 engeller.
        cursor.execute(f"DELETE FROM {target} WHERE id IN (SELECT id FROM {temp});")
        cursor.execute(f"INSERT INTO {target} SELECT * FROM {temp};")
        
        conn.commit()
        print(f"✅ Başarılı: {target} güncellendi.")
    except Exception as e:
        conn.rollback()
        print(f"❌ Veri tabanı hatası: {e}")
    finally:
        cursor.close()
        conn.close()

def scheduled_job_wrapper():
    """Zamanlayıcı tarafından tetiklenen ana döngü"""
    print(f"🕒 İşlem Döngüsü Başladı: {time.ctime()}")
    # try:
    #     # Örnek iş akışı:
    #     # df = pd.read_csv(RAW_STOCKS_FILE)
    #     # df_clean = clean_production_data(df)
    #     # execute_redshift_upsert(df_clean, TARGET_TABLE, TEMP_TABLE)
    # except Exception as e:
    #     print(f"İş akışı hatası: {e}")

if __name__ == '__main__':
    scheduler = BlockingScheduler()
    trigger = IntervalTrigger(minutes=SCHEDULE_INTERVAL_MINUTES)
    
    scheduler.add_job(scheduled_job_wrapper, trigger)
    
    print("----------------------------------------------------------------------")
    print(f"🚀 Otonom Fabrika Veri Hattı Aktif! (Döngü: {SCHEDULE_INTERVAL_MINUTES} dk)")
    print("----------------------------------------------------------------------")
    
    try:
        scheduled_job_wrapper() # İlk tetikleme
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("Sistem durduruldu.")
