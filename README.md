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
    - [Client Application](examples/client-applications/python/) with AppRole Auth, Token Renewal, and Secret Management
- Java (Spring)
  - Uses community-maintained library [spring-vault](https://spring.io/projects/spring-vault)
  - Provided examples:
    - [Quick Start](examples/_quick-start/java/Example.java) with Token Auth
    - [Client Applications](examples/client-applications/):
      - [Pure Java](examples/client-applications/java-pure/) with AppRole Auth, Token Renewal, and Secret Management
      - [Spring Boot Web](examples/client-applications/java-web-springboot/) with Spring Cloud Vault Config and Web UI
      - [Tomcat Web](examples/client-applications/java-web-tomcat/) with Servlet + JSP and Token Auto-Renewal
- C
  - Uses [libcurl](https://curl.se/libcurl/) and [json-c](https://github.com/json-c/json-c)
  - Provided examples:
    - [Client Application](examples/client-applications/c/) with AppRole Auth, Token Renewal, and Secret Management
- C++
  - Uses [libcurl](https://curl.se/libcurl/) and [nlohmann/json](https://github.com/nlohmann/json) (C++17)
  - Provided examples:
    - [Client Application](examples/client-applications/cpp/) with AppRole Auth, Token Renewal, and Secret Management
- Script (Bash)
  - Uses [curl](https://curl.se/) and [jq](https://stedolan.github.io/jq/) with [Vault Proxy](https://developer.hashicorp.com/vault/docs/agent-and-proxy/proxy)
  - Provided examples:
    - [Script Samples](examples/client-applications/script-sample/) with Vault Proxy integration
    - Supports KV, Database Dynamic/Static, SSH (KV/OTP/Signed Certificate), and AWS secrets
    - No Vault CLI required, uses pure curl

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

## Client Applications

For complete, runnable client application examples that demonstrate real-world Vault integration patterns, see the [Client Applications](examples/client-applications/) directory.

These examples include:
- Complete applications in multiple languages (C, C++, Java, Python, Spring Boot, Tomcat)
- Script examples using Vault Proxy
- Real-world patterns for authentication, token renewal, and secret management
- Multiple secret engine support (KV v2, Database Dynamic/Static, SSH, AWS)

Each example includes:
- Full source code
- Build and run instructions
- Configuration examples
- Detailed documentation

See the [Client Applications README](examples/client-applications/README.md) for more details.

## How To Contribute

If you would like to submit a code example to this repo, please create a file
containing one function (or a grouping of several related functions) in the
appropriate directory.
