#include "Config.hpp"
#include "VaultClient.hpp"
#include <iostream>
#include <thread>
#include <atomic>
#include <chrono>
#include <csignal>
#include <memory>

// Global variables
std::unique_ptr<VaultClient> vault_client;
AppConfig app_config;
std::atomic<bool> should_exit{false};

// Signal handler
void signal_handler(int sig) {
    std::cout << "\nReceived signal " << sig << ". Shutting down..." << std::endl;
    should_exit = true;
    
    // Additional signal setup for forced termination
    if (sig == SIGINT) {
        std::signal(SIGINT, SIG_DFL); // Next Ctrl+C will force terminate
    }
}

// KV secret renewal thread
void kv_refresh_thread() {
    while (!should_exit) {
        // Wait for configured interval
        int refresh_interval = app_config.secret_kv.refresh_interval;
        for (int i = 0; i < refresh_interval && !should_exit; i++) {
            std::this_thread::sleep_for(std::chrono::seconds(1));
        }
        
        if (should_exit) break;
        
        // Renew KV secret
        if (app_config.secret_kv.enabled) {
            std::cout << "\n=== KV Secret Refresh ===" << std::endl;
            vault_client->refresh_kv_secret();
        }
    }
    
    std::cout << "KV refresh thread terminated" << std::endl;
}

// Database Dynamic secret renewal thread
void db_dynamic_refresh_thread() {
    while (!should_exit) {
        // Wait for configured interval
        int refresh_interval = app_config.secret_kv.refresh_interval;
        for (int i = 0; i < refresh_interval && !should_exit; i++) {
            std::this_thread::sleep_for(std::chrono::seconds(1));
        }
        
        if (should_exit) break;
        
        // Renew Database Dynamic secret
        if (app_config.secret_database_dynamic.enabled) {
            std::cout << "\n=== Database Dynamic Secret Refresh ===" << std::endl;
            vault_client->refresh_db_dynamic_secret();
        }
    }
    
    std::cout << "Database Dynamic refresh thread terminated" << std::endl;
}

// Database Static secret renewal thread
void db_static_refresh_thread() {
    while (!should_exit) {
        // Wait for configured interval (Database Static changes less frequently, so longer interval)
        int refresh_interval = app_config.secret_kv.refresh_interval * 2; // 2x interval
        for (int i = 0; i < refresh_interval && !should_exit; i++) {
            std::this_thread::sleep_for(std::chrono::seconds(1));
        }
        
        if (should_exit) break;
        
        // Renew Database Static secret
        if (app_config.secret_database_static.enabled) {
            std::cout << "\n=== Database Static Secret Refresh ===" << std::endl;
            vault_client->refresh_db_static_secret();
        }
    }
    
    std::cout << "Database Static refresh thread terminated" << std::endl;
}

// Token renewal thread (safe renewal logic)
void token_renewal_thread() {
    while (!should_exit) {
        // Check token status every 10 seconds (handle short TTL)
        for (int i = 0; i < 10 && !should_exit; i++) {
            std::this_thread::sleep_for(std::chrono::seconds(1));
        }
        
        if (should_exit) break;
        
        // Print token status
        std::cout << "\n=== Token Status Check ===" << std::endl;
        vault_client->print_token_status();
        
        // Check if renewal is needed (renew at 4/5 point)
        if (!vault_client->is_token_valid()) {
            std::cout << "🔄 Token renewal triggered" << std::endl;
            
            if (!vault_client->renew_token()) {
                std::cout << "❌ Token renewal failed. Attempting re-login..." << std::endl;
                if (!vault_client->login(app_config.vault_role_id, app_config.vault_secret_id)) {
                    std::cerr << "❌ Re-login failed. Exiting..." << std::endl;
                    should_exit = true;
                    break;
                } else {
                    std::cout << "✅ Re-login successful" << std::endl;
                    vault_client->print_token_status();
                }
            } else {
                std::cout << "✅ Token renewed successfully" << std::endl;
                vault_client->print_token_status();
            }
        } else {
            std::cout << "✅ Token is still healthy, no renewal needed" << std::endl;
        }
    }
    
    std::cout << "Token renewal thread terminated" << std::endl;
}

