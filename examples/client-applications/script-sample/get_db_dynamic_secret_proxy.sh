#!/bin/bash

# =============================================================================
# Database Dynamic Secret Retrieval Script (Vault Proxy Integration)
# =============================================================================
# This script retrieves Database Dynamic secrets through Vault Proxy.
# Uses pure curl to fetch dynamic credentials without Vault CLI.
# =============================================================================

# Vault Proxy configuration (hardcoded)
VAULT_PROXY_ADDR="http://127.0.0.1:8400"
VAULT_NAMESPACE=""  # Vault Namespace (set if needed, e.g., "my-namespace")
DB_DYNAMIC_PATH="my-vault-app-database/creds/db-demo-dynamic"

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check jq installation
check_jq() {
    if ! command -v jq >/dev/null 2>&1; then
        log_error "jq is not installed. Please install jq."
        log_error "Ubuntu/Debian: sudo apt-get install jq"
        log_error "CentOS/RHEL: sudo yum install jq"
        log_error "macOS: brew install jq"
        exit 1
    fi
}

# Check Vault Proxy connection
check_vault_proxy() {
    log_info "Checking Vault Proxy connection... ($VAULT_PROXY_ADDR)"
    
    if ! curl -s -f "$VAULT_PROXY_ADDR/v1/sys/health" >/dev/null 2>&1; then
        log_error "Cannot connect to Vault Proxy."
        log_error "Please check if Vault Proxy is running: $VAULT_PROXY_ADDR"
        log_error "Start Vault Proxy: cd vault-proxy-demo && ./start-proxy.sh"
        exit 1
    fi
    
    log_success "Vault Proxy connection verified"
}

# Retrieve Database Dynamic secret
get_db_dynamic_secret() {
    log_info "Retrieving Database Dynamic secret... ($DB_DYNAMIC_PATH)"
    
    # Retrieve secret using curl
    if [ -n "$VAULT_NAMESPACE" ]; then
        RESPONSE=$(curl -s -w "\n%{http_code}" \
            -H "X-Vault-Namespace: $VAULT_NAMESPACE" \
            "$VAULT_PROXY_ADDR/v1/$DB_DYNAMIC_PATH")
    else
        RESPONSE=$(curl -s -w "\n%{http_code}" \
            "$VAULT_PROXY_ADDR/v1/$DB_DYNAMIC_PATH")
    fi
    
    # Separate HTTP status code and response body
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$RESPONSE" | sed '$d')
    
    # Check HTTP status code
    if [ "$HTTP_CODE" != "200" ]; then
        log_error "Secret retrieval failed (HTTP $HTTP_CODE)"
        echo "Response: $RESPONSE_BODY"
        exit 1
    fi
    
    # Parse and output JSON
    log_success "Database Dynamic secret retrieval successful!"
    echo ""
    echo "=== Database Dynamic Credentials ==="
    
    # Output credential information
    USERNAME=$(echo "$RESPONSE_BODY" | jq -r '.data.username')
    PASSWORD=$(echo "$RESPONSE_BODY" | jq -r '.data.password')
    LEASE_ID=$(echo "$RESPONSE_BODY" | jq -r '.lease_id')
    LEASE_DURATION=$(echo "$RESPONSE_BODY" | jq -r '.lease_duration')
    
    echo "Username: $USERNAME"
    echo "Password: $PASSWORD"
    echo "Lease ID: $LEASE_ID"
    echo "Lease Duration: ${LEASE_DURATION} seconds"
    
    # Calculate TTL information
    if [ "$LEASE_DURATION" != "null" ] && [ "$LEASE_DURATION" != "0" ]; then
        TTL_HOURS=$((LEASE_DURATION / 3600))
        TTL_MINUTES=$(((LEASE_DURATION % 3600) / 60))
        echo "TTL: ${TTL_HOURS} hours ${TTL_MINUTES} minutes"
    fi
    
    echo ""
    echo "=== Usage Example ==="
    echo "mysql -h localhost -P 3306 -u $USERNAME -p$PASSWORD"
    echo "or"
    echo "export DB_USERNAME=\"$USERNAME\""
    echo "export DB_PASSWORD=\"$PASSWORD\""
    
    echo ""
    echo "=== Vault Proxy Information ==="
    echo "Proxy Address: $VAULT_PROXY_ADDR"
    echo "Secret Path: $DB_DYNAMIC_PATH"
}

# Main execution
main() {
    echo "============================================================================="
    echo "🔄 Database Dynamic Secret Retrieval Script (Vault Proxy Integration)"
    echo "============================================================================="
    echo ""
    
    # 1. Check jq installation
    check_jq
    
    # 2. Check Vault Proxy connection
    check_vault_proxy
    
    # 3. Retrieve Database Dynamic secret
    get_db_dynamic_secret
    
    echo ""
    echo "============================================================================="
    log_success "Database Dynamic secret retrieval completed!"
    echo "============================================================================="
}

# Execute script
main "$@"
