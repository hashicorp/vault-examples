package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"time"

	credentials "cloud.google.com/go/iam/credentials/apiv1"
	vault "github.com/hashicorp/vault/api"
	credentialspb "google.golang.org/genproto/googleapis/iam/credentials/v1"
)

// Fetches a key-value secret (kv-v2) after authenticating to Vault via GCP IAM,
// one of two auth methods used to authenticate with GCP (the other is GCE auth).
//
// A role must first be created in Vault bound to the IAM user's service account you wish to authenticate with, like so:
// 	vault write auth/gcp/role/dev-role-iam \
//     	type="iam" \
//     	policies="dev-policy" \
//     	bound_service_accounts="my-service@my-project.iam.gserviceaccount.com"
// Your Vault instance must also be configured with GCP credentials to perform API calls to IAM, like so:
// 	vault write auth/gcp/config credentials=@path/to/server/creds.json
// Learn more at https://www.vaultproject.io/docs/auth/gcp
func getSecretWithGCPAuthIAM() (string, error) {
	config := vault.DefaultConfig() // modify for more granular configuration

	client, err := vault.NewClient(config)
	if err != nil {
		return "", fmt.Errorf("unable to initialize Vault client: %w", err)
	}

	// Learn about authenticating to GCS with service account credentials at https://cloud.google.com/docs/authentication/production
	if pathToCreds := os.Getenv("GOOGLE_APPLICATION_CREDENTIALS"); pathToCreds == "" {
		fmt.Printf("WARNING: Environment variable GOOGLE_APPLICATION_CREDENTIALS was not set. IAM client for JWT signing and Vault server IAM client will both fall back to default instance credentials.\n")
	}

	jwtResp, err := signJWT()
	if err != nil {
		return "", fmt.Errorf("unable to sign JWT for authenticating to GCP: %w", err)
	}

	// log in to Vault's GCP auth method with signed JWT token
	params := map[string]interface{}{
		"role": "dev-role-iam", // the name of the role in Vault that was created with this IAM bound to it
		"jwt":  jwtResp.SignedJwt,
	}

	// Environment variable GOOGLE_APPLICATION_CREDENTIALS pointing to the path to a valid credentials JSON must be set,
	// or Vault will fall back to Google's default instance credentials
	resp, err := client.Logical().Write("auth/gcp/login", params)
	if err != nil {
		return "", fmt.Errorf("unable to log in with GCP IAM auth: %w", err)
	}
	if resp == nil || resp.Auth == nil || resp.Auth.ClientToken == "" {
		return "", fmt.Errorf("login response did not return client token")
	}

	client.SetToken(resp.Auth.ClientToken)

	// get secret
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

// generate signed JWT token from GCP IAM
func signJWT() (*credentialspb.SignJwtResponse, error) {
	svcAccountEmail := fmt.Sprintf("%s@%s.iam.gserviceaccount.com", os.Getenv("GCP_SERVICE_ACCOUNT_NAME"), os.Getenv("GOOGLE_CLOUD_PROJECT"))

	ctx := context.Background()
	iamClient, err := credentials.NewIamCredentialsClient(ctx) // can pass option.WithCredentialsFile("path/to/creds.json") as second param if GOOGLE_APPLICATION_CREDENTIALS env var not set
	if err != nil {
		return nil, fmt.Errorf("unable to initialize IAM credentials client: %w", err)
	}
	defer iamClient.Close()

	resourceName := fmt.Sprintf("projects/-/serviceAccounts/%s", svcAccountEmail)
	jwtPayload := map[string]interface{}{
		"aud": "vault/dev-role-iam", // the name of the role in Vault that was created with this IAM service account bound to it
		"sub": svcAccountEmail,
		"exp": time.Now().Add(time.Minute * 10).Unix(),
	}

	payloadBytes, err := json.Marshal(jwtPayload)
	if err != nil {
		return nil, fmt.Errorf("unable to marshal jwt payload to json: %w", err)
	}

	signJWTReq := &credentialspb.SignJwtRequest{
		Name:    resourceName,
		Payload: string(payloadBytes),
	}

	jwtResp, err := iamClient.SignJwt(ctx, signJWTReq)
	if err != nil {
		return nil, fmt.Errorf("unable to sign JWT: %w", err)
	}

	return jwtResp, nil
}
