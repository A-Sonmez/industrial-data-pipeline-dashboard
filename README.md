# 🏭 Industrial Data Pipeline & Analytics Dashboard

A robust, production-ready ETL solution that automatically moves production logs from the factory floor to AWS Redshift. It cleans messy data, runs on a schedule, and is fully containerized for easy deployment.

## 🎯 Why This Project Exists
Factory logs are often dirty, incomplete, or inconsistent. This pipeline takes care of cleaning, validating, and loading them reliably into Redshift — so the team can focus on analysis instead of fighting with data.

## 🌟 Key Features
- **Fully automated ETL** — Runs every hour using APScheduler.
- **Smart data cleaning** — Heavy use of Pandas and regex to fix and validate data before loading.
- **Seamless Redshift integration** — Optimized loading with psycopg2.
- **Dockerized & production ready** — Works consistently anywhere.
- **Excellent logging** — Clear, real-time monitoring of successes and failures.
- **Optional dashboard** — Streamlit interface for easy monitoring.

## 🛠 Tech Stack
- **Python 3.9+**
- **Pandas & NumPy** for data processing
- **AWS Redshift** (PostgreSQL-compatible)
- **APScheduler** for scheduling
- **Docker** for containerization
- **Streamlit** (optional dashboard)

## 🐳 Getting Started with Docker (Recommended)

### 1. Prerequisites
- Docker Desktop installed
- A `.streamlit/secrets.toml` file with your Redshift credentials

### 2. Build the Image
docker build -t industrial-pipeline-service .

### 3. Run the Pipeline
docker run -d --name etl_worker \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/.streamlit:/app/.streamlit" \
  industrial-pipeline-service

### 4. Monitor Logs
docker logs -f etl_worker

## 📂 Project Structure
├── .streamlit/          # Secrets & config (never commit to git)
├── data/                # Raw CSV files from production
├── Dockerfile           # Docker build configuration
├── main.py              # Main ETL logic + scheduler
├── requirements.txt     # Project dependencies
└── README.md            # Documentation

## 📝 Important Note
The pipeline is built for Redshift, but it gracefully handles environments without a live database connection. In local testing, it will log the connection error but still complete the data cleaning and processing steps successfully.
