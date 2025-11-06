#!/bin/bash

# =============================================================================
# Vault Proxy Token Setup Script
# =============================================================================
# This script saves the root token to a file for use by Vault Proxy.
# For demo purposes only.
# =============================================================================

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

# Vault server configuration
VAULT_ADDR="http://127.0.0.1:8200"
VAULT_TOKEN="root"
TOKEN_FILE="./token"

# Check Vault connection
check_vault_connection() {
    log_info "Checking Vault server connection... ($VAULT_ADDR)"
    
    export VAULT_ADDR="$VAULT_ADDR"
    export VAULT_TOKEN="$VAULT_TOKEN"
    
    if ! vault status >/dev/null 2>&1; then
        log_error "Cannot connect to Vault server."
        log_error "Please check if Vault development server is running:"
        log_error "  vault server -dev -dev-root-token-id=\"root\""
        exit 1
    fi
    
    log_success "Vault server connection verified"
}

# Create token file
create_token_file() {
    log_info "Creating token file... ($TOKEN_FILE)"
    
    # Create token file
    echo "$VAULT_TOKEN" > "$TOKEN_FILE"
    
    # Set file permissions (owner read/write only)
    chmod 600 "$TOKEN_FILE"
    
    log_success "Token file created"
}

# Verify token validity
verify_token() {
    log_info "Verifying token validity..."
    
    export VAULT_ADDR="$VAULT_ADDR"
    export VAULT_TOKEN="$(cat $TOKEN_FILE)"
    
    if vault token lookup >/dev/null 2>&1; then
        log_success "Token validity verified"
    else
        log_error "Token is invalid."
        exit 1
    fi
}

# Main execution
main() {
    echo "============================================================================="
    echo "🔑 Vault Proxy Token Setup Script"
    echo "============================================================================="
    echo ""
    
    # 1. Check Vault connection
    check_vault_connection
    
    # 2. Create token file
    create_token_file
    
    # 3. Verify token validity
    verify_token
    
    echo ""
    echo "============================================================================="
    log_success "Token setup completed!"
    echo "============================================================================="
    echo ""
    echo "Next steps:"
    echo "1. Start Vault Proxy: ./start-proxy.sh"
    echo "2. Test script: ../get_kv_secret.sh (modify port to 8400)"
    echo ""
    echo "Notes:"
    echo "- This setup is for demo purposes only"
    echo "- Please secure the token file"
}

# Execute script
main "$@"
