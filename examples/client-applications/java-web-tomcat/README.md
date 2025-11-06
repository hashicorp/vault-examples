# Tomcat Web Application with Vault

This example demonstrates how to securely manage secrets in a traditional Java Web Application using Vault. It is implemented based on Servlet + JSP, and maintains continuous security through AppRole Authentication and Token Auto-Renewal.

## Overview

### Purpose and Usage Scenarios

This example demonstrates how to securely manage secrets in a **traditional Java Web Application** using Vault.
- Implemented based on **Servlet + JSP** (without Spring Boot)
- Maintains continuous security through **AppRole Authentication** and **Token Auto-Renewal**
- Uses Apache Commons DBCP2 for database connection pool management
- Provides a web UI through JSP + JSTL

### Key Scenarios
- **Traditional Java Web**: A web application based on Servlet + JSP (without Spring Boot)
- **AppRole Authentication**: Machine-to-machine authentication for secure access to Vault
- **Token Auto-Renewal**: Automatically checks token status every 10 seconds and renews at 80% of TTL
- **Connection Pool**: Manages database connection pool using Apache Commons DBCP2
- **Automatic Renewal**: Automatically renews database credentials based on TTL

### Supported Secret Types
- **KV v2**: Key-value store (direct Vault API call)
- **Database Dynamic**: Dynamic database credentials (automatic connection pool renewal)
- **Database Static**: Static database credentials (direct Vault API call)

### Database Credential Source Selection

The application can choose one of the following three credential sources for database access:
- **KV Secret**: Static credentials (renewal based on version change detection)
- **Database Dynamic Secret**: Dynamic credentials (TTL-based automatic renewal)
- **Database Static Secret**: Statically managed credentials (automatically rotated by Vault)

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
   - Code for automatic renewal is implemented using `ScheduledExecutorService`
   - Token renewal occurs at 4/5 of TTL (80% point)

### Operational Sequence

The application follows this sequence:

1. **Application Initialization**
   - Load configuration from `vault.properties`
   - Initialize Vault client

2. **Vault Authentication**
   - Authenticate with Vault using AppRole (Role ID + Secret ID)
   - Receive client token and TTL information

3. **Token Management**
   - Background scheduler checks token status every 10 seconds
   - Renews token when 4/5 of TTL has passed
   - Handles token renewal failures

4. **Secret Retrieval**
   - **KV Secrets**: Version-based caching (renews only when version changes)
   - **Database Dynamic**: TTL-based caching (renews at 80% of TTL)
   - **Database Static**: Time-based caching

5. **Connection Pool Management**
   - Automatically recreates connection pool when credentials change
   - Uses Apache Commons DBCP2 for connection pool management

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
- Tomcat 10
- Vault server (with development server setup completed)
- MySQL (for database integration)

### 2. Build and Deploy

```bash
# Build with Maven
mvn clean package

# Copy the WAR file to the Tomcat webapps directory
cp target/vault-tomcat-app.war $TOMCAT_HOME/webapps/

# Start Tomcat
$TOMCAT_HOME/bin/startup.sh
```

### 3. Access in Web Browser
```
http://localhost:8080/vault-tomcat-app/
```

## Key Features

### 1. AppRole Authentication and Token Auto-Renewal

Securely access Vault via **AppRole Authentication** and maintain continuous security with **Token Auto-Renewal**:

```java
// AppRole Authentication (VaultClient.java)
private void authenticateWithAppRole() {
    String roleId = VaultConfig.getAppRoleId();
    String secretId = VaultConfig.getAppRoleSecretId();
    
    Map<String, Object> authData = new HashMap<>();
    authData.put("role_id", roleId);
    authData.put("secret_id", secretId);
    
    // Obtain token by calling Vault API
    Map<String, Object> response = callAppRoleLogin(authData);
    this.vaultToken = (String) auth.get("client_token");
    this.tokenExpiry = System.currentTimeMillis() + (leaseDuration * 1000L);
}

// Token Auto-Renewal (TokenRenewalScheduler.java)
scheduler.scheduleAtFixedRate(() -> {
    if (vaultClient.shouldRenew()) {
        boolean success = vaultClient.renewToken();
        if (!success) {
            System.exit(1); // Terminate application on renewal failure
        }
    }
}, 10, 10, TimeUnit.SECONDS);
```

