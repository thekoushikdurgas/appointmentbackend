<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

## Complete Guide to Deploy FastAPI with Gunicorn and Uvicorn Workers on Ubuntu with NGINX

This comprehensive guide covers the deployment process for FastAPI applications using Gunicorn as the process manager with Uvicorn workers, systemd for service management, and NGINX as a reverse proxy on Ubuntu. The example environment targets a production host reachable at the public IP `54.221.83.239`.

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

Create your project directory and set up a virtual environment:[^3][^4][^1]

```bash
# Create project directory
sudo mkdir -p /var/www/myapp
cd /var/www/myapp

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
git remote add origin <your-repo-url>
git pull origin <your-branch-name>
```


### Step 4: Install Python Dependencies

Install FastAPI, Gunicorn, and Uvicorn along with your application dependencies:[^4][^5][^3]

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
- `app.main:app`: Your FastAPI application module and instance
- `--bind 0.0.0.0:8000`: Bind address and port[^7]

If successful, you should see Gunicorn starting with Uvicorn workers. Press `Ctrl+C` to stop the test server.

### Step 6: Create Systemd Service File

Create a systemd service to manage your FastAPI application:[^8][^3][^1]

```bash
sudo nano /etc/systemd/system/myapp.service
```

Add the following configuration:[^3][^4][^1]

```ini
[Unit]
Description=Gunicorn instance to serve FastAPI application
After=network.target

[Service]
User=<username>
Group=www-data
WorkingDirectory=/var/www/myapp/src
Environment="PATH=/var/www/myapp/venv/bin"
ExecStart=/var/www/myapp/venv/bin/gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app --bind 127.0.0.1:8000
Restart=always
RestartSec=10
StandardOutput=append:/var/www/myapp/logs/access.log
StandardError=append:/var/www/myapp/logs/error.log

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
sudo mkdir -p /var/www/myapp/logs
```


### Step 7: Enable and Start the Service

Reload systemd, enable auto-start, and start your service:[^9][^1][^8]

```bash
# Reload systemd daemon to recognize new service
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable myapp

# Start the service
sudo systemctl start myapp

# Check service status
sudo systemctl status myapp
```

Your FastAPI application should now be running as a background service.

### Step 8: Configure NGINX as Reverse Proxy

Create an NGINX configuration file for your application:[^5][^2][^1]

```bash
sudo nano /etc/nginx/sites-available/myapp
```

Add the following configuration:[^10][^2][^1]

```nginx
server {
    listen 80;
    server_name 54.221.83.239;

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
sudo ln -s /etc/nginx/sites-available/myapp /etc/nginx/sites-enabled/

# Test NGINX configuration for syntax errors
sudo nginx -t

# Restart NGINX to apply changes
sudo systemctl restart nginx
```


### Step 10: Verify Deployment

Your FastAPI application should now be accessible through NGINX. Test by visiting:

```
http://54.221.83.239
```

Check the automatic API documentation:

```
http://54.221.83.239/docs
```


### Optional Enhancements

#### Environment Variables Management

For production environments, use `.env` files to manage configuration:[^12][^13]

1. Install python-dotenv:
```bash
pip install python-dotenv
```

2. Create a `.env` file in your project root:
```
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
sudo systemctl reload myapp
# or
sudo kill -HUP $(pgrep -f gunicorn)
```


### Troubleshooting

**Check service logs:**

```bash
sudo journalctl -u myapp -f
```

**View application logs:**

