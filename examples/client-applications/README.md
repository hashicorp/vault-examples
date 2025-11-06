# Client Applications

A collection of complete, runnable client application examples demonstrating how to integrate with Vault using various programming languages and frameworks. These examples show how to securely manage secrets in applications by dynamically fetching and automatically renewing secrets from Vault.

## Overview

This directory contains complete client application examples that demonstrate real-world Vault integration patterns. Unlike the code snippets in other directories, these are full applications that you can build and run.

### Key Features Across Examples

- **AppRole Authentication**: Secure Vault access via Role ID + Secret ID
- **Automatic Token Renewal**: Background token renewal to maintain access
- **Secret Caching**: Efficient caching strategies to minimize API calls
- **Multiple Secret Engines**: Support for KV v2, Database Dynamic, and Database Static secrets
- **Error Handling**: Robust error handling and retry logic
- **Production-Ready Patterns**: Examples demonstrate best practices for production use

### Mandatory Operational Requirements

- Most examples use AppRole authentication
- After AppRole authentication, the app receives a token from Vault
- The token has specific permissions and an expiration time
- The token must be renewed before it expires
- If renewal fails, access to Vault is denied

### Token Renewal Exceptions

- **Spring Cloud Vault Config** (used in the Spring Boot example) handles token renewal automatically
- **Vault Proxy** is used for scripts where token renewal is difficult to implement

## Available Examples

### C Example ([c/](./c/))
- **Language**: C (libcurl + json-c)
- **Features**:
  - Supports KV v2, Database Dynamic, and Database Static secret engines
  - Real-time renewal, version-based caching, TTL-based renewal
  - Entity-based permissions, automatic token renewal
- **Build**: `make`
- **Run**: `./vault-app`

### C++ Example ([cpp/](./cpp/))
- **Language**: C++17 (libcurl + nlohmann/json)
- **Features**:
  - Modern C++17 style, RAII pattern, smart pointers
  - CMake-based cross-platform build
  - Thread safety (std::mutex, std::atomic)
  - Same features and configuration compatibility as the C version
- **Build**: `mkdir build && cd build && cmake .. && make`
- **Run**: `./vault-app`

### Java Pure Example ([java-pure/](./java-pure/))
- **Language**: Java 11+ (Apache HttpClient + Jackson)
- **Features**:
  - Maven-based project structure
  - Real-time TTL calculation, multi-threaded renewal
  - System property override support
- **Build**: `mvn clean package`
- **Run**: `java -jar target/vault-java-app.jar`

### Python Example ([python/](./python/))
- **Language**: Python 3.7+ (hvac + threading)
- **Features**:
  - Uses hvac 2.3.0, a dedicated Vault library
  - Virtual environment-based package management
  - Environment variable override support
  - Real-time TTL calculation, multi-threaded renewal
- **Install**: `pip install -r requirements.txt`
- **Run**: `python vault_app.py`

### Java Web Spring Boot Example ([java-web-springboot/](./java-web-springboot/))
- **Language**: Java 11+ (Spring Boot + Spring Cloud Vault Config)
- **Features**:
  - Vault access via AppRole authentication
  - Automatic Token Renewal by Spring Cloud Vault
  - Automatic injection of Database Dynamic Secrets via Spring Cloud Vault Config
  - Web UI provided through Thymeleaf
  - Real-time secret updates via @RefreshScope
  - Direct Vault API calls to fetch KV and Static Secrets
  - MySQL integration and display of database statistics
- **Build**: `./gradlew build`
- **Run**: `./gradlew bootRun`
- **Web Access**: `http://localhost:8080/vault-web`

### Java Web Tomcat Example ([java-web-tomcat/](./java-web-tomcat/))
- **Language**: Java 11+ (Servlet + JSP + Apache Commons DBCP2)
- **Features**:
  - Traditional Java Web Application (Servlet + JSP)
  - Vault access via AppRole authentication
  - Token Auto-Renewal (checks every 10s, renews at 80% of TTL)
  - Automatic renewal of Apache Commons DBCP2 Connection Pool
  - Web UI provided through JSP + JSTL
  - MySQL integration and display of database statistics
- **Build**: `mvn clean package`
- **Run**: Deploy WAR to Tomcat 10
- **Web Access**: `http://localhost:8080/vault-tomcat-app`

