package com.example.vaulttomcat.config;

import com.example.vaulttomcat.model.SecretInfo;
import com.example.vaulttomcat.service.VaultSecretService;
import org.apache.commons.dbcp2.BasicDataSource;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.sql.Connection;
import java.sql.SQLException;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

/**
 * Database Connection Pool Configuration Management Class
 */
public class DatabaseConfig {
  private static final Logger logger = LoggerFactory.getLogger(DatabaseConfig.class);

  private static BasicDataSource dataSource;
  private static ScheduledExecutorService scheduler;
  private static VaultSecretService vaultSecretService;
  private static SecretInfo currentCredentialInfo;

  /**
   * Initialize Database Connection Pool
   */
  public static void initialize(VaultSecretService vaultService) {
    vaultSecretService = vaultService;
    String credentialSource = VaultConfig.getDatabaseCredentialSource();

    logger.info("=== Database Connection Pool Initialization (Credential Source: {}) ===", credentialSource);

    try {
      switch (credentialSource.toLowerCase()) {
        case "kv":
          initializeWithKv();
          break;
        case "dynamic":
          initializeWithDynamic();
          break;
        case "static":
          initializeWithStatic();
          break;
        default:
          throw new IllegalArgumentException("Unsupported credential source: " + credentialSource);
      }

      logger.info("🎉 Database Connection Pool initialization completed");

    } catch (Exception e) {
      logger.error("❌ Database Connection Pool initialization failed: {}", e.getMessage(), e);
      throw new RuntimeException("Database Connection Pool initialization failed", e);
    }
  }

  /**
   * Initialize with KV
   */
  private static void initializeWithKv() {
    logger.info("📦 KV-based Database credential initialization");

    // Retrieve credentials from KV
    SecretInfo kvSecret = vaultSecretService.getKvSecret();
    Map<String, Object> data = (Map<String, Object>) kvSecret.getData();

    String username = (String) data.get("database_username");
    String password = (String) data.get("database_password");

    // Create Connection Pool
    createDataSource(username, password, kvSecret);

    // Schedule KV version change detection
    int refreshInterval = VaultConfig.getDatabaseKvRefreshInterval();
    scheduleKvVersionCheck(refreshInterval, kvSecret.getVersion());
  }

  /**
   * Initialize with Dynamic
   */
  private static void initializeWithDynamic() {
    logger.info("🔄 Database Dynamic Secret-based credential initialization");

    // Retrieve Dynamic Secret
    SecretInfo dbSecret = vaultSecretService.getDatabaseDynamicSecret();
    Map<String, Object> data = (Map<String, Object>) dbSecret.getData();

    String username = (String) data.get("username");
    String password = (String) data.get("password");

    // Create Connection Pool
    createDataSource(username, password, dbSecret);

    // Schedule TTL-based renewal
    if (dbSecret.getTtl() != null && dbSecret.getTtl() > 0) {
      long refreshDelay = (long) (dbSecret.getTtl() * 0.8 * 1000);
      scheduleCredentialRefresh(refreshDelay);
    }
  }

  /**
   * Initialize with Static
   */
  private static void initializeWithStatic() {
    logger.info("🔒 Database Static Secret-based credential initialization");

    // Retrieve Static Secret
    SecretInfo staticSecret = vaultSecretService.getDatabaseStaticSecret();
    Map<String, Object> data = (Map<String, Object>) staticSecret.getData();

    String username = (String) data.get("username");
    String password = (String) data.get("password");

    // Create Connection Pool
    createDataSource(username, password, staticSecret);

    // Periodic renewal not needed for Static (automatically rotated by Vault)
    logger.info("ℹ️ Static Secret is automatically rotated by Vault");
  }

