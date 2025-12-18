#!/bin/bash

set -e

echo "Initializing Vault..."

# Wait for Vault to be ready
echo "Waiting for Vault to be ready..."
until docker exec -e VAULT_TOKEN=root-token vault vault status > /dev/null 2>&1; do
  sleep 2
done

echo "Vault is ready!"

# Wait for Keycloak to be ready (from host)
echo "Waiting for Keycloak to be ready..."
MAX_WAIT=60
WAIT_COUNT=0
until curl -f http://localhost:8080/realms/master > /dev/null 2>&1; do
  if [ $WAIT_COUNT -ge $MAX_WAIT ]; then
    echo "Error: Keycloak did not become ready within ${MAX_WAIT} seconds"
    exit 1
  fi
  echo "Waiting for Keycloak to start... ($WAIT_COUNT/$MAX_WAIT)"
  sleep 2
  WAIT_COUNT=$((WAIT_COUNT + 2))
done

echo "Keycloak is ready!"

# Wait for Keycloak realm to be ready
echo "Waiting for Keycloak realm to be ready..."
WAIT_COUNT=0
until curl -f http://localhost:8080/realms/mcp-demo/.well-known/openid-configuration > /dev/null 2>&1; do
  if [ $WAIT_COUNT -ge $MAX_WAIT ]; then
    echo "Error: Keycloak realm did not become ready within ${MAX_WAIT} seconds"
    echo "Please make sure init-keycloak.sh has been run"
    exit 1
  fi
  echo "Waiting for Keycloak realm... ($WAIT_COUNT/$MAX_WAIT)"
  sleep 2
  WAIT_COUNT=$((WAIT_COUNT + 2))
done

echo "Keycloak realm is ready!"

# Enable JWT auth
echo "Enabling JWT auth method..."
docker exec -e VAULT_TOKEN=root-token vault vault auth enable jwt 2>/dev/null || echo "JWT auth already enabled"

# Delete existing JWT config if it exists (to avoid conflicts)
echo "Clearing existing JWT config (if any)..."
docker exec -e VAULT_TOKEN=root-token vault vault delete auth/jwt/config 2>/dev/null || echo "No existing JWT config to clear"

# Configure JWT auth with Keycloak using jwks_url directly
echo "Configuring JWT auth with Keycloak..."
# Use jwks_url directly instead of oidc_discovery_url to avoid discovery URL issues
# The issuer in Keycloak's discovery doc is http://localhost:8080, but we access via keycloak:8080
# So we use jwks_url directly and set bound_issuer to match the actual issuer in tokens
docker exec -e VAULT_TOKEN=root-token vault vault write auth/jwt/config \
  jwks_url="http://keycloak:8080/realms/mcp-demo/protocol/openid-connect/certs" \
  bound_issuer="http://localhost:8080/realms/mcp-demo"

if [ $? -eq 0 ]; then
  echo "JWT auth configured successfully!"
else
  echo "Error: Failed to configure JWT auth"
  exit 1
fi

# Enable KV secrets engine
echo "Enabling KV secrets engine..."
docker exec -e VAULT_TOKEN=root-token vault vault secrets enable -version=2 -path=secret kv 2>/dev/null || echo "KV secrets engine already enabled"

# Enable Database secrets engine
echo "Enabling Database secrets engine..."
docker exec -e VAULT_TOKEN=root-token vault vault secrets enable database 2>/dev/null || echo "Database secrets engine already enabled"

# Create policy
echo "Creating user-secrets policy..."
# Using Entity name based templating
# Entity name is set to username (alice, bob) for easier management
# Entity alias name is set to Keycloak user ID (JWT 'sub' claim value)
# This allows using entity.name directly in the path for easier management
cat > /tmp/user-secrets-policy.hcl <<POLICY_EOF
path "secret/data/users/{{identity.entity.name}}/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/users/{{identity.entity.name}}/*" {
  capabilities = ["list"]
}

# Allow users to read their own entity information
path "identity/entity/name/{{identity.entity.name}}" {
  capabilities = ["read"]
}

# Allow users to get database credentials for their own role
path "database/creds/{{identity.entity.name}}" {
  capabilities = ["read"]
}

# Allow users to read their own database role definition (for verification)
path "database/roles/{{identity.entity.name}}" {
  capabilities = ["read"]
}
POLICY_EOF

