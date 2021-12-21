package main

import (
	"context"
	"fmt"

	vault "github.com/hashicorp/vault/api"
	auth "github.com/hashicorp/vault/api/auth/kubernetes"
)

// Fetches a key-value secret (kv-v2) after authenticating to Vault with a Kubernetes service account.
func getSecretWithKubernetesAuth() (string, error) {
	// If set, the VAULT_ADDR environment variable will be the address that
	// your pod uses to communicate with Vault.
	config := vault.DefaultConfig() // modify for more granular configuration

	client, err := vault.NewClient(config)
	if err != nil {
		return "", fmt.Errorf("unable to initialize Vault client: %w", err)
	}

	// The service-account token will be read from the path where the token's
	// Kubernetes Secret is mounted. By default, Kubernetes will mount it to
	// /var/run/secrets/kubernetes.io/serviceaccount/token, but an administrator
	// may have configured it to be mounted elsewhere.
	// In that case, we'll use the option WithServiceAccountTokenPath to look
	// for the token there.
	k8sAuth, err := auth.NewKubernetesAuth(
		"dev-role-k8s",
		auth.WithServiceAccountTokenPath("path/to/service-account-token"),
	)
	if err != nil {
		return "", fmt.Errorf("unable to initialize Kubernetes auth method: %w", err)
	}

	authInfo, err := client.Auth().Login(context.TODO(), k8sAuth)
	if err != nil {
		return "", fmt.Errorf("unable to log in with Kubernetes auth: %w", err)
	}
	if authInfo == nil {
		return "", fmt.Errorf("no auth info was returned after login")
	}

	// get secret from Vault
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