  /**
   * Create Connection Pool
   */
  private static void createDataSource(String username, String password, SecretInfo secretInfo) {
    logger.info("🔧 Starting Database Connection Pool creation...");

    dataSource = new BasicDataSource();

    // Set database connection settings
    String url = VaultConfig.getDatabaseUrl();
    String driverClass = VaultConfig.getDatabaseDriver();

    dataSource.setUrl(url);
    dataSource.setDriverClassName(driverClass);
    dataSource.setUsername(username);
    dataSource.setPassword(password);

    logger.info("🗄️ Database URL: {}", url);
    logger.info("🔌 Database Driver: {}", driverClass);
    logger.info("🔑 Database credential configured - Username: {}, Password: ***", username);

    // Connection Pool settings
    dataSource.setInitialSize(5);
    dataSource.setMaxTotal(20);
    dataSource.setMaxIdle(10);
    dataSource.setMinIdle(5);
    dataSource.setMaxWaitMillis(30000);
    logger.info("📊 Connection Pool settings - Initial: 5, MaxTotal: 20, MaxIdle: 10, MinIdle: 5");

    // Connection validation
    dataSource.setValidationQuery("SELECT 1");
    dataSource.setTestOnBorrow(true);
    dataSource.setTestWhileIdle(true);
    dataSource.setTimeBetweenEvictionRunsMillis(30000);
    logger.info("🔍 Connection validation settings completed");

    // Test Connection Pool
    try {
      Connection testConnection = dataSource.getConnection();
      logger.info("✅ Database Connection test successful");
      testConnection.close();
      logger.info("🔌 Database Connection test connection closed");
    } catch (SQLException e) {
      logger.error("❌ Database Connection test failed: {}", e.getMessage());
    }

    // Store current credential information
    currentCredentialInfo = secretInfo;

    logger.info("🎉 Database Connection Pool creation completed - Username: {}", username);
  }

  /**
   * Schedule credential renewal
   */
  private static void scheduleCredentialRefresh(long delayMs) {
    logger.info("⏰ Scheduling Database Secret credential renewal - executing in {}s", delayMs / 1000);

    scheduler = Executors.newSingleThreadScheduledExecutor(r -> {
      Thread t = new Thread(r, "vault-credential-refresh");
      t.setDaemon(true);
      return t;
    });

    scheduler.schedule(() -> {
      logger.info("🔔 Scheduled Database Secret renewal time reached - starting renewal");
      try {
        refreshCredentials();
      } catch (Exception e) {
        logger.error("❌ Scheduled credential renewal failed: {}", e.getMessage(), e);
      }
    }, delayMs, TimeUnit.MILLISECONDS);

    logger.info("✅ Database Secret renewal scheduling completed");
  }

  /**
   * KV version check scheduler
   */
  private static void scheduleKvVersionCheck(int intervalSeconds, String currentVersion) {
    logger.info("⏰ Scheduling KV version check - executing every {}s", intervalSeconds);

    scheduler = Executors.newSingleThreadScheduledExecutor(r -> {
      Thread t = new Thread(r, "vault-kv-version-check");
      t.setDaemon(true);
      return t;
    });

    scheduler.scheduleAtFixedRate(() -> {
      try {
        SecretInfo newKvSecret = vaultSecretService.getKvSecret();
        String newVersion = newKvSecret.getVersion();

        if (!currentVersion.equals(newVersion)) {
          logger.info("🔔 KV version change detected ({}→{}) - recreating Connection Pool",
              currentVersion, newVersion);
          refreshCredentialsFromKv(newKvSecret);
        } else {
          logger.debug("✅ No KV version change (version: {})", currentVersion);
        }
      } catch (Exception e) {
        logger.error("❌ KV version check failed: {}", e.getMessage(), e);
      }
    }, intervalSeconds, intervalSeconds, TimeUnit.SECONDS);
  }

  /**
   * Refresh KV credentials
   */
  private static void refreshCredentialsFromKv(SecretInfo newKvSecret) {
    logger.info("=== 🔄 KV Credential Renewal Started ===");

    try {
      Map<String, Object> data = (Map<String, Object>) newKvSecret.getData();
      String username = (String) data.get("database_username");
      String password = (String) data.get("database_password");

      logger.info("✅ New KV credentials retrieved - Username: {}", username);

      // Recreate Connection Pool
      closeDataSource();
      createDataSource(username, password, newKvSecret);

      // Schedule next version check
      int refreshInterval = VaultConfig.getDatabaseKvRefreshInterval();
      scheduleKvVersionCheck(refreshInterval, newKvSecret.getVersion());

      logger.info("🎉 KV credential renewal and Connection Pool recreation completed");

    } catch (Exception e) {
      logger.error("❌ KV credential renewal failed: {}", e.getMessage(), e);
    }
  }

