// Copyright IBM Corp. 2021, 2025
// SPDX-License-Identifier: MPL-2.0

using System;
using System.Collections.Generic;
using System.IO;
using System.Threading.Tasks;
using Google.Apis.Auth.OAuth2;
using Google.Apis.Services;
using Google.Apis.Iam.v1;
using Newtonsoft.Json;
using VaultSharp;
using VaultSharp.V1.AuthMethods;
using VaultSharp.V1.AuthMethods.GoogleCloud;
using VaultSharp.V1.Commons;

using Data = Google.Apis.Iam.v1.Data;

namespace Examples
{
    public class GCPAuthExample 
    {
        /// <summary>
        /// Fetches a key-value secret (kv-v2) after authenticating to Vault via GCP IAM,
        /// one of two auth methods used to authenticate with GCP (the other is GCE auth).
        /// </summary>
        public string GetSecretGcp()
        {
            var vaultAddr = Environment.GetEnvironmentVariable("VAULT_ADDR");
            if(String.IsNullOrEmpty(vaultAddr))
            {
                throw new System.ArgumentNullException("Vault Address");
            }

            var roleName = Environment.GetEnvironmentVariable("VAULT_ROLE");
            if(String.IsNullOrEmpty(roleName))
            {
                throw new System.ArgumentNullException("Vault Role Name");
            }

            // Learn about authenticating to GCS with service account credentials at https://cloud.google.com/docs/authentication/production
            if(String.IsNullOrEmpty(Environment.GetEnvironmentVariable("GOOGLE_APPLICATION_CREDENTIALS")))
            {
                Console.WriteLine("WARNING: Environment variable GOOGLE_APPLICATION_CREDENTIALS was not set. IAM client for JWT signing will fall back to default instance credentials.");
            }

            var jwt = SignJWT();
 
            IAuthMethodInfo authMethod = new GoogleCloudAuthMethodInfo(roleName, jwt);
            var vaultClientSettings = new VaultClientSettings(vaultAddr, authMethod);

            IVaultClient vaultClient = new VaultClient(vaultClientSettings); 

            // We can retrieve the secret after creating our VaultClient object
            Secret<SecretData> kv2Secret = null;
            kv2Secret = vaultClient.V1.Secrets.KeyValue.V2.ReadSecretAsync(path: "/creds").Result;
            
            var password = kv2Secret.Data.Data["password"];
            
            return password.ToString();
        }

        /// <summary>
        /// Generate signed JWT from GCP IAM
        /// </summary>
        private string SignJWT()
        {
            var roleName = Environment.GetEnvironmentVariable("GCP_ROLE");
            var svcAcctName = Environment.GetEnvironmentVariable("GCP_SERVICE_ACCOUNT_NAME");
            var gcpProjName = Environment.GetEnvironmentVariable("GOOGLE_CLOUD_PROJECT");

            IamService iamService = new IamService(new BaseClientService.Initializer
            {
                HttpClientInitializer = GetCredential(),
                ApplicationName = "Google-iamSample/0.1",
            });

            string svcEmail = $"{svcAcctName}@{gcpProjName}.iam.gserviceaccount.com";
            string name = $"projects/-/serviceAccounts/{svcEmail}";  

            TimeSpan currentTime = (DateTime.UtcNow - new DateTime(1970, 1, 1));
            int expiration = (int)(currentTime.TotalSeconds) + 900;

            Data.SignJwtRequest requestBody = new Data.SignJwtRequest();
            requestBody.Payload = JsonConvert.SerializeObject(new Dictionary<string, object> ()
            {
                { "aud", $"vault/{roleName}" } ,
                { "sub", svcEmail } ,
                { "exp", expiration }
            });

            ProjectsResource.ServiceAccountsResource.SignJwtRequest request = iamService.Projects.ServiceAccounts.SignJwt(requestBody, name);

            Data.SignJwtResponse response = request.Execute();
            
            return JsonConvert.SerializeObject(response.SignedJwt).Replace("\"", "");
        }

        public static GoogleCredential GetCredential()
        {
            GoogleCredential credential = Task.Run(() => GoogleCredential.GetApplicationDefaultAsync()).Result;
            if (credential.IsCreateScopedRequired)
            {
                credential = credential.CreateScoped("https://www.googleapis.com/auth/cloud-platform");
            }
           return credential;
        }
    }
}