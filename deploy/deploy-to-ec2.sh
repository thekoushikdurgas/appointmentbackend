#!/bin/bash

# Appointment360 FastAPI Backend - EC2 Deployment Script
# This script automates the deployment of the Appointment360 backend to AWS EC2

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
APP_DIR="/home/ubuntu/appointment360"
SERVICE_NAME="appointmentbackend"
NGINX_SITE="appointment360"

# Helper functions
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root (we need sudo for some operations)
if [ "$EUID" -eq 0 ]; then 
    print_error "Please do not run this script as root. It will use sudo when needed."
    exit 1
fi

print_status "Starting Appointment360 Backend Deployment"
print_status "=============================================="

# Phase 1: System Updates and Prerequisites
print_status "Phase 1: Updating system packages..."
sudo apt update
sudo apt upgrade -y

print_status "Installing prerequisites..."

# Add deadsnakes PPA for Python 3.11 (Ubuntu 22.04 doesn't include it by default)
print_status "Adding deadsnakes PPA for Python 3.11..."
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update

# Install Python 3.11 and related packages
print_status "Installing Python 3.11..."
sudo apt install -y \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip \
    build-essential \
    libpq-dev \
    nginx \
    git \
    curl

# Verify Python version
PYTHON_VERSION=$(python3.11 --version 2>&1 | awk '{print $2}')
print_status "Python version: $PYTHON_VERSION"

# Phase 2: Application Setup
print_status "Phase 2: Setting up application..."

# Check if directory exists
if [ -d "$APP_DIR" ]; then
    print_warning "Directory $APP_DIR already exists. Pulling latest changes..."
    cd "$APP_DIR"
    git pull
else
    print_error "Directory $APP_DIR does not exist."
    print_error "Please clone the repository first:"
    print_error "  git clone <repository-url> $APP_DIR"
    exit 1
fi

cd "$APP_DIR"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    print_status "Creating Python virtual environment..."
    python3.11 -m venv venv
    if [ $? -ne 0 ]; then
        print_error "Failed to create virtual environment with python3.11"
        print_warning "Trying with default python3..."
        python3 -m venv venv
        if [ $? -ne 0 ]; then
            print_error "Failed to create virtual environment"
            exit 1
        fi
    fi
else
    print_status "Virtual environment already exists."
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install dependencies
print_status "Installing application dependencies..."
pip install -r requirements.txt

# Create required directories
print_status "Creating required directories..."
mkdir -p uploads/avatars uploads/exports logs
chmod -R 755 uploads logs

# Check for .env file
if [ ! -f ".env" ]; then
    print_warning ".env file not found!"
    print_warning "Please create .env file with production configuration."
    print_warning "You can use deploy/.env.example as a template."
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    print_status ".env file found."
fi

# Phase 3: Systemd Service Configuration
print_status "Phase 3: Configuring systemd service..."

# Copy service file
if [ -f "deploy/appointmentbackend.service" ]; then
    sudo cp deploy/appointmentbackend.service /etc/systemd/system/${SERVICE_NAME}.service
    print_status "Service file copied to /etc/systemd/system/${SERVICE_NAME}.service"
else
    print_error "Service file not found at deploy/appointmentbackend.service"
    exit 1
fi

# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable ${SERVICE_NAME}

# Phase 4: Nginx Configuration
print_status "Phase 4: Configuring Nginx..."

# Copy Nginx configuration
if [ -f "deploy/nginx-appointment360.conf" ]; then
    sudo cp deploy/nginx-appointment360.conf /etc/nginx/sites-available/${NGINX_SITE}
    print_status "Nginx configuration copied"
else
    print_error "Nginx configuration not found at deploy/nginx-appointment360.conf"
    exit 1
fi

# Create symlink if it doesn't exist
if [ ! -L "/etc/nginx/sites-enabled/${NGINX_SITE}" ]; then
    sudo ln -s /etc/nginx/sites-available/${NGINX_SITE} /etc/nginx/sites-enabled/
    print_status "Nginx site enabled"
