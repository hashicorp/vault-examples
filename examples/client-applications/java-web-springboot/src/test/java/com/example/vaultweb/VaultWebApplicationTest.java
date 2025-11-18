package com.example.vaultweb;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.TestPropertySource;

/**
 * Vault Spring Boot Web Application Test Class
 */
@SpringBootTest
@TestPropertySource(properties = {
    "spring.cloud.vault.enabled=false",
    "spring.datasource.url=jdbc:h2:mem:testdb",
    "spring.datasource.driver-class-name=org.h2.Driver"
})
class VaultWebApplicationTest {

    @Test
    void contextLoads() {
        // Test if Spring Boot application context loads successfully
    }
}
