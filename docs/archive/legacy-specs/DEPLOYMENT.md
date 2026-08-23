# Crossword Helper - Deployment Guide

**Version:** 1.0
**Last Updated:** 2025-11-18

---

## Quick Start (Development)

### Prerequisites
- Python 3.9 or higher
- pip (Python package manager)
- Git

### Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd crossword-helper
```

2. **Install backend dependencies:**
```bash
cd backend
pip install -r requirements.txt
```

3. **Install CLI dependencies:**
```bash
cd ../cli
pip install -r requirements.txt
```

4. **Run the web application:**
```bash
cd ../backend
python app.py
```

The app will be available at http://localhost:5000

5. **Use the CLI tool:**
```bash
cd ../cli
./crossword --help
```

---

## Running Tests

### Backend Tests
```bash
cd backend
pytest tests/ -v
```

### CLI Tests
```bash
cd cli
pytest tests/ -v
```

### All Tests
```bash
# From project root
pytest backend/tests/ cli/tests/ -v
```

---

## Production Deployment (Basic)

### Option 1: Local Production Server

**Using Gunicorn (recommended for production):**

1. **Install Gunicorn:**
```bash
pip install gunicorn
```

2. **Run with Gunicorn:**
```bash
cd backend
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

Parameters:
- `-w 4` - 4 worker processes (adjust based on CPU cores)
- `-b 0.0.0.0:5000` - Bind to all interfaces on port 5000
- `app:app` - Module and application name

3. **Add systemd service (Linux):**

Create `/etc/systemd/system/crossword-helper.service`:
```ini
[Unit]
Description=Crossword Helper Web App
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/crossword-helper/backend
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 app:app

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable crossword-helper
sudo systemctl start crossword-helper
```

---

### Option 2: Docker Deployment (Recommended)

**Coming in Phase 4** - Full Docker containerization with:
- Multi-stage builds
- Nginx reverse proxy
- Environment configuration
- Docker Compose orchestration

---

### Option 3: Cloud Platform Deployment

#### Heroku

1. **Create `Procfile` in project root:**
```
web: cd backend && gunicorn -w 4 app:app
```

2. **Create `runtime.txt`:**
```
python-3.11.0
```

3. **Deploy:**
```bash
heroku create your-app-name
git push heroku main
```

#### Render.com

1. Connect your GitHub repository
2. Configure build settings:
   - **Build Command:** `cd backend && pip install -r requirements.txt`
   - **Start Command:** `cd backend && gunicorn -w 4 app:app`
3. Deploy automatically on push

#### AWS/GCP/Azure

For cloud deployment, consider:
- EC2/Compute Engine/VM instances
- Load balancer (if scaling)
- Managed databases (for Phase 4 features)
- Static file hosting (S3/Cloud Storage)

---

## Configuration

### Environment Variables

Create `.env` file in `backend/` directory:

```bash
# Flask configuration
FLASK_ENV=production
SECRET_KEY=your-secret-key-here

# CLI path (auto-detected by default)
CLI_PATH=/path/to/crossword-helper/cli/crossword

# Timeouts (seconds)
CLI_TIMEOUT=300
PATTERN_TIMEOUT=10
NORMALIZE_TIMEOUT=5
NUMBER_TIMEOUT=5

# Performance
CACHE_ENABLED=true
CACHE_MAX_SIZE=128

# Wordlist paths
WORDLIST_DIR=/path/to/wordlists
```

Load in `app.py`:
```python
from dotenv import load_dotenv
load_dotenv()
```

---

## Reverse Proxy Setup (Nginx)

### Nginx Configuration

