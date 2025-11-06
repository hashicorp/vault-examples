#include "vault_client.h"
#include "config.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

// Structure to store HTTP response
struct http_response {
    char *data;
    size_t size;
};

// libcurl callback function
static size_t write_callback(void *contents, size_t size, size_t nmemb, struct http_response *response) {
    size_t total_size = size * nmemb;
    response->data = realloc(response->data, response->size + total_size + 1);
    
    if (response->data) {
        memcpy(&(response->data[response->size]), contents, total_size);
        response->size += total_size;
        response->data[response->size] = 0;
    }
    
    return total_size;
}

// Initialize Vault client
int vault_client_init(vault_client_t *client, app_config_t *config) {
    if (!client || !config) return -1;
    
    // Store configuration reference
    client->config = config;
    
    // Set URL
    strncpy(client->vault_url, config->vault_url, sizeof(client->vault_url) - 1);
    client->vault_url[sizeof(client->vault_url) - 1] = '\0';
    
    // Initialize CURL
    client->curl = curl_easy_init();
    if (!client->curl) {
        fprintf(stderr, "Failed to initialize CURL\n");
        return -1;
    }
    
    // Set CURL options (from configuration)
    curl_easy_setopt(client->curl, CURLOPT_TIMEOUT, config->http_timeout);
    curl_easy_setopt(client->curl, CURLOPT_FOLLOWLOCATION, 1L);
    curl_easy_setopt(client->curl, CURLOPT_SSL_VERIFYPEER, 0L);
    curl_easy_setopt(client->curl, CURLOPT_SSL_VERIFYHOST, 0L);
    
    client->token[0] = '\0';
    client->token_expiry = 0;
    client->token_issued = 0;
    
    // Initialize KV cache
    client->cached_kv_secret = NULL;
    client->kv_last_refresh = 0;
    client->kv_path[0] = '\0';
    client->kv_version = -1;  // Initial version is -1 (no cache)
    
    // Initialize Database Dynamic cache
    client->cached_db_dynamic_secret = NULL;
    client->db_dynamic_last_refresh = 0;
    client->db_dynamic_path[0] = '\0';
    client->lease_id[0] = '\0';
    client->lease_expiry = 0;
    
    // Initialize Database Static cache
    client->cached_db_static_secret = NULL;
    client->db_static_last_refresh = 0;
    client->db_static_path[0] = '\0';
    
    // Set KV path (Entity-based)
    if (config->secret_kv.enabled && config->secret_kv.kv_path[0]) {
        snprintf(client->kv_path, sizeof(client->kv_path), "%s-kv/data/%s", 
                config->entity, config->secret_kv.kv_path);
    }
    
    // Set Database Dynamic path (Entity-based)
    if (config->secret_database_dynamic.enabled && config->secret_database_dynamic.role_id[0]) {
        snprintf(client->db_dynamic_path, sizeof(client->db_dynamic_path), "%s-database/creds/%s", 
                config->entity, config->secret_database_dynamic.role_id);
    }
    
    // Set Database Static path (Entity-based)
    if (config->secret_database_static.enabled && config->secret_database_static.role_id[0]) {
        snprintf(client->db_static_path, sizeof(client->db_static_path), "%s-database/static-creds/%s", 
                config->entity, config->secret_database_static.role_id);
    }
    
    return 0;
}

// Cleanup Vault client
void vault_client_cleanup(vault_client_t *client) {
    if (client) {
        if (client->curl) {
            curl_easy_cleanup(client->curl);
            client->curl = NULL;
        }
        
        // Cleanup KV cache
        vault_cleanup_kv_cache(client);
        
        // Cleanup Database Dynamic cache
        vault_cleanup_db_dynamic_cache(client);
        
        // Cleanup Database Static cache
        vault_cleanup_db_static_cache(client);
    }
}

