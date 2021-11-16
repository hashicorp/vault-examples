package main

import (
	"context"
	"fmt"
	"os"

	vault "github.com/hashicorp/vault/api"
	auth "github.com/hashicorp/vault/api/auth/approle"
)

// Fetches a key-value secret (kv-v2) after authenticating via AppRole,
// an auth method used by machines that are unable to use platform-based
// authentication mechanisms like AWS Auth, Kubernetes Auth, etc.
func getSecretWithAppRole() (string, error) {
	config := vault.DefaultConfig() // modify for more granular configuration

	client, err := vault.NewClient(config)
	if err != nil {
		return "", fmt.Errorf("unable to initialize Vault client: %w", err)
	}

	// A combination of a Role ID and Secret ID is required to log in to Vault
	// with an AppRole.
	// First, let's get the role ID given to us by our Vault administrator.
	roleID := os.Getenv("APPROLE_ROLE_ID")
	if roleID == "" {
		return "", fmt.Errorf("no role ID was provided in APPROLE_ROLE_ID env var")
	}

	// The Secret ID is a value that needs to be protected, so instead of the
	// app having knowledge of the secret ID directly, we have a trusted orchestrator (https://learn.hashicorp.com/tutorials/vault/secure-introduction?in=vault/app-integration#trusted-orchestrator)
	// give the app access to a short-lived response-wrapping token (https://www.vaultproject.io/docs/concepts/response-wrapping).
	// Read more at: https://learn.hashicorp.com/tutorials/vault/approle-best-practices?in=vault/auth-methods#secretid-delivery-best-practices
	secretID := &auth.SecretID{FromFile: "path/to/wrapping-token"}

	appRoleAuth, err := auth.NewAppRoleAuth(
		roleID,
		secretID,
		auth.WithWrappingToken(),
	)
	if err != nil {
		return "", fmt.Errorf("unable to initialize AppRole auth method: %w", err)
	}

	authInfo, err := client.Auth().Login(context.TODO(), appRoleAuth)
	if err != nil {
		return "", fmt.Errorf("unable to login to AppRole auth method: %w", err)
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
