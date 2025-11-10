<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

## FastAPI + Uvicorn Deployment on Ubuntu with Nginx

Deploying a FastAPI application with Uvicorn on an Ubuntu server using Nginx as a reverse proxy creates a robust, production-ready setup. This configuration leverages Gunicorn as a process manager with Uvicorn workers to handle ASGI requests, while Nginx efficiently manages client connections and serves as the entry point.

### Prerequisites

Before starting the deployment, ensure your Ubuntu server has the following:[^1][^2][^3]

- Ubuntu 18.04 or later
- Python 3.7+ installed
- Nginx installed and running
- Port 80 (HTTP) and 443 (HTTPS) open in your firewall
- SSH access to your server
- A FastAPI application ready for deployment


### Step 1: Set Up the Project Environment

Create a dedicated directory for your application and set up a Python virtual environment:[^2][^3][^1]

```bash
# Create project directory
mkdir ~/my_fastapi_project
cd ~/my_fastapi_project

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate
```

Clone your application from your repository or copy your files to this directory:[^3]

```bash
git init
git remote add origin <your-repo-url>
git pull origin <branch-name>
```


### Step 2: Install Dependencies

Install FastAPI, Uvicorn, and Gunicorn within your virtual environment:[^4][^1][^2]

```bash
pip install fastapi
pip install 'uvicorn[standard]'
pip install gunicorn
```

If your application has a requirements.txt file, install all dependencies:

```bash
pip install -r requirements.txt
```


### Step 3: Test Your Application

Before configuring the production setup, verify that your application works locally:[^5][^2]

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Test the endpoint using curl from another terminal:

```bash
curl http://localhost:8000
```


### Step 4: Configure Gunicorn with Uvicorn Workers

Gunicorn acts as a process manager, spawning multiple Uvicorn worker processes to handle concurrent requests. Create a Gunicorn configuration file for better management:[^6][^1][^5][^2]

```bash
vim gunicorn_conf.py
```

Add the following configuration:

```python
bind = "0.0.0.0:8000"
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
```

Run Gunicorn with the configuration:[^1][^2][^4]

```bash
gunicorn -k uvicorn.workers.UvicornWorker -c gunicorn_conf.py main:app
```

The `-k uvicorn.workers.UvicornWorker` flag tells Gunicorn to use Uvicorn as the worker class, enabling ASGI support required for FastAPI.[^6][^1]

### Step 5: Create a Systemd Service

To ensure your application runs automatically on boot and restarts on failure, create a systemd service:[^5][^2][^3]

```bash
sudo vim /etc/systemd/system/fastapi.service
```

Add the following configuration:[^2][^3]

```ini
[Unit]
Description=FastAPI Gunicorn service
After=network.target

[Service]
User=your_username
Group=www-data
WorkingDirectory=/home/your_username/my_fastapi_project
Environment="PATH=/home/your_username/my_fastapi_project/venv/bin"
ExecStart=/home/your_username/my_fastapi_project/venv/bin/gunicorn -k uvicorn.workers.UvicornWorker -c /home/your_username/my_fastapi_project/gunicorn_conf.py main:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**Important configuration notes**:[^7]

- Set `reload = False` in production to avoid high CPU usage (80-100%) when running from systemd
- Replace paths with your actual project location
- Adjust the user to match your system user

Enable and start the service:[^3][^2]

```bash
sudo systemctl daemon-reload
sudo systemctl start fastapi.service
sudo systemctl enable fastapi.service
sudo systemctl status fastapi.service
```


### Step 6: Configure Nginx as Reverse Proxy

Create an Nginx configuration file for your application:[^8][^1][^3]

```bash
sudo vim /etc/nginx/sites-available/fastapi_app
```

Add the following configuration:[^9][^8][^1]

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
    }
}
```

