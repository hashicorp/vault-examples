#include "Config.hpp"
#include <fstream>
#include <iostream>
#include <sstream>
#include <algorithm>
#include <cctype>

int ConfigLoader::load_config(const std::string& config_file, AppConfig& config) {
    // Set default values
    config.vault_url = DEFAULT_VAULT_URL;
    config.vault_namespace = DEFAULT_VAULT_NAMESPACE;
    config.entity = DEFAULT_ENTITY;
    config.vault_role_id.clear();
    config.vault_secret_id.clear();
    
    // Set secret engine default values
    config.secret_kv.enabled = false;
    config.secret_kv.kv_path.clear();
    config.secret_kv.refresh_interval = DEFAULT_KV_REFRESH_INTERVAL;
    
    config.secret_database_dynamic.enabled = false;
    config.secret_database_dynamic.role_id.clear();
    
    config.secret_database_static.enabled = false;
    config.secret_database_static.role_id.clear();
    
    config.http_timeout = DEFAULT_HTTP_TIMEOUT;
    config.max_response_size = DEFAULT_MAX_RESPONSE_SIZE;
    
    // Open INI file
    std::ifstream file(config_file);
    if (!file.is_open()) {
        std::cout << "Warning: Could not open config file '" << config_file << "'. Using defaults." << std::endl;
        return 0; // Continue with defaults
    }
    
    std::string line;
    std::string current_section;
    
    while (std::getline(file, line)) {
        // Remove whitespace and newline characters
        line.erase(std::remove(line.begin(), line.end(), '\r'), line.end());
        line.erase(std::remove(line.begin(), line.end(), '\n'), line.end());
        
        // Skip empty lines or comment lines
        if (line.empty() || line[0] == ';' || line[0] == '#') {
            continue;
        }
        
        // Handle section [section]
        if (line[0] == '[' && line.find(']') != std::string::npos) {
            size_t end_bracket = line.find(']');
            current_section = line.substr(1, end_bracket - 1);
            continue;
        }
        
        // Handle key=value
        size_t equals_pos = line.find('=');
        if (equals_pos != std::string::npos) {
            std::string key = trim(line.substr(0, equals_pos));
            std::string value = trim(line.substr(equals_pos + 1));
            
            // Apply configuration value
            if (current_section == "vault") {
                if (key == "entity") {
                    config.entity = value;
                } else if (key == "url") {
                    config.vault_url = value;
                } else if (key == "namespace") {
                    config.vault_namespace = value;
                } else if (key == "role_id") {
                    config.vault_role_id = value;
                } else if (key == "secret_id") {
                    config.vault_secret_id = value;
                }
            } else if (current_section == "secret-kv") {
                if (key == "enabled") {
                    config.secret_kv.enabled = (to_lower(value) == "true");
                } else if (key == "kv_path") {
                    config.secret_kv.kv_path = value;
                } else if (key == "refresh_interval") {
                    config.secret_kv.refresh_interval = std::stoi(value);
                }
            } else if (current_section == "secret-database-dynamic") {
                if (key == "enabled") {
                    config.secret_database_dynamic.enabled = (to_lower(value) == "true");
                } else if (key == "role_id") {
                    config.secret_database_dynamic.role_id = value;
                }
            } else if (current_section == "secret-database-static") {
                if (key == "enabled") {
                    config.secret_database_static.enabled = (to_lower(value) == "true");
                } else if (key == "role_id") {
                    config.secret_database_static.role_id = value;
                }
            } else if (current_section == "http") {
                if (key == "timeout") {
                    config.http_timeout = std::stoi(value);
                } else if (key == "max_response_size") {
                    config.max_response_size = std::stoi(value);
                }
            }
        }
    }
    
    file.close();
    
    // Validate configuration
    if (!validate_config(config)) {
        return -1;
    }
    
    return 0;
}

