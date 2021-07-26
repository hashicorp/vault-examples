package main

import (
	"fmt"
	"os"

	vault "github.com/hashicorp/vault/api"
)

// Fetches a key-value secret (kv-v2) after authenticating to Vault via AWS IAM,
// one of two auth methods used to authenticate with AWS (the other is EC2 auth).
// A role must first be created in Vault bound to the IAM ARN you wish to authenticate with, like so:
// vault write auth/aws/role/dev-role-iam \
//     auth_type=iam \
//     bound_iam_principal_arn="arn:aws:iam::AWS-ACCOUNT-NUMBER:role/AWS-IAM-ROLE-NAME" \
//     ttl=24h \
//     resolve_aws_unique_ids=false
// Learn more about the available parameters at https://www.vaultproject.io/api/auth/aws#parameters-10
func getSecretWithAWSAuthIAM() (string, error) {
	vaultAddr := os.Getenv("VAULT_ADDR")

	config := &vault.Config{
		Address: vaultAddr,
	}

	client, err := vault.NewClient(config)
	if err != nil {
		return "", fmt.Errorf("unable to initialize Vault client: %w", err)
	}

	// If environment variables are empty, will fall back on other AWS-provided mechanisms to retrieve credentials.
	// creds, err := awsAuth.RetrieveCreds(os.Getenv("AWS_ACCESS_KEY_ID"), os.Getenv("AWS_SECRET_ACCESS_KEY"), os.Getenv("AWS_SESSION_TOKEN"), hclog.Default())
	// if err != nil {
	// 	return "", fmt.Errorf("unable to retrieve creds from STS: %w", err)
	// }

	// the AWS SDKs work like this: if no cred env vars are provided, then the AWS SDK will retrieve temporary credentials from the instance metadata service on that EC2 instance.
	// not sure how it functions with lambda or ECS tasks, but it somehow returns temporary session creds from AWS either way.

	// params, err := awsAuth.GenerateLoginData(creds, "TODO_THINGY", os.Getenv("AWS_DEFAULT_REGION"))
	// if err != nil {
	// 	return "", err
	// }
	if params == nil {
		return "", fmt.Errorf("got nil response from GenerateLoginData")
	}
	params["role"] = "dev-role-iam" // the name of the role in Vault that was created with this IAM principal ARN bound to it

	resp, err := client.Logical().Write("auth/aws/login", params)
	if err != nil {
		return "", fmt.Errorf("unable to log in with AWS IAM auth: %w", err)
	}

	client.SetToken(resp.Auth.ClientToken)

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

// func getSecretWithAWSAuthEC2() (string, error) {
// }

// GenerateLoginData populates the necessary data to send to the Vault server for generating a token
// func GenerateLoginData(creds *credentials.Credentials, headerValue, configuredRegion string) (map[string]interface{}, error) {
// 	loginData := make(map[string]interface{})

// 	// Use the credentials we've found to construct an STS session
// 	region, err := awsutil.GetRegion(configuredRegion)
// 	if err != nil {
// 		hclog.Default().Warn(fmt.Sprintf("defaulting region to %q due to %s", awsutil.DefaultRegion, err.Error()))
// 		region = awsutil.DefaultRegion
// 	}
// 	stsSession, err := session.NewSessionWithOptions(session.Options{
// 		Config: aws.Config{
// 			Credentials:      creds,
// 			Region:           &region,
// 			EndpointResolver: endpoints.ResolverFunc(stsSigningResolver),
// 		},
// 	})
// 	if err != nil {
// 		return nil, err
// 	}

// 	var params *sts.GetCallerIdentityInput
// 	svc := sts.New(stsSession)
// 	stsRequest, _ := svc.GetCallerIdentityRequest(params)

// 	// Inject the required auth header value, if supplied, and then sign the request including that header
// 	if headerValue != "" {
// 		stsRequest.HTTPRequest.Header.Add(iamServerIdHeader, headerValue)
// 	}
// 	stsRequest.Sign()

// 	// Now extract out the relevant parts of the request
// 	headersJson, err := json.Marshal(stsRequest.HTTPRequest.Header)
// 	if err != nil {
// 		return nil, err
// 	}
// 	requestBody, err := ioutil.ReadAll(stsRequest.HTTPRequest.Body)
// 	if err != nil {
// 		return nil, err
// 	}
// 	loginData["iam_http_request_method"] = stsRequest.HTTPRequest.Method
// 	loginData["iam_request_url"] = base64.StdEncoding.EncodeToString([]byte(stsRequest.HTTPRequest.URL.String()))
// 	loginData["iam_request_headers"] = base64.StdEncoding.EncodeToString(headersJson)
// 	loginData["iam_request_body"] = base64.StdEncoding.EncodeToString(requestBody)

// 	return loginData, nil
// }
