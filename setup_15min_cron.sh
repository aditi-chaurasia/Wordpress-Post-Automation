#!/bin/bash

# Setup script for Ubuntu server automation - 15 minute intervals
# This script installs dependencies and sets up cron jobs for every 15 minutes

set -e  # Exit on any error

echo "=========================================="
echo "Hindi News RSS to WordPress Automation Setup"
echo "15-Minute Interval Configuration"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_warning "Running as root. This is not recommended for security reasons."
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Update package list
print_status "Updating package list..."
sudo apt update

# Install Python3 and pip if not already installed
print_status "Installing Python3 and pip..."
sudo apt install -y python3 python3-pip python3-venv

# Install required system packages
print_status "Installing system dependencies..."
sudo apt install -y git curl wget cron

# Create virtual environment
print_status "Creating Python virtual environment..."
python3 -m venv venv

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
print_status "Installing Python dependencies..."
pip install -r requirements.txt

# Make scripts executable
print_status "Making scripts executable..."
chmod +x run_automation.sh
chmod +x setup_15min_cron.sh

# Create logs directory
print_status "Creating logs directory..."
mkdir -p logs

# Test the automation
print_status "Testing automation setup..."
if python3 -c "import wordpress; print('Import successful')" 2>/dev/null; then
    print_status "Python imports working correctly"
else
    print_error "Python imports failed. Please check your setup."
    exit 1
fi

# Set up cron jobs for 15-minute intervals
print_status "Setting up cron jobs for 15-minute intervals..."

# Get the current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRON_SCRIPT="$SCRIPT_DIR/run_automation.sh"

# Create cron job entries for 15-minute intervals
CRON_AUTOMATION="*/15 * * * * $CRON_SCRIPT >/dev/null 2>&1"
CRON_IMAGE_RETRY="0 */3 * * * cd $SCRIPT_DIR && python3 scheduler.py image_retry >/dev/null 2>&1"

# Remove existing automation cron jobs
print_status "Removing existing automation cron jobs..."
crontab -l 2>/dev/null | grep -v "$CRON_SCRIPT" | grep -v "scheduler.py" | crontab -

# Add new automation cron job (every 15 minutes)
(crontab -l 2>/dev/null; echo "$CRON_AUTOMATION") | crontab -
print_status "Added automation cron job (every 15 minutes)"

# Add image retry cron job (every 3 hours)
(crontab -l 2>/dev/null; echo "$CRON_IMAGE_RETRY") | crontab -
print_status "Added image retry cron job (every 3 hours)"

# Display current cron jobs
print_status "Current cron jobs:"
crontab -l

# Start cron service
print_status "Starting cron service..."
sudo systemctl enable cron
sudo systemctl start cron

# Create monitoring script
print_status "Creating monitoring script..."
cat > monitor_automation.sh << 'EOF'
#!/bin/bash

# Monitoring script for automation
echo "=== WordPress Automation Status ==="
echo "Current time: $(date)"
echo ""
echo "Last automation run:"
tail -n 1 cron_automation.log 2>/dev/null || echo "No logs found"
echo ""
echo "Recent scheduler logs (last 10 lines):"
tail -n 10 scheduler.log 2>/dev/null || echo "No scheduler logs found"
echo ""
echo "Cron jobs:"
crontab -l | grep -E "(run_automation|scheduler)" || echo "No automation cron jobs found"
echo ""
echo "Process status:"
ps aux | grep -E "(python3.*scheduler|run_automation)" | grep -v grep || echo "No automation processes running"
echo ""
echo "Log files in logs/ directory:"
ls -la logs/ 2>/dev/null || echo "No logs directory found"
echo ""
echo "WordPress connectivity test:"
curl -s -I "$(grep 'site_url' config.json | cut -d'"' -f4)" | head -n 1 || echo "Cannot connect to WordPress site"
EOF

chmod +x monitor_automation.sh

# Create restart script
print_status "Creating restart script..."
cat > restart_automation.sh << 'EOF'
#!/bin/bash

echo "Restarting WordPress automation..."

# Kill any running automation processes
pkill -f "python3.*scheduler" || true
pkill -f "run_automation" || true

# Restart cron service
sudo systemctl restart cron

echo "Automation restarted successfully"
echo "Next run scheduled in 15 minutes"
EOF

chmod +x restart_automation.sh

# Final instructions
echo ""
echo "=========================================="
echo "Setup completed successfully!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Update config.json with your WordPress credentials"
echo "2. Test the automation manually: ./run_automation.sh"
echo "3. Monitor the automation: ./monitor_automation.sh"
echo "4. Check logs in the 'logs' directory"
echo ""
echo "Cron jobs configured:"
echo "- Automation runs every 15 minutes"
echo "- Image retry runs every 3 hours"
echo ""
echo "Management commands:"
echo "- Monitor: ./monitor_automation.sh"
echo "- Restart: ./restart_automation.sh"
echo "- View cron jobs: crontab -l"
echo "- Edit cron jobs: crontab -e"
echo ""
echo "Log files:"
echo "- cron_automation.log: Shell script logs"
echo "- scheduler.log: Python scheduler logs"
echo "- logs/scheduler_*.log: Individual run logs"
echo ""
print_status "Setup completed! Your automation will start running every 15 minutes." 