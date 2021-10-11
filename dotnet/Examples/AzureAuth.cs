using System;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Net.Http;
using System.Text;
using Newtonsoft.Json;
using VaultSharp;
using VaultSharp.V1.AuthMethods;
using VaultSharp.V1.AuthMethods.Azure;
using VaultSharp.V1.Commons;

namespace Examples
{
    public class AzureAuthExample 
    {
        /// <summary> 
        /// Fetches a key-value secret (kv-v2) after authenticating to Vault via Azure authentication.
        /// This example assumes you have a configured Azure AD Application. 
        /// Learn more about Azure authentication prerequisites: https://www.vaultproject.io/docs/auth/azure
        ///
        /// A role must first be created in Vault bound to the resource groups and subscription ids:
        /// 	vault write auth/azure/role/dev-role \
        ///     policies="dev-policy"
        ///     bound_subscription_ids=$AZURE_SUBSCRIPTION_ID \
        ///     bound_resource_groups=test-rg \ 
        ///     ttl=24h
        /// </summary>
        public string GetSecretWithAzureAuth()
        {
            string vaultAddr = Environment.GetEnvironmentVariable("VAULT_ADDR");
            if(String.IsNullOrEmpty(vaultAddr))
            {
                throw new System.ArgumentNullException("Vault Address");
            }

            string roleName = Environment.GetEnvironmentVariable("ROLE_NAME");
            if(String.IsNullOrEmpty(roleName))
            {
                throw new System.ArgumentNullException("Role Name");
            }   

            string jwt = GetJWT();

            IAuthMethodInfo authMethod = new AzureAuthMethodInfo(roleName, jwt);
            var vaultClientSettings = new VaultClientSettings(vaultAddr, authMethod);

            IVaultClient vaultClient = new VaultClient(vaultClientSettings);
        
            // We can retrieve the secret from the VaultClient object
            Secret<SecretData> kv2Secret = null;
            kv2Secret = vaultClient.V1.Secrets.KeyValue.V2.ReadSecretAsync(path: "/creds").Result;
            
            var password = kv2Secret.Data.Data["password"];
            
            return password.ToString();
        }
    
        /// <summary>
        /// Query Azure Resource Manager (ARM) for an access token
        /// </summary>
        private string GetJWT()
        {
            // Build request to query ARM for an access token
            HttpWebRequest request = (HttpWebRequest)WebRequest.Create("http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://management.azure.com/");
            request.Headers["Metadata"] = "true";
            request.Method = "GET";

            string results;
            try
            {
                HttpWebResponse response = (HttpWebResponse)request.GetResponse();

                // Pipe response Stream to a StreamReader and extract access token
                StreamReader streamResponse = new StreamReader(response.GetResponseStream()); 
                string stringResponse = streamResponse.ReadToEnd();
                var resultsDict = JsonConvert.DeserializeObject<Dictionary<string, string>>(stringResponse);
                results = resultsDict["access_token"];
            }
            catch (Exception e)
            {
                results = String.Format("{0} \n\n{1}", e.Message, e.InnerException != null ? e.InnerException.Message : "Acquire token failed");
            }

            return results;
        }
    }
}