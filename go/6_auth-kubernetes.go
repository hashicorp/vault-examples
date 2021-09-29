package main

import (
	"fmt"
	"os"

	vault "github.com/hashicorp/vault/api"
)

// Fetches a key-value secret (kv-v2) after authenticating to Vault with a Kubernetes service account.
//
// As the client, all we need to do is pass along the JWT token representing our application's Kubernetes Service Account in our login request to Vault.
// This token is automatically mounted to your application's container by Kubernetes.
//
// SETUP NOTES: The Vault server must first also be configured to be able to communicate with the Kubernetes API, to
// verify that the client's token is from the service-account it says it is. If an operator hasn't already done this for you, you will do so like this:
//    // TOKEN_REVIEWER_SECRET is the name of the Kubernetes Secret representing the token for whichever service account will be used to communicate with Kubernetes' TokenReview API to approve tokens. That serviceaccount needs the ClusterRole system:auth-delegator.
//    export TOKEN_REVIEW_JWT=$(kubectl get secret $TOKEN_REVIEWER_SECRET --output='go-template={{ .data.token }}' | base64 --decode)
//    export KUBE_HOST=$(kubectl config view --raw --minify --flatten --output='jsonpath={.clusters[].cluster.server}')
//
//    vault write auth/kubernetes/config \
//  	token_reviewer_jwt=${TOKEN_REVIEW_JWT} \
//      kubernetes_host=${KUBE_HOST} \
//      kubernetes_ca_cert=@path/to/kube_ca_cert \
//      issuer="kubernetes/serviceaccount"
//
// The "issuer" field only needs to be set when running Kubernetes version 1.21 or above:
// https://www.vaultproject.io/docs/platform/k8s/csi#setting-issuer-for-kubernetes-authentication.
// Issuer validation can also be disabled with the flag disable_iss_validation=true
//
// Finally, make sure to create a role in Vault bound to your pod's service account:
//
// 	vault write auth/kubernetes/role/dev-role-k8s \
//     	policies="dev-policy" \
//     	bound_service_account_names="my-app" \
//		bound_service_account_namespaces="default"
func getSecretWithKubernetesAuth() (string, error) {
	// If not specified, the VAULT_ADDR environment variable (if set) will be the address that your pod uses to communicate with Vault.
	// For an application running in Kubernetes accessing a Vault server outside of Kubernetes, you will need to set VAULT_ADDR in your pod spec to
	// point at your Kubernetes cluster's gateway address. See this tutorial for more information: https://learn.hashicorp.com/tutorials/vault/kubernetes-external-vault
	config := vault.DefaultConfig() // modify for more granular configuration

	client, err := vault.NewClient(config)
	if err != nil {
		return "", fmt.Errorf("unable to initialize Vault client: %w", err)
	}

	// Read the service-account token from the path where the token's Kubernetes Secret is mounted.
	// By default, Kubernetes will mount this to /var/run/secrets/kubernetes.io/serviceaccount/token
	// but an administrator may have configured it to be mounted elsewhere.
	jwt, err := os.ReadFile("path/to/service-account-token")
	if err != nil {
		return "", fmt.Errorf("unable to read file containing service account token: %w", err)
	}

	params := map[string]interface{}{
		"jwt":  string(jwt),
		"role": "dev-role-k8s", // the name of the role in Vault that was created with this app's Kubernetes service account bound to it
	}

	// log in to Vault's Kubernetes auth method
	resp, err := client.Logical().Write("auth/kubernetes/login", params)
	if err != nil {
		return "", fmt.Errorf("unable to log in with Kubernetes auth: %w", err)
	}
	if resp == nil || resp.Auth == nil || resp.Auth.ClientToken == "" {
		return "", fmt.Errorf("login response did not return client token")
	}

	// now you will use the resulting Vault token for making all future calls to Vault
	client.SetToken(resp.Auth.ClientToken)

	// get secret from Vault
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
