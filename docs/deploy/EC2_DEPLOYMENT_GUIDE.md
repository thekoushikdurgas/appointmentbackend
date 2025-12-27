# EC2 Deployment Guide for Appointment360 Backend

This guide provides step-by-step instructions for deploying the Appointment360 FastAPI backend to AWS EC2 with Nginx reverse proxy and systemd service management.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [EC2 Instance Setup](#ec2-instance-setup)
3. [Application Deployment](#application-deployment)
4. [Service Configuration](#service-configuration)
5. [Verification](#verification)
6. [Troubleshooting](#troubleshooting)
7. [Maintenance](#maintenance)

## Prerequisites

Before starting the deployment, ensure you have:

- **AWS EC2 Instance**: Ubuntu 22.04 LTS or later
- **SSH Access**: Key pair for EC2 instance access
- **Database**: PostgreSQL database accessible from EC2 (or connection details)
- **Domain/IP**: EC2 instance public IP (34.229.94.175)
- **Security Groups**: Configured to allow:
  - SSH (port 22)
  - HTTP (port 80)
  - HTTPS (port 443, if using SSL)

### Required Information

Gather the following information before deployment:

- Database connection details (host, port, user, password, database name)
- Secret keys for JWT tokens
- API keys for external services (Gemini, Apollo, etc.)
- AWS credentials (if using S3)
- MongoDB connection string (if used)

## EC2 Instance Setup

### Step 1: Connect to EC2 Instance

```bash
ssh -i your-key.pem ubuntu@34.229.94.175
```

### Step 2: Update System Packages

```bash
sudo apt update
sudo apt upgrade -y
```

### Step 3: Install Prerequisites

```bash
# Install Python 3.11 and build tools
sudo apt install -y python3.11 python3.11-venv python3-pip build-essential

# Install PostgreSQL client libraries
sudo apt install -y libpq-dev

# Install Nginx
sudo apt install -y nginx

# Install Git
sudo apt install -y git
```

### Step 4: Clone Repository

```bash
cd /home/ubuntu
git clone <your-repository-url> appointment360
cd appointment360
```

**Note**: Replace `<your-repository-url>` with your actual Git repository URL.

## Application Deployment

### Step 1: Set Up Python Virtual Environment

```bash
cd /home/ubuntu/appointment360
python3.11 -m venv venv
source venv/bin/activate
```

### Step 2: Install Dependencies

```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables

```bash
# Copy the example environment file
cp deploy/env.example .env

# Edit the .env file with your production values
nano .env
```

**Critical Environment Variables to Configure**:

- `POSTGRES_USER`, `POSTGRES_PASS`, `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB` - Database connection
- `SECRET_KEY` - Strong random secret key for JWT tokens
- `BASE_URL` - Set to `http://34.229.94.175`
- `ENVIRONMENT` - Set to `production`
- `DEBUG` - Set to `false`
- API keys for external services (Gemini, etc.)

### Step 4: Create Required Directories

```bash
mkdir -p uploads/avatars uploads/exports logs
chmod -R 755 uploads logs
```

### Step 5: Test Application Locally (Optional)

```bash
# Activate virtual environment
source venv/bin/activate

# Test that the application starts
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Press `Ctrl+C` to stop the test server.

## Service Configuration

### Step 1: Configure Systemd Service

```bash
# Copy the service file
sudo cp deploy/appointmentbackend.service /etc/systemd/system/

# Reload systemd daemon
sudo systemctl daemon-reload

# Enable the service (starts on boot)
sudo systemctl enable appointmentbackend

# Start the service
sudo systemctl start appointmentbackend

# Check service status
sudo systemctl status appointmentbackend
```

**View Service Logs**:

```bash
# View recent logs
sudo journalctl -u appointmentbackend -n 50

# Follow logs in real-time
sudo journalctl -u appointmentbackend -f
```

### Step 2: Configure Nginx Reverse Proxy

```bash
# Copy Nginx configuration
sudo cp deploy/nginx-appointment360.conf /etc/nginx/sites-available/appointment360

# Create symlink to enable the site
sudo ln -s /etc/nginx/sites-available/appointment360 /etc/nginx/sites-enabled/

# Remove default site (optional)
sudo rm /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t

# If test passes, reload Nginx
sudo systemctl reload nginx

# Enable Nginx on boot
sudo systemctl enable nginx
```

**Nginx Configuration File**: `deploy/nginx-appointment360.conf`

This configuration:
- Listens on port 80
- Proxies requests to FastAPI on `localhost:8000`
- Includes proper headers for FastAPI
- Supports WebSocket connections
- Configures timeouts for long-running requests

### Step 3: Configure Firewall (UFW)

```bash
# Set default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (IMPORTANT - do this first!)
sudo ufw allow ssh

# Allow HTTP
sudo ufw allow http

# Allow HTTPS (for future SSL setup)
sudo ufw allow https

# Enable UFW
sudo ufw enable

# Verify firewall status
sudo ufw status verbose
```

**Important**: Ensure SSH access is working before enabling UFW, or you may lock yourself out!

## Verification

### Step 1: Check Service Status

```bash
# Check systemd service
sudo systemctl status appointmentbackend

# Check Nginx
sudo systemctl status nginx
```

### Step 2: Test Health Endpoints

```bash
# Test basic health endpoint
curl http://34.229.94.175/health

# Test database health endpoint
curl http://34.229.94.175/health/db

# Test API documentation
curl http://34.229.94.175/docs
```

Expected responses:
- `/health` should return `{"status": "healthy", "environment": "production"}`
- `/health/db` should return database connection status
- `/docs` should return the Swagger UI HTML

### Step 3: Test from Browser

Open in your browser:
- **API Base**: http://34.229.94.175
- **API Documentation**: http://34.229.94.175/docs
- **ReDoc**: http://34.229.94.175/redoc

### Step 4: Verify Logs

```bash
# Application logs
sudo journalctl -u appointmentbackend -n 100

# Nginx access logs
sudo tail -f /var/log/nginx/access.log

# Nginx error logs
sudo tail -f /var/log/nginx/error.log

# Application log file (if configured)
tail -f logs/app.log
```

## Troubleshooting

### Service Won't Start

**Check service status**:
```bash
sudo systemctl status appointmentbackend
```

**View error logs**:
```bash
sudo journalctl -u appointmentbackend -n 100 --no-pager
```

**Common issues**:
1. **Missing .env file**: Ensure `.env` file exists in `/home/ubuntu/appointment360/`
2. **Wrong paths**: Verify paths in `appointmentbackend.service` match your installation
3. **Permission errors**: Check file permissions on `uploads/` and `logs/` directories
4. **Database connection**: Verify database credentials in `.env` file

### Nginx 502 Bad Gateway

This usually means Nginx can't connect to the FastAPI application.

**Check**:
1. Is the FastAPI service running?
   ```bash
   sudo systemctl status appointmentbackend
   ```
2. Is the service listening on port 8000?
   ```bash
   sudo netstat -tlnp | grep 8000
   ```
3. Check Nginx error logs:
   ```bash
   sudo tail -f /var/log/nginx/error.log
   ```

### Database Connection Issues

**Test database connection**:
```bash
# Activate virtual environment
source venv/bin/activate

# Test connection (if psql is installed)
psql "postgresql://user:password@host:port/database" -c "SELECT 1;"
```

**Check**:
1. Database credentials in `.env` file
2. Database security groups allow connections from EC2
3. Database host is accessible from EC2

### Port Already in Use

If port 8000 is already in use:

```bash
# Find process using port 8000
sudo lsof -i :8000

# Kill the process (replace PID with actual process ID)
sudo kill -9 PID
```

### Permission Denied Errors

**Fix directory permissions**:
```bash
# Ensure ubuntu user owns the application directory
sudo chown -R ubuntu:ubuntu /home/ubuntu/appointment360

# Set correct permissions
chmod -R 755 /home/ubuntu/appointment360
chmod 644 /home/ubuntu/appointment360/.env
```

## Maintenance

### Updating the Application

```bash
cd /home/ubuntu/appointment360

# Pull latest changes
git pull

# Activate virtual environment
source venv/bin/activate

# Update dependencies (if requirements.txt changed)
pip install -r requirements.txt

# Restart the service
sudo systemctl restart appointmentbackend

# Check status
sudo systemctl status appointmentbackend
```

### Viewing Logs

```bash
# Application logs (systemd)
sudo journalctl -u appointmentbackend -f

# Application logs (file)
tail -f logs/app.log

# Nginx access logs
sudo tail -f /var/log/nginx/access.log

# Nginx error logs
sudo tail -f /var/log/nginx/error.log
```

### Restarting Services

```bash
# Restart FastAPI service
sudo systemctl restart appointmentbackend

# Restart Nginx
sudo systemctl restart nginx

# Restart both
sudo systemctl restart appointmentbackend nginx
```

### Stopping Services

```bash
# Stop FastAPI service
sudo systemctl stop appointmentbackend

# Stop Nginx
sudo systemctl stop nginx
```

### Backup

**Backup application files**:
```bash
# Create backup directory
mkdir -p ~/backups

# Backup application
tar -czf ~/backups/appointment360-$(date +%Y%m%d).tar.gz /home/ubuntu/appointment360

# Backup .env file separately (contains secrets)
cp /home/ubuntu/appointment360/.env ~/backups/.env-$(date +%Y%m%d)
```

## Automated Deployment

For automated deployment, use the provided deployment script:

```bash
cd /home/ubuntu/appointment360
chmod +x deploy/deploy-to-ec2.sh
./deploy/deploy-to-ec2.sh
```

The script automates:
- System package updates
- Prerequisite installation
- Virtual environment setup
- Dependency installation
- Directory creation
- Service configuration
- Nginx configuration
- Firewall setup
- Service startup

## SSL/HTTPS Setup (Optional)

For production, consider setting up SSL/HTTPS using Let's Encrypt:

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain SSL certificate (replace with your domain)
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Certbot will automatically configure Nginx and set up auto-renewal
```

## Monitoring

### Check Resource Usage

```bash
# CPU and memory usage
htop

# Disk usage
df -h

# Service status
systemctl status appointmentbackend nginx
```

### Set Up Monitoring (Optional)

Consider setting up:
- **CloudWatch**: AWS CloudWatch for EC2 metrics
- **Application Monitoring**: Sentry, DataDog, or similar
- **Log Aggregation**: ELK stack, CloudWatch Logs, or similar

## Security Best Practices

1. **Keep system updated**: Regularly run `sudo apt update && sudo apt upgrade`
2. **Use strong secrets**: Generate strong random keys for `SECRET_KEY`
3. **Restrict SSH access**: Use key-based authentication, disable password auth
4. **Enable firewall**: UFW is configured, ensure it's enabled
5. **Regular backups**: Set up automated backups of application and database
6. **Monitor logs**: Regularly check logs for suspicious activity
7. **SSL/HTTPS**: Use SSL certificates for production
8. **Environment variables**: Never commit `.env` file to version control

## Rollback Procedure

If deployment fails and you need to rollback:

```bash
# Stop services
sudo systemctl stop appointmentbackend nginx

# Restore previous version
cd /home/ubuntu/appointment360
git checkout <previous-commit-hash>

# Restart services
sudo systemctl start appointmentbackend nginx
```

## Support

For issues or questions:
1. Check logs: `sudo journalctl -u appointmentbackend -n 100`
2. Review this guide's troubleshooting section
3. Check application documentation
4. Contact the development team

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [Systemd Documentation](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
- [UFW Documentation](https://help.ubuntu.com/community/UFW)

