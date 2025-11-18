package com.example.vaultweb.service;

import com.example.vaultweb.model.SecretInfo;
import com.example.vaultweb.config.VaultConfig;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.stereotype.Service;
import org.springframework.vault.core.VaultTemplate;
import org.springframework.vault.support.VaultResponse;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

/**
 * Vault Secret Service Class
 * Retrieves and manages secrets through Spring Cloud Vault Config.
 */
@Service
@RefreshScope
public class VaultSecretService {

  private static final Logger logger = LoggerFactory.getLogger(VaultSecretService.class);

  private final VaultTemplate vaultTemplate;

  @Autowired
  private VaultConfig vaultConfig;

  // KV secret (automatically injected from Spring Cloud Vault Config)
  @Value("${vault.kv.api_key:}")
  private String kvApiKey;

  @Value("${vault.kv.database_url:}")
  private String kvDatabaseUrl;

  // Database Dynamic secret (automatically injected from Spring Cloud Vault Config)
  @Value("${spring.datasource.username:}")
  private String dbDynamicUsername;

  @Value("${spring.datasource.password:}")
  private String dbDynamicPassword;

  public VaultSecretService(VaultTemplate vaultTemplate) {
    this.vaultTemplate = vaultTemplate;
  }

  /**
   * Get KV secret
   */
  public SecretInfo getKvSecret() {
    try {
      logger.info("=== KV Secret Refresh ===");

      // Retrieve KV data directly from Vault
      VaultResponse response = vaultTemplate.read("my-vault-app-kv/data/database");
      Map<String, Object> kvData = new HashMap<>();

      if (response != null && response.getData() != null) {
        // In KV v2, actual data is inside the 'data' key
        Object dataObj = response.getData().get("data");
        if (dataObj instanceof Map) {
          @SuppressWarnings("unchecked")
          Map<String, Object> actualData = (Map<String, Object>) dataObj;
          kvData.putAll(actualData);
        } else {
          kvData.putAll(response.getData());
        }

        String version = "1";
        if (response.getMetadata() != null && response.getMetadata().get("version") != null) {
          version = response.getMetadata().get("version").toString();
        }
        logger.info("✅ KV secret fetch successful (version: {})", version);
        logger.info("📦 KV Secret Data (version: {}): {}", version, kvData);

        SecretInfo secretInfo = new SecretInfo("KV", "my-vault-app-kv/data/database", kvData);
        secretInfo.setVersion(version);
        return secretInfo;
      } else {
        // Use values injected from Spring Cloud Vault Config
        kvData.put("api_key", kvApiKey != null ? kvApiKey : "");
        kvData.put("database_url", kvDatabaseUrl != null ? kvDatabaseUrl : "");
        logger.info("📦 KV Secret Data (from config): {}", kvData);

        SecretInfo secretInfo = new SecretInfo("KV", "my-vault-app-kv/data/database", kvData);
        secretInfo.setVersion("1");
        return secretInfo;
      }

    } catch (Exception e) {
      logger.error("❌ KV secret fetch failed: {}", e.getMessage());
      return createErrorSecretInfo("KV", "my-vault-app-kv/data/database", e.getMessage());
    }
  }

  /**
   * Get Database Dynamic secret
   */
  public SecretInfo getDatabaseDynamicSecret() {
    try {
      logger.info("=== Database Dynamic Secret Refresh ===");

      // Retrieve latest credentials via direct Vault API call
      VaultResponse response = vaultTemplate.read("my-vault-app-database/creds/db-demo-dynamic");

      if (response != null && response.getData() != null) {
        Map<String, Object> dbData = new HashMap<>();
        dbData.put("username", response.getData().get("username"));
        dbData.put("password", response.getData().get("password"));

        SecretInfo secretInfo = new SecretInfo("Database Dynamic",
            "my-vault-app-database/creds/db-demo-dynamic", dbData);

        // Set lease information
        if (response.getLeaseId() != null) {
          secretInfo.setLeaseId(response.getLeaseId());
        }
        if (response.getLeaseDuration() > 0) {
          secretInfo.setTtl(response.getLeaseDuration());
        }
        secretInfo.setRenewable(response.isRenewable());

        logger.info("✅ Database Dynamic secret fetch successful (TTL: {}s)", secretInfo.getTtl());
        logger.info("🗄️ Database Dynamic Secret (TTL: {}s): username: {}, password: {}",
            secretInfo.getTtl(), response.getData().get("username"), "***");

        return secretInfo;
      } else {
        throw new RuntimeException("Database Dynamic secret not found");
      }

    } catch (Exception e) {
      logger.error("❌ Database Dynamic secret fetch failed: {}", e.getMessage());
      return createErrorSecretInfo("Database Dynamic",
          "my-vault-app-database/creds/db-demo-dynamic", e.getMessage());
    }
  }

