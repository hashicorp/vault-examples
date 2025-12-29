package com.example.vaultweb.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.DatabaseMetaData;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Database Service Class
 * Connects to Database using credentials from Vault and retrieves table
 * information
 */
@Service
public class DatabaseService {

  private static final Logger logger = LoggerFactory.getLogger(DatabaseService.class);

  @Autowired
  private DataSource dataSource;

  /**
   * Test database connection
   */
  public Map<String, Object> testConnection() {
    logger.info("=== Database Connection Test Started ===");
    Map<String, Object> result = new HashMap<>();

    try {
      logger.info("Attempting to get connection from DataSource...");
      Connection connection = dataSource.getConnection();
      logger.info("Connection obtained successfully");

      DatabaseMetaData metaData = connection.getMetaData();

      result.put("status", "success");
      result.put("database_product", metaData.getDatabaseProductName());
      result.put("database_version", metaData.getDatabaseProductVersion());
      result.put("driver_name", metaData.getDriverName());
      result.put("driver_version", metaData.getDriverVersion());
      result.put("url", metaData.getURL());
      result.put("username", metaData.getUserName());

      logger.info("Database connection successful");
      logger.info("Database Info: {} {}",
          metaData.getDatabaseProductName(), metaData.getDatabaseProductVersion());

      // Log result data
      logger.info("Database Connection Result: {}", result);

      connection.close();
      logger.info("Connection closed successfully");

    } catch (SQLException e) {
      logger.error("Database connection failed: {}", e.getMessage());
      result.put("status", "error");
      result.put("error", e.getMessage());
    } catch (Exception e) {
      logger.error("Unexpected error during database connection: {}", e.getMessage());
      result.put("status", "error");
      result.put("error", "Unexpected error: " + e.getMessage());
    }

    logger.info("=== Database Connection Test Completed ===");
    return result;
  }

  /**
   * Get table list
   */
  public List<Map<String, Object>> getTables() {
    List<Map<String, Object>> tables = new ArrayList<>();

    try (Connection connection = dataSource.getConnection()) {
      logger.info("=== Database Tables Query ===");

      DatabaseMetaData metaData = connection.getMetaData();
      String[] tableTypes = { "TABLE", "VIEW" };

      try (ResultSet rs = metaData.getTables(null, null, "%", tableTypes)) {
        while (rs.next()) {
          Map<String, Object> table = new HashMap<>();
          table.put("table_name", rs.getString("TABLE_NAME"));
          table.put("table_type", rs.getString("TABLE_TYPE"));
          table.put("table_catalog", rs.getString("TABLE_CAT"));
          table.put("table_schema", rs.getString("TABLE_SCHEM"));
          table.put("remarks", rs.getString("REMARKS"));

          tables.add(table);
        }
      }

      logger.info("Table list fetch successful ({} tables)", tables.size());
      tables.forEach(table -> logger.info("Table: {} ({})",
          table.get("table_name"), table.get("table_type")));

    } catch (SQLException e) {
      logger.error("Table list fetch failed: {}", e.getMessage());
    }

    return tables;
  }

  /**
   * Get column information for a specific table
   */
  public List<Map<String, Object>> getTableColumns(String tableName) {
    List<Map<String, Object>> columns = new ArrayList<>();

    try (Connection connection = dataSource.getConnection()) {
      logger.info("=== Table Columns Query: {} ===", tableName);

      DatabaseMetaData metaData = connection.getMetaData();

      try (ResultSet rs = metaData.getColumns(null, null, tableName, "%")) {
        while (rs.next()) {
          Map<String, Object> column = new HashMap<>();
          column.put("column_name", rs.getString("COLUMN_NAME"));
          column.put("data_type", rs.getInt("DATA_TYPE"));
          column.put("type_name", rs.getString("TYPE_NAME"));
          column.put("column_size", rs.getInt("COLUMN_SIZE"));
          column.put("nullable", rs.getInt("NULLABLE"));
          column.put("column_def", rs.getString("COLUMN_DEF"));
          column.put("remarks", rs.getString("REMARKS"));

          columns.add(column);
        }
      }

      logger.info("Table column fetch successful: {} ({} columns)", tableName, columns.size());
      columns.forEach(column -> logger.info("Column: {} ({})",
          column.get("column_name"), column.get("type_name")));

    } catch (SQLException e) {
      logger.error("Table column fetch failed: {} - {}", tableName, e.getMessage());
    }

    return columns;
  }

  /**
   * Get database statistics
   */
  public Map<String, Object> getDatabaseStats() {
    Map<String, Object> stats = new HashMap<>();

    try (Connection connection = dataSource.getConnection()) {
      logger.info("=== Database Statistics ===");

      DatabaseMetaData metaData = connection.getMetaData();

      stats.put("database_product", metaData.getDatabaseProductName());
      stats.put("database_version", metaData.getDatabaseProductVersion());
      stats.put("driver_name", metaData.getDriverName());
      stats.put("driver_version", metaData.getDriverVersion());
      stats.put("url", metaData.getURL());
      stats.put("username", metaData.getUserName());
      stats.put("max_connections", metaData.getMaxConnections());
      stats.put("max_columns_in_table", metaData.getMaxColumnsInTable());
      stats.put("max_columns_in_index", metaData.getMaxColumnsInIndex());
      stats.put("max_columns_in_select", metaData.getMaxColumnsInSelect());

      // Table count
      List<Map<String, Object>> tables = getTables();
      stats.put("table_count", tables.size());

      logger.info("Database statistics fetch successful");
      logger.info("Database Stats: {} tables, {} max connections",
          tables.size(), metaData.getMaxConnections());

    } catch (SQLException e) {
      logger.error("Database statistics fetch failed: {}", e.getMessage());
      stats.put("error", e.getMessage());
    }

    return stats;
  }
}
