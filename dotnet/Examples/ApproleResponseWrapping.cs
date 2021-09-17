using System;
using System.Collections.Generic;
using System.IO;
using VaultSharp;
using VaultSharp.V1.AuthMethods;
using VaultSharp.V1.AuthMethods.AppRole;
using VaultSharp.V1.AuthMethods.Token;
using VaultSharp.V1.Commons;

namespace dotnet 
{
    class ApproleAuthExample
    {
        public static string GetSecretWithAppRole()
        {
            // A combination of a Role ID and Secret ID is required to log in to Vault with an AppRole.
	        // The Secret ID is a value that needs to be protected, so instead of the app having knowledge of the secret ID directly,
	        // we have a trusted orchestrator (https://learn.hashicorp.com/tutorials/vault/secure-introduction?in=vault/app-integration#trusted-orchestrator)
	        // give the app access to a short-lived response-wrapping token (https://www.vaultproject.io/docs/concepts/response-wrapping).
	        // Read more at: https://learn.hashicorp.com/tutorials/vault/approle-best-practices?in=vault/auth-methods#secretid-delivery-best-practices             
            var roleId = Environment.GetEnvironmentVariable("APPROLE_ROLE_ID");
            var vaultAddr = "http://127.0.0.1:8200";

            string wrappingToken = File.ReadAllText("../dotnet/path/to/wrapping-token"); // placed here by a trusted orchestrator

            // We need to create two VaultClient objects for authenticating via AppRole. The first is for
            // using the unwrap utility. We need to initalize the client with the wrapping token.
            IAuthMethodInfo wrappedTokenAuthMethod = new TokenAuthMethodInfo(wrappingToken);
            var wrappedVaultClientSettings = new VaultClientSettings(vaultAddr, wrappedTokenAuthMethod);

            IVaultClient wrappedVaultClient = new VaultClient(wrappedVaultClientSettings);

            // because our client is initialized with the wrapping token, we don't and SHOULD NOT
            // pass the token in the parameter. Else, it'll deplete its single usage.
            Secret<Dictionary<string, object>> secretIdData =  wrappedVaultClient.V1.System
                .UnwrapWrappedResponseDataAsync<Dictionary<string, object>>(null).Result; 

            var secretId = secretIdData.Data["secret_id"]; // Grab the secret_id 

            // We create a second VaultClient and initialize it with the AppRole auth method and our 
            // new credentials.
            IAuthMethodInfo authMethod = new AppRoleAuthMethodInfo(roleId, secretId.ToString());
            var vaultClientSettings = new VaultClientSettings(vaultAddr, authMethod);

            IVaultClient vaultClient = new VaultClient(vaultClientSettings);

            // We can retreive the secret from there
            Secret<SecretData> kv2Secret = null;
            try
            {   
                // Very important to provide mountpath and secret name as two separate parameters. Don't provide a single combined string.
                // Please use named parameters for 100% clarity of code. (the method also takes version and wrapTimeToLive as params)
                kv2Secret = vaultClient.V1.Secrets.KeyValue.V2.ReadSecretAsync(path: "/creds").Result;
            }
            catch(Exception e)
            {
                Console.WriteLine($"An error occurred while retreiving secret: ", e.Message); 
                return string.Empty;
            }
            
            var password = kv2Secret.Data.Data["password"];
            
            return password.ToString();
        }
    }
}