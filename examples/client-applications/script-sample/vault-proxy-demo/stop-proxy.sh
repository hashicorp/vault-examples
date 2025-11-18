#!/bin/bash

# =============================================================================
# Vault Proxy Stop Script
# =============================================================================
# This script stops the running Vault Proxy.
# =============================================================================

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration files
PID_FILE="./vault-proxy.pid"
LOG_FILE="./vault-proxy.log"
TOKEN_FILE="./token"

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

# Stop Vault Proxy
stop_proxy() {
    if [ ! -f "$PID_FILE" ]; then
        log_warning "PID file not found. Vault Proxy may not be running."
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    
    if ! ps -p "$PID" >/dev/null 2>&1; then
        log_warning "Process with PID $PID is not running."
        rm -f "$PID_FILE"
        return 1
    fi
    
    log_info "Stopping Vault Proxy... (PID: $PID)"
    
    # Terminate process
    kill "$PID"
    
    # Wait for termination (max 10 seconds)
    for i in {1..10}; do
        if ! ps -p "$PID" >/dev/null 2>&1; then
            log_success "Vault Proxy stopped"
            rm -f "$PID_FILE"
            return 0
        fi
        sleep 1
    done
    
    # Force kill
    log_warning "Normal termination failed, attempting force kill..."
    kill -9 "$PID" 2>/dev/null
    
    if ! ps -p "$PID" >/dev/null 2>&1; then
        log_success "Vault Proxy force killed"
        rm -f "$PID_FILE"
        return 0
    else
        log_error "Vault Proxy termination failed"
        return 1
    fi
}

# Cleanup tasks
cleanup() {
    log_info "Performing cleanup..."
    
    # Clean up PID file
    if [ -f "$PID_FILE" ]; then
        rm -f "$PID_FILE"
        log_info "PID file cleaned up"
    fi
    
    # Clean up token file (optional)
    if [ -f "$TOKEN_FILE" ]; then
        log_info "Token file remains: $TOKEN_FILE"
        log_info "For security, please delete manually: rm $TOKEN_FILE"
    fi
    
    log_success "Cleanup completed"
}

# Main execution
main() {
    echo "============================================================================="
    echo "🛑 Vault Proxy Stop Script"
    echo "============================================================================="
    echo ""
    
    # 1. Stop Vault Proxy
    if stop_proxy; then
        echo ""
        # 2. Cleanup
        cleanup
        
        echo ""
        echo "============================================================================="
        log_success "Vault Proxy stopped!"
        echo "============================================================================="
        echo ""
        echo "Cleaned up files:"
        echo "- PID file: $PID_FILE"
        echo ""
        echo "Remaining files:"
        echo "- Log file: $LOG_FILE (can be deleted manually)"
        echo "- Token file: $TOKEN_FILE (recommended to delete manually for security)"
    else
        echo ""
        echo "============================================================================="
        log_error "Vault Proxy stop failed"
        echo "============================================================================="
        echo ""
        echo "Please check manually:"
        echo "1. ps aux | grep vault"
        echo "2. netstat -tlnp | grep 8400"
        exit 1
    fi
}

# Execute script
main "$@"
