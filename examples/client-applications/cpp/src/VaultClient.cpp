#include "VaultClient.hpp"
#include <iostream>
#include <sstream>
#include <iomanip>

VaultClient::VaultClient(const AppConfig& config) 
    : config_(config), kv_version_(-1) {
    
    // Initialize HTTP client
    http_client_ = std::make_unique<HttpClient>(config.http_timeout);
    
    // Set paths (Entity-based)
    if (config.secret_kv.enabled && !config.secret_kv.kv_path.empty()) {
        kv_path_ = config.entity + "-kv/data/" + config.secret_kv.kv_path;
    }
    
    if (config.secret_database_dynamic.enabled && !config.secret_database_dynamic.role_id.empty()) {
        db_dynamic_path_ = config.entity + "-database/creds/" + config.secret_database_dynamic.role_id;
    }
    
    if (config.secret_database_static.enabled && !config.secret_database_static.role_id.empty()) {
        db_static_path_ = config.entity + "-database/static-creds/" + config.secret_database_static.role_id;
    }
}

bool VaultClient::login(const std::string& role_id, const std::string& secret_id) {
    std::lock_guard<std::mutex> lock(token_mutex_);
    
    // Create JSON request
    nlohmann::json request;
    request["role_id"] = role_id;
    request["secret_id"] = secret_id;
    
    std::string json_string = request.dump();
    
    // Build URL
    std::string url = config_.vault_url + "/v1/auth/approle/login";
    
    // HTTP request
    auto response = http_client_->post_json(url, json_string);
    
    if (!response.is_success()) {
        std::cerr << "Login request failed with status: " << response.status_code << std::endl;
        return false;
    }
    
    try {
        auto json_response = nlohmann::json::parse(response.data);
        
        // Extract token
        if (json_response.contains("auth") && json_response["auth"].contains("client_token")) {
            token_ = json_response["auth"]["client_token"];
            token_issued_ = now();
            
            // Set token expiry time
            if (json_response["auth"].contains("lease_duration")) {
                int ttl_seconds = json_response["auth"]["lease_duration"];
                token_expiry_ = token_issued_ + std::chrono::seconds(ttl_seconds);
                std::cout << "Token TTL from Vault: " << ttl_seconds << " seconds" << std::endl;
            } else {
                // Use default value if TTL info is not available (1 hour)
                token_expiry_ = token_issued_ + std::chrono::seconds(3600);
                std::cout << "Warning: No TTL info from Vault, using default 1 hour" << std::endl;
            }
            
            long remaining = get_duration_seconds(now(), token_expiry_);
            std::cout << "Login successful. Token expires in " << remaining << " seconds" << std::endl;
            return true;
        } else {
            std::cerr << "Failed to extract token from response" << std::endl;
            return false;
        }
    } catch (const nlohmann::json::parse_error& e) {
        std::cerr << "Failed to parse login response: " << e.what() << std::endl;
        return false;
    }
}

bool VaultClient::renew_token() {
    std::lock_guard<std::mutex> lock(token_mutex_);
    
    if (token_.empty()) {
        return false;
    }
    
    // Build URL
    std::string url = config_.vault_url + "/v1/auth/token/renew-self";
    
    // Set headers
    auto headers = get_auth_headers();
    auto ns_headers = get_namespace_headers();
    headers.insert(ns_headers.begin(), ns_headers.end());
    
    // HTTP request
    auto response = http_client_->post(url, "", headers);
    
    if (!response.is_success()) {
        std::cerr << "Token renewal failed with status: " << response.status_code << std::endl;
        std::cout << "Response: " << response.data << std::endl;
        return false;
    }
    
    try {
        auto json_response = nlohmann::json::parse(response.data);
        
        if (json_response.contains("auth") && json_response["auth"].contains("lease_duration")) {
            int lease_seconds = json_response["auth"]["lease_duration"];
            auto now_time = now();
            token_issued_ = now_time;
            token_expiry_ = now_time + std::chrono::seconds(lease_seconds);
            
            long remaining = get_duration_seconds(now_time, token_expiry_);
            std::cout << "Token renewed successfully. New expiry: " << remaining << " seconds" << std::endl;
            return true;
        } else {
            std::cout << "Warning: No lease_duration in renewal response" << std::endl;
            std::cout << "Renewal response: " << response.data << std::endl;
            return false;
        }
    } catch (const nlohmann::json::parse_error& e) {
        std::cout << "Warning: Failed to parse renewal response: " << e.what() << std::endl;
        std::cout << "Renewal response: " << response.data << std::endl;
        return false;
    }
}

