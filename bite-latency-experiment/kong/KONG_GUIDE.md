# Kong API Gateway - Quick Reference Guide

## Overview

Kong API Gateway is deployed as part of the Bite Latency Experiment to provide:
- **API Key Authentication** (key-auth plugin)
- **Rate Limiting** to prevent abuse
- **Request/Response Logging**
- **CORS Support** for browser-based clients
- **Load Balancing** and health checks

## Architecture

```
Client Request
    ↓
Kong Gateway (Port 8000)
    ↓ (applies authentication, rate limiting, etc.)
Django Application (Port 8080)
    ↓
PostgreSQL / Redis
```

## Pre-configured API Keys

| Consumer | API Key | Purpose |
|----------|---------|---------|
| test-client | `test-api-key-12345` | Development and testing |
| jmeter-client | `jmeter-load-test-key-67890` | JMeter load testing |
| production-client | `prod-secure-key-CHANGE-THIS-IN-PRODUCTION` | Production use (⚠️ MUST CHANGE) |
| monitoring-client | `monitor-health-check-key-11111` | Health check monitoring |

## Quick Commands

### Check Kong Status
```bash
curl http://localhost:8001/status
```

### List All Services
```bash
curl http://localhost:8001/services | jq
```

### List All Routes
```bash
curl http://localhost:8001/routes | jq
```

### List All Consumers
```bash
curl http://localhost:8001/consumers | jq
```

### List All Plugins
```bash
curl http://localhost:8001/plugins | jq
```

## Managing API Keys

### Create a New Consumer
```bash
curl -X POST http://localhost:8001/consumers \
  -d "username=new-client" \
  -d "custom_id=custom-001"
```

### Add API Key to Consumer
```bash
curl -X POST http://localhost:8001/consumers/new-client/key-auth \
  -d "key=my-new-api-key-123456"
```

### Generate Random API Key
```bash
curl -X POST http://localhost:8001/consumers/new-client/key-auth
# Kong will generate a random key
```

### List Consumer's API Keys
```bash
curl http://localhost:8001/consumers/new-client/key-auth | jq
```

### Delete an API Key
```bash
curl -X DELETE http://localhost:8001/consumers/new-client/key-auth/{key-id}
```

## Testing API Endpoints

### Test Without Authentication (Should Fail)
```bash
curl -i http://localhost:8000/api/report/?projectId=proj-001&month=2026-01
# Expected: 401 Unauthorized
```

### Test With Valid API Key (Header)
```bash
curl -i -H "apikey: test-api-key-12345" \
  http://localhost:8000/api/report/?projectId=proj-001&month=2026-01
# Expected: 200 OK
```

### Test With Valid API Key (Query Parameter)
```bash
curl -i "http://localhost:8000/api/report/?projectId=proj-001&month=2026-01&apikey=test-api-key-12345"
# Expected: 200 OK
```

### Test Health Endpoint (No Auth Required)
```bash
curl http://localhost:8000/api/health/
# Expected: {"status": "ok", "service": "bite-latency-experiment"}
```

## Routes Configuration

Kong is configured with the following routes:

| Route Name | Path | Methods | Authentication |
|------------|------|---------|----------------|
| health-check | /api/health | GET | No |
| get-report | /api/report | GET | Yes (key-auth) |
| clear-cache | /api/cache/clear | POST | Yes (key-auth) |
| django-admin | /admin | ALL | Yes (key-auth) |

## Plugins Configuration

### Global Plugins (Apply to All Routes)

1. **Request Size Limiting**
   - Maximum payload: 10 MB
   - Prevents large request attacks

### Service-Level Plugins

1. **Rate Limiting**
   - 100 requests per minute per consumer
   - 1000 requests per hour per consumer
   - Policy: local (in-memory)

2. **File Logging**
   - Logs all requests to `/tmp/kong-requests.log`
   - Useful for debugging and audit

3. **CORS**
   - Allows all origins (`*`)
   - Supports credentials
   - Max age: 3600 seconds

### Route-Level Plugins

1. **Key-Auth** (on protected routes)
   - Accepts API keys in:
     - Header: `apikey` or `x-api-key`
     - Query parameter: `apikey`
   - Hides credentials from upstream service

## Updating Kong Configuration

### Method 1: Update Declarative Config File

1. Edit `kong/kong.yml`
2. Reload Kong:
   ```bash
   docker compose restart kong
   ```

### Method 2: Use Kong Admin API