# Copy policy file to vault container and apply
docker cp /tmp/user-secrets-policy.hcl vault:/tmp/user-secrets-policy.hcl
docker exec -e VAULT_TOKEN=root-token vault vault policy write user-secrets /tmp/user-secrets-policy.hcl
rm -f /tmp/user-secrets-policy.hcl

# Get JWT mount accessor for entity alias creation
echo "Getting JWT mount accessor..."
JWT_ACCESSOR=$(docker exec -e VAULT_TOKEN=root-token vault vault read -field=accessor sys/auth/jwt 2>/dev/null || echo "")
if [ -z "$JWT_ACCESSOR" ]; then
  echo "Error: Could not get JWT accessor"
  exit 1
fi
echo "JWT accessor: $JWT_ACCESSOR"

# Clean up any existing auto-generated entities and aliases
echo "Cleaning up any existing auto-generated entities and aliases..."
echo "This ensures we create entities with proper names (alice, bob) instead of auto-generated names"

# Get all existing entities
EXISTING_ENTITIES=$(docker exec -e VAULT_TOKEN=root-token vault vault list -format=json identity/entity/name 2>/dev/null || echo "[]")
for entity_name in $(echo "$EXISTING_ENTITIES" | python3 -c "import sys, json; [print(name) for name in json.load(sys.stdin)]" 2>/dev/null); do
  if [ -n "$entity_name" ]; then
    # Check if this is an auto-generated entity name (starts with "entity_")
    if echo "$entity_name" | grep -q "^entity_"; then
      echo "Found auto-generated entity: $entity_name, deleting it..."
      # Get entity ID first to delete associated aliases
      ENTITY_DATA=$(docker exec -e VAULT_TOKEN=root-token vault vault read -format=json identity/entity/name/$entity_name 2>/dev/null || echo "{}")
      ENTITY_ID=$(echo "$ENTITY_DATA" | python3 -c "import sys, json; print(json.load(sys.stdin).get('data', {}).get('id', ''))" 2>/dev/null || echo "")
      if [ -n "$ENTITY_ID" ]; then
        # Delete all aliases for this entity
        ALIAS_LIST=$(docker exec -e VAULT_TOKEN=root-token vault vault list -format=json identity/entity-alias/id 2>/dev/null || echo "[]")
        for alias_id in $(echo "$ALIAS_LIST" | python3 -c "import sys, json; [print(aid) for aid in json.load(sys.stdin)]" 2>/dev/null); do
          if [ -n "$alias_id" ]; then
            ALIAS_DATA=$(docker exec -e VAULT_TOKEN=root-token vault vault read -format=json identity/entity-alias/id/$alias_id 2>/dev/null || echo "{}")
            ALIAS_CANONICAL_ID=$(echo "$ALIAS_DATA" | python3 -c "import sys, json; print(json.load(sys.stdin).get('data', {}).get('canonical_id', ''))" 2>/dev/null || echo "")
            if [ "$ALIAS_CANONICAL_ID" = "$ENTITY_ID" ]; then
              echo "  Deleting alias: $alias_id"
              docker exec -e VAULT_TOKEN=root-token vault vault delete identity/entity-alias/id/$alias_id 2>/dev/null || true
            fi
          fi
        done
      fi
      # Delete the entity
      docker exec -e VAULT_TOKEN=root-token vault vault delete identity/entity/name/$entity_name 2>/dev/null || true
    fi
  fi
done

# Create entities for Keycloak users
echo "Creating Vault entities for Keycloak users..."

# Get Keycloak admin token
echo "Getting Keycloak admin token..."
KC_TOKEN=""
RETRY_COUNT=0
MAX_RETRIES=5

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
  KC_TOKEN=$(curl -s -X POST "http://localhost:8080/realms/master/protocol/openid-connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=admin" \
    -d "password=admin" \
    -d "grant_type=password" \
    -d "client_id=admin-cli" 2>/dev/null | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('access_token', ''))" 2>/dev/null || echo "")
  
  if [ -n "$KC_TOKEN" ] && [ "$KC_TOKEN" != "None" ] && [ "$KC_TOKEN" != "" ]; then
    break
  fi
  
  RETRY_COUNT=$((RETRY_COUNT + 1))
  if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
    echo "Retrying to get Keycloak token... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 3
  fi
done

if [ -z "$KC_TOKEN" ] || [ "$KC_TOKEN" == "None" ] || [ "$KC_TOKEN" == "" ]; then
  echo "Warning: Could not get Keycloak token after $MAX_RETRIES attempts, skipping entity creation"
  echo "This is not critical - entities will be created automatically on first login"
