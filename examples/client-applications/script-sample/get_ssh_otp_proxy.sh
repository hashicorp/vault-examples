#!/bin/bash

# SSH OTP Generation Script via Vault Proxy

VAULT_PROXY_ADDR="http://127.0.0.1:8400"
VAULT_NAMESPACE=""  # Vault Namespace (set if needed, e.g., "my-namespace")
SSH_OTP_PATH="my-vault-app-ssh-otp/creds/otp-role"

# User configuration (modify as needed)
SSH_USERNAME="test1"
SSH_HOST="10.10.0.222"

echo "=== SSH OTP Generation via Vault Proxy ==="
echo "Vault Proxy: $VAULT_PROXY_ADDR"
echo "SSH OTP Path: $SSH_OTP_PATH"
echo "Target: $SSH_USERNAME@$SSH_HOST"
echo ""

# Generate SSH OTP
if [ -n "$VAULT_NAMESPACE" ]; then
    RESPONSE=$(curl -s -w "\n%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -H "X-Vault-Namespace: $VAULT_NAMESPACE" \
        -d "{\"ip\":\"$SSH_HOST\",\"username\":\"$SSH_USERNAME\"}" \
        "$VAULT_PROXY_ADDR/v1/$SSH_OTP_PATH")
else
    RESPONSE=$(curl -s -w "\n%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -d "{\"ip\":\"$SSH_HOST\",\"username\":\"$SSH_USERNAME\"}" \
        "$VAULT_PROXY_ADDR/v1/$SSH_OTP_PATH")
fi

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ SSH OTP generation successful"
    echo ""
    
    # Extract OTP key
    OTP_KEY=$(echo "$RESPONSE_BODY" | jq -r '.data.key')
    OTP_IP=$(echo "$RESPONSE_BODY" | jq -r '.data.ip')
    OTP_USERNAME=$(echo "$RESPONSE_BODY" | jq -r '.data.username')
    OTP_PORT=$(echo "$RESPONSE_BODY" | jq -r '.data.port // "22"')
    
    echo "📋 SSH OTP Information:"
    echo "  - OTP Key: $OTP_KEY"
    echo "  - Username: $OTP_USERNAME"
    echo "  - Host: $OTP_IP"
    echo "  - Port: $OTP_PORT"
    echo ""
    echo "🔐 SSH Connection Method:"
    echo "  ssh $OTP_USERNAME@$OTP_IP"
    echo "  Password: $OTP_KEY"
    echo ""
    echo "⚠️  Warning: OTP is single-use and can only be used once."
else
    echo "❌ SSH OTP generation failed (HTTP $HTTP_CODE)"
    echo "$RESPONSE_BODY" | jq -r '.errors[]' 2>/dev/null || echo "$RESPONSE_BODY"
    exit 1
fi

# Operation test
# sshpass -p "0fb11fc4-2cdf-17af-860d-40ccd633e6cd" ssh test@146.56.162.165 -p 22 \
#     -o StrictHostKeyChecking=no \
#     -o UserKnownHostsFile=/dev/null \
#     -o ConnectTimeout=5