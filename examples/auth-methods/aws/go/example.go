package main

import (
	"context"
	"fmt"

	vault "github.com/hashicorp/vault/api"
	auth "github.com/hashicorp/vault/api/auth/aws"
)

// Fetches a key-value secret (kv-v2) after authenticating to Vault via AWS IAM,
// one of two auth methods used to authenticate with AWS (the other is EC2 auth).
func getSecretWithAWSAuthIAM() (string, error) {
	config := vault.DefaultConfig() // modify for more granular configuration

	client, err := vault.NewClient(config)
	if err != nil {
		return "", fmt.Errorf("unable to initialize Vault client: %w", err)
	}

	awsAuth, err := auth.NewAWSAuth(
		auth.WithRole("dev-role-iam"), // if not provided, Vault will fall back on looking for a role with the IAM role name if you're using the iam auth type, or the EC2 instance's AMI id if using the ec2 auth type
	)
	if err != nil {
		return "", fmt.Errorf("unable to initialize AWS auth method: %w", err)
	}

	authInfo, err := client.Auth().Login(context.TODO(), awsAuth)
	if err != nil {
		return "", fmt.Errorf("unable to login to AWS auth method: %w", err)
	}
	if authInfo == nil {
		return "", fmt.Errorf("no auth info was returned after login")
	}

	// get secret
	secret, err := client.Logical().Read("kv-v2/data/creds")
	if err != nil {
		return "", fmt.Errorf("unable to read secret: %w", err)
	}

	data, ok := secret.Data["data"].(map[string]interface{})
	if !ok {
		return "", fmt.Errorf("data type assertion failed: %T %#v", secret.Data["data"], secret.Data["data"])
	}

	// data map can contain more than one key-value pair,
	// in this case we're just grabbing one of them
	key := "password"
	value, ok := data[key].(string)
	if !ok {
		return "", fmt.Errorf("value type assertion failed: %T %#v", data[key], data[key])
	}

	return value, nil
}
