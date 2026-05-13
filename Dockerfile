# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required for Redshift (PostgreSQL) drivers
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Ensure the log file exists and has the correct permissions
RUN touch pipeline_execution.log && chmod 777 pipeline_execution.log

# Define the command to run the ETL service
# Use ["streamlit", "run", "dashboard.py"] if you want to launch the UI instead
CMD ["python", "main.py"]
