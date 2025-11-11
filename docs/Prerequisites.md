<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

## Prerequisites

Before deploying your FastAPI application, ensure your Ubuntu server has the following installed:[^1][^2]

- Python 3.7 or above
- Pip (Python package manager)
- NGINX web server
- Git (for pulling your application code)
- Virtual environment tool (venv, virtualenv, or conda)


## System Setup

Update your Ubuntu system and install necessary packages:[^2]

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-dev build-essential nginx
```


## Application Setup

### Create Project Directory

Set up your project directory and virtual environment:[^1][^2]

```bash
mkdir /var/www/myapp
cd /var/www/myapp
python3 -m venv venv
source venv/bin/activate
```


### Deploy Application Code

Clone your FastAPI application repository:[^1]

```bash
git init
git remote add origin <your-repo-url>
git pull origin <your-branch-name>
```


### Install Dependencies

Install FastAPI, Uvicorn, and Gunicorn:[^3][^2][^1]

```bash
pip install -r requirements.txt
pip install fastapi uvicorn gunicorn
```


## Gunicorn Configuration

### Test Gunicorn Manually

Before creating a system service, test that Gunicorn works with Uvicorn workers:[^4][^3][^1]

```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000
```

Replace `main:app` with your actual application module and instance name.[^1]

### Optional: Create Gunicorn Configuration File

For more control, create a `gunicorn_conf.py` file:[^5]

```python
bind = "0.0.0.0:8000"
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
```

Then run with:

```bash
gunicorn -c gunicorn_conf.py main:app
```


## Create Systemd Service

Create a systemd service file for automatic startup and management:[^1]

```bash
sudo nano /etc/systemd/system/myapp.service
```

Add the following configuration:[^1]

```ini
[Unit]
Description=Gunicorn instance to serve MyApp
After=network.target

[Service]
User=<username>
Group=www-data
WorkingDirectory=/var/www/myapp/src
Environment="PATH=/var/www/myapp/venv/bin"
ExecStart=/var/www/myapp/venv/bin/gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app

[Install]
WantedBy=multi-user.target
```

Enable and start the service:[^1]

```bash
sudo systemctl start myapp
sudo systemctl enable myapp
sudo systemctl status myapp
```


## NGINX Configuration

### Create NGINX Server Block

Create a new NGINX configuration file:[^2]

```bash
sudo nano /etc/nginx/sites-available/myapp
```

Add the reverse proxy configuration:[^2]

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


### Enable the Configuration

Create a symbolic link to enable the site:[^2]

```bash
sudo ln -s /etc/nginx/sites-available/myapp /etc/nginx/sites-enabled/
```

Test and reload NGINX:[^2]

```bash
sudo nginx -t
sudo systemctl reload nginx
```


## Understanding the Architecture

This deployment uses Gunicorn as a process manager running multiple Uvicorn worker processes. Gunicorn handles process management, worker lifecycle, and load balancing, while Uvicorn workers handle the ASGI protocol that FastAPI requires. NGINX acts as a reverse proxy, forwarding client requests to Gunicorn and handling static files efficiently.[^6][^3][^2]

The typical worker count is **4 workers** (or 2-4 times the number of CPU cores), which provides good performance for most applications.[^5][^4][^1]

## Verification

Test your deployment by accessing your server's IP address or domain in a browser. You should see your FastAPI application running. Check the service logs if you encounter issues:[^2]

```bash
sudo journalctl -u myapp -f
```

<span style="display:none">[^10][^11][^12][^13][^14][^15][^16][^17][^18][^7][^8][^9]</span>

<div align="center">⁂</div>

[^1]: https://dev.to/shuv1824/deploy-fastapi-application-on-ubuntu-with-nginx-gunicorn-and-uvicorn-3mbl

[^2]: https://dev.to/udara_dananjaya/setting-up-a-fastapi-project-with-nginx-reverse-proxy-on-ubuntu-883

[^3]: https://docs.vultr.com/how-to-deploy-a-fastapi-application-with-gunicorn-and-nginx-on-ubuntu-2404

[^4]: https://geekyshows.com/blog/post/deploy-fas/

[^5]: https://gist.github.com/ShilGen/abaeafe8b130ccd8d43edde4af8d6dce

[^6]: https://render.com/articles/fastapi-deployment-options

[^7]: http://arxiv.org/pdf/2301.05522.pdf

[^8]: https://arxiv.org/pdf/1905.07314.pdf

[^9]: https://arxiv.org/pdf/2104.12721.pdf

[^10]: https://pmc.ncbi.nlm.nih.gov/articles/PMC10577930/

[^11]: https://arxiv.org/pdf/2212.08146.pdf

[^12]: https://arxiv.org/pdf/2309.14821.pdf

[^13]: https://arxiv.org/pdf/1711.01758.pdf

[^14]: https://arxiv.org/pdf/2311.06962.pdf

[^15]: https://dylancastillo.co/fastapi-nginx-gunicorn/

[^16]: https://fastapi.tiangolo.com/deployment/manually/

[^17]: https://leapcell.io/blog/deploying-python-web-apps-for-production-with-gunicorn-uvicorn-and-nginx

[^18]: https://www.digitalocean.com/community/tutorials/how-to-configure-nginx-as-a-reverse-proxy-on-ubuntu-22-04

