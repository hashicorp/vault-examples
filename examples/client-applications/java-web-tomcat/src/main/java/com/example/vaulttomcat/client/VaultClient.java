package com.example.vaulttomcat.client;

import com.example.vaulttomcat.config.VaultConfig;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.hc.client5.http.classic.methods.HttpGet;
import org.apache.hc.client5.http.classic.methods.HttpPost;
import org.apache.hc.client5.http.impl.classic.CloseableHttpClient;
import org.apache.hc.client5.http.impl.classic.CloseableHttpResponse;
import org.apache.hc.client5.http.impl.classic.HttpClients;
import org.apache.hc.core5.http.ContentType;
import org.apache.hc.core5.http.io.entity.StringEntity;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;

/**
 * Vault API Client
 */
public class VaultClient {
  private static final Logger logger = LoggerFactory.getLogger(VaultClient.class);

  private final String vaultUrl;
  private final String vaultNamespace;
  private String vaultToken; // Removed final
  private long tokenExpiry; // Added
  private boolean renewable; // Added
  private final CloseableHttpClient httpClient;
  private final ObjectMapper objectMapper;

  public VaultClient() {
    this.vaultUrl = VaultConfig.getVaultUrl();
    this.vaultNamespace = VaultConfig.getVaultNamespace();
    this.httpClient = HttpClients.createDefault();
    this.objectMapper = new ObjectMapper();

    // Use AppRole authentication
    if ("approle".equals(VaultConfig.getAuthType())) {
      authenticateWithAppRole();
    } else {
      // Fallback to existing token method
      this.vaultToken = VaultConfig.getVaultToken();
    }

    logger.info("VaultClient initialized - URL: {}, Namespace: {}, Auth Type: {}",
        vaultUrl,
        vaultNamespace.isEmpty() ? "(root)" : vaultNamespace,
        VaultConfig.getAuthType());
  }

  /**
   * Call Vault API
   */
  public Map<String, Object> callVaultApi(String path, String method, Map<String, Object> data) throws IOException {
    String url = vaultUrl + "/v1/" + path;

    if ("GET".equals(method)) {
      return callGetApi(url);
    } else if ("POST".equals(method)) {
      return callPostApi(url, data);
    } else {
      throw new IllegalArgumentException("Unsupported HTTP method: " + method);
    }
  }

  private Map<String, Object> callGetApi(String url) throws IOException {
    HttpGet request = new HttpGet(url);
    request.setHeader("X-Vault-Token", vaultToken);
    request.setHeader("Content-Type", "application/json");

    // Add Namespace header
    if (vaultNamespace != null && !vaultNamespace.isEmpty()) {
      request.setHeader("X-Vault-Namespace", vaultNamespace);
    }

    try (CloseableHttpResponse response = httpClient.execute(request)) {
      return parseResponse(response);
    }
  }

  private Map<String, Object> callPostApi(String url, Map<String, Object> data) throws IOException {
    HttpPost request = new HttpPost(url);
    request.setHeader("X-Vault-Token", vaultToken);
    request.setHeader("Content-Type", "application/json");

    // Add Namespace header
    if (vaultNamespace != null && !vaultNamespace.isEmpty()) {
      request.setHeader("X-Vault-Namespace", vaultNamespace);
    }

    if (data != null && !data.isEmpty()) {
      String jsonData = objectMapper.writeValueAsString(data);
      request.setEntity(new StringEntity(jsonData, ContentType.APPLICATION_JSON));
    }

    try (CloseableHttpResponse response = httpClient.execute(request)) {
      return parseResponse(response);
    }
  }

  private Map<String, Object> parseResponse(CloseableHttpResponse response) throws IOException {
    int statusCode = response.getCode();

    if (statusCode >= 200 && statusCode < 300) {
      JsonNode jsonNode = objectMapper.readTree(response.getEntity().getContent());
      return objectMapper.convertValue(jsonNode, Map.class);
    } else {
      logger.error("Vault API call failed with status: {}", statusCode);
      throw new IOException("Vault API call failed with status: " + statusCode);
    }
  }

  /**
   * Get KV v2 secret
   */
  public Map<String, Object> getKvSecret(String path) throws IOException {
    logger.info("Getting KV secret from path: {}", path);
    return callVaultApi(path, "GET", null);
  }

  /**
   * Get Database Dynamic secret
   */
  public Map<String, Object> getDatabaseDynamicSecret(String role) throws IOException {
    String path = VaultConfig.getDatabasePath() + "/creds/" + role;
    logger.info("Getting Database Dynamic secret for role: {}", role);
    return callVaultApi(path, "GET", null);
  }

