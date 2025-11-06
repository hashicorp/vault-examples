package com.example.vaulttomcat.model;

import java.util.Date;
import java.util.Map;

/**
 * Model class containing Vault secret information
 */
public class SecretInfo {
  private String type;
  private String path;
  private Map<String, Object> data;
  private String version;
  private Long ttl;
  private String leaseId;
  private Boolean renewable;
  private Date lastUpdated;

  public SecretInfo() {
    this.lastUpdated = new Date();
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

  public Boolean getRenewable() {
    return renewable;
  }

  public void setRenewable(Boolean renewable) {
    this.renewable = renewable;
  }

  public Date getLastUpdated() {
    return lastUpdated;
  }

  public void setLastUpdated(Date lastUpdated) {
    this.lastUpdated = lastUpdated;
  }

  @Override
  public String toString() {
    return "SecretInfo{" +
        "type='" + type + '\'' +
        ", path='" + path + '\'' +
        ", version='" + version + '\'' +
        ", ttl=" + ttl +
        ", renewable=" + renewable +
        ", lastUpdated=" + lastUpdated +
        '}';
  }
}
