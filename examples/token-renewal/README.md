# Token Renewal

All secrets in Vault have a [time-to-live](https://www.vaultproject.io/docs/concepts/tokens#token-time-to-live-periodic-tokens-and-explicit-max-ttls) (TTL), including the client tokens that we use when interacting with Vault.

Before the TTL has been reached, you can renew the token as many times as you want, up until the point where the token has reached its [max TTL](https://learn.hashicorp.com/tutorials/vault/tokens#ttl-and-max-ttl). At this point, a full re-login to Vault is required. All tokens have a max TTL, even if not explicitly set. The system default value is 32 days.

Currently, only the Go client library supports token renewal, using a struct called [LifetimeWatcher](https://pkg.go.dev/github.com/hashicorp/vault/api#LifetimeWatcher). More language examples will be added as token renewal capabilities are added to more client libraries.

When doing token renewals, it is important to make sure that all cases are being handled: a) the token was successfully renewed, b) it was unable to be renewed because of an error or some configuration, or c) it has reached its max TTL and thus needs to fully log in again.

See the sample app Hello-Vault ([Go](https://github.com/hashicorp/hello-vault-go)) for an out-of-the-box working demo that includes token renewal.