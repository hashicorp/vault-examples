#!/bin/bash

# Vault server and authentication path configuration
export VAULT_ADDR="http://127.0.0.1:8200"  # Change to your Vault server address
export VAULT_NAMESPACE="admin"  # Set if needed
export AWS_SECRET_PATH="aws/creds/ec2_admin"  # AWS Secret Path, change according to role

# AWS credentials file location
export AWS_CREDENTIALS_FILE="$HOME/.aws/credentials"
export AWS_PROFILE="default"  # AWS profile to use

# Login to Vault with Userpass
echo "Logging in to Vault with Userpass..."
vault login -method=userpass username=admin

if [ $? -ne 0 ]; then
  echo "Vault login failed"
  exit 1
fi

# Issue AWS Access Key, Secret Key, Session Token
echo "Requesting AWS Secret issuance..."
export AWS_SECRET=$(vault read -format=json $AWS_SECRET_PATH)

if [ $? -ne 0 ]; then
  echo "AWS Secret issuance failed"
  exit 1
fi

# Extract issued Access Key, Secret Key, Session Token
export AWS_ACCESS_KEY=$(echo $AWS_SECRET | jq -r '.data.access_key')
export AWS_SECRET_KEY=$(echo $AWS_SECRET | jq -r '.data.secret_key')
export AWS_SESSION_TOKEN=$(echo $AWS_SECRET | jq -r '.data.security_token')

# Update .aws/credentials file
echo "Updating AWS credentials file..."
mkdir -p "$(dirname "$AWS_CREDENTIALS_FILE")"

cat > "$AWS_CREDENTIALS_FILE" <<EOL
[$AWS_PROFILE]
aws_access_key_id = $AWS_ACCESS_KEY
aws_secret_access_key = $AWS_SECRET_KEY
aws_session_token = $AWS_SESSION_TOKEN
EOL

echo "AWS credentials file update completed!"

# Completion message
echo "Successfully issued AWS Secrets and updated credentials file."