// AppRole login
int vault_login(vault_client_t *client, const char *role_id, const char *secret_id) {
    if (!client || !role_id || !secret_id) return -1;
    
    // Create new CURL handle
    CURL *curl = curl_easy_init();
    if (!curl) {
        fprintf(stderr, "Failed to initialize CURL\n");
        return -1;
    }
    
    // Create JSON request
    json_object *request = json_object_new_object();
    json_object_object_add(request, "role_id", json_object_new_string(role_id));
    json_object_object_add(request, "secret_id", json_object_new_string(secret_id));
    
    char *json_string = (char*)json_object_to_json_string(request);
    
    // Setup HTTP request
    struct http_response response = {0};
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_callback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, json_string);
    curl_easy_setopt(curl, CURLOPT_POSTFIELDSIZE, strlen(json_string));
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, client->config->http_timeout);
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 0L);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYHOST, 0L);
    
    // Set URL
    char url[512];
    snprintf(url, sizeof(url), "%s/v1/auth/approle/login", client->vault_url);
    curl_easy_setopt(curl, CURLOPT_URL, url);
    
    // Set Content-Type header
    struct curl_slist *headers = NULL;
    headers = curl_slist_append(headers, "Content-Type: application/json");
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    
    // Execute request
    CURLcode res = curl_easy_perform(curl);
    curl_slist_free_all(headers);
    json_object_put(request);
    
    if (res != CURLE_OK) {
        fprintf(stderr, "Login request failed: %s\n", curl_easy_strerror(res));
        free(response.data);
        curl_easy_cleanup(curl);
        return -1;
    }
    
    // Parse response
    json_object *json_response = json_tokener_parse(response.data);
    if (!json_response) {
        fprintf(stderr, "Failed to parse login response\n");
        free(response.data);
        return -1;
    }
    
    // Extract token
    json_object *auth, *client_token;
    if (json_object_object_get_ex(json_response, "auth", &auth) &&
        json_object_object_get_ex(auth, "client_token", &client_token)) {
        
        const char *token = json_object_get_string(client_token);
        strncpy(client->token, token, sizeof(client->token) - 1);
        client->token[sizeof(client->token) - 1] = '\0';
        
        // Record token issuance time
        client->token_issued = time(NULL);
        
        // Set token expiry time (use actual TTL from Vault)
        json_object *lease_duration;
        if (json_object_object_get_ex(auth, "lease_duration", &lease_duration)) {
            int ttl_seconds = json_object_get_int(lease_duration);
            client->token_expiry = client->token_issued + ttl_seconds;
            printf("Token TTL from Vault: %d seconds\n", ttl_seconds);
        } else {
            // Use default value if TTL info is not available (1 hour)
            client->token_expiry = client->token_issued + 3600;
            printf("Warning: No TTL info from Vault, using default 1 hour\n");
        }
        
        printf("Login successful. Token expires in %ld seconds\n", 
               client->token_expiry - time(NULL));
    } else {
        fprintf(stderr, "Failed to extract token from response\n");
        json_object_put(json_response);
        free(response.data);
        return -1;
    }
    
    json_object_put(json_response);
    free(response.data);
    curl_easy_cleanup(curl);
    return 0;
}

// Renew token
int vault_renew_token(vault_client_t *client) {
    if (!client || !client->token[0]) return -1;
    
    // Create new CURL handle
    CURL *curl = curl_easy_init();
    if (!curl) {
        fprintf(stderr, "Failed to initialize CURL for renewal\n");
        return -1;
    }
    
    // Setup HTTP request
    struct http_response response = {0};
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_callback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, "");
    curl_easy_setopt(curl, CURLOPT_POSTFIELDSIZE, 0);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, client->config->http_timeout);
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 0L);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYHOST, 0L);
    
    // Set URL
    char url[512];
    snprintf(url, sizeof(url), "%s/v1/auth/token/renew-self", client->vault_url);
    curl_easy_setopt(curl, CURLOPT_URL, url);
    
    // Set Authorization header
    char auth_header[1024];
    snprintf(auth_header, sizeof(auth_header), "X-Vault-Token: %s", client->token);
    struct curl_slist *headers = NULL;
    headers = curl_slist_append(headers, auth_header);
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    
    // Execute request
    CURLcode res = curl_easy_perform(curl);
    curl_slist_free_all(headers);
    
    if (res != CURLE_OK) {
        fprintf(stderr, "Token renewal failed: %s\n", curl_easy_strerror(res));
        free(response.data);
        curl_easy_cleanup(curl);
        return -1;
    }
    
    // Check HTTP status code
    long http_code;
    curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &http_code);
    if (http_code != 200) {
        fprintf(stderr, "Token renewal failed with HTTP %ld\n", http_code);
        printf("Response: %s\n", response.data);
        free(response.data);
        curl_easy_cleanup(curl);
        return -1;
    }
    
    // Parse response
    json_object *json_response = json_tokener_parse(response.data);
    if (json_response) {
        json_object *auth, *lease_duration;
        if (json_object_object_get_ex(json_response, "auth", &auth) &&
            json_object_object_get_ex(auth, "lease_duration", &lease_duration)) {
            
            int lease_seconds = json_object_get_int(lease_duration);
            time_t now = time(NULL);
            client->token_issued = now;  // Update renewal time
            client->token_expiry = now + lease_seconds;
            
            printf("Token renewed successfully. New expiry: %ld seconds\n", 
                   client->token_expiry - now);
        } else {
            printf("Warning: No lease_duration in renewal response\n");
            // Print response content (for debugging)
            printf("Renewal response: %s\n", response.data);
        }
        json_object_put(json_response);
    } else {
        printf("Warning: Failed to parse renewal response\n");
        printf("Renewal response: %s\n", response.data);
    }
    
    free(response.data);
    curl_easy_cleanup(curl);
    return 0;
}