### Script Sample ([script-sample/](./script-sample/))
- **Language**: Bash Scripts
- **Features**:
  - Direct Vault API calls and Vault Proxy integration
  - Supported Secrets: KV, Database Dynamic/Static, SSH (KV/OTP/Signed Certificate), AWS
  - No Vault CLI required, uses pure curl
- **Usage**: See [script-sample/README.md](./script-sample/README.md)

## Quick Start

### 1. Set Up Vault Server

Before running any examples, you need to set up a Vault development server. Use the provided setup script:

```bash
# Set up Vault development server
./setup-vault-for-my-vault-app.sh
```

Or manually configure Vault following the instructions in each example's README.

### 2. Run Examples

#### C Example
```bash
cd c
make clean && make
./vault-app
```

#### C++ Example
```bash
cd cpp
mkdir build && cd build
cmake ..
make
./vault-app
```

#### Java Pure Example
```bash
cd java-pure
mvn clean package
java -jar target/vault-java-app.jar
```

#### Python Example
```bash
cd python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python vault_app.py
```

#### Spring Boot Web Example
```bash
cd java-web-springboot
./gradlew bootRun
# Access in web browser: http://localhost:8080/vault-web
```

#### Tomcat Web Example
```bash
cd java-web-tomcat
mvn clean package
# Deploy WAR to Tomcat 10
# Access in web browser: http://localhost:8080/vault-tomcat-app
```

#### Script Examples (with Vault Proxy)
```bash
cd script-sample/vault-proxy-demo
./setup-token.sh
./start-proxy.sh

# Move to the parent directory and run scripts
cd ..
./get_kv_secret_proxy.sh
./get_db_dynamic_secret_proxy.sh
./get_db_static_secret_proxy.sh

# Stop Vault Proxy
cd vault-proxy-demo
./stop-proxy.sh
```

## Integration Approaches

Each example demonstrates one or more of these integration approaches:

### 1. Direct Vault API Integration (Recommended)
- Application communicates directly with Vault server
- Requires implementing authentication and token renewal logic
- Most flexible and secure approach
- Used in: C, C++, Java Pure, Python, Java Web Tomcat examples

### 2. Vault Proxy
- Proxy sits between application and Vault
- Simplifies application code by handling authentication/token management
- Used in: Script examples

### 3. Spring Cloud Vault Config
- Automatic secret injection and token renewal
- Framework handles Vault integration
- Used in: Java Web Spring Boot example

## Common Patterns

### Authentication Flow
1. Application authenticates with Vault using AppRole (Role ID + Secret ID)
2. Vault returns a client token with TTL
3. Application uses token to access secrets
4. Token must be renewed before expiration

### Token Renewal
- Tokens have a TTL (Time To Live)
- Renew tokens at 4/5 of TTL (80% point)
- If renewal fails, application should re-authenticate or gracefully shutdown

### Secret Caching
- **KV Secrets**: Version-based caching (renew only when version changes)
- **Database Dynamic**: TTL-based caching (renew when TTL is low)
- **Database Static**: Time-based caching (renew periodically)

## Configuration

Each example includes a configuration file (config.ini, config.properties, etc.) that you need to customize:

- **Vault Server Address**: `http://127.0.0.1:8200`
- **Namespace**: Vault namespace (optional)
- **Entity**: Entity name for your application
- **Role ID**: AppRole Role ID
- **Secret ID**: AppRole Secret ID

**Note**: Secret IDs typically expire after issuance, so you may need to regenerate them or use environment variables to override configuration at runtime.

## Security Considerations

- Never embed secrets in code
- Use secrets only in memory
- Do not save secrets to files or logs
- Set appropriate token expiration times
- Use Entity-based permissions for isolation
- Regularly audit secret access

## References

- [Vault API Documentation](https://developer.hashicorp.com/vault/api-docs)
- [AppRole Auth Method](https://developer.hashicorp.com/vault/api-docs/auth/approle)
- [KV Secrets Engine](https://developer.hashicorp.com/vault/api-docs/secret/kv)
- [Database Secrets Engine](https://developer.hashicorp.com/vault/api-docs/secret/databases)
- [Spring Cloud Vault](https://spring.io/projects/spring-cloud-vault)

