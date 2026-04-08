To Use External PostgreSQL Database
1. Update .env file:
# Change DB_HOST from 'postgres' (Docker service) to your external DB
DB_HOST=your-external-db-ip-or-hostname
DB_PORT=5432  # or your DB port
DB_NAME=bite_latency
DB_USER=bite_user
DB_PASSWORD=your-password
2. Update docker-compose.yml: Comment out or remove the postgres service since you won't need it:
# Remove or comment out the postgres service
# postgres:
#   image: postgres:16-alpine
#   ...

# Update django-app dependencies
django-app:
  # Remove postgres from depends_on
  depends_on:
    redis:
      condition: service_healthy
    # postgres:  <-- Remove this
    #   condition: service_healthy
3. Ensure external DB is accessible:
External PostgreSQL must allow connections from your VPS IP
Configure pg_hba.conf on external DB to allow your VPS
Make sure firewall allows port 5432 from your VPS
That's it! The Django app will connect to your external PostgreSQL using the credentials in .env. The same applies for Redis - you can also point REDIS_URL to an external Redis instance (like AWS ElastiCache).