  /**
   * Refresh credentials
   */
  private static void refreshCredentials() {
    String credentialSource = VaultConfig.getDatabaseCredentialSource();

    logger.info("=== Database Credential Renewal (Source: {}) ===", credentialSource);

    try {
      SecretInfo newSecret = null;
      String username = null;
      String password = null;

      switch (credentialSource.toLowerCase()) {
        case "kv":
          // KV is handled by version check, so not called here
          logger.warn("⚠️ KV credentials are renewed by version check");
          return;
        case "dynamic":
          newSecret = vaultSecretService.getDatabaseDynamicSecret();
          Map<String, Object> dynamicData = (Map<String, Object>) newSecret.getData();
          username = (String) dynamicData.get("username");
          password = (String) dynamicData.get("password");
          break;
        case "static":
          newSecret = vaultSecretService.getDatabaseStaticSecret();
          Map<String, Object> staticData = (Map<String, Object>) newSecret.getData();
          username = (String) staticData.get("username");
          password = (String) staticData.get("password");
          break;
      }

      // Recreate Connection Pool
      closeDataSource();
      createDataSource(username, password, newSecret);

      // Schedule next renewal for Dynamic
      if ("dynamic".equals(credentialSource) && newSecret.getTtl() != null && newSecret.getTtl() > 0) {
        long refreshDelay = (long) (newSecret.getTtl() * 0.8 * 1000);
        scheduleCredentialRefresh(refreshDelay);
      }

      logger.info("🎉 Database credential renewal completed");

    } catch (Exception e) {
      logger.error("❌ Database credential renewal failed: {}", e.getMessage(), e);
    }
  }

  /**
   * Close Connection Pool
   */
  private static void closeDataSource() {
    if (dataSource != null) {
      try {
        // Log Connection Pool status
        logger.info("📊 Existing Connection Pool status - Active: {}, Idle: {}",
            dataSource.getNumActive(), dataSource.getNumIdle());

        logger.info("🔄 Closing existing Database Connection Pool...");
        dataSource.close();
        logger.info("✅ Existing Database Connection Pool closed");
      } catch (SQLException e) {
        logger.error("❌ Error occurred while closing Database Connection Pool: {}", e.getMessage());
      } finally {
        dataSource = null;
        logger.info("🧹 DataSource reference cleanup completed");
      }
    } else {
      logger.info("ℹ️ No DataSource to close");
    }
  }

  /**
   * Get database connection
   */
  public static Connection getConnection() throws SQLException {
    if (dataSource == null) {
      throw new SQLException("DataSource is not initialized");
    }
    return dataSource.getConnection();
  }

  /**
   * Check Connection Pool status
   */
  public static Map<String, Object> getPoolStatus() {
    Map<String, Object> status = new HashMap<>();

    if (dataSource != null) {
      status.put("initialSize", dataSource.getInitialSize());
      status.put("maxTotal", dataSource.getMaxTotal());
      status.put("maxIdle", dataSource.getMaxIdle());
      status.put("minIdle", dataSource.getMinIdle());
      status.put("numActive", dataSource.getNumActive());
      status.put("numIdle", dataSource.getNumIdle());
    } else {
      status.put("status", "not_initialized");
    }

    return status;
  }

  /**
   * Get currently used Database Dynamic Secret information
   */
  public static SecretInfo getCurrentCredentialInfo() {
    return currentCredentialInfo;
  }

  /**
   * Clean up resources
   */
  public static void shutdown() {
    logger.info("=== DatabaseConfig Shutdown ===");

    // Shutdown Scheduler
    if (scheduler != null && !scheduler.isShutdown()) {
      scheduler.shutdown();
      try {
        if (!scheduler.awaitTermination(5, TimeUnit.SECONDS)) {
          scheduler.shutdownNow();
        }
      } catch (InterruptedException e) {
        scheduler.shutdownNow();
        Thread.currentThread().interrupt();
      }
    }

    // Shutdown DataSource
    closeDataSource();

    logger.info("✅ DatabaseConfig shutdown completed");
  }
}
