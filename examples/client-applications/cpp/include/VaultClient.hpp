#ifndef VAULT_CLIENT_HPP
#define VAULT_CLIENT_HPP

#include "Config.hpp"
#include "HttpClient.hpp"
#include "json.hpp"
#include <string>
#include <memory>
#include <mutex>
#include <atomic>
#include <chrono>
#include <optional>

/**
 * Vault Client Class
 * Provides AppRole authentication, token management, and secret retrieval functionality
 */
class VaultClient {
public:
    /**
     * Constructor
     * @param config Application configuration
     */
    explicit VaultClient(const AppConfig& config);
    
    /**
     * Destructor
     */
    ~VaultClient() = default;
    
    // Disable copy constructor and assignment operator
    VaultClient(const VaultClient&) = delete;
    VaultClient& operator=(const VaultClient&) = delete;
    
    /**
     * AppRole login
     * @param role_id AppRole Role ID
     * @param secret_id AppRole Secret ID
     * @return true on success, false on failure
     */
    bool login(const std::string& role_id, const std::string& secret_id);
    
    /**
     * Renew token
     * @return true on success, false on failure
     */
    bool renew_token();
    
    /**
     * Check token validity
     * @return true if token is valid, false otherwise
     */
    bool is_token_valid() const;
    
    /**
     * Print token status
     */
    void print_token_status() const;
    
    /**
     * Get KV secret (with cache check)
     * @param secret_data Secret data to return
     * @return true on success, false on failure
     */
    bool get_kv_secret(nlohmann::json& secret_data);
    
    /**
     * Get Database Dynamic secret (with cache check)
     * @param secret_data Secret data to return
     * @return true on success, false on failure
     */
    bool get_db_dynamic_secret(nlohmann::json& secret_data);
    
    /**
     * Get Database Static secret (with cache check)
     * @param secret_data Secret data to return
     * @return true on success, false on failure
     */
    bool get_db_static_secret(nlohmann::json& secret_data);
    
    /**
     * Refresh KV secret
     * @return true on success, false on failure
     */
    bool refresh_kv_secret();
    
    /**
     * Refresh Database Dynamic secret
     * @return true on success, false on failure
     */
    bool refresh_db_dynamic_secret();
    
    /**
     * Refresh Database Static secret
     * @return true on success, false on failure
     */
    bool refresh_db_static_secret();
    
    /**
     * Get KV version information
     * @return KV secret version
     */
    int get_kv_version() const;
    
    /**
     * Check Database Dynamic TTL
     * @param ttl TTL value (seconds)
     * @return true on success, false on failure
     */
    bool get_db_dynamic_ttl(int& ttl) const;

private:
    const AppConfig& config_;
    std::unique_ptr<HttpClient> http_client_;
    
    // Token management
    std::string token_;
    std::chrono::system_clock::time_point token_issued_;
    std::chrono::system_clock::time_point token_expiry_;
    mutable std::mutex token_mutex_;
    
    // KV secret cache
    std::shared_ptr<nlohmann::json> cached_kv_secret_;
    std::chrono::system_clock::time_point kv_last_refresh_;
    std::string kv_path_;
    int kv_version_;
    mutable std::mutex kv_mutex_;
    
    // Database Dynamic secret cache
    std::shared_ptr<nlohmann::json> cached_db_dynamic_secret_;
    std::chrono::system_clock::time_point db_dynamic_last_refresh_;
    std::string db_dynamic_path_;
    std::string lease_id_;
    std::chrono::system_clock::time_point lease_expiry_;
    mutable std::mutex db_dynamic_mutex_;
    
    // Database Static secret cache
    std::shared_ptr<nlohmann::json> cached_db_static_secret_;
    std::chrono::system_clock::time_point db_static_last_refresh_;
    std::string db_static_path_;
    mutable std::mutex db_static_mutex_;
    
    /**
     * Get secret (common)
     * @param path Secret path
     * @param secret_data Secret data to return
     * @return true on success, false on failure
     */
    bool get_secret(const std::string& path, nlohmann::json& secret_data);
    
    /**
     * Get KV secret directly (ignore cache)
     * @param secret_data Secret data to return
     * @return true on success, false on failure
     */
    bool get_kv_secret_direct(nlohmann::json& secret_data);
    
    /**
     * Get Database Dynamic secret directly (ignore cache)
     * @param secret_data Secret data to return
     * @return true on success, false on failure
     */
    bool get_db_dynamic_secret_direct(nlohmann::json& secret_data);
    
    /**
     * Get Database Static secret directly (ignore cache)
     * @param secret_data Secret data to return
     * @return true on success, false on failure
     */
    bool get_db_static_secret_direct(nlohmann::json& secret_data);
    
    /**
     * Check if KV secret is stale
     * @return true if secret is stale, false otherwise
     */
    bool is_kv_secret_stale() const;
    
    /**
     * Check if Database Dynamic secret is stale
     * @return true if secret is stale, false otherwise
     */
    bool is_db_dynamic_secret_stale() const;
    
    /**
     * Check if Database Static secret is stale
     * @return true if secret is stale, false otherwise
     */
    bool is_db_static_secret_stale() const;
    
    /**
     * Check lease status
     * @param lease_id Lease ID to check
     * @param expire_time Expiration time
     * @param ttl TTL value (seconds)
     * @return true on success, false on failure
     */
    bool check_lease_status(const std::string& lease_id, 
                           std::chrono::system_clock::time_point& expire_time, 
                           int& ttl) const;
    
    /**
     * Generate Authorization header
     * @return Authorization header map
     */
    std::map<std::string, std::string> get_auth_headers() const;
    
    /**
     * Generate Namespace header (if needed)
     * @return Namespace header map
     */
    std::map<std::string, std::string> get_namespace_headers() const;
    
    /**
     * Get current time
     * @return Current time
     */
    static std::chrono::system_clock::time_point now();
    
    /**
     * Calculate time difference (seconds)
     * @param start Start time
     * @param end End time
     * @return Time difference (seconds)
     */
    static long get_duration_seconds(const std::chrono::system_clock::time_point& start,
                                    const std::chrono::system_clock::time_point& end);
};

#endif // VAULT_CLIENT_HPP
