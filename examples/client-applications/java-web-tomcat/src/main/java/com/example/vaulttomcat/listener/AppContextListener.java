/*
 * Copyright IBM Corp. 2021, 2026
 */

package com.example.vaulttomcat.listener;

import com.example.vaulttomcat.client.VaultClient;
import com.example.vaulttomcat.config.DatabaseConfig;
import com.example.vaulttomcat.config.TokenRenewalScheduler;
import com.example.vaulttomcat.service.DatabaseService;
import com.example.vaulttomcat.service.VaultSecretService;
import jakarta.servlet.ServletContext;
import jakarta.servlet.ServletContextEvent;
import jakarta.servlet.ServletContextListener;
import jakarta.servlet.annotation.WebListener;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Application Initialization Listener
 * Initializes Vault client and Database Connection Pool when application starts
 */
@WebListener
public class AppContextListener implements ServletContextListener {
  private static final Logger logger = LoggerFactory.getLogger(AppContextListener.class);

  @Override
  public void contextInitialized(ServletContextEvent sce) {
    System.out.println("=== Vault Tomcat Web Application Starting ===");
    logger.info("=== Vault Tomcat Web Application Starting ===");

    ServletContext context = sce.getServletContext();

    try {
      // 1. Initialize Vault client
      System.out.println("Initializing Vault client...");
      logger.info("Initializing Vault client...");
      VaultSecretService vaultSecretService = new VaultSecretService();
      context.setAttribute("vaultSecretService", vaultSecretService);

      // Start Token Renewal Scheduler
      VaultClient vaultClient = vaultSecretService.getVaultClient();
      TokenRenewalScheduler.start(vaultClient);

      System.out.println("✅ Vault client initialization completed");
      logger.info("✅ Vault client initialization completed");

      // 2. Initialize Database Connection Pool
      System.out.println("Initializing Database Connection Pool...");
      logger.info("Initializing Database Connection Pool...");
      try {
        DatabaseConfig.initialize(vaultSecretService);
        System.out.println("✅ Database Connection Pool initialization completed");
        logger.info("✅ Database Connection Pool initialization completed");
      } catch (Exception e) {
        System.out.println("⚠️ Database Connection Pool initialization failed: " + e.getMessage());
        logger.warn("⚠️ Database Connection Pool initialization failed: {}", e.getMessage());
        logger.warn("Database functionality will be limited");
      }

      // 3. Initialize Database service
      System.out.println("Initializing Database service...");
      logger.info("Initializing Database service...");
      DatabaseService databaseService = new DatabaseService();
      context.setAttribute("databaseService", databaseService);
      System.out.println("✅ Database service initialization completed");
      logger.info("✅ Database service initialization completed");

      System.out.println("🎉 Vault Tomcat Web Application initialization completed");
      logger.info("🎉 Vault Tomcat Web Application initialization completed");

    } catch (Exception e) {
      System.out.println("❌ Application initialization failed: " + e.getMessage());
      logger.error("❌ Application initialization failed: {}", e.getMessage(), e);
      // Allow application to start even if initialization fails
      System.out.println("⚠️ Starting application in limited mode");
      logger.warn("⚠️ Starting application in limited mode");
    }
  }

  @Override
  public void contextDestroyed(ServletContextEvent sce) {
    logger.info("=== Vault Tomcat Web Application Shutting Down ===");

    ServletContext context = sce.getServletContext();

    try {
      // 1. Shutdown Token Renewal Scheduler
      TokenRenewalScheduler.shutdown();

      // 2. Cleanup Vault service
      VaultSecretService vaultSecretService = (VaultSecretService) context.getAttribute("vaultSecretService");
      if (vaultSecretService != null) {
        vaultSecretService.close();
        logger.info("✅ Vault service cleanup completed");
      }

      // 3. Cleanup Database Connection Pool
      DatabaseConfig.shutdown();
      logger.info("✅ Database Connection Pool cleanup completed");

      logger.info("🎉 Vault Tomcat Web Application shutdown completed");
      System.out.println("🎉 Vault Tomcat Web Application shutdown completed");

    } catch (Exception e) {
      logger.error("❌ Error occurred during application shutdown: {}", e.getMessage(), e);
    }
  }
}