```bash
# Add a new route
curl -X POST http://localhost:8001/services/bite-latency-api/routes \
  -d "name=new-route" \
  -d "paths[]=/api/new-endpoint" \
  -d "methods[]=GET"

# Add key-auth plugin to route
curl -X POST http://localhost:8001/routes/new-route/plugins \
  -d "name=key-auth" \
  -d "config.key_names[]=apikey"
```

## Health Checks and Upstreams

Kong monitors the Django application health:

- **Active Health Checks**:
  - Interval: 10 seconds
  - Endpoint: `/api/health/`
  - Healthy: 2 consecutive successes
  - Unhealthy: 3 consecutive failures

- **Passive Health Checks**:
  - Monitors actual traffic
  - Healthy: 5 consecutive successes
  - Unhealthy: 5 HTTP failures or 2 TCP failures

## Monitoring and Debugging

### View Kong Logs
```bash
docker compose logs -f kong
```

### Check Configuration Syntax
```bash
docker compose exec kong kong config parse /usr/local/kong/declarative/kong.yml
```

### Verify Database Connection
```bash
docker compose exec kong kong migrations list
```

### Test Admin API
```bash
curl http://localhost:8001/
# Should return Kong's admin API information
```

## Security Best Practices

1. **Restrict Admin API Access**
   - Use firewall to allow only trusted IPs
   - Consider binding to 127.0.0.1 only
   ```bash
   sudo ufw allow from YOUR_IP to any port 8001
   ```

2. **Use Strong API Keys**
   - Minimum 32 characters
   - Use random generation
   ```bash
   openssl rand -hex 32
   ```

3. **Enable HTTPS**
   - Use SSL certificates for production
   - Configure Kong to listen on 8443 with certificates

4. **Rotate API Keys Regularly**
   - Create new keys
   - Update clients
   - Delete old keys

5. **Monitor Rate Limits**
   - Adjust based on actual usage patterns
   - Use Redis for distributed rate limiting in multi-instance setups

## Production Considerations

### 1. Database Mode vs Declarative Mode

Current setup uses **Declarative Mode** (DB-less) for simplicity. For large-scale production:

- Consider using **Database Mode** for dynamic configuration
- Enables Kong Manager UI
- Supports multiple Kong instances with shared config

### 2. Scalability

To scale Kong horizontally:

```yaml
# docker-compose.yml
kong:
  deploy:
    replicas: 3
```

Add a load balancer (e.g., Nginx) in front of Kong instances.

### 3. Advanced Rate Limiting

For distributed rate limiting across multiple Kong instances:

```yaml
plugins:
  - name: rate-limiting
    config:
      policy: redis
      redis_host: redis
      redis_port: 6379
```

### 4. Monitoring and Observability

Consider integrating:
- **Prometheus Plugin**: For metrics
- **StatsD Plugin**: For real-time stats
- **Datadog/New Relic**: For APM

```bash
# Add Prometheus plugin
curl -X POST http://localhost:8001/plugins \
  -d "name=prometheus"
```

## Troubleshooting

### Issue: 502 Bad Gateway

**Cause**: Kong can't reach Django application

**Solution**:
```bash
# Check Django is running
docker compose ps django-app

# Check Django health directly
curl http://localhost:8080/api/health/

# Check Kong logs
docker compose logs kong
```

### Issue: API Key Not Working

**Cause**: Key not properly configured or wrong consumer

**Solution**:
```bash
# Verify consumer exists
curl http://localhost:8001/consumers/test-client

# List consumer's keys
curl http://localhost:8001/consumers/test-client/key-auth | jq

# Test with correct header name
curl -H "apikey: test-api-key-12345" http://localhost:8000/api/health/
```

### Issue: Configuration Not Loading

**Cause**: Syntax error in kong.yml

**Solution**:
```bash
# Validate configuration
docker compose exec kong kong config parse /usr/local/kong/declarative/kong.yml

# Check for errors in output
# Fix kong.yml and restart
docker compose restart kong
```

## References

- **Kong Documentation**: https://docs.konghq.com/
- **Key-Auth Plugin**: https://docs.konghq.com/hub/kong-inc/key-auth/
- **Rate Limiting Plugin**: https://docs.konghq.com/hub/kong-inc/rate-limiting/
- **Kong Admin API**: https://docs.konghq.com/gateway/latest/admin-api/

## Support

For issues specific to this deployment, use the management script:

```bash
./kong/manage_kong.sh help
```
