package com.example.vaulttomcat.service;

import com.example.vaulttomcat.client.VaultClient;
import com.example.vaulttomcat.config.VaultConfig;
import com.example.vaulttomcat.model.SecretInfo;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.HashMap;
import java.util.Map;

/**
 * Vault secret retrieval and management service
 */
public class VaultSecretService {
  private static final Logger logger = LoggerFactory.getLogger(VaultSecretService.class);

  private final VaultClient vaultClient;

  // Secret caching variables
  private SecretInfo cachedKvSecret;
  private SecretInfo cachedDbStaticSecret;
  private long lastKvRefresh = 0;
  private long lastDbStaticRefresh = 0;

  // Cache validity time (milliseconds) - 1 hour
  private static final long CACHE_VALIDITY_MS = 60 * 60 * 1000;

  public VaultSecretService() {
    this.vaultClient = new VaultClient();
  }

  /**
   * Get KV secret (with caching)
   */
  public SecretInfo getKvSecret() {
    long currentTime = System.currentTimeMillis();

    // Return cached value if cache is valid
    if (cachedKvSecret != null && (currentTime - lastKvRefresh) < CACHE_VALIDITY_MS) {
      logger.info("📦 KV Secret returned from cache (last refresh: {}s ago)",
          (currentTime - lastKvRefresh) / 1000);
      return cachedKvSecret;
    }

    try {
      logger.info("=== KV Secret Refresh (retrieved from Vault) ===");

      String kvPath = VaultConfig.getDatabaseKvPath();
      Map<String, Object> response = vaultClient.getKvSecret(kvPath);

      if (response != null && response.containsKey("data")) {
        @SuppressWarnings("unchecked")
        Map<String, Object> data = (Map<String, Object>) response.get("data");

        // In KV v2, actual data is inside the 'data' key
        @SuppressWarnings("unchecked")
        Map<String, Object> actualData = (Map<String, Object>) data.get("data");

        // Extract version information from metadata
        @SuppressWarnings("unchecked")
        Map<String, Object> metadata = (Map<String, Object>) data.get("metadata");
        String version = metadata != null ? metadata.get("version").toString() : "1";

        SecretInfo secretInfo = new SecretInfo("KV", kvPath, actualData);
        secretInfo.setVersion(version);

        // Update cache
        cachedKvSecret = secretInfo;
        lastKvRefresh = currentTime;

        logger.info("✅ KV secret fetch successful (version: {}) - cache updated", version);
        logger.info("📦 KV Secret Data (version: {}): {}", version, actualData);

        return secretInfo;
      } else {
        throw new RuntimeException("KV secret not found");
      }

    } catch (Exception e) {
      logger.error("❌ KV secret fetch failed: {}", e.getMessage());
      return createErrorSecretInfo("KV", VaultConfig.getDatabaseKvPath(), e.getMessage());
    }
  }

  /**
   * Get Database Dynamic secret
   */
  public SecretInfo getDatabaseDynamicSecret() {
    try {
      logger.info("=== Database Dynamic Secret Refresh ===");

      String role = VaultConfig.getDatabaseDynamicRole();
      Map<String, Object> response = vaultClient.getDatabaseDynamicSecret(role);

      if (response != null && response.containsKey("data")) {
        @SuppressWarnings("unchecked")
        Map<String, Object> data = (Map<String, Object>) response.get("data");

        String path = VaultConfig.getDatabasePath() + "/creds/" + role;
        SecretInfo secretInfo = new SecretInfo("Database Dynamic", path, data);

        // Set lease information
        if (response.containsKey("lease_id")) {
          secretInfo.setLeaseId(response.get("lease_id").toString());
        }
        if (response.containsKey("lease_duration")) {
          secretInfo.setTtl(Long.valueOf(response.get("lease_duration").toString()));
        }
        if (response.containsKey("renewable")) {
          secretInfo.setRenewable(Boolean.valueOf(response.get("renewable").toString()));
        }

        logger.info("✅ Database Dynamic secret fetch successful (TTL: {}s)", secretInfo.getTtl());
        logger.info("🗄️ Database Dynamic Secret (TTL: {}s): username: {}, password: {}",
            secretInfo.getTtl(), data.get("username"), "***");

        return secretInfo;
      } else {
        throw new RuntimeException("Database Dynamic secret not found");
      }

    } catch (Exception e) {
      logger.error("❌ Database Dynamic secret fetch failed: {}", e.getMessage());
      return createErrorSecretInfo("Database Dynamic",
          VaultConfig.getDatabasePath() + "/creds/" + VaultConfig.getDatabaseDynamicRole(), e.getMessage());
    }
  }