  /**
   * Get Database Dynamic secret (direct Vault API call)
   */
  public VaultResponse getDatabaseCredentials(String roleName) {
    try {
      logger.info("=== Database Dynamic Secret API Call ===");

      String path = "my-vault-app-database/creds/" + roleName;
      VaultResponse response = vaultTemplate.read(path);

      if (response != null && response.getData() != null) {
        logger.info("✅ Database Dynamic secret API call successful: {}", path);
        return response;
      } else {
        throw new RuntimeException("Database Dynamic secret not found: " + path);
      }

    } catch (Exception e) {
      logger.error("❌ Database Dynamic secret API call failed: {}", e.getMessage());
      throw new RuntimeException("Database Dynamic secret fetch failed: " + e.getMessage());
    }
  }

  /**
   * Get Database Static secret
   */
  public SecretInfo getDatabaseStaticSecret() {
    try {
      logger.info("=== Database Static Secret Refresh ===");

      // Retrieve Static secret via direct Vault API call
      VaultResponse response = vaultTemplate.read("my-vault-app-database/static-creds/db-demo-static");

      if (response != null && response.getData() != null) {
        Map<String, Object> dbData = (Map<String, Object>) response.getData();

        SecretInfo secretInfo = new SecretInfo("Database Static",
            "my-vault-app-database/static-creds/db-demo-static", dbData);
        secretInfo.setTtl(3600L);
        secretInfo.setRenewable(false);

        logger.info("✅ Database Static secret fetch successful (TTL: {}s)", secretInfo.getTtl());
        logger.info("🔒 Database Static Secret (TTL: {}s): {}",
            secretInfo.getTtl(), dbData);

        return secretInfo;
      } else {
        throw new RuntimeException("Database Static secret not found.");
      }

    } catch (Exception e) {
      logger.error("❌ Database Static secret fetch failed: {}", e.getMessage());
      return createErrorSecretInfo("Database Static",
          "my-vault-app-database/static-creds/db-demo-static", e.getMessage());
    }
  }

  /**
   * Get all secret information
   */
  public Map<String, SecretInfo> getAllSecrets() {
    Map<String, SecretInfo> secrets = new HashMap<>();

    // Check credential source
    String credentialSource = vaultConfig.getDatabase() != null
        ? vaultConfig.getDatabase().getCredentialSource()
        : "dynamic";

    logger.info("🔍 Current credential source: {}", credentialSource);

    // KV Secret is always retrieved (independent of Database credentials)
    secrets.put("kv", getKvSecret());

    // Retrieve Database credentials based on configured source
    switch (credentialSource.toLowerCase()) {
      case "kv":
        // Use Database credentials from KV Secret (not displayed separately)
        logger.info("📦 Database credentials: Using KV Secret");
        break;
      case "static":
        secrets.put("database_static", getDatabaseStaticSecret());
        break;
      case "dynamic":
      default:
        secrets.put("database_dynamic", getDatabaseDynamicSecret());
        break;
    }

    return secrets;
  }

  /**
   * Create error secret information
   */
  private SecretInfo createErrorSecretInfo(String type, String path, String errorMessage) {
    SecretInfo secretInfo = new SecretInfo(type, path, new HashMap<>());
    secretInfo.getData().put("error", errorMessage);
    secretInfo.getData().put("status", "failed");
    return secretInfo;
  }

  /**
   * Detect and log secret changes
   */
  public void logSecretChanges() {
    logger.info("🔄 Starting secret renewal... (automatic renewal enabled)");

    // Retrieve all secrets to detect changes
    getAllSecrets().forEach((key, secretInfo) -> {
      logger.info("📊 {} secret status: {}", key, secretInfo.getType());
    });
  }
}
