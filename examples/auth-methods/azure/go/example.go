package main

import (
	"context"
	"fmt"

	vault "github.com/hashicorp/vault/api"
	auth "github.com/hashicorp/vault/api/auth/azure"
)

// Fetches a key-value secret (kv-v2) after authenticating to Vault via Azure authentication.
// This example assumes you have a configured Azure AD Application.
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

	authInfo, err := client.Auth().Login(context.Background(), azureAuth)
	if err != nil {
		return "", fmt.Errorf("unable to login to Azure auth method: %w", err)
	}
	if authInfo == nil {
		return "", fmt.Errorf("no auth info was returned after login")
	}

	// get secret from the default mount path for KV v2 in dev mode, "secret"
	secret, err := client.KVv2("secret").Get(context.Background(), "creds")
	if err != nil {
		return "", fmt.Errorf("unable to read secret: %w", err)
	}

	// data map can contain more than one key-value pair,
	// in this case we're just grabbing one of them
	value, ok := secret.Data["password"].(string)
	if !ok {
		return "", fmt.Errorf("value type assertion failed: %T %#v", secret.Data["password"], secret.Data["password"])
	}

	return value, nil
}
