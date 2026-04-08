#!/bin/bash

# Kong Management Script
# Helper script to manage Kong API Gateway

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Kong Admin API URL
KONG_ADMIN="http://localhost:8001"

# Function to check Kong status
check_status() {
    print_info "Checking Kong Gateway status..."
    curl -s "${KONG_ADMIN}/status" | jq '.' || {
        print_error "Kong is not responding"
        exit 1
    }
    print_success "Kong is running"
}

# Function to list all services
list_services() {
    print_info "Listing Kong services..."
    curl -s "${KONG_ADMIN}/services" | jq '.data[] | {name: .name, url: .url, id: .id}'
}

# Function to list all routes
list_routes() {
    print_info "Listing Kong routes..."
    curl -s "${KONG_ADMIN}/routes" | jq '.data[] | {name: .name, paths: .paths, id: .id}'
}

# Function to list all consumers
list_consumers() {
    print_info "Listing Kong consumers..."
    curl -s "${KONG_ADMIN}/consumers" | jq '.data[] | {username: .username, custom_id: .custom_id, id: .id}'
}

# Function to list all plugins
list_plugins() {
    print_info "Listing Kong plugins..."
    curl -s "${KONG_ADMIN}/plugins" | jq '.data[] | {name: .name, enabled: .enabled, id: .id}'
}

# Function to create a new API key for a consumer
create_api_key() {
    local consumer_name=$1
    local api_key=$2

    if [ -z "$consumer_name" ]; then
        print_error "Consumer name is required"
        echo "Usage: $0 create-key <consumer-name> [api-key]"
        exit 1
    fi

    print_info "Creating API key for consumer: $consumer_name"

    if [ -z "$api_key" ]; then
        # Generate random API key if not provided
        api_key=$(openssl rand -hex 32)
    fi

    curl -s -X POST "${KONG_ADMIN}/consumers/${consumer_name}/key-auth" \
        -d "key=${api_key}" | jq '.'

    print_success "API key created: $api_key"
}

# Function to list API keys for a consumer
list_consumer_keys() {
    local consumer_name=$1

    if [ -z "$consumer_name" ]; then
        print_error "Consumer name is required"
        echo "Usage: $0 list-keys <consumer-name>"
        exit 1
    fi

    print_info "Listing API keys for consumer: $consumer_name"
    curl -s "${KONG_ADMIN}/consumers/${consumer_name}/key-auth" | jq '.data[] | {id: .id, key: .key}'
}

# Function to test an API endpoint with authentication
test_api() {
    local api_key=$1
    local endpoint=${2:-"/api/health"}

    if [ -z "$api_key" ]; then
        print_error "API key is required"
        echo "Usage: $0 test <api-key> [endpoint]"
        exit 1
    fi

    print_info "Testing endpoint: $endpoint"
    curl -i -H "apikey: $api_key" "http://localhost:8000${endpoint}"
}

# Function to reload Kong configuration
reload_config() {
    print_info "Reloading Kong configuration..."
    docker compose restart kong
    sleep 5
    check_status
    print_success "Kong configuration reloaded"
}

# Function to view Kong logs
view_logs() {
    print_info "Viewing Kong logs (Ctrl+C to exit)..."
    docker compose logs -f kong
}

# Function to display help
show_help() {
    cat << EOF
Kong Management Script

Usage: $0 <command> [options]

Commands:
  status              Check Kong Gateway status
  services            List all services
  routes              List all routes
  consumers           List all consumers
  plugins             List all plugins
  create-key          Create API key for consumer
                      Usage: $0 create-key <consumer-name> [api-key]
  list-keys           List API keys for consumer
                      Usage: $0 list-keys <consumer-name>
  test                Test API endpoint with authentication
                      Usage: $0 test <api-key> [endpoint]
  reload              Reload Kong configuration
  logs                View Kong logs
  help                Show this help message

Examples:
  $0 status
  $0 create-key my-consumer
  $0 list-keys test-client
  $0 test test-api-key-12345 /api/report/?projectId=proj-001&month=2026-01
  $0 reload

EOF
}

# Main script logic
case "$1" in
    status)
        check_status
        ;;
    services)
        list_services
        ;;
    routes)
        list_routes
        ;;
    consumers)
        list_consumers
        ;;
    plugins)
        list_plugins
        ;;
    create-key)
        create_api_key "$2" "$3"
        ;;
    list-keys)
        list_consumer_keys "$2"
        ;;
    test)
        test_api "$2" "$3"
        ;;
    reload)
        reload_config
        ;;
    logs)
        view_logs
        ;;
    help|--help|-h|"")
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
