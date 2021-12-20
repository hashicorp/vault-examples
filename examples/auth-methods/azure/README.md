# Azure Authentication

The code snippets in this directory are examples in various languages of how to authenticate an application to Vault with the [Azure authentication method](https://www.vaultproject.io/docs/auth/azure) in order to fetch a secret.

The Azure auth method expects all login requests to contain a JWT signed by Azure Active Directory for the

## Configuring the Vault server

After you've enabled the Azure auth method on your Vault instance, you will need to configure it to check against your application's App Registration in Azure.

```
vault write auth/azure/config \
    tenant_id=MY-TENANT-ID \
    resource=https://management.azure.com/ \
    client_id=MY-CLIENT-ID \
    client_secret=MY-CLIENT-SECRET
``` 

The tenant ID, client ID, and client secret for your application are all values you can retrieve from the App Registrations page in Azure.

`resource` will be the URI that Vault should expect to be passed in as the `aud` value of the JWT token in any valid login request.

A role must then be created in Vault bound to the specific Azure resources that you wish to allow logins from.
For example:

```
vault write auth/azure/role/dev-role \
    policies="dev-policy"
    bound_subscription_ids=$AZURE_SUBSCRIPTION_ID \
    bound_resource_groups=test-rg \
    ttl=24h
```

See other constraint options [here](https://www.vaultproject.io/api/auth/azure#create-role).