bool VaultClient::is_token_valid() const {
    std::lock_guard<std::mutex> lock(token_mutex_);
    
    if (token_.empty()) {
        return false;
    }
    
    auto now_time = now();
    auto total_ttl = get_duration_seconds(token_issued_, token_expiry_);
    auto elapsed = get_duration_seconds(token_issued_, now_time);
    auto renewal_point = total_ttl * 4 / 5;  // Renewal needed at 4/5 point
    
    return (elapsed < renewal_point);
}

void VaultClient::print_token_status() const {
    std::lock_guard<std::mutex> lock(token_mutex_);
    
    if (token_.empty()) {
        std::cout << "❌ No token available!" << std::endl;
        return;
    }
    
    auto now_time = now();
    auto remaining = get_duration_seconds(now_time, token_expiry_);
    
    if (remaining > 0) {
        std::cout << "Token status: " << remaining << " seconds remaining (expires in " 
                  << (remaining / 60) << " minutes)" << std::endl;
        
        // Calculate recommended renewal point (based on 4/5 point)
        auto total_ttl = get_duration_seconds(token_issued_, token_expiry_);
        auto elapsed = get_duration_seconds(token_issued_, now_time);
        auto renewal_point = total_ttl * 4 / 5;  // 4/5 point
        auto urgent_point = total_ttl * 9 / 10;  // 9/10 point
        
        if (elapsed >= urgent_point) {
            std::cout << "⚠️  URGENT: Token should be renewed soon (at " 
                      << (elapsed * 100) / total_ttl << "% of TTL)" << std::endl;
        } else if (elapsed >= renewal_point) {
            std::cout << "🔄 Token renewal recommended (at " 
                      << (elapsed * 100) / total_ttl << "% of TTL)" << std::endl;
        } else {
            std::cout << "✅ Token is healthy (at " 
                      << (elapsed * 100) / total_ttl << "% of TTL)" << std::endl;
        }
    } else {
        std::cout << "❌ Token has expired!" << std::endl;
    }
}

bool VaultClient::get_kv_secret(nlohmann::json& secret_data) {
    std::lock_guard<std::mutex> lock(kv_mutex_);
    
    if (!config_.secret_kv.enabled) {
        return false;
    }
    
    // Refresh if cache is missing or stale
    if (!cached_kv_secret_ || is_kv_secret_stale()) {
        std::cout << "🔄 KV cache is stale, refreshing..." << std::endl;
        if (!refresh_kv_secret()) {
            return false;
        }
    }
    
    // Return cached data
    if (cached_kv_secret_) {
        secret_data = *cached_kv_secret_;
        return true;
    }
    
    return false;
}

bool VaultClient::get_db_dynamic_secret(nlohmann::json& secret_data) {
    std::lock_guard<std::mutex> lock(db_dynamic_mutex_);
    
    if (!config_.secret_database_dynamic.enabled) {
        return false;
    }
    
    // Refresh if cache is missing or stale
    if (!cached_db_dynamic_secret_ || is_db_dynamic_secret_stale()) {
        std::cout << "🔄 Database Dynamic cache is stale, refreshing..." << std::endl;
        if (!refresh_db_dynamic_secret()) {
            return false;
        }
    }
    
    // Return cached data
    if (cached_db_dynamic_secret_) {
        secret_data = *cached_db_dynamic_secret_;
        return true;
    }
    
    return false;
}

bool VaultClient::get_db_static_secret(nlohmann::json& secret_data) {
    std::lock_guard<std::mutex> lock(db_static_mutex_);
    
    if (!config_.secret_database_static.enabled) {
        return false;
    }
    
    // Check if cache is stale
    if (is_db_static_secret_stale()) {
        std::cout << "🔄 Database Static cache is stale, refreshing..." << std::endl;
        if (!refresh_db_static_secret()) {
            return false;
        }
    }
    
    // Return cached secret
    if (cached_db_static_secret_) {
        secret_data = *cached_db_static_secret_;
        return true;
    }
    
    return false;
}