else
  # Get users from Keycloak
  echo "Fetching users from Keycloak..."
  CURL_OUTPUT=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X GET "http://localhost:8080/admin/realms/mcp-demo/users" \
    -H "Authorization: Bearer ${KC_TOKEN}" 2>&1)
  
  # Extract HTTP status code
  HTTP_CODE=$(echo "$CURL_OUTPUT" | grep "HTTP_CODE:" | sed 's/.*HTTP_CODE://')
  USERS_JSON=$(echo "$CURL_OUTPUT" | sed '/HTTP_CODE:/d')
  
  # Check if curl failed
  if [ -z "$HTTP_CODE" ]; then
    echo "Error: Failed to connect to Keycloak"
    echo "Output: $CURL_OUTPUT"
    exit 1
  fi
  
  # Check HTTP status code
  if [ "$HTTP_CODE" != "200" ]; then
    echo "Error: Failed to fetch users from Keycloak (HTTP $HTTP_CODE)"
    if [ -n "$USERS_JSON" ]; then
      echo "Response: $(echo "$USERS_JSON" | head -c 200)"
    fi
    exit 1
  fi
  
  # Check if response is empty
  if [ -z "$USERS_JSON" ] || [ "$USERS_JSON" = "" ]; then
    echo "Error: Empty response from Keycloak"
    echo "Make sure init-keycloak.sh has been run successfully and users exist"
    exit 1
  fi
  
  # Parse users and create entities using a temporary file to avoid subshell issues
  echo "Parsing users from Keycloak..."
  
  # Check if we got valid JSON
  if ! echo "$USERS_JSON" | python3 -c "import sys, json; json.load(sys.stdin)" 2>/dev/null; then
    echo "Error: Invalid JSON response from Keycloak"
    echo "Response (first 500 chars): $(echo "$USERS_JSON" | head -c 500)"
    exit 1
  fi
  
  # Parse users using Python (simpler inline approach)
  echo "Extracting user information..."
  TEMP_USERS_FILE=$(mktemp)
  TEMP_PYTHON_SCRIPT=$(mktemp)
  
  # Create Python script to avoid quote escaping issues
  cat > "$TEMP_PYTHON_SCRIPT" <<'PYEOF'
import sys, json
try:
    users = json.load(sys.stdin)
    count = 0
    for user in users:
        uid = user.get('id', '')
        uname = user.get('username', '')
        if uid and uname:
            count += 1
            print('{}|{}'.format(uid, uname))
    if count == 0:
        print('ERROR: No users found', file=sys.stderr)
        sys.exit(1)
except Exception as e:
    print('ERROR: {}'.format(e), file=sys.stderr)
    sys.exit(1)
