#ifndef HTTP_CLIENT_HPP
#define HTTP_CLIENT_HPP

#include <string>
#include <vector>
#include <map>
#include <memory>
#include <curl/curl.h>

/**
 * HTTP response structure
 */
struct HttpResponse {
    std::string data;
    long status_code = 0;
    std::map<std::string, std::string> headers;
    
    // Check if response is successful
    bool is_success() const {
        return status_code >= 200 && status_code < 300;
    }
    
    // Check if response data is empty
    bool is_empty() const {
        return data.empty();
    }
};

/**
 * HTTP client class
 * C++ wrapper for libcurl with RAII pattern
 */
class HttpClient {
public:
    /**
     * Constructor
     * @param timeout HTTP request timeout (seconds)
     */
    explicit HttpClient(int timeout = 30);
    
    /**
     * Destructor
     * Automatically cleans up libcurl resources
     */
    ~HttpClient();
    
    // Disable copy constructor and assignment operator
    HttpClient(const HttpClient&) = delete;
    HttpClient& operator=(const HttpClient&) = delete;
    
    // Move constructor and assignment operator
    HttpClient(HttpClient&& other) noexcept;
    HttpClient& operator=(HttpClient&& other) noexcept;
    
    /**
     * HTTP GET request
     * @param url URL to request
     * @param headers Additional headers (optional)
     * @return HTTP response
     */
    HttpResponse get(const std::string& url, 
                    const std::map<std::string, std::string>& headers = {}) const;
    
    /**
     * HTTP POST request
     * @param url URL to request
     * @param data POST data
     * @param headers Additional headers (optional)
     * @return HTTP response
     */
    HttpResponse post(const std::string& url, 
                     const std::string& data,
                     const std::map<std::string, std::string>& headers = {}) const;
    
    /**
     * HTTP POST request (JSON data)
     * @param url URL to request
     * @param json_data JSON string
     * @param headers Additional headers (optional)
     * @return HTTP response
     */
    HttpResponse post_json(const std::string& url, 
                          const std::string& json_data,
                          const std::map<std::string, std::string>& headers = {}) const;
    
    /**
     * Set timeout
     * @param timeout New timeout value (seconds)
     */
    void set_timeout(int timeout);
    
    /**
     * Set SSL verification
     * @param verify true to verify SSL, false to skip verification
     */
    void set_ssl_verify(bool verify);

private:
    CURL* curl_;
    int timeout_;
    bool ssl_verify_;
    
    /**
     * Initialize libcurl
     * @return true on success, false on failure
     */
    bool initialize_curl();
    
    /**
     * Setup HTTP headers
     * @param headers Header map to set
     * @return Configured curl_slist pointer (memory must be freed)
     */
    struct curl_slist* setup_headers(const std::map<std::string, std::string>& headers) const;
    
    /**
     * libcurl callback function (static)
     * @param contents Received data
     * @param size Data size
     * @param nmemb Number of data items
     * @param userp User data (HttpResponse pointer)
     * @return Number of bytes processed
     */
    static size_t write_callback(void* contents, size_t size, size_t nmemb, void* userp);
    
    /**
     * Header callback function (static)
     * @param contents Received header
     * @param size Header size
     * @param nmemb Number of header items
     * @param userp User data (HttpResponse pointer)
     * @return Number of bytes processed
     */
    static size_t header_callback(void* contents, size_t size, size_t nmemb, void* userp);
};

#endif // HTTP_CLIENT_HPP
