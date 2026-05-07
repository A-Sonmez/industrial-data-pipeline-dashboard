Industrial Data Pipeline & Analytics Dashboard
🏭 Smart Factory Data Management Solution
This project features an automated ETL (Extract, Transform, Load) system designed for high-volume manufacturing and inventory data. It orchestrates the flow of data from decentralized network sources into AWS Redshift, complemented by an interactive Streamlit dashboard for real-time technical analysis.

🎯 Problems Solved
Data Fragmentation: Consolidated scattered Excel and CSV files from various network directories into a single source of truth (Redshift).

Manual Overhead: Replaced time-consuming and error-prone hourly manual data processing with a fully autonomous pipeline.

Memory Optimization: Overcame RAM limitations during the processing of large-scale datasets through optimized chunking.

Security Vulnerabilities: Decoupled sensitive credentials (server IPs, passwords) from the source code using secure secret management.

🛠 Technical Architecture
⚙️ Autonomous ETL Pipeline (main.py)
Scheduling: Implemented APScheduler to automate data tasks on an hourly basis.

Data Cleaning: Leveraged Pandas and Regex for robust data sanitization (handling corrupted characters, null values, and formatting).

Database Logic: Developed an UPSERT (Merge) logic using temporary tables in Redshift to prevent duplicate records and ensure data integrity.

📊 Interactive Dashboard (dashboard.py)
Framework: Built with Streamlit for a lightweight and responsive UI.

Key Metrics: Visualizes Production Volume, Error Rates, and Part-based summaries.

Visualizations: Integrated Altair for time-series trend analysis and distribution charts.

UX: Dynamic filtering by production step, variant, and date range for deep-dive analysis.

🚀 Installation & Usage

Clone the repository:
git clone https://github.com/ammarsonmez/industrial-data-pipeline.git
cd industrial-data-pipeline

Install dependencies:
pip install -r requirements.txt

Launch the Dashboard:
streamlit run dashboard.py

Start the ETL Service:
python main.py

🔒 Security & Context
Anonymization: Corporate network paths and sensitive server details have been anonymized for privacy.

Secret Management: Database credentials are managed via .streamlit/secrets.toml.

Background: This project was inspired by real-world manufacturing challenges encountered during my internship at Schaeffler, designed to meet industrial-grade production requirements.
