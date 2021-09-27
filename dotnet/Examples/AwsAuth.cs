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
        public string GetSecretAWSAuthIAM()
        {
            var vaultAddr = Environment.GetEnvironmentVariable("VAULT_ADDR");
            var roleName = "dev-role-iam";

            var amazonSecurityTokenServiceConfig = new AmazonSecurityTokenServiceConfig();

            // Initalize BasicAWS Credentials w/ an acessKey and secretKey
            Amazon.Runtime.AWSCredentials awsCredentials = new SessionAWSCredentials(awsAccessKeyId: Environment.GetEnvironmentVariable("AWS_ACCESS_KEY_ID"), 
                                                                awsSecretAccessKey: Environment.GetEnvironmentVariable("AWS_SECRET_ACCESS_KEY"),
                                                                token: Environment.GetEnvironmentVariable("AWS_SESSION_TOKEN"));
            
            /*Amazon.Runtime.AWSCredentials awsCredentials = new BasicAWSCredentials(accessKey: Environment.GetEnvironmentVariable("AWS_ACCESS_KEY_ID"), 
                                                                secretKey: Environment.GetEnvironmentVariable("AWS_SECRET_ACCESS_KEY"));*/
            
            var iamRequest = GetCallerIdentityRequestMarshaller.Instance.Marshall(new GetCallerIdentityRequest());
            
            iamRequest.Endpoint = new Uri(amazonSecurityTokenServiceConfig.DetermineServiceURL());
            iamRequest.ResourcePath = "/";

            iamRequest.Headers.Add("User-Agent", "some-agent");
            iamRequest.Headers.Add("X-Amz-Security-Token", awsCredentials.GetCredentials().Token);
            iamRequest.Headers.Add("Content-Type", "application/x-www-form-urlencoded; charset=utf-8");
            
            foreach(var key in iamRequest.Headers.Keys)
            {
                Console.WriteLine(iamRequest.Headers[key].ToString());
            }

            try
            {
                // Use AWS utility to sign our request
                new AWS4Signer().Sign(iamRequest, amazonSecurityTokenServiceConfig, new RequestMetrics(), new Amazon.Runtime.ImmutableCredentials(Environment.GetEnvironmentVariable("AWS_ACCESS_KEY_ID"), Environment.GetEnvironmentVariable("AWS_SECRET_ACCESS_KEY"), Environment.GetEnvironmentVariable("AWS_SESSION_TOKEN")));
                //new AWS4Signer().Sign(iamRequest, amazonSecurityTokenServiceConfig, new RequestMetrics(), awsCredentials.GetCredentials().AccessKey, awsCredentials.GetCredentials().SecretKey);
            }
            catch(Exception e)
            {
                Console.WriteLine($"Can't sign request: ", e.Message);
            }

            var iamSTSRequestHeaders = iamRequest.Headers;

            // Convert headers to Base64 encoded version
            var base64EncodedIamRequestHeaders = Convert.ToBase64String(Encoding.UTF8.GetBytes(JsonConvert.SerializeObject(iamSTSRequestHeaders)));
            Console.WriteLine(base64EncodedIamRequestHeaders.ToString());

            IAuthMethodInfo authMethod = new IAMAWSAuthMethodInfo(roleName: roleName, requestHeaders: base64EncodedIamRequestHeaders);
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