bool VaultClient::refresh_kv_secret() {
    std::lock_guard<std::mutex> lock(kv_mutex_);
    
    if (!config_.secret_kv.enabled || kv_path_.empty()) {
        return false;
    }
    
    std::cout << "🔄 Refreshing KV secret from path: " << kv_path_ << std::endl;
    
    // Get new secret
    nlohmann::json new_secret;
    if (!get_kv_secret_direct(new_secret)) {
        std::cerr << "❌ Failed to refresh KV secret" << std::endl;
        return false;
    }
    
    // Extract version information
    int new_version = -1;
    if (new_secret.contains("data") && 
        new_secret["data"].contains("metadata") && 
        new_secret["data"]["metadata"].contains("version")) {
        new_version = new_secret["data"]["metadata"]["version"];
    }
    
    // Update only if version is different or cache doesn't exist
    if (new_version != kv_version_) {
        // Update cache
        cached_kv_secret_ = std::make_shared<nlohmann::json>(new_secret);
        kv_last_refresh_ = now();
        kv_version_ = new_version;
        
        std::cout << "✅ KV secret updated (version: " << new_version << ")" << std::endl;
    } else {
        std::cout << "✅ KV secret unchanged (version: " << new_version << ")" << std::endl;
        kv_last_refresh_ = now();  // Update last check time
    }
    
    return true;
}

bool VaultClient::refresh_db_dynamic_secret() {
    std::lock_guard<std::mutex> lock(db_dynamic_mutex_);
    
    if (!config_.secret_database_dynamic.enabled || db_dynamic_path_.empty()) {
        return false;
    }
    
    std::cout << "🔄 Refreshing Database Dynamic secret from path: " << db_dynamic_path_ << std::endl;
    
    // Check TTL if existing cache is available
    if (cached_db_dynamic_secret_ && !lease_id_.empty()) {
        std::chrono::system_clock::time_point expire_time;
        int ttl;
        if (check_lease_status(lease_id_, expire_time, ttl)) {
            // Don't refresh if TTL is sufficient
            if (ttl > 10) {  // Don't refresh if more than 10 seconds remaining
                std::cout << "✅ Database Dynamic secret is still valid (TTL: " << ttl << " seconds)" << std::endl;
                db_dynamic_last_refresh_ = now();
                return true;
            } else {
                std::cout << "⚠️ Database Dynamic secret expiring soon (TTL: " << ttl << " seconds), creating new credentials" << std::endl;
            }
        }
    }
    
    // Create new Database Dynamic secret
    nlohmann::json new_secret;
    if (!get_db_dynamic_secret_direct(new_secret)) {
        std::cerr << "❌ Failed to refresh Database Dynamic secret" << std::endl;
        return false;
    }
    
    // Extract lease_id
    if (new_secret.contains("lease_id")) {
        lease_id_ = new_secret["lease_id"];
    }
    
    // Update cache
    cached_db_dynamic_secret_ = std::make_shared<nlohmann::json>(new_secret);
    db_dynamic_last_refresh_ = now();
    
    // Check lease expiry time
    if (!lease_id_.empty()) {
        std::chrono::system_clock::time_point expire_time;
        int ttl = 0;
        if (check_lease_status(lease_id_, expire_time, ttl)) {
            lease_expiry_ = expire_time;
            std::cout << "✅ Database Dynamic secret created successfully (TTL: " << ttl << " seconds)" << std::endl;
        }
    }
    
    return true;
}

bool VaultClient::refresh_db_static_secret() {
    std::lock_guard<std::mutex> lock(db_static_mutex_);
    
    if (!config_.secret_database_static.enabled || db_static_path_.empty()) {
        return false;
    }
    
    std::cout << "🔄 Refreshing Database Static secret from path: " << db_static_path_ << std::endl;
    
    // Get new secret
    nlohmann::json new_secret;
    if (!get_db_static_secret_direct(new_secret)) {
        std::cerr << "❌ Failed to refresh Database Static secret" << std::endl;
        return false;
    }
    
    // Update cache
    cached_db_static_secret_ = std::make_shared<nlohmann::json>(new_secret);
    db_static_last_refresh_ = now();
    
    std::cout << "✅ Database Static secret updated" << std::endl;
    return true;
}

int VaultClient::get_kv_version() const {
    std::lock_guard<std::mutex> lock(kv_mutex_);
    return kv_version_;
}

bool VaultClient::get_db_dynamic_ttl(int& ttl) const {
    std::lock_guard<std::mutex> lock(db_dynamic_mutex_);
    
    if (lease_id_.empty()) {
        return false;
    }
    
    std::chrono::system_clock::time_point expire_time;
    return check_lease_status(lease_id_, expire_time, ttl);
}

