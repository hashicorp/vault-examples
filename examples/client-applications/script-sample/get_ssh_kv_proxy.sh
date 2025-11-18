#!/bin/bash

# SSH KV Credential Retrieval and Connection Script via Vault Proxy

VAULT_PROXY_ADDR="http://127.0.0.1:8400"
VAULT_NAMESPACE=""  # Vault Namespace (set if needed, e.g., "my-namespace")
DEFAULT_SSH_HOST="10.10.0.222"
SSH_HOST="${1:-$DEFAULT_SSH_HOST}"
KV_PATH="my-vault-app-kv/data/ssh/$SSH_HOST"

echo "=== SSH KV Credential Retrieval via Vault Proxy ==="
echo "Vault Proxy: $VAULT_PROXY_ADDR"
echo "KV Path: $KV_PATH"
echo "Target Host: $SSH_HOST"
echo ""

# Retrieve SSH credentials from KV
if [ -n "$VAULT_NAMESPACE" ]; then
    RESPONSE=$(curl -s -w "\n%{http_code}" \
        -H "X-Vault-Namespace: $VAULT_NAMESPACE" \
        "$VAULT_PROXY_ADDR/v1/$KV_PATH")
else
    RESPONSE=$(curl -s -w "\n%{http_code}" \
        "$VAULT_PROXY_ADDR/v1/$KV_PATH")
fi

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ SSH KV credential retrieval successful"
    echo ""
    
    # Extract username and password
    SSH_USERNAME=$(echo "$RESPONSE_BODY" | jq -r '.data.data.ssh_username')
    SSH_PASSWORD=$(echo "$RESPONSE_BODY" | jq -r '.data.data.ssh_password')
    
    echo "📋 SSH Credential Information:"
    echo "  - Host: $SSH_HOST"
    echo "  - Username: $SSH_USERNAME"
    echo "  - Password: $SSH_PASSWORD"
    echo ""
else
    echo "❌ SSH KV credential retrieval failed (HTTP $HTTP_CODE)"
    echo "$RESPONSE_BODY" | jq -r '.errors[]' 2>/dev/null || echo "$RESPONSE_BODY"
    echo ""
    echo "🔧 Troubleshooting:"
    echo "1. Check KV path: $KV_PATH"
    echo "2. Check Vault Proxy status: $VAULT_PROXY_ADDR"
    echo "3. Verify KV data exists:"
    echo "   vault kv get my-vault-app-kv/ssh/$SSH_HOST"
    exit 1
fi

# Check sshpass and auto-connect
# sshpass -p "$SSH_PASSWORD" ssh \
#     -o StrictHostKeyChecking=no \
#     -o UserKnownHostsFile=/dev/null \
#     -o ConnectTimeout=5 \
#     -o ConnectionAttempts=1 \
#     "$SSH_USERNAME@$SSH_HOST"