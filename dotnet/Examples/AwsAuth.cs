using System;
using System.Text;
using Amazon.Runtime;
using Amazon.Runtime.Internal;
using Amazon.Runtime.Internal.Auth;
using Amazon.Runtime.Internal.Util;
using Amazon.SecurityToken;
using Amazon.SecurityToken.Model;
using Amazon.SecurityToken.Model.Internal.MarshallTransformations;
using Newtonsoft.Json;
using VaultSharp;
using VaultSharp.V1.AuthMethods;
using VaultSharp.V1.AuthMethods.AWS;
using VaultSharp.V1.Commons;
using VaultSharp.V1.SecretsEngines.AWS;

namespace dotnet
{
    class AwsAuthExample 
    {
        public void GetSecretAWSAuthIAM()
        {
            var vaultAddr = "http://127.0.0.1:8200";
            var roleName = "";
            var nonce = "";

            var amazonSecurityTokenServiceConfig = new AmazonSecurityTokenServiceConfig();

            // Pretty sure I need the session token here
            Amazon.Runtime.AWSCredentials awsCredentials = new BasicAWSCredentials(accessKey: Environment.GetEnvironmentVariable("AWS_ACCESS_KEY_ID"), 
                                                                secretKey: Environment.GetEnvironmentVariable("AWS_SECRET_ACCESS_KEY"),
                                                                sessionToken: Environment.GetEnvironmentVariable("AWS_SESSION_TOKEN")); // explicit credentials
            
            var iamRequest = GetCallerIdentityRequestMarshaller.Instance.Marshall(new GetCallerIdentityRequest());
            
            iamRequest.Endpoint = new Uri(amazonSecurityTokenServiceConfig.DetermineServiceURL());
            iamRequest.ResourcePath = "/";

            iamRequest.Headers.Add("User-Agent", "");
            iamRequest.Headers.Add("X-Amz-Security-Token", awsCredentials.GetCredentials().Token);
            iamRequest.Headers.Add("Content-Type", "application/x-www-form-urlencoded; charset=utf-8");

            new AWS4Signer().Sign(iamRequest, amazonSecurityTokenServiceConfig, new RequestMetrics(), awsCredentials.GetCredentials().AccessKey, awsCredentials.GetCredentials().SecretKey);

            // This is the point, when you have the final set of required Headers.
            var iamSTSRequestHeaders = iamRequest.Headers;

            // Step 3: Convert the headers into a base64 value needed by Vault.
            var base64EncodedIamRequestHeaders = Convert.ToBase64String(Encoding.UTF8.GetBytes(JsonConvert.SerializeObject(iamSTSRequestHeaders)));

            // Step 4: Setup the IAM AWS Auth Info.

            IAuthMethodInfo authMethod = new IAMAWSAuthMethodInfo(nonce: nonce, roleName: roleName, requestHeaders: base64EncodedIamRequestHeaders);
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