bool VaultClient::get_secret(const std::string& path, nlohmann::json& secret_data) {
    // Build URL
    std::string url = config_.vault_url + "/v1/" + path;
    
    // Set headers
    auto headers = get_auth_headers();
    auto ns_headers = get_namespace_headers();
    headers.insert(ns_headers.begin(), ns_headers.end());
    
    // HTTP request
    auto response = http_client_->get(url, headers);
    
    if (!response.is_success()) {
        std::cerr << "Secret request failed with status: " << response.status_code << std::endl;
        return false;
    }
    
    try {
        auto json_response = nlohmann::json::parse(response.data);
        
        // Check for errors
        if (json_response.contains("errors")) {
            std::cout << "🔍 Debug: Vault returned errors:" << std::endl;
            std::cout << "   " << json_response["errors"].dump() << std::endl;
        }
        
        // Extract secret data
        if (json_response.contains("data") && json_response["data"].contains("data")) {
            secret_data = json_response["data"]["data"];
            std::cout << "Secret retrieved successfully" << std::endl;
            return true;
        } else {
            std::cerr << "Failed to extract secret data" << std::endl;
            return false;
        }
    } catch (const nlohmann::json::parse_error& e) {
        std::cerr << "Failed to parse secret response: " << e.what() << std::endl;
        return false;
    }
}

bool VaultClient::get_kv_secret_direct(nlohmann::json& secret_data) {
    // Build URL
    std::string url = config_.vault_url + "/v1/" + kv_path_;
    
    // Set headers
    auto headers = get_auth_headers();
    auto ns_headers = get_namespace_headers();
    headers.insert(ns_headers.begin(), ns_headers.end());
    
    // HTTP request
    auto response = http_client_->get(url, headers);
    
    if (!response.is_success()) {
        std::cerr << "KV secret request failed with status: " << response.status_code << std::endl;
        std::cout << "Response: " << response.data << std::endl;
        return false;
    }
    
    try {
        auto json_response = nlohmann::json::parse(response.data);
        
        // Check for errors
        if (json_response.contains("errors")) {
            std::cout << "🔍 Debug: Vault returned errors:" << std::endl;
            std::cout << "   " << json_response["errors"].dump() << std::endl;
        }
        
        // Return full response (including metadata)
        secret_data = json_response;
        std::cout << "KV secret retrieved successfully" << std::endl;
        return true;
    } catch (const nlohmann::json::parse_error& e) {
        std::cerr << "Failed to parse KV secret response: " << e.what() << std::endl;
        return false;
    }
}

bool VaultClient::get_db_dynamic_secret_direct(nlohmann::json& secret_data) {
    // Build URL
    std::string url = config_.vault_url + "/v1/" + db_dynamic_path_;
    
    // Set headers
    auto headers = get_auth_headers();
    auto ns_headers = get_namespace_headers();
    headers.insert(ns_headers.begin(), ns_headers.end());
    
    // HTTP request
    auto response = http_client_->get(url, headers);
    
    if (!response.is_success()) {
        std::cerr << "Database Dynamic secret request failed with status: " << response.status_code << std::endl;
        std::cout << "Response: " << response.data << std::endl;
        return false;
    }
    
    try {
        auto json_response = nlohmann::json::parse(response.data);
        
        // Check for errors
        if (json_response.contains("errors")) {
            std::cout << "🔍 Debug: Vault returned errors:" << std::endl;
            std::cout << "   " << json_response["errors"].dump() << std::endl;
        }
        
        // Database Dynamic secret returns full response (unlike KV which has data.data structure)
        secret_data = json_response;
        std::cout << "Database Dynamic secret retrieved successfully" << std::endl;
        return true;
    } catch (const nlohmann::json::parse_error& e) {
        std::cerr << "Failed to parse Database Dynamic secret response: " << e.what() << std::endl;
        return false;
    }
}

