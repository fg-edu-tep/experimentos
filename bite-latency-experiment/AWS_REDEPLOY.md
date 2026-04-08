# AWS Redeployment Instructions

## Changes Made

### 1. Kong Configuration
- **Changed from**: Database mode (with PostgreSQL)
- **Changed to**: Declarative/DB-less mode (using kong.yml)
- **Benefits**: Simpler, faster, no separate Kong database needed

### 2. PostgreSQL Configuration
- **Removed**: Local PostgreSQL container
- **Using**: External AWS PostgreSQL at `ec2-54-83-92-122.compute-1.amazonaws.com:5434`

### 3. ALLOWED_HOSTS
- Added AWS hostname: `ec2-13-222-13-14.compute-1.amazonaws.com`
- Added AWS IP: `13.222.13.14`

## Deployment Steps

### On Your AWS Instance (ec2-13-222-13-14.compute-1.amazonaws.com)

SSH into your server:
```bash
ssh ubuntu@ec2-13-222-13-14.compute-1.amazonaws.com
```

Then run these commands:

```bash
# 1. Navigate to project directory
cd ~/experimentos/bite-latency-experiment

# 2. Stop existing containers
docker compose down

# 3. Remove old Kong database volume (not needed anymore)
docker volume rm bite-latency-experiment_kong_data || true

# 4. Pull latest changes from your repository
git pull origin main
# OR if you haven't pushed yet, manually update these files:
#   - docker-compose.yml
#   - .env (update ALLOWED_HOSTS)

# 5. Update .env file with correct settings
nano .env
# Make sure these are set:
# ALLOWED_HOSTS=127.0.0.1,localhost,ec2-13-222-13-14.compute-1.amazonaws.com,13.222.13.14
# DB_HOST=ec2-54-83-92-122.compute-1.amazonaws.com
# DB_PORT=5434
# DB_NAME=bite_latency
# DB_USER=bite_user
# DB_PASSWORD=bite_pass

# 6. Rebuild and start containers
docker compose up -d --build

# 7. Wait for services to start
sleep 15

# 8. Check status
docker compose ps

# 9. Verify Kong loaded declarative config
curl http://localhost:8001/routes
# Should show routes, NOT {"next":null,"data":[]}

# 10. Test health endpoint
curl http://localhost:8000/api/health
# Should return: {"status": "healthy"}

# 11. Test authenticated endpoint
curl -H "apikey: test-api-key-12345" \
  "http://localhost:8000/api/report/?projectId=proj-001&month=2026-01"
```

## Quick Copy-Paste Script

```bash
cd ~/experimentos/bite-latency-experiment && \
docker compose down && \
docker volume rm bite-latency-experiment_kong_data || true && \
docker compose up -d --build && \
sleep 15 && \
echo "=== Container Status ===" && \
docker compose ps && \
echo "" && \
echo "=== Kong Routes ===" && \
curl -s http://localhost:8001/routes | head -20 && \
echo "" && \
echo "=== Health Check ===" && \
curl -s http://localhost:8000/api/health
```

## Verification

After deployment, test from your local machine:

```bash
# Test health endpoint
curl http://ec2-13-222-13-14.compute-1.amazonaws.com:8000/api/health

# Test with API key
curl -H "apikey: test-api-key-12345" \
  "http://ec2-13-222-13-14.compute-1.amazonaws.com:8000/api/report/?projectId=proj-001&month=2026-01"

# Check Kong admin
curl http://ec2-13-222-13-14.compute-1.amazonaws.com:8001/services
```

## Troubleshooting

### Kong shows no routes
```bash
# Check if kong.yml is mounted
docker compose exec kong ls -la /usr/local/kong/declarative/

# Check Kong logs
docker compose logs kong

# Restart Kong
docker compose restart kong
```

### Django connection refused
```bash
# Check Django logs
docker compose logs django-app

# Verify PostgreSQL connection
docker compose exec django-app python -c "
from django.db import connection
print('DB Host:', connection.settings_dict['HOST'])
print('DB Port:', connection.settings_dict['PORT'])
with connection.cursor() as cursor:
    cursor.execute('SELECT version();')
    print('Connected:', cursor.fetchone()[0][:50])
"
```

### Can't connect from external
```bash
# Check firewall
sudo ufw status

# Check if ports are listening
sudo netstat -tuln | grep -E '8000|8001|8080'
```

## Pre-configured API Keys

| Consumer | API Key | Purpose |
|----------|---------|---------|
| test-client | `test-api-key-12345` | Testing |
| jmeter-client | `jmeter-load-test-key-67890` | Load testing |
| production-client | `prod-secure-key-CHANGE-THIS-IN-PRODUCTION` | Production |
| monitoring-client | `monitor-health-check-key-11111` | Monitoring |

## Architecture After Redeployment

```
┌─────────────────┐
│     Client      │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│  Kong Gateway (Declarative) │  Port 8000
│  - No Database Required     │
│  - Routes from kong.yml     │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│    Django App (Gunicorn)    │  Port 8080
└────┬────────────────┬───────┘
     │                │
     ▼                ▼
┌─────────┐    ┌──────────┐
│ Redis   │    │ External │
│ (local) │    │ PostgreSQL│
└─────────┘    └──────────┘
              ec2-54-83...
```

## Next Steps

1. Test all API endpoints
2. Update DNS to point to your AWS instance (optional)
3. Set up SSL/HTTPS (optional, see VPS_DEPLOYMENT_GUIDE.md)
4. Configure automated backups for external PostgreSQL
5. Set up monitoring and alerts
