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

## AWS
echo "Enabling AWS auth"
curl -X POST -H "X-Vault-Token: ${VAULT_DEV_ROOT_TOKEN_ID}" -d '{"type": "aws"}' ${VAULT_ADDR}/v1/sys/auth/aws

echo "Creating role with dev-policy for AWS auth method"
curl -X PUT -H "X-Vault-Token: ${VAULT_DEV_ROOT_TOKEN_ID}" -H "X-Vault-Request: true" -d '{"token_policies":"dev-policy", "auth_type":"iam","bound_iam_principal_arn":"arn:aws:iam::501359222269:role/vaultAwsDevRole","resolve_aws_unique_ids":"false","ttl":"24h"}' ${VAULT_ADDR}/v1/auth/aws/role/dev-role-iam




mkdir -p go/path/to

# vault write auth/aws/role/dev-role-iam \
#     auth_type=iam \
#     bound_iam_principal_arn="arn:aws:iam::501359222269:role/vaultAwsDevRole" \
#     ttl=24h \
#     resolve_aws_unique_ids=false