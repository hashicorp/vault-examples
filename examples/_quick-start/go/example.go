package main

import (
	"context"
	"fmt"
	"log"

	vault "github.com/hashicorp/vault/api"
)

// This is the accompanying code for the Developer Quick Start.
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
		"password": "Hashi123",
	}

	// Writing a secret
	_, err = client.KVv2("secret").Put(context.TODO(), "my-secret-password", secretData)
	if err != nil {
		log.Fatalf("unable to write secret: %v", err)
	}

	fmt.Println("Secret written successfully.")

	// Reading a secret
	secret, err := client.KVv2("secret").Get(context.TODO(), "my-secret-password")
	if err != nil {
		log.Fatalf("unable to read secret: %v", err)
	}

	value, ok := secret.Data["password"].(string)
	if !ok {
		log.Fatalf("value type assertion failed: %T %#v", secret.Data["password"], secret.Data["password"])
	}

	if value != "Hashi123" {
		log.Fatalf("unexpected password value %q retrieved from vault", value)
	}

	fmt.Println("Access granted!")
}