  /**
   * Get Database Static secret
   */
  public Map<String, Object> getDatabaseStaticSecret(String role) throws IOException {
    String path = VaultConfig.getDatabasePath() + "/static-creds/" + role;
    logger.info("Getting Database Static secret for role: {}", role);
    return callVaultApi(path, "GET", null);
  }

  /**
   * Get token information
   */
  public Map<String, Object> getTokenInfo() throws IOException {
    logger.info("Getting token info");
    return callVaultApi("auth/token/lookup-self", "GET", null);
  }

  /**
   * Renew lease
   */
  public Map<String, Object> renewLease(String leaseId) throws IOException {
    logger.info("Renewing lease: {}", leaseId);
    Map<String, Object> data = new HashMap<>();
    data.put("lease_id", leaseId);
    return callVaultApi("sys/leases/renew", "POST", data);
  }

  /**
   * AppRole authentication
   */
  private void authenticateWithAppRole() {
    try {
      String roleId = VaultConfig.getAppRoleId();
      String secretId = VaultConfig.getAppRoleSecretId();

      Map<String, Object> authData = new HashMap<>();
      authData.put("role_id", roleId);
      authData.put("secret_id", secretId);

      Map<String, Object> response = callAppRoleLogin(authData);

      Map<String, Object> auth = (Map<String, Object>) response.get("auth");
      this.vaultToken = (String) auth.get("client_token");

      // lease_duration (period value)
      Integer leaseDuration = (Integer) auth.get("lease_duration");
      this.tokenExpiry = System.currentTimeMillis() + (leaseDuration * 1000L);
      this.renewable = (Boolean) auth.get("renewable");

      logger.info("AppRole authentication successful - Token TTL: {}s, Renewable: {}",
          leaseDuration, renewable);
    } catch (Exception e) {
      logger.error("AppRole authentication failed: {}", e.getMessage());
      throw new RuntimeException("AppRole authentication failed", e);
    }
  }

  /**
   * Call AppRole login API
   */
  private Map<String, Object> callAppRoleLogin(Map<String, Object> authData) throws IOException {
    String url = vaultUrl + "/v1/auth/approle/login";
    HttpPost request = new HttpPost(url);
    request.setHeader("Content-Type", "application/json");

    // Add Namespace header
    if (vaultNamespace != null && !vaultNamespace.isEmpty()) {
      request.setHeader("X-Vault-Namespace", vaultNamespace);
    }

    String jsonData = objectMapper.writeValueAsString(authData);
    request.setEntity(new StringEntity(jsonData, ContentType.APPLICATION_JSON));

    try (CloseableHttpResponse response = httpClient.execute(request)) {
      return parseResponse(response);
    }
  }

  /**
   * Renew token
   */
  public boolean renewToken() {
    if (!renewable) {
      logger.warn("Token is not renewable");
      return false;
    }

    try {
      String url = vaultUrl + "/v1/auth/token/renew-self";
      HttpPost request = new HttpPost(url);
      request.setHeader("X-Vault-Token", vaultToken);
      request.setHeader("Content-Type", "application/json");

      try (CloseableHttpResponse response = httpClient.execute(request)) {
        Map<String, Object> result = parseResponse(response);
        Map<String, Object> auth = (Map<String, Object>) result.get("auth");

        Integer leaseDuration = (Integer) auth.get("lease_duration");
        this.tokenExpiry = System.currentTimeMillis() + (leaseDuration * 1000L);

        // Token renewal successful (logging handled by TokenRenewalScheduler)
        return true;
      }
    } catch (Exception e) {
      logger.error("Token renewal failed: {}", e.getMessage());
      return false;
    }
  }

  /**
   * Get token expiry time
   */
  public long getTokenExpiry() {
    return tokenExpiry;
  }

  /**
   * Check if token is renewable
   */
  public boolean isRenewable() {
    return renewable;
  }

  /**
   * Check if token renewal is needed
   */
  public boolean shouldRenew() {
    if (!renewable)
      return false;

    long now = System.currentTimeMillis();
    long remainingTtl = tokenExpiry - now;
    long threshold = (long) ((tokenExpiry - (now - remainingTtl)) * VaultConfig.getTokenRenewalThreshold());

    return remainingTtl <= threshold;
  }

  /**
   * Clean up resources
   */
  public void close() {
    try {
      httpClient.close();
    } catch (IOException e) {
      logger.error("Error closing HTTP client", e);
    }
  }
}