// Get secret
int vault_get_secret(vault_client_t *client, const char *path, json_object **secret_data) {
    if (!client || !path || !secret_data) return -1;
    
    // Create new CURL handle
    CURL *curl = curl_easy_init();
    if (!curl) {
        fprintf(stderr, "Failed to initialize CURL for secret\n");
        return -1;
    }
    
    // Setup HTTP request
    struct http_response response = {0};
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_callback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
    curl_easy_setopt(curl, CURLOPT_HTTPGET, 1L);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, client->config->http_timeout);
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 0L);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYHOST, 0L);
    
    // Set URL
    char url[512];
    snprintf(url, sizeof(url), "%s/v1/%s", client->vault_url, path);
    curl_easy_setopt(curl, CURLOPT_URL, url);
    
    // Set Authorization header
    char auth_header[1024];
    snprintf(auth_header, sizeof(auth_header), "X-Vault-Token: %s", client->token);
    struct curl_slist *headers = NULL;
    headers = curl_slist_append(headers, auth_header);
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    
    // Execute request
    CURLcode res = curl_easy_perform(curl);
    curl_slist_free_all(headers);
    
    if (res != CURLE_OK) {
        fprintf(stderr, "Secret request failed: %s\n", curl_easy_strerror(res));
        free(response.data);
        curl_easy_cleanup(curl);
        return -1;
    }
    
    // Parse response
    json_object *json_response = json_tokener_parse(response.data);
    if (!json_response) {
        fprintf(stderr, "Failed to parse secret response\n");
        free(response.data);
        return -1;
    }
    
    // Extract secret data
    json_object *data, *data_obj;
    if (json_object_object_get_ex(json_response, "data", &data) &&
        json_object_object_get_ex(data, "data", &data_obj)) {
        
        *secret_data = json_object_get(data_obj); // Increase reference count
        
        printf("Secret retrieved successfully\n");
    } else {
        fprintf(stderr, "Failed to extract secret data\n");
        json_object_put(json_response);
        free(response.data);
        return -1;
    }
    
    // Release json_response (safe because secret_data has separate reference)
    json_object_put(json_response);
    free(response.data);
    curl_easy_cleanup(curl);
    return 0;
}

// Check token validity
int vault_is_token_valid(vault_client_t *client) {
    if (!client || !client->token[0]) return 0;
    
    time_t now = time(NULL);
    time_t total_ttl = client->token_expiry - client->token_issued;
    time_t elapsed = now - client->token_issued;
    time_t renewal_point = total_ttl * 4 / 5;  // Renewal needed at 4/5 point
    
    return (elapsed < renewal_point);
}

// Print token remaining time
void vault_print_token_status(vault_client_t *client) {
    if (!client || !client->token[0] || !client->config) return;
    
    time_t now = time(NULL);
    time_t remaining = client->token_expiry - now;
    
    if (remaining > 0) {
        printf("Token status: %ld seconds remaining (expires in %ld minutes)\n", 
               remaining, remaining / 60);
        
        // Calculate recommended renewal point (based on 4/5 point)
        time_t total_ttl = client->token_expiry - client->token_issued;
        time_t elapsed = time(NULL) - client->token_issued;
        time_t renewal_point = total_ttl * 4 / 5;  // 4/5 point
        time_t urgent_point = total_ttl * 9 / 10;  // 9/10 point
        
        if (elapsed >= urgent_point) {
            printf("⚠️  URGENT: Token should be renewed soon (at %ld%% of TTL)\n", 
                   (elapsed * 100) / total_ttl);
        } else if (elapsed >= renewal_point) {
            printf("🔄 Token renewal recommended (at %ld%% of TTL)\n", 
                   (elapsed * 100) / total_ttl);
        } else {
            printf("✅ Token is healthy (at %ld%% of TTL)\n", 
                   (elapsed * 100) / total_ttl);
        }
    } else {
        printf("❌ Token has expired!\n");
    }
}