PYEOF
  
  echo "$USERS_JSON" | python3 "$TEMP_PYTHON_SCRIPT" > "$TEMP_USERS_FILE" 2>&1
  PYTHON_EXIT_CODE=$?
  
  # Clean up Python script
  rm -f "$TEMP_PYTHON_SCRIPT"
  
  if [ $PYTHON_EXIT_CODE -ne 0 ]; then
    PYTHON_ERROR=$(cat "$TEMP_USERS_FILE" 2>&1)
    echo "Error: Failed to parse users from Keycloak"
    echo "Python error: $PYTHON_ERROR"
    echo "JSON response length: $(echo "$USERS_JSON" | wc -c) bytes"
    rm -f "$TEMP_USERS_FILE"
    exit 1
  fi
  
  # Verify temp file was created and has content
  if [ ! -f "$TEMP_USERS_FILE" ]; then
    echo "Error: Temporary users file was not created"
    exit 1
  fi
  
  USER_COUNT=$(wc -l < "$TEMP_USERS_FILE" 2>/dev/null | tr -d ' ' || echo "0")
  if [ -z "$USER_COUNT" ] || [ "$USER_COUNT" = "0" ]; then
    echo "Warning: No users found in Keycloak realm 'mcp-demo'"
    echo "Make sure init-keycloak.sh has been run successfully"
    echo "Temp file content: $(cat "$TEMP_USERS_FILE" 2>/dev/null || echo 'empty')"
    rm -f "$TEMP_USERS_FILE"
    exit 1
  fi
  
  echo "Found $USER_COUNT user(s) in Keycloak:"
  while IFS='|' read -r user_id username; do
    if [ -n "$user_id" ] && [ -n "$username" ]; then
      echo "  - $username (ID: $user_id)"
    fi
  done < "$TEMP_USERS_FILE"

  # Process each user from the temp file
  while IFS='|' read -r user_id username; do
    if [ -n "$user_id" ] && [ -n "$username" ]; then
      echo ""
      echo "=== Processing user: $username (Keycloak ID: $user_id) ==="
      
      # Delete existing entity if it exists (by name) and all its aliases
      echo "Step 1: Cleaning up existing entity (if any) for username: $username..."
      EXISTING_ENTITY_READ=$(docker exec -e VAULT_TOKEN=root-token vault vault read -format=json identity/entity/name/$username 2>/dev/null || echo "{}")
      EXISTING_ENTITY_ID=$(echo "$EXISTING_ENTITY_READ" | python3 -c "import sys, json; print(json.load(sys.stdin).get('data', {}).get('id', ''))" 2>/dev/null || echo "")
      if [ -n "$EXISTING_ENTITY_ID" ]; then
        echo "  Found existing entity: $EXISTING_ENTITY_ID, deleting all aliases..."
        # Delete all aliases for this entity
        ALIAS_LIST=$(docker exec -e VAULT_TOKEN=root-token vault vault list -format=json identity/entity-alias/id 2>/dev/null || echo "[]")
        for alias_id in $(echo "$ALIAS_LIST" | python3 -c "import sys, json; [print(aid) for aid in json.load(sys.stdin)]" 2>/dev/null); do
          if [ -n "$alias_id" ]; then
            ALIAS_DATA=$(docker exec -e VAULT_TOKEN=root-token vault vault read -format=json identity/entity-alias/id/$alias_id 2>/dev/null || echo "{}")
            ALIAS_CANONICAL_ID=$(echo "$ALIAS_DATA" | python3 -c "import sys, json; print(json.load(sys.stdin).get('data', {}).get('canonical_id', ''))" 2>/dev/null || echo "")
            if [ "$ALIAS_CANONICAL_ID" = "$EXISTING_ENTITY_ID" ]; then
              echo "    Deleting alias: $alias_id"
              docker exec -e VAULT_TOKEN=root-token vault vault delete identity/entity-alias/id/$alias_id 2>/dev/null || true
            fi
          fi
        done
        echo "  Deleting entity: $username"
        docker exec -e VAULT_TOKEN=root-token vault vault delete identity/entity/name/$username 2>/dev/null || true
        sleep 1
      else
        echo "  No existing entity found for username: $username"
      fi
      
      # Also check for any alias with this user_id and delete it
      echo "Step 2: Cleaning up any alias with user_id: $user_id..."
      ALIAS_LIST=$(docker exec -e VAULT_TOKEN=root-token vault vault list -format=json identity/entity-alias/id 2>/dev/null || echo "[]")
      for alias_id in $(echo "$ALIAS_LIST" | python3 -c "import sys, json; [print(aid) for aid in json.load(sys.stdin)]" 2>/dev/null); do
        if [ -n "$alias_id" ]; then
          ALIAS_DATA=$(docker exec -e VAULT_TOKEN=root-token vault vault read -format=json identity/entity-alias/id/$alias_id 2>/dev/null || echo "{}")
          ALIAS_NAME=$(echo "$ALIAS_DATA" | python3 -c "import sys, json; print(json.load(sys.stdin).get('data', {}).get('name', ''))" 2>/dev/null || echo "")
          if [ "$ALIAS_NAME" = "$user_id" ]; then
            echo "  Found existing alias with user_id: $alias_id, deleting it..."
            docker exec -e VAULT_TOKEN=root-token vault vault delete identity/entity-alias/id/$alias_id 2>/dev/null || true
          fi
        fi
      done
      
      # Create entity with name = username (for easier management)
      echo "Step 3: Creating entity with name: $username..."
      ENTITY_RESPONSE=$(docker exec -e VAULT_TOKEN=root-token vault vault write -format=json identity/entity \
        name="$username" \
        metadata=user_id="$user_id" \
        metadata=source="keycloak" 2>&1)
      
      # Get entity ID
      ENTITY_ID=$(echo "$ENTITY_RESPONSE" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('data', {}).get('id', ''))" 2>/dev/null || echo "")
      
      # Verify entity was created
      if [ -z "$ENTITY_ID" ]; then
        echo "  Warning: Entity creation response did not contain ID, checking if entity exists..."
        sleep 1
        ENTITY_READ=$(docker exec -e VAULT_TOKEN=root-token vault vault read -format=json identity/entity/name/$username 2>/dev/null || echo "{}")
        ENTITY_ID=$(echo "$ENTITY_READ" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('data', {}).get('id', ''))" 2>/dev/null || echo "")
        if [ -z "$ENTITY_ID" ]; then
          echo "  ✗ Error: Failed to create or find entity for username: $username"
          echo "  Response: $ENTITY_RESPONSE"
          continue
        fi
      fi
      
      echo "  ✓ Entity created successfully: $ENTITY_ID (name: $username)"
      
      if [ -n "$ENTITY_ID" ]; then
        # Attach policy to entity first (before creating alias)
        echo "Step 4: Attaching policy 'user-secrets' to entity: $username..."
        POLICY_ATTACH_RESPONSE=$(docker exec -e VAULT_TOKEN=root-token vault vault write identity/entity/id/$ENTITY_ID \
          policies="user-secrets" 2>&1)
        if echo "$POLICY_ATTACH_RESPONSE" | grep -q "error"; then
          echo "  ⚠ Warning: Failed to attach policy, but continuing..."
          echo "  Response: $POLICY_ATTACH_RESPONSE"
        else
          echo "  ✓ Policy 'user-secrets' attached to entity"
        fi
        
        # Create entity alias (name = Keycloak user ID, which matches JWT 'sub' claim)
        echo "Step 5: Creating entity alias (name: $user_id, matches JWT 'sub' claim)..."
        ALIAS_RESPONSE=$(docker exec -e VAULT_TOKEN=root-token vault vault write -format=json identity/entity-alias \
          name="$user_id" \
          canonical_id="$ENTITY_ID" \
          mount_accessor="$JWT_ACCESSOR" 2>&1)
        
        # Check if alias was created successfully
        ALIAS_ID=$(echo "$ALIAS_RESPONSE" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('data', {}).get('id', ''))" 2>/dev/null || echo "")
        
        if [ -z "$ALIAS_ID" ]; then
          # Check if alias already exists by searching all aliases
          echo "  Alias creation returned no ID, checking if alias already exists..."
          sleep 1
          EXISTING_ALIAS=""
          ALIAS_LIST=$(docker exec -e VAULT_TOKEN=root-token vault vault list -format=json identity/entity-alias/id 2>/dev/null || echo "[]")
          for alias_id in $(echo "$ALIAS_LIST" | python3 -c "import sys, json; [print(aid) for aid in json.load(sys.stdin)]" 2>/dev/null); do
            if [ -n "$alias_id" ]; then
              ALIAS_DATA=$(docker exec -e VAULT_TOKEN=root-token vault vault read -format=json identity/entity-alias/id/$alias_id 2>/dev/null || echo "{}")
              ALIAS_NAME=$(echo "$ALIAS_DATA" | python3 -c "import sys, json; print(json.load(sys.stdin).get('data', {}).get('name', ''))" 2>/dev/null || echo "")
              ALIAS_CANONICAL_ID=$(echo "$ALIAS_DATA" | python3 -c "import sys, json; print(json.load(sys.stdin).get('data', {}).get('canonical_id', ''))" 2>/dev/null || echo "")
              if [ "$ALIAS_NAME" = "$user_id" ] && [ "$ALIAS_CANONICAL_ID" = "$ENTITY_ID" ]; then
                EXISTING_ALIAS="$alias_id"
                break
              fi
            fi
          done
          
          if [ -n "$EXISTING_ALIAS" ]; then
            echo "  ✓ Entity alias already exists: $EXISTING_ALIAS"
            ALIAS_ID="$EXISTING_ALIAS"
          else
            echo "  ✗ Error: Failed to create alias for user $username"
            echo "  Response: $ALIAS_RESPONSE"
            # Try to read the error details
            if echo "$ALIAS_RESPONSE" | grep -q "error"; then
              ERROR_MSG=$(echo "$ALIAS_RESPONSE" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('errors', ['Unknown error'])[0])" 2>/dev/null || echo "Unknown error")
              echo "  Error message: $ERROR_MSG"
            fi
            echo "  ⚠ Continuing anyway - alias may be created on first login"
          fi
        else
          echo "  ✓ Entity alias created successfully: $ALIAS_ID"
        fi
        
        # Verify alias is correctly linked to entity
        if [ -n "$ALIAS_ID" ]; then
          echo "Step 6: Verifying alias configuration..."
          VERIFY_ALIAS=$(docker exec -e VAULT_TOKEN=root-token vault vault read -format=json identity/entity-alias/id/$ALIAS_ID 2>/dev/null | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('data', {}).get('canonical_id', ''))" 2>/dev/null || echo "")
          if [ "$VERIFY_ALIAS" = "$ENTITY_ID" ]; then
            echo "  ✓ Verified: Entity alias correctly linked to entity $ENTITY_ID"
          else
            echo "  ⚠ Warning: Entity alias verification failed (canonical_id mismatch)"
          fi
          
          # Verify entity has policy
          ENTITY_VERIFY=$(docker exec -e VAULT_TOKEN=root-token vault vault read -format=json identity/entity/name/$username 2>/dev/null || echo "{}")
          ENTITY_POLICIES=$(echo "$ENTITY_VERIFY" | python3 -c "import sys, json; print(','.join(json.load(sys.stdin).get('data', {}).get('policies', [])))" 2>/dev/null || echo "")
          if echo "$ENTITY_POLICIES" | grep -q "user-secrets"; then
            echo "  ✓ Verified: Policy 'user-secrets' is attached to entity"
          else
            echo "  ⚠ Warning: Policy 'user-secrets' is not attached to entity"
            echo "  Attempting to attach policy again..."
            docker exec -e VAULT_TOKEN=root-token vault vault write identity/entity/id/$ENTITY_ID \
              policies="user-secrets" 2>&1 | grep -v "WARNING" || true
          fi
        fi
        
        echo "  ✓ User $username setup completed successfully!"
        echo ""
      else
        echo "Warning: Could not create or find entity for user: $username"
      fi
    fi
  done < "$TEMP_USERS_FILE"
  
  # Clean up temp file
  rm -f "$TEMP_USERS_FILE"
  echo "Entity creation process completed for all users."
