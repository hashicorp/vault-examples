# C Vault Client Application

`vault-app` is a Vault client application implemented in C. It supports KV, Database Dynamic, and Database Static secret engines, and provides real-time secret renewal and caching features.

This example demonstrates how to integrate with Vault using Direct Vault API Integration (Option 1), which is the recommended approach for new applications.

## Overview

### Purpose and Usage Scenarios

- The example provides scenarios for using KV, Database Dynamic, and Database Static secrets
- If needed only for initial application startup, it makes an API call once and then utilizes the cache for subsequent runs to reduce memory usage
- The example is implemented to periodically fetch and renew secrets

### Key Features

- **Multi-Secret Engine Support**: KV v2, Database Dynamic, Database Static
- **Real-time Renewal**: Automatic secret renewal via background threads
- **Efficient Caching**: Version-based KV caching, TTL-based Database caching
- **Automatic Token Renewal**: Automatic token renewal at the 4/5 point of TTL
- **Metadata Display**: Provides useful information like version, TTL, etc.
- **Security**: Entity-based permission management and secure memory handling

## Integration Approach

This example uses **Direct Vault API Integration**, which means the application communicates directly with the Vault server to fetch secrets.

### Authentication Process

1. **AppRole Authentication**: The application logs into Vault using Role ID + Secret ID
   - `role_id`: The application's identifier (public)
   - `secret_id`: The application's password (private)

2. **Token Issuance**: Upon successful login, Vault issues a temporary token
   - This token is used to access secrets
   - The token expires after a certain period for security

3. **Token Renewal**: The token must be renewed before it expires
   - Code for automatic renewal is implemented in background threads
   - Token renewal occurs at 4/5 of TTL (80% point)

### Operational Sequence

The application follows this sequence:

1. **Application Initialization**
   - Load configuration from `config.ini`
   - Initialize Vault client

2. **Vault Authentication**
   - Authenticate with Vault using AppRole (Role ID + Secret ID)
   - Receive client token and TTL information

3. **Token Management**
   - Background thread checks token status every 10 seconds
   - Renews token when 4/5 of TTL has passed
   - Handles token renewal failures

4. **Secret Retrieval**
   - **KV Secrets**: Version-based caching (renews only when version changes)
   - **Database Dynamic**: TTL-based caching (renews when TTL is 10 seconds or less)
   - **Database Static**: Time-based caching (renews every 5 minutes)

5. **Background Renewal**
   - Separate threads handle renewal for each secret type
   - Automatic refresh based on configuration

## Vault Development Server Setup

