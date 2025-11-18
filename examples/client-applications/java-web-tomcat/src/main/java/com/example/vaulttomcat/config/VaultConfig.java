package com.example.vaulttomcat.config;

import java.io.IOException;
import java.io.InputStream;
import java.util.Properties;

/**
 * Vault Configuration Management Class
 */
public class VaultConfig {
  private static final String CONFIG_FILE = "vault.properties";
  private static Properties properties;

  static {
    loadProperties();
  }

  private static void loadProperties() {
    properties = new Properties();
    try (InputStream input = VaultConfig.class.getClassLoader().getResourceAsStream(CONFIG_FILE)) {
      if (input != null) {
        properties.load(input);
      }
    } catch (IOException e) {
      System.err.println("Failed to load vault.properties: " + e.getMessage());
    }
  }

  public static String getVaultUrl() {
    return getProperty("vault.url", "http://127.0.0.1:8200");
  }

  public static String getVaultToken() {
    return getProperty("vault.token", "root");
  }

  public static String getAuthType() {
    return getProperty("vault.auth.type", "token");
  }

  public static String getAppRoleId() {
    return getProperty("vault.approle.role_id", "");
  }

  public static String getAppRoleSecretId() {
    return getProperty("vault.approle.secret_id", "");
  }

  public static boolean isTokenRenewalEnabled() {
    return Boolean.parseBoolean(getProperty("vault.token.renewal.enabled", "true"));
  }

  public static double getTokenRenewalThreshold() {
    return Double.parseDouble(getProperty("vault.token.renewal.threshold", "0.8"));
  }

  public static String getKvPath() {
    return getProperty("vault.kv.path", "my-vault-app-kv");
  }

  public static String getDatabasePath() {
    return getProperty("vault.database.path", "my-vault-app-database");
  }

  public static String getDatabaseDynamicRole() {
    return getProperty("vault.database.dynamic.role", "db-demo-dynamic");
  }

  public static String getDatabaseStaticRole() {
    return getProperty("vault.database.static.role", "db-demo-static");
  }

  // Database credential source (kv, dynamic, static)
  public static String getDatabaseCredentialSource() {
    return getProperty("vault.database.credential.source", "dynamic");
  }

  public static String getDatabaseKvPath() {
    return getProperty("vault.database.kv.path", "my-vault-app-kv/data/database");
  }

  public static int getDatabaseKvRefreshInterval() {
    return Integer.parseInt(getProperty("vault.database.kv.refresh_interval", "30"));
  }

  public static String getDatabaseUrl() {
    return getProperty("vault.database.url", "jdbc:mysql://127.0.0.1:3306/mydb");
  }

  public static String getDatabaseDriver() {
    return getProperty("vault.database.driver", "com.mysql.cj.jdbc.Driver");
  }

  public static String getVaultNamespace() {
    return getProperty("vault.namespace", "");
  }

  private static String getProperty(String key, String defaultValue) {
    // 1. Check system properties
    String systemProperty = System.getProperty(key);
    if (systemProperty != null && !systemProperty.isEmpty()) {
      return systemProperty;
    }

    // 2. Check environment variables
    String envProperty = System.getenv(key.toUpperCase().replace(".", "_"));
    if (envProperty != null && !envProperty.isEmpty()) {
      return envProperty;
    }

    // 3. Check properties file
    return properties.getProperty(key, defaultValue);
  }
}
