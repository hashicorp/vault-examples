package main

import (
	"context"
	"fmt"

	vault "github.com/hashicorp/vault/api"
	auth "github.com/hashicorp/vault/api/auth/kubernetes"
)

// Fetches a key-value secret (kv-v2) after authenticating to Vault with a Kubernetes service account.
//
// As the client, all we need to do is pass along the JWT token representing
// our application's Kubernetes Service Account in our login request to Vault.
// This token is automatically mounted to your application's container by
// Kubernetes. Read more at https://www.vaultproject.io/docs/auth/kubernetes
//
// SETUP NOTES: If an operator has not already set up Kubernetes auth in Vault
// for you, then you must also first configure the Vault server with its own
// Service Account token to be able to communicate with the Kubernetes API
// so it can verify that the client's service-account token is valid.
// The service account that will be performing that verification needs
// the ClusterRole system:auth-delegator.
//
//    export TOKEN_REVIEW_JWT=$(kubectl get secret $TOKEN_REVIEWER_SECRET --output='go-template={{ .data.token }}' | base64 --decode)
//    export KUBE_HOST=$(kubectl config view --raw --minify --flatten --output='jsonpath={.clusters[].cluster.server}')
//    kubectl config view --raw --minify --flatten --output='jsonpath={.clusters[].cluster.certificate-authority-data}' | base64 --decode > path/to/kube_ca_cert
//
//    vault write auth/kubernetes/config \
//  	token_reviewer_jwt=${TOKEN_REVIEW_JWT} \
//      kubernetes_host=${KUBE_HOST} \
//      kubernetes_ca_cert=@path/to/kube_ca_cert \
//      issuer="kubernetes/serviceaccount"
//
// The "issuer" field is normally only required when running Kubernetes 1.21
// or above, and may differ from the default value above:
// https://www.vaultproject.io/docs/auth/kubernetes#discovering-the-service-account-issuer.
//
// Finally, make sure to create a role in Vault bound to your pod's service account:
//
// 	vault write auth/kubernetes/role/dev-role-k8s \
//     	policies="dev-policy" \
//     	bound_service_account_names="my-app" \
//		bound_service_account_namespaces="default"
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
		return "", fmt.Errorf("unable to login to Kubernetes auth method: %w", err)
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
