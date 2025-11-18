# Python Vault Client Application

This is a Vault client application implemented in Python. It supports KV, Database Dynamic, and Database Static secret engines, and provides real-time secret renewal and caching features.

This example demonstrates how to integrate with Vault using Direct Vault API Integration (Option 1), which is the recommended approach for new applications.

## Overview

### Purpose and Usage Scenarios

This example is a reference application for Vault integration development.
- If needed only for initial application startup, it makes an API call once and then utilizes the cache for subsequent runs to reduce memory usage
- The example is implemented to periodically fetch and renew secrets
- It is designed using the hvac library rather than being implemented as a library solely for Vault

### Key Scenarios
- **Initial Startup**: Fetches secrets from Vault only once when the application starts
- **Real-time Renewal**: Periodically renews secrets to maintain the latest state
- **Cache Utilization**: Minimizes unnecessary API calls through version/TTL-based caching

### Supported Secret Types
- **KV v2**: Key-value store (version-based caching)
- **Database Dynamic**: Dynamic database credentials (TTL-based renewal)
- **Database Static**: Static database credentials (time-based caching)

### Key Features
- **Multi-Secret Engine Support**: KV v2, Database Dynamic, Database Static
- **Real-time Renewal**: Automatic secret renewal via background threads
- **Efficient Caching**: Version-based KV caching, TTL-based Database caching
- **Automatic Token Renewal**: Automatic token renewal at the 4/5 point of TTL
- **Environment Variable Override**: Supports runtime configuration override via environment variables
- **Virtual Environment Support**: Uses Python virtual environment for package management

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
   - Initialize Vault client using hvac library

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

## Quick Start

### 1. Prerequisites
- Python 3.7 or higher
- pip (Python package manager)
- Vault server (with development server setup completed)

### 2. Create Virtual Environment and Install Dependencies

```bash
# Create a Python virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install Python packages
pip install -r requirements.txt
```

**Note for macOS users**: 
You cannot install packages directly into the system Python environment on macOS. You must use a virtual environment.

### 3. Modify Configuration File

You can change the Vault connection settings by modifying the `config.ini` file.

### 4. Run the Application

```bash
# Run with the virtual environment activated
python vault_app.py

# Or run directly
python3 vault_app.py
```

### 5. Deactivate Virtual Environment

```bash
# Deactivate the virtual environment after you are done
deactivate
```

## Example Output

```
🚀 Starting Vault Python Client Application
✅ Vault login successful
⚙️ Current Configuration:
- Entity: my-vault-app
- Vault URL: http://127.0.0.1:8200
- KV Enabled: true
- Database Dynamic Enabled: true
- Database Static Enabled: true

📖 Example Purpose and Usage Scenarios
This example is a reference application for Vault integration development.
If needed only for initial application startup, it makes an API call once and then utilizes the cache for subsequent runs to reduce memory usage.
The example is implemented to periodically fetch and renew secrets.

🔧 Supported Features:
- KV v2 Secret Engine (version-based caching)
- Database Dynamic Secret Engine (TTL-based renewal)
- Database Static Secret Engine (time-based caching)
- Automatic Token Renewal
- Entity-based Permission Management

🔄 Starting secret renewal... (Press Ctrl+C to exit)

=== KV Secret Refresh ===
✅ KV secret fetch successful
📦 KV Secret Data:
{
  "api_key": "myapp-api-key-123456",
  "database_url": "mysql://localhost:3306/mydb"
}

=== Database Dynamic Secret Refresh ===
✅ Database Dynamic secret fetch successful (TTL: 60s)
🗄️ Database Dynamic Secret (TTL: 60s):
  username: v-approle-db-demo-dy-JRHTDBobE5o
  password: qLteLnVHZdBcmR-sJS1b

=== Database Static Secret Refresh ===
✅ Database Static secret fetch successful (TTL: 3600s)
🔒 Database Static Secret (TTL: 3600s):
  username: my-vault-app-static
  password: OfK6S-6R2PiWA0C8Fqxj
```

## Configuration Options

### Configuration Priority

Generally, predefined configurations are defined in the `config.ini` file. Since the `secret_id` used for Vault authentication expires after issuance, it is implemented to be overridden by an environment variable at runtime.

1. **Environment Variables** - Highest priority
2. **config.ini file** - Default value

### How to Use Environment Variables
```bash
# Override settings with environment variables at runtime
export VAULT_ROLE_ID=your-role-id
export VAULT_SECRET_ID=your-secret-id
export VAULT_URL=http://your-vault-server:8200
python vault_app.py

# Or individual settings
export VAULT_SECRET_ID=3ee5080b-c9b3-2714-799c-f8d45a715625
python vault_app.py
```

