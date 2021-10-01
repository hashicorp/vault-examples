module github.com/hashicorp/vault-examples

go 1.16

replace (
	github.com/hashicorp/vault => ../../../vault
	github.com/hashicorp/vault/api => ../../../vault/api
)

require (
	cloud.google.com/go v0.56.0
	github.com/hashicorp/vault v1.8.1
	github.com/hashicorp/vault/api v1.1.1
	google.golang.org/genproto v0.0.0-20200526211855-cb27e3aa2013
)
