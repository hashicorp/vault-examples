#include "HttpClient.hpp"
#include <iostream>
#include <sstream>
#include <algorithm>

HttpClient::HttpClient(int timeout) 
    : curl_(nullptr), timeout_(timeout), ssl_verify_(true) {
    if (!initialize_curl()) {
        throw std::runtime_error("Failed to initialize libcurl");
    }
}

HttpClient::~HttpClient() {
    if (curl_) {
        curl_easy_cleanup(curl_);
    }
}

HttpClient::HttpClient(HttpClient&& other) noexcept
    : curl_(other.curl_), timeout_(other.timeout_), ssl_verify_(other.ssl_verify_) {
    other.curl_ = nullptr;
}

HttpClient& HttpClient::operator=(HttpClient&& other) noexcept {
    if (this != &other) {
        if (curl_) {
            curl_easy_cleanup(curl_);
        }
        curl_ = other.curl_;
        timeout_ = other.timeout_;
        ssl_verify_ = other.ssl_verify_;
        other.curl_ = nullptr;
    }
    return *this;
}

bool HttpClient::initialize_curl() {
    curl_ = curl_easy_init();
    if (!curl_) {
        return false;
    }
    
    // Set default options
    curl_easy_setopt(curl_, CURLOPT_TIMEOUT, timeout_);
    curl_easy_setopt(curl_, CURLOPT_FOLLOWLOCATION, 1L);
    curl_easy_setopt(curl_, CURLOPT_SSL_VERIFYPEER, ssl_verify_ ? 1L : 0L);
    curl_easy_setopt(curl_, CURLOPT_SSL_VERIFYHOST, ssl_verify_ ? 2L : 0L);
    curl_easy_setopt(curl_, CURLOPT_WRITEFUNCTION, write_callback);
    curl_easy_setopt(curl_, CURLOPT_HEADERFUNCTION, header_callback);
    
    return true;
}

HttpResponse HttpClient::get(const std::string& url, 
                           const std::map<std::string, std::string>& headers) const {
    HttpResponse response;
    
    // Set URL
    curl_easy_setopt(curl_, CURLOPT_URL, url.c_str());
    curl_easy_setopt(curl_, CURLOPT_HTTPGET, 1L);
    curl_easy_setopt(curl_, CURLOPT_WRITEDATA, &response);
    curl_easy_setopt(curl_, CURLOPT_HEADERDATA, &response);
    
    // Set headers
    struct curl_slist* header_list = setup_headers(headers);
    if (header_list) {
        curl_easy_setopt(curl_, CURLOPT_HTTPHEADER, header_list);
    }
    
    // Execute request
    CURLcode res = curl_easy_perform(curl_);
    
    // Cleanup header list
    if (header_list) {
        curl_slist_free_all(header_list);
    }
    
    if (res != CURLE_OK) {
        std::cerr << "HTTP GET request failed: " << curl_easy_strerror(res) << std::endl;
        response.status_code = -1;
        return response;
    }
    
    // Get HTTP status code
    curl_easy_getinfo(curl_, CURLINFO_RESPONSE_CODE, &response.status_code);
    
    return response;
}

HttpResponse HttpClient::post(const std::string& url, 
                            const std::string& data,
                            const std::map<std::string, std::string>& headers) const {
    HttpResponse response;
    
    // Set URL
    curl_easy_setopt(curl_, CURLOPT_URL, url.c_str());
    curl_easy_setopt(curl_, CURLOPT_POSTFIELDS, data.c_str());
    curl_easy_setopt(curl_, CURLOPT_POSTFIELDSIZE, data.length());
    curl_easy_setopt(curl_, CURLOPT_WRITEDATA, &response);
    curl_easy_setopt(curl_, CURLOPT_HEADERDATA, &response);
    
    // Set headers
    struct curl_slist* header_list = setup_headers(headers);
    if (header_list) {
        curl_easy_setopt(curl_, CURLOPT_HTTPHEADER, header_list);
    }
    
    // Execute request
    CURLcode res = curl_easy_perform(curl_);
    
    // Cleanup header list
    if (header_list) {
        curl_slist_free_all(header_list);
    }
    
    if (res != CURLE_OK) {
        std::cerr << "HTTP POST request failed: " << curl_easy_strerror(res) << std::endl;
        response.status_code = -1;
        return response;
    }
    
    // Get HTTP status code
    curl_easy_getinfo(curl_, CURLINFO_RESPONSE_CODE, &response.status_code);
    
    return response;
}

HttpResponse HttpClient::post_json(const std::string& url, 
                                 const std::string& json_data,
                                 const std::map<std::string, std::string>& headers) const {
    // Add JSON header
    auto json_headers = headers;
    json_headers["Content-Type"] = "application/json";
    
    return post(url, json_data, json_headers);
}

void HttpClient::set_timeout(int timeout) {
    timeout_ = timeout;
    curl_easy_setopt(curl_, CURLOPT_TIMEOUT, timeout_);
}

void HttpClient::set_ssl_verify(bool verify) {
    ssl_verify_ = verify;
    curl_easy_setopt(curl_, CURLOPT_SSL_VERIFYPEER, verify ? 1L : 0L);
    curl_easy_setopt(curl_, CURLOPT_SSL_VERIFYHOST, verify ? 2L : 0L);
}

struct curl_slist* HttpClient::setup_headers(const std::map<std::string, std::string>& headers) const {
    struct curl_slist* header_list = nullptr;
    
    for (const auto& header : headers) {
        std::string header_string = header.first + ": " + header.second;
        header_list = curl_slist_append(header_list, header_string.c_str());
    }
    
    return header_list;
}

size_t HttpClient::write_callback(void* contents, size_t size, size_t nmemb, void* userp) {
    size_t total_size = size * nmemb;
    HttpResponse* response = static_cast<HttpResponse*>(userp);
    
    response->data.append(static_cast<char*>(contents), total_size);
    
    return total_size;
}

size_t HttpClient::header_callback(void* contents, size_t size, size_t nmemb, void* userp) {
    size_t total_size = size * nmemb;
    HttpResponse* response = static_cast<HttpResponse*>(userp);
    
    std::string header_line(static_cast<char*>(contents), total_size);
    
    // Parse header (Key: Value format)
    size_t colon_pos = header_line.find(':');
    if (colon_pos != std::string::npos) {
        std::string key = header_line.substr(0, colon_pos);
        std::string value = header_line.substr(colon_pos + 1);
        
        // Remove leading and trailing whitespace
        key.erase(0, key.find_first_not_of(" \t\r\n"));
        key.erase(key.find_last_not_of(" \t\r\n") + 1);
        value.erase(0, value.find_first_not_of(" \t\r\n"));
        value.erase(value.find_last_not_of(" \t\r\n") + 1);
        
        // Convert to lowercase (HTTP headers are case-insensitive)
        std::transform(key.begin(), key.end(), key.begin(), ::tolower);
        
        response->headers[key] = value;
    }
    
    return total_size;
}
