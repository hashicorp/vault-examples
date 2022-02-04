# Quick Start

This is the full version of the code accompanying the Developer Quick Start.

You can run it against a Vault dev server to write and read your first secret!

To start up a Vault dev server, run:

```
docker run -p 8200:8200 -e 'VAULT_DEV_ROOT_TOKEN_ID=dev-only-token' vault
```

or without Docker,

```
vault server -dev -dev-root-token-id="dev-only-token"
```