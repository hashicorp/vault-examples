#ifndef CONFIG_HPP
#define CONFIG_HPP

#include <string>
#include <optional>

/**
 * Application configuration structure
 * Implements the same configuration as the C version in C++ style
 */
struct AppConfig {
    // Vault basic settings
    std::string vault_url;
    std::string vault_namespace;
    std::string vault_role_id;
    std::string vault_secret_id;
    std::string entity;
    
    // Secret engine settings
    struct {
        bool enabled = false;
        std::string kv_path;
        int refresh_interval = 300;  // KV refresh interval (seconds)
    } secret_kv;
    
    struct {
        bool enabled = false;
        std::string role_id;
    } secret_database_dynamic;
    
    struct {
        bool enabled = false;
        std::string role_id;
    } secret_database_static;
    
    // HTTP settings
    int http_timeout = 30;
    int max_response_size = 4096;
};

/**
 * Configuration loader class
 * Responsible for INI file parsing and configuration validation
 */
class ConfigLoader {
public:
    // Default values
    static constexpr const char* DEFAULT_VAULT_URL = "http://127.0.0.1:8200";
    static constexpr const char* DEFAULT_VAULT_NAMESPACE = "";
    static constexpr const char* DEFAULT_ENTITY = "my-vault-app";
    static constexpr int DEFAULT_HTTP_TIMEOUT = 30;
    static constexpr int DEFAULT_MAX_RESPONSE_SIZE = 4096;
    static constexpr int DEFAULT_KV_REFRESH_INTERVAL = 300;  // 5 minutes default

    /**
     * Load configuration file
     * @param config_file Configuration file path
     * @param config Configuration object to load
     * @return 0 on success, -1 on failure
     */
    static int load_config(const std::string& config_file, AppConfig& config);
    
    /**
     * Print configuration information
     * @param config Configuration object to print
     */
    static void print_config(const AppConfig& config);

private:
    /**
     * Trim string (remove leading and trailing whitespace)
     * @param str String to trim
     * @return Trimmed string
     */
    static std::string trim(const std::string& str);
    
    /**
     * Convert string to lowercase
     * @param str String to convert
     * @return Lowercase string
     */
    static std::string to_lower(const std::string& str);
    
    /**
     * Validate configuration
     * @param config Configuration object to validate
     * @return true if configuration is valid, false otherwise
     */
    static bool validate_config(const AppConfig& config);
};

#endif // CONFIG_HPP
