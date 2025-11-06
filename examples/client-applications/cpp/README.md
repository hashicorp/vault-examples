# C++ Vault Client Application

`vault-app` is a Vault client application implemented in C++. It supports KV, Database Dynamic, and Database Static secret engines, and provides real-time secret renewal and caching features.

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
- **Modern C++**: Uses C++17 standard, RAII pattern, and smart pointers

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

## Quick Start

### 1. Install Required Libraries

**Ubuntu/Debian**:
```bash
sudo apt-get update
sudo apt-get install -y build-essential cmake libcurl4-openssl-dev
```

**CentOS/RHEL**:
```bash
sudo yum install gcc-c++ cmake libcurl-devel
```

**macOS (Homebrew)**:
```bash
brew install cmake curl
```

### 2. Build and Run

```bash
# Create build directory
mkdir build && cd build

# Configure with CMake
cmake ..

# Build
make

# Run
./vault-app

# Run with a custom config file
./vault-app ../config.ini
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
=== Vault C++ Client Application ===
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
{ "api_key": "myapp-api-key-123456", "database_url": "mysql://localhost:3306/mydb" }

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
cpp/
├── CMakeLists.txt                 # CMake build configuration
├── config.ini                     # Application configuration file
├── README.md                      # This file
├── include/
│   ├── Config.hpp                 # Configuration management class
│   ├── VaultClient.hpp           # Vault client class
│   └── HttpClient.hpp            # HTTP client wrapper
├── src/
│   ├── main.cpp                   # Main application
│   ├── Config.cpp                 # Configuration implementation
│   ├── VaultClient.cpp            # Vault client implementation
│   └── HttpClient.cpp             # HTTP client implementation
└── third_party/
    └── json.hpp                   # nlohmann/json (single header)
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

### Modern C++ Features
- **C++17 Standard**: Uses modern C++ features
- **RAII Pattern**: Resource management through constructors/destructors
- **Smart Pointers**: Automatic memory management with `std::unique_ptr` and `std::shared_ptr`
- **Thread Safety**: Uses `std::mutex` and `std::atomic` for thread synchronization

## Developer Guide

### Core Implementation Points

**1. Memory Management with RAII**
```cpp
// Automatic cleanup with RAII
class VaultClient {
    std::unique_ptr<HttpClient> http_client;
    // Destructor automatically cleans up
};
```

**2. Token Renewal Logic**
```cpp
// Renew at 4/5 point (when 80% of token TTL has passed)
auto renewal_point = total_ttl * 4 / 5;
if (elapsed >= renewal_point) {
    renewToken();
}
```

**3. Error Handling**
```cpp
// Exception-based error handling
try {
    renewToken();
} catch (const VaultException& e) {
    // Handle error
    if (login(role_id, secret_id) != 0) {
        should_exit = true;  // Exit if re-login also fails
    }
}
```

### Key Classes

**VaultClient**
- `init()`: Initializes the client
- `login()`: Logs in with AppRole
- `renewToken()`: Renews the token
- `getKvSecret()`: Fetches a KV secret
- `getDbDynamicSecret()`: Fetches a Database Dynamic secret
- `getDbStaticSecret()`: Fetches a Database Static secret

**HttpClient**
- Wrapper around libcurl for HTTP requests
- Handles JSON parsing with nlohmann/json

**Config**
- Loads and parses INI configuration files
- Provides access to configuration values

## Troubleshooting

### Build Errors
- **Missing Libraries**: Install required packages (see Quick Start section)
- **CMake Issues**: Ensure CMake 3.10 or higher is installed
- **Compiler Issues**: Ensure C++17 compatible compiler (GCC 7+, Clang 5+)

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
- [C++17 Standard](https://en.cppreference.com/w/cpp/17)
