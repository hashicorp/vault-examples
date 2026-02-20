// Copyright IBM Corp. 2021, 2025
// SPDX-License-Identifier: MPL-2.0

using System;
using System.IO;
using VaultSharp;
using VaultSharp.V1.AuthMethods;
using VaultSharp.V1.AuthMethods.Kubernetes;
using VaultSharp.V1.Commons;

namespace Examples
{
    public class KubernetesAuthExample 
    {
        const string DefaultTokenPath = "path/to/service-account-token";

        // Fetches a key-value secret (kv-v2) after authenticating to Vault with a Kubernetes service account.
        public string GetSecretWithK8s()
        {
            var vaultAddr = Environment.GetEnvironmentVariable("VAULT_ADDR");
            if(String.IsNullOrEmpty(vaultAddr))
            {
                throw new System.ArgumentNullException("Vault Address");
            }

            var roleName = Environment.GetEnvironmentVariable("VAULT_ROLE");
            if(String.IsNullOrEmpty(roleName))
            {
                throw new System.ArgumentNullException("Vault Role Name");
            }

            // Get the path to service account token or fall back on default path
            string pathToToken = String.IsNullOrEmpty(Environment.GetEnvironmentVariable("SA_TOKEN_PATH")) ? DefaultTokenPath : Environment.GetEnvironmentVariable("SA_TOKEN_PATH");
            string jwt = File.ReadAllText(pathToToken); 

            IAuthMethodInfo authMethod = new KubernetesAuthMethodInfo(roleName, jwt);
            var vaultClientSettings = new VaultClientSettings(vaultAddr, authMethod);

            IVaultClient vaultClient = new VaultClient(vaultClientSettings); 

            // We can retrieve the secret after creating our VaultClient object
            Secret<SecretData> kv2Secret = null;
            kv2Secret = vaultClient.V1.Secrets.KeyValue.V2.ReadSecretAsync(path: "/creds").Result;
            
            var password = kv2Secret.Data.Data["password"];
            
            return password.ToString();
        }
    }
}