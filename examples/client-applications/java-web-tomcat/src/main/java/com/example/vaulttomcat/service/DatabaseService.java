package com.example.vaulttomcat.service;

import com.example.vaulttomcat.config.DatabaseConfig;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.sql.Connection;
import java.sql.DatabaseMetaData;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.HashMap;
import java.util.Map;

/**
 * Database Service Class
 * Connects to Database using credentials from Vault and retrieves statistics information
 */
public class DatabaseService {
  private static final Logger logger = LoggerFactory.getLogger(DatabaseService.class);

  /**
   * Test database connection
   */
  public Map<String, Object> testConnection() {
    logger.info("=== Database Connection Test Started ===");
    Map<String, Object> result = new HashMap<>();

    try (Connection connection = DatabaseConfig.getConnection()) {
      logger.info("Connection obtained successfully");

      DatabaseMetaData metaData = connection.getMetaData();

      result.put("status", "success");
      result.put("database_product", metaData.getDatabaseProductName());
      result.put("database_version", metaData.getDatabaseProductVersion());
      result.put("driver_name", metaData.getDriverName());
      result.put("driver_version", metaData.getDriverVersion());
      result.put("url", metaData.getURL());
      result.put("username", metaData.getUserName());

      logger.info("✅ Database connection successful");
      logger.info("🗄️ Database Info: {} {}",
          metaData.getDatabaseProductName(), metaData.getDatabaseProductVersion());

      // Log result data
      logger.info("📊 Database Connection Result: {}", result);

    } catch (SQLException e) {
      logger.error("❌ Database connection failed: {}", e.getMessage());
      result.put("status", "error");
      result.put("error", e.getMessage());
    } catch (Exception e) {
      logger.error("❌ Unexpected error during database connection: {}", e.getMessage());
      result.put("status", "error");
      result.put("error", "Unexpected error: " + e.getMessage());
    }

    logger.info("=== Database Connection Test Completed ===");
    return result;
  }

  /**
   * Get database statistics information
   */
  public Map<String, Object> getDatabaseStats() {
    logger.info("=== Database Stats Query ===");
    Map<String, Object> stats = new HashMap<>();

    try (Connection connection = DatabaseConfig.getConnection()) {
      DatabaseMetaData metaData = connection.getMetaData();

      // Connection Pool status
      Map<String, Object> poolStatus = DatabaseConfig.getPoolStatus();
      stats.putAll(poolStatus);

      // Database limit information
      stats.put("max_connections", metaData.getMaxConnections());
      stats.put("max_columns_in_table", metaData.getMaxColumnsInTable());
      stats.put("max_columns_in_index", metaData.getMaxColumnsInIndex());
      stats.put("max_columns_in_select", metaData.getMaxColumnsInSelect());

      // Get table count
      try (ResultSet tables = metaData.getTables(null, null, "%", new String[] { "TABLE" })) {
        int tableCount = 0;
        while (tables.next()) {
          tableCount++;
        }
        stats.put("table_count", tableCount);
      }

      logger.info("✅ Database statistics fetch successful");
      logger.info("📊 Database Stats: {}", stats);

    } catch (SQLException e) {
      logger.error("❌ Database statistics fetch failed: {}", e.getMessage());
      stats.put("error", e.getMessage());
    }

    return stats;
  }

  /**
   * Get table list
   */
  public Map<String, Object> getTables() {
    logger.info("=== Database Tables Query ===");
    Map<String, Object> result = new HashMap<>();

    try (Connection connection = DatabaseConfig.getConnection()) {
      DatabaseMetaData metaData = connection.getMetaData();

      try (ResultSet tables = metaData.getTables(null, null, "%", new String[] { "TABLE" })) {
        int tableCount = 0;
        while (tables.next()) {
          tableCount++;
        }
        result.put("table_count", tableCount);
        result.put("status", "success");
      }

      logger.info("✅ Database table fetch successful");

    } catch (SQLException e) {
      logger.error("❌ Database table fetch failed: {}", e.getMessage());
      result.put("status", "error");
      result.put("error", e.getMessage());
    }

    return result;
  }
}
