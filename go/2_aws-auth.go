package main

import (
	"fmt"

	vault "github.com/hashicorp/vault/api"
	auth "github.com/hashicorp/vault/auth/aws"
)

// Fetches a key-value secret (kv-v2) after authenticating to Vault via AWS IAM,
// one of two auth methods used to authenticate with AWS (the other is EC2 auth).
// A role must first be created in Vault bound to the IAM ARN you wish to authenticate with, like so:
// vault write auth/aws/role/dev-role-iam \
//     auth_type=iam \
//     bound_iam_principal_arn="arn:aws:iam::AWS-ACCOUNT-NUMBER:role/AWS-IAM-ROLE-NAME" \
//     ttl=24h
// Learn more about the available parameters at https://www.vaultproject.io/api/auth/aws#parameters-10
func getSecretWithAWSAuthIAM() (string, error) {
	config := vault.DefaultConfig() // modify for more granular configuration

	client, err := vault.NewClient(config)
	if err != nil {
		return "", fmt.Errorf("unable to initialize Vault client: %w", err)
	}

	// "auth" will be the specific auth package chosen by the user, like vault/auth/aws or vault/auth/gcp (a new set of modules)
	// if their desired auth provider does not have a corresponding auth package, they will need to write to that auth method's /login endpoint directly
	awsAuth, err := auth.NewAWSAuth(
		auth.WithCredentialsFile("path/to/creds/file"), // if you don't pass any LoginOptions here, it will default to looking for creds in env vars
	)
	if err != nil {
		return "", fmt.Errorf("unable to initialize AWS auth method: %w", err)
	}

	authInfo, err := client.Auth().Login(awsAuth)
	if err != nil {
		return "", fmt.Errorf("unable to login to AWS auth method: %w", err)
	}
	if authInfo == nil {
		return "", fmt.Errorf("no auth info was returned after login")
	}

	secret, err := client.Logical().Read("kv-v2/data/creds")
	if err != nil {
		return "", fmt.Errorf("unable to read secret: %w", err)
	}

	data, ok := secret.Data["data"].(map[string]interface{})
	if !ok {
		return "", fmt.Errorf("data type assertion failed: %T %#v", secret.Data["data"], secret.Data["data"])
	}

	// data map can contain more than one key-value pair, in this case we're just grabbing one of them
	key := "password"
	value, ok := data[key].(string)
	if !ok {
		return "", fmt.Errorf("value type assertion failed: %T %#v", data[key], data[key])
	}

	return value, nil
}
