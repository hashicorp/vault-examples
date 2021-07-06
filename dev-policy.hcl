path "secret/data/*" {
  capabilities = ["create", "update", "read"]
}

path "secret/data/foo" {
  capabilities = ["read"]
}