// Cleanup secret data
void vault_cleanup_secret(json_object *secret_data) {
    if (secret_data) {
        json_object_put(secret_data);
    }
}

// Refresh KV secret (version-based)
int vault_refresh_kv_secret(vault_client_t *client) {
    if (!client || !client->config || !client->config->secret_kv.enabled) {
        return -1;
    }
    
    if (!client->kv_path[0]) {
        fprintf(stderr, "KV path not configured\n");
        return -1;
    }
    
    printf("🔄 Refreshing KV secret from path: %s\n", client->kv_path);
    
    // Get new secret (direct HTTP request for full response)
    json_object *new_secret = NULL;
    int result = vault_get_kv_secret_direct(client, &new_secret);
    
    if (result == 0 && new_secret) {
        // Extract version information
        json_object *data, *metadata, *version_obj;
        int new_version = -1;
        
        if (json_object_object_get_ex(new_secret, "data", &data) &&
            json_object_object_get_ex(data, "metadata", &metadata) &&
            json_object_object_get_ex(metadata, "version", &version_obj)) {
            
            new_version = json_object_get_int(version_obj);
        }
        
        // Update only if version is different or cache doesn't exist
        if (new_version != client->kv_version) {
            // Cleanup existing cache
            vault_cleanup_kv_cache(client);
            
            // Update cache
            client->cached_kv_secret = json_object_get(new_secret);
            client->kv_last_refresh = time(NULL);
            client->kv_version = new_version;
            
            printf("✅ KV secret updated (version: %d)\n", new_version);
        } else {
            printf("✅ KV secret unchanged (version: %d)\n", new_version);
            client->kv_last_refresh = time(NULL);  // Update last check time
        }
        
        // Cleanup temporary object
        json_object_put(new_secret);
        return 0;
    } else {
        fprintf(stderr, "❌ Failed to refresh KV secret\n");
        return -1;
    }
}

// Get KV secret (check cache)
int vault_get_kv_secret(vault_client_t *client, json_object **secret_data) {
    if (!client || !secret_data || !client->config || !client->config->secret_kv.enabled) {
        return -1;
    }
    
    // Refresh if cache is missing or stale
    if (!client->cached_kv_secret || vault_is_kv_secret_stale(client)) {
        printf("🔄 KV cache is stale, refreshing...\n");
        if (vault_refresh_kv_secret(client) != 0) {
            return -1;
        }
    }
    
    // Return cached data
    if (client->cached_kv_secret) {
        *secret_data = json_object_get(client->cached_kv_secret);
        return 0;
    }
    
    return -1;
}

// Check if KV secret is stale (version-based)
int vault_is_kv_secret_stale(vault_client_t *client) {
    if (!client || !client->config) {
        return 1;  // Consider stale if configuration is missing
    }
    
    // Always need refresh if cache doesn't exist
    if (!client->cached_kv_secret) {
        return 1;
    }
    
    // Version-based refresh: always check for latest version
    // KV v2 provides version information, so refresh is version-based rather than time-based
    return 1;  // Always attempt refresh to check version
}

// Cleanup KV cache
void vault_cleanup_kv_cache(vault_client_t *client) {
    if (client && client->cached_kv_secret) {
        json_object_put(client->cached_kv_secret);
        client->cached_kv_secret = NULL;
        client->kv_last_refresh = 0;
        client->kv_version = -1;  // Reset version as well
    }
}