int main(int argc, char* argv[]) {
    // Setup signal handlers
    std::signal(SIGINT, signal_handler);
    std::signal(SIGTERM, signal_handler);
    
    std::cout << "=== Vault C++ Client Application ===" << std::endl;
    
    // Determine configuration file path
    std::string config_file = "config.ini";
    if (argc > 1) {
        config_file = argv[1];
    }
    
    // Load configuration file
    std::cout << "Loading configuration from: " << config_file << std::endl;
    if (ConfigLoader::load_config(config_file, app_config) != 0) {
        std::cerr << "Failed to load configuration" << std::endl;
        return 1;
    }
    
    // Print configuration
    ConfigLoader::print_config(app_config);
    
    // Initialize Vault client
    try {
        vault_client = std::make_unique<VaultClient>(app_config);
    } catch (const std::exception& e) {
        std::cerr << "Failed to initialize Vault client: " << e.what() << std::endl;
        return 1;
    }
    
    // AppRole login
    std::cout << "Logging in to Vault..." << std::endl;
    if (!vault_client->login(app_config.vault_role_id, app_config.vault_secret_id)) {
        std::cerr << "Login failed" << std::endl;
        return 1;
    }
    
    // Print token status
    vault_client->print_token_status();
    
    // Start token renewal thread
    std::thread renewal_thread(token_renewal_thread);
    
    // Start KV renewal thread (if KV engine is enabled)
    std::thread kv_refresh_thread_handle;
    if (app_config.secret_kv.enabled) {
        kv_refresh_thread_handle = std::thread(kv_refresh_thread);
        std::cout << "✅ KV refresh thread started (interval: " << app_config.secret_kv.refresh_interval << " seconds)" << std::endl;
    }
    
    // Start Database Dynamic renewal thread (if Database Dynamic engine is enabled)
    std::thread db_dynamic_refresh_thread_handle;
    if (app_config.secret_database_dynamic.enabled) {
        db_dynamic_refresh_thread_handle = std::thread(db_dynamic_refresh_thread);
        std::cout << "✅ Database Dynamic refresh thread started (interval: " << app_config.secret_kv.refresh_interval << " seconds)" << std::endl;
    }
    
    // Start Database Static renewal thread (if Database Static engine is enabled)
    std::thread db_static_refresh_thread_handle;
    if (app_config.secret_database_static.enabled) {
        db_static_refresh_thread_handle = std::thread(db_static_refresh_thread);
        std::cout << "✅ Database Static refresh thread started (interval: " << (app_config.secret_kv.refresh_interval * 2) << " seconds)" << std::endl;
    }
    
    // Main loop
    while (!should_exit) {
        std::cout << "\n=== Fetching Secret ===" << std::endl;
        
        // Get KV secret (check cache)
        if (app_config.secret_kv.enabled) {
            nlohmann::json kv_secret;
            if (vault_client->get_kv_secret(kv_secret)) {
                // Extract and print only data.data part
                if (kv_secret.contains("data") && kv_secret["data"].contains("data")) {
                    std::cout << "📦 KV Secret Data (version: " << vault_client->get_kv_version() << "):" << std::endl;
                    std::cout << kv_secret["data"]["data"].dump() << std::endl;
                }
            } else {
                std::cerr << "Failed to retrieve KV secret" << std::endl;
            }
        }
        
        // Get Database Dynamic secret (check cache)
        if (app_config.secret_database_dynamic.enabled) {
            nlohmann::json db_dynamic_secret;
            if (vault_client->get_db_dynamic_secret(db_dynamic_secret)) {
                // Get TTL information
                int ttl = 0;
                if (vault_client->get_db_dynamic_ttl(ttl)) {
                    std::cout << "🗄️ Database Dynamic Secret (TTL: " << ttl << " seconds):" << std::endl;
                } else {
                    std::cout << "🗄️ Database Dynamic Secret:" << std::endl;
                }
                
                // Extract only username and password from data section
                if (db_dynamic_secret.contains("data")) {
                    auto data = db_dynamic_secret["data"];
                    if (data.contains("username") && data.contains("password")) {
                        std::cout << "  username: " << data["username"] << std::endl;
                        std::cout << "  password: " << data["password"] << std::endl;
                    }
                }
            } else {
                std::cerr << "Failed to retrieve Database Dynamic secret" << std::endl;
            }
        }
        
        // Get Database Static secret (check cache)
        if (app_config.secret_database_static.enabled) {
            nlohmann::json db_static_secret;
            if (vault_client->get_db_static_secret(db_static_secret)) {
                // Extract TTL information
                int ttl = 0;
                if (db_static_secret.contains("ttl")) {
                    ttl = db_static_secret["ttl"];
                }
                
                if (ttl > 0) {
                    std::cout << "🔒 Database Static Secret (TTL: " << ttl << " seconds):" << std::endl;
                } else {
                    std::cout << "🔒 Database Static Secret:" << std::endl;
                }
                
                // Extract username and password
                if (db_static_secret.contains("username") && db_static_secret.contains("password")) {
                    std::cout << "  username: " << db_static_secret["username"] << std::endl;
                    std::cout << "  password: " << db_static_secret["password"] << std::endl;
                }
            } else {
                std::cerr << "Failed to retrieve Database Static secret" << std::endl;
            }
        }
        
        // Print token status briefly
        std::cout << "\n--- Token Status ---" << std::endl;
        vault_client->print_token_status();
        
        // Wait 10 seconds
        for (int i = 0; i < 10 && !should_exit; i++) {
            std::this_thread::sleep_for(std::chrono::seconds(1));
        }
    }
    
    // Cleanup
    std::cout << "Cleaning up..." << std::endl;
    
    // Wait for threads to terminate
    if (renewal_thread.joinable()) {
        renewal_thread.join();
    }
    
    if (kv_refresh_thread_handle.joinable()) {
        kv_refresh_thread_handle.join();
    }
    
    if (db_dynamic_refresh_thread_handle.joinable()) {
        db_dynamic_refresh_thread_handle.join();
    }
    
    if (db_static_refresh_thread_handle.joinable()) {
        db_static_refresh_thread_handle.join();
    }
    
    vault_client.reset();
    
    std::cout << "Application terminated" << std::endl;
    return 0;
}
