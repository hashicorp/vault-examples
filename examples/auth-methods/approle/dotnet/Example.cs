// Copyright IBM Corp. 2021, 2025
// SPDX-License-Identifier: MPL-2.0

using System;
using System.Collections.Generic;
using System.IO;
using VaultSharp;
using VaultSharp.V1.AuthMethods;
using VaultSharp.V1.AuthMethods.AppRole;
using VaultSharp.V1.AuthMethods.Token;
using VaultSharp.V1.Commons;

namespace Examples 
{
    public class ApproleAuthExample
    {
        const string DefaultTokenPath = "../../../path/to/wrapping-token";
        
        /// <summary>
        /// Fetches a key-value secret (kv-v2) after authenticating to Vault via AppRole authentication
        /// </summary>
        public string GetSecretWithAppRole()
        {
            // A combination of a Role ID and Secret ID is required to log in to Vault with an AppRole.
	        // The Secret ID is a value that needs to be protected, so instead of the app having knowledge of the secret ID directly,
	        // we have a trusted orchestrator (https://learn.hashicorp.com/tutorials/vault/secure-introduction?in=vault/app-integration#trusted-orchestrator)
	        // give the app access to a short-lived response-wrapping token (https://www.vaultproject.io/docs/concepts/response-wrapping).
	        // Read more at: https://learn.hashicorp.com/tutorials/vault/approle-best-practices?in=vault/auth-methods#secretid-delivery-best-practices             
            var vaultAddr = Environment.GetEnvironmentVariable("VAULT_ADDR");
            if(String.IsNullOrEmpty(vaultAddr))
            {
                throw new System.ArgumentNullException("Vault Address");
            }

            var roleId = Environment.GetEnvironmentVariable("APPROLE_ROLE_ID");
            if(String.IsNullOrEmpty(vaultAddr))
            {
                throw new System.ArgumentNullException("AppRole Role Id");
            }
            // Get the path to wrapping token or fall back on default path
            string pathToToken = !String.IsNullOrEmpty(Environment.GetEnvironmentVariable("WRAPPING_TOKEN_PATH")) ? Environment.GetEnvironmentVariable("WRAPPING_TOKEN_PATH") : DefaultTokenPath;
            string wrappingToken = File.ReadAllText(pathToToken); // placed here by a trusted orchestrator

            // We need to create two VaultClient objects for authenticating via AppRole. The first is for
            // using the unwrap utility. We need to initialize the client with the wrapping token.
            IAuthMethodInfo wrappedTokenAuthMethod = new TokenAuthMethodInfo(wrappingToken);
            var vaultClientSettingsForUnwrapping = new VaultClientSettings(vaultAddr, wrappedTokenAuthMethod);

            IVaultClient vaultClientForUnwrapping = new VaultClient(vaultClientSettingsForUnwrapping);

            // We pass null here instead of the wrapping token to avoid depleting its single usage
            // given that we already initialized our client with the wrapping token
            Secret<Dictionary<string, object>> secretIdData =  vaultClientForUnwrapping.V1.System
                .UnwrapWrappedResponseDataAsync<Dictionary<string, object>>(null).Result; 

            var secretId = secretIdData.Data["secret_id"]; // Grab the secret_id 

            // We create a second VaultClient and initialize it with the AppRole auth method and our new credentials.
            IAuthMethodInfo authMethod = new AppRoleAuthMethodInfo(roleId, secretId.ToString());
            var vaultClientSettings = new VaultClientSettings(vaultAddr, authMethod);

            IVaultClient vaultClient = new VaultClient(vaultClientSettings);

            // We can retrieve the secret from VaultClient
            Secret<SecretData> kv2Secret = null;
            kv2Secret = vaultClient.V1.Secrets.KeyValue.V2.ReadSecretAsync(path: "/creds").Result;
            
            var password = kv2Secret.Data.Data["password"];
            
            return password.ToString();
        }
    }
}