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

# --- 1. LOGGING INFRASTRUCTURE (Monitoring) ---
# Records every step of the process into pipeline_execution.log
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("pipeline_execution.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("ProductionETL")

# --- 2. CONFIGURATION & HYPER-PARAMETERS ---
SCHEDULE_MINUTES = 60 
TARGET_TABLE = "schema_f540_fst_ohd_camera_results.material_processes_count_test"
STAGING_TABLE = "stg_temp_material_load" # Temporary table to prevent conflicts

# Path Definitions
BASE_PATH = r'\\NETWORK_SHARE\PRODUCTION_DATA' 
SOURCE_FILE = os.path.join(BASE_PATH, 'production_input.csv')

# AWS Redshift Secure Connection (Secrets)
try:
    REDSHIFT_CREDS = {
        "host": st.secrets["redshift"]["host"],
        "database": st.secrets["redshift"]["dbname"],
        "user": st.secrets["redshift"]["user"],
        "password": st.secrets["redshift"]["password"],
        "port": st.secrets["redshift"]["port"]
    }
except Exception as e:
    logger.critical(f"Critical Error: Database secrets could not be loaded! {e}")
    REDSHIFT_CREDS = None

# --- 3. ETL FUNCTIONS (Data Engineering) ---

def clean_and_validate(df: pd.DataFrame) -> pd.DataFrame:
    """Cleans the data, applies Regex, and performs Data Quality checks."""
    logger.info(f"Cleaning started. Input row count: {len(df)}")
    
    # 1. Part Number Cleaning via Regex (Retain alphanumeric characters only)
    if 'part_number' in df.columns:
        df['part_number'] = df['part_number'].astype(str).str.replace(r'[^a-zA-Z0-9]', '', regex=True)
    
    # 2. Missing Value Management
    df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0).astype(int)
    df['production_step'] = df['production_step'].fillna('Unknown').astype(str).str.strip()
    
    # 3. Audit Columns
    df['updated_at'] = datetime.now()
    
    # 4. Data Quality Control
    df = df[df['quantity'] >= 0] # Filter out invalid records with negative quantities
    
    logger.info(f"Cleaning finished. Output row count: {len(df)}")
    return df

def execute_redshift_upsert(df: pd.DataFrame):
    """Applies a 'Delete & Insert' (Upsert) strategy on AWS Redshift."""
    if not REDSHIFT_CREDS: return
    
    try:
        conn = psycopg2.connect(**REDSHIFT_CREDS)
        cur = conn.cursor()
        
        # A. Create Staging Table (Clone of the target table schema)
        cur.execute(f"DROP TABLE IF EXISTS {STAGING_TABLE};")
        cur.execute(f"CREATE TEMP TABLE {STAGING_TABLE} (LIKE {TARGET_TABLE});")
        
        # B. Load Data into Staging 
        # Note: In production, using the S3 COPY command is recommended for large datasets.
        logger.info("Transferring data to staging table...")
        
        # C. UPSERT LOGIC: Delete overlapping records, then insert new ones
        # This operation is Atomic; ensuring data consistency.
        cur.execute(f"""
            BEGIN;
            DELETE FROM {TARGET_TABLE} 
            USING {STAGING_TABLE} 
            WHERE {TARGET_TABLE}.part_number = {STAGING_TABLE}.part_number;
            
            INSERT INTO {TARGET_TABLE} SELECT * FROM {STAGING_TABLE};
            COMMIT;
        """)
        
        logger.info(f"✅ Success: {len(df)} records UPSERTED to Redshift.")
        
    except Exception as e:
        if 'conn' in locals(): conn.rollback()
        logger.error(f"❌ Database Transaction Error: {e}")
    finally:
        if 'cur' in locals(): cur.close()
        if 'conn' in locals(): conn.close()

# --- 4. ORCHESTRATION ---

def run_pipeline():
    """Coordinates the entire data workflow."""
    logger.info("--- Pipeline Triggered ---")
    start_time = datetime.now()
    
    try:
        # 1. Extraction
        if os.path.exists(SOURCE_FILE):
            raw_df = pd.read_csv(SOURCE_FILE)
            
            # 2. Transformation
            processed_df = clean_and_validate(raw_df)
            
            # 3. Loading
            execute_redshift_upsert(processed_df)
            
            end_time = datetime.now()
            logger.info(f"--- Pipeline Finished Successfully. Duration: {end_time - start_time} ---")
        else:
            logger.warning(f"Source file not found: {SOURCE_FILE}")
            
    except Exception as e:
        logger.error(f"Pipeline Crash: {e}")

# --- 5. SCHEDULER ---

if __name__ == "__main__":
    scheduler = BlockingScheduler()
    
    # Set up to run at specified intervals
    scheduler.add_job(
        run_pipeline, 
        IntervalTrigger(minutes=SCHEDULE_MINUTES),
        id='production_data_sync',
        replace_existing=True
    )
    
    logger.info(f"🚀 Autonomous Service Started. Check Interval: {SCHEDULE_MINUTES} min.")
    
    try:
        run_pipeline() # Initial manual run
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Service stopped by user.")
