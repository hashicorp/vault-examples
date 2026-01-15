package com.example.mcp.config;

import org.springframework.vault.core.VaultVersionedKeyValueOperations;
import org.springframework.vault.core.VaultOperations;
import org.springframework.vault.support.Versioned;
import org.springframework.stereotype.Component;
import jakarta.annotation.PostConstruct;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@Component
public class ApiKeyProperties {

    private static final Logger logger = LoggerFactory.getLogger(ApiKeyProperties.class);
    private final VaultOperations vaultOperations;
    private String apiKey;

    public ApiKeyProperties(VaultOperations vaultOperations) {
        this.vaultOperations = vaultOperations;
    }

    @PostConstruct
    public void init() {
        try {
            logger.info("Loading API key from Vault...");
            VaultVersionedKeyValueOperations kvOps = vaultOperations.opsForVersionedKeyValue("secret");

            // Read from secret/mcp (application-name path)
            // Vault path: secret/mcp
            // Key: api-key
            Versioned<Map<String, Object>> secret = kvOps.get("mcp");
            if (secret != null && secret.getData() != null) {
                Object apiKeyValue = secret.getData().get("api-key");
                if (apiKeyValue != null) {
                    this.apiKey = apiKeyValue.toString();
                    logger.info("API key loaded successfully from Vault. Length: {}", this.apiKey != null ? this.apiKey.length() : 0);
                } else {
                    logger.error("API key not found in Vault secret data at secret/mcp with key 'api-key'");
                }
            } else {
                logger.error("Vault secret not found or data is null at path secret/mcp");
            }
        } catch (Exception e) {
            logger.error("Failed to load API key from Vault", e);
            // Log error but don't fail startup
        }
    }

    public String getValue() {
        return apiKey;
    }
}