fi

# Remove default site if it exists
if [ -L "/etc/nginx/sites-enabled/default" ]; then
    sudo rm /etc/nginx/sites-enabled/default
    print_status "Default Nginx site removed"
fi

# Test Nginx configuration
print_status "Testing Nginx configuration..."
if sudo nginx -t; then
    print_status "Nginx configuration is valid"
else
    print_error "Nginx configuration test failed!"
    exit 1
fi

# Phase 5: Firewall Configuration
print_status "Phase 5: Configuring firewall (UFW)..."

# Set default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (important - do this first!)
sudo ufw allow ssh
print_status "SSH access allowed"

# Allow HTTP
sudo ufw allow http
print_status "HTTP (port 80) allowed"

# Allow HTTPS (for future SSL setup)
sudo ufw allow https
print_status "HTTPS (port 443) allowed"

# Enable UFW (with confirmation prompt)
print_warning "Enabling UFW firewall..."
print_warning "Make sure SSH access is working before continuing!"
read -p "Enable UFW now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo ufw --force enable
    print_status "UFW enabled"
else
    print_warning "UFW not enabled. You can enable it later with: sudo ufw enable"
fi

# Show firewall status
sudo ufw status verbose

# Phase 6: Start Services
print_status "Phase 6: Starting services..."

# Start systemd service
print_status "Starting ${SERVICE_NAME} service..."
sudo systemctl restart ${SERVICE_NAME}

# Wait a moment for service to start
sleep 3

# Check service status
if sudo systemctl is-active --quiet ${SERVICE_NAME}; then
    print_status "${SERVICE_NAME} service is running"
else
    print_error "${SERVICE_NAME} service failed to start!"
    print_error "Check logs with: sudo journalctl -u ${SERVICE_NAME} -n 50"
    exit 1
fi

# Start/restart Nginx
print_status "Starting Nginx..."
sudo systemctl restart nginx

if sudo systemctl is-active --quiet nginx; then
    print_status "Nginx is running"
else
    print_error "Nginx failed to start!"
    print_error "Check logs with: sudo journalctl -u nginx -n 50"
    exit 1
fi

# Enable Nginx on boot
sudo systemctl enable nginx

# Phase 7: Verification
print_status "Phase 7: Verifying deployment..."

# Get server IP (or use the configured one)
SERVER_IP="34.229.94.175"

print_status "Testing health endpoint..."
if curl -f -s "http://${SERVER_IP}/health" > /dev/null; then
    print_status "Health endpoint is responding"
else
    print_warning "Health endpoint test failed. Service may still be starting..."
fi

print_status "Testing database health endpoint..."
if curl -f -s "http://${SERVER_IP}/health/db" > /dev/null; then
    print_status "Database health endpoint is responding"
else
    print_warning "Database health endpoint test failed. Check database connection."
fi

# Final Summary
print_status ""
print_status "=============================================="
print_status "Deployment Complete!"
print_status "=============================================="
print_status ""
print_status "Application URL: http://${SERVER_IP}"
print_status "API Documentation: http://${SERVER_IP}/docs"
print_status "Health Check: http://${SERVER_IP}/health"
print_status ""
print_status "Useful commands:"
print_status "  Service status: sudo systemctl status ${SERVICE_NAME}"
print_status "  Service logs:   sudo journalctl -u ${SERVICE_NAME} -f"
print_status "  Nginx logs:     sudo tail -f /var/log/nginx/error.log"
print_status "  Restart service: sudo systemctl restart ${SERVICE_NAME}"
print_status "  Restart Nginx:    sudo systemctl restart nginx"
print_status ""
print_status "Next steps:"
print_status "  1. Verify application is accessible at http://${SERVER_IP}"
print_status "  2. Check service logs for any errors"
print_status "  3. Configure SSL/HTTPS if needed (Let's Encrypt)"
print_status "  4. Set up monitoring and logging"
print_status ""

