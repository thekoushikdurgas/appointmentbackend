<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

## FastAPI with Uvicorn and Nginx on Ubuntu - Complete Production Setup

This comprehensive guide covers deploying a FastAPI application on Ubuntu using Uvicorn as the ASGI server, Gunicorn as the process manager, and Nginx as a reverse proxy.[^1][^2][^3]

### Prerequisites

Before starting, ensure your Ubuntu system has the necessary packages installed:[^2][^1]

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-dev python3-venv build-essential nginx -y
```


### Step 1: Create Your FastAPI Project

Set up your project directory with a virtual environment:[^3][^1][^2]

```bash
mkdir ~/my_fastapi_project
cd ~/my_fastapi_project
python3 -m venv venv
source venv/bin/activate
```

Install FastAPI and required dependencies:[^2][^3]

```bash
pip install fastapi uvicorn gunicorn
```

Create a simple FastAPI application (`main.py`):[^1]

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello from FastAPI on Ubuntu"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

Test your application locally:[^4]

```bash
uvicorn main:app --reload
```


### Step 2: Configure Gunicorn with Uvicorn Workers

For production, use Gunicorn as a process manager with Uvicorn workers. This provides better process management and multi-core CPU utilization.[^5][^3][^1][^2]

Create a Gunicorn configuration file (`gunicorn_conf.py`):[^2]

```python
bind = "0.0.0.0:8000"
workers = 4  # Recommended: (2 x CPU cores) + 1
worker_class = "uvicorn.workers.UvicornWorker"
keepalive = 120
timeout = 30
graceful_timeout = 20
```

The number of workers should typically be `(2 × number_of_cpu_cores) + 1`. For a 2-core system, use 4-5 workers.[^6]

Test Gunicorn manually:[^3][^2]

```bash
gunicorn -k uvicorn.workers.UvicornWorker -c gunicorn_conf.py main:app
```

**Important:** When using systemd services, ensure you set `reload=False` in your configuration. The auto-reload feature can cause 80-100% CPU usage when running as a system service.[^7][^8]

### Step 3: Create a Systemd Service

Create a systemd service file to manage your application automatically:[^9][^3][^2]

```bash
sudo nano /etc/systemd/system/fastapi.service
```

Add the following configuration:[^3][^2]

```ini
[Unit]
Description=FastAPI Application with Gunicorn and Uvicorn
After=network.target

[Service]
User=your_username
Group=www-data
WorkingDirectory=/home/your_username/my_fastapi_project
Environment="PATH=/home/your_username/my_fastapi_project/venv/bin"
ExecStart=/home/your_username/my_fastapi_project/venv/bin/gunicorn \
    -k uvicorn.workers.UvicornWorker \
    -c /home/your_username/my_fastapi_project/gunicorn_conf.py \
    main:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Replace `your_username` with your actual username. The `Restart=always` and `RestartSec=5` ensure automatic restarts if the service crashes.[^9][^2]

Enable and start the service:[^9][^2][^3]

```bash
sudo systemctl daemon-reload
sudo systemctl start fastapi
sudo systemctl enable fastapi
sudo systemctl status fastapi
```


### Step 4: Configure Nginx as Reverse Proxy

Create an Nginx configuration file:[^10][^11][^1]

```bash
sudo nano /etc/nginx/sites-available/fastapi_app
```

Add the following configuration:[^11][^1][^3]

```nginx
server {
    listen 80;
    server_name your_domain_or_ip;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

The proxy headers are essential for FastAPI to receive correct client information. The `X-Forwarded-Proto` header is particularly important for CORS and HTTPS detection behind proxies.[^12][^11][^1]

Enable the site and test the configuration:[^1][^3]

```bash
sudo ln -s /etc/nginx/sites-available/fastapi_app /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```


### Step 5: Optional - Add Rate Limiting and Security

Add rate limiting to protect against DDoS attacks. In your Nginx configuration:[^13]

```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

