# AWS Authentication

The code snippets in this directory are examples in various languages of how to
authenticate an application to Vault with the
[AWS authentication method](https://www.vaultproject.io/docs/auth/aws) in order
to fetch a secret.

There are two options for authenticating using AWS:
[IAM auth](https://www.vaultproject.io/docs/auth/aws#iam-auth-method) and
[EC2 auth](https://www.vaultproject.io/docs/auth/aws#ec2-auth-method). IAM is
the generally recommended option, but there may be certain
[use cases](https://www.vaultproject.io/docs/auth/aws#comparison-of-the-iam-and-ec2-methods)
where EC2 auth fits better.

## Configuring the Vault server

A role must first be created in Vault, bound to certain constraints depending on
whether you're using IAM auth or EC2 auth. For example, with IAM auth you can
bind the role to a certain IAM principal ARN like so:

```sh
vault write auth/aws/role/dev-role-iam \
    auth_type=iam \
    bound_iam_principal_arn="arn:aws:iam::AWS-ACCOUNT-NUMBER:role/AWS-IAM-ROLE-NAME" \
    ttl=24h
```

Learn more about the available constraints for both auth types
[here](https://www.vaultproject.io/api/auth/aws#parameters-10).

For EC2 auth, your Vault server will need to have a
[certificate](https://www.vaultproject.io/api/auth/aws#create-certificate-configuration)
registered with it that will be used to verify instance identity documents.
