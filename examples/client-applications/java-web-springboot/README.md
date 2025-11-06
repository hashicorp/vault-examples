# Spring Boot Web Application with Vault

This example demonstrates how to manage Vault secrets in a web application using Spring Boot and Spring Cloud Vault Config. It uses Spring Cloud Vault Config to automatically inject secrets and displays secret information on a web UI via Thymeleaf.

## Overview

### Purpose and Usage Scenarios

This example demonstrates how to manage Vault secrets in a web application using Spring Boot and Spring Cloud Vault Config.
- Uses Spring Cloud Vault Config to automatically inject secrets
- Displays secret information on a web UI via Thymeleaf
- In Spring Boot, the database connection is managed through the `datasource` configuration
- This example uses Dynamic Secrets provided by Vault to manage the database connection
- The `DatabaseConfig` class uses the `@RefreshScope` annotation to update the database connection information in real-time

### Key Scenarios
- **AppRole Authentication**: Secure Vault access via Role ID + Secret ID
- **Automatic Secret Injection**: Automatic secret management via Spring Cloud Vault Config
- **Automatic Token Renewal**: Spring Cloud Vault handles token renewal automatically
- **Web UI Provision**: Visualization of secret information using Thymeleaf
- **Real-time Updates**: Automatic secret renewal via @RefreshScope
- **Database Integration**: Database connection and statistics retrieval using Vault Dynamic Secrets

### Supported Secret Types
- **KV v2**: Key-value store (direct Vault API call)
- **Database Dynamic**: Dynamic database credentials (automatic DataSource configuration)
- **Database Static**: Static database credentials (direct Vault API call)

### Database Credential Source Selection

The application can choose one of the following three credential sources for database access:
- **KV Secret**: Static credentials (fetches database credentials from a KV Secret)
- **Database Dynamic Secret**: Dynamic credentials (TTL-based automatic renewal)
- **Database Static Secret**: Statically managed credentials (automatically rotated by Vault)

## Integration Approach

This example uses **Spring Cloud Vault Config**, which is a framework-level integration that automatically handles Vault authentication, token renewal, and secret injection.

### Authentication Process

1. **AppRole Authentication**: Spring Cloud Vault Config handles AppRole authentication automatically
   - Configuration is provided in `bootstrap.yml`
   - `role_id` and `secret_id` are read from configuration

2. **Token Management**: Spring Cloud Vault Config automatically handles token renewal
   - No manual token renewal code is required
   - The framework handles all token lifecycle management

3. **Secret Injection**: Secrets are automatically injected into Spring configuration
   - Database Dynamic Secrets are automatically injected into `DataSource` configuration
   - KV and Static Secrets require direct Vault API calls

### Differences from Direct API Integration

**Direct API Integration (Other Examples)**:
- Requires manual implementation of authentication and token renewal
- More control but more code to maintain

**Spring Cloud Vault Config (This Example)**:
- Framework handles authentication and token renewal automatically
- Less code, but less control over the process
- Automatic secret injection into Spring configuration

## Vault Development Server Setup