**For production applications with long-running requests**, adjust timeout settings:[^10]

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # Timeout configurations
    proxy_read_timeout 300s;
    proxy_send_timeout 300s;
    proxy_connect_timeout 60s;
}
```

Enable the configuration by creating a symbolic link:[^3]

```bash
sudo ln -s /etc/nginx/sites-available/fastapi_app /etc/nginx/sites-enabled/
```

Test the Nginx configuration and restart the service:[^1][^3]

```bash
sudo nginx -t
sudo systemctl restart nginx
```


### Step 7: Handle Client IP Addresses

When running behind Nginx, configure Uvicorn to trust proxy headers to correctly identify client IP addresses. If running Uvicorn programmatically:[^11]

```python
import uvicorn

config = uvicorn.Config(
    'main:app',
    host='0.0.0.0',
    port=8000,
    proxy_headers=True,
    forwarded_allow_ips='*'  # In production, specify proxy IP explicitly
)
```

For command-line usage:

```bash
uvicorn main:app --proxy-headers --forwarded-allow-ips='*'
```


### Step 8: Unix Domain Socket (Advanced)

For improved security and performance, use Unix domain sockets instead of TCP binding. Modify your Gunicorn start script:[^12][^5]

```bash
#!/bin/bash
source /path/to/venv/bin/activate
cd /path/to/project

exec gunicorn \
  -k uvicorn.workers.UvicornWorker \
  main:app \
  --bind unix:/tmp/uvicorn.sock \
  -w 4 \
  --timeout 30 \
  --graceful-timeout 20
