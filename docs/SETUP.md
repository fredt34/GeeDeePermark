# GeeDeePerMark Setup Guide

Complete installation and deployment instructions for self-hosting GeeDeePerMark.

## Prerequisites

- Linux server (Debian/Ubuntu recommended)
- Python 3.10+
- Systemd (for service management)
- Reverse proxy: Caddy (recommended) or Nginx

## Quick Installation

### 1. Install Python Virtual Environment

```bash
sudo apt install python3.10-venv
python3 -m venv venv
```

### 2. Install Dependencies

```bash
# If running as service user (e.g., caddy)
sudo chown -R caddy:caddy venv
sudo -u caddy ./venv/bin/pip install fastapi uvicorn pillow pymupdf httpx python-multipart

# Or as current user
./venv/bin/pip install fastapi uvicorn pillow pymupdf httpx python-multipart
```

### 3. Configure Systemd Service

Copy the service file to systemd:

```bash
sudo cp setup/geedeepermark.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable geedeepermark.service
sudo systemctl start geedeepermark.service
```

Check status:

```bash
sudo systemctl status geedeepermark.service
```

### 4. Configure Reverse Proxy

## Caddy Configuration (Recommended)

Caddy automatically handles HTTPS certificates via Let's Encrypt.

Add to your Caddyfile:

```caddyfile
geedeepermark.yourdomain.org {
    # Logging (optional)
    log {
        output file /var/log/caddy/geedeepermark.log
    }
    
    # Serve static files from /var/www/GeeDeePermark2/docs
    root * /var/www/GeeDeePermark2/docs
    
    # API endpoints go to Python backend
    @api {
        path /watermark*
        path /download_from_grist*
        path /upload_to_grist*
    }
    handle @api {
        reverse_proxy 127.0.0.1:8000
    }
    
    # Everything else served as static files
    handle {
        file_server
    }
    
    # Enable compression
    encode gzip
}
```

Reload Caddy:

```bash
sudo systemctl reload caddy
```

## Nginx Configuration (Alternative)

**Note:** This configuration is provided as an example without guarantee. Caddy is the recommended solution.

Create `/etc/nginx/sites-available/geedeepermark`:

```nginx
server {
    listen 80;
    server_name geedeepermark.yourdomain.org;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name geedeepermark.yourdomain.org;

    # SSL certificates (use certbot)
    ssl_certificate /etc/letsencrypt/live/geedeepermark.yourdomain.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/geedeepermark.yourdomain.org/privkey.pem;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;

    # Large file upload support
    client_max_body_size 50M;

    # API endpoints proxy to Python backend
    location ~ ^/(watermark|download_from_grist|upload_to_grist) {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts for large file processing
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # Static files
    location / {
        root /var/www/GeeDeePermark2/docs;
        try_files $uri $uri/ =404;
    }

    access_log /var/log/nginx/geedeepermark.log;
    error_log /var/log/nginx/geedeepermark-error.log;
}
```

Enable and reload:

```bash
sudo ln -s /etc/nginx/sites-available/geedeepermark /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Systemd Service Configuration

Example service file (`setup/geedeepermark.service`):

```ini
[Unit]
Description=GeeDeePerMark Watermarking Service
After=network.target

[Service]
Type=simple
User=caddy
Group=caddy
WorkingDirectory=/var/www/GeeDeePermark2
Environment="PATH=/var/www/GeeDeePermark2/venv/bin"
ExecStart=/var/www/GeeDeePermark2/venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Key Configuration Points:

- **User/Group:** Run as unprivileged user (e.g., `caddy`, `www-data`, or dedicated user)
- **WorkingDirectory:** Path to your GeeDeePermark2 installation
- **Port:** Internal port (8000) - only accessible via reverse proxy
- **Restart:** Automatic restart on failure

## Security Hardening

### 1. File Permissions

```bash
# Set ownership to service user
sudo chown -R caddy:caddy /var/www/GeeDeePermark2

# Restrict permissions
sudo chmod 750 /var/www/GeeDeePermark2
sudo chmod 640 /var/www/GeeDeePermark2/app.py
```

### 2. Firewall Configuration

```bash
# Only allow HTTPS and SSH
sudo ufw allow 22/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Block direct access to uvicorn port
sudo ufw deny 8000/tcp
```

### 3. Systemd Security Options

Add to `[Service]` section in systemd unit:

```ini
# Restrict access to filesystem
PrivateTmp=true
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/tmp

# Restrict network
RestrictAddressFamilies=AF_INET AF_INET6

# Restrict capabilities
CapabilityBoundingSet=
```

## Monitoring & Logs

### Check Service Status

```bash
sudo systemctl status geedeepermark.service
```

### View Application Logs

```bash
sudo journalctl -u geedeepermark.service -f
```

### View Access Logs

**Caddy:**
```bash
tail -f /var/log/caddy/geedeepermark.log
```

**Nginx:**
```bash
tail -f /var/log/nginx/geedeepermark.log
```

## Updating

### Update Code

```bash
cd /var/www/GeeDeePermark2
git pull origin main
```

### Update Dependencies

```bash
sudo -u caddy ./venv/bin/pip install --upgrade fastapi uvicorn pillow pymupdf httpx python-multipart
```

### Restart Service

```bash
sudo systemctl restart geedeepermark.service
```

## Troubleshooting

### Service Won't Start

Check logs:
```bash
sudo journalctl -u geedeepermark.service -n 50
```

Common issues:
- Python virtual environment not activated
- Missing dependencies
- Port already in use
- Permission issues

### 502 Bad Gateway

- Verify uvicorn is running: `sudo systemctl status geedeepermark.service`
- Check reverse proxy configuration
- Verify firewall allows internal connections to port 8000

### Upload Fails / File Too Large

Increase limits in reverse proxy:

**Caddy:** (usually no limit)

**Nginx:** Increase `client_max_body_size` in server block

### Memory Issues

Monitor with:
```bash
sudo systemctl status geedeepermark.service
```

Consider limiting workers in uvicorn:
```bash
ExecStart=/var/www/GeeDeePermark2/venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000 --workers 2
```

## Advanced Configuration

### Using Gunicorn (Production)

For production deployments, use Gunicorn with uvicorn workers:

```bash
./venv/bin/pip install gunicorn
```

Update systemd service:
```ini
ExecStart=/var/www/GeeDeePermark2/venv/bin/gunicorn app:app -w 4 -k uvicorn.workers.UvicornWorker --bind 127.0.0.1:8000
```

### Custom Domain

Update your DNS records to point to your server, then update Caddyfile or Nginx config with your domain name. Caddy will automatically obtain SSL certificates.

## Dependencies

- **fastapi** — Web framework
- **uvicorn** — ASGI server
- **pillow** — Image processing
- **pymupdf** — PDF handling
- **httpx** — HTTP client for Grist integration
- **python-multipart** — Form data parsing

## Support

- [API Documentation](API.md)
- [Grist Plugin Guide](../grist-plugin/README.md)
- [GitHub Issues](https://github.com/fredt34/GeeDeePermark/issues)

---

**Author:** FredT34, seasoned DPO
