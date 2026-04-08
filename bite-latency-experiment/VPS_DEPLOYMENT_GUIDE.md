# AWS VPS Ubuntu 24 Deployment Guide

## Prerequisites

- AWS EC2 instance running Ubuntu 24.04 LTS
- SSH access to the VPS
- Domain name (optional, but recommended for production)
- Basic knowledge of Linux and Docker

## Step-by-Step Deployment

### 1. Connect to Your VPS

```bash
ssh ubuntu@your-vps-ip
```

### 2. Update System Packages

```bash
sudo apt-get update && sudo apt-get upgrade -y
```

### 3. Install Required Tools

```bash
# Install git
sudo apt-get install -y git curl wget jq

# Install Docker (will be done by deploy.sh if not present)
# Or manually:
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

**Important**: After adding user to docker group, log out and log back in for changes to take effect.

### 4. Clone the Repository

```bash
cd ~
git clone <your-repository-url>
cd bite-latency-experiment
```

### 5. Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit with your configuration
nano .env
```

**Required Changes:**

```bash
# Generate a secure SECRET_KEY
python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# Update .env file with:
SECRET_KEY=your-generated-secret-key
DEBUG=False
ALLOWED_HOSTS=your-vps-ip,your-domain.com

# Set secure passwords
DB_PASSWORD=your-secure-db-password
KONG_PG_PASSWORD=your-secure-kong-password

# Optional: Configure Django superuser
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@yourdomain.com
DJANGO_SUPERUSER_PASSWORD=secure-admin-password

# Optional: Seed initial data
SEED_DATA=true
SEED_PROJECTS=100
SEED_MONTHS=12
```

### 6. Update Kong API Keys (IMPORTANT!)

```bash
# Edit Kong configuration
nano kong/kong.yml

# Find the production-client consumer and update the API key:
consumers:
  - username: production-client
    custom_id: prod-001
    tags:
      - production
    keyauth_credentials:
      - key: YOUR-NEW-SECURE-PRODUCTION-KEY-HERE
```

**Generate a secure API key:**
```bash
openssl rand -hex 32
```

### 7. Configure Firewall

```bash
# Enable UFW firewall
sudo ufw --force enable

# Allow SSH (IMPORTANT - do this first!)
sudo ufw allow ssh
sudo ufw allow 22/tcp

# Allow Kong Proxy (public API)
sudo ufw allow 8000/tcp

# Allow HTTPS (if you plan to use SSL)
sudo ufw allow 8443/tcp

# Restrict Kong Admin API to your IP only
sudo ufw allow from YOUR_ADMIN_IP to any port 8001

# Check firewall status
sudo ufw status verbose
```

### 8. Deploy the Application

```bash
# Make deployment script executable
chmod +x deploy.sh

# Run deployment
./deploy.sh
```

The deployment script will:
1. Install Docker if needed
2. Build and start all containers
3. Run database migrations
4. Create Django superuser (if configured)
5. Seed initial data (if enabled)
6. Configure Kong API Gateway

### 9. Verify Deployment

```bash
# Check all services are running
docker compose ps

# Test health endpoint (no authentication)
curl http://localhost:8000/api/health/

# Test authenticated endpoint
curl -H "apikey: test-api-key-12345" \
  "http://localhost:8000/api/report/?projectId=proj-001&month=2026-01"

# Check Kong status
./kong/manage_kong.sh status
```

### 10. Test from External Client

From your local machine:

```bash
# Replace YOUR_VPS_IP with your actual VPS IP
curl http://YOUR_VPS_IP:8000/api/health/

# Test with authentication
curl -H "apikey: your-production-key" \
  "http://YOUR_VPS_IP:8000/api/report/?projectId=proj-001&month=2026-01"
```

## Post-Deployment Configuration

### Set Up Automatic Restarts

```bash
# Create systemd service for auto-restart on boot
sudo nano /etc/systemd/system/bite-latency.service
```

Add this content:

```ini
[Unit]
Description=Bite Latency Experiment Docker Compose
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/ubuntu/bite-latency-experiment
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

Enable the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable bite-latency.service
sudo systemctl start bite-latency.service
```

### Configure Log Rotation

```bash
sudo nano /etc/logrotate.d/bite-latency
```

Add this content:

```
/var/lib/docker/containers/*/*.log {
    rotate 7
    daily
    compress
    size=10M
    missingok
    delaycompress
    copytruncate
}
```

### Set Up Monitoring

```bash
# Install monitoring script
nano ~/monitor.sh
```

Add this content:

```bash
#!/bin/bash
cd ~/bite-latency-experiment

# Check if services are running
if ! docker compose ps | grep -q "running"; then
    echo "Services are down! Restarting..."
    docker compose up -d
    echo "Services restarted at $(date)" >> monitor.log
fi

# Check API health
if ! curl -f -s http://localhost:8000/api/health/ > /dev/null; then
    echo "Health check failed! Restarting services..."
    docker compose restart
    echo "Services restarted due to health check failure at $(date)" >> monitor.log
fi
```