Before running this example, you need to set up a Vault development server. See the [Vault Development Server Setup Guide](../README.md#vault-development-server-setup) in the parent directory, or use the provided setup script:

```bash
cd ..
./setup-vault-for-my-vault-app.sh
```

## Quick Start

### 1. Prerequisites
- Java 11 or higher
- Gradle 7.0 or higher
- Vault server (with development server setup completed)
- MySQL (for database integration)

### 2. Build and Run

```bash
# Build with Gradle
./gradlew build

# Run the application
./gradlew bootRun

# Or run the JAR file
java -jar build/libs/vault-web-app-1.0.0.war
```

### 3. Access in Web Browser
```
http://localhost:8080/vault-web
```

## Key Features

### 1. AppRole Authentication and Automatic Token Renewal

Spring Cloud Vault automatically handles AppRole authentication and token renewal:

```yaml
# bootstrap.yml
spring:
  cloud:
    vault:
      authentication: APPROLE
      app-role:
        role-id: 4060cafc-6cda-3bb4-a690-63177f9a5bc6
        secret-id: 715d4f2c-20ed-6aac-235d-b075b65c9d74
```

### 2. Automatic Secret Injection

Spring Cloud Vault Config automatically injects Database Dynamic Secrets:

```yaml
# bootstrap.yml
spring:
  cloud:
    vault:
      authentication: APPROLE
      app-role:
        role-id: <Role ID from setup script>
        secret-id: <Secret ID from setup script>
      database:
        enabled: true
        backend: my-vault-app-database
        role: db-demo-dynamic
        username-property: spring.datasource.username
        password-property: spring.datasource.password
```

**Important**: Spring Cloud Vault Config only automatically injects Database Dynamic Secrets. KV and Database Static Secrets are fetched by calling the Vault API directly.

### 3. Web UI Features
- **Display Secret Information**: KV, Database Dynamic/Static secret information
- **Test Database Connection**: Connects to the database using Vault Dynamic Secrets
- **Database Statistics**: Database connection statistics
- **Auto-Refresh**: Automatically refreshes the page every 30 seconds
- **Manual Refresh**: Manual secret refresh functionality

### 4. API Endpoints
- `GET /` - Main page (index.html)
- `GET /refresh` - Refresh secrets

## Configuration Options

### Vault Configuration (bootstrap.yml)

```yaml
spring:
  cloud:
    vault:
      namespace: <namespace_name>
      host: localhost
      port: 8200
      scheme: http
      authentication: APPROLE
      app-role:
        role-id: <Role ID from setup script>
        secret-id: <Secret ID from setup script>
      database:
        enabled: true
        backend: my-vault-app-database
        role: db-demo-dynamic
        username-property: spring.datasource.username
        password-property: spring.datasource.password
```

### Database Credential Source Selection (application.yml)

```yaml
vault:
  database:
    credential-source: kv  # Choose from kv, dynamic, static
    kv:
      path: my-vault-app-kv/data/database
      username-key: database_username
      password-key: database_password
    dynamic:
      role: db-demo-dynamic
    static:
      role: db-demo-static
```

#### 1. KV Secret (Static Credentials)
```yaml
vault:
  database:
    credential-source: kv
```
- Fetches database credentials from a KV Secret
- Uses `database_username` and `database_password` keys
- **Note**: Application restart is required if the credentials in the KV Secret change

#### 2. Database Dynamic Secret (Dynamic Credentials)
```yaml
vault:
  database:
    credential-source: dynamic
```
- TTL-based automatic renewal
- Utilizes Spring Cloud Vault Config's automatic injection

#### 3. Database Static Secret (Statically Managed Credentials)
```yaml
vault:
  database:
    credential-source: static
```
- Automatically rotated by Vault
- The user remains the same, so periodic renewal is not required in the application

### Application Configuration (application.yml)

```yaml
server:
  port: 8080
  servlet:
    context-path: /vault-web

spring:
  thymeleaf:
    prefix: classpath:/templates/
    suffix: .html
    cache: false
  datasource:
    url: jdbc:mysql://127.0.0.1:3306/mydb
    driver-class-name: com.mysql.cj.jdbc.Driver
```

### Environment Variable Configuration

```bash
# AppRole authentication settings (optional)
export SPRING_CLOUD_VAULT_APP_ROLE_ROLE_ID=4060cafc-6cda-3bb4-a690-63177f9a5bc6
export SPRING_CLOUD_VAULT_APP_ROLE_SECRET_ID=715d4f2c-20ed-6aac-235d-b075b65c9d74
```

## Project Structure

```
java-web-springboot/
├── build.gradle
├── settings.gradle
├── gradlew
├── gradlew.bat
├── README.md
└── src/
    ├── main/
    │   ├── java/
    │   │   └── com/
    │   │       └── example/
    │   │           └── vaultweb/
    │   │               ├── VaultWebApplication.java    # Main application
    │   │               ├── config/
    │   │               │   ├── DatabaseConfig.java     # Database configuration with @RefreshScope
    │   │               │   └── VaultConfig.java         # Vault client configuration
    │   │               ├── controller/
    │   │               │   └── HomeController.java      # Web controller
    │   │               ├── model/
    │   │               │   └── SecretInfo.java          # Secret information model
    │   │               └── service/
    │   │                   ├── DatabaseService.java     # Database service
    │   │                   └── VaultSecretService.java  # Vault secret service
    │   └── resources/
    │       ├── bootstrap.yml                           # Spring Cloud Vault configuration
    │       ├── application.yml                         # Application configuration
    │       ├── logback-spring.xml                       # Logging configuration
    │       └── templates/
    │           ├── index.html                          # Main page
    │           └── health.html                         # Health check page
    └── test/
        └── java/
            └── com/
                └── example/
                    └── vaultweb/
                        └── VaultWebApplicationTest.java
```

## Architecture

### Key Components

**VaultWebApplication**
- Main Spring Boot application class
- Entry point for the application

**DatabaseConfig**
- Database configuration class with `@RefreshScope`
- Automatically updates database connection when secrets change
- Uses Spring Cloud Vault Config injected credentials

**VaultConfig**
- Vault client configuration for direct API calls
- Used for KV and Static Secrets (not automatically injected)

**HomeController**
- Web controller for handling HTTP requests
- Displays secret information on web UI

**VaultSecretService**
- Service for fetching secrets from Vault
- Handles KV, Database Dynamic, and Static Secrets

**DatabaseService**
- Service for database operations
- Uses injected DataSource configuration

### @RefreshScope Annotation

The `@RefreshScope` annotation allows beans to be refreshed when secrets change:

```java
@Configuration
@RefreshScope
public class DatabaseConfig {
    @Bean
    @RefreshScope
    public DataSource dataSource(
        @Value("${spring.datasource.username}") String username,
        @Value("${spring.datasource.password}") String password
    ) {
        // DataSource configuration
    }
}
```

When secrets are refreshed via `/actuator/refresh` or Spring Cloud Config, the DataSource will be recreated with new credentials.

## Developer Guide

### Core Implementation Points

**1. Spring Cloud Vault Configuration**
```yaml
spring:
  cloud:
    vault:
      authentication: APPROLE
      app-role:
        role-id: ${VAULT_ROLE_ID}
        secret-id: ${VAULT_SECRET_ID}
      database:
        enabled: true
        backend: my-vault-app-database
        role: db-demo-dynamic
```

**2. Direct Vault API Calls**
```java
// For KV and Static Secrets (not automatically injected)
VaultOperations vaultOperations;
Secret secret = vaultOperations.read("my-vault-app-kv/data/database");
```

**3. RefreshScope Usage**
```java
@RefreshScope
@Bean
public DataSource dataSource() {
    // Automatically uses latest credentials from Spring Cloud Vault
}
```

## Troubleshooting

### Build Errors
- **Missing Dependencies**: Ensure Gradle can download dependencies
- **Java Version**: Ensure Java 11 or higher is installed
- **Gradle Version**: Ensure Gradle 7.0 or higher is installed

### Runtime Errors
- **Vault Connection Failure**: Check Vault server status and URL in `bootstrap.yml`
- **Authentication Failure**: Verify Role ID and Secret ID in `bootstrap.yml`
- **Permission Errors**: Check Entity policies and path permissions
- **Database Connection Failure**: Check MySQL is running and credentials are correct

### Spring Cloud Vault Issues
- **Secrets Not Injected**: Check `bootstrap.yml` configuration
- **Token Renewal Failure**: Spring Cloud Vault handles this automatically, check Vault server logs
- **@RefreshScope Not Working**: Ensure actuator is enabled and `/actuator/refresh` endpoint is accessible

## References

- [Vault API Documentation](https://developer.hashicorp.com/vault/api-docs)
- [Spring Cloud Vault](https://spring.io/projects/spring-cloud-vault)
- [Spring Cloud Vault Reference](https://docs.spring.io/spring-cloud-vault/docs/current/reference/html/)
- [AppRole Auth Method](https://developer.hashicorp.com/vault/api-docs/auth/approle)
- [Database Secrets Engine](https://developer.hashicorp.com/vault/api-docs/secret/databases)
- [KV Secrets Engine](https://developer.hashicorp.com/vault/api-docs/secret/kv)
