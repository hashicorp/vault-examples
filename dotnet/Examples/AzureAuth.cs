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
        public class InstanceMetadata
        {
            public string name { get; set; }
            public string resourceGroupName { get; set; }
            public string subscriptionId { get; set; }
        }

        const string MetadataEndPoint = "http://169.254.169.254/metadata/instance?api-version=2017-08-01";
        const string AccessTokenEndPoint = "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://management.azure.com/";

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

            string roleName = Environment.GetEnvironmentVariable("VAULT_ROLE");
            if(String.IsNullOrEmpty(roleName))
            {
                throw new System.ArgumentNullException("Vault Role Name");
            }   

            string jwt = GetJWT();
            InstanceMetadata metadata = GetMetadata();

            IAuthMethodInfo authMethod = new AzureAuthMethodInfo(roleName: roleName, jwt: jwt, subscriptionId: metadata.subscriptionId, resourceGroupName: metadata.resourceGroupName, virtualMachineName: metadata.name);
            var vaultClientSettings = new VaultClientSettings(vaultAddr, authMethod);

            IVaultClient vaultClient = new VaultClient(vaultClientSettings);
        
            // We can retrieve the secret from the VaultClient object
            Secret<SecretData> kv2Secret = null;
            kv2Secret = vaultClient.V1.Secrets.KeyValue.V2.ReadSecretAsync(path: "/creds").Result;
            
            var password = kv2Secret.Data.Data["password"];
            
            return password.ToString();
        }
    
        /// <summary>
        /// Query Azure Resource Manage for metadata about the Azure instance
        /// </summary>
        private InstanceMetadata GetMetadata()
        {
            HttpWebRequest metadataRequest = (HttpWebRequest)WebRequest.Create(MetadataEndPoint);
            metadataRequest.Headers["Metadata"] = "true";
            metadataRequest.Method = "GET";

            HttpWebResponse metadataResponse = (HttpWebResponse)metadataRequest.GetResponse();

            StreamReader streamResponse = new StreamReader(metadataResponse.GetResponseStream());
            string stringResponse = streamResponse.ReadToEnd();
            var resultsDict = JsonConvert.DeserializeObject<Dictionary<string, InstanceMetadata>>(stringResponse);
            
            return resultsDict["compute"];
        }

        /// <summary>
        /// Query Azure Resource Manager (ARM) for an access token
        /// </summary>
        private string GetJWT()
        {
            HttpWebRequest request = (HttpWebRequest)WebRequest.Create(AccessTokenEndPoint);
            request.Headers["Metadata"] = "true";
            request.Method = "GET";

            HttpWebResponse response = (HttpWebResponse)request.GetResponse();

            // Pipe response Stream to a StreamReader and extract access token
            StreamReader streamResponse = new StreamReader(response.GetResponseStream()); 
            string stringResponse = streamResponse.ReadToEnd();
            var resultsDict = JsonConvert.DeserializeObject<Dictionary<string, string>>(stringResponse);

            return resultsDict["access_token"];
        }
    }
}