#!/bin/bash

set -e

echo "=========================================="
echo "Cleaning up Spring AI MCP Server"
echo "=========================================="
echo ""

echo "Step 1: Stopping and removing containers..."
docker-compose down -v

echo ""
echo "Step 2: Removing generated files..."
rm -f .env
rm -f inspector-config.json

echo ""
echo "Step 3: Cleaning build artifacts..."
mvn clean 2>/dev/null || echo "Maven clean skipped (Maven not available or not needed)"

echo ""
echo "=========================================="
echo "Cleanup completed!"
echo "=========================================="
echo ""
echo "Removed:"
echo "  - Docker containers and volumes"
echo "  - .env file"
echo "  - inspector-config.json file"
echo "  - Build artifacts (target/)"
echo ""
