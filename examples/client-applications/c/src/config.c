#include "config.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// INI file parsing function
int load_config(const char *config_file, app_config_t *config) {
    if (!config_file || !config) {
        return -1;
    }
    
    // Set default values
    strncpy(config->vault_url, DEFAULT_VAULT_URL, sizeof(config->vault_url) - 1);
    config->vault_url[sizeof(config->vault_url) - 1] = '\0';
    
    strncpy(config->vault_namespace, DEFAULT_VAULT_NAMESPACE, sizeof(config->vault_namespace) - 1);
    config->vault_namespace[sizeof(config->vault_namespace) - 1] = '\0';
    
    strncpy(config->entity, DEFAULT_ENTITY, sizeof(config->entity) - 1);
    config->entity[sizeof(config->entity) - 1] = '\0';
    
    config->vault_role_id[0] = '\0';
    config->vault_secret_id[0] = '\0';
    
    // Set secret engine default values
    config->secret_kv.enabled = 0;
    config->secret_kv.kv_path[0] = '\0';
    config->secret_kv.refresh_interval = DEFAULT_KV_REFRESH_INTERVAL;
    
    config->secret_database_dynamic.enabled = 0;
    config->secret_database_dynamic.role_id[0] = '\0';
    
    config->secret_database_static.enabled = 0;
    config->secret_database_static.role_id[0] = '\0';
    
    config->http_timeout = DEFAULT_HTTP_TIMEOUT;
    config->max_response_size = DEFAULT_MAX_RESPONSE_SIZE;
    
    // Open INI file
    FILE *file = fopen(config_file, "r");
    if (!file) {
        printf("Warning: Could not open config file '%s'. Using defaults.\n", config_file);
        return 0; // Continue with defaults
    }
    
    char line[512];
    char current_section[64] = "";
    
    while (fgets(line, sizeof(line), file)) {
        // Remove whitespace and newline characters
        line[strcspn(line, "\r\n")] = '\0';
        
        // Skip empty lines or comment lines
        if (line[0] == '\0' || line[0] == ';' || line[0] == '#') {
            continue;
        }
        
        // Handle section [section]
        if (line[0] == '[' && strchr(line, ']') != NULL) {
            char *end_bracket = strchr(line, ']');
            *end_bracket = '\0';
            strncpy(current_section, line + 1, sizeof(current_section) - 1);
            current_section[sizeof(current_section) - 1] = '\0';
            continue;
        }
        
        // Handle key=value
        char *equals = strchr(line, '=');
        if (equals != NULL) {
            *equals = '\0';
            char *key = line;
            char *value = equals + 1;
            
            // Remove leading and trailing whitespace
            while (*key == ' ' || *key == '\t') key++;
            while (*value == ' ' || *value == '\t') value++;
            
            char *key_end = key + strlen(key) - 1;
            char *value_end = value + strlen(value) - 1;
            
            while (key_end > key && (*key_end == ' ' || *key_end == '\t')) {
                *key_end = '\0';
                key_end--;
            }
            
            while (value_end > value && (*value_end == ' ' || *value_end == '\t')) {
                *value_end = '\0';
                value_end--;
            }
            
            // Apply configuration value
            if (strcmp(current_section, "vault") == 0) {
                if (strcmp(key, "entity") == 0) {
                    strncpy(config->entity, value, sizeof(config->entity) - 1);
                    config->entity[sizeof(config->entity) - 1] = '\0';
                } else if (strcmp(key, "url") == 0) {
                    strncpy(config->vault_url, value, sizeof(config->vault_url) - 1);
                    config->vault_url[sizeof(config->vault_url) - 1] = '\0';
                } else if (strcmp(key, "namespace") == 0) {
                    strncpy(config->vault_namespace, value, sizeof(config->vault_namespace) - 1);
                    config->vault_namespace[sizeof(config->vault_namespace) - 1] = '\0';
                } else if (strcmp(key, "role_id") == 0) {
                    strncpy(config->vault_role_id, value, sizeof(config->vault_role_id) - 1);
                    config->vault_role_id[sizeof(config->vault_role_id) - 1] = '\0';
                } else if (strcmp(key, "secret_id") == 0) {
                    strncpy(config->vault_secret_id, value, sizeof(config->vault_secret_id) - 1);
                    config->vault_secret_id[sizeof(config->vault_secret_id) - 1] = '\0';
                }
            } else if (strcmp(current_section, "secret-kv") == 0) {
                if (strcmp(key, "enabled") == 0) {
                    config->secret_kv.enabled = (strcmp(value, "true") == 0) ? 1 : 0;
                } else if (strcmp(key, "kv_path") == 0) {
                    strncpy(config->secret_kv.kv_path, value, sizeof(config->secret_kv.kv_path) - 1);
                    config->secret_kv.kv_path[sizeof(config->secret_kv.kv_path) - 1] = '\0';
                } else if (strcmp(key, "refresh_interval") == 0) {
                    config->secret_kv.refresh_interval = atoi(value);
                }
            } else if (strcmp(current_section, "secret-database-dynamic") == 0) {
                if (strcmp(key, "enabled") == 0) {
                    config->secret_database_dynamic.enabled = (strcmp(value, "true") == 0) ? 1 : 0;
                } else if (strcmp(key, "role_id") == 0) {
                    strncpy(config->secret_database_dynamic.role_id, value, sizeof(config->secret_database_dynamic.role_id) - 1);
                    config->secret_database_dynamic.role_id[sizeof(config->secret_database_dynamic.role_id) - 1] = '\0';
                }
            } else if (strcmp(current_section, "secret-database-static") == 0) {
                if (strcmp(key, "enabled") == 0) {
                    config->secret_database_static.enabled = (strcmp(value, "true") == 0) ? 1 : 0;
                } else if (strcmp(key, "role_id") == 0) {
                    strncpy(config->secret_database_static.role_id, value, sizeof(config->secret_database_static.role_id) - 1);
                    config->secret_database_static.role_id[sizeof(config->secret_database_static.role_id) - 1] = '\0';
                }
            } else if (strcmp(current_section, "http") == 0) {
                if (strcmp(key, "timeout") == 0) {
                    config->http_timeout = atoi(value);
                } else if (strcmp(key, "max_response_size") == 0) {
                    config->max_response_size = atoi(value);
                }
            }
        }
    }
    
    fclose(file);
    
    // Check required settings
    if (strlen(config->vault_role_id) == 0) {
        fprintf(stderr, "Error: vault.role_id is required in config file\n");
        return -1;
    }
    
    if (strlen(config->vault_secret_id) == 0) {
        fprintf(stderr, "Error: vault.secret_id is required in config file\n");
        return -1;
    }
    
    return 0;
}

