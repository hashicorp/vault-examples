package com.example.mcp.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.Map;

@RestController
public class InfoController {

    @GetMapping("/")
    public Map<String, Object> info() {
        Map<String, Object> info = new HashMap<>();
        info.put("name", "Spring AI MCP Server");
        info.put("version", "1.0.0");
        info.put("status", "running");
        info.put("endpoints", Map.of(
                "mcp", "/mcp",
                "message", "/mcp/message"));
        info.put("authentication", "X-API-KEY header required");
        return info;
    }
}