fi

# Create JWT role
echo "Creating JWT role..."
# user_claim="sub" sets the Entity alias name to JWT's 'sub' claim value
# Vault will automatically find existing entities with matching alias name and use them
docker exec -e VAULT_TOKEN=root-token vault vault write auth/jwt/role/user \
  role_type="jwt" \
  bound_audiences="mcp-client,account" \
  user_claim="sub" \
  groups_claim="groups" \
  policies="user-secrets" \
  ttl=1h \
  max_ttl=24h

# Create Jira secrets for alice user only (for comparison with bob)
echo "Creating Jira secrets for alice user only..."

# Entity name is now username, so use "alice" directly
# Note: vault kv put automatically adds "data/" prefix for KV v2, so use "secret/users/..." not "secret/data/users/..."
echo "Creating Jira secret for alice (entity name: alice)..."
docker exec -e VAULT_TOKEN=root-token vault vault kv put secret/users/alice/jira \
  username="alice-jira" \
  password="alice-jira-password" \
  api_token="alice-jira-token-12345" 2>&1
if [ $? -eq 0 ]; then
  echo "Jira secret created for alice at path: secret/data/users/alice/jira"
else
  echo "Warning: Failed to create Jira secret for alice"
fi

echo "Bob user will not have Jira secret (for comparison)"