// Refresh Database Dynamic secret
int vault_refresh_db_dynamic_secret(vault_client_t *client) {
    if (!client || !client->config || !client->config->secret_database_dynamic.enabled) {
        return -1;
    }
    
    if (!client->db_dynamic_path[0]) {
        fprintf(stderr, "Database Dynamic path not configured\n");
        return -1;
    }
    
    printf("🔄 Refreshing Database Dynamic secret from path: %s\n", client->db_dynamic_path);
    
    // Check TTL if existing cache is available
    if (client->cached_db_dynamic_secret && strlen(client->lease_id) > 0) {
        time_t expire_time;
        int ttl;
        if (vault_check_lease_status(client, client->lease_id, &expire_time, &ttl) == 0) {
            // Don't refresh if TTL is sufficient
            if (ttl > 10) {  // Don't refresh if more than 10 seconds remaining
                printf("✅ Database Dynamic secret is still valid (TTL: %d seconds)\n", ttl);
                client->db_dynamic_last_refresh = time(NULL);
                return 0;
            } else {
                printf("⚠️ Database Dynamic secret expiring soon (TTL: %d seconds), creating new credentials\n", ttl);
            }
        }
    }
    
    // Cleanup existing cache
    vault_cleanup_db_dynamic_cache(client);
    
    // Create new Database Dynamic secret
    json_object *new_secret = NULL;
    int result = vault_get_db_dynamic_secret_direct(client, &new_secret);
    
    if (result == 0 && new_secret) {
        // Extract lease_id
        json_object *lease_id_obj;
        if (json_object_object_get_ex(new_secret, "lease_id", &lease_id_obj)) {
            const char *lease_id = json_object_get_string(lease_id_obj);
            strncpy(client->lease_id, lease_id, sizeof(client->lease_id) - 1);
            client->lease_id[sizeof(client->lease_id) - 1] = '\0';
        }
        
        // Update cache
        client->cached_db_dynamic_secret = json_object_get(new_secret);
        client->db_dynamic_last_refresh = time(NULL);
        
        // Check lease expiry time
        time_t expire_time;
        int ttl = 0;
        if (strlen(client->lease_id) > 0 && vault_check_lease_status(client, client->lease_id, &expire_time, &ttl) == 0) {
            client->lease_expiry = expire_time;
        }
        
        printf("✅ Database Dynamic secret created successfully (TTL: %d seconds)\n", ttl);
        
        // Cleanup temporary object
        json_object_put(new_secret);
        return 0;
    } else {
        fprintf(stderr, "❌ Failed to refresh Database Dynamic secret\n");
        return -1;
    }
}

// Get Database Dynamic secret (with cache check)
int vault_get_db_dynamic_secret(vault_client_t *client, json_object **secret_data) {
    if (!client || !secret_data || !client->config || !client->config->secret_database_dynamic.enabled) {
        return -1;
    }
    
    // Refresh if cache doesn't exist or is stale
    if (!client->cached_db_dynamic_secret || vault_is_db_dynamic_secret_stale(client)) {
        printf("🔄 Database Dynamic cache is stale, refreshing...\n");
        if (vault_refresh_db_dynamic_secret(client) != 0) {
            return -1;
        }
    }
    
    // Return cached data
    if (client->cached_db_dynamic_secret) {
        *secret_data = json_object_get(client->cached_db_dynamic_secret);
        return 0;
    }
    
    return -1;
}

// Check if Database Dynamic secret is stale
int vault_is_db_dynamic_secret_stale(vault_client_t *client) {
    if (!client || !client->config || !client->cached_db_dynamic_secret) {
        return 1;  // Consider stale if cache doesn't exist
    }
    
    // Check lease status
    time_t expire_time;
    int ttl;
    if (vault_check_lease_status(client, client->lease_id, &expire_time, &ttl) == 0) {
        // Database Dynamic Secret is refreshed only when TTL is almost expired (10 seconds or less)
        int renewal_threshold = 10;  // Refresh when 10 seconds or less
        return (ttl <= renewal_threshold);
    }
    
    // Use default refresh interval if lease status check fails
    time_t now = time(NULL);
    time_t elapsed = now - client->db_dynamic_last_refresh;
    int refresh_interval = client->config->secret_kv.refresh_interval; // Use same interval as KV
    
    return (elapsed >= refresh_interval);
}

