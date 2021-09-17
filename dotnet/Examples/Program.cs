using System;
using System.IO;
using VaultSharp;
using VaultSharp.V1.AuthMethods;
using VaultSharp.V1.AuthMethods.Token;
using VaultSharp.V1.Commons;
using VaultSharp.V1.SecretsEngines.Consul;

namespace dotnet
{
    class Program
    {
        static void Main(string[] args)
        {
            // Run test examples here
            ApproleAuthExample appRoleEg = new ApproleAuthExample();
            string results = ApproleAuthExample.GetSecretWithAppRole();
            Console.WriteLine(results);
        }
    }
}