echo "Creating GitHub secrets for alice and bob users..."

# Create GitHub secret for alice
echo "Creating GitHub secret for alice (entity name: alice)..."
docker exec -e VAULT_TOKEN=root-token vault vault kv put secret/users/alice/github \
  token="alice-github-token-12345" \
  username="alice-github" 2>&1
if [ $? -eq 0 ]; then
  echo "GitHub secret created for alice at path: secret/data/users/alice/github"
else
  echo "Warning: Failed to create GitHub secret for alice"
fi

# Create GitHub secret for bob
echo "Creating GitHub secret for bob (entity name: bob)..."
docker exec -e VAULT_TOKEN=root-token vault vault kv put secret/users/bob/github \
  token="bob-github-token-67890" \
  username="bob-github" 2>&1
if [ $? -eq 0 ]; then
  echo "GitHub secret created for bob at path: secret/data/users/bob/github"
else
  echo "Warning: Failed to create GitHub secret for bob"
fi

# Configure PostgreSQL connection in Database secrets engine
echo "Configuring PostgreSQL connection in Database secrets engine..."

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
MAX_WAIT=60
WAIT_COUNT=0
until docker exec postgresql pg_isready -U postgres > /dev/null 2>&1; do
  if [ $WAIT_COUNT -ge $MAX_WAIT ]; then
    echo "Error: PostgreSQL did not become ready within ${MAX_WAIT} seconds"
    exit 1
  fi
  echo "Waiting for PostgreSQL to start... ($WAIT_COUNT/$MAX_WAIT)"
  sleep 2
  WAIT_COUNT=$((WAIT_COUNT + 2))