// Check lease status
int vault_check_lease_status(vault_client_t *client, const char *lease_id, time_t *expire_time, int *ttl) {
    if (!client || !lease_id || !expire_time || !ttl) {
        return -1;
    }
    
    // Set up HTTP request
    struct http_response response = {0};
    curl_easy_setopt(client->curl, CURLOPT_WRITEFUNCTION, write_callback);
    curl_easy_setopt(client->curl, CURLOPT_WRITEDATA, &response);
    curl_easy_setopt(client->curl, CURLOPT_HTTPGET, 1L);
    
    // Set URL
    char url[512];
    snprintf(url, sizeof(url), "%s/v1/sys/leases/lookup", client->vault_url);
    curl_easy_setopt(client->curl, CURLOPT_URL, url);
    
    // Set Authorization header
    char auth_header[1024];
    snprintf(auth_header, sizeof(auth_header), "X-Vault-Token: %s", client->token);
    struct curl_slist *headers = NULL;
    headers = curl_slist_append(headers, auth_header);
    headers = curl_slist_append(headers, "Content-Type: application/json");
    curl_easy_setopt(client->curl, CURLOPT_HTTPHEADER, headers);
    
    // Set POST data
    char post_data[1024];
    snprintf(post_data, sizeof(post_data), "{\"lease_id\":\"%s\"}", lease_id);
    curl_easy_setopt(client->curl, CURLOPT_POSTFIELDS, post_data);
    curl_easy_setopt(client->curl, CURLOPT_POSTFIELDSIZE, strlen(post_data));
    curl_easy_setopt(client->curl, CURLOPT_CUSTOMREQUEST, "POST");
    
    // Execute request
    CURLcode res = curl_easy_perform(client->curl);
    curl_slist_free_all(headers);
    
    if (res != CURLE_OK) {
        fprintf(stderr, "Lease status check failed: %s\n", curl_easy_strerror(res));
        free(response.data);
        return -1;
    }
    
    // Parse response
    json_object *json_response = json_tokener_parse(response.data);
    if (!json_response) {
        fprintf(stderr, "Failed to parse lease status response\n");
        free(response.data);
        return -1;
    }
    
    // Extract TTL
    json_object *data, *ttl_obj;
    if (json_object_object_get_ex(json_response, "data", &data) &&
        json_object_object_get_ex(data, "ttl", &ttl_obj)) {
        
        *ttl = json_object_get_int(ttl_obj);
        
        // Calculate expire_time
        *expire_time = time(NULL) + *ttl;
        
        json_object_put(json_response);
        free(response.data);
        return 0;
    }
    json_object_put(json_response);
    free(response.data);
    return -1;
}

// Get Database Dynamic secret directly (different JSON structure)
int vault_get_db_dynamic_secret_direct(vault_client_t *client, json_object **secret_data) {
    if (!client || !secret_data) return -1;
    
    // Set up HTTP request (Database Dynamic Secret uses GET request)
    struct http_response response = {0};
    curl_easy_setopt(client->curl, CURLOPT_WRITEFUNCTION, write_callback);
    curl_easy_setopt(client->curl, CURLOPT_WRITEDATA, &response);
    curl_easy_setopt(client->curl, CURLOPT_HTTPGET, 1L);
    
    // Set URL
    char url[512];
    snprintf(url, sizeof(url), "%s/v1/%s", client->vault_url, client->db_dynamic_path);
    curl_easy_setopt(client->curl, CURLOPT_URL, url);
    
    // Set Authorization header
    char auth_header[1024];
    snprintf(auth_header, sizeof(auth_header), "X-Vault-Token: %s", client->token);
    struct curl_slist *headers = NULL;
    headers = curl_slist_append(headers, auth_header);
    curl_easy_setopt(client->curl, CURLOPT_HTTPHEADER, headers);
    
    // Execute request
    CURLcode res = curl_easy_perform(client->curl);
    curl_slist_free_all(headers);
    
    if (res != CURLE_OK) {
        fprintf(stderr, "Database Dynamic secret request failed: %s\n", curl_easy_strerror(res));
        free(response.data);
        return -1;
    }
    
    // Check HTTP status code
    long http_code;
    curl_easy_getinfo(client->curl, CURLINFO_RESPONSE_CODE, &http_code);
    
    // Parse response
    json_object *json_response = json_tokener_parse(response.data);
    if (!json_response) {
        fprintf(stderr, "Failed to parse Database Dynamic secret response\n");
        printf("Raw response: %s\n", response.data);
        free(response.data);
        return -1;
    }
    
    // Check for errors
    json_object *errors;
    if (json_object_object_get_ex(json_response, "errors", &errors)) {
        printf("🔍 Debug: Vault returned errors:\n");
        printf("   %s\n", json_object_to_json_string(errors));
    }
    
    if (http_code != 200) {
        fprintf(stderr, "Database Dynamic secret request failed with HTTP %ld\n", http_code);
        printf("Response: %s\n", response.data);
        json_object_put(json_response);
        free(response.data);
        return -1;
    }
    
    // Database Dynamic secret returns full response (unlike KV which has data.data structure)
    *secret_data = json_object_get(json_response);
    json_object_get(*secret_data); // Increment reference count
    
    printf("Database Dynamic secret retrieved successfully\n");
    
    json_object_put(json_response);
    free(response.data);
    return 0;
}


