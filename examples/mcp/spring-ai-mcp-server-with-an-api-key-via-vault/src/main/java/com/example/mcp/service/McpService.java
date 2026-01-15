package com.example.mcp.service;

import org.springaicommunity.mcp.annotation.McpResource;
import org.springaicommunity.mcp.annotation.McpTool;
import org.springaicommunity.mcp.annotation.McpToolParam;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

@Service
public class McpService {

    @McpTool(name = "get-server-info", description = "Get information about the MCP server")
    public Map<String, Object> getServerInfo() {
        Map<String, Object> info = new HashMap<>();
        info.put("name", "Spring AI MCP Server");
        info.put("version", "1.0.0");
        info.put("timestamp", LocalDateTime.now().toString());
        info.put("status", "running");
        return info;
    }

    @McpTool(name = "echo", description = "Echo back the provided message")
    public String echo(
            @McpToolParam(description = "Message to echo", required = true) String message) {
        return "Echo: " + message;
    }

    @McpResource(uri = "info://server", name = "Server Information")
    public String getServerResource() {
        return "Spring AI MCP Server with HashiCorp Vault Security";
    }
}