Before running this example, you need to set up a Vault development server. See the [Vault Development Server Setup Guide](../README.md#vault-development-server-setup) in the parent directory, or use the provided setup script:

```bash
cd ..
./setup-vault-for-my-vault-app.sh
```

### Quick Setup Steps

1. **Run Vault in Development Mode**
   ```bash
   vault server -dev -dev-root-token-id="root"
   ```

2. **Set Environment Variables**
   ```bash
   export VAULT_ADDR='http://127.0.0.1:8200'
   export VAULT_TOKEN='root'
   ```

3. **Enable AppRole and Configure**
   - Enable AppRole authentication
   - Create Entity and AppRole
   - Configure policies with Entity-based templating
   - Enable KV v2 and Database secret engines

See the setup script or the parent README for detailed instructions.

## Quick Start

### 1. Install Required Libraries

**macOS (Homebrew)**:
```bash
brew install curl json-c
```

**Ubuntu/Debian**:
```bash
sudo apt-get install libcurl4-openssl-dev libjson-c-dev
```

**CentOS/RHEL**:
```bash
sudo yum install libcurl-devel json-c-devel
```

### 2. Build and Run

```bash
# Build
make clean && make

# Run
./vault-app

# Run with a custom config file
./vault-app custom-config.ini
```

### 3. Configure the Configuration File

Modify the `config.ini` file to set up your Vault connection information:

```ini
[vault]
entity = my-vault-app
url = http://127.0.0.1:8200
namespace = 
role_id = your-role-id-here
secret_id = your-secret-id-here

[secret-kv]
enabled = true
kv_path = database
refresh_interval = 5

[secret-database-dynamic]
enabled = true
role_id = db-demo-dynamic

[secret-database-static]
enabled = true
role_id = db-demo-static

[http]
timeout = 30
max_response_size = 4096
```

## Example Output

```
=== Vault C Client Application ===
Loading configuration from: config.ini
=== Application Configuration ===
Vault URL: http://127.0.0.1:8200
Vault Namespace: (empty)
Entity: my-vault-app
Vault Role ID: 7fb49dd0-4b87-19cd-7b72-a7e21e5c543e
Vault Secret ID: 475a6500-f9f8-fdd4-ec30-54fadcad926e

--- Secret Engines ---
KV Engine: enabled
  KV Path: database
  Refresh Interval: 5 seconds
Database Dynamic: enabled
  Role ID: db-demo-dynamic
Database Static: enabled
  Role ID: db-demo-static

--- HTTP Settings ---
HTTP Timeout: 30 seconds
Max Response Size: 4096 bytes
=====================================
Logging in to Vault...
Token TTL from Vault: 60 seconds
Login successful. Token expires in 60 seconds
Token status: 60 seconds remaining (expires in 1 minutes)
✅ Token is healthy (at 0% of TTL)
✅ KV refresh thread started (interval: 5 seconds)
✅ Database Dynamic refresh thread started (interval: 5 seconds)
✅ Database Static refresh thread started (interval: 10 seconds)

=== Fetching Secret ===
📦 KV Secret Data (version: 10):
{ "api_key": "myapp-api-key-123456", "database_url": "mysql://@localhost:3306/myappdb" }

🗄️ Database Dynamic Secret (TTL: 59 seconds):
  username: v-approle-db-demo-dy-0x50Hgcj5Mj
  password: AdCNFYg6wDV6p8fz-byK

🔒 Database Static Secret (TTL: 2412 seconds):
  username: my-vault-app-static
  password: sntZ-lhR2rZ9GLjgGvry

--- Token Status ---
Token status: 60 seconds remaining (expires in 1 minutes)
✅ Token is healthy (at 0% of TTL)
```

## Project Structure

```
c/
├── src/
│   ├── main.c              # Main application and thread management
│   ├── vault_client.h      # Vault client header
│   ├── vault_client.c      # Vault client implementation
│   └── config.c            # INI file parsing
├── config.h                # Configuration structure definition
├── config.ini              # Application configuration file
├── Makefile                # Build script
└── README.md               # This file
```

## Configuration Options

### Vault Settings (`[vault]`)
- `entity`: Entity name (required)
- `url`: Vault server address
- `namespace`: Vault namespace (optional)
- `role_id`: AppRole Role ID
- `secret_id`: AppRole Secret ID

### KV Secret Settings (`[secret-kv]`)
- `enabled`: Whether the KV engine is enabled
- `kv_path`: KV secret path
- `refresh_interval`: Refresh interval (seconds)

### Database Dynamic Settings (`[secret-database-dynamic]`)
- `enabled`: Whether the Database Dynamic engine is enabled
- `role_id`: Database Dynamic Role ID

### Database Static Settings (`[secret-database-static]`)
- `enabled`: Whether the Database Static engine is enabled
- `role_id`: Database Static Role ID

### HTTP Settings (`[http]`)
- `timeout`: HTTP request timeout (seconds)
- `max_response_size`: Maximum response size (bytes)

## Architecture

### Thread Structure
- **Main Thread**: Fetches and prints secrets
- **Token Renewal Thread**: Checks token status every 10 seconds, renews at 4/5 of TTL
- **KV Renewal Thread**: Renews KV secrets at the configured interval
- **Database Dynamic Renewal Thread**: Renews Dynamic secrets at the configured interval
- **Database Static Renewal Thread**: Renews Static secrets at double the interval

### Caching Strategy
- **KV Secret**: Version-based caching (renews only when the version changes)
- **Database Dynamic**: TTL-based caching (renews when TTL is 10 seconds or less)
- **Database Static**: Time-based caching (renews every 5 minutes)

### Security Features
- **Entity-based Permissions**: Uses `{entity}-{engine}` path patterns
- **Automatic Token Renewal**: Automatically renews tokens before expiration
- **Memory Security**: Cleans up secret data immediately after use
- **Error Handling**: Retries on network errors or token expiration

## Developer Guide

### Core Implementation Points

**1. Memory Management**
```c
// Correct way: Create and clean up CURL handle
CURL *curl = curl_easy_init();
// ... process request ...
curl_easy_cleanup(curl);

// Manage JSON object reference count
*secret_data = json_object_get(data_obj);
// ... after use ...
vault_cleanup_secret(secret_data);
```

**2. Token Renewal Logic**
```c
// Renew at 4/5 point (when 80% of token TTL has passed)
time_t renewal_point = total_ttl * 4 / 5;
if (elapsed >= renewal_point) {
    vault_renew_token(client);
}
```

**3. Error Handling**
```c
// Re-login if token renewal fails
if (vault_renew_token(client) != 0) {
    if (vault_login(client, role_id, secret_id) != 0) {
        should_exit = 1;  // Exit if re-login also fails
    }
}
```

### Key Functions

**Vault Client Functions**
- `vault_client_init()`: Initializes the client
- `vault_login()`: Logs in with AppRole
- `vault_renew_token()`: Renews the token
- `vault_get_kv_secret()`: Fetches a KV secret
- `vault_get_db_dynamic_secret()`: Fetches a Database Dynamic secret
- `vault_get_db_static_secret()`: Fetches a Database Static secret

**Cache Management Functions**
- `vault_refresh_kv_secret()`: Renews a KV secret
- `vault_refresh_db_dynamic_secret()`: Renews a Database Dynamic secret
- `vault_refresh_db_static_secret()`: Renews a Database Static secret

## Troubleshooting

### Build Errors
- **Missing Libraries**: `brew install curl json-c` (macOS)
- **Path Issues**: Check include paths in the Makefile
- **Permission Issues**: Grant execute permission to the binary

### Runtime Errors
- **Vault Connection Failure**: Check Vault server status and URL
- **Authentication Failure**: Verify Role ID and Secret ID
- **Permission Errors**: Check Entity policies and path permissions

### Performance Optimization
- **Memory Usage**: Prevent unnecessary secret renewals
- **Network Calls**: Optimize caching strategy
- **Thread Management**: Set appropriate renewal intervals

## References

- [Vault API Documentation](https://developer.hashicorp.com/vault/api-docs)
- [Database Secrets Engine](https://developer.hashicorp.com/vault/api-docs/secret/databases)
- [KV Secrets Engine](https://developer.hashicorp.com/vault/api-docs/secret/kv)
- [AppRole Auth Method](https://developer.hashicorp.com/vault/api-docs/auth/approle)
