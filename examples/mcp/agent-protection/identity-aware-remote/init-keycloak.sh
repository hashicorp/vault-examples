#!/bin/bash

set -e

echo "Initializing Keycloak..."

# Wait for Keycloak to be ready
echo "Waiting for Keycloak to be ready..."
# Check if Keycloak is ready by accessing the realms endpoint
until curl -f http://localhost:8080/realms/master > /dev/null 2>&1; do
  echo "Waiting for Keycloak..."
  sleep 5
done

echo "Keycloak is ready!"

# Get admin token
echo "Getting admin token..."
TOKEN=$(curl -s -X POST "http://localhost:8080/realms/master/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin" \
  -d "password=admin" \
  -d "grant_type=password" \
  -d "client_id=admin-cli" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

if [ -z "$TOKEN" ] || [ "$TOKEN" == "None" ]; then
  echo "Failed to get admin token"
  exit 1
fi

# Create realm
echo "Creating realm: mcp-demo..."
curl -s -X POST "http://localhost:8080/admin/realms" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "realm": "mcp-demo",
    "enabled": true,
    "displayName": "MCP Demo Realm"
  }' || echo "Realm may already exist"

# Create client
echo "Creating client: mcp-client..."
CLIENT_RESPONSE=$(curl -s -X POST "http://localhost:8080/admin/realms/mcp-demo/clients" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "clientId": "mcp-client",
    "enabled": true,
    "publicClient": false,
    "secret": "mcp-client-secret",
    "redirectUris": ["http://localhost:8501/*"],
    "webOrigins": ["*"],
    "protocol": "openid-connect",
    "attributes": {
      "access.token.lifespan": "3600"
    }
  }')

# Get client UUID
CLIENT_ID=$(curl -s -X GET "http://localhost:8080/admin/realms/mcp-demo/clients?clientId=mcp-client" \
  -H "Authorization: Bearer ${TOKEN}" | python3 -c "import sys, json; print(json.load(sys.stdin)[0]['id'])")

# Update client to include groups in token
echo "Updating client protocol mappers..."
curl -s -X POST "http://localhost:8080/admin/realms/mcp-demo/clients/${CLIENT_ID}/protocol-mappers/models" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "groups",
    "protocol": "openid-connect",
    "protocolMapper": "oidc-usermodel-realm-role-mapper",
    "config": {
      "claim.name": "groups",
      "jsonType.label": "String",
      "user.attribute": "groups",
      "id.token.claim": "true",
      "access.token.claim": "true"
    }
  }' || echo "Groups mapper may already exist"

# Add audience mapper to set audience to mcp-client
echo "Adding audience mapper..."
curl -s -X POST "http://localhost:8080/admin/realms/mcp-demo/clients/${CLIENT_ID}/protocol-mappers/models" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "audience-mapper",
    "protocol": "openid-connect",
    "protocolMapper": "oidc-audience-mapper",
    "config": {
      "included.client.audience": "mcp-client",
      "id.token.claim": "true",
      "access.token.claim": "true"
    }
  }' || echo "Audience mapper may already exist"

# Create users
echo "Creating users..."

# User 1: alice
echo "Creating user: alice..."
ALICE_RESPONSE=$(curl -s -X POST "http://localhost:8080/admin/realms/mcp-demo/users" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "email": "alice@example.com",
    "firstName": "Alice",
    "lastName": "Smith",
    "enabled": true,
    "credentials": [{
      "type": "password",
      "value": "alice123",
      "temporary": false
    }]
  }')

# Get alice user ID
sleep 2
ALICE_USER_ID=$(curl -s -X GET "http://localhost:8080/admin/realms/mcp-demo/users?username=alice" \
  -H "Authorization: Bearer ${TOKEN}" | python3 -c "import sys, json; users = json.load(sys.stdin); print(users[0]['id'] if users else '')" 2>/dev/null || echo "")

if [ -z "$ALICE_USER_ID" ]; then
  echo "Warning: Could not retrieve alice user ID"
else
  echo "alice user ID: $ALICE_USER_ID"
  echo "$ALICE_USER_ID" > /tmp/alice_user_id.txt
fi

# User 2: bob
echo "Creating user: bob..."
BOB_RESPONSE=$(curl -s -X POST "http://localhost:8080/admin/realms/mcp-demo/users" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "bob",
    "email": "bob@example.com",
    "firstName": "Bob",
    "lastName": "Jones",
    "enabled": true,
    "credentials": [{
      "type": "password",
      "value": "bob123",
      "temporary": false
    }]
  }')

# Get bob user ID
sleep 2
BOB_USER_ID=$(curl -s -X GET "http://localhost:8080/admin/realms/mcp-demo/users?username=bob" \
  -H "Authorization: Bearer ${TOKEN}" | python3 -c "import sys, json; users = json.load(sys.stdin); print(users[0]['id'] if users else '')" 2>/dev/null || echo "")

if [ -z "$BOB_USER_ID" ]; then
  echo "Warning: Could not retrieve bob user ID"
else
  echo "bob user ID: $BOB_USER_ID"
  echo "$BOB_USER_ID" > /tmp/bob_user_id.txt
fi

echo "Keycloak initialization completed!"
echo ""
echo "Users created:"
echo "  - alice / alice123 (ID: ${ALICE_USER_ID:-N/A})"
echo "  - bob / bob123 (ID: ${BOB_USER_ID:-N/A})"

