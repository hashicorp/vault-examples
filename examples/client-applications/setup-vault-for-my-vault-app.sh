#!/bin/bash

# =============================================================================
# Vault Development Server Auto-Configuration Script
# =============================================================================
# This script automates all settings for Vault development server configuration
# 
# Usage:
#   ./setup-vault-for-my-vault-app.sh
#
# Prerequisites:
#   - Vault must be running (vault server -dev)
#   - Docker must be installed (for MySQL container)
#   - vault CLI must be in PATH
# =============================================================================

set -e  # Exit on error

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

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check Vault connection
check_vault_connection() {
    log_info "Checking Vault connection..."
    
    if ! vault status > /dev/null 2>&1; then
        log_error "Cannot connect to Vault server."
        log_error "Please start Vault development server first with:"
        log_error "  vault server -dev -dev-root-token-id=\"root\""
        exit 1
    fi
    
    log_success "Vault server connection verified"
}

# Setup environment variables
setup_environment() {
    log_info "Setting up Vault environment variables..."
    
    export VAULT_ADDR='http://127.0.0.1:8200'
    export VAULT_TOKEN='root'
    
    log_success "Environment variables set"
}

# Enable AppRole authentication
enable_approle() {
    log_info "Enabling AppRole authentication..."
    
    if vault auth list | grep -q "approle/"; then
        log_warning "AppRole is already enabled."
    else
        vault auth enable approle
        log_success "AppRole authentication enabled"
    fi
}

# Create Entity-based policy
create_policy() {
    log_info "Creating Entity-based template policy..."
    
    vault policy write myapp-templated-policy - <<EOF
# App-specific secret paths (based on identity.entity.name)
path "{{identity.entity.name}}-kv/data/*" {
  capabilities = ["read", "list"]
}

path "{{identity.entity.name}}-database/creds/*" {
  capabilities = ["read", "list", "create", "update"]
}

path "{{identity.entity.name}}-database/static-creds/*" {
  capabilities = ["read", "list"]
}

# Token renewal permission
path "auth/token/renew-self" {
  capabilities = ["update"]
}

# Token lookup permission
path "auth/token/lookup-self" {
  capabilities = ["read"]
}

# Lease lookup permission (for Database Dynamic secret TTL check)
path "sys/leases/lookup" {
  capabilities = ["update"]
}

# Lease renewal permission (for Database Dynamic secret renewal)
path "sys/leases/renew" {
  capabilities = ["update"]
}

# SSH OTP permission
path "{{identity.entity.name}}-ssh-otp/creds/*" {
  capabilities = ["read", "create", "update"]
}

# SSH CA permission
path "{{identity.entity.name}}-ssh-ca/sign/*" {
  capabilities = ["read", "create", "update"]
}
EOF
    
    log_success "Policy created"
}

# Create Entity
create_entity() {
    log_info "Creating Entity..."
    
    # Create Entity
    vault write identity/entity name="my-vault-app" policies="myapp-templated-policy"
    
    # Extract Entity ID
    ENTITY_ID=$(vault read -field=id /identity/entity/name/my-vault-app)
    echo "ENTITY_ID=$ENTITY_ID" > .vault-setup.env
    
    log_success "Entity created (ID: $ENTITY_ID)"
}

# Setup AppRole
setup_approle() {
    log_info "Setting up AppRole..."
    
    # Extract AppRole Accessor ID
    APPROLE_ACCESSOR=$(vault read -field=accessor sys/auth/approle)
    echo "APPROLE_ACCESSOR=$APPROLE_ACCESSOR" >> .vault-setup.env
    
    # Create AppRole
    vault write auth/approle/role/my-vault-app \
        secret_id_ttl=1h \
        token_ttl=0 \
        token_max_ttl=0 \
        period=1m \
        orphan=true
    
    log_success "AppRole configured"

    ROLE_ID=$(vault read -field=role_id auth/approle/role/my-vault-app/role-id)
    log_info "Role ID: $ROLE_ID"
    echo "ROLE_ID=$ROLE_ID" >> .vault-setup.env
}

# Create Entity Alias (link AppRole and Entity)
create_entity_alias() {
    log_info "Creating Entity Alias..."
    
    # Load environment variables
    source .vault-setup.env
    
    # Create Entity Alias
    vault write identity/entity-alias \
        name="$ROLE_ID" \
        canonical_id="$ENTITY_ID" \
        mount_accessor="$APPROLE_ACCESSOR"
    
    log_success "Entity Alias created"
}

# Enable KV secrets engine
enable_kv_secrets() {
    log_info "Enabling KV secrets engine..."
    
    if vault secrets list | grep -q "my-vault-app-kv/"; then
        log_warning "KV engine is already enabled."
    else
        vault secrets enable -path=my-vault-app-kv kv-v2
        log_success "KV engine enabled"
    fi
    
    # Create example secret data
    log_info "Creating example secret data..."

    vault kv put my-vault-app-kv/database \
        api_key="myapp-api-key-123456" \
        database_url="mysql://localhost:3306/mydb" \
        database_username="root" \
        database_password="password"

    vault kv put my-vault-app-kv/ssh/10.10.0.222 \
        ssh_username="test" \
        ssh_password="password"
    
    # Additional SSH host example
    vault kv put my-vault-app-kv/ssh/192.168.0.47 \
        ssh_username="vault-test" \
        ssh_password="test-password"
    
    log_success "KV secret data created"
}

