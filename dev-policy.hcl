path "kv-v2/data/*" {
  capabilities = ["create", "update", "read"]
}

path "kv-v2/data/foo" {
  capabilities = ["read"]
}