  /**
   * Get Database Static secret (with caching)
   */
  public SecretInfo getDatabaseStaticSecret() {
    long currentTime = System.currentTimeMillis();

    // Return cached value if cache is valid
    if (cachedDbStaticSecret != null && (currentTime - lastDbStaticRefresh) < CACHE_VALIDITY_MS) {
      logger.info("🔒 Database Static Secret returned from cache (last refresh: {}s ago)",
          (currentTime - lastDbStaticRefresh) / 1000);
      return cachedDbStaticSecret;
    }

    try {
      logger.info("=== Database Static Secret Refresh (retrieved from Vault) ===");

      String role = VaultConfig.getDatabaseStaticRole();
      Map<String, Object> response = vaultClient.getDatabaseStaticSecret(role);

      if (response != null && response.containsKey("data")) {
        @SuppressWarnings("unchecked")
        Map<String, Object> data = (Map<String, Object>) response.get("data");

        String path = VaultConfig.getDatabasePath() + "/static-creds/" + role;
        SecretInfo secretInfo = new SecretInfo("Database Static", path, data);
        secretInfo.setTtl(3600L); // Static secret has long or fixed TTL
        secretInfo.setRenewable(false); // Static secret is generally not renewable

        // Update cache
        cachedDbStaticSecret = secretInfo;
        lastDbStaticRefresh = currentTime;

        logger.info("✅ Database Static secret fetch successful (TTL: {}s) - cache updated", secretInfo.getTtl());
        logger.info("🔒 Database Static Secret (TTL: {}s): username: {}, password: {}",
            secretInfo.getTtl(), data.get("username"), "***");

        return secretInfo;
      } else {
        throw new RuntimeException("Database Static secret not found");
      }

    } catch (Exception e) {
      logger.error("❌ Database Static secret fetch failed: {}", e.getMessage());
      return createErrorSecretInfo("Database Static",
          VaultConfig.getDatabasePath() + "/static-creds/" + VaultConfig.getDatabaseStaticRole(), e.getMessage());
    }
  }

  /**
   * Get all secret information (excluding Database Dynamic Secret)
   */
  public Map<String, SecretInfo> getAllSecrets() {
    Map<String, SecretInfo> secrets = new HashMap<>();

    // Check current Database credential source
    String credentialSource = VaultConfig.getDatabaseCredentialSource();

    // KV Secret is always retrieved (independent of Database credentials)
    secrets.put("kv", getKvSecret());

    // Database Static Secret is retrieved only in static mode
    if ("static".equals(credentialSource)) {
      secrets.put("dbStatic", getDatabaseStaticSecret());
    }

    // dbDynamic is managed by DatabaseConfig, so not retrieved here
    return secrets;
  }

  /**
   * Get secret information for display (excluding Database Dynamic Secret)
   */
  public Map<String, SecretInfo> getDisplaySecrets() {
    return getAllSecrets();
  }

  /**
   * Get currently used Database Dynamic Secret information (does not issue new)
   */
  public SecretInfo getCurrentDatabaseDynamicSecret() {
    return com.example.vaulttomcat.config.DatabaseConfig.getCurrentCredentialInfo();
  }

  /**
   * Return VaultClient instance
   */
  public VaultClient getVaultClient() {
    return vaultClient;
  }

  /**
   * Detect and log secret changes
   */
  public void logSecretChanges() {
    logger.info("🔄 Secret change detection and logging (to be implemented)");
  }

  /**
   * Clean up resources
   */
  public void close() {
    if (vaultClient != null) {
      vaultClient.close();
    }
  }

  private SecretInfo createErrorSecretInfo(String type, String path, String errorMessage) {
    Map<String, Object> errorData = new HashMap<>();
    errorData.put("error", errorMessage);
    return new SecretInfo(type, path, errorData);
  }
}