Make it executable and add to cron:

```bash
chmod +x ~/monitor.sh

# Add to crontab (runs every 5 minutes)
crontab -e
# Add this line:
*/5 * * * * /home/ubuntu/monitor.sh
```

## SSL/HTTPS Configuration (Recommended for Production)

### Option 1: Using Let's Encrypt

```bash
# Install certbot
sudo apt-get install -y certbot

# Generate certificate (replace with your domain)
sudo certbot certonly --standalone -d yourdomain.com

# Certificates will be in /etc/letsencrypt/live/yourdomain.com/
```

Then configure Kong to use these certificates (see Kong documentation).

### Option 2: Using Nginx as Reverse Proxy

```bash
# Install Nginx
sudo apt-get install -y nginx

# Configure Nginx
sudo nano /etc/nginx/sites-available/bite-latency
```

Add this configuration:

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/bite-latency /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Then use certbot with nginx
sudo certbot --nginx -d yourdomain.com
```

## Database Backups

### Automated Backup Script

```bash
nano ~/backup.sh
```

Add this content:

```bash
#!/bin/bash
BACKUP_DIR="/home/ubuntu/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup Django database
docker compose exec -T postgres pg_dump -U bite_user bite_latency > \
  "$BACKUP_DIR/django_db_$TIMESTAMP.sql"

# Backup Kong database
docker compose exec -T kong-database pg_dump -U kong kong > \
  "$BACKUP_DIR/kong_db_$TIMESTAMP.sql"

# Compress backups
gzip "$BACKUP_DIR/django_db_$TIMESTAMP.sql"
gzip "$BACKUP_DIR/kong_db_$TIMESTAMP.sql"

# Delete backups older than 7 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

echo "Backup completed: $TIMESTAMP"
```

Make it executable and schedule:

```bash
chmod +x ~/backup.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add this line:
0 2 * * * /home/ubuntu/backup.sh >> /home/ubuntu/backup.log 2>&1
```

## Troubleshooting

### Services Won't Start

```bash
# Check logs
docker compose logs

# Check specific service
docker compose logs django-app
docker compose logs kong

# Restart all services
docker compose down
docker compose up -d
```

### Can't Connect from External Network

```bash
# Check firewall
sudo ufw status

# Check if ports are open
sudo netstat -tlnp | grep -E '8000|8080|8001'

# Check Docker network
docker network inspect bite-latency-experiment_bite-network
```

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker compose ps postgres

# Connect to database manually
docker compose exec postgres psql -U bite_user -d bite_latency

# Check database logs
docker compose logs postgres
```

### Kong Not Working

```bash
# Check Kong logs
docker compose logs kong

# Verify Kong configuration
docker compose exec kong kong config parse /usr/local/kong/declarative/kong.yml

# Check Kong status via Admin API
curl http://localhost:8001/status

# Restart Kong
docker compose restart kong
```

## Updating the Application

```bash
cd ~/bite-latency-experiment

# Pull latest changes
git pull origin main

# Rebuild and restart
docker compose down
docker compose up -d --build

# Run migrations (if needed)
docker compose exec django-app python manage.py migrate
```

## Security Checklist

- [ ] Changed SECRET_KEY to a secure random string
- [ ] Set DEBUG=False
- [ ] Updated ALLOWED_HOSTS
- [ ] Changed all default passwords
- [ ] Updated production API key in kong.yml
- [ ] Configured firewall (UFW)
- [ ] Restricted Kong Admin API access
- [ ] Set up SSL/HTTPS
- [ ] Configured automatic backups
- [ ] Set up monitoring
- [ ] Secured .env file (`chmod 600 .env`)
- [ ] Disabled root SSH login
- [ ] Set up SSH key authentication
- [ ] Configured fail2ban (optional but recommended)

## Additional Resources

- **Main README**: [README.md](README.md)
- **Kong Guide**: [kong/KONG_GUIDE.md](kong/KONG_GUIDE.md)
- **Kong Documentation**: https://docs.konghq.com/
- **Django Deployment**: https://docs.djangoproject.com/en/stable/howto/deployment/
- **Docker Compose**: https://docs.docker.com/compose/

## Support Commands

```bash
# View all services
docker compose ps

# View logs
docker compose logs -f

# Restart a service
docker compose restart [service-name]

# Stop all services
docker compose down

# Start all services
docker compose up -d

# Check Kong status
./kong/manage_kong.sh status

# List API consumers
./kong/manage_kong.sh consumers
```

## Getting Help

If you encounter issues:

1. Check the logs: `docker compose logs`
2. Review the troubleshooting section above
3. Consult the Kong Guide: `kong/KONG_GUIDE.md`
4. Check service status: `docker compose ps`
5. Verify configuration: review `.env` and `kong/kong.yml`
