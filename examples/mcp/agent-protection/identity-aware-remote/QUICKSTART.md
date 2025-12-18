# Quick Start Guide

Korean Quick Start Guide is available [here](QUICKSTART(KR).md)

Prerequisites:
- Docker and Docker Compose installed
- curl and Python 3

## 1. Start Services

```bash
docker-compose up -d
```

## 2. Initialize Keycloak (wait approximately 30 seconds)

```bash
# Wait for Keycloak to be ready
sleep 30

# Initialize Keycloak
./init-keycloak.sh
```

## 3. Initialize Vault

```bash
# Initialize Vault
./init-vault.sh
```

This script automatically performs the following:
- Enables JWT authentication method
- Configures Keycloak integration
- Enables KV secrets engine (for Jira, Github)
- Enables Database secrets engine (for PostgreSQL)
- Configures PostgreSQL connection and creates dynamic roles
- Creates user-specific policies using Policy Templating
- Creates JWT role
- Initializes user-specific credentials (alice: Jira, Github, PostgreSQL / bob: Github, PostgreSQL)

## 4. Verify User Credentials (Optional)

The `init-vault.sh` script automatically creates credentials:
- **alice**: All credentials created (Jira, Github, PostgreSQL)
- **bob**: Only Github and PostgreSQL credentials created (no Jira - for demo purposes)

To verify credentials:

```bash
# Check Alice's credentials
docker exec -e VAULT_TOKEN=root-token vault vault kv get secret/users/alice/jira
docker exec -e VAULT_TOKEN=root-token vault vault kv get secret/users/alice/github
docker exec -e VAULT_TOKEN=root-token vault vault read database/roles/alice

# Check Bob's credentials
docker exec -e VAULT_TOKEN=root-token vault vault kv get secret/users/bob/github
docker exec -e VAULT_TOKEN=root-token vault vault read database/roles/bob
```

## 5. Access

Open http://localhost:8501 in your browser

**Login Information:**
- Username: `alice` / Password: `alice123`
- Username: `bob` / Password: `bob123`

## 6. Usage

1. **Login**: Authenticate with Keycloak
2. **Select MCP Server**: Select one or more MCP servers (multiple selection via checkboxes)
   - **Jira**: Manage Jira issues and projects
   - **Github**: Manage GitHub repositories and issues
   - **PostgreSQL**: Query and manage PostgreSQL database
3. **Click "Load Tools"**:
   - Load available tool list
   - **Authentication Flow Trace automatically displayed**
4. **Select and Execute Tools**: Select desired tool, enter parameters, and execute

## Authentication Flow Trace

The following information is automatically displayed when clicking "Load Tools":

- **Step 1-2**: User login and JWT issuance information
- **Step 3**: MCP server request status
- **Step 4-5**: Vault authentication and Entity information
- **Step 6**: Credential status for each MCP server
  - **User Information**: User ID (JWT's `sub`), Username, Email
  - **Vault Path**: Vault path where current user's credentials are stored
  - **Credentials (Masked)**: Masked credentials (partial display for security)
  - **Credential Existence**: Check if credentials exist for each MCP server

This allows you to verify that each user only retrieves their own credentials.

## Service Status Check

```bash
# All service status
docker-compose ps

# Specific service logs
docker-compose logs -f streamlit-client
docker-compose logs -f jira-mcp-server
docker-compose logs -f vault
```

## Troubleshooting

### Keycloak Not Starting
```bash
docker-compose logs keycloak
docker-compose restart keycloak
```

### Vault Configuration Error
```bash
docker exec -e VAULT_TOKEN=root-token vault vault status
docker-compose logs vault
```

### MCP Server Connection Error
```bash
docker-compose logs jira-mcp-server
docker-compose logs github-mcp-server
docker-compose logs postgresql-mcp-server
```

### Credential Retrieval Failure
```bash
# Check Vault policy
docker exec -e VAULT_TOKEN=root-token vault vault policy read user-secrets

# Check Vault logs
docker-compose logs vault
```

