// WARNING: The code in this hello-world file is potentially insecure.
// It is not safe for use in production.
// This is just a quickstart for trying out the Vault client library
// for the first time.

package main

import (
	"context"
	"fmt"

	vault "github.com/hashicorp/vault/api"
	auth "github.com/hashicorp/vault/api/auth/userpass"
)

// Fetches a key-value secret (kv-v2 secrets engine) after authenticating with
// the userpass auth method
func getSecret() (string, error) {
	config := vault.DefaultConfig() // modify for more granular configuration

	client, err := vault.NewClient(config)
	if err != nil {
		return "", fmt.Errorf("unable to initialize Vault client: %w", err)
	}

	// WARNING: Storing any long-lived token with secret access in an
	// environment variable poses a security risk. Additionally, root tokens
	// should never be used in production or against Vault installations
	// containing real secrets.
	//
	// See the files starting in auth-* for examples of how to securely log in to Vault using various auth methods.

	// "auth" will be the package corresponding to the specific auth backend
	// module chosen by the user, like vault/auth/aws or vault/auth/kubernetes.
	// If the desired auth provider does not yet have a corresponding auth
	// package, you will need to write to that auth method's /login endpoint
	// directly with client.Logical().Write.
	userpassAuth, err := auth.NewUserpassAuth("my-user", &auth.Password{FromEnv: "SOME_ENV_VAR"})
	if err != nil {
		return "", fmt.Errorf("unable to initialize userpass auth method: %w", err)
	}

	authInfo, err := client.Auth().Login(context.TODO(), userpassAuth)
	if err != nil {
		return "", fmt.Errorf("unable to login to userpass auth method: %w", err)
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

	// data map can contain more than one key-value pair,
	// in this case we're just grabbing one of them
	key := "password"
	value, ok := data[key].(string)
	if !ok {
		return "", fmt.Errorf("value type assertion failed: %T %#v", data[key], data[key])
	}

	return value, nil
}
