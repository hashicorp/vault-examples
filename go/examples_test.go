package main

import (
	"log"
	"os"
	"testing"

	vault "github.com/hashicorp/vault/api"
)

var expected = os.Getenv("EXPECTED_SECRET_VALUE")

func TestGetSecret(t *testing.T) {
	value, err := getSecret()
	if err != nil {
		t.Fatalf("Failed to get secret with token: %v", err)
	}
	if value != expected {
		t.Fatalf("Expected %s, but got %s", expected, value)
	}
}

func TestRenewToken(t *testing.T) {
	config := vault.DefaultConfig()

	client, err := vault.NewClient(config)
	if err != nil {
		t.Fatalf("Failed to initialize Vault client: %v", err)
	}

	vaultLoginResp, err := login(client)
	if err != nil {
		log.Fatalf("unable to authenticate to Vault: %v", err)
	}

	token, err := client.Auth().Token().LookupSelf()
	if err != nil {
		t.Fatalf("Failed to lookup token on client: %v", err)
	}

	originalTokenExpiration, exists := token.Data["expire_time"]
	if !exists {
		t.Fatalf("Token secret does not have expire_time.")
	}

	renewErr := manageTokenLifecycle(client, vaultLoginResp) // can't just pass our var called "token" because the api.Secret returned by LookupSelf() does not contain an Auth object
	if renewErr != nil {
		log.Fatalf("unable to start managing token lifecycle: %v", renewErr)
	}

	// we should have renewed at least one time
	renewedToken, err := client.Auth().Token().LookupSelf()
	if err != nil {
		t.Fatalf("Failed to lookup renewed token on client: %v", err)
	}

	newTokenExpiration, exists := renewedToken.Data["expire_time"]
	if !exists {
		t.Fatalf("Renewed token secret does not have expire_time.")
	}

	if originalTokenExpiration == newTokenExpiration {
		t.Fatalf("Token had same expiration time before and after calling for renewal. Renewal did not occur.")
	}
}

func TestGetSecretWithAppRole(t *testing.T) {
	value, err := getSecretWithAppRole()
	if err != nil {
		t.Fatalf("Failed to get secret with app role: %v", err)
	}
	if value != expected {
		t.Fatalf("Expected %s, but got %s", expected, value)
	}
}

func TestGetSecretWithAWSAuthIAM(t *testing.T) {
	if os.Getenv("LOCAL_TESTING") == "" {
		t.Skip("skipping test in CI for now")
	}
	value, err := getSecretWithAWSAuthIAM()
	if err != nil {
		t.Fatalf("Failed to get secret with AWS IAM: %v", err)
	}
	if value != expected {
		t.Fatalf("Expected %s, but got %s", expected, value)
	}
}

func TestGetSecretWithGCPAuthIAM(t *testing.T) {
	if os.Getenv("LOCAL_TESTING") == "" {
		t.Skip("skipping test in CI for now")
	}
	value, err := getSecretWithGCPAuthIAM()
	if err != nil {
		t.Fatalf("Failed to get secret with GCP IAM: %v", err)
	}
	if value != expected {
		t.Fatalf("Expected %s, but got %s", expected, value)
	}
}

func TestGetSecretWithKubernetesAuth(t *testing.T) {
	if os.Getenv("LOCAL_TESTING") == "" {
		t.Skip("skipping test in CI for now")
	}
	value, err := getSecretWithKubernetesAuth()
	if err != nil {
		t.Fatalf("Failed to get secret using Kubernetes service account: %v", err)
	}
	if value != expected {
		t.Fatalf("Expected %s, but got %s", expected, value)
	}
}
