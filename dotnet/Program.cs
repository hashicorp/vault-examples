using System;
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
            // Initialize one of the several auth methods.
            IAuthMethodInfo authMethod = new TokenAuthMethodInfo("MY_VAULT_TOKEN");

            // Initialize settings. You can also set proxies, custom delegates etc. here.
            var vaultClientSettings = new VaultClientSettings("https://MY_VAULT_SERVER:8200", authMethod);

            IVaultClient vaultClient = new VaultClient(vaultClientSettings);

            // Use client to read a key-value secret.

            // Very important to provide mountpath and secret name as two separate parameters. Don't provide a single combined string.
            // Please use named parameters for 100% clarity of code. (the method also takes version and wrapTimeToLive as params)

            // Note: It is generally not recommended to use .Result
            Secret<SecretData> kv2Secret = vaultClient.V1.Secrets.KeyValue.V2
                               .ReadSecretAsync(path: "secretPath", mountPoint: "mountPointIfNotDefault").Result;

            // Generate a dynamic Consul credential
            Secret<ConsulCredentials> consulCreds = vaultClient.V1.Secrets.Consul.GetCredentialsAsync(null, null).Result;
            string consulToken = consulCreds.Data.Token;        }
    }
}
