# Vault Examples

A collection of copy-pastable code example snippets demonstrating the various
ways to use the Vault client libraries for various languages to authenticate and
retrieve secrets.

## Currently Supported Languages

- Go
  - Uses official library
    [HashiCorp Vault](https://pkg.go.dev/github.com/hashicorp/vault/api)
  - Provided examples:
    - [Quick Start](examples/_quick-start/go/example.go) with Token Auth
    - Auth Methods ([AppRole](examples/auth-methods/approle/go/example.go),
      [AWS](examples/auth-methods/aws/go/example.go),
      [Azure](examples/auth-methods/azure/go/example.go),
      [GCP](examples/auth-methods/gcp/go/example.go),
      [Kubernetes](examples/auth-methods/kubernetes/go/example.go))
    - [Token Renewal](examples/token-renewal/go/example.go)
- Ruby
  - Uses official library [vault-ruby](https://github.com/hashicorp/vault-ruby)
  - Provided examples:
    - [Quick Start](examples/_quick-start/ruby/example.rb) with Token Auth
- C#
  - Uses community-maintained library
    [VaultSharp](https://github.com/rajanadar/VaultSharp)
  - Provided examples:
    - [Quick Start](examples/_quick-start/dotnet/Example.cs) with Token Auth
    - Auth Methods ([AppRole](examples/auth-methods/approle/dotnet/Example.cs),
      [AWS](examples/auth-methods/aws/dotnet/Example.cs),
      [Azure](examples/auth-methods/azure/dotnet/Example.cs),
      [GCP](examples/auth-methods/gcp/dotnet/Example.cs),
      [Kubernetes](examples/auth-methods/kubernetes/dotnet/Example.cs))
- Python
  - Uses community-maintained library [HVAC](https://hvac.readthedocs.io/en/stable/overview.html)
  - Provided examples:
    - [Quick Start](examples/_quick-start/python/example.py) with Token Auth
- Java (Spring)
  - Uses community-maintained library [spring-vault](https://spring.io/projects/spring-vault)
  - Provided examples:
    - [Quick Start](examples/_quick-start/java/Example.java) with Token Auth

## How To Use

Find the relevant directory for the concept you're interested in learning about,
then find the file for your language of choice. You can use the example code as
a reference or paste it into your application and tweak as needed. Each
concept's directory also contains a readme explaining some of the specific
terminology and operational setup.

This repo is not intended to be "run" as a standalone application.

For an out-of-the-box runnable sample app, please see our Hello-Vault repos.

Hello-Vault:

- [Go](https://github.com/hashicorp/hello-vault-go)
- [C#](https://github.com/hashicorp/hello-vault-dotnet)

## How To Contribute

If you would like to submit a code example to this repo, please create a file
containing one function (or a grouping of several related functions) in the
appropriate directory.
