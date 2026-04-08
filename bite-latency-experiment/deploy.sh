#!/bin/bash

# Deployment script for Bite Latency Experiment on AWS VPS (Ubuntu 24)
# This script automates the deployment process with Kong API Gateway

set -e  # Exit on error

echo "=========================================="
echo "Bite Latency Experiment - Deployment"
echo "=========================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored messages
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check if .env file exists
if [ ! -f .env ]; then
    print_error ".env file not found!"
    echo "Please create a .env file with the required environment variables."
    echo "You can use .env.example as a template."
    exit 1
fi

print_success ".env file found"

# Load environment variables
source .env

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed"
    echo "Installing Docker..."

    # Update package index
    sudo apt-get update

    # Install prerequisites
    sudo apt-get install -y ca-certificates curl gnupg lsb-release

    # Add Docker's official GPG key
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

    # Set up Docker repository
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker Engine
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Add current user to docker group
    sudo usermod -aG docker $USER

    print_success "Docker installed successfully"
    print_warning "Please log out and log back in for group changes to take effect"
else
    print_success "Docker is already installed"
fi

# Check if Docker Compose is available
if ! docker compose version &> /dev/null; then
    print_error "Docker Compose plugin is not available"
    exit 1
fi

print_success "Docker Compose is available"

# Stop existing containers (if any)
echo ""
echo "Stopping existing containers..."
docker compose down || true
print_success "Existing containers stopped"

# Remove old images (optional - uncomment to save space)
# docker compose down --rmi all

# Build and start containers
echo ""
echo "Building and starting containers..."
docker compose up -d --build

# Wait for services to be healthy
echo ""
echo "Waiting for services to be ready..."
sleep 10

# Check External PostgreSQL connection
echo "Checking external PostgreSQL connection..."
docker compose exec -T django-app python -c "
import psycopg2
import os
try:
    conn = psycopg2.connect(
        dbname=os.getenv('DB_NAME', 'bite_latency'),
        user=os.getenv('DB_USER', 'bite_user'),
        password=os.getenv('DB_PASSWORD', 'bite_pass'),
        host=os.getenv('DB_HOST', '127.0.0.1'),
        port=os.getenv('DB_PORT', '5434')
    )
    conn.close()
    print('Connected successfully')
except Exception as e:
    print(f'Connection failed: {e}')
    exit(1)
" || {
    print_error "Cannot connect to external PostgreSQL database"
    print_warning "Check your DB_HOST, DB_PORT, and network connectivity in .env"
    exit 1
}
print_success "External PostgreSQL connection verified"

# Check Redis
echo "Checking Redis..."
docker compose exec -T redis redis-cli ping || {
    print_error "Redis is not ready"
    exit 1
}
print_success "Redis is ready"

# Note: Migrations run automatically on container startup via entrypoint
echo ""
echo "Django migrations will run automatically on container startup"
print_success "Migration setup configured"

# Create Django superuser (optional - only if environment variables are set)
if [ ! -z "$DJANGO_SUPERUSER_USERNAME" ] && [ ! -z "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo ""
    echo "Creating Django superuser..."
    docker compose exec -T django-app python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='$DJANGO_SUPERUSER_USERNAME').exists():
    User.objects.create_superuser('$DJANGO_SUPERUSER_USERNAME', '$DJANGO_SUPERUSER_EMAIL', '$DJANGO_SUPERUSER_PASSWORD')
    print('Superuser created successfully')
else:
    print('Superuser already exists')
EOF
    print_success "Superuser setup completed"
fi

# Seed initial data (optional - controlled by environment variable)
if [ "$SEED_DATA" = "true" ]; then
    echo ""
    echo "Seeding initial data..."
    docker compose exec -T django-app python manage.py seed_reports --projects ${SEED_PROJECTS:-10} --months ${SEED_MONTHS:-3} --replace
    print_success "Data seeding completed"
fi

# Warm cache (optional - controlled by environment variable)
if [ "$WARM_CACHE" = "true" ]; then
    echo ""
    echo "Warming cache..."
    docker compose exec -T django-app python manage.py warm_cache --limit ${WARM_CACHE_LIMIT:-100}
    print_success "Cache warming completed"
fi

# Check Kong health
echo ""
echo "Checking Kong Gateway..."
sleep 5
curl -f http://localhost:8001/status || {
    print_error "Kong is not ready"
    exit 1
}
print_success "Kong Gateway is ready"

# Display service status
echo ""
echo "=========================================="
echo "Deployment completed successfully!"
echo "=========================================="
echo ""
echo "Services status:"
docker compose ps
echo ""
echo "Access points:"
echo "  - Django App (direct):     http://localhost:8080"
echo "  - Kong Proxy (API Gateway): http://localhost:8000"
echo "  - Kong Admin API:          http://localhost:8001"
echo "  - Django Health Check:     http://localhost:8000/api/health"
echo ""
echo "API Key Authentication:"
echo "  - Test API Key:      test-api-key-12345"
echo "  - JMeter API Key:    jmeter-load-test-key-67890"
echo ""
echo "Example authenticated request:"
echo "  curl -H 'apikey: test-api-key-12345' 'http://localhost:8000/api/report/?projectId=proj-001&month=2026-01'"
echo ""
echo "To view logs:"
echo "  docker compose logs -f [service-name]"
echo ""
echo "To stop all services:"
echo "  docker compose down"
echo ""
print_success "Deployment complete!"
