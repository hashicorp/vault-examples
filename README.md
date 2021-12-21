# Vault Examples

A collection of copy-pastable code example snippets demonstrating the various ways to use the Vault client libraries for various languages to authenticate and retrieve secrets.

## Currently Supported Languages

- Go
  - Uses official library [HashiCorp Vault](https://pkg.go.dev/github.com/hashicorp/vault/api)
  - Provided examples:
    - Auth Methods ([AppRole](https://github.com/hashicorp/vault-examples/tree/main/examples/auth-methods/approle/example.go), [AWS](https://github.com/hashicorp/vault-examples/tree/main/examples/auth-methods/aws/example.go), [Azure](https://github.com/hashicorp/vault-examples/tree/main/examples/auth-methods/azure/example.go), [GCP](https://github.com/hashicorp/vault-examples/tree/main/examples/auth-methods/gcp/example.go), [Kubernetes](https://github.com/hashicorp/vault-examples/tree/main/examples/auth-methods/kubernetes/example.go))
    - [Token Renewal](https://github.com/hashicorp/vault-examples/tree/main/examples/token-renewal/example.go)
- C#
  - Uses community-maintained library [VaultSharp](https://github.com/rajanadar/VaultSharp)
  - Provided examples:
    - Auth Methods ([AppRole](https://github.com/hashicorp/vault-examples/tree/main/examples/auth-methods/approle/Example.cs), [AWS](https://github.com/hashicorp/vault-examples/tree/main/examples/auth-methods/aws/Example.cs), [Azure](https://github.com/hashicorp/vault-examples/tree/main/examples/auth-methods/azure/Example.cs), [GCP](https://github.com/hashicorp/vault-examples/tree/main/examples/auth-methods/gcp/Example.cs), [Kubernetes](https://github.com/hashicorp/vault-examples/tree/main/examples/auth-methods/kubernetes/Example.cs))

## How To Use

Find the relevant directory for the concept you're interested in learning about, then find the file for your language of choice. You can use the example code as a reference or paste it into your application and tweak as needed. Each concept's directory also contains a readme explaining some of the specific terminology and operational setup.

This repo is not intended to be "run" as a standalone application. 

For an out-of-the-box runnable sample app, please see our Hello-Vault repos.

Hello-Vault:
- [Go](https://github.com/hashicorp/hello-vault-go)

## How To Contribute

If you would like to submit a code example to this repo, please create a file containing one function (or a grouping of several related functions) in the appropriate directory.