// Get KV secret directly (returns full response)
int vault_get_kv_secret_direct(vault_client_t *client, json_object **secret_data) {
    if (!client || !secret_data) return -1;
    
    // Create new CURL handle
    CURL *curl = curl_easy_init();
    if (!curl) {
        fprintf(stderr, "Failed to initialize CURL for KV secret\n");
        return -1;
    }
    
    // Set up HTTP request
    struct http_response response = {0};
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_callback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
    curl_easy_setopt(curl, CURLOPT_HTTPGET, 1L);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, client->config->http_timeout);
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 0L);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYHOST, 0L);
    
    // Set URL
    char url[512];
    snprintf(url, sizeof(url), "%s/v1/%s", client->vault_url, client->kv_path);
    curl_easy_setopt(curl, CURLOPT_URL, url);
    
    // Set Authorization header
    char auth_header[1024];
    snprintf(auth_header, sizeof(auth_header), "X-Vault-Token: %s", client->token);
    struct curl_slist *headers = NULL;
    headers = curl_slist_append(headers, auth_header);
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    
    // Execute request
    CURLcode res = curl_easy_perform(curl);
    curl_slist_free_all(headers);
    
    if (res != CURLE_OK) {
        fprintf(stderr, "KV secret request failed: %s\n", curl_easy_strerror(res));
        free(response.data);
        curl_easy_cleanup(curl);
        return -1;
    }
    
    // Check HTTP status code
    long http_code;
    curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &http_code);
    if (http_code != 200) {
        fprintf(stderr, "KV secret request failed with HTTP %ld\n", http_code);
        printf("Response: %s\n", response.data);
        free(response.data);
        curl_easy_cleanup(curl);
        return -1;
    }
    
    // Parse response
    json_object *json_response = json_tokener_parse(response.data);
    if (!json_response) {
        fprintf(stderr, "Failed to parse KV secret response\n");
        free(response.data);
        curl_easy_cleanup(curl);
        return -1;
    }
    
    // Check for errors
    json_object *errors;
    if (json_object_object_get_ex(json_response, "errors", &errors)) {
        printf("🔍 Debug: Vault returned errors:\n");
        printf("   %s\n", json_object_to_json_string(errors));
        json_object_put(json_response);
        free(response.data);
        curl_easy_cleanup(curl);
        return -1;
    }
    
    // Return full response (including metadata)
    *secret_data = json_object_get(json_response);
    json_object_get(*secret_data); // Increment reference count
    
    printf("KV secret retrieved successfully\n");
    
    json_object_put(json_response);
    free(response.data);
    curl_easy_cleanup(curl);
    return 0;
}

// Cleanup Database Dynamic cache
void vault_cleanup_db_dynamic_cache(vault_client_t *client) {
    if (client && client->cached_db_dynamic_secret) {
        json_object_put(client->cached_db_dynamic_secret);
        client->cached_db_dynamic_secret = NULL;
        client->db_dynamic_last_refresh = 0;
        client->lease_id[0] = '\0';
        client->lease_expiry = 0;
    }
}

// Refresh Database Static secret
int vault_refresh_db_static_secret(vault_client_t *client) {
    if (!client || !client->config || !client->config->secret_database_static.enabled) {
        return -1;
    }
    
    if (!client->db_static_path[0]) {
        fprintf(stderr, "Database Static path not configured\n");
        return -1;
    }
    
    printf("🔄 Refreshing Database Static secret from path: %s\n", client->db_static_path);
    
    // Get new secret
    json_object *new_secret = NULL;
    int result = vault_get_db_static_secret_direct(client, &new_secret);
    
    if (result == 0 && new_secret) {
        // Cleanup existing cache
        vault_cleanup_db_static_cache(client);
        
        // Update cache
        client->cached_db_static_secret = json_object_get(new_secret);
        client->db_static_last_refresh = time(NULL);
        
        printf("✅ Database Static secret updated\n");
        
        json_object_put(new_secret);
        return 0;
    } else {
        fprintf(stderr, "❌ Failed to refresh Database Static secret\n");
        return -1;
    }
}

