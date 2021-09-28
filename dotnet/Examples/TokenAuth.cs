using System;
using System.IO;
using VaultSharp;
using VaultSharp.V1.AuthMethods;
using VaultSharp.V1.AuthMethods.Token;
using VaultSharp.V1.Commons;

// WARNING: The code in this hello-world file is potentially insecure. It is not safe for use in production.
// This is just a quickstart for trying out the Vault client library for the first time.
namespace Examples
{
    public class TokenAuthExample
    {
        /// <summary>
        /// Fetches a key-value secret (kv-v2) after authenticating to Vault via Token authentication 
        /// </summary>
        public string GetSecretWithToken()
        {
            /* WARNING: Storing any long-lived token with secret access in an environment variable poses a security risk.
	           Additionally, root tokens should never be used in production or against Vault installations containing real secrets.
	           See approle-with-response-wrapping.go for an example of how to use wrapping tokens for greater security. */
            var vaultAddr = Environment.GetEnvironmentVariable("VAULT_ADDR");
            if(String.IsNullOrEmpty(vaultAddr))
            {
                throw new System.ArgumentNullException("Vault Address");
            }

            var token = Environment.GetEnvironmentVariable("VAULT_TOKEN");
            if(String.IsNullOrEmpty(token))
            {
                throw new System.ArgumentNullException("Vault Token");
            }

            /* VaultSharp performs a lazy login in this case, so login will only be attempted when 
               performing some action on Vault (e.g. reading a secret) */
            IAuthMethodInfo authMethod = new TokenAuthMethodInfo(token);

            var vaultClientSettings = new VaultClientSettings(vaultAddr, authMethod);
            IVaultClient vaultClient = new VaultClient(vaultClientSettings);

            // We can retrieve the secret from the VaultClient object
            Secret<SecretData> kv2Secret = null;
            try
            {   
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
