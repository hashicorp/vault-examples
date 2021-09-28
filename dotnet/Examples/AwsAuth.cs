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

namespace Examples
{
    public class AwsAuthExample 
    {
        /// <summary> 
        /// Fetches a key-value secret (kv-v2) after authenticating to Vault via AWS IAM,
        /// one of two auth methods used to authenticate with AWS (the other is EC2 auth).
        /// A role must first be created in Vault bound to the IAM ARN you wish to authenticate with, like so:
        /// 	vault write auth/aws/role/dev-role-iam \
        ///     auth_type=iam \
        ///     bound_iam_principal_arn="arn:aws:iam::AWS-ACCOUNT-NUMBER:role/AWS-IAM-ROLE-NAME" \
        ///     ttl=24h
        ///  Learn more about the available parameters at https://www.vaultproject.io/api/auth/aws#parameters-10
        /// </summary>
        public string GetSecretAWSAuthIAM()
        {
            var vaultAddr = Environment.GetEnvironmentVariable("VAULT_ADDR");
            if(String.IsNullOrEmpty(vaultAddr))
            {
                throw new System.ArgumentNullException("Vault Address");
            }

            var roleName = Environment.GetEnvironmentVariable("AWS_ROLE_NAME");
            if(String.IsNullOrEmpty(roleName))
            {
                throw new System.ArgumentNullException("AWS Role Name");
            }

            var amazonSecurityTokenServiceConfig = new AmazonSecurityTokenServiceConfig();

            // Initialize BasicAWS Credentials w/ an accessKey and secretKey
            Amazon.Runtime.AWSCredentials awsCredentials = new BasicAWSCredentials(accessKey: Environment.GetEnvironmentVariable("AWS_ACCESS_KEY_ID"), 
                                                                secretKey: Environment.GetEnvironmentVariable("AWS_SECRET_ACCESS_KEY"));
            
            // Construct the IAM Request and add necessary headers
            var iamRequest = GetCallerIdentityRequestMarshaller.Instance.Marshall(new GetCallerIdentityRequest());
            
            iamRequest.Endpoint = new Uri(amazonSecurityTokenServiceConfig.DetermineServiceURL());
            iamRequest.ResourcePath = "/";

            iamRequest.Headers.Add("User-Agent", "some-agent");
            iamRequest.Headers.Add("X-Amz-Security-Token", awsCredentials.GetCredentials().Token);
            iamRequest.Headers.Add("Content-Type", "application/x-www-form-urlencoded; charset=utf-8");

            try
            {
                // Use AWS utility to sign our request
                new AWS4Signer().Sign(iamRequest, amazonSecurityTokenServiceConfig, new RequestMetrics(), awsCredentials.GetCredentials().AccessKey, awsCredentials.GetCredentials().SecretKey);
            }
            catch(Exception e)
            {
                Console.WriteLine($"Failed to sign IAM request: ", e.Message);
            }

            var iamSTSRequestHeaders = iamRequest.Headers;

            // Convert headers to Base64 encoded version
            var base64EncodedIamRequestHeaders = Convert.ToBase64String(Encoding.UTF8.GetBytes(JsonConvert.SerializeObject(iamSTSRequestHeaders)));

            IAuthMethodInfo authMethod = new IAMAWSAuthMethodInfo(roleName: roleName, requestHeaders: base64EncodedIamRequestHeaders);
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