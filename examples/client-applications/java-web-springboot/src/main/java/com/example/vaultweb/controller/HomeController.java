package com.example.vaultweb.controller;

import com.example.vaultweb.model.SecretInfo;
import com.example.vaultweb.service.DatabaseService;
import com.example.vaultweb.service.VaultSecretService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Main Controller Class
 * Handles web page requests and displays Vault secret information on the screen.
 */
@Controller
@RequestMapping("/")
public class HomeController {

  private static final Logger logger = LoggerFactory.getLogger(HomeController.class);

  @Autowired
  private VaultSecretService vaultSecretService;

  @Autowired
  private DatabaseService databaseService;

  /**
   * Main page (index.jsp)
   */
  @GetMapping
  public String index(Model model) {
    logger.info("🚀 Starting Vault Spring Boot Web Application");

    try {
      // Retrieve Vault secret information
      Map<String, SecretInfo> secrets = vaultSecretService.getAllSecrets();
      model.addAttribute("secrets", secrets);

      // Test database connection
      logger.info("🔍 Starting database connection test");
      try {
        Map<String, Object> dbConnection = databaseService.testConnection();
        logger.info("🔍 Database connection test completed: {}", dbConnection.get("status"));
        logger.info("🔍 Database connection result data: {}", dbConnection);
        model.addAttribute("dbConnection", dbConnection);
      } catch (Exception e) {
        logger.error("❌ Error occurred during database connection test: {}", e.getMessage(), e);
        Map<String, Object> errorResult = new HashMap<>();
        errorResult.put("status", "error");
        errorResult.put("error", e.getMessage());
        model.addAttribute("dbConnection", errorResult);
      }

      // Database statistics
      logger.info("🔍 Starting database statistics retrieval");
      Map<String, Object> dbStats = databaseService.getDatabaseStats();
      logger.info("🔍 Database statistics retrieval completed");
      model.addAttribute("dbStats", dbStats);

      logger.info("✅ Main page data load completed");
      logger.info("📊 Loaded data: {} secrets",
          secrets.size());

    } catch (Exception e) {
      logger.error("❌ Main page data load failed: {}", e.getMessage());
      model.addAttribute("error", e.getMessage());
    }

    return "index";
  }

  /**
   * Secret renewal API
   */
  @GetMapping("/refresh")
  public String refresh(Model model) {
    logger.info("🔄 Secret renewal request");

    try {
      // Detect and log secret changes
      vaultSecretService.logSecretChanges();

      // Retrieve renewed secret information
      Map<String, SecretInfo> secrets = vaultSecretService.getAllSecrets();
      model.addAttribute("secrets", secrets);
      model.addAttribute("refreshTime", java.time.LocalDateTime.now());

      // Additional database connection test
      logger.info("🔍 Starting database connection test");
      try {
        Map<String, Object> dbConnection = databaseService.testConnection();
        logger.info("🔍 Database connection test completed: {}", dbConnection.get("status"));
        model.addAttribute("dbConnection", dbConnection);
      } catch (Exception e) {
        logger.error("❌ Error occurred during database connection test: {}", e.getMessage(), e);
        Map<String, Object> errorResult = new HashMap<>();
        errorResult.put("status", "error");
        errorResult.put("error", e.getMessage());
        model.addAttribute("dbConnection", errorResult);
      }

      // Additional database statistics
      logger.info("🔍 Starting database statistics retrieval");
      Map<String, Object> dbStats = databaseService.getDatabaseStats();
      logger.info("🔍 Database statistics retrieval completed");
      model.addAttribute("dbStats", dbStats);

      logger.info("✅ Secret renewal completed");

    } catch (Exception e) {
      logger.error("❌ Secret renewal failed: {}", e.getMessage());
      model.addAttribute("error", e.getMessage());
    }

    return "index";
  }

  /**
   * Database Information API
   */
  @GetMapping("/database")
  public String database(Model model) {
    logger.info("🗄️ Database information retrieval request");

    try {
      // Test database connection
      Map<String, Object> dbConnection = databaseService.testConnection();
      model.addAttribute("dbConnection", dbConnection);

      // Database table information
      List<Map<String, Object>> tables = databaseService.getTables();
      model.addAttribute("tables", tables);

      // Database statistics
      Map<String, Object> dbStats = databaseService.getDatabaseStats();
      model.addAttribute("dbStats", dbStats);

      logger.info("✅ Database information retrieval completed");

    } catch (Exception e) {
      logger.error("❌ Database information retrieval failed: {}", e.getMessage());
      model.addAttribute("error", e.getMessage());
    }

    return "database";
  }

  /**
   * Health Check API
   */
  @GetMapping("/health")
  public String health(Model model) {
    logger.info("🏥 Health Check request");

    Map<String, Object> health = new java.util.HashMap<>();
    health.put("status", "UP");
    health.put("timestamp", java.time.LocalDateTime.now());
    health.put("application", "Vault Spring Boot Web App");

    try {
      // Check Vault connection status
      Map<String, SecretInfo> secrets = vaultSecretService.getAllSecrets();
      health.put("vault_status", "CONNECTED");
      health.put("secrets_count", secrets.size());

      // Check Database connection status
      Map<String, Object> dbConnection = databaseService.testConnection();
      health.put("database_status", dbConnection.get("status"));

      logger.info("✅ Health Check completed: Vault={}, Database={}",
          health.get("vault_status"), health.get("database_status"));

    } catch (Exception e) {
      logger.error("❌ Health Check failed: {}", e.getMessage());
      health.put("status", "DOWN");
      health.put("error", e.getMessage());
    }

    model.addAttribute("health", health);
    return "health";
  }
}
