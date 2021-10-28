using System;
using System.IO;
using VaultSharp;
using VaultSharp.V1.AuthMethods;
using VaultSharp.V1.AuthMethods.Kubernetes;
using VaultSharp.V1.Commons;

namespace Examples
{
    public class KubernetesAuthExample 
    {
        const string DefaultTokenPath = "path/to/service-account-token";

        // Fetches a key-value secret (kv-v2) after authenticating to Vault with a Kubernetes service account.
        //
        // As the client, all we need to do is pass along the JWT token representing our application's Kubernetes Service Account in our login request to Vault.
        // This token is automatically mounted to your application's container by Kubernetes. Read more at https://www.vaultproject.io/docs/auth/kubernetes
        //
        // SETUP NOTES: If an operator has not already set up Kubernetes auth in Vault for you, then you must also first configure the Vault server with its own Service Account token to be able to communicate with the Kubernetes API
        // so it can verify that the client's service-account token is valid. The service account that will be performing that verification needs the ClusterRole system:auth-delegator.
        //
        //    export TOKEN_REVIEW_JWT=$(kubectl get secret $TOKEN_REVIEWER_SECRET --output='go-template={{ .data.token }}' | base64 --decode)
        //    export KUBE_HOST=$(kubectl config view --raw --minify --flatten --output='jsonpath={.clusters[].cluster.server}')
        //    kubectl config view --raw --minify --flatten --output='jsonpath={.clusters[].cluster.certificate-authority-data}' | base64 --decode > path/to/kube_ca_cert
        //
        //    vault write auth/kubernetes/config \
        //  	token_reviewer_jwt=${TOKEN_REVIEW_JWT} \
        //      kubernetes_host=${KUBE_HOST} \
        //      kubernetes_ca_cert=@path/to/kube_ca_cert \
        //      issuer="kubernetes/serviceaccount"
        //
        // The "issuer" field is normally only required when running Kubernetes 1.21 or above, and may differ from the default value above:
        // https://www.vaultproject.io/docs/auth/kubernetes#discovering-the-service-account-issuer.
        //
        // Finally, make sure to create a role in Vault bound to your pod's service account:
        //
        // 	vault write auth/kubernetes/role/dev-role-k8s \
        //     	policies="dev-policy" \
        //     	bound_service_account_names="my-app" \
        //		bound_service_account_namespaces="default"
        public string GetSecretWithK8s()
        {
            var vaultAddr = Environment.GetEnvironmentVariable("VAULT_ADDR");
            if(String.IsNullOrEmpty(vaultAddr))
            {
                throw new System.ArgumentNullException("Vault Address");
            }

            var roleName = Environment.GetEnvironmentVariable("K8S_ROLE");
            if(String.IsNullOrEmpty(roleName))
            {
                throw new System.ArgumentNullException("Kubernetes Role Name");
            }

            // Get the path to wrapping token or fall back on default path
            string pathToToken = !String.IsNullOrEmpty(Environment.GetEnvironmentVariable("SA_TOKEN_PATH")) ? Environment.GetEnvironmentVariable("SA_TOKEN_PATH") : DefaultTokenPath;
            string jwt = File.ReadAllText(pathToToken); 

            IAuthMethodInfo authMethod = new KubernetesAuthMethodInfo(roleName, jwt);
            var vaultClientSettings = new VaultClientSettings(vaultAddr, authMethod);

            IVaultClient vaultClient = new VaultClient(vaultClientSettings); 

            // We can retrieve the secret after creating our VaultClient object
            Secret<SecretData> kv2Secret = null;
            kv2Secret = vaultClient.V1.Secrets.KeyValue.V2.ReadSecretAsync(path: "/creds").Result;
            
            var password = kv2Secret.Data.Data["password"];
            
            return password.ToString();
        }
    }
}