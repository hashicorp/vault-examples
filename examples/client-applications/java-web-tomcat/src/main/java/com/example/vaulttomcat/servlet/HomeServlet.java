package com.example.vaulttomcat.servlet;

import com.example.vaulttomcat.model.SecretInfo;
import com.example.vaulttomcat.service.DatabaseService;
import com.example.vaulttomcat.service.VaultSecretService;
import jakarta.servlet.ServletException;
import jakarta.servlet.annotation.WebServlet;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;

/**
 * Main page Servlet
 */
public class HomeServlet extends HttpServlet {
  private static final Logger logger = LoggerFactory.getLogger(HomeServlet.class);

  @Override
  protected void doGet(HttpServletRequest request, HttpServletResponse response)
      throws ServletException, IOException {

    logger.info("🚀 Starting Vault Tomcat Web Application");

    try {
      // Get service objects
      VaultSecretService vaultSecretService = (VaultSecretService) getServletContext()
          .getAttribute("vaultSecretService");
      DatabaseService databaseService = (DatabaseService) getServletContext().getAttribute("databaseService");

      // Retrieve Vault secret information
      if (vaultSecretService != null) {
        try {
          Map<String, SecretInfo> secrets = vaultSecretService.getDisplaySecrets();

          // Add currently used Database credential information (do not issue new)
          String credentialSource = com.example.vaulttomcat.config.VaultConfig.getDatabaseCredentialSource();

          // In static mode, dbStatic is already retrieved in getAllSecrets(), so don't add duplicate
          if (!"static".equals(credentialSource)) {
            SecretInfo currentDbCredential = vaultSecretService.getCurrentDatabaseDynamicSecret();
            if (currentDbCredential != null) {
              if ("dynamic".equals(credentialSource)) {
                secrets.put("dbDynamic", currentDbCredential);
              } else if ("kv".equals(credentialSource)) {
                secrets.put("dbKv", currentDbCredential);
              }
            }
          }

          // Add logs for debugging
          logger.info("🔍 Current credential source: {}", credentialSource);
          logger.info("🔍 secrets Map keys: {}", secrets.keySet());
          for (Map.Entry<String, SecretInfo> entry : secrets.entrySet()) {
            logger.info("🔍 Secret key: {}, type: {}, path: {}",
                entry.getKey(), entry.getValue().getType(), entry.getValue().getPath());
          }

          request.setAttribute("secrets", secrets);
          logger.info("✅ Vault secret information loaded: {} secrets (including Database credentials)", secrets.size());
        } catch (Exception e) {
          logger.warn("⚠️ Vault secret fetch failed: {}", e.getMessage());
          request.setAttribute("vaultError", "Vault secret fetch failed: " + e.getMessage());
        }
      } else {
        logger.warn("⚠️ VaultSecretService is not initialized");
        request.setAttribute("vaultError", "Vault service is not initialized");
      }

      // Test database connection
      if (databaseService != null) {
        try {
          logger.info("🔍 Starting database connection test");
          Map<String, Object> dbConnection = databaseService.testConnection();
          logger.info("🔍 Database connection test completed: {}", dbConnection.get("status"));
          request.setAttribute("dbConnection", dbConnection);

          // Database statistics
          logger.info("🔍 Starting database statistics retrieval");
          Map<String, Object> dbStats = databaseService.getDatabaseStats();
          logger.info("🔍 Database statistics retrieval completed");
          request.setAttribute("dbStats", dbStats);
        } catch (Exception e) {
          logger.warn("⚠️ Database connection test failed: {}", e.getMessage());
          Map<String, Object> errorResult = new HashMap<>();
          errorResult.put("status", "error");
          errorResult.put("error", e.getMessage());
          request.setAttribute("dbConnection", errorResult);
        }
      } else {
        logger.warn("⚠️ DatabaseService is not initialized");
        Map<String, Object> errorResult = new HashMap<>();
        errorResult.put("status", "error");
        errorResult.put("error", "Database service is not initialized");
        request.setAttribute("dbConnection", errorResult);
      }

      logger.info("✅ Main page data load completed");

    } catch (Exception e) {
      logger.error("❌ Main page data load failed: {}", e.getMessage());
      request.setAttribute("error", e.getMessage());
    }

    // Forward to JSP
    request.getRequestDispatcher("/WEB-INF/jsp/index.jsp").forward(request, response);
  }
}
