package main

import (
	"fmt"
	"log"

	vault "github.com/hashicorp/vault/api"
)

// This is the full version of the code accompanying the Developer Quick Start.
// WARNING: Using root tokens is insecure and should never be done in production!
func main() {
	config := vault.DefaultConfig()

	config.Address = "http://127.0.0.1:8200"

	client, err := vault.NewClient(config)
	if err != nil {
		log.Fatalf("unable to initialize Vault client: %v", err)
	}

	// Authentication
	client.SetToken("dev-only-token")

	secretData := map[string]interface{}{
		"data": map[string]interface{}{
			"password": "Hashi123",
		},
	}

	// Writing a secret
	_, err = client.Logical().Write("secret/data/my-secret-password", secretData)
	if err != nil {
		log.Fatalf("unable to write secret: %v", err)
	}

	fmt.Println("Secret written successfully.")

	// Reading a secret
	secret, err := client.Logical().Read("secret/data/my-secret-password")
	if err != nil {
		log.Fatalf("unable to read secret: %v", err)
	}

	data, ok := secret.Data["data"].(map[string]interface{})
	if !ok {
		log.Fatalf("data type assertion failed: %T %#v", secret.Data["data"], secret.Data["data"])
	}

	key := "password"
	value, ok := data[key].(string)
	if !ok {
		log.Fatalf("value type assertion failed: %T %#v", data[key], data[key])
	}

	if value != "Hashi123" {
		log.Fatalf("unexpected password value %q retrieved from vault", value)
	}

	fmt.Println("Access granted!")
}
