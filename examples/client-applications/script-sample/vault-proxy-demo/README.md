# Vault Proxy Demo Environment

This directory contains a demo environment using Vault Proxy. Vault Proxy acts as an intermediary between Vault server and clients, handling complex authentication processes on their behalf.

## 📋 Overview

### What is Vault Proxy?
- **Role**: Intermediary server between Vault server and clients
- **Advantages**: No need for complex authentication on client side
- **Operation**: Proxy authenticates with Vault, clients only need to request from Proxy

### Demo Environment Features
- **Root Token Usage**: Root token used for demo purposes only
- **Port**: 8400 (Vault server: 8200)
- **Authentication**: Token file-based automatic authentication
- **Caching**: Secret caching for improved performance

## 🚀 Quick Start

### 1. Prerequisites
```bash
# Start Vault development server (in another terminal)
vault server -dev -dev-root-token-id="root"

# Setup Vault server (in another terminal)
cd /path/to/Development-Guide
./setup-vault-for-my-vault-app.sh
```

### 2. Vault Proxy Setup
```bash
# Create token file
./setup-token.sh

# Start Vault Proxy
./start-proxy.sh
```

### 3. Testing
```bash
# Check Vault Proxy status
curl http://127.0.0.1:8400/v1/sys/health

# Get KV secret (using script modified for port 8400)
../get_kv_secret_proxy.sh
```

### 4. Cleanup
```bash
# Stop Vault Proxy
./stop-proxy.sh
```

## 📁 File Structure

```
vault-proxy-demo/
├── vault-proxy.hcl       # Vault Proxy configuration file
├── setup-token.sh        # Token file creation script
├── start-proxy.sh        # Proxy startup script
├── stop-proxy.sh         # Proxy shutdown script
├── README.md             # This file
├── token                 # Root token file (auto-generated)
├── vault-proxy.pid       # PID file (auto-generated)
└── vault-proxy.log        # Log file (auto-generated)
```

## 🔧 Configuration File Description

### vault-proxy.hcl
```hcl
# Listener configuration (port 8400)
listener "tcp" {
  address = "127.0.0.1:8400"
  tls_disable = true
}

# Vault server connection (port 8200)
vault {
  address = "http://127.0.0.1:8200"
}

# Auto authentication (using token file)
auto_auth {
  method "token" {
    config = {
      token_file_path = "./token"
    }
  }
}

# Cache configuration
cache {
  use_auto_auth_token = true
}
```

## 🛠️ Script Usage

### setup-token.sh
- **Purpose**: Save root token to file
- **Execution**: `./setup-token.sh`
- **Result**: Creates `token` file

### start-proxy.sh
- **Purpose**: Start Vault Proxy in background
- **Execution**: `./start-proxy.sh`
- **Result**: Proxy runs on port 8400

### stop-proxy.sh
- **Purpose**: Stop Vault Proxy and cleanup
- **Execution**: `./stop-proxy.sh`
- **Result**: Proxy process terminated, files cleaned up

## 🔍 Testing Methods

### 1. Basic Connection Test
```bash
# Check Vault Proxy status
curl http://127.0.0.1:8400/v1/sys/health

# Direct Vault server connection (for comparison)
curl http://127.0.0.1:8200/v1/sys/health
```

### 2. Secret Retrieval Test
```bash
# Get KV secret
curl http://127.0.0.1:8400/v1/my-vault-app-kv/data/database

# Get Database Dynamic secret
curl http://127.0.0.1:8400/v1/my-vault-app-database/creds/db-demo-dynamic

# Get Database Static secret
curl http://127.0.0.1:8400/v1/my-vault-app-database/static-creds/db-demo-static
```

### 3. Script Testing
```bash
# Test with scripts modified for Proxy
# (Change port 8200 → 8400)
```

## ⚠️ Notes

### Security Considerations
- **Root Token**: For demo purposes only
- **Token File**: Be careful with security (chmod 600)
- **Production Environment**: Use appropriate authentication methods

### Port Conflicts
- **Vault Server**: 8200
- **Vault Proxy**: 8400
- **Conflict Prevention**: Other ports can be used

### File Cleanup
```bash
# Manual cleanup (if needed)
rm -f token vault-proxy.pid vault-proxy.log
```

## 🔧 Troubleshooting

### Vault Proxy Startup Failure
```bash
# Check logs
cat vault-proxy.log

# Check port usage
netstat -tlnp | grep 8400

# Check process
ps aux | grep vault
```

### Connection Failure
```bash
# Check Vault server status
curl http://127.0.0.1:8200/v1/sys/health

# Verify token validity
vault token lookup
```

### Permission Issues
```bash
# Check token file permissions
ls -la token

# Fix permissions
chmod 600 token
```

## 📚 Additional Information

### Vault Proxy vs Direct Connection
- **Direct Connection**: Complex authentication, token management required
- **Using Proxy**: Simple HTTP requests to retrieve secrets

### Caching Benefits
- **Performance**: Improved response speed through secret caching
- **Load**: Reduced load on Vault server
- **Stability**: Use cached data in case of network issues

### Production Environment Considerations
- **Authentication**: Use appropriate authentication methods (AppRole, LDAP, etc.)
- **Security**: TLS encryption, firewall configuration
- **Monitoring**: Log collection, metrics collection
- **High Availability**: Multiple proxies, load balancing
