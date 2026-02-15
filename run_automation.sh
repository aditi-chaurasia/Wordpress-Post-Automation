#!/bin/bash

# Automation wrapper script for cron jobs
# This script sets up the environment and runs the automation

# Set the working directory to the script location
cd "$(dirname "$0")"

# Set environment variables
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export PYTHONIOENCODING=utf-8

# Log file for shell script
LOG_FILE="cron_automation.log"

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Start logging
log_message "Starting automation wrapper script"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    log_message "ERROR: Python3 is not installed or not in PATH"
    exit 1
fi

# Check if required files exist
if [ ! -f "wordpress.py" ]; then
    log_message "ERROR: wordpress.py not found"
    exit 1
fi

if [ ! -f "scheduler.py" ]; then
    log_message "ERROR: scheduler.py not found"
    exit 1
fi

if [ ! -f "config.json" ]; then
    log_message "ERROR: config.json not found"
    exit 1
fi

# Check if virtual environment exists and activate it (optional)
if [ -d "venv" ]; then
    log_message "Activating virtual environment"
    source venv/bin/activate
fi

# Run the automation
log_message "Running automation script"
python3 scheduler.py automation

# Check exit status
if [ $? -eq 0 ]; then
    log_message "Automation completed successfully"
else
    log_message "Automation failed with exit code $?"
fi

# Optional: Run image retry every few hours (uncomment if needed)
# python3 scheduler.py image_retry

log_message "Automation wrapper script finished" 