```bash
tail -f /var/www/myapp/logs/access.log
tail -f /var/www/myapp/logs/error.log
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
- **Connection refused**: Check that Gunicorn is binding to `127.0.0.1:8000`[^5][^1]


### Production Considerations

1. **Worker count**: Set workers to 2-4 times the number of CPU cores for optimal performance[^6][^2]
2. **Security**: Always use HTTPS in production (consider Let's Encrypt for free SSL certificates)[^15][^5]
3. **Monitoring**: Implement logging and monitoring solutions
4. **Firewall**: Configure UFW or iptables to allow only necessary ports
5. **Regular updates**: Keep system packages, Python dependencies, and NGINX updated

This setup provides a robust, production-ready deployment of your FastAPI application with Gunicorn managing multiple Uvicorn workers, systemd ensuring service reliability, and NGINX efficiently handling client requests as a reverse proxy.[^2][^5][^1]
<span style="display:none">[^16][^17][^18][^19][^20][^21][^22][^23][^24][^25][^26][^27][^28][^29][^30][^31][^32][^33][^34][^35][^36][^37][^38][^39][^40][^41][^42][^43][^44][^45][^46][^47][^48][^49][^50][^51][^52][^53][^54][^55][^56][^57][^58][^59]</span>

<div align="center">⁂</div>

[^1]: https://dev.to/shuv1824/deploy-fastapi-application-on-ubuntu-with-nginx-gunicorn-and-uvicorn-3mbl

[^2]: https://dev.to/udara_dananjaya/setting-up-a-fastapi-project-with-nginx-reverse-proxy-on-ubuntu-883

[^3]: https://gist.github.com/ShilGen/abaeafe8b130ccd8d43edde4af8d6dce

[^4]: https://geekyshows.com/blog/post/deploy-fas/

[^5]: https://docs.vultr.com/how-to-deploy-a-fastapi-application-with-gunicorn-and-nginx-on-ubuntu-2404

[^6]: https://fastapi.xiniushu.com/sv/deployment/server-workers/

[^7]: https://docs.gunicorn.org/en/stable/settings.html

[^8]: https://rolisz.ro/2023/setting-up-systemd/

[^9]: https://stribny.name/posts/fastapi-production/

[^10]: https://github.com/fastapi/fastapi/discussions/12123

[^11]: https://ubiq.co/tech-blog/increase-request-timeout-nginx/

[^12]: https://dev.to/yanagisawahidetoshi/efficiently-using-environment-variables-in-fastapi-4lal

[^13]: https://tecadmin.net/using-env-file-in-fastapi/

[^14]: https://www.reddit.com/r/FastAPI/comments/1enitwy/fastapi_gunicorn_hup_signal_to_reload_workers/

[^15]: https://dylancastillo.co/fastapi-nginx-gunicorn/

[^16]: https://arxiv.org/pdf/2310.08247.pdf

[^17]: https://arxiv.org/pdf/1905.07314.pdf

[^18]: http://arxiv.org/pdf/2301.05522.pdf

[^19]: https://arxiv.org/pdf/2212.08146.pdf

[^20]: https://arxiv.org/pdf/2104.12721.pdf

[^21]: https://dl.acm.org/doi/pdf/10.1145/3613424.3614280

[^22]: https://arxiv.org/pdf/2403.00515.pdf

[^23]: https://arxiv.org/pdf/1711.01758.pdf

[^24]: https://fastapi.tiangolo.com/deployment/manually/

[^25]: https://www.youtube.com/watch?v=Dh5lzOwyVAY

[^26]: https://fastapi.tiangolo.com/deployment/server-workers/

[^27]: https://arxiv.org/abs/2409.11413

[^28]: http://www.ssc.smr.ru/media/journals/izvestia/2023/2023_6_112_124.pdf

[^29]: https://academic.oup.com/healthaffairsscholar/article/doi/10.1093/haschl/qxae099/7735458

[^30]: https://www.semanticscholar.org/paper/5459ee5d2ee486b05e3d57620b9d25de938232c3

[^31]: https://ijsspp.yayasanwayanmarwanpulungan.com/index.php/IJSSPP/article/view/73

[^32]: https://www.microbiologyresearch.org/content/journal/mgen/10.1099/mgen.0.000166

[^33]: https://www.spiedigitallibrary.org/conference-proceedings-of-spie/12978/3019611/Research-on-shipping-statistics-method-based-on-AIS-big-data/10.1117/12.3019611.full

[^34]: http://lj.uwpress.org/lookup/doi/10.3368/lj.43.2.35

[^35]: https://ejournal.uniska-kediri.ac.id/index.php/akuntansi/article/view/5228

[^36]: https://onepetro.org/OTCBRASIL/proceedings/25OTCB/25OTCB/D022S054R009/792287

[^37]: https://arxiv.org/pdf/2305.05920.pdf

[^38]: https://zenodo.org/record/7994295/files/2023131243.pdf

[^39]: http://arxiv.org/pdf/2103.11439.pdf

[^40]: https://arxiv.org/pdf/2502.09766.pdf

[^41]: https://arxiv.org/pdf/2410.23873.pdf

[^42]: https://arxiv.org/pdf/2002.04688.pdf

[^43]: https://zenodo.org/record/3387092/files/main.pdf

[^44]: https://arxiv.org/pdf/2502.15524.pdf

[^45]: https://ieeexplore.ieee.org/document/9442035/

[^46]: https://ejournal2.uika-bogor.ac.id/index.php/PROMOTOR/article/view/465

[^47]: https://peerj.com/articles/20061

[^48]: https://ieeexplore.ieee.org/document/11028389/

[^49]: https://www.semanticscholar.org/paper/b4ea067a325b87749d8e2699c903344e140ce23f

[^50]: https://scholarsjournal.net/index.php/ijier/article/view/3751

[^51]: https://www.nature.com/articles/s41597-020-0453-3

[^52]: https://www.semanticscholar.org/paper/1f679d1b67eb7f059f0bbcd804406f949d2a0266

[^53]: https://www.ingentaconnect.com/content/10.3114/sim.2025.111.01_SUPP

[^54]: https://www.beilstein-journals.org/bjnano/articles/6/183

[^55]: https://arxiv.org/pdf/2502.13681.pdf

[^56]: https://arxiv.org/pdf/2503.14443.pdf

[^57]: https://pmc.ncbi.nlm.nih.gov/articles/PMC10577930/

[^58]: http://arxiv.org/pdf/2412.18109.pdf

[^59]: https://arxiv.org/pdf/2109.01002.pdf

