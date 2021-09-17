using System;
using System.IO;
using VaultSharp;
using VaultSharp.V1.AuthMethods;
using VaultSharp.V1.AuthMethods.Token;
using VaultSharp.V1.Commons;

// WARNING: The code in this hello-world file is potentially insecure. It is not safe for use in production.
// This is just a quickstart for trying out the Vault client library for the first time.GetSecretWithToken()
namespace dotnet
{
    class TokenAuthExample
    {
        string GetSecretWithToken()
        {
            // Get the token via env variable
            var token = Environment.GetEnvironmentVariable("VAULT_TOKEN");

            // Address of vault server
            var vaultAddr = "http://127.0.0.1:8200";

            // Initialize settings. You can also set proxies, custom delegates etc. here.
            // Note: VaultSharp performs a lazy login in this case, so login will only be attempted when 
            // performing some action on Vault (e.g. reading a secret)
            IAuthMethodInfo authMethod = new TokenAuthMethodInfo(token);

            var vaultClientSettings = new VaultClientSettings(vaultAddr, authMethod);
            IVaultClient vaultClient = new VaultClient(vaultClientSettings);

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
