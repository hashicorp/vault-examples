# GCP Authentication

The code snippets in this directory are examples in various languages of how to authenticate an application to Vault with the [Google Cloud Platform authentication method](https://www.vaultproject.io/docs/auth/gcp) in order to fetch a secret.

There are two options for authenticating using GCP: [IAM auth](https://www.vaultproject.io/docs/auth/gcp#iam-login) and [GCE auth](https://www.vaultproject.io/docs/auth/gcp#gce-login).

## Configuring the Vault server

Your Vault instance must be configured with GCP credentials to
perform API calls to IAM. For example:

```
vault write auth/gcp/config credentials=@path/to/vault/server/creds.json
```

For IAM auth, a role must first be created in Vault bound to the IAM user's service
account you wish to authenticate with. For example:

```
vault write auth/gcp/role/dev-role-iam \
    type="iam" \
    policies="dev-policy" \
    bound_service_accounts="my-service@my-project.iam.gserviceaccount.com"
```

With GCE auth, you will use `type="gce"`, and can add [additional parameters](https://www.vaultproject.io/api/auth/gcp#gce-only-parameters) specific to the GCE auth type.

Other constraint options for both auth types can be found [here](https://www.vaultproject.io/api/auth/gcp#create-role).