done

echo "PostgreSQL is ready!"

# Configure PostgreSQL plugin connection
echo "Configuring PostgreSQL plugin connection..."
docker exec -e VAULT_TOKEN=root-token vault vault write database/config/postgresql \
  plugin_name=postgresql-database-plugin \
  allowed_roles="*" \
  connection_url="postgresql://{{username}}:{{password}}@postgresql:5432/mcp_demo?sslmode=disable" \
  username="vault_admin" \
  password="vault-admin-password-12345" \
  verify_connection=false 2>&1

if [ $? -eq 0 ]; then
  echo "PostgreSQL connection configured successfully!"
else
  echo "Warning: Failed to configure PostgreSQL connection"
fi

# Create dynamic roles for alice and bob
echo "Creating PostgreSQL dynamic roles for alice and bob users..."

# Create role for alice
echo "Creating PostgreSQL role for alice (entity name: alice)..."
ROLE_CREATE_OUTPUT=$(docker exec -e VAULT_TOKEN=root-token vault vault write database/roles/alice \
  db_name=postgresql \
  creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; GRANT USAGE ON SCHEMA public TO \"{{name}}\"; GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO \"{{name}}\"; GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO \"{{name}}\"; ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO \"{{name}}\"; ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO \"{{name}}\";" \
  revocation_statements="REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM \"{{name}}\"; REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM \"{{name}}\"; REVOKE USAGE ON SCHEMA public FROM \"{{name}}\"; DROP ROLE IF EXISTS \"{{name}}\";" \
  default_ttl="1h" \
  max_ttl="24h" 2>&1)

if [ $? -eq 0 ]; then
  echo "PostgreSQL role created for alice"
  # Verify role was created
  ROLE_VERIFY=$(docker exec -e VAULT_TOKEN=root-token vault vault read database/roles/alice 2>&1)
  if echo "$ROLE_VERIFY" | grep -q "db_name"; then
    echo "✓ Verified: PostgreSQL role 'alice' exists in Vault"
  else
    echo "⚠ Warning: PostgreSQL role 'alice' may not have been created correctly"
  fi
else
  echo "Error: Failed to create PostgreSQL role for alice"
  echo "Output: $ROLE_CREATE_OUTPUT"
fi

# Create role for bob
echo "Creating PostgreSQL role for bob (entity name: bob)..."
ROLE_CREATE_OUTPUT=$(docker exec -e VAULT_TOKEN=root-token vault vault write database/roles/bob \
  db_name=postgresql \
  creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; GRANT USAGE ON SCHEMA public TO \"{{name}}\"; GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO \"{{name}}\"; GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO \"{{name}}\"; ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO \"{{name}}\"; ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO \"{{name}}\";" \
  revocation_statements="REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM \"{{name}}\"; REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM \"{{name}}\"; REVOKE USAGE ON SCHEMA public FROM \"{{name}}\"; DROP ROLE IF EXISTS \"{{name}}\";" \
  default_ttl="1h" \
  max_ttl="24h" 2>&1)

if [ $? -eq 0 ]; then
  echo "PostgreSQL role created for bob"
  # Verify role was created
  ROLE_VERIFY=$(docker exec -e VAULT_TOKEN=root-token vault vault read database/roles/bob 2>&1)
  if echo "$ROLE_VERIFY" | grep -q "db_name"; then
    echo "✓ Verified: PostgreSQL role 'bob' exists in Vault"
  else
    echo "⚠ Warning: PostgreSQL role 'bob' may not have been created correctly"
  fi
else
  echo "Error: Failed to create PostgreSQL role for bob"
  echo "Output: $ROLE_CREATE_OUTPUT"
fi

# List all database roles for verification
echo "Listing all database roles for verification..."
docker exec -e VAULT_TOKEN=root-token vault vault list database/roles 2>&1

