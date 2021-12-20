# AppRole Authentication

The code snippets in this directory are examples in various languages of how to authenticate an application to Vault with the [AppRole authentication method](https://www.vaultproject.io/docs/auth/approle) in order to fetch a secret.

The AppRole auth method is a great choice for those who wish to authenticate entirely using mechanisms included with Vault, rather than relying on an auth method which validates external identities from some other source, as with the AWS or Azure auth methods. This may make AppRole a good choice for users running their applications in an on-prem data center. 

With AppRole, all you need to log in to Vault is a [role ID](https://www.vaultproject.io/docs/auth/approle#roleid) and a [secret ID](https://www.vaultproject.io/docs/auth/approle#secretid). The role ID is a unique identifier for an application, and the secret ID is a value that acts as a login credential (and should thus always be protected).

Check out our Hello-Vault sample app ([Go](https://github.com/hashicorp/hello-vault-go), [C#](https://github.com/hashicorp/hello-vault-dotnet)) for a runnable example of how to use AppRole authentication.

## How do I protect the value of the secret ID?

We recommend having a [trusted orchestrator](https://learn.hashicorp.com/tutorials/vault/secure-introduction?in=vault/app-integration#trusted-orchestrator) take care of generating a single-use [response-wrapping token](https://www.vaultproject.io/docs/concepts/response-wrapping) and placing it somewhere your application has access to. The trusted orchestrator could be Kubernetes, Chef, Nomad--basically whatever privileged process is used to launch your application.

Read more about secret ID best practices [here](https://learn.hashicorp.com/tutorials/vault/approle-best-practices?in=vault/auth-methods#secretid-delivery-best-practices).

## What do I do when the token I got back from logging in to Vault expires?

All secrets in Vault have TTLs, including the token returned when you perform a login. Go users can perform periodic token renewals using the Go client's LifetimeWatcher. See the [token-renewal](https://github.com/hashicorp/vault-examples/tree/main/examples/token-renewal) directory of this repo for examples. If a token cannot be renewed (such as when it reaches its [max TTL](https://learn.hashicorp.com/tutorials/vault/tokens#ttl-and-max-ttl)), a full re-login to Vault is required.

Once the secret ID has been used past its [secret_id_num_uses](https://www.vaultproject.io/api/auth/approle#parameters) (which is only 1 if the secret ID is response-wrapped), the trusted orchestrator will need to replace the secret ID so that the application can log in again.