# Kubernetes Authentication

The code snippets in this directory are examples in various languages of how to
authenticate an application to Vault with the
[Kubernetes authentication method](https://www.vaultproject.io/docs/auth/kubernetes)
in order to fetch a secret.

As the client, all we need to do is pass along the JWT token representing our
application's Kubernetes Service Account in our login request to Vault. This
token is automatically mounted to your application's container by Kubernetes.
Read more [here](https://www.vaultproject.io/docs/auth/kubernetes).

## Configuring the Vault server

If an operator has not already set up the Kubernetes auth method in Vault for
you, then you must first configure the Vault server with its own Service Account
token to be able to communicate with the Kubernetes API so it can verify that
the client's service-account token is valid.

The service account that will be performing that verification needs the
ClusterRole `system:auth-delegator`.

```sh
export TOKEN_REVIEW_JWT=$(kubectl get secret $TOKEN_REVIEWER_SECRET --output='go-template={{ .data.token }}' | base64 --decode)
export KUBE_HOST=$(kubectl config view --raw --minify --flatten --output='jsonpath={.clusters[].cluster.server}')
kubectl config view --raw --minify --flatten --output='jsonpath={.clusters[].cluster.certificate-authority-data}' | base64 --decode > path/to/kube_ca_cert

vault write auth/kubernetes/config \
 	token_reviewer_jwt=${TOKEN_REVIEW_JWT} \
    kubernetes_host=${KUBE_HOST} \
    kubernetes_ca_cert=@path/to/kube_ca_cert \
    issuer="kubernetes/serviceaccount"
```

The "issuer" field is normally only required when running Kubernetes 1.21 or
above, and
[may differ from the default value above](https://www.vaultproject.io/docs/auth/kubernetes#discovering-the-service-account-issuer).

Finally, make sure to create a role in Vault bound to your pod's service
account:

```sh
vault write auth/kubernetes/role/dev-role-k8s \
    policies="dev-policy" \
    bound_service_account_names="my-app" \
	bound_service_account_namespaces="default"
```

## Tutorials

See the HashiCorp
[Learn guides](https://learn.hashicorp.com/collections/vault/kubernetes) for
tutorials that explain a variety of Kubernetes-related Vault topics, such as
[how to integrate a Kubernetes with an external Vault instance](https://learn.hashicorp.com/tutorials/vault/kubernetes-external-vault)
and
[how to install Vault on Kubernetes](https://learn.hashicorp.com/tutorials/vault/kubernetes-raft-deployment-guide?in=vault/kubernetes).