bool VaultClient::get_db_static_secret_direct(nlohmann::json& secret_data) {
    // Build URL
    std::string url = config_.vault_url + "/v1/" + db_static_path_;
    
    // Set headers
    auto headers = get_auth_headers();
    auto ns_headers = get_namespace_headers();
    headers.insert(ns_headers.begin(), ns_headers.end());
    
    // HTTP request
    auto response = http_client_->get(url, headers);
    
    if (!response.is_success()) {
        std::cerr << "Database Static secret request failed with status: " << response.status_code << std::endl;
        std::cout << "Response: " << response.data << std::endl;
        return false;
    }
    
    try {
        auto json_response = nlohmann::json::parse(response.data);
        
        // Check for errors
        if (json_response.contains("errors")) {
            std::cout << "🔍 Debug: Vault returned errors:" << std::endl;
            std::cout << "   " << json_response["errors"].dump() << std::endl;
        }
        
        std::cout << "Database Static secret retrieved successfully" << std::endl;
        
        // Return only data section
        if (json_response.contains("data")) {
            secret_data = json_response["data"];
        } else {
            secret_data = json_response;
        }
        
        return true;
    } catch (const nlohmann::json::parse_error& e) {
        std::cerr << "Failed to parse Database Static secret response: " << e.what() << std::endl;
        return false;
    }
}

bool VaultClient::is_kv_secret_stale() const {
    // Always need refresh if cache doesn't exist
    if (!cached_kv_secret_) {
        return true;
    }
    
    // Version-based refresh: always check for latest version
    // KV v2 provides version information, so refresh is version-based rather than time-based
    return true;  // Always attempt refresh to check version
}

bool VaultClient::is_db_dynamic_secret_stale() const {
    if (!cached_db_dynamic_secret_) {
        return true;  // Consider stale if cache doesn't exist
    }
    
    // Check lease status
    if (!lease_id_.empty()) {
        std::chrono::system_clock::time_point expire_time;
        int ttl;
        if (check_lease_status(lease_id_, expire_time, ttl)) {
            // Database Dynamic Secret is refreshed only when TTL is almost expired (10 seconds or less)
            int renewal_threshold = 10;  // Refresh when 10 seconds or less
            return (ttl <= renewal_threshold);
        }
    }
    
    // Use default refresh interval if lease status check fails
    auto now_time = now();
    auto elapsed = get_duration_seconds(db_dynamic_last_refresh_, now_time);
    int refresh_interval = config_.secret_kv.refresh_interval; // Use same interval as KV
    
    return (elapsed >= refresh_interval);
}

bool VaultClient::is_db_static_secret_stale() const {
    if (!cached_db_static_secret_) {
        return true; // Consider stale if cache doesn't exist
    }
    
    auto now_time = now();
    auto elapsed = get_duration_seconds(db_static_last_refresh_, now_time);
    
    // Refresh every 5 minutes (Database Static doesn't change frequently)
    return (elapsed >= 300);
}

bool VaultClient::check_lease_status(const std::string& lease_id, 
                                    std::chrono::system_clock::time_point& expire_time, 
                                    int& ttl) const {
    // Build URL
    std::string url = config_.vault_url + "/v1/sys/leases/lookup";
    
    // Set headers
    auto headers = get_auth_headers();
    headers["Content-Type"] = "application/json";
    auto ns_headers = get_namespace_headers();
    headers.insert(ns_headers.begin(), ns_headers.end());
    
    // Set POST data
    nlohmann::json post_data;
    post_data["lease_id"] = lease_id;
    std::string json_string = post_data.dump();
    
    // HTTP request
    auto response = http_client_->post(url, json_string, headers);
    
    if (!response.is_success()) {
        std::cerr << "Lease status check failed with status: " << response.status_code << std::endl;
        return false;
    }
    
    try {
        auto json_response = nlohmann::json::parse(response.data);
        
        // Extract TTL
        if (json_response.contains("data") && json_response["data"].contains("ttl")) {
            ttl = json_response["data"]["ttl"];
            
            // Calculate expire_time
            expire_time = now() + std::chrono::seconds(ttl);
            
            return true;
        }
    } catch (const nlohmann::json::parse_error& e) {
        std::cerr << "Failed to parse lease status response: " << e.what() << std::endl;
    }
    
    return false;
}

std::map<std::string, std::string> VaultClient::get_auth_headers() const {
    std::lock_guard<std::mutex> lock(token_mutex_);
    return {{"X-Vault-Token", token_}};
}

std::map<std::string, std::string> VaultClient::get_namespace_headers() const {
    if (!config_.vault_namespace.empty()) {
        return {{"X-Vault-Namespace", config_.vault_namespace}};
    }
    return {};
}

std::chrono::system_clock::time_point VaultClient::now() {
    return std::chrono::system_clock::now();
}

long VaultClient::get_duration_seconds(const std::chrono::system_clock::time_point& start,
                                      const std::chrono::system_clock::time_point& end) {
    return std::chrono::duration_cast<std::chrono::seconds>(end - start).count();
}
