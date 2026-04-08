# Bite Latency Experiment

This project is a Django application designed to experiment with and measure latency, particularly focusing on data retrieval with and without caching mechanisms. It provides an API for accessing reports, along with management commands for data seeding, cache warming, and JMeter CSV generation.

**Includes Kong API Gateway with key-auth authentication for secure API access.**

## Quick Links

- **[VPS Deployment Guide](VPS_DEPLOYMENT_GUIDE.md)** - Complete step-by-step deployment guide for AWS VPS Ubuntu 24
- **[Kong API Gateway Guide](kong/KONG_GUIDE.md)** - Comprehensive Kong configuration and management reference
- **[Environment Configuration](.env.example)** - Template for environment variables

## Table of Contents

- [Application Structure](#application-structure)
- [Components](#components)
  - [Config Application (`config/`)](#config-application-config)
  - [Reports Application (`reports/`)](#reports-application-reports)
- [Features and Functions](#features-and-functions)
- [Deployment on a VPS](#deployment-on-a-vps)
  - [Environment Variables](#environment-variables)
  - [Ports and Network Interfaces](#ports-and-network-interfaces)
  - [Web Server (Gunicorn/Nginx)](#web-server-gunicornnginx)
- [Local Development Setup](#local-development-setup)
- [Usage](#usage)
  - [API Endpoints](#api-endpoints)
  - [Management Commands](#management-commands)

## Application Structure

The project is organized as follows:

- `bite-latency-experiment/`: The root directory of the Django project.
  - `config/`: Main Django project configuration.
  - `reports/`: Django application for managing and serving reports.
  - `jmeter/`: Contains JMeter test plans and results.
  - `venv/`: Python virtual environment.
  - `manage.py`: Django's command-line utility.
  - `requirements.txt`: Python dependencies.
  - `.env`: Environment variables (for local development).

## Components

### Config Application (`config/`)

This directory holds the core Django project settings and URL routing.

- `__init__.py`: Marks the directory as a Python package.
- `asgi.py`: ASGI configuration for asynchronous applications (e.g., websockets).
- `settings.py`:
    - **`SECRET_KEY`**: Used for cryptographic signing. **Must be kept secret in production.**
    - **`DEBUG`**: Boolean flag for debug mode. Set to `False` in production.
    - **`ALLOWED_HOSTS`**: A list of strings representing the host/domain names that this Django site can serve. Essential for security in production.
    - **`INSTALLED_APPS`**: Includes `rest_framework` and the `reports` app.
    - **`DATABASES`**: Configured for PostgreSQL, using environment variables for credentials and host/port.
        - Default: `DB_NAME=bite_latency`, `DB_USER=bite_user`, `DB_PASSWORD=bite_pass`, `DB_HOST=127.0.0.1`, `DB_PORT=5434`.
    - **`CACHES`**: Configured to use Redis as a backend for caching.
        - Default: `REDIS_URL=redis://127.0.0.1:6379`.
- `urls.py`: Defines the project's URL patterns.
    - Includes Django admin at `/admin/`.
    - Routes API requests to the `reports` app at `/api/`.
- `wsgi.py`: WSGI configuration for synchronous applications (standard HTTP requests).

### Reports Application (`reports/`)

This Django app handles the business logic related to reports.

- `__init__.py`: Marks the directory as a Python package.
- `admin.py`: Registers the `Report` model with the Django admin interface.
- `apps.py`: Application configuration.
- `models.py`: Defines the `Report` model with fields like `project_id`, `month`, `total_cost`, `currency`, `idle_resources`, `underutilized_instances`, and `estimated_waste`. It includes `unique_together` constraint and indexes for `project_id` and `month` for efficient lookups.
- `urls.py`: Defines API endpoints for the `reports` app:
    - `/api/health/`: Health check endpoint.
    - `/api/report/`: Endpoint to retrieve reports by `projectId` and `month`.
    - `/api/cache/clear/`: Endpoint to clear the application cache.
- `views.py`: Contains the view logic for the API endpoints.
    - `health_check`: Returns a simple JSON response indicating service status.
    - `report_view`:
        - Retrieves `projectId` and `month` from query parameters.
        - Attempts to fetch the report from Redis cache first (`cache.get`).
        - If not found in cache (cache miss), retrieves from the PostgreSQL database.
        - Stores the retrieved report in Redis cache (`cache.set`) for future requests.
        - Measures and includes `responseTimeMs` in the response.
    - `clear_cache`: Clears the entire Redis cache.
- `management/commands/`: Custom Django management commands.
    - `generate_jmeter_csv.py`: Generates a CSV file (`jmeter/report_requests.csv` by default) containing `projectId` and `month` from existing reports, suitable for JMeter test plans.
    - `seed_reports.py`: Populates the database with dummy report data for testing purposes. Allows specifying the number of projects and months, and an option to replace existing data.
    - `warm_cache.py`: Preloads report data into Redis cache, useful for "warm cache" latency tests.

## Features and Functions

- **Report Management**: Stores and retrieves financial reports related to cloud resource usage.
- **API Endpoints**: Provides RESTful endpoints for health checks, report retrieval, and cache management.
- **Caching**: Implements Redis caching to reduce database load and improve response times for frequently accessed reports.
- **Data Seeding**: Custom command to generate and populate the database with test data.
- **JMeter Integration**: Command to generate CSV files for JMeter, facilitating performance testing.
- **Cache Warming**: Custom command to pre-fill the cache with data, enabling "warm cache" performance testing scenarios.

## Deployment on AWS VPS (Ubuntu 24)

This application is designed to be deployed on an AWS VPS running Ubuntu 24 using Docker and Docker Compose. The deployment includes Kong API Gateway with key-auth authentication for secure API access.

### Quick Start Deployment

1. **Clone the repository on your VPS**:
   ```bash
   git clone <repository_url>
   cd bite-latency-experiment
   ```

2. **Configure environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your production values
   nano .env
   ```

3. **Run the deployment script**:
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

The deployment script will:
- Install Docker and Docker Compose (if not already installed)
- Build and start all containers (Django, PostgreSQL, Redis, Kong)
- Run database migrations
- Optionally seed data and warm cache
- Configure Kong API Gateway with key-auth

### Architecture Overview

The deployment includes the following services:

- **Django Application**: Runs with Gunicorn on port 8080 (internal)
- **PostgreSQL Database**: Port 5432 (internal to Docker network)
- **Redis Cache**: Port 6379 (internal to Docker network)
- **Kong API Gateway**:
  - Proxy (API access): Port 8000 (HTTP), 8443 (HTTPS)
  - Admin API: Port 8001 (HTTP), 8444 (HTTPS)
- **Kong Database**: Separate PostgreSQL instance for Kong

### Environment Variables

Copy `.env.example` to `.env` and configure the following:

**Django Configuration:**
- `SECRET_KEY`: Generate with `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`
- `DEBUG`: Set to `False` in production
- `ALLOWED_HOSTS`: Your domain/IP (e.g., `yourdomain.com,your-vps-ip`)

**Database Configuration:**
- `DB_NAME`: PostgreSQL database name (default: `bite_latency`)
- `DB_USER`: PostgreSQL user (default: `bite_user`)
- `DB_PASSWORD`: Secure password
- `DB_HOST`: `postgres` (Docker service name)
- `DB_PORT`: `5432` (internal Docker port)

**Cache Configuration:**
- `REDIS_URL`: `redis://redis:6379` (Docker service name)

**Kong Configuration:**
- `KONG_PG_PASSWORD`: Secure password for Kong's database

**Optional Settings:**
- `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL`, `DJANGO_SUPERUSER_PASSWORD`: For admin access
- `SEED_DATA`: Set to `true` to seed initial data
- `WARM_CACHE`: Set to `true` to pre-warm cache

### Kong API Gateway Configuration

Kong is configured using declarative configuration in [kong/kong.yml](kong/kong.yml).

**Pre-configured API Keys:**
1. **test-client**: `test-api-key-12345` (for development/testing)
2. **jmeter-client**: `jmeter-load-test-key-67890` (for JMeter load testing)
3. **production-client**: `prod-secure-key-CHANGE-THIS-IN-PRODUCTION` (⚠️ **MUST change in production**)
4. **monitoring-client**: `monitor-health-check-key-11111` (for health checks)

**Important**: Update the production API key in `kong/kong.yml` before deploying to production.

### Network Ports and Security

**Exposed Ports:**
- `8000`: Kong Proxy HTTP (public API access)
- `8080`: Django app (direct access - should be restricted via firewall)
- `8001`: Kong Admin API (restrict to localhost/admin IPs only)

**Internal Ports (not exposed to internet):**
- PostgreSQL: 5432
- Redis: 6379
- Kong Database: 5432

**Firewall Configuration** (using UFW on Ubuntu):
```bash
# Allow SSH
sudo ufw allow ssh

# Allow Kong Proxy (public API)
sudo ufw allow 8000/tcp

# Optionally allow HTTPS
sudo ufw allow 8443/tcp

# Restrict Kong Admin API to specific IP (replace with your IP)
sudo ufw allow from YOUR_ADMIN_IP to any port 8001

# Enable firewall
sudo ufw enable
```

### Kong Management

Use the Kong management script for common operations:

```bash
# Make script executable
chmod +x kong/manage_kong.sh

# Check Kong status
./kong/manage_kong.sh status

# List all consumers and their API keys
./kong/manage_kong.sh consumers
./kong/manage_kong.sh list-keys test-client

# Create new API key for a consumer
./kong/manage_kong.sh create-key my-consumer

# Test API endpoint
./kong/manage_kong.sh test test-api-key-12345 /api/report/?projectId=proj-001&month=2026-01

# View Kong logs
./kong/manage_kong.sh logs

# Reload Kong configuration
./kong/manage_kong.sh reload
```

### Service Management

**Start all services:**
```bash
docker compose up -d
```

**Stop all services:**
```bash
docker compose down
```

**View logs:**
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f django-app
docker compose logs -f kong
```

**Restart a service:**
```bash
docker compose restart django-app
docker compose restart kong
```

**Check service status:**
```bash
docker compose ps
```

## Local Development Setup

1.  **Clone the repository**:
    ```bash
    git clone <repository_url>
    cd bite-latency-experiment
    ```
2.  **Create a virtual environment**:
    ```bash
    python -m venv venv
    source venv/Scripts/activate # On Windows
    # source venv/bin/activate # On Linux/macOS
    ```
3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
4.  **Create a `.env` file**:
    Create a file named `.env` in the `bite-latency-experiment/` directory with the following content (adjust as needed):
    ```
    SECRET_KEY=your_secret_key_for_dev
    DEBUG=True
    ALLOWED_HOSTS=127.0.0.1,localhost
    DB_NAME=bite_latency_dev
    DB_USER=bite_user_dev
    DB_PASSWORD=bite_pass_dev
    DB_HOST=127.0.0.1
    DB_PORT=5434
    REDIS_URL=redis://127.0.0.1:6379
    ```
    Ensure you have a PostgreSQL database running and accessible at `DB_HOST:DB_PORT` and a Redis instance at `REDIS_URL`.
5.  **Run migrations**:
    ```bash
    python manage.py migrate
    ```
6.  **Seed initial data (optional)**:
    ```bash
    python manage.py seed_reports --projects 10 --months 3 --replace
    ```
7.  **Warm the cache (optional)**:
    ```bash
    python manage.py warm_cache --limit 100
    ```
8.  **Start the development server**:
    ```bash
    python manage.py runserver
    ```
    The application will be accessible at `http://127.0.0.1:8000/`.

## Usage

### API Endpoints

All API requests should be made through Kong API Gateway at `http://localhost:8000` (or your VPS IP/domain).

**Authentication**: Most endpoints require an API key. Include it in the request header or query parameter:
- Header: `apikey: your-api-key` or `x-api-key: your-api-key`
- Query: `?apikey=your-api-key`

#### 1. Health Check (No Authentication Required)

```bash
# Direct request
curl http://localhost:8000/api/health/

# Response
{"status": "ok", "service": "bite-latency-experiment"}
```

#### 2. Get Report (Authentication Required)

```bash
# Using header authentication
curl -H "apikey: test-api-key-12345" \
  "http://localhost:8000/api/report/?projectId=proj-001&month=2026-01"

# Using query parameter authentication
curl "http://localhost:8000/api/report/?projectId=proj-001&month=2026-01&apikey=test-api-key-12345"

# Response (example)
{
    "projectId": "proj-001",
    "month": "2026-01",
    "source": "cache",  // or "database"
    "report": {
        "totalCost": 1234567.89,
        "currency": "COP",
        "wasteIndicators": {
            "idleResources": 5,
            "underutilizedInstances": 3,
            "estimatedWaste": 123456.78
        }
    },
    "responseTimeMs": 1.23
}
```

#### 3. Clear Cache (Authentication Required)

```bash
# Using header authentication
curl -X POST -H "apikey: test-api-key-12345" \
  http://localhost:8000/api/cache/clear/

# Response
{"status": "ok", "message": "Cache limpiado correctamente."}
```

#### 4. Django Admin (Authentication Required)

```bash
# Access via browser with API key as query parameter
http://localhost:8000/admin/?apikey=test-api-key-12345
```

### Testing Authentication

**Successful request (with valid API key):**
```bash
curl -H "apikey: test-api-key-12345" http://localhost:8000/api/health/
# Returns: {"status": "ok", "service": "bite-latency-experiment"}
```

**Failed request (without API key):**
```bash
curl http://localhost:8000/api/report/?projectId=proj-001&month=2026-01
# Returns: {"message": "No API key found in request"}
```

**Failed request (with invalid API key):**
```bash
curl -H "apikey: invalid-key" http://localhost:8000/api/report/?projectId=proj-001&month=2026-01
# Returns: {"message": "Invalid authentication credentials"}
```

### Django Management Commands

Execute Django management commands inside the Docker container:

**Generate JMeter CSV:**
```bash
docker compose exec django-app python manage.py generate_jmeter_csv \
  --output jmeter/my_requests.csv --limit 1000
```

**Seed Reports:**
```bash
docker compose exec django-app python manage.py seed_reports \
  --projects 50 --months 6 --replace
```

**Warm Cache:**
```bash
docker compose exec django-app python manage.py warm_cache --limit 500
```

**Create Django Superuser:**
```bash
docker compose exec django-app python manage.py createsuperuser
```

**Run Migrations:**
```bash
docker compose exec django-app python manage.py migrate
```

### JMeter Load Testing with Kong

The application includes Kong API Gateway, so JMeter tests must include API key authentication:

1. **Generate test data CSV:**
   ```bash
   docker compose exec django-app python manage.py generate_jmeter_csv \
     --output jmeter/report_requests.csv --limit 1000
   ```

2. **Configure JMeter HTTP Header Manager:**
   - Add HTTP Header Manager to your test plan
   - Header Name: `apikey`
   - Header Value: `jmeter-load-test-key-67890`

3. **Update JMeter request URL:**
   - Server: Your VPS IP or `localhost`
   - Port: `8000` (Kong proxy port)
   - Path: `/api/report/?projectId=${projectId}&month=${month}`

### Monitoring and Troubleshooting

**Check service health:**
```bash
# Check all services
docker compose ps

# Health check via API
curl http://localhost:8000/api/health/

# Kong status
./kong/manage_kong.sh status
```

**View logs:**
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f django-app
docker compose logs -f kong
docker compose logs -f postgres
docker compose logs -f redis
```

**Connect to PostgreSQL:**
```bash
# Django database
docker compose exec postgres psql -U bite_user -d bite_latency

# Kong database
docker compose exec kong-database psql -U kong -d kong
```

**Connect to Redis:**
```bash
docker compose exec redis redis-cli
```

**Debugging Kong:**
```bash
# Check Kong configuration
docker compose exec kong kong config parse /usr/local/kong/declarative/kong.yml

# Test Kong health
curl http://localhost:8001/status

# List all Kong routes
curl http://localhost:8001/routes | jq
```

### Production Checklist

Before deploying to production:

- [ ] Change `SECRET_KEY` to a secure random string
- [ ] Set `DEBUG=False` in `.env`
- [ ] Update `ALLOWED_HOSTS` with your domain/IP
- [ ] Change all default passwords (DB_PASSWORD, KONG_PG_PASSWORD)
- [ ] Update production API key in `kong/kong.yml`
- [ ] Configure firewall to restrict Kong Admin API access
- [ ] Set up SSL/HTTPS certificates (recommend using Let's Encrypt)
- [ ] Configure proper backup strategy for PostgreSQL databases
- [ ] Set up monitoring and alerting
- [ ] Review and adjust Kong rate limiting settings
- [ ] Secure `.env` file permissions: `chmod 600 .env`
- [ ] Consider using Docker secrets or AWS Secrets Manager for sensitive data

### SSL/HTTPS Configuration (Optional)

For production deployments, configure SSL certificates:

1. **Using Let's Encrypt with Certbot:**
   ```bash
   # Install certbot
   sudo apt-get install certbot

   # Generate certificate
   sudo certbot certonly --standalone -d yourdomain.com

   # Certificates will be in /etc/letsencrypt/live/yourdomain.com/
   ```

2. **Update Kong configuration** to use certificates (see Kong documentation)

3. **Or use a reverse proxy** (Nginx/Traefik) in front of Kong for SSL termination
