package main

import (
	"context"
	"fmt"

	vault "github.com/hashicorp/vault/api"
	auth "github.com/hashicorp/vault/api/auth/azure"
)

// Fetches a key-value secret (kv-v2) after authenticating to Vault via Azure authentication.
// This example assumes you have a configured Azure AD Application.
// Learn more about Azure authentication prerequisites: https://www.vaultproject.io/docs/auth/azure
//
// A role must first be created in Vault bound to the resource groups and subscription ids:
// 	vault write auth/azure/role/dev-role \
//     policies="dev-policy"
//     bound_subscription_ids=$AZURE_SUBSCRIPTION_ID \
//     bound_resource_groups=test-rg \
//     ttl=24h
func getSecretWithAzureAuth() (string, error) {
	config := vault.DefaultConfig() // modify for more granular configuration

	client, err := vault.NewClient(config)
	if err != nil {
		return "", fmt.Errorf("unable to initialize Vault client: %w", err)
	}

	azureAuth, err := auth.NewAzureAuth(
		"dev-role-azure",
	)
	if err != nil {
		return "", fmt.Errorf("unable to initialize Azure auth method: %w", err)
	}

	authInfo, err := client.Auth().Login(context.TODO(), azureAuth)
	if err != nil {
		return "", fmt.Errorf("unable to login to Azure auth method: %w", err)
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
