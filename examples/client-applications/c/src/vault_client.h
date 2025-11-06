#ifndef VAULT_CLIENT_H
#define VAULT_CLIENT_H

#include <curl/curl.h>
#include <json.h>
#include <time.h>
#include "config.h"

// Vault client structure
typedef struct {
    char vault_url[256];
    char token[512];
    time_t token_expiry;
    time_t token_issued;  // Token issuance time
    CURL *curl;
    app_config_t *config;  // Configuration reference
    
    // KV secret cache
    json_object *cached_kv_secret;
    time_t kv_last_refresh;
    char kv_path[256];
    int kv_version;  // KV secret version tracking
    
    // Database Dynamic secret cache
    json_object *cached_db_dynamic_secret;
    time_t db_dynamic_last_refresh;
    char db_dynamic_path[256];
    char lease_id[512];
    time_t lease_expiry;
    
    // Database Static secret cache
    json_object *cached_db_static_secret;
    time_t db_static_last_refresh;
    char db_static_path[256];
} vault_client_t;

// Function declarations
int vault_client_init(vault_client_t *client, app_config_t *config);
void vault_client_cleanup(vault_client_t *client);
int vault_login(vault_client_t *client, const char *role_id, const char *secret_id);
int vault_renew_token(vault_client_t *client);
int vault_get_secret(vault_client_t *client, const char *path, json_object **secret_data);
int vault_is_token_valid(vault_client_t *client);
void vault_print_token_status(vault_client_t *client);
void vault_cleanup_secret(json_object *secret_data);

// KV secret renewal related functions
int vault_refresh_kv_secret(vault_client_t *client);
int vault_get_kv_secret(vault_client_t *client, json_object **secret_data);
int vault_get_kv_secret_direct(vault_client_t *client, json_object **secret_data);
int vault_is_kv_secret_stale(vault_client_t *client);
void vault_cleanup_kv_cache(vault_client_t *client);

// Database Dynamic secret related functions
int vault_refresh_db_dynamic_secret(vault_client_t *client);
int vault_get_db_dynamic_secret(vault_client_t *client, json_object **secret_data);
int vault_get_db_dynamic_secret_direct(vault_client_t *client, json_object **secret_data);
int vault_is_db_dynamic_secret_stale(vault_client_t *client);
int vault_check_lease_status(vault_client_t *client, const char *lease_id, time_t *expire_time, int *ttl);
void vault_cleanup_db_dynamic_cache(vault_client_t *client);

// Database Static secret related functions
int vault_refresh_db_static_secret(vault_client_t *client);
int vault_get_db_static_secret(vault_client_t *client, json_object **secret_data);
int vault_get_db_static_secret_direct(vault_client_t *client, json_object **secret_data);
int vault_is_db_static_secret_stale(vault_client_t *client);
void vault_cleanup_db_static_cache(vault_client_t *client);

#endif