### Vault Server Settings
```ini
[vault]
# Entity name (required)
entity = my-vault-app
# Vault server address
url = http://127.0.0.1:8200
# Vault namespace (optional)
namespace = 
# AppRole authentication info (required)
role_id = 7fb49dd0-4b87-19cd-7b72-a7e21e5c543e
secret_id = 475a6500-f9f8-fdd4-ec30-54fadcad926e
```

### Secret Engine Settings
```ini
[kv_secret]
# KV Secret settings
enabled = true
path = database
refresh_interval = 5

[database_dynamic]
# Database Dynamic Secret settings
enabled = true
role_id = db-demo-dynamic

[database_static]
# Database Static Secret settings
enabled = true
role_id = db-demo-static
```

### HTTP Settings
```ini
[http]
# HTTP request timeout (seconds)
timeout = 30
# Maximum response size (bytes)
max_response_size = 4096
```

## Project Structure

```
python/
├── README.md                      # Usage guide
├── requirements.txt               # Python package dependencies
├── config.ini                     # Configuration file
├── vault_app.py                   # Main application
├── vault_client.py                # Vault client class
└── config_loader.py               # Configuration loader
```

## Architecture

### File Structure
```
python/
├── vault_app.py                   # Main application
├── vault_client.py                # Vault client
├── config_loader.py               # Configuration class
└── config.ini                     # Configuration file
```

### Key Components
- **VaultApplication**: Main application logic, scheduler management
- **VaultConfig**: Loads and manages configuration files
- **VaultClient**: Vault API integration, secret retrieval, caching using hvac library

### Caching Strategy
- **KV v2**: Version-based caching (5-minute interval)
- **Database Dynamic**: TTL-based caching (10-second threshold)
- **Database Static**: Time-based caching (5-minute interval)

### Real-time TTL Calculation
- Displays the real-time decrease of the TTL for Database Dynamic/Static Secrets
- Calculates the remaining TTL by subtracting the elapsed time from the cached TTL
- Prevents negative values with `max(0, remaining_ttl)`

### Security Features
- **Entity-based Permissions**: Uses `{entity}-{engine}` path patterns
- **Automatic Token Renewal**: Automatically renews tokens before expiration
- **Memory Security**: Cleans up secret data immediately after use
- **Error Handling**: Retries on network errors or token expiration

## Developer Guide

### 1. Understanding the Project Structure
```
python/
├── vault_app.py                   # Main application
├── vault_client.py                # Vault client
├── config_loader.py               # Configuration class
└── config.ini                     # Configuration file
```

### 2. Implementing Key Features
- **Authentication**: AppRole-based Vault authentication
- **Token Management**: Automatic token renewal
- **Secret Retrieval**: Fetches KV, Database Dynamic, and Static secrets
- **Caching**: Efficient secret caching strategy
- **TTL Management**: Real-time TTL calculation and display

### 3. Extensible Structure
- Add new secret engines
- Implement custom caching strategies
- Enhance monitoring and logging

### Core Implementation Points

**1. Token Renewal Logic**
```python
# Renew at 4/5 point (when 80% of token TTL has passed)
renewal_point = total_ttl * 4 / 5
if elapsed >= renewal_point:
    renew_token()
```

**2. Error Handling**
```python
# Re-login if token renewal fails
try:
    renew_token()
except VaultException as e:
    # Handle error
    if login(role_id, secret_id) != 0:
        should_exit = True  # Exit if re-login also fails
```

**3. Caching Strategy**
```python
# Version-based caching for KV
if cached_secret is None or cached_secret['version'] != current_version:
    # Fetch new secret
    pass

# TTL-based caching for Dynamic secrets
if cached_secret is None or cached_secret['remaining_ttl'] <= 10:
    # Fetch new secret
    pass
```

## Build and Run

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python vault_app.py

# Deactivate the virtual environment
deactivate
```

## Troubleshooting

1. **Vault Connection Failure**: Check URL, namespace
2. **Authentication Failure**: Check Role ID, Secret ID
3. **Permission Error**: Check Entity policies
4. **Secret Retrieval Failure**: Check if the secret engine is enabled
5. **Package Installation Failure**: Check if you are using a virtual environment
   ```bash
   # If package installation fails on macOS
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

## References

- [Vault API Documentation](https://developer.hashicorp.com/vault/api-docs)
- [AppRole Auth Method](https://developer.hashicorp.com/vault/api-docs/auth/approle)
- [KV v2 Secrets Engine](https://developer.hashicorp.com/vault/api-docs/secret/kv/kv-v2)
- [Database Secrets Engine](https://developer.hashicorp.com/vault/api-docs/secret/databases)
- [hvac Python Library](https://hvac.readthedocs.io/)