```

Update the Nginx configuration to use the socket:[^8][^12]

```nginx
server {
    listen 80;
    server_name your_domain;
    
    location / {
        proxy_pass http://unix:/tmp/uvicorn.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```


### Step 9: Add SSL/TLS with Let's Encrypt

For production deployments, enable HTTPS using Let's Encrypt:[^13][^1]

```bash
sudo apt install python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

Configure the firewall to allow HTTPS traffic:[^13]

```bash
sudo ufw allow 'Nginx Full'
sudo ufw delete allow 'Nginx HTTP'
sudo ufw status
```


### Security Best Practices

Implement these security measures for production deployments:[^14][^15]

1. **Always use HTTPS** in production environments with valid SSL certificates
2. **Implement authentication** using OAuth2 or JWT tokens
3. **Validate all input** using Pydantic models to prevent injection attacks
4. **Restrict CORS** to trusted domains only
5. **Store secrets securely** using environment variables or secret management tools
6. **Apply security headers** in Nginx configuration
7. **Keep dependencies updated** and scan for vulnerabilities regularly
8. **Disable debug mode** and auto-reload in production

### Performance Optimization

Configure the number of Gunicorn workers based on your server's CPU cores:[^6]

```bash
workers = (2 * CPU_cores) + 1
```

For a 4-core system, use 9 workers for optimal performance. Monitor your application and adjust based on actual load patterns.

### Monitoring and Maintenance

Check service status and logs using systemd commands:[^2]

```bash
# Check service status
sudo systemctl status fastapi.service

# View logs
sudo journalctl -u fastapi.service -f

# Restart service
sudo systemctl restart fastapi.service
```

This complete setup provides a production-ready FastAPI deployment with automatic restarts, process management, and efficient request handling through Nginx.
<span style="display:none">[^16][^17][^18][^19][^20][^21][^22][^23][^24][^25][^26][^27][^28][^29][^30][^31][^32][^33][^34][^35][^36][^37][^38][^39][^40][^41][^42][^43][^44][^45][^46][^47][^48][^49][^50][^51][^52]</span>

<div align="center">⁂</div>

[^1]: https://dev.to/udara_dananjaya/setting-up-a-fastapi-project-with-nginx-reverse-proxy-on-ubuntu-883

[^2]: https://gist.github.com/ShilGen/abaeafe8b130ccd8d43edde4af8d6dce

[^3]: https://dev.to/shuv1824/deploy-fastapi-application-on-ubuntu-with-nginx-gunicorn-and-uvicorn-3mbl

[^4]: https://geekyshows.com/blog/post/deploy-fas/

[^5]: https://www.codearmo.com/python-tutorial/ultimate-guide-deploy-fastapi-app-nginx-linux

[^6]: https://fastapi.xiniushu.com/sv/deployment/server-workers/

[^7]: https://github.com/tiangolo/fastapi/issues/1741

[^8]: https://stackoverflow.com/questions/62898917/running-fastapi-app-using-uvicorn-on-ubuntu-server

[^9]: https://docs.vultr.com/how-to-deploy-a-fastapi-application-with-gunicorn-and-nginx-on-ubuntu-2404

[^10]: https://www.netdata.cloud/academy/nginx-eliminate-upstream-timeout/

[^11]: https://stackoverflow.com/questions/78732486/how-to-pass-client-ip-address-via-nginx-reverse-proxy-to-fastapi

[^12]: https://github.com/encode/uvicorn/issues/53

[^13]: https://www.codementor.io/@collinsonyemaobi/deploy-a-secure-fastapi-app-on-ubuntu-20-04-using-python3-10-certbot-nginx-and-gunicorn-1spdjl4suw

[^14]: https://xygeni.io/blog/fastapi-security-faqs-what-developers-should-know/

[^15]: https://escape.tech/blog/how-to-secure-fastapi-api/

[^16]: http://arxiv.org/pdf/2301.05522.pdf

[^17]: https://arxiv.org/pdf/1712.06139.pdf

[^18]: https://pmc.ncbi.nlm.nih.gov/articles/PMC10577930/

[^19]: http://arxiv.org/pdf/2403.19257.pdf

[^20]: https://arxiv.org/pdf/2104.12721.pdf

[^21]: https://onlinelibrary.wiley.com/doi/10.1002/spe.3383

[^22]: https://arxiv.org/pdf/1905.07314.pdf

[^23]: http://arxiv.org/pdf/2407.00110.pdf

[^24]: https://fastapi.tiangolo.com/deployment/manually/

[^25]: https://github.com/fastapi/fastapi/discussions/7357

[^26]: http://arxiv.org/pdf/0706.2748.pdf

[^27]: https://arxiv.org/pdf/1609.03750.pdf

[^28]: https://zenodo.org/record/3387092/files/main.pdf

[^29]: https://arxiv.org/pdf/2112.10106.pdf

[^30]: https://arxiv.org/pdf/1609.08524.pdf

[^31]: http://arxiv.org/pdf/2405.06085.pdf

[^32]: http://arxiv.org/pdf/2503.12878.pdf

[^33]: https://arxiv.org/html/2410.00026

[^34]: https://www.youtube.com/watch?v=Dh5lzOwyVAY

[^35]: https://ijsrem.com/download/enterprise-ai-transformation-with-google-vertex-ai-best-practices-strategies/

[^36]: https://onlinelibrary.wiley.com/doi/10.1002/spy2.450

[^37]: https://www.mdpi.com/2673-7655/5/2/17

[^38]: https://journalcjast.com/index.php/CJAST/article/view/4519

[^39]: https://academic.oup.com/pnasnexus/article/doi/10.1093/pnasnexus/pgae433/7828925

[^40]: https://ect-journals.rtu.lv/conect/article/view/CONECT.2025.077

[^41]: https://link.springer.com/10.1007/s11356-024-33975-7

[^42]: https://panor.ru/articles/luchshie-mirovye-praktiki-razvitiya-akvakultury-v-ramkakh-realizatsii-proektov-mnogotselevogo-ispolzovaniya-infrastruktury-toplivno-energeticheskogo-kompleksa/95832.html

[^43]: https://www.ajol.info/index.php/afsjg/article/view/226615

[^44]: https://isjem.com/download/best-ai-framework-guide-build-production-ready-agents-that-work/

[^45]: https://arxiv.org/pdf/2212.06606.pdf

[^46]: https://arxiv.org/pdf/2105.02031.pdf

[^47]: https://arxiv.org/pdf/2202.01612.pdf

[^48]: https://arxiv.org/pdf/2301.01261.pdf

[^49]: http://arxiv.org/pdf/2106.13123.pdf

[^50]: http://arxiv.org/pdf/2409.16526.pdf

[^51]: http://arxiv.org/pdf/2404.05598.pdf

[^52]: https://arxiv.org/abs/2009.11248

