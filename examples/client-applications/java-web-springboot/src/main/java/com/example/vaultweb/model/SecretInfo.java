package com.example.vaultweb.model;

import java.time.LocalDateTime;
import java.util.Map;

/**
 * Secret Information Model Class
 * DTO containing secret information retrieved from Vault
 */
public class SecretInfo {

  private String type;
  private String path;
  private Map<String, Object> data;
  private LocalDateTime lastUpdated;
  private String version;
  private Long ttl;
  private String leaseId;
  private boolean renewable;

  public SecretInfo() {
    this.lastUpdated = LocalDateTime.now();
  }

  public SecretInfo(String type, String path, Map<String, Object> data) {
    this();
    this.type = type;
    this.path = path;
    this.data = data;
  }

  // Getters and Setters
  public String getType() {
    return type;
  }

  public void setType(String type) {
    this.type = type;
  }

  public String getPath() {
    return path;
  }

  public void setPath(String path) {
    this.path = path;
  }

  public Map<String, Object> getData() {
    return data;
  }

  public void setData(Map<String, Object> data) {
    this.data = data;
  }

  public LocalDateTime getLastUpdated() {
    return lastUpdated;
  }

  public void setLastUpdated(LocalDateTime lastUpdated) {
    this.lastUpdated = lastUpdated;
  }

  public String getVersion() {
    return version;
  }

  public void setVersion(String version) {
    this.version = version;
  }

  public Long getTtl() {
    return ttl;
  }

  public void setTtl(Long ttl) {
    this.ttl = ttl;
  }

  public String getLeaseId() {
    return leaseId;
  }

  public void setLeaseId(String leaseId) {
    this.leaseId = leaseId;
  }

  public boolean isRenewable() {
    return renewable;
  }

  public void setRenewable(boolean renewable) {
    this.renewable = renewable;
  }

  @Override
  public String toString() {
    return "SecretInfo{" +
        "type='" + type + '\'' +
        ", path='" + path + '\'' +
        ", lastUpdated=" + lastUpdated +
        ", version='" + version + '\'' +
        ", ttl=" + ttl +
        ", renewable=" + renewable +
        '}';
  }
}
