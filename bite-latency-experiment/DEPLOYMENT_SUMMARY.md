# Deployment Summary - Kong API Gateway Integration

## Overview

This repository has been configured for deployment on AWS VPS (Ubuntu 24) with Kong API Gateway providing key-auth authentication. All components run in Docker containers for easy deployment and management.

## Files Created/Modified

### Docker Configuration
- **[docker-compose.yml](docker-compose.yml)** - Complete Docker Compose configuration with 6 services:
  - `postgres` - PostgreSQL database for Django
  - `redis` - Redis cache
  - `kong-database` - PostgreSQL database for Kong
  - `kong-migration` - Kong database initialization
  - `kong` - Kong API Gateway
  - `django-app` - Django application with Gunicorn

- **[Dockerfile](Dockerfile)** - Production-ready Dockerfile for Django application
  - Based on Python 3.12 slim
  - Runs as non-root user
  - Includes health checks
  - Optimized for production

- **[.dockerignore](.dockerignore)** - Excludes unnecessary files from Docker build
- **[.gitignore](.gitignore)** - Updated to exclude sensitive and generated files

### Kong Configuration
- **[kong/kong.yml](kong/kong.yml)** - Declarative Kong configuration:
  - Service: `bite-latency-api` pointing to Django app
  - 4 Routes: health-check, get-report, clear-cache, django-admin
  - 4 Pre-configured consumers with API keys
  - Plugins: key-auth, rate-limiting, cors, file-log
  - Health check configuration
  - Upstream load balancing setup

- **[kong/manage_kong.sh](kong/manage_kong.sh)** - Kong management utility script:
  - Check status
  - List services, routes, consumers, plugins
  - Create/manage API keys
  - Test API endpoints
  - View logs
  - Reload configuration

- **[kong/KONG_GUIDE.md](kong/KONG_GUIDE.md)** - Comprehensive Kong reference guide:
  - Quick commands
  - API key management
  - Route configuration
  - Plugin configuration
  - Security best practices
  - Troubleshooting

### Deployment Scripts
- **[deploy.sh](deploy.sh)** - Automated deployment script:
  - Installs Docker if needed
  - Configures environment
  - Builds and starts all services
  - Runs migrations
  - Seeds data (optional)
  - Warms cache (optional)
  - Displays deployment summary

### Configuration Templates
- **[.env.example](.env.example)** - Environment variable template:
  - Django settings
  - Database credentials
  - Redis configuration
  - Kong configuration
  - Optional seeding/warming settings
  - Production deployment notes

### Documentation
- **[README.md](README.md)** - Updated with:
  - Quick deployment instructions
  - Kong API Gateway section
  - Architecture overview
  - Environment configuration
  - API endpoints with authentication examples
  - Service management commands
  - Monitoring and troubleshooting
  - Production checklist
  - SSL/HTTPS configuration

- **[VPS_DEPLOYMENT_GUIDE.md](VPS_DEPLOYMENT_GUIDE.md)** - Complete deployment guide:
  - Step-by-step VPS setup
  - Firewall configuration
  - SSL/HTTPS setup
  - Automated backups
  - Monitoring setup
  - Troubleshooting
  - Security checklist

## Quick Deployment

### On AWS VPS Ubuntu 24:

```bash
# 1. Clone repository
git clone <repository_url>
cd bite-latency-experiment

# 2. Configure environment
cp .env.example .env
nano .env  # Update with your settings

# 3. Update production API key
nano kong/kong.yml  # Change production-client API key

# 4. Run deployment
chmod +x deploy.sh
./deploy.sh
```

## Service Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Client                                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Kong API Gateway (Port 8000)                    │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Plugins:                                            │    │
│  │  - Key Auth (API key validation)                   │    │
│  │  - Rate Limiting (100/min, 1000/hour)              │    │
│  │  - CORS (cross-origin support)                     │    │
│  │  - File Log (request logging)                      │    │
│  └────────────────────────────────────────────────────┘    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│         Django Application (Gunicorn, Port 8080)            │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Apps:                                               │    │
│  │  - Reports API (/api/report/)                      │    │
│  │  - Health Check (/api/health/)                     │    │
│  │  - Cache Management (/api/cache/clear/)            │    │
│  │  - Django Admin (/admin/)                          │    │
│  └────────────────────────────────────────────────────┘    │
└────────────┬─────────────────────────┬─────────────────────┘
             │                         │
             ▼                         ▼
┌───────────────────────┐  ┌──────────────────────┐
│  PostgreSQL (5432)    │  │   Redis (6379)       │
│  - Reports data       │  │   - Cache layer      │
│  - User data          │  │   - Session storage  │
└───────────────────────┘  └──────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│              Kong Database - PostgreSQL (5432)               │
│              - Kong configuration                            │
│              - Consumer/API key storage                      │
└─────────────────────────────────────────────────────────────┘
```

## Pre-configured API Keys

| Consumer | API Key | Purpose |
|----------|---------|---------|
| test-client | `test-api-key-12345` | Development and testing |
| jmeter-client | `jmeter-load-test-key-67890` | JMeter load testing |
| production-client | `prod-secure-key-CHANGE-THIS-IN-PRODUCTION` | Production use ⚠️ |
| monitoring-client | `monitor-health-check-key-11111` | Health monitoring |

**IMPORTANT**: Change the production API key before deploying to production!

## API Endpoints

### Public (No Authentication)
- `GET /api/health/` - Health check

### Protected (Requires API Key)
- `GET /api/report/?projectId=X&month=YYYY-MM` - Get report
- `POST /api/cache/clear/` - Clear cache
- `ALL /admin/` - Django admin interface

### Example Authenticated Request
```bash
curl -H "apikey: test-api-key-12345" \
  "http://localhost:8000/api/report/?projectId=proj-001&month=2026-01"
