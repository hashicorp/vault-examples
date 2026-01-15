#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Starting Vault setup..."

if ! docker-compose ps vault | grep -q "Up"; then
    echo "Starting Vault container..."
    docker-compose up -d vault
    
    echo "Waiting for Vault to be ready..."
    sleep 5
    
    max_attempts=30
    attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if docker-compose exec -T vault vault status > /dev/null 2>&1; then
            echo "Vault is ready!"
            break
        fi
        attempt=$((attempt + 1))
        echo "Waiting for Vault... ($attempt/$max_attempts)"
        sleep 2
    done
    
    if [ $attempt -eq $max_attempts ]; then
        echo "Error: Vault failed to start within expected time"
        exit 1
    fi
fi

echo "Running Vault initialization..."

VAULT_CONTAINER=$(docker-compose ps -q vault)
NETWORK_NAME=$(docker inspect "$VAULT_CONTAINER" --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}}{{end}}' | head -1)

docker run --rm \
    --network "$NETWORK_NAME" \
    -e VAULT_ADDR=http://vault:8200 \
    -e VAULT_TOKEN=myroot \
    -v "$SCRIPT_DIR/scripts/vault-init.sh:/vault-init.sh:ro" \
    -v "$SCRIPT_DIR:/workspace" \
    --workdir /workspace \
    hashicorp/vault:1.21.1 \
    /bin/sh /vault-init.sh

echo ""
echo "Step 3: Building application..."
mvn clean package -DskipTests

echo ""
echo "Step 4: Starting Spring Boot application and MCP Inspector..."
docker-compose up -d app mcp-inspector

echo ""
echo "Step 5: Waiting for application to be ready..."
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if curl -s http://localhost:8080/ > /dev/null 2>&1; then
        echo "Application is ready!"
        break
    fi
    attempt=$((attempt + 1))
    echo "Waiting for application... ($attempt/$max_attempts)"
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo "Warning: Application may not be ready yet. Please check manually."
fi

echo ""
echo "Step 6: Waiting for MCP Inspector to be ready..."
sleep 3
max_attempts=15
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if curl -s http://localhost:6274 > /dev/null 2>&1; then
        echo "MCP Inspector is ready!"
        break
    fi
    attempt=$((attempt + 1))
    echo "Waiting for MCP Inspector... ($attempt/$max_attempts)"
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo "Warning: MCP Inspector may not be ready yet. Please check manually."
fi

# Read API key from .env file
if [ -f .env ]; then
    API_KEY=$(grep MCP_API_KEY .env | cut -d'=' -f2)
else
    API_KEY="(not found)"
fi

echo ""
echo "=========================================="
echo "Setup completed!"
echo "=========================================="
echo ""
echo "Application is running at: http://localhost:8080"
echo "MCP Inspector is running at: http://localhost:6274"
echo ""
echo "Open your browser and navigate to:"
echo "  http://localhost:6274"
echo ""
echo "=========================================="
echo "Demo Credentials"
echo "=========================================="
echo "Role ID: demo-role-id-12345"
echo "Secret ID: demo-secret-id-67890"
echo "API Key: $API_KEY"
echo ""
echo "Vault Secret Path:"
echo "  Path: secret/mcp"
echo "  Key: api-key"
echo "  Read command: vault kv get -field=api-key secret/mcp"
echo "  Or via Docker: docker-compose exec vault vault kv get -field=api-key secret/mcp"
echo ""
echo "To test API key:"
echo "  curl -H \"X-API-KEY: $API_KEY\" http://localhost:8080/"
echo ""
echo "To stop all services:"
echo "  docker-compose down"
echo "=========================================="