server {
    listen 80;
    server_name your_domain_or_ip;

    location / {
        limit_req zone=api_limit burst=20 nodelay;
        proxy_pass http://127.0.0.1:8000;
        # ... rest of proxy settings
    }
}
```

This limits each IP to 10 requests per second with a burst allowance of 20.[^13]

### Step 6: Environment Variables Management

For production deployments, use environment variables properly. Create a `.env` file in your project directory:[^14][^15]

```bash
# .env
DATABASE_URL=postgresql://user:password@localhost/dbname
SECRET_KEY=your-secret-key-here
DEBUG=False
```

Load environment variables in your FastAPI app:[^15][^14]

```python
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY")
DEBUG = os.getenv("DEBUG", "False") == "True"
```

For production servers, set environment variables directly in the systemd service file or use your hosting platform's configuration management.[^14]

### Step 7: SSL/HTTPS Configuration (Recommended)

For production, always use HTTPS. Install Certbot for free SSL certificates:[^16]

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your_domain.com
```

Certbot will automatically update your Nginx configuration to redirect HTTP to HTTPS and handle certificate renewal.[^16]

### Monitoring and Logging

Configure proper logging for production. In your `gunicorn_conf.py`:[^17]

```python
loglevel = "info"
accesslog = "/var/log/fastapi/access.log"
errorlog = "/var/log/fastapi/error.log"
```

Create the log directory:[^17]

```bash
sudo mkdir -p /var/log/fastapi
sudo chown your_username:www-data /var/log/fastapi
```

View logs using systemd:[^9]

```bash
sudo journalctl -u fastapi -f  # Follow logs in real-time
sudo journalctl -u fastapi --since "1 hour ago"  # Last hour
```


### Common Commands for Management

Manage your FastAPI service:[^2][^9]

```bash
# Restart after code changes
sudo systemctl restart fastapi

# Check service status
sudo systemctl status fastapi

# Stop the service
sudo systemctl stop fastapi

# View logs
sudo journalctl -u fastapi -n 100
```

Manage Nginx:[^1][^3]

```bash
# Test configuration
sudo nginx -t

# Reload configuration
sudo systemctl reload nginx

# Restart Nginx
sudo systemctl restart nginx
```


### Performance Optimization Tips

**Worker Configuration**: The optimal number of workers depends on your application type:[^6]

- CPU-bound tasks: `(2 × cores) + 1` workers
- I/O-bound tasks: Can use more workers (up to `4 × cores`)
- Always monitor and adjust based on actual performance

**Timeout Settings**: Adjust based on your longest-running endpoint:[^11]

```python
# In gunicorn_conf.py
timeout = 30  # Default: 30 seconds
graceful_timeout = 20  # Time for graceful shutdown
keepalive = 120  # Keep connections alive
```

**Unix Socket Communication**: For better performance, use Unix sockets instead of TCP:[^11]

In `gunicorn_conf.py`:

```python
bind = "unix:/tmp/uvicorn.sock"
```

In Nginx configuration:

```nginx
location / {
    proxy_pass http://unix:/tmp/uvicorn.sock;
    # ... rest of configuration
}
```

This setup provides a robust, production-ready deployment of FastAPI on Ubuntu with proper process management, automatic restarts, reverse proxy capabilities, and security considerations.[^11][^3][^1][^2]
<span style="display:none">[^18][^19][^20][^21][^22][^23][^24][^25][^26][^27][^28][^29][^30][^31][^32][^33][^34][^35][^36][^37][^38][^39][^40][^41][^42][^43][^44][^45][^46][^47][^48][^49][^50][^51][^52][^53][^54]</span>

<div align="center">⁂</div>

[^1]: https://dev.to/udara_dananjaya/setting-up-a-fastapi-project-with-nginx-reverse-proxy-on-ubuntu-883

[^2]: https://gist.github.com/ShilGen/abaeafe8b130ccd8d43edde4af8d6dce

[^3]: https://dev.to/shuv1824/deploy-fastapi-application-on-ubuntu-with-nginx-gunicorn-and-uvicorn-3mbl

[^4]: https://fastapi.tiangolo.com/deployment/manually/

[^5]: https://fastapi.xiniushu.com/sv/deployment/server-workers/

[^6]: https://github.com/tiangolo/fastapi/issues/1727

[^7]: https://github.com/fastapi/fastapi/discussions/7357

[^8]: https://github.com/tiangolo/fastapi/issues/1741

[^9]: https://santoshm.com.np/2024/02/15/deploying-a-fastapi-project-on-a-linux-server-with-nginx-and-systemd-service-a-simplified-guide-with-uvicorn-and-hot-reload/

