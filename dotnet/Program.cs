using System;
using System.IO;
using VaultSharp;
using VaultSharp.V1.AuthMethods;
using VaultSharp.V1.AuthMethods.Token;
using VaultSharp.V1.Commons;
using VaultSharp.V1.SecretsEngines.Consul;

// WARNING: The code in this hello-world file is potentially insecure. It is not safe for use in production.
// This is just a quickstart for trying out the Vault client library for the first time.
namespace dotnet
{
    class Program
    {
        static void Main(string[] args)
        {
            // Get the token via env variable
            var token = Environment.GetEnvironmentVariable("TOKEN");

            // Provide Vault Token
            IAuthMethodInfo authMethod = new TokenAuthMethodInfo(token);

            // Initialize settings. You can also set proxies, custom delegates etc. here.
            // Note: VaultSharp performs a lazy login in this case, so login will only be attempted when 
            // performing some action on Vault
            var vaultClientSettings = new VaultClientSettings("https://127.0.0.1:8200", authMethod);
            IVaultClient vaultClient = new VaultClient(vaultClientSettings);

            // Use client to read a key-value secret.

            // Very important to provide mountpath and secret name as two separate parameters. Don't provide a single combined string.
            // Please use named parameters for 100% clarity of code. (the method also takes version and wrapTimeToLive as params)

            // Note: It is generally not recommended to use .Result
            Secret<SecretData> kv2Secret = null;
            try
            {
                kv2Secret = vaultClient.V1.Secrets.KeyValue.V2.ReadSecretAsync(path: "kv-v2/data/creds").Result;
            }
            catch(Exception e)
            {
                Console.WriteLine(e.Message); 
                return;  
            }
            
            // gets a secret at kv2Secret/
            Console.WriteLine(kv2Secret.ToString());
        }
    }
}
