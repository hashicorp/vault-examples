#!/bin/bash

# SSH Signed Certificate Generation Script via Vault Proxy

VAULT_PROXY_ADDR="http://127.0.0.1:8400"
VAULT_NAMESPACE=""  # Vault Namespace (set if needed, e.g., "my-namespace")
SSH_CA_PATH="my-vault-app-ssh-ca/sign/client-signer"

# User configuration (modify as needed)
SSH_USERNAME="test2"
SSH_PUBLIC_KEY_PATH="$HOME/.ssh/vault_rsa.pub"

echo "=== SSH Signed Certificate Generation via Vault Proxy ==="
echo "Vault Proxy: $VAULT_PROXY_ADDR"
echo "SSH CA Path: $SSH_CA_PATH"
echo "Username: $SSH_USERNAME"
echo "Public Key: $SSH_PUBLIC_KEY_PATH"
echo ""

# Read Public Key
if [ ! -f "$SSH_PUBLIC_KEY_PATH" ]; then
    echo "❌ Public key file not found: $SSH_PUBLIC_KEY_PATH"
    echo "Generate SSH key with the following command:"
    echo "  ssh-keygen -t rsa -C \"test@rocky\" -f ~/.ssh/vault_rsa"
    exit 1
fi

PUBLIC_KEY=$(cat "$SSH_PUBLIC_KEY_PATH")

# Generate SSH Signed Certificate
if [ -n "$VAULT_NAMESPACE" ]; then
    RESPONSE=$(curl -s -w "\n%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -H "X-Vault-Namespace: $VAULT_NAMESPACE" \
        -d "{\"public_key\":\"$PUBLIC_KEY\",\"valid_principals\":\"$SSH_USERNAME\"}" \
        "$VAULT_PROXY_ADDR/v1/$SSH_CA_PATH")
else
    RESPONSE=$(curl -s -w "\n%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -d "{\"public_key\":\"$PUBLIC_KEY\",\"valid_principals\":\"$SSH_USERNAME\"}" \
        "$VAULT_PROXY_ADDR/v1/$SSH_CA_PATH")
fi

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ SSH Signed Certificate generation successful"
    echo ""
    
    # Extract and save certificate
    SIGNED_KEY=$(echo "$RESPONSE_BODY" | jq -r '.data.signed_key')
    SERIAL_NUMBER=$(echo "$RESPONSE_BODY" | jq -r '.data.serial_number')
    
    CERT_PATH="$HOME/.ssh/vault_rsa-cert.pub"
    echo "$SIGNED_KEY" > "$CERT_PATH"
    
    # Verify certificate validity
    if ssh-keygen -L -f "$CERT_PATH" >/dev/null 2>&1; then
        echo "✅ Certificate validity verified"
    else
        echo "❌ Certificate validity verification failed"
        echo "Certificate content check:"
        cat "$CERT_PATH"
    fi
    
    echo "📋 SSH Certificate Information:"
    echo "  - Serial Number: $SERIAL_NUMBER"
    echo "  - Certificate Path: $CERT_PATH"
    echo ""
    echo "🔐 SSH Connection Method:"
    echo "  1. SSH Server Configuration (one-time setup):"
    echo "     # Register CA Public Key on SSH server"
    echo "     vault read -field=public_key my-vault-app-ssh-ca/config/ca | sudo tee /etc/ssh/trusted-user-ca-keys.pem"
    echo "     echo 'TrustedUserCAKeys /etc/ssh/trusted-user-ca-keys.pem' | sudo tee -a /etc/ssh/sshd_config"
    echo "     sudo systemctl restart sshd"
    echo ""
    echo "  2. SSH Connection:"
    echo "     ssh -i ~/.ssh/vault_rsa -o CertificateFile=~/.ssh/vault_rsa-cert.pub -o IdentitiesOnly=yes test2@<host-ip>"
    echo ""
    echo "  3. Certificate Verification:"
    echo "     ssh-keygen -L -f $CERT_PATH"
    echo ""
    echo "⚠️  Warning: Certificate expires after 20 seconds."
else
    echo "❌ SSH Signed Certificate generation failed (HTTP $HTTP_CODE)"
    echo "$RESPONSE_BODY" | jq -r '.errors[]' 2>/dev/null || echo "$RESPONSE_BODY"
    exit 1
fi

# Operation test
# ssh -i ~/.ssh/vault_rsa -i ~/.ssh/vault_rsa-cert.pub test2@146.56.162.165
