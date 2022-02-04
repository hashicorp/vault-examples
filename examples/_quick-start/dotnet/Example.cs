using System;
using System.Collections.Generic;
using VaultSharp;
using VaultSharp.V1.AuthMethods;
using VaultSharp.V1.AuthMethods.Token;
using VaultSharp.V1.Commons;

// This is the accompanying code for the Developer Quick Start.
// WARNING: Using root tokens is insecure and should never be done in production!
namespace DeveloperQuickstart
{
    class Program
    {
        static void Main(string[] args)
        {
            // Authentication
            IAuthMethodInfo authMethod = new TokenAuthMethodInfo(vaultToken: "dev-only-token");

            VaultClientSettings vaultClientSettings = new VaultClientSettings("http://127.0.0.1:8200", authMethod);
            IVaultClient vaultClient = new VaultClient(vaultClientSettings);

            // Writing a secret
            var secretData = new Dictionary<string, object> { { "password", "Hashi123" } };
            vaultClient.V1.Secrets.KeyValue.V2.WriteSecretAsync(
                path: "/my-secret-password",
                data: secretData,
                mountPoint: "secret"
            ).Wait();

            Console.WriteLine("Secret written successfully.");

            // Reading a secret
            Secret<SecretData> secret = vaultClient.V1.Secrets.KeyValue.V2.ReadSecretAsync(
                path: "/my-secret-password",
                mountPoint: "secret"
            ).Result;

            var password = secret.Data.Data["password"];

            if (password.ToString() != "Hashi123")
            {
                throw new System.Exception("Unexpected password");
            }

            Console.WriteLine("Access granted!");
        }
    }
}