void ConfigLoader::print_config(const AppConfig& config) {
    std::cout << "=== Application Configuration ===" << std::endl;
    std::cout << "Vault URL: " << config.vault_url << std::endl;
    std::cout << "Vault Namespace: " << (config.vault_namespace.empty() ? "(empty)" : config.vault_namespace) << std::endl;
    std::cout << "Entity: " << config.entity << std::endl;
    std::cout << "Vault Role ID: " << config.vault_role_id << std::endl;
    std::cout << "Vault Secret ID: " << config.vault_secret_id << std::endl;
    
    std::cout << "\n--- Secret Engines ---" << std::endl;
    std::cout << "KV Engine: " << (config.secret_kv.enabled ? "enabled" : "disabled") << std::endl;
    if (config.secret_kv.enabled) {
        std::cout << "  KV Path: " << config.secret_kv.kv_path << std::endl;
        std::cout << "  Refresh Interval: " << config.secret_kv.refresh_interval << " seconds" << std::endl;
    }
    
    std::cout << "Database Dynamic: " << (config.secret_database_dynamic.enabled ? "enabled" : "disabled") << std::endl;
    if (config.secret_database_dynamic.enabled) {
        std::cout << "  Role ID: " << config.secret_database_dynamic.role_id << std::endl;
    }
    
    std::cout << "Database Static: " << (config.secret_database_static.enabled ? "enabled" : "disabled") << std::endl;
    if (config.secret_database_static.enabled) {
        std::cout << "  Role ID: " << config.secret_database_static.role_id << std::endl;
    }
    
    std::cout << "\n--- HTTP Settings ---" << std::endl;
    std::cout << "HTTP Timeout: " << config.http_timeout << " seconds" << std::endl;
    std::cout << "Max Response Size: " << config.max_response_size << " bytes" << std::endl;
    std::cout << "=====================================" << std::endl;
}

std::string ConfigLoader::trim(const std::string& str) {
    size_t first = str.find_first_not_of(' ');
    if (first == std::string::npos) {
        return "";
    }
    size_t last = str.find_last_not_of(' ');
    return str.substr(first, (last - first + 1));
}

std::string ConfigLoader::to_lower(const std::string& str) {
    std::string result = str;
    std::transform(result.begin(), result.end(), result.begin(), ::tolower);
    return result;
}

bool ConfigLoader::validate_config(const AppConfig& config) {
    // Check required settings
    if (config.vault_role_id.empty()) {
        std::cerr << "Error: vault.role_id is required in config file" << std::endl;
        return false;
    }
    
    if (config.vault_secret_id.empty()) {
        std::cerr << "Error: vault.secret_id is required in config file" << std::endl;
        return false;
    }
    
    // Validate URL format (simple validation)
    if (config.vault_url.empty() || 
        (config.vault_url.find("http://") != 0 && config.vault_url.find("https://") != 0)) {
        std::cerr << "Error: Invalid vault URL format" << std::endl;
        return false;
    }
    
    // Validate HTTP timeout
    if (config.http_timeout <= 0) {
        std::cerr << "Error: HTTP timeout must be positive" << std::endl;
        return false;
    }
    
    // Validate KV configuration
    if (config.secret_kv.enabled && config.secret_kv.kv_path.empty()) {
        std::cerr << "Error: KV path is required when KV engine is enabled" << std::endl;
        return false;
    }
    
    if (config.secret_kv.enabled && config.secret_kv.refresh_interval <= 0) {
        std::cerr << "Error: KV refresh interval must be positive" << std::endl;
        return false;
    }
    
    // Validate Database Dynamic configuration
    if (config.secret_database_dynamic.enabled && config.secret_database_dynamic.role_id.empty()) {
        std::cerr << "Error: Database Dynamic role_id is required when enabled" << std::endl;
        return false;
    }
    
    // Validate Database Static configuration
    if (config.secret_database_static.enabled && config.secret_database_static.role_id.empty()) {
        std::cerr << "Error: Database Static role_id is required when enabled" << std::endl;
        return false;
    }
    
    return true;
}