### 2. Automatic Renewal of Database Dynamic Secrets

Automatic renewal using Apache Commons DBCP2 Connection Pool and `ScheduledExecutorService`:

```java
// Schedule credential renewal at 80% of TTL
long refreshDelay = (long) (dbSecret.getTtl() * 0.8 * 1000);
scheduler.schedule(() -> refreshCredentials(), delayMs, TimeUnit.MILLISECONDS);
```

### 3. Web UI Features
- **Display Secret Information**: KV, Database Dynamic/Static secret information
- **Test Database Connection**: Connects to the database using Vault Dynamic Secrets
- **Database Statistics**: Database connection statistics
- **Auto-Refresh**: Automatically refreshes the page every 30 seconds
- **Manual Refresh**: Manual secret refresh functionality

### 4. Servlet Endpoints
- `GET /` - Main page (index.jsp)
- `GET /refresh` - Refresh secrets

## Configuration Options

### Vault Configuration (vault.properties)

```properties
# Vault Server Settings
vault.url=http://127.0.0.1:8200

# AppRole Authentication Settings
vault.auth.type=approle
vault.approle.role_id=4060cafc-6cda-3bb4-a690-63177f9a5bc6
vault.approle.secret_id=715d4f2c-20ed-6aac-235d-b075b65c9d74

# Token renewal settings
vault.token.renewal.enabled=true
vault.token.renewal.threshold=0.8

# KV Secrets Engine Settings
vault.kv.path=my-vault-app-kv

# Database Secrets Engine Settings
vault.database.path=my-vault-app-database
vault.database.dynamic.role=db-demo-dynamic
vault.database.static.role=db-demo-static

# Database credential source selection (one of kv, dynamic, static)
vault.database.credential.source=kv
#vault.database.credential.source=dynamic
#vault.database.credential.source=static

# KV-based Database credential settings (if source=kv)
vault.database.kv.path=my-vault-app-kv/data/database
vault.database.kv.refresh_interval=30

# Database URL settings
vault.database.url=jdbc:mysql://127.0.0.1:3306/mydb
vault.database.driver=com.mysql.cj.jdbc.Driver
```

### Database Credential Source Selection

You can select the database credential source in `vault.properties`:

#### 1. KV Secret (Static Credentials)
```properties
vault.database.credential.source=kv
vault.database.kv.path=my-vault-app-kv/data/database
vault.database.kv.refresh_interval=30
```
- Periodically detects KV version changes
- Recreates the Connection Pool when the version changes

#### 2. Database Dynamic Secret (Dynamic Credentials)
```properties
vault.database.credential.source=dynamic
```
- TTL-based automatic renewal
- Issues a new credential and recreates the Connection Pool at 80% of TTL

#### 3. Database Static Secret (Statically Managed Credentials)
```properties
vault.database.credential.source=static
```
- Automatically rotated by Vault
- The user remains the same, so periodic renewal is not required in the application

### Environment Variable Configuration

```bash
# Vault Server Settings
export VAULT_URL=http://127.0.0.1:8200

# AppRole Authentication Settings (recommended to set in vault.properties)
export VAULT_AUTH_TYPE=approle
export VAULT_APPROLE_ROLE_ID=4060cafc-6cda-3bb4-a690-63177f9a5bc6
export VAULT_APPROLE_SECRET_ID=715d4f2c-20ed-6aac-235d-b075b65c9d74
```

## Project Structure

```
java-web-tomcat/
├── pom.xml
├── README.md
└── src/
    ├── main/
    │   ├── java/
    │   │   └── com/
    │   │       └── example/
    │   │           └── vaulttomcat/
    │   │               ├── client/
    │   │               │   └── VaultClient.java         # Vault client
    │   │               ├── config/
    │   │               │   ├── DatabaseConfig.java      # Database configuration
    │   │               │   ├── TokenRenewalScheduler.java  # Token renewal scheduler
    │   │               │   └── VaultConfig.java         # Vault configuration
    │   │               ├── listener/
    │   │               │   └── AppContextListener.java  # Application context listener
    │   │               ├── model/
    │   │               │   └── SecretInfo.java         # Secret information model
    │   │               ├── service/
    │   │               │   ├── DatabaseService.java    # Database service
    │   │               │   └── VaultSecretService.java # Vault secret service
    │   │               └── servlet/
    │   │                   ├── HomeServlet.java         # Main servlet
    │   │                   ├── RefreshServlet.java      # Refresh servlet
    │   │                   └── TestServlet.java        # Test servlet
    │   ├── resources/
    │   │   ├── logback.xml                             # Logging configuration
    │   │   └── vault.properties                        # Vault configuration
    │   └── webapp/
    │       ├── css/
    │       │   └── style.css                           # CSS styles
    │       └── WEB-INF/
    │           ├── jsp/
    │           │   └── index.jsp                       # Main page
    │           └── web.xml                             # Web application configuration
    └── test/
        └── java/
            └── com/
                └── example/
                    └── vaulttomcat/
                        └── VaultApplicationTest.java
```

