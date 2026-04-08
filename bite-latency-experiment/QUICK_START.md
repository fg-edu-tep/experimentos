# Quick Start Guide

## 5-Minute Deployment on AWS VPS Ubuntu 24

This guide will get your application running with Kong API Gateway in 5 minutes.

### Prerequisites
- AWS VPS running Ubuntu 24.04
- SSH access to the VPS
- Git installed

---

## Step 1: Clone Repository (30 seconds)

```bash
ssh ubuntu@your-vps-ip
git clone <repository_url>
cd bite-latency-experiment
```

---

## Step 2: Configure Environment (1 minute)

```bash
# Copy environment template
cp .env.example .env

# Generate secret key
python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# Edit .env file - update these minimum values:
nano .env
```

**Minimum required changes in `.env`:**
```bash
SECRET_KEY=<paste-generated-secret-key>
DEBUG=False
ALLOWED_HOSTS=your-vps-ip,localhost,127.0.0.1

DB_PASSWORD=your-secure-db-password
KONG_PG_PASSWORD=your-secure-kong-password
```

Save and exit (Ctrl+X, Y, Enter)

---

## Step 3: Update Production API Key (30 seconds)

```bash
# Generate secure API key
openssl rand -hex 32

# Edit Kong config
nano kong/kong.yml
```

Find this section and update the key:
```yaml
- username: production-client
  keyauth_credentials:
    - key: YOUR-NEW-SECURE-KEY-HERE  # <-- Change this!
```

Save and exit (Ctrl+X, Y, Enter)

---

## Step 4: Deploy! (3 minutes)

```bash
# Make script executable
chmod +x deploy.sh

# Run deployment
./deploy.sh
```

The script will:
- Install Docker (if needed)
- Build all containers
- Start all services
- Run database migrations
- Display access information

---

## Step 5: Test Deployment (30 seconds)

```bash
# Test health endpoint (no auth required)
curl http://localhost:8000/api/health/

# Test with authentication
curl -H "apikey: test-api-key-12345" \
  "http://localhost:8000/api/report/?projectId=proj-001&month=2026-01"
```

**Expected responses:**
- Health check: `{"status": "ok", "service": "bite-latency-experiment"}`
- Authenticated request: Should return report data or empty result

---

## Step 6: Configure Firewall (1 minute)

```bash
# Enable firewall
sudo ufw --force enable

# Allow SSH (IMPORTANT!)
sudo ufw allow ssh

# Allow Kong API Gateway
sudo ufw allow 8000/tcp

# Restrict Admin API to your IP only
sudo ufw allow from YOUR_LOCAL_IP to any port 8001

# Check status
sudo ufw status
```

---

## Done! 🎉

Your application is now running with Kong API Gateway!

### Access Points:

**Public API (through Kong):**
- `http://your-vps-ip:8000/api/health/` - Health check
- `http://your-vps-ip:8000/api/report/` - Get reports (requires API key)

**API Keys for Testing:**
- Development: `test-api-key-12345`
- JMeter: `jmeter-load-test-key-67890`
- Production: `<your-generated-key>` (from Step 3)

### Example Request from Your Local Machine:

```bash
# Replace YOUR_VPS_IP and YOUR_API_KEY
curl -H "apikey: test-api-key-12345" \
  "http://YOUR_VPS_IP:8000/api/report/?projectId=proj-001&month=2026-01"
```

---

## Common Commands

### View Service Status
```bash
docker compose ps
```

### View Logs
```bash
docker compose logs -f
```

### Restart All Services
```bash
docker compose restart
```

### Stop All Services
```bash
docker compose down
```

### Start All Services
```bash
docker compose up -d
```

---

## Next Steps

### 1. Seed Test Data (Optional)
```bash
docker compose exec django-app python manage.py seed_reports --projects 100 --months 12
```

### 2. Create Django Admin User
```bash
docker compose exec django-app python manage.py createsuperuser
```

### 3. Set Up SSL/HTTPS
See [VPS_DEPLOYMENT_GUIDE.md](VPS_DEPLOYMENT_GUIDE.md#sslhttps-configuration-recommended-for-production)

### 4. Configure Automated Backups
See [VPS_DEPLOYMENT_GUIDE.md](VPS_DEPLOYMENT_GUIDE.md#database-backups)

### 5. Set Up Monitoring
See [VPS_DEPLOYMENT_GUIDE.md](VPS_DEPLOYMENT_GUIDE.md#set-up-monitoring)

---

## Troubleshooting

### Services won't start?
```bash
docker compose logs
```

### Can't connect from external network?
```bash
# Check firewall
sudo ufw status

# Check if port is listening
sudo netstat -tlnp | grep 8000
```

### Kong returns 502?
```bash
# Check Django is running
docker compose ps django-app

# Test Django directly
curl http://localhost:8080/api/health/
```

### API key not working?
```bash
# List all consumers
./kong/manage_kong.sh consumers

# List keys for specific consumer
./kong/manage_kong.sh list-keys test-client
```

---

## Documentation

- **[DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md)** - Complete overview of the deployment
- **[VPS_DEPLOYMENT_GUIDE.md](VPS_DEPLOYMENT_GUIDE.md)** - Detailed deployment guide
- **[kong/KONG_GUIDE.md](kong/KONG_GUIDE.md)** - Kong API Gateway reference
- **[README.md](README.md)** - Application documentation

---

## Architecture at a Glance

```
Internet
   ↓
Firewall (UFW)
   ↓
Kong Gateway (Port 8000)
   ├─ Key Authentication
   ├─ Rate Limiting
   └─ CORS Support
   ↓
Django App (Gunicorn)
   ├─ PostgreSQL Database
   └─ Redis Cache
```

---

## Security Checklist

After deployment, ensure:

- [x] Deployed application
- [ ] Changed production API key in `kong/kong.yml`
- [ ] Updated `SECRET_KEY` in `.env`
- [ ] Set `DEBUG=False`
- [ ] Configured firewall
- [ ] Changed all default passwords
- [ ] Set up SSL/HTTPS (for production)
- [ ] Configured backups

---

## Getting Help

1. Check logs: `docker compose logs -f`
2. Review [DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md)
3. Check Kong status: `./kong/manage_kong.sh status`
4. Review [VPS_DEPLOYMENT_GUIDE.md](VPS_DEPLOYMENT_GUIDE.md) troubleshooting section

---

**Need more detailed instructions?** See [VPS_DEPLOYMENT_GUIDE.md](VPS_DEPLOYMENT_GUIDE.md)

**Questions about Kong?** See [kong/KONG_GUIDE.md](kong/KONG_GUIDE.md)
