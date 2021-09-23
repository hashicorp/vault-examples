package main

import (
	"fmt"
	"log"

	vault "github.com/hashicorp/vault/api"
)

// Once you've set the token for your Vault client, you will need to periodically renew its lease.
// A function like this should be run as a goroutine to avoid blocking.
func renewToken(client *vault.Client) {
	for {
		vaultLoginResp, err := login(client)
		if err != nil {
			log.Fatalf("unable to authenticate to Vault: %v", err)
		}
		tokenErr := manageTokenLifecycle(client, vaultLoginResp)
		if tokenErr != nil {
			log.Fatalf("unable to start managing token lifecycle: %v", tokenErr)
		}
	}
}

// Starts token lifecycle management. Returns only fatal errors as errors, otherwise returns nil so we can attempt login again.
func manageTokenLifecycle(client *vault.Client, token *vault.Secret) error {
	renew := token.Auth.Renewable // You may notice a different top-level field called Renewable. That one is used for dynamic secrets renewal, not token renewal.
	if renew {
		watcher, err := client.NewLifetimeWatcher(&vault.LifetimeWatcherInput{
			Secret:    token,
			Increment: 3600, // Learn more about this optional value in https://www.vaultproject.io/docs/concepts/lease#lease-durations-and-renewal
		})
		if err != nil {
			return fmt.Errorf("unable to initialize new lifetime watcher for renewing auth token: %w", err)
		}

		go watcher.Start()
		defer watcher.Stop()

		for {
			select {
			// `DoneCh` will return if renewal fails, or if the remaining lease duration is
			// under a built-in threshold and either renewing is not extending it or
			// renewing is disabled.  In any case, the caller needs to attempt to log in again.
			case err := <-watcher.DoneCh():
				if err != nil {
					log.Printf("Failed to renew token: %v. Re-attempting login.", err)
					return nil
				}
				log.Printf("Token can no longer be renewed. Re-attempting login.")
				return nil

			// Successfully completed renewal
			case renewal := <-watcher.RenewCh():
				log.Printf("Successfully renewed: %#v", renewal)
			}
		}
	}
	log.Printf("Token is not configured to be renewable. Re-attempting login.")
	return nil
}

func login(client *vault.Client) (*vault.Secret, error) {
	// WARNING: A plaintext password like this is obviously insecure.
	// See the files starting in auth-* for full examples of how to securely log in to Vault using various auth methods.
	// This is just demonstrating the basic idea that a *vault.Secret is returned by a call to an auth method's /login API endpoint.
	resp, err := client.Logical().Write("auth/userpass/login/my-user", map[string]interface{}{"password": "my-password"})
	if err != nil {
		return nil, err
	}

	// have the client use that token for all Vault calls from now on
	client.SetToken(resp.Auth.ClientToken)

	return resp, nil
}