## Architecture

### Key Components

**VaultClient**
- Vault API integration
- Handles authentication, token renewal, and secret retrieval

**VaultConfig**
- Loads configuration from `vault.properties`
- Provides access to configuration values

**TokenRenewalScheduler**
- Background scheduler for token renewal
- Checks token status every 10 seconds
- Renews token at 80% of TTL

**DatabaseConfig**
- Database connection pool configuration
- Uses Apache Commons DBCP2
- Automatically recreates connection pool when credentials change

**AppContextListener**
- Application context lifecycle management
- Initializes Vault client and token renewal scheduler
- Cleans up resources on shutdown

**HomeServlet**
- Main servlet for displaying secret information
- Handles HTTP requests and renders JSP pages

**VaultSecretService**
- Service for fetching secrets from Vault
- Handles KV, Database Dynamic, and Static Secrets

**DatabaseService**
- Service for database operations
- Uses connection pool managed by DatabaseConfig

### Token Renewal Strategy

```java
// Token renewal at 80% of TTL
scheduler.scheduleAtFixedRate(() -> {
    if (vaultClient.shouldRenew()) {
        boolean success = vaultClient.renewToken();
        if (!success) {
            System.exit(1); // Terminate application on renewal failure
        }
    }
}, 10, 10, TimeUnit.SECONDS);
```

### Connection Pool Renewal Strategy

```java
// Schedule credential renewal at 80% of TTL
long refreshDelay = (long) (dbSecret.getTtl() * 0.8 * 1000);
scheduler.schedule(() -> refreshCredentials(), delayMs, TimeUnit.MILLISECONDS);
```

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
if (!renewToken()) {
    if (!login(roleId, secretId)) {
        System.exit(1); // Exit if re-login also fails
    }
}
```

**3. Connection Pool Renewal**
```java
// Recreate connection pool when credentials change
BasicDataSource newDataSource = new BasicDataSource();
newDataSource.setUrl(databaseUrl);
newDataSource.setUsername(newUsername);
newDataSource.setPassword(newPassword);
// Close old connection pool and use new one
```

## Troubleshooting

### Build Errors
- **Missing Dependencies**: Ensure Maven can download dependencies
- **Java Version**: Ensure Java 11 or higher is installed
- **Maven Version**: Ensure Maven 3.6 or higher is installed

### Runtime Errors
- **Vault Connection Failure**: Check Vault server status and URL in `vault.properties`
- **Authentication Failure**: Verify Role ID and Secret ID in `vault.properties`
- **Permission Errors**: Check Entity policies and path permissions
- **Database Connection Failure**: Check MySQL is running and credentials are correct
- **Tomcat Deployment Issues**: Check Tomcat logs for deployment errors

### Performance Optimization
- **Memory Usage**: Prevent unnecessary secret renewals
- **Network Calls**: Optimize caching strategy
- **Thread Management**: Set appropriate renewal intervals
- **Connection Pool**: Configure appropriate pool size

## References

- [Vault API Documentation](https://developer.hashicorp.com/vault/api-docs)
- [AppRole Auth Method](https://developer.hashicorp.com/vault/api-docs/auth/approle)
- [Database Secrets Engine](https://developer.hashicorp.com/vault/api-docs/secret/databases)
- [KV Secrets Engine](https://developer.hashicorp.com/vault/api-docs/secret/kv)
- [Apache Commons DBCP2](https://commons.apache.org/proper/commons-dbcp/)
- [Jakarta EE 9](https://jakarta.ee/specifications/servlet/5.0/)