# Setup MySQL container
setup_mysql() {
    log_info "Setting up MySQL container..."
    
    # Check if container already exists
    if docker ps -a | grep -q "my-vault-app-mysql"; then
        log_warning "MySQL container already exists."
        if ! docker ps | grep -q "my-vault-app-mysql"; then
            docker start my-vault-app-mysql

            log_info "Starting MySQL container..."
            sleep 10
        fi
    else
        log_info "Creating MySQL container..."
        docker run --name my-vault-app-mysql -e MYSQL_ROOT_PASSWORD=password -d -p 3306:3306 mysql:9
        
        # Wait for MySQL to start
        log_info "Waiting for MySQL to start..."
        sleep 10
    fi
    
    # Create MySQL database and user
    log_info "Creating MySQL database and user..."
    mysql -u root -ppassword -h 127.0.0.1 -P 3306 --protocol=TCP -e "
        CREATE DATABASE IF NOT EXISTS mydb;
        CREATE USER IF NOT EXISTS 'my-vault-app-static'@'%' IDENTIFIED BY 'password';
        GRANT ALL PRIVILEGES ON *.* TO 'my-vault-app-static'@'%';
        FLUSH PRIVILEGES;
    " 2>/dev/null || {
        log_warning "Failed to create MySQL database and user (MySQL may not have started yet)"
        log_info "Please run the following command manually:"
        log_info "mysql -u root -ppassword -h 127.0.0.1 -P 3306 --protocol=TCP -e \"CREATE DATABASE IF NOT EXISTS mydb; CREATE USER 'my-vault-app-static'@'%' IDENTIFIED BY 'password'; GRANT ALL PRIVILEGES ON *.* TO 'my-vault-app-static'@'%'; FLUSH PRIVILEGES;\""
    }
    
    log_success "MySQL setup completed"
}

# Enable Database secrets engine
enable_database_secrets() {
    log_info "Enabling Database secrets engine..."
    
    if vault secrets list | grep -q "my-vault-app-database/"; then
        log_warning "Database engine is already enabled."
    else
        vault secrets enable -path=my-vault-app-database database
        log_success "Database engine enabled"
    fi
    
    # Configure Database secrets engine
    log_info "Configuring Database secrets engine..."
    vault write my-vault-app-database/config/mysql-demo \
        plugin_name=mysql-database-plugin \
        connection_url="{{username}}:{{password}}@tcp(localhost:3306)/" \
        allowed_roles="*" \
        username="root" \
        password="password"
    
    # Create Dynamic Role (1 minute for testing)
    vault write my-vault-app-database/roles/db-demo-dynamic \
        db_name=mysql-demo \
        creation_statements="CREATE USER '{{username}}'@'%' IDENTIFIED BY '{{password}}'; GRANT ALL PRIVILEGES ON *.* TO '{{username}}'@'%';" \
        default_ttl="1m" \
        max_ttl="24h"
    
    # Create Static Role
    vault write my-vault-app-database/static-roles/db-demo-static \
        db_name=mysql-demo \
        username=my-vault-app-static \
        rotation_schedule="0 * * * *"
    
    log_success "Database secrets engine configured"
}

# Enable SSH Secrets Engine (OTP)
enable_ssh_otp() {
    log_info "Enabling SSH OTP Secrets Engine..."
    
    if vault secrets list | grep -q "my-vault-app-ssh-otp/"; then
        log_warning "SSH OTP engine is already enabled."
    else
        vault secrets enable -path=my-vault-app-ssh-otp ssh
        log_success "SSH OTP engine enabled"
    fi
    
    # Create OTP Role
    log_info "Creating SSH OTP Role..."
    vault write my-vault-app-ssh-otp/roles/otp-role \
        key_type=otp \
        allowed_users=test1,test2 \
        default_user=test1 \
        cidr_list=0.0.0.0/0
    
    log_success "SSH OTP Role created"
}

# Enable SSH Secrets Engine (CA)
enable_ssh_ca() {
    log_info "Enabling SSH CA Secrets Engine..."
    
    if vault secrets list | grep -q "my-vault-app-ssh-ca/"; then
        log_warning "SSH CA engine is already enabled."
    else
        vault secrets enable -path=my-vault-app-ssh-ca ssh
        log_success "SSH CA engine enabled"
    fi
    
    # Generate CA key
    log_info "Generating SSH CA key..."
    vault delete my-vault-app-ssh-ca/config/ca
    vault write my-vault-app-ssh-ca/config/ca generate_signing_key=true
    
    # Create Client Signer Role
    log_info "Creating SSH Client Signer Role..."
    vault write my-vault-app-ssh-ca/roles/client-signer - <<-EOF
    {
        "key_type": "ca",
        "allow_user_certificates": true,
        "allowed_users": "*",
        "allowed_extensions": "permit-pty,permit-port-forwarding",
        "default_extensions": {
            "permit-pty":""
        },
        "ttl": "20s",
        "max_ttl": "20s"
    }
EOF
    
    log_success "SSH CA Role created"
}

