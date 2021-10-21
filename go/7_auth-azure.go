package main

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"net/url"

	vault "github.com/hashicorp/vault/api"
)

type responseJson struct {
	AccessToken  string `json:"access_token"`
	RefreshToken string `json:"refresh_token"`
	ExpiresIn    string `json:"expires_in"`
	ExpiresOn    string `json:"expires_on"`
	NotBefore    string `json:"not_before"`
	Resource     string `json:"resource"`
	TokenType    string `json:"token_type"`
}

type metadataJson struct {
	Compute computeJson `json:"compute"`
}

type computeJson struct {
	VirtualMachineName string `json:"name"`
	SubscriptionId     string `json:"subscriptionId"`
	ResourceGroupName  string `json:"resourceGroupName"`
}

// Fetches a key-value secret (kv-v2) after authenticating to Vault via Azure authentication.
// This example assumes you have a configured Azure AD Application.
// Learn more about Azure authentication prerequisites: https://www.vaultproject.io/docs/auth/azure
//
// A role must first be created in Vault bound to the resource groups and subscription ids:
// 	vault write auth/azure/role/dev-role \
//     policies="dev-policy"
//     bound_subscription_ids=$AZURE_SUBSCRIPTION_ID \
//     bound_resource_groups=test-rg \
//     ttl=24h
func getSecretWithAzureAuth() (string, error) {
	config := vault.DefaultConfig() // modify for more granular configuration

	client, err := vault.NewClient(config)
	if err != nil {
		return "", fmt.Errorf("unable to initialize Vault client: %w", err)
	}

	// Get AccessToken
	jwtResp, err := getJWT()
	if err != nil {
		return "", fmt.Errorf("unable to get access token: %w", err)
	}

	// Get metadata for Azure instance
	metadataRespJson, err := getMetadata()
	if err != nil {
		return "", fmt.Errorf("unable to get instance metadata: %w", err)
	}

	// log in to Vault's  auth method with signed JWT token
	params := map[string]interface{}{
		"role":                "dev-role-azure", // the name of the role in Vault w/ bound subscription id and resource group
		"jwt":                 jwtResp,
		"vm_name":             metadataRespJson.Compute.VirtualMachineName,
		"subscription_id":     metadataRespJson.Compute.SubscriptionId,
		"resource_group_name": metadataRespJson.Compute.ResourceGroupName,
	}

	// log in to Vault's Azure auth method
	resp, err := client.Logical().Write("auth/azure/login", params) // confirm with your Vault administrator that "azure" is the correct mount name
	if err != nil {
		return "", fmt.Errorf("unable to log in with Azure auth: %w", err)
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

// Retrieve instance metadata from Azure
func getMetadata() (metadataJson, error) {
	var metadataEndpoint *url.URL
	metadataEndpoint, err := url.Parse("http://169.254.169.254/metadata/instance")
	if err != nil {
		fmt.Println("Error creating URL: ", err)
		return metadataJson{}, err
	}

	metadataParameters := metadataEndpoint.Query()
	metadataParameters.Add("api-version", "2018-02-01")
	metadataEndpoint.RawQuery = metadataParameters.Encode()
	req, err := http.NewRequest("GET", metadataEndpoint.String(), nil)
	if err != nil {
		return metadataJson{}, fmt.Errorf("Error creating HTTP Request: %w", err)
	}
	req.Header.Add("Metadata", "true")

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		fmt.Println("Error calling token endpoint: ", err)
		return metadataJson{}, fmt.Errorf("Error calling token endpoint: %w", err)
	}

	responseBytes, err := ioutil.ReadAll(resp.Body)
	defer resp.Body.Close()
	if err != nil {
		return metadataJson{}, fmt.Errorf("Error reading response body: %w", err)
	}

	// Unmarshal response body into metadata struct
	var r metadataJson
	err = json.Unmarshal(responseBytes, &r)
	if err != nil {
		return metadataJson{}, fmt.Errorf("Error unmarshalling the response: %w", err)
	}

	return r, nil
}

// Retrieves an access token from Azure MSI
// Learn more here: https://docs.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/how-to-use-vm-token
func getJWT() (string, error) {
	// Create HTTP request for a managed services for Azure resources token to access Azure Resource Manager
	var msiEndpoint *url.URL
	msiEndpoint, err := url.Parse("http://169.254.169.254/metadata/identity/oauth2/token")
	if err != nil {
		return "", fmt.Errorf("Error creating URL: %w", err)
	}

	msiParameters := msiEndpoint.Query()
	msiParameters.Add("api-version", "2018-02-01")
	msiParameters.Add("resource", "https://management.azure.com/")
	msiEndpoint.RawQuery = msiParameters.Encode()

	req, err := http.NewRequest("GET", msiEndpoint.String(), nil)
	if err != nil {
		return "", fmt.Errorf("Error creating HTTP request: %w", err)
	}
	req.Header.Add("Metadata", "true")

	// Call managed services for Azure resources token endpoint
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return "", fmt.Errorf("Error calling token endpoint: %w", err)
	}

	responseBytes, err := ioutil.ReadAll(resp.Body)
	defer resp.Body.Close()
	if err != nil {
		return "", fmt.Errorf("Error reading response body: %w", err)
	}

	// Unmarshal response body into struct
	var r responseJson
	err = json.Unmarshal(responseBytes, &r)
	if err != nil {
		return "", fmt.Errorf("Error unmarshalling the response: %w", err)
	}

	return r.AccessToken, nil
}