[^10]: https://stackoverflow.com/questions/62898917/running-fastapi-app-using-uvicorn-on-ubuntu-server

[^11]: https://www.codearmo.com/python-tutorial/ultimate-guide-deploy-fastapi-app-nginx-linux

[^12]: https://www.reddit.com/r/FastAPI/comments/1lfqwzb/fastapi_cros_error_with_nginx/

[^13]: https://blog.stackademic.com/securing-apis-with-fastapi-489c3d4d1ea0

[^14]: https://stackoverflow.com/questions/68156262/how-to-set-environment-variable-based-on-development-or-production-in-fastapi

[^15]: https://dev.to/yanagisawahidetoshi/efficiently-using-environment-variables-in-fastapi-4lal

[^16]: https://www.youtube.com/watch?v=ut4eTMg1kpM

[^17]: https://konfuzio.com/en/configuration-of-fastapi-logging-locally-and-in-production/

[^18]: https://zenodo.org/record/3387092/files/main.pdf

[^19]: http://arxiv.org/pdf/2301.05522.pdf

[^20]: https://pmc.ncbi.nlm.nih.gov/articles/PMC10577930/

[^21]: https://arxiv.org/pdf/2211.14417.pdf

[^22]: https://jutif.if.unsoed.ac.id/index.php/jurnal/article/download/1062/394

[^23]: https://onlinelibrary.wiley.com/doi/10.1002/spe.3383

[^24]: https://arxiv.org/pdf/1808.08192v2.pdf

[^25]: https://arxiv.org/pdf/2305.00600.pdf

[^26]: https://hoop.dev/blog/the-simplest-way-to-make-fastapi-nginx-work-like-it-should/

[^27]: https://geekyshows.com/blog/post/deploy-fas/

[^28]: https://stackoverflow.com/questions/65594905/how-can-i-deploy-fastapi-manually-on-a-ubuntu-server

[^29]: https://dl.acm.org/doi/pdf/10.1145/3673038.3673123

[^30]: http://arxiv.org/pdf/0706.2748.pdf

[^31]: https://arxiv.org/pdf/2104.07508.pdf

[^32]: https://arxiv.org/html/2404.16393v1

[^33]: https://arxiv.org/pdf/2210.01073.pdf

[^34]: https://arxiv.org/pdf/2208.13068.pdf

[^35]: https://arxiv.org/pdf/1910.01558.pdf

[^36]: https://stribny.name/posts/fastapi-production/

[^37]: http://arxiv.org/pdf/2411.01129.pdf

[^38]: https://arxiv.org/pdf/2503.14443.pdf

[^39]: https://arxiv.org/pdf/2403.00515.pdf

[^40]: http://arxiv.org/pdf/2311.07818.pdf

[^41]: https://arxiv.org/pdf/2211.02762.pdf

[^42]: https://arxiv.org/pdf/2402.03671.pdf

[^43]: https://community.sanicframework.org/t/correct-settings-for-uvicorn-gunicorn-for-production/694

[^44]: https://peerj.com/articles/20061

[^45]: https://www.emerald.com/sef/article/doi/10.1108/SEF-12-2024-0883/1276233/Unveiling-climate-risk-s-role-in-ESG-and-firm

[^46]: https://www.semanticscholar.org/paper/1f06e05264d467d359bf7555a3f77e334cc4b14c

[^47]: http://neptjournal.com/upload-images/(22)D-1073.pdf

[^48]: https://www.semanticscholar.org/paper/74e62f76952fd3e2707f7cb000b619ac86e84881

[^49]: https://acsess.onlinelibrary.wiley.com/doi/10.1094/FG-2011-0126-01-RS

[^50]: https://neptjournal.com/upload-images/(15)D-1118.pdf

[^51]: https://www.semanticscholar.org/paper/fa7f998eaedb97865db9a21b3a2a46059204b237

[^52]: https://www.semanticscholar.org/paper/01f519568977c66dc3c5b2840fe40f25b51a0496

[^53]: https://journal.unaab.edu.ng/index.php/JAgSE/article/view/2012

[^54]: https://pmc.ncbi.nlm.nih.gov/articles/PMC8049414/