# Verify setup
verify_setup() {
    log_info "Verifying setup..."
    
    echo ""
    log_info "=== Checking Vault status ==="
    vault status
    
    echo ""
    log_info "=== Checking authentication methods ==="
    vault auth list
    
    echo ""
    log_info "=== Checking secret engines ==="
    vault secrets list
    
    echo ""
    log_info "=== Checking policies ==="
    vault policy list
    
    echo ""
    log_info "=== Checking Entity ==="
    vault list identity/entity/name 2>/dev/null || vault read identity/entity/name/my-vault-app
    
    echo ""
    log_info "=== Checking AppRole configuration ==="
    vault read auth/approle/role/my-vault-app
    
    echo ""
    log_info "=== Testing KV secret ==="
    vault kv get my-vault-app-kv/database
    
    echo ""
    log_info "=== Testing Database Dynamic Role ==="
    vault read my-vault-app-database/creds/db-demo-dynamic
    
    echo ""
    log_info "=== Testing Database Static Role ==="
    vault read my-vault-app-database/static-creds/db-demo-static
    
    echo ""
    log_info "=== Checking SSH OTP Role ==="
    vault read my-vault-app-ssh-otp/roles/otp-role
    
    echo ""
    log_info "=== Checking SSH CA Role ==="
    vault read my-vault-app-ssh-ca/roles/client-signer
    
    echo ""
    log_info "=== Checking SSH CA Public Key ==="
    vault read -field=public_key my-vault-app-ssh-ca/config/ca
    
    log_success "Setup verification completed"
}

# Update config.ini instructions
update_config_ini() {
    log_info "Providing config.ini update instructions..."

    echo ""
    log_info "=== config.ini file update required ==="
    echo ""
    echo "Run the following commands to update the config.ini file:"
    echo ""
    echo "  # Check Role ID"
    echo "  vault read -field=role_id auth/approle/role/my-vault-app/role-id"
    echo ""
    echo "  # Check Secret ID"
    echo "  vault write -field=secret_id -f auth/approle/role/my-vault-app/secret-id"
    echo ""
    echo "Or manually set the following values in config.ini:"
    echo "  role_id = <output Role ID>"
    echo "  secret_id = <output Secret ID>"
    echo ""
    log_success "config.ini update instructions provided"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up temporary files..."
    rm -f .vault-setup.env
    log_success "Cleanup completed"
}

# Main execution function
main() {
    echo "============================================================================="
    echo "🏗️  Vault Development Server Auto-Configuration Script"
    echo "============================================================================="
    echo ""
    
    # 1. Check Vault connection
    check_vault_connection
    
    # 2. Setup environment variables
    setup_environment
    
    # 3. Enable AppRole authentication
    enable_approle
    
    # 4. Create Entity-based policy
    create_policy
    
    # 5. Create Entity
    create_entity
    
    # 6. Setup AppRole
    setup_approle
    
    # 7. Create Entity Alias
    create_entity_alias
    
    # 8. Enable KV secrets engine
    enable_kv_secrets
    
    # 9. Setup MySQL (optional)
    if command -v docker >/dev/null 2>&1; then
        setup_mysql
        enable_database_secrets
    else
        log_warning "Docker is not installed. Skipping Database secrets engine."
    fi
    
    # 10. Setup SSH OTP
    enable_ssh_otp
    
    # 11. Setup SSH CA
    enable_ssh_ca
    
    # 10. Verify setup
    verify_setup
    
    # 11. Update config.ini
    update_config_ini
    
    # 12. Cleanup
    cleanup
    
    echo ""
    echo "============================================================================="
    log_success "🎉 Vault development server setup completed!"
    echo "============================================================================="
    echo ""
    echo "Next steps:"
    echo "1. Update config.ini file (run the commands shown above)"
    echo "2. Run example applications:"
    echo "   - C application: cd c && make && ./vault-app"
    echo "   - C++ application: cd cpp && mkdir build && cd build && cmake .. && make && ./vault-app"
    echo "   - Java application: cd java-pure && mvn clean package && java -jar target/vault-java-app.jar"
    echo "   - Python application: cd python && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && python vault_app.py"
    echo "   - Spring Boot web application: cd java-web-springboot && ./gradlew bootRun"
    echo "     (Access in web browser: http://localhost:8080/vault-web)"
    echo ""
    echo "SSH setup:"
    echo "- SSH OTP: See script-sample/get_ssh_otp_proxy.sh"
    echo "- SSH CA: See script-sample/get_ssh_signed_cert_proxy.sh"
    echo "- SSH target host configuration is required (modify <host> placeholder in scripts)"
    echo ""
    echo "Notes:"
    echo "- This setup is for development environment only"
    echo "- All data will be lost when Vault server is restarted"
    echo "- MySQL container must be stopped manually: docker stop my-vault-app-mysql"
    echo "- When creating multiple apps, update each app's config.ini individually"
    echo ""
}

# Execute script
main "$@"
