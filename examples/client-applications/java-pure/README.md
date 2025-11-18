# Java Vault Client Application

This is a Vault client application implemented in Java. It supports KV, Database Dynamic, and Database Static secret engines, and provides real-time secret renewal and caching features.

This example demonstrates how to integrate with Vault using Direct Vault API Integration (Option 1), which is the recommended approach for new applications.

## Overview

### Purpose and Usage Scenarios

- Reference application for Vault integration development
- If needed only for initial application startup, it makes an API call once and then utilizes the cache for subsequent runs to reduce memory usage
- The example is implemented to periodically fetch and renew secrets
- Designed to call the API directly rather than being implemented as a library solely for Vault

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
- **Metadata Display**: Provides useful information like version, TTL, etc.
- **Security**: Entity-based permission management and secure memory handling
- **System Property Override**: Supports runtime configuration override via system properties

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
   - Load configuration from `config.properties`
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

### 1. Prerequisites
- Java 11 or higher
- Maven 3.6 or higher
- Vault server (with development server setup completed)

### 2. Build and Run

```bash
# Build the project
mvn clean package

# Run the application
java -jar target/vault-java-app.jar

# Or run directly with Maven
mvn exec:java -Dexec.mainClass="com.example.vault.VaultApplication"
```

### 3. Modify Configuration File

You can change the Vault connection settings by modifying the `src/main/resources/config.properties` file.

## Example Output

```
🚀 Starting Vault Java Client Application
✅ Vault login successful (TTL: 60s)
✅ KV secret renewal scheduler started (interval: 5s)
✅ Database Dynamic secret renewal scheduler started (interval: 5s)
✅ Database Static secret renewal scheduler started (interval: 10s)

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

⚙️ Current Configuration:
- Entity: my-vault-app
- Vault URL: http://127.0.0.1:8200
- KV Enabled: true
- Database Dynamic Enabled: true
- Database Static Enabled: true

🔄 Starting secret renewal... (Press Ctrl+C to exit)

=== KV Secret Refresh ===
✅ KV secret fetch successful (version: 11)
📦 KV Secret Data (version: 11):
{"api_key":"myapp-api-key-123456","database_url":"mysql://localhost:3306/mydb"}

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

Generally, predefined configurations are defined in the `config.properties` file. Since the `secret_id` used for Vault authentication expires after issuance, it is implemented to be overridden by a system property at runtime.

1. **System Properties** (`-D` option) - Highest priority
2. **config.properties file** - Default value

### How to Use System Properties
```bash
# Override settings with system properties at runtime
java -Dvault.role_id=your-role-id \
     -Dvault.secret_id=your-secret-id \
     -Dvault.url=http://your-vault-server:8200 \
     -jar target/vault-java-app.jar

# Or individual settings
java -Dvault.secret_id=3ee5080b-c9b3-2714-799c-f8d45a715625 -jar target/vault-java-app.jar
```

### Vault Server Settings
```properties
# Entity name (required)
vault.entity=my-vault-app
# Vault server address
vault.url=http://127.0.0.1:8200
# Vault namespace (optional)
vault.namespace=
# AppRole authentication info (required)
vault.role_id=7fb49dd0-4b87-19cd-7b72-a7e21e5c543e
vault.secret_id=475a6500-f9f8-fdd4-ec30-54fadcad926e
```

### Secret Engine Settings
```properties
# KV Secret settings
secret.kv.enabled=true
secret.kv.path=database
secret.kv.refresh_interval=5

# Database Dynamic Secret settings
secret.database.dynamic.enabled=true
secret.database.dynamic.role_id=db-demo-dynamic

# Database Static Secret settings
secret.database.static.enabled=true
secret.database.static.role_id=db-demo-static
```

### HTTP Settings
```properties
# HTTP request timeout (seconds)
http.timeout=30
# Maximum response size (bytes)
http.max_response_size=4096
```

## Project Structure

```
java-pure/
├── pom.xml
├── README.md
└── src/
    ├── main/
    │   ├── java/
    │   │   └── com/
    │   │       └── example/
    │   │           └── vault/
    │   │               ├── VaultApplication.java    # Main application
    │   │               ├── config/
    │   │               │   └── VaultConfig.java     # Configuration management
    │   │               └── client/
    │   │                   └── VaultClient.java      # Vault client
    │   └── resources/
    │       ├── config.properties                    # Configuration file
    │       └── logback.xml                          # Logging configuration
    └── test/
        └── java/
            └── com/
                └── example/
                    └── vault/
                        └── VaultApplicationTest.java
```

## Architecture

### Class Structure
```
com.example.vault/
├── VaultApplication.java          # Main application
├── config/
│   └── VaultConfig.java           # Configuration management
└── client/
    └── VaultClient.java           # Vault client
```

### Key Components
- **VaultApplication**: Main application logic, scheduler management
- **VaultConfig**: Loads and manages configuration files
- **VaultClient**: Vault API integration, secret retrieval, caching

### Caching Strategy
- **KV v2**: Version-based caching (renews only when version changes)
- **Database Dynamic**: TTL-based caching (10-second threshold)
- **Database Static**: Time-based caching (5-minute interval)

### Real-time TTL Calculation
- Displays the real-time decrease of the TTL for Database Dynamic/Static Secrets
- Calculates the remaining TTL by subtracting the elapsed time from the cached TTL
- Prevents negative values with `Math.max(0, remainingTtl)`

### Security Features
- **Entity-based Permissions**: Uses `{entity}-{engine}` path patterns
- **Automatic Token Renewal**: Automatically renews tokens before expiration
- **Memory Security**: Cleans up secret data immediately after use
- **Error Handling**: Retries on network errors or token expiration

## Developer Guide

### Core Implementation Points

**1. Token Renewal Logic**
```java
// Renew at 4/5 point (when 80% of token TTL has passed)
long renewalPoint = totalTtl * 4 / 5;
if (elapsed >= renewalPoint) {
    renewToken();
}
```

**2. Error Handling**
```java
// Re-login if token renewal fails
try {
    renewToken();
} catch (VaultException e) {
    // Handle error
    if (login(roleId, secretId) != 0) {
        shouldExit = true;  // Exit if re-login also fails
    }
}
```

**3. Caching Strategy**
```java
// Version-based caching for KV
if (cachedSecret == null || cachedSecret.getVersion() != currentVersion) {
    // Fetch new secret
}

// TTL-based caching for Dynamic secrets
if (cachedSecret == null || cachedSecret.getRemainingTtl() <= 10) {
    // Fetch new secret
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

**VaultConfig**
- Loads configuration from `config.properties`
- Supports system property override
- Provides access to configuration values

## Troubleshooting

### Build Errors
- **Missing Dependencies**: Ensure Maven can download dependencies
- **Java Version**: Ensure Java 11 or higher is installed
- **Maven Version**: Ensure Maven 3.6 or higher is installed

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
- [Apache HttpClient](https://hc.apache.org/httpcomponents-client-5.1.x/)
- [Jackson JSON](https://github.com/FasterXML/jackson)
