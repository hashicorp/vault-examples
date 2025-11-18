package com.example.vaultweb;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * Spring Boot Vault Web Application Main Class
 * 
 * Main features:
 * - Secret management through Spring Cloud Vault Config
 * - AppRole authentication
 * - Automatic token renewal
 * - KV, Database Dynamic/Static secret retrieval
 * - Web UI provided
 */
@SpringBootApplication
@RefreshScope
@EnableScheduling
public class VaultWebApplication {

  public static void main(String[] args) {
    System.setProperty("spring.profiles.active", "dev");
    SpringApplication.run(VaultWebApplication.class, args);
  }
}