// Print configuration function
void print_config(const app_config_t *config) {
    if (!config) return;
    
    printf("=== Application Configuration ===\n");
    printf("Vault URL: %s\n", config->vault_url);
    printf("Vault Namespace: %s\n", config->vault_namespace[0] ? config->vault_namespace : "(empty)");
    printf("Entity: %s\n", config->entity);
    printf("Vault Role ID: %s\n", config->vault_role_id);
    printf("Vault Secret ID: %s\n", config->vault_secret_id);
    
    printf("\n--- Secret Engines ---\n");
    printf("KV Engine: %s\n", config->secret_kv.enabled ? "enabled" : "disabled");
    if (config->secret_kv.enabled) {
        printf("  KV Path: %s\n", config->secret_kv.kv_path);
        printf("  Refresh Interval: %d seconds\n", config->secret_kv.refresh_interval);
    }
    
    printf("Database Dynamic: %s\n", config->secret_database_dynamic.enabled ? "enabled" : "disabled");
    if (config->secret_database_dynamic.enabled) {
        printf("  Role ID: %s\n", config->secret_database_dynamic.role_id);
    }
    
    printf("Database Static: %s\n", config->secret_database_static.enabled ? "enabled" : "disabled");
    if (config->secret_database_static.enabled) {
        printf("  Role ID: %s\n", config->secret_database_static.role_id);
    }
    
    printf("\n--- HTTP Settings ---\n");
    printf("HTTP Timeout: %d seconds\n", config->http_timeout);
    printf("Max Response Size: %d bytes\n", config->max_response_size);
    printf("=====================================\n");
}