# Verify entities and aliases were created correctly
echo ""
echo "=== Verifying Entity and Alias Configuration ==="
echo "Fetching users from Keycloak for verification..."
KC_TOKEN=""
if [ -n "$KC_TOKEN" ] || [ "$KC_TOKEN" != "None" ]; then
  KC_TOKEN=$(curl -s -X POST "http://localhost:8080/realms/master/protocol/openid-connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=admin" \
    -d "password=admin" \
    -d "grant_type=password" \
    -d "client_id=admin-cli" 2>/dev/null | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('access_token', ''))" 2>/dev/null || echo "")
fi

if [ -n "$KC_TOKEN" ] && [ "$KC_TOKEN" != "None" ] && [ "$KC_TOKEN" != "" ]; then
  USERS_JSON=$(curl -s -X GET "http://localhost:8080/admin/realms/mcp-demo/users" \
    -H "Authorization: Bearer ${KC_TOKEN}")
  
  echo "$USERS_JSON" | python3 <<PYTHON_SCRIPT | while IFS='|' read -r user_id username; do
import sys
import json

try:
    users = json.load(sys.stdin)
    for user in users:
        user_id = user.get('id', '')
        username = user.get('username', '')
        if user_id and username:
            print(f"{user_id}|{username}")
except Exception as e:
    pass
PYTHON_SCRIPT
    if [ -n "$user_id" ] && [ -n "$username" ]; then
      echo ""
      echo "Verifying entity for user: $username (Keycloak ID: $user_id)"
      
      # Check entity exists
      ENTITY_DATA=$(docker exec -e VAULT_TOKEN=root-token vault vault read -format=json identity/entity/name/$username 2>/dev/null || echo "{}")
      ENTITY_ID=$(echo "$ENTITY_DATA" | python3 -c "import sys, json; print(json.load(sys.stdin).get('data', {}).get('id', ''))" 2>/dev/null || echo "")
      
      if [ -n "$ENTITY_ID" ]; then
        echo "  ✓ Entity exists: $ENTITY_ID (name: $username)"
        
        # Check entity has policy attached
        ENTITY_POLICIES=$(echo "$ENTITY_DATA" | python3 -c "import sys, json; print(','.join(json.load(sys.stdin).get('data', {}).get('policies', [])))" 2>/dev/null || echo "")
        if echo "$ENTITY_POLICIES" | grep -q "user-secrets"; then
          echo "  ✓ Policy 'user-secrets' is attached to entity"
        else
          echo "  ⚠ Warning: Policy 'user-secrets' is not attached to entity"
        fi
        
        # Check alias exists
        ALIAS_FOUND=false
        ALIAS_LIST=$(docker exec -e VAULT_TOKEN=root-token vault vault list -format=json identity/entity-alias/id 2>/dev/null || echo "[]")
        for alias_id in $(echo "$ALIAS_LIST" | python3 -c "import sys, json; [print(aid) for aid in json.load(sys.stdin)]" 2>/dev/null); do
          if [ -n "$alias_id" ]; then
            ALIAS_DATA=$(docker exec -e VAULT_TOKEN=root-token vault vault read -format=json identity/entity-alias/id/$alias_id 2>/dev/null || echo "{}")
            ALIAS_NAME=$(echo "$ALIAS_DATA" | python3 -c "import sys, json; print(json.load(sys.stdin).get('data', {}).get('name', ''))" 2>/dev/null || echo "")
            ALIAS_CANONICAL_ID=$(echo "$ALIAS_DATA" | python3 -c "import sys, json; print(json.load(sys.stdin).get('data', {}).get('canonical_id', ''))" 2>/dev/null || echo "")
            if [ "$ALIAS_NAME" = "$user_id" ] && [ "$ALIAS_CANONICAL_ID" = "$ENTITY_ID" ]; then
              echo "  ✓ Entity alias exists: $alias_id (name: $user_id, matches JWT 'sub' claim)"
              ALIAS_FOUND=true
              break
            fi
          fi
        done
        
        if [ "$ALIAS_FOUND" = false ]; then
          echo "  ✗ Error: Entity alias not found for user_id: $user_id"
          echo "    This will cause authentication failures!"
        fi
      else
        echo "  ✗ Error: Entity not found for username: $username"
        echo "    This will cause authentication failures!"
      fi
    fi
  done
else
  echo "Skipping entity verification (could not get Keycloak token)"
fi

echo ""
echo "Vault initialization completed!"

