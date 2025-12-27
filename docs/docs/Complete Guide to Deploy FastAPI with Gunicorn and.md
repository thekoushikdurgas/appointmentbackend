<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

## Complete Guide to Deploy FastAPI with Gunicorn and Uvicorn Workers on Ubuntu with NGINX

This comprehensive guide covers the deployment process for FastAPI applications using Gunicorn as the process manager with Uvicorn workers, systemd for service management, and NGINX as a reverse proxy on Ubuntu.

### Prerequisites

Before starting, ensure you have:

- Ubuntu 18.04 or later
- Python 3.8 or higher installed
- NGINX installed and running
- Root or sudo access to the server
- Your FastAPI application code ready

### Step 1: System Preparation and Dependencies

Update your system and install required packages:[^1][^2]

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-dev python3-venv build-essential nginx
```

### Step 2: Project Setup

Create your project directory and set up a virtual environment:

```bash
# Create project directory
sudo mkdir -p /var/www/appointmentbackend
cd /var/www/appointmentbackend

# Create source directory
sudo mkdir src

# Set up virtual environment
python3 -m venv venv
source venv/bin/activate

# Navigate to source directory
cd src
```

### Step 3: Deploy Your Application Code

Pull your FastAPI application from your repository:[^1]

```bash
git init
git remote add origin https://github.com/thekoushikdurgas/appointmentbackend.git
git pull origin main
```

### Step 4: Install Python Dependencies

Install FastAPI, Gunicorn, and Uvicorn along with your application dependencies:

```bash
pip install -r requirements.txt
pip install fastapi gunicorn uvicorn[standard]
```

### Step 5: Test Your Application

Before configuring systemd, test that your application runs correctly with Gunicorn and Uvicorn workers:[^2][^1]

```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000
```

**Command breakdown:**

- `-w 4`: Number of worker processes (typically 2-4 × CPU cores)[^6][^2]
- `-k uvicorn.workers.UvicornWorker`: Specifies Uvicorn worker class for ASGI support[^4][^2]
- `main:app`: Your FastAPI application module and instance
- `--bind 0.0.0.0:8000`: Bind address and port[^7]

If successful, you should see Gunicorn starting with Uvicorn workers. Press `Ctrl+C` to stop the test server.

### Step 6: Create Systemd Service File

Create a systemd service to manage your FastAPI application:[^8][^3][^1]

```bash
sudo nano /etc/systemd/system/appointmentbackend.service
```

Add the following configuration:[^3][^4][^1]

```ini
[Unit]
Description=Gunicorn instance to serve FastAPI application
After=network.target

[Service]
User=<username>
Group=www-data
WorkingDirectory=/var/www/appointmentbackend/src
Environment="PATH=/var/www/appointmentbackend/venv/bin"
ExecStart=/var/www/appointmentbackend/venv/bin/gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 127.0.0.1:8000
Restart=always
RestartSec=10
StandardOutput=append:/var/www/appointmentbackend/logs/access.log
StandardError=append:/var/www/appointmentbackend/logs/error.log

[Install]
WantedBy=multi-user.target
```

**Configuration explanation:**

- `User`: The system user running the service (replace `<username>`)
- `Group`: Group ownership (typically `www-data` for web services)
- `WorkingDirectory`: Your application's source directory
- `Environment`: Path to virtual environment binaries
- `ExecStart`: Full command to start Gunicorn
- `Restart=always`: Auto-restart on failure
- `RestartSec=10`: Wait 10 seconds before restarting[^8]

Create the logs directory:

```bash
sudo mkdir -p /var/www/appointmentbackend/logs
```

### Step 7: Enable and Start the Service

Reload systemd, enable auto-start, and start your service:[^9][^1][^8]

```bash
# Reload systemd daemon to recognize new service
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable appointmentbackend

# Start the service
sudo systemctl start appointmentbackend

# Check service status
sudo systemctl status appointmentbackend
```

Your FastAPI application should now be running as a background service.

### Step 8: Configure NGINX as Reverse Proxy

Create an NGINX configuration file for your application:[^5][^2][^1]

```bash
sudo nano /etc/nginx/sites-available/appointmentbackend
```

Add the following configuration:[^10][^2][^1]

```nginx
server {
    listen 80;
    server_name 34.229.94.175;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Optional: Limit request size (helps prevent DoS attacks)
    client_max_body_size 10M;
}
```

**Configuration parameters:**

- `listen 80`: Listen on port 80 (HTTP)
- `server_name`: Your domain name or server IP address
- `proxy_pass`: Forward requests to Gunicorn on port 8000
- `proxy_set_header`: Pass client information to backend[^2][^1]
- `client_max_body_size`: Maximum request body size[^11][^10]

### Step 9: Enable NGINX Configuration

Create a symbolic link and restart NGINX:[^1][^2]

```bash
# Create symbolic link to enable the site
sudo ln -s /etc/nginx/sites-available/appointmentbackend /etc/nginx/sites-enabled/

# Test NGINX configuration for syntax errors
sudo nginx -t

# Restart NGINX to apply changes
sudo systemctl restart nginx
```

### Step 10: Verify Deployment

Your FastAPI application should now be accessible through NGINX. Test by visiting:

```
http://your_domain_or_ip
```

Check the automatic API documentation:

```
http://your_domain_or_ip/docs
```

### Optional Enhancements

#### Environment Variables Management

For production environments, use `.env` files to manage configuration:[^12][^13]

1. Install python-dotenv:

```bash
pip install python-dotenv
```

2. Create a `.env` file in your project root:

```txt
DATABASE_URL=postgresql://user:password@localhost:5432/mydb
SECRET_KEY=your-secret-key
DEBUG=False
```

3. Load environment variables in your FastAPI app:

```python
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY")
DEBUG = os.getenv("DEBUG") == "True"
```

#### Adjust NGINX Timeouts

For long-running requests, configure appropriate timeouts in your NGINX configuration:[^11]

```nginx
proxy_connect_timeout 300s;
proxy_read_timeout 300s;
proxy_send_timeout 300s;
```

#### Graceful Reloads

To reload your application with zero downtime, send a HUP signal to Gunicorn:[^14]

```bash
sudo systemctl reload appointmentbackend
# or
sudo kill -HUP $(pgrep -f gunicorn)
```

### Troubleshooting

**Check service logs:**

```bash
sudo journalctl -u appointmentbackend -f
```

**View application logs:**

```bash
tail -f /var/www/appointmentbackend/logs/access.log
tail -f /var/www/appointmentbackend/logs/error.log
```

**Check NGINX logs:**

```bash
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

**Common issues:**

- **Permission errors**: Ensure proper ownership of directories and files
- **Port conflicts**: Verify port 8000 isn't in use by another service
- **Import errors**: Confirm all dependencies are installed in the virtual environment
- **Connection refused**: Check that Gunicorn is binding to `127.0.0.1:8000`

### Production Considerations

1. **Worker count**: Set workers to 2-4 times the number of CPU cores for optimal performance[^6][^2]
2. **Security**: Always use HTTPS in production (consider Let's Encrypt for free SSL certificates)[^15][^5]
3. **Monitoring**: Implement logging and monitoring solutions
4. **Firewall**: Configure UFW or iptables to allow only necessary ports
5. **Regular updates**: Keep system packages, Python dependencies, and NGINX updated

This setup provides a robust, production-ready deployment of your FastAPI application with Gunicorn managing multiple Uvicorn workers, systemd ensuring service reliability, and NGINX efficiently handling client requests as a reverse proxy.