```

## Network Ports

### Exposed to Public
- **8000** - Kong Proxy HTTP (API Gateway)
- **8443** - Kong Proxy HTTPS (requires SSL configuration)

### Internal/Admin Only
- **8001** - Kong Admin API (restrict access!)
- **8080** - Django direct access (optional, can be blocked)

### Internal (Docker network only)
- **5432** - PostgreSQL (Django)
- **6379** - Redis
- **5432** - PostgreSQL (Kong)

## Security Features

1. **API Key Authentication** - All protected endpoints require valid API keys
2. **Rate Limiting** - 100 requests/minute, 1000 requests/hour per consumer
3. **CORS Support** - Configured for cross-origin requests
4. **Request Size Limiting** - Maximum 10MB payload
5. **Health Checks** - Active and passive monitoring
6. **Firewall Rules** - UFW configuration for port restrictions
7. **Non-root Docker User** - Django runs as non-root user in container

## Management Commands

### Kong Management
```bash
# Check status
./kong/manage_kong.sh status

# List consumers
./kong/manage_kong.sh consumers

# Create new API key
./kong/manage_kong.sh create-key my-consumer

# Test endpoint
./kong/manage_kong.sh test test-api-key-12345 /api/report/?projectId=proj-001&month=2026-01
```

### Service Management
```bash
# View status
docker compose ps

# View logs
docker compose logs -f [service-name]

# Restart service
docker compose restart [service-name]

# Stop all
docker compose down

# Start all
docker compose up -d
```

### Django Management
```bash
# Run migrations
docker compose exec django-app python manage.py migrate

# Seed data
docker compose exec django-app python manage.py seed_reports --projects 100 --months 12

# Warm cache
docker compose exec django-app python manage.py warm_cache --limit 500

# Create superuser
docker compose exec django-app python manage.py createsuperuser
```

## Production Checklist

Before deploying to production, ensure:

- [ ] Updated `SECRET_KEY` in `.env`
- [ ] Set `DEBUG=False` in `.env`
- [ ] Configured `ALLOWED_HOSTS` with your domain/IP
- [ ] Changed all database passwords
- [ ] Updated production API key in `kong/kong.yml`
- [ ] Configured firewall (UFW)
- [ ] Restricted Kong Admin API (port 8001) access
- [ ] Set up SSL/HTTPS certificates
- [ ] Configured automated backups
- [ ] Set up monitoring and alerting
- [ ] Secured `.env` file (`chmod 600 .env`)
- [ ] Reviewed Kong rate limiting settings
- [ ] Tested all API endpoints
- [ ] Configured log rotation

## Monitoring

### Health Checks
```bash
# Application health
curl http://localhost:8000/api/health/

# Kong status
curl http://localhost:8001/status

# Service status
docker compose ps
```

### Logs
```bash
# All services
docker compose logs -f

# Django application
docker compose logs -f django-app

# Kong Gateway
docker compose logs -f kong

# PostgreSQL
docker compose logs -f postgres
```

## Backup and Recovery

### Manual Backup
```bash
# Backup Django database
docker compose exec postgres pg_dump -U bite_user bite_latency > backup.sql

# Backup Kong database
docker compose exec kong-database pg_dump -U kong kong > kong_backup.sql
```

### Automated Backups
See [VPS_DEPLOYMENT_GUIDE.md](VPS_DEPLOYMENT_GUIDE.md#database-backups) for automated backup setup.

## Troubleshooting

### Common Issues

1. **Services won't start**
   ```bash
   docker compose logs
   docker compose down && docker compose up -d
   ```

2. **Kong returns 502**
   - Check Django is running: `docker compose ps django-app`
   - Check Django health: `curl http://localhost:8080/api/health/`

3. **API key not working**
   - Verify consumer exists: `./kong/manage_kong.sh consumers`
   - Check API key: `./kong/manage_kong.sh list-keys test-client`

4. **Can't connect from external network**
   - Check firewall: `sudo ufw status`
   - Verify ports: `sudo netstat -tlnp | grep 8000`

## Additional Resources

- **[VPS Deployment Guide](VPS_DEPLOYMENT_GUIDE.md)** - Complete deployment instructions
- **[Kong Guide](kong/KONG_GUIDE.md)** - Detailed Kong reference
- **[Main README](README.md)** - Application documentation
- **Kong Documentation**: https://docs.konghq.com/
- **Django Documentation**: https://docs.djangoproject.com/

## Support

For issues or questions:
1. Check the logs: `docker compose logs`
2. Review troubleshooting guides
3. Verify configuration files
4. Test with Kong management script: `./kong/manage_kong.sh`

---

**Deployment Date**: April 2026
**Kong Version**: 3.8
**Django Version**: 6.0.3
**PostgreSQL Version**: 16
**Redis Version**: 7
