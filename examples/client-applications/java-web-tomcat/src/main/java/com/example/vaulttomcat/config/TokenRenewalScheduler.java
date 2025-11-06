package com.example.vaulttomcat.config;

import com.example.vaulttomcat.client.VaultClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

/**
 * Token Renewal Scheduler
 * Handles automatic renewal of orphan tokens received via AppRole.
 */
public class TokenRenewalScheduler {
  private static final Logger logger = LoggerFactory.getLogger(TokenRenewalScheduler.class);
  private static ScheduledExecutorService scheduler;
  private static VaultClient vaultClient;

  /**
   * Start Token Renewal Scheduler
   */
  public static void start(VaultClient client) {
    if (!VaultConfig.isTokenRenewalEnabled()) {
      logger.info("Token renewal is disabled");
      return;
    }

    vaultClient = client;
    scheduler = Executors.newSingleThreadScheduledExecutor();

    // Check if token renewal is needed every 10 seconds
    scheduler.scheduleAtFixedRate(() -> {
      try {
        if (vaultClient.shouldRenew()) {
          logger.info("Token renewal needed - attempting renewal...");
          boolean success = vaultClient.renewToken();

          if (success) {
            logger.info("✅ Token renewal successful - TTL: {}s",
                (vaultClient.getTokenExpiry() - System.currentTimeMillis()) / 1000);
          } else {
            logger.error("❌ Token renewal failed - shutting down application");
            shutdown();
            System.exit(1);
          }
        }
      } catch (Exception e) {
        logger.error("Token renewal scheduler error: {}", e.getMessage());
      }
    }, 10, 10, TimeUnit.SECONDS);

    logger.info("Token Renewal Scheduler started (checking every 10 seconds)");
  }

  /**
   * Shutdown Token Renewal Scheduler
   */
  public static void shutdown() {
    if (scheduler != null && !scheduler.isShutdown()) {
      scheduler.shutdown();
      logger.info("Token Renewal Scheduler shut down");
    }
  }
}
