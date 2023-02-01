# Copyright (c) HashiCorp, Inc.
# SPDX-License-Identifier: MPL-2.0

require "vault"

Vault.configure do |config|
    config.address = "http://127.0.0.1:8200"
    config.token = "dev-only-token"
end

secret_data = {data: {password: "Hashi123"}}
Vault.logical.write("secret/data/my-secret-password", secret_data)

puts "Secret written successfully."

secret = Vault.logical.read("secret/data/my-secret-password")
password = secret.data[:data][:password]

abort "Unexpected password" if password != "Hashi123"

puts "Access granted!"
