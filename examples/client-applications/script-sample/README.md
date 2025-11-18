# Script Sample with Vault Proxy

This directory contains script examples that use Vault Proxy to retrieve secrets using curl. These scripts demonstrate how to integrate with Vault when token management is difficult to implement (e.g., in shell scripts).

## Overview

### Purpose and Usage Scenarios

These scripts demonstrate how to retrieve secrets from Vault using **Vault Proxy** (Option 2), which is useful when:
- Token management with multi-threading is difficult to implement in scripts
- Managing elements required for Vault login (e.g., AppRole Secret_id, Password) is difficult
- You want to simplify application code by handling authentication/token management in the proxy

### Integration Approach

This example uses **Vault Proxy**, which is an intermediary server that sits between the application and Vault.

**Differences from Direct API Integration**:
- **Application's Role**: Requests secrets from the Proxy
- **Proxy's Role**: Fetches secrets from Vault and delivers them to the application
- **Advantage**: Eliminates the need for complex authentication/token management code in the application

**Using Vault Proxy**:
```bash
# Very simple code
curl http://vault-proxy:8400/v1/kv-demo/data/db
```

The proxy handles complex authentication processes (AppRole login, token renewal), so scripts can retrieve secrets with simple HTTP requests.

## Script List

### Vault Proxy Integration Scripts (Recommended)

#### 1. `get_kv_secret_proxy.sh` - Get KV Secret (Proxy)
- **Purpose**: Retrieve static key-value secrets via Vault Proxy
- **Path**: `my-vault-app-kv/data/database`
- **Output**: API key, database URL, metadata

#### 2. `get_db_dynamic_secret_proxy.sh` - Get Database Dynamic Secret (Proxy)
- **Purpose**: Retrieve dynamic database credentials via Vault Proxy
- **Path**: `my-vault-app-database/creds/db-demo-dynamic`
- **Output**: Temporary username, password, Lease information

#### 3. `get_db_static_secret_proxy.sh` - Get Database Static Secret (Proxy)
- **Purpose**: Retrieve static database credentials via Vault Proxy
- **Path**: `my-vault-app-database/static-creds/db-demo-static`
- **Output**: Fixed username, password, TTL information

#### 4. `get_ssh_kv_proxy.sh` - Get SSH KV Credentials (Proxy)
- **Purpose**: Retrieve KV-based SSH credentials via Vault Proxy and connect
- **Path**: `my-vault-app-kv/ssh/<hostIP>`
- **Output**: SSH credential information, automatic connection (using sshpass)
- **Arguments**: hostIP (optional, default: 10.10.0.222)

#### 5. `get_ssh_otp_proxy.sh` - Generate SSH OTP (Proxy)
- **Purpose**: Generate SSH OTP via Vault Proxy and manual connection guide
- **Path**: `my-vault-app-ssh-otp/creds/otp-role`
- **Output**: One-time OTP key, username, host information, SSH connection command

#### 6. `get_ssh_signed_cert_proxy.sh` - Generate SSH Signed Certificate (Proxy)
- **Purpose**: Generate SSH Signed Certificate via Vault Proxy and save
- **Path**: `my-vault-app-ssh-ca/sign/client-signer`
- **Output**: Signed SSH certificate, serial number, SSH connection command
- **Prerequisites**: SSH server needs CA Public Key registered

### AWS Credential Scripts

#### 7. `get_aws_userpass.sh` - Get AWS Credentials (Userpass)
- **Purpose**: Retrieve AWS credentials and update credentials file
- **Authentication**: Userpass method
- **Output**: AWS Access Key, Secret Key, Session Token

#### 8. `get_aws_oidc.sh` - Get AWS Credentials (OIDC)
- **Purpose**: Retrieve AWS credentials and update credentials file
- **Authentication**: OIDC method
- **Output**: AWS Access Key, Secret Key, Session Token

### Vault Proxy Demo Environment

#### 9. `vault-proxy-demo/` - Vault Proxy Demo Environment
- **Purpose**: Run and manage Vault Proxy
- **Includes**: Configuration file, start/stop scripts, usage guide
- **Features**: Uses root token, port 8400

## Usage

### Vault Proxy Integration (Recommended)

#### Prerequisites
1. **Vault Server Running**: Vault development server must be running at `http://127.0.0.1:8200`
2. **Vault Server Setup**: Vault server must be configured using `setup-vault-for-my-vault-app.sh`
3. **jq Installation**: jq must be installed for JSON parsing

#### Vault Proxy Setup and Start

```bash
# Navigate to Vault Proxy demo environment
cd vault-proxy-demo

# Create token file
./setup-token.sh

# Start Vault Proxy
./start-proxy.sh
```

