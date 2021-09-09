module github.com/hashicorp/vault-examples

go 1.16

replace (
	github.com/hashicorp/vault => ../../../vault
	github.com/hashicorp/vault/api => ../../../vault/api
)

require (
	github.com/hashicorp/vault v1.8.1
	github.com/hashicorp/vault/api v1.1.1
)