// Get Database Static secret (with cache check)
int vault_get_db_static_secret(vault_client_t *client, json_object **secret_data) {
    if (!client || !secret_data) {
        return -1;
    }
    
    // Check if cache is stale
    if (vault_is_db_static_secret_stale(client)) {
        printf("🔄 Database Static cache is stale, refreshing...\n");
        if (vault_refresh_db_static_secret(client) != 0) {
            return -1;
        }
    }
    
    // Return cached secret
    if (client->cached_db_static_secret) {
        *secret_data = json_object_get(client->cached_db_static_secret);
        return 0;
    }
    
    return -1;
}

// Get Database Static secret directly (HTTP request)
int vault_get_db_static_secret_direct(vault_client_t *client, json_object **secret_data) {
    if (!client || !secret_data) {
        return -1;
    }
    
    // Create separate CURL handle
    CURL *curl = curl_easy_init();
    if (!curl) {
        fprintf(stderr, "Failed to initialize CURL for Database Static secret\n");
        return -1;
    }
    
    // Build URL
    char url[512];
    snprintf(url, sizeof(url), "%s/v1/%s", client->vault_url, client->db_static_path);
    
    // Set up HTTP request
    struct http_response response = {0};
    curl_easy_setopt(curl, CURLOPT_URL, url);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_callback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
    curl_easy_setopt(curl, CURLOPT_HTTPGET, 1L);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, client->config->http_timeout);
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 0L);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYHOST, 0L);
    
    // Set headers
    struct curl_slist *headers = NULL;
    char auth_header[1024];
    snprintf(auth_header, sizeof(auth_header), "X-Vault-Token: %s", client->token);
    headers = curl_slist_append(headers, auth_header);
    
    if (client->config->vault_namespace[0]) {
        char ns_header[256];
        snprintf(ns_header, sizeof(ns_header), "X-Vault-Namespace: %s", client->config->vault_namespace);
        headers = curl_slist_append(headers, ns_header);
    }
    
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    
    // Execute HTTP request
    CURLcode res = curl_easy_perform(curl);
    long http_code;
    curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &http_code);
    
    curl_slist_free_all(headers);
    
    if (res != CURLE_OK) {
        fprintf(stderr, "Database Static secret request failed: %s\n", curl_easy_strerror(res));
        free(response.data);
        curl_easy_cleanup(curl);
        return -1;
    }
    
    // Parse JSON
    json_object *json_response = json_tokener_parse(response.data);
    if (!json_response) {
        fprintf(stderr, "Failed to parse Database Static secret response\n");
        free(response.data);
        curl_easy_cleanup(curl);
        return -1;
    }
    
    // Check for errors
    json_object *errors;
    if (json_object_object_get_ex(json_response, "errors", &errors)) {
        printf("🔍 Debug: Vault returned errors:\n");
        printf("   %s\n", json_object_to_json_string(errors));
    }
    
    if (http_code != 200) {
        fprintf(stderr, "Database Static secret request failed with HTTP %ld\n", http_code);
        printf("Response: %s\n", response.data);
        json_object_put(json_response);
        free(response.data);
        curl_easy_cleanup(curl);
        return -1;
    }
    
    printf("Database Static secret retrieved successfully\n");
    
    // Return only data section
    json_object *data;
    if (json_object_object_get_ex(json_response, "data", &data)) {
        *secret_data = json_object_get(data);
    } else {
        *secret_data = json_object_get(json_response);
    }
    
    json_object_put(json_response);
    free(response.data);
    curl_easy_cleanup(curl);
    return 0;
}

// Check if Database Static secret is stale
int vault_is_db_static_secret_stale(vault_client_t *client) {
    if (!client || !client->cached_db_static_secret) {
        return 1; // Consider stale if cache doesn't exist
    }
    
    time_t now = time(NULL);
    time_t elapsed = now - client->db_static_last_refresh;
    
    // Refresh every 5 minutes (Database Static doesn't change frequently)
    return (elapsed >= 300);
}

// Cleanup Database Static cache
void vault_cleanup_db_static_cache(vault_client_t *client) {
    if (client && client->cached_db_static_secret) {
        json_object_put(client->cached_db_static_secret);
        client->cached_db_static_secret = NULL;
        client->db_static_last_refresh = 0;
    }
}