#### Run Scripts

```bash
# Move to parent directory
cd ..

# Get KV Secret
./get_kv_secret_proxy.sh

# Get Database Dynamic Secret
./get_db_dynamic_secret_proxy.sh

# Get Database Static Secret
./get_db_static_secret_proxy.sh

# Get SSH KV credentials and connect
./get_ssh_kv_proxy.sh                    # Use default host
./get_ssh_kv_proxy.sh 192.168.0.47       # Specify host

# Generate SSH OTP (manual connection)
./get_ssh_otp_proxy.sh

# Generate SSH Signed Certificate
./get_ssh_signed_cert_proxy.sh
```

#### Stop Vault Proxy

```bash
cd vault-proxy-demo
./stop-proxy.sh
```

### AWS Credential Retrieval

```bash
# Get AWS Credentials (Userpass authentication)
./get_aws_userpass.sh

# Get AWS Credentials (OIDC authentication)
./get_aws_oidc.sh
```

## Configuration

### Vault Server Address
- **Direct Integration**: `http://127.0.0.1:8200`
- **Proxy Integration**: `http://127.0.0.1:8400`

### Secret Paths
- **KV**: `my-vault-app-kv/data/database`
- **Database Dynamic**: `my-vault-app-database/creds/db-demo-dynamic`
- **Database Static**: `my-vault-app-database/static-creds/db-demo-static`

### Port Configuration
- **Vault Server**: 8200 (for direct integration)
- **Vault Proxy**: 8400 (for proxy integration)
- **Conflict Prevention**: Other ports can be used

## Features

### Common Features
- **No Vault CLI Required**: Uses pure curl
- **Vault Proxy Integration**: Uses already authenticated Proxy
- **JSON Parsing**: Structured output using jq
- **Color Output**: Color logs for better readability
- **Error Handling**: Simple error handling based on HTTP status codes

### KV Secret Scripts
- Output secret data and metadata
- Display version information and creation time

### Database Dynamic Scripts
- Output temporary credential information
- Provide Lease ID and TTL information
- Provide MySQL connection example commands

### Database Static Scripts
- Output fixed credential information
- Provide TTL information and explain Static vs Dynamic differences
- Provide MySQL connection example commands

## Vault Development Server Setup

Before running these scripts, you need to set up a Vault development server. See the [Vault Development Server Setup Guide](../README.md#vault-development-server-setup) in the parent directory, or use the provided setup script:

```bash
cd ..
./setup-vault-for-my-vault-app.sh
```

## Important Notes

1. **Vault Proxy Authentication**: Scripts assume Vault Proxy is already authenticated
2. **Network Connection**: Network connection to Vault Proxy is required
3. **jq Dependency**: jq must be installed for JSON parsing
4. **Permissions**: Vault Proxy must have access permissions to the secret paths

## Troubleshooting

### Vault Proxy Connection Failure
```bash
# Check Vault Proxy status
curl -s http://127.0.0.1:8400/v1/sys/health
```

### jq Installation
```bash
# Ubuntu/Debian
sudo apt-get install jq

# CentOS/RHEL
sudo yum install jq

# macOS
brew install jq
```

### Permission Errors
Check if Vault Proxy has access permissions to the secrets.

### SSH Connection Failure
```bash
# Check SSH server configuration
ssh -v user@host  # Check connection process with detailed logs

# Enable password authentication on SSH server
sudo vim /etc/ssh/sshd_config
# Add PasswordAuthentication yes
sudo systemctl restart sshd
```

## Vault Proxy Configuration

The Vault Proxy configuration is in `vault-proxy-demo/vault-proxy.hcl`:

```hcl
listener "tcp" {
  address = "127.0.0.1:8400"
  tls_disable = true
}

vault {
  address = "http://127.0.0.1:8200"
}

cache {
  use_auto_auth_token = true
}
```

## References

- [Vault API Documentation](https://developer.hashicorp.com/vault/api-docs)
- [Vault Proxy](https://developer.hashicorp.com/vault/docs/agent-and-proxy/proxy)
- [AppRole Auth Method](https://developer.hashicorp.com/vault/api-docs/auth/approle)
- [Database Secrets Engine](https://developer.hashicorp.com/vault/api-docs/secret/databases)
- [KV Secrets Engine](https://developer.hashicorp.com/vault/api-docs/secret/kv)
- [SSH Secrets Engine](https://developer.hashicorp.com/vault/api-docs/secret/ssh)
- [AWS Secrets Engine](https://developer.hashicorp.com/vault/api-docs/secret/aws)
