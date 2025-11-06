#!/bin/bash

# =============================================================================
# Vault Proxy Start Script
# =============================================================================
# This script starts Vault Proxy in the background.
# =============================================================================

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration files
CONFIG_FILE="./vault-proxy.hcl"
PID_FILE="./vault-proxy.pid"
LOG_FILE="./vault-proxy.log"

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

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check Vault Proxy running status
check_proxy_status() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" >/dev/null 2>&1; then
            log_warning "Vault Proxy is already running (PID: $PID)"
            return 0
        else
            log_info "PID file exists but process is not running. Cleaning up PID file."
            rm -f "$PID_FILE"
        fi
    fi
    return 1
}

# Start Vault Proxy
start_proxy() {
    log_info "Starting Vault Proxy... (Port: 8400)"
    
    # Check configuration file
    if [ ! -f "$CONFIG_FILE" ]; then
        log_error "Configuration file not found: $CONFIG_FILE"
        exit 1
    fi
    
    # Check token file
    if [ ! -f "./token" ]; then
        log_error "Token file not found. Please run ./setup-token.sh first."
        exit 1
    fi
    
    # Start Vault Proxy (background)
    vault proxy -config="$CONFIG_FILE" > "$LOG_FILE" 2>&1 &
    PROXY_PID=$!
    
    # Save PID file
    echo "$PROXY_PID" > "$PID_FILE"
    
    # Wait briefly to verify startup
    sleep 2
    
    if ps -p "$PROXY_PID" >/dev/null 2>&1; then
        log_success "Vault Proxy started (PID: $PROXY_PID)"
        log_info "Log file: $LOG_FILE"
        log_info "PID file: $PID_FILE"
    else
        log_error "Vault Proxy startup failed"
        log_error "Please check logs: $LOG_FILE"
        rm -f "$PID_FILE"
        exit 1
    fi
}

# Verify Vault Proxy status
verify_proxy() {
    log_info "Verifying Vault Proxy status... (http://127.0.0.1:8400)"
    
    # Wait briefly
    sleep 3
    
    if curl -s -f "http://127.0.0.1:8400/v1/sys/health" >/dev/null 2>&1; then
        log_success "Vault Proxy is running normally"
        echo ""
        echo "=== Vault Proxy Information ==="
        echo "Address: http://127.0.0.1:8400"
        echo "PID: $(cat $PID_FILE)"
        echo "Log: $LOG_FILE"
        echo ""
        echo "=== Test Commands ==="
        echo "curl http://127.0.0.1:8400/v1/sys/health"
        echo "curl http://127.0.0.1:8400/v1/my-vault-app-kv/data/database"
    else
        log_error "Vault Proxy status verification failed"
        log_error "Please check logs: $LOG_FILE"
        exit 1
    fi
}

# Main execution
main() {
    echo "============================================================================="
    echo "🚀 Vault Proxy Start Script"
    echo "============================================================================="
    echo ""
    
    # 1. Check running status
    if check_proxy_status; then
        echo ""
        log_info "Vault Proxy is already running."
        echo "To stop: ./stop-proxy.sh"
        exit 0
    fi
    
    # 2. Start Vault Proxy
    start_proxy
    
    # 3. Verify status
    verify_proxy
    
    echo ""
    echo "============================================================================="
    log_success "Vault Proxy started!"
    echo "============================================================================="
    echo ""
    echo "Next steps:"
    echo "1. Test script: ../get_kv_secret.sh (modify port to 8400)"
    echo "2. Stop Proxy: ./stop-proxy.sh"
    echo ""
    echo "Notes:"
    echo "- Vault Proxy runs in the background"
    echo "- Use ./stop-proxy.sh to stop it"
}

# Execute script
main "$@"
