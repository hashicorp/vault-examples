package com.example.vaultweb.config;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.stereotype.Component;

import javax.sql.DataSource;
import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;
import com.example.vaultweb.service.VaultSecretService;

/**
 * Database Configuration Management Class
 * Configures DataSource using credentials received from Vault.
 */
@Configuration
@Component
@RefreshScope
@ConfigurationProperties(prefix = "spring.datasource")
public class DatabaseConfig {

  private static final Logger logger = LoggerFactory.getLogger(DatabaseConfig.class);

  @Autowired
  private VaultSecretService vaultSecretService;

  @Autowired
  private VaultConfig vaultConfig;

  private String url;
  private String driverClassName;
  private String username;
  private String password;
  private Hikari hikari;

  @Bean
  @RefreshScope
  public DataSource dataSource() {
    logger.info("=== DatabaseConfig Debug ===");
    logger.info("URL: {}", this.url);
    logger.info("Driver: {}", this.driverClassName);
    logger.info("Username: {}", this.username);
    logger.info("Password: {}", (this.password != null ? "***" : "NULL"));

    // Set default value if driverClassName is null
    if (this.driverClassName == null) {
      this.driverClassName = "com.mysql.cj.jdbc.Driver";
      logger.info("Setting default driver: {}", this.driverClassName);
    }

    // Throw error if URL is null (required in configuration file)
    if (this.url == null) {
      logger.error("Database URL is not configured. Please set spring.datasource.url in application.yml.");
      throw new IllegalStateException("Database URL is not configured.");
    }

    // Check credential source from Vault configuration
    String credentialSource = vaultConfig.getDatabase() != null
        ? vaultConfig.getDatabase().getCredentialSource()
        : "dynamic";

    logger.info("=== Database Credential Source: {} ===", credentialSource);

    String finalUsername = this.username;
    String finalPassword = this.password;

    try {
      switch (credentialSource.toLowerCase()) {
        case "kv":
          // Retrieve credentials from KV Secret
          var kvSecret = vaultSecretService.getKvSecret();
          if (kvSecret != null && kvSecret.getData() != null) {
            // Get key names from configuration
            String usernameKey = vaultConfig.getDatabase() != null
                && vaultConfig.getDatabase().getKv() != null
                && vaultConfig.getDatabase().getKv().getUsernameKey() != null
                    ? vaultConfig.getDatabase().getKv().getUsernameKey()
                    : "database_username";
            String passwordKey = vaultConfig.getDatabase() != null
                && vaultConfig.getDatabase().getKv() != null
                && vaultConfig.getDatabase().getKv().getPasswordKey() != null
                    ? vaultConfig.getDatabase().getKv().getPasswordKey()
                    : "database_password";

            finalUsername = (String) kvSecret.getData().get(usernameKey);
            finalPassword = (String) kvSecret.getData().get(passwordKey);
            logger.info("Using KV Secret credentials: {} (keys: {}/{})", finalUsername, usernameKey, passwordKey);
          }
          break;

        case "static":
          // Retrieve credentials from Database Static Secret
          var staticSecret = vaultSecretService.getDatabaseStaticSecret();
          if (staticSecret != null && staticSecret.getData() != null) {
            finalUsername = (String) staticSecret.getData().get("username");
            finalPassword = (String) staticSecret.getData().get("password");
            logger.info("Using Static Secret credentials: {}", finalUsername);
          }
          break;

        case "dynamic":
        default:
          // Retrieve credentials from Database Dynamic Secret
          String role = vaultConfig.getDatabase() != null
              && vaultConfig.getDatabase().getDynamic() != null
              && vaultConfig.getDatabase().getDynamic().getRole() != null
                  ? vaultConfig.getDatabase().getDynamic().getRole()
                  : (vaultConfig.getDatabase() != null
                      && vaultConfig.getDatabase().getRole() != null
                          ? vaultConfig.getDatabase().getRole()
                          : "db-demo-dynamic");
          var dynamicSecret = vaultSecretService.getDatabaseCredentials(role);
          if (dynamicSecret != null && dynamicSecret.getData() != null) {
            finalUsername = (String) dynamicSecret.getData().get("username");
            finalPassword = (String) dynamicSecret.getData().get("password");
            logger.info("Using Dynamic Secret credentials: {} (role: {})", finalUsername, role);
          }
          break;
      }
    } catch (Exception e) {
      logger.error("Failed to retrieve Vault credentials, using defaults: {}", e.getMessage());
    }

    HikariConfig config = new HikariConfig();
    config.setJdbcUrl(this.url);
    config.setDriverClassName(this.driverClassName != null ? this.driverClassName : "com.mysql.cj.jdbc.Driver");
    config.setUsername(finalUsername);
    config.setPassword(finalPassword);

    if (hikari != null) {
      config.setMaximumPoolSize(hikari.getMaximumPoolSize());
      config.setMinimumIdle(hikari.getMinimumIdle());
      config.setConnectionTimeout(hikari.getConnectionTimeout());
      config.setIdleTimeout(hikari.getIdleTimeout());
      config.setMaxLifetime(hikari.getMaxLifetime());
    }

    return new HikariDataSource(config);
  }

  // Getters and Setters
  public String getUrl() {
    return url;
  }

  public void setUrl(String url) {
    this.url = url;
  }

  public String getDriverClassName() {
    return driverClassName;
  }

  public void setDriverClassName(String driverClassName) {
    this.driverClassName = driverClassName;
  }

  public String getUsername() {
    return username;
  }

  public void setUsername(String username) {
    this.username = username;
  }

  public String getPassword() {
    return password;
  }

  public void setPassword(String password) {
    this.password = password;
  }

  public Hikari getHikari() {
    return hikari;
  }

  public void setHikari(Hikari hikari) {
    this.hikari = hikari;
  }

  // Inner Class
  public static class Hikari {
    private int maximumPoolSize;
    private int minimumIdle;
    private long connectionTimeout;
    private long idleTimeout;
    private long maxLifetime;

    // Getters and Setters
    public int getMaximumPoolSize() {
      return maximumPoolSize;
    }

    public void setMaximumPoolSize(int maximumPoolSize) {
      this.maximumPoolSize = maximumPoolSize;
    }

    public int getMinimumIdle() {
      return minimumIdle;
    }

    public void setMinimumIdle(int minimumIdle) {
      this.minimumIdle = minimumIdle;
    }

    public long getConnectionTimeout() {
      return connectionTimeout;
    }

    public void setConnectionTimeout(long connectionTimeout) {
      this.connectionTimeout = connectionTimeout;
    }

    public long getIdleTimeout() {
      return idleTimeout;
    }

    public void setIdleTimeout(long idleTimeout) {
      this.idleTimeout = idleTimeout;
    }

    public long getMaxLifetime() {
      return maxLifetime;
    }

    public void setMaxLifetime(long maxLifetime) {
      this.maxLifetime = maxLifetime;
    }
  }
}