Create `/etc/nginx/sites-available/crossword-helper`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts for long-running autofill requests
        proxy_read_timeout 600s;
        proxy_connect_timeout 10s;
    }

    # Static files (optional optimization)
    location /static {
        alias /path/to/crossword-helper/frontend/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/crossword-helper /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### SSL/HTTPS (Certbot)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## Performance Tuning

### 1. Gunicorn Workers

Calculate optimal workers:
```python
workers = (2 x CPU_cores) + 1
```

Example for 4-core system:
```bash
gunicorn -w 9 app:app
```

### 2. Caching

Enable in-memory caching (already implemented):
```python
# backend/core/cli_adapter.py uses @lru_cache
from functools import lru_cache

@lru_cache(maxsize=128)
def cached_normalize(text: str):
    # ...
```

### 3. Database (Phase 4)

For future database features:
- Use connection pooling
- Enable query caching
- Add database indexes
- Use read replicas for scaling

---

## Monitoring

### Basic Logging

Configure logging in `app.py`:
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/var/log/crossword-helper/app.log'),
        logging.StreamHandler()
    ]
)
```

### Health Check Endpoint

Already implemented:
```bash
curl http://localhost:5000/api/health
```

Returns:
```json
{
  "status": "healthy",
  "architecture": "cli-backend",
  "components": {
    "cli_adapter": "ok",
    "api_server": "ok"
  }
}
```

### Monitoring Tools (Production)

Consider adding:
- **Sentry** - Error tracking
- **Prometheus** - Metrics collection
- **Grafana** - Metrics visualization
- **Uptime Robot** - Uptime monitoring

---

## Security Considerations

### Current Security Features
✅ Input validation on all endpoints
✅ Path traversal protection
✅ Timeout protection (prevents DoS)
✅ Subprocess security (no shell=True)
✅ CORS configuration

### Additional Production Security
- [ ] Rate limiting (Flask-Limiter)
- [ ] HTTPS enforcement
- [ ] Security headers (Flask-Talisman)
- [ ] API authentication (Phase 4)
- [ ] Request signing
- [ ] Web Application Firewall (WAF)

---

## Backup & Recovery

### What to Backup
- **Wordlists:** `data/wordlists/`
- **Grid templates:** (Phase 4 feature)
- **Clue database:** (Phase 4 feature)
- **Configuration:** `.env` files

### Backup Script Example
```bash
#!/bin/bash
BACKUP_DIR="/backup/crossword-helper"
DATE=$(date +%Y%m%d)

# Backup wordlists
tar -czf "$BACKUP_DIR/wordlists-$DATE.tar.gz" data/wordlists/

# Backup configuration
cp backend/.env "$BACKUP_DIR/env-$DATE.backup"

# Keep last 30 days
find "$BACKUP_DIR" -mtime +30 -delete
```

---

## Troubleshooting

### Common Issues

**1. CLI not found error:**
```
Solution: Check CLI_PATH in .env or verify cli/crossword is executable
chmod +x cli/crossword
```

**2. Import errors:**
```
Solution: Ensure all dependencies installed
pip install -r requirements.txt
```

**3. Timeout errors on autofill:**
```
Solution: Increase timeout in API call
POST /api/fill with {"timeout": 600}
```

**4. Port 5000 already in use:**
```
Solution: Change port in app.py or kill conflicting process
lsof -ti:5000 | xargs kill -9
```

**5. Tests failing:**
```
Solution: Check Python version (needs 3.9+) and dependencies
python --version
pip list
```

---

## Scaling Considerations

### Horizontal Scaling

**Load Balancer Setup:**
```nginx
upstream crossword_backend {
    server 127.0.0.1:5001;
    server 127.0.0.1:5002;
    server 127.0.0.1:5003;
}

server {
    location / {
        proxy_pass http://crossword_backend;
    }
}
```

### Vertical Scaling

- Increase worker processes
- Add more RAM for caching
- Use faster storage (SSD)
- Optimize wordlist loading

### Database Scaling (Phase 4)

- Master-slave replication
- Read replicas
- Connection pooling
- Query optimization

---

## Maintenance

### Regular Tasks
- [ ] Monitor disk space (logs, backups)
- [ ] Review error logs weekly
- [ ] Update dependencies monthly
- [ ] Test backups quarterly
- [ ] Performance audit annually

### Update Procedure
```bash
# 1. Backup current version
tar -czf backup-$(date +%Y%m%d).tar.gz crossword-helper/

# 2. Pull updates
git pull origin main

# 3. Update dependencies
pip install -r backend/requirements.txt
pip install -r cli/requirements.txt

# 4. Run tests
pytest backend/tests/ cli/tests/

# 5. Restart service
sudo systemctl restart crossword-helper
```

---

## Next Steps

This basic deployment guide covers local and simple production setups. For more advanced deployment:

**Phase 4 Will Add:**
- Docker containerization
- CI/CD pipeline (GitHub Actions)
- Database migrations
- Redis caching
- WebSocket support
- Production monitoring stack

**See:** `docs/ROADMAP.md` for Phase 4 plans

---

## Support

- **Documentation:** `docs/` directory
- **Issues:** GitHub issues (if applicable)
- **Tests:** Run `pytest` to verify installation
- **Status:** Check `/api/health` endpoint

**Current Version:** Phase 3 Complete (CLI-backend integration)
**Test Coverage:** 172/172 tests passing (100%)
