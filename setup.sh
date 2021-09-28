#!/bin/bash

set -euo pipefail

## general setup
echo "Enabling kv-v2 secrets engine at /kv-v2"
curl -X POST -H "X-Vault-Token: ${VAULT_DEV_ROOT_TOKEN_ID}" -d '{"type": "kv-v2"}' ${VAULT_ADDR}/v1/sys/mounts/kv-v2

echo "Creating an access policy for application developers"
curl -X PUT -H "X-Vault-Token: ${VAULT_DEV_ROOT_TOKEN_ID}" -d '{"policy":"path \"kv-v2/data/*\" {\n  capabilities = [\"create\", \"update\", \"read\"]\n}\n\npath \"kv-v2/data/foo\" {\n  capabilities = [\"read\"]\n}"}' ${VAULT_ADDR}/v1/sys/policies/acl/dev-policy

echo "Creating secret"
curl -X PUT -H "X-Vault-Token: ${VAULT_DEV_ROOT_TOKEN_ID}" -d '{"data": {"password": "Hashi123"}}' ${VAULT_ADDR}/v1/kv-v2/data/creds

## APPROLE
echo "Enabling approle auth"
curl -X POST -H "X-Vault-Token: ${VAULT_DEV_ROOT_TOKEN_ID}" -d '{"type": "approle"}' ${VAULT_ADDR}/v1/sys/auth/approle

echo "Creating role with dev-policy for approle auth method"
curl -X POST -H "X-Vault-Token: ${VAULT_DEV_ROOT_TOKEN_ID}" -d '{"token_policies":"dev-policy"}' ${VAULT_ADDR}/v1/auth/approle/role/my-role

echo "Creating path for wrapping token"
mkdir -p go/path/to

echo "Generating wrapping token"
curl -X PUT -H "X-Vault-Token: ${VAULT_DEV_ROOT_TOKEN_ID}" -H "X-Vault-Wrap-Ttl: 5m0s" -d "null" ${VAULT_ADDR}/v1/auth/approle/role/my-role/secret-id | jq -r .wrap_info.token > go/path/to/wrapping-token

echo "Creating path for dotnet wrapping token"
mkdir -p dotnet/ExampleTests/path/to

echo "Generating wrapping token for dotnet tests"
curl -X PUT -H "X-Vault-Token: ${VAULT_DEV_ROOT_TOKEN_ID}" -H "X-Vault-Wrap-Ttl: 5m0s" -d "null" ${VAULT_ADDR}/v1/auth/approle/role/my-role/secret-id | jq -r .wrap_info.token > dotnet/ExampleTests/path/to/wrapping-token