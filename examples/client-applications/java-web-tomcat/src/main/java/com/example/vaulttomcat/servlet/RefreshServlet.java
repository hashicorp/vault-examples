/*
 * Copyright IBM Corp. 2021, 2026
 */

package com.example.vaulttomcat.servlet;

import com.example.vaulttomcat.model.SecretInfo;
import com.example.vaulttomcat.service.DatabaseService;
import com.example.vaulttomcat.service.VaultSecretService;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;

/**
 * Secret Renewal Servlet
 */
public class RefreshServlet extends HttpServlet {
  private static final Logger logger = LoggerFactory.getLogger(RefreshServlet.class);

  @Override
  protected void doGet(HttpServletRequest request, HttpServletResponse response)
      throws ServletException, IOException {

    logger.info("🔄 Secret renewal request");

    try {
      // Get service objects
      VaultSecretService vaultSecretService = (VaultSecretService) getServletContext()
          .getAttribute("vaultSecretService");
      DatabaseService databaseService = (DatabaseService) getServletContext().getAttribute("databaseService");

      // Renew Vault secret information
      if (vaultSecretService != null) {
        try {
          Map<String, SecretInfo> secrets = vaultSecretService.getAllSecrets();
          request.setAttribute("secrets", secrets);
          logger.info("✅ Vault secret information renewal completed: {} secrets", secrets.size());
        } catch (Exception e) {
          logger.warn("⚠️ Vault secret renewal failed: {}", e.getMessage());
          request.setAttribute("vaultError", "Vault secret renewal failed: " + e.getMessage());
        }
      } else {
        logger.warn("⚠️ VaultSecretService is not initialized");
        request.setAttribute("vaultError", "Vault service is not initialized");
      }

      // Renew database connection test
      if (databaseService != null) {
        try {
          logger.info("🔍 Starting database connection test renewal");
          Map<String, Object> dbConnection = databaseService.testConnection();
          logger.info("🔍 Database connection test renewal completed: {}", dbConnection.get("status"));
          request.setAttribute("dbConnection", dbConnection);

          // Renew database statistics
          logger.info("🔍 Starting database statistics renewal");
          Map<String, Object> dbStats = databaseService.getDatabaseStats();
          logger.info("🔍 Database statistics renewal completed");
          request.setAttribute("dbStats", dbStats);
        } catch (Exception e) {
          logger.warn("⚠️ Database connection test renewal failed: {}", e.getMessage());
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

      // Add renewal time
      request.setAttribute("refreshTime", new java.util.Date());
      logger.info("✅ Secret renewal completed");

    } catch (Exception e) {
      logger.error("❌ Secret renewal failed: {}", e.getMessage());
      request.setAttribute("error", e.getMessage());
    }

    // Forward to JSP
    request.getRequestDispatcher("/WEB-INF/jsp/index.jsp").forward(request, response);
  }
}
