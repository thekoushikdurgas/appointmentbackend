# Ubuntu Production Deployment Guide

This guide distills the repository deployment notes into a single checklist for running the Appointment360 FastAPI backend on Ubuntu with Gunicorn, Uvicorn workers, and Nginx.

## 1. Server Preparation

- `sudo apt update && sudo apt upgrade -y`
- Install dependencies: `sudo apt install -y python3-venv python3-pip build-essential nginx git`
- (Optional) create an app user: `sudo adduser --system --group --no-create-home app`

## 2. Fetch the Application

```bash
sudo mkdir -p /opt/appointment360
sudo chown "$USER":www-data /opt/appointment360
cd /opt/appointment360
git clone <repo-url> .
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 3. Configure Environment Variables

- Copy `.env.example` to `.env` and replace placeholder values.
- Ensure secrets (`SECRET_KEY`, `CONTACTS_WRITE_KEY`) and production-only settings (`ALLOWED_ORIGINS`, `TRUSTED_HOSTS`) are set.
- Choose a Gunicorn bind target (`GUNICORN_BIND` in `.env`); the template defaults to a Unix socket at `/run/appointment360.sock`.
- Run database migrations if required (e.g. `alembic upgrade head`).

## 4. Validate Locally

```bash
source .venv/bin/activate
./scripts/run_gunicorn.sh
# or for a quick check
gunicorn --config gunicorn_conf.py app.main:app
```

Visit `http://SERVER_IP:8000/health` before placing Nginx in front.

## 5. Install the systemd Service

1. Copy the service template and edit paths/usernames as needed:

   ```bash
   sudo cp infra/systemd/fastapi.service /etc/systemd/system/appointment360.service
   sudo nano /etc/systemd/system/appointment360.service
   ```

2. Reload and start:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now appointment360.service
   sudo systemctl status appointment360.service
   ```

3. Logs: `sudo journalctl -u appointment360.service -f`

## 6. Configure Nginx

1. Copy the site definition and update `server_name`, log paths, and socket targets (Unix socket `/run/appointment360.sock` or TCP `127.0.0.1:8000` if preferred):

   ```bash
   sudo cp infra/nginx/fastapi_app.conf /etc/nginx/sites-available/appointment360
   sudo nano /etc/nginx/sites-available/appointment360
   sudo ln -s /etc/nginx/sites-available/appointment360 /etc/nginx/sites-enabled/
   ```

2. Test and reload:

   ```bash
   sudo nginx -t
   sudo systemctl reload nginx
   ```

3. (Optional) enable HTTPS:

   ```bash
   sudo apt install -y python3-certbot-nginx
   sudo certbot --nginx -d appointment360.example.com
   sudo systemctl reload nginx
   ```

## 7. Operational Tips

- Reload the API after deploying code: `sudo systemctl restart appointment360.service`
- Tail Gunicorn logs (if writing to file): `sudo journalctl -u appointment360.service -n 200`
- Monitor socket path permissions when running under a dedicated user.
- Update dependencies regularly (`pip install -r requirements.txt --upgrade`) and rerun migrations.
- Keep firewall ports 80/443 open and restrict SSH to trusted addresses.

This workflow complements the scripts (`scripts/run_gunicorn.sh`, `scripts/run_worker.sh`) and configuration defaults shipped in the repository, enabling a consistent production rollout across environments.
