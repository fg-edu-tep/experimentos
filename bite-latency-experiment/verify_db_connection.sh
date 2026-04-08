#!/bin/bash

# Script to verify Django is connected to the correct PostgreSQL instance

echo "=========================================="
echo "Database Connection Verification"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Expected Database (from .env):${NC}"
source .env
echo "  Host: $DB_HOST"
echo "  Port: $DB_PORT"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo ""

echo -e "${BLUE}Testing connection from Django container...${NC}"
echo ""

# Run Django shell command to show database connection details
docker compose exec -T django-app python manage.py shell << 'EOF'
from django.db import connection
from django.conf import settings
import socket

print("=" * 50)
print("DJANGO DATABASE CONFIGURATION")
print("=" * 50)

db_settings = settings.DATABASES['default']
print(f"\nDatabase Engine: {db_settings['ENGINE']}")
print(f"Database Name: {db_settings['NAME']}")
print(f"Database User: {db_settings['USER']}")
print(f"Database Host: {db_settings['HOST']}")
print(f"Database Port: {db_settings['PORT']}")

print("\n" + "=" * 50)
print("ACTUAL CONNECTION DETAILS")
print("=" * 50)

# Test actual connection
try:
    with connection.cursor() as cursor:
        # Get PostgreSQL version
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"\nPostgreSQL Version:\n  {version}")

        # Get current database name
        cursor.execute("SELECT current_database();")
        current_db = cursor.fetchone()[0]
        print(f"\nConnected to Database: {current_db}")

        # Get connection info
        cursor.execute("SELECT inet_server_addr(), inet_server_port();")
        server_info = cursor.fetchone()
        server_ip = server_info[0] if server_info[0] else 'localhost/socket'
        server_port = server_info[1] if server_info[1] else 'N/A'
        print(f"\nServer IP: {server_ip}")
        print(f"Server Port: {server_port}")

        # Resolve hostname to verify it's the external DB
        try:
            host = db_settings['HOST']
            ip = socket.gethostbyname(host)
            print(f"\nHost '{host}' resolves to: {ip}")
        except:
            print(f"\nCould not resolve hostname: {host}")

        # Get list of tables (to verify it's your database)
        cursor.execute("""
            SELECT tablename
            FROM pg_catalog.pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename;
        """)
        tables = cursor.fetchall()
        print(f"\nTables in database ({len(tables)} total):")
        for table in tables[:10]:  # Show first 10
            print(f"  - {table[0]}")
        if len(tables) > 10:
            print(f"  ... and {len(tables) - 10} more")

        # Count rows in a Django table if exists
        cursor.execute("""
            SELECT COUNT(*)
            FROM pg_catalog.pg_tables
            WHERE schemaname = 'public' AND tablename = 'django_migrations';
        """)
        if cursor.fetchone()[0] > 0:
            cursor.execute("SELECT COUNT(*) FROM django_migrations;")
            migration_count = cursor.fetchone()[0]
            print(f"\nDjango Migrations Applied: {migration_count}")

        print("\n" + "=" * 50)
        print("✓ CONNECTION VERIFIED")
        print("=" * 50)

except Exception as e:
    print(f"\n✗ Connection Error: {e}")
    exit(1)
EOF

echo ""
echo -e "${GREEN}=========================================="
echo "Verification Complete!"
echo -e "==========================================${NC}"
echo ""
echo "If the 'Server IP' matches your AWS PostgreSQL instance,"
echo "then you are successfully connected to the external database."
echo ""
echo "You can also check the PostgreSQL logs on AWS to see the connection."
