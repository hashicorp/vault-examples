#!/bin/sh

set -e

echo "Waiting for Vault to be ready..."
until vault status > /dev/null 2>&1; do
    echo "Vault is not ready yet. Waiting..."
    sleep 2
done

echo "Vault is ready. Starting initialization..."

vault secrets enable -path=secret kv-v2 2>&1 || echo "KV secrets engine already enabled"

vault auth enable approle 2>&1 || echo "AppRole auth method already enabled"
POLICY_TMP=$(mktemp)
cat > "$POLICY_TMP" <<EOF
path "secret/data/mcp" {
  capabilities = ["read"]
}
path "secret/data/mcp/*" {
  capabilities = ["read"]
}
EOF
vault policy write mcp-read-policy "$POLICY_TMP" 2>&1 || true
rm -f "$POLICY_TMP"

vault write auth/approle/role/spring-boot-app \
    token_policies="mcp-read-policy" \
    token_ttl=1h \
    token_max_ttl=4h \
    secret_id_ttl=24h 2>&1 || true

CURRENT_ROLE_ID=$(vault read -field=role_id auth/approle/role/spring-boot-app/role-id 2>&1 || echo "")

ROLE_ID="demo-role-id-12345"
vault write auth/approle/role/spring-boot-app/role-id role_id="$ROLE_ID" 2>&1 || true

SECRET_ID="demo-secret-id-67890"

set +e
SECRET_ID_EXISTS=$(vault write auth/approle/role/spring-boot-app/custom-secret-id secret_id="$SECRET_ID" 2>&1)
SECRET_ID_EXIT=$?
set -e

if echo "$SECRET_ID_EXISTS" | grep -q "already registered"; then
    vault write auth/approle/role/spring-boot-app/secret-id/destroy secret_id="$SECRET_ID" 2>&1 || true
    vault write auth/approle/role/spring-boot-app/custom-secret-id secret_id="$SECRET_ID" 2>&1 || true
elif [ $SECRET_ID_EXIT -ne 0 ]; then
    vault write auth/approle/role/spring-boot-app/custom-secret-id secret_id="$SECRET_ID" 2>&1 || true
fi

API_KEY=$(head -c 32 /dev/urandom | base64 | tr -d '\n' | tr -d '=' | cut -c1-64)

# Store API key in secret/mcp (application-name path)
# ApiKeyProperties reads from secret/mcp with key "api-key"
vault kv put secret/mcp api-key="$API_KEY" 2>&1 || true

ENV_FILE="${ENV_FILE:-/workspace/.env}"
INSPECTOR_CONFIG="${INSPECTOR_CONFIG:-/workspace/inspector-config.json}"

cat > "$ENV_FILE" <<EOF
VAULT_ROLE_ID=${ROLE_ID}
VAULT_SECRET_ID=${SECRET_ID}
MCP_API_KEY=${API_KEY}
EOF

cat > "$INSPECTOR_CONFIG" <<EOF
{
  "mcpServers": {
    "spring-mcp": {
      "url": "http://app:8080/mcp",
      "headers": {
        "X-API-KEY": "${API_KEY}"
      }
    }
  }
}
EOF

echo "=========================================="
echo "Vault initialization completed!"
echo "=========================================="
echo "Role ID: $ROLE_ID"
echo "Secret ID: $SECRET_ID"
echo "API Key: $API_KEY"
echo "=========================================="
echo ""
echo "Vault Secret Path:"
echo "  secret/mcp (key: api-key)"
echo "  Read command: vault kv get -field=api-key secret/mcp"
echo ""
echo ".env file has been generated at: $ENV_FILE"
echo "MCP Inspector config has been generated at: $INSPECTOR_CONFIG"
