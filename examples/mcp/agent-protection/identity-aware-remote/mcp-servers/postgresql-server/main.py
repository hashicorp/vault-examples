"""
PostgreSQL MCP Server using FastMCP
Handles MCP requests and retrieves credentials from Vault
"""
import os
import json
import base64
import httpx
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, Tuple
import logging
from contextvars import ContextVar
from fastmcp import FastMCP
from fastapi import Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Context variable to store user JWT token
user_jwt_context: ContextVar[Optional[str]] = ContextVar("user_jwt", default=None)

# Environment variables
VAULT_ADDR = os.getenv("VAULT_ADDR", "http://localhost:8200")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

# Initialize FastMCP server
mcp = FastMCP("PostgreSQL MCP Server")


class VaultClient:
    """Helper class for Vault operations"""
    
    def __init__(self):
        self.vault_addr = VAULT_ADDR
    
    async def get_credentials(self, user_jwt: str) -> Tuple[dict, str]:
        """Authenticate with Vault using JWT and retrieve user credentials
        Returns: (credentials_dict, entity_name)
        """
        try:
            async with httpx.AsyncClient() as client:
                # Login to Vault with JWT
                login_response = await client.post(
                    f"{self.vault_addr}/v1/auth/jwt/login",
                    json={"role": "user", "jwt": user_jwt}
                )
                login_response.raise_for_status()
                auth_data = login_response.json()["auth"]
                vault_token = auth_data["client_token"]
                
                # Get entity name from token lookup
                lookup_response = await client.get(
                    f"{self.vault_addr}/v1/auth/token/lookup-self",
                    headers={"X-Vault-Token": vault_token}
                )
                lookup_response.raise_for_status()
                lookup_data = lookup_response.json()["data"]
                
                # Extract entity name (which is the username for pre-created entities)
                entity_id = lookup_data.get("entity_id")
                entity_name = None
                
                # Try to get entity_name from JWT first (username)
                _, user_info = extract_user_id_from_jwt(user_jwt)
                entity_name = user_info.get("preferred_username", "unknown")
                logger.info(f"Using entity name from JWT: {entity_name}")
                
                # Fetch entity information using entity name
                if entity_name:
                    try:
                        entity_response = await client.get(
                            f"{self.vault_addr}/v1/identity/entity/name/{entity_name}",
                            headers={"X-Vault-Token": vault_token}
                        )
                        if entity_response.status_code == 200:
                            entity_data = entity_response.json().get("data", {})
                            fetched_name = entity_data.get("name")
                            if fetched_name:
                                entity_name = fetched_name
                                logger.info(f"Verified entity name: {entity_name}")
                    except Exception as e:
                        logger.error(f"Error fetching entity name: {e}")
                        pass
                
                # Get database credentials from Database secrets engine using role name (entity_name)
                # The role name matches the entity name (alice, bob)
                creds_response = await client.get(
                    f"{self.vault_addr}/v1/database/creds/{entity_name}",
                    headers={"X-Vault-Token": vault_token}
                )
                
                if creds_response.status_code == 404:
                    raise ValueError(f"Database role not found: {entity_name}")
                
                creds_response.raise_for_status()
                creds_data = creds_response.json()["data"]
                
                # Database secrets engine returns username and password
                # We need to construct the full connection info
                credentials = {
                    "host": POSTGRES_HOST,
                    "port": POSTGRES_PORT,
                    "database": "mcp_demo",
                    "username": creds_data.get("username"),
                    "password": creds_data.get("password")
                }
                
                return credentials, entity_name
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting credentials: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error getting credentials: {e}")
            raise
    
    async def get_vault_auth_info(self, user_jwt: str) -> Optional[dict]:
        """Get Vault authentication and entity information"""
        try:
            async with httpx.AsyncClient() as client:
                # Login to Vault with JWT
                login_response = await client.post(
                    f"{self.vault_addr}/v1/auth/jwt/login",
                    json={"role": "user", "jwt": user_jwt}
                )
                login_response.raise_for_status()
                auth_data = login_response.json()["auth"]
                vault_token = auth_data["client_token"]
                
                # Get token lookup info
                lookup_response = await client.get(
                    f"{self.vault_addr}/v1/auth/token/lookup-self",
                    headers={"X-Vault-Token": vault_token}
                )
                lookup_response.raise_for_status()
                lookup_data = lookup_response.json()["data"]
                
                # Get entity name
                entity_id = lookup_data.get("entity_id")
                entity_name = None
                
                _, user_info = extract_user_id_from_jwt(user_jwt)
                entity_name = user_info.get("preferred_username", "unknown")
                
                # Fetch entity information using entity name
                if entity_name:
                    try:
                        entity_response = await client.get(
                            f"{self.vault_addr}/v1/identity/entity/name/{entity_name}",
                            headers={"X-Vault-Token": vault_token}
                        )
                        if entity_response.status_code == 200:
                            entity_data = entity_response.json().get("data", {})
                            fetched_name = entity_data.get("name")
                            if fetched_name:
                                entity_name = fetched_name
                    except:
                        pass
                
                return {
                    "entity_id": entity_id,
                    "entity_name": entity_name,
                    "policies": lookup_data.get("policies", []),
                    "metadata": lookup_data.get("meta", {}),
                    "aliases": lookup_data.get("aliases", []),
                    "lease_duration": auth_data.get("lease_duration"),
                    "renewable": auth_data.get("renewable", False)
                }
        except Exception as e:
            logger.error(f"Error getting Vault auth info: {e}")
            return None


vault_client = VaultClient()


def extract_user_id_from_jwt(user_jwt: str) -> Tuple[str, dict]:
    """Extract user ID and info from JWT token"""
    try:
        parts = user_jwt.split('.')
        if len(parts) >= 2:
            payload = json.loads(base64.urlsafe_b64decode(parts[1] + '=='))
            user_id = payload.get('sub', 'default')
            user_info = {
                "sub": user_id,
                "preferred_username": payload.get('preferred_username', 'unknown'),
                "email": payload.get('email', 'unknown')
            }
            return user_id, user_info
    except:
        pass
    return 'default', {"sub": "default"}


async def get_credentials() -> dict:
    """Get credentials for the current user"""
    user_jwt = user_jwt_context.get()
    if not user_jwt:
        raise ValueError("No JWT token found in context")
    credentials, _ = await vault_client.get_credentials(user_jwt)
    return credentials


def get_db_connection(credentials: dict):
    """Create PostgreSQL connection using credentials"""
    conn = psycopg2.connect(
        host=credentials.get("host", POSTGRES_HOST),
        port=int(credentials.get("port", POSTGRES_PORT)),
        database=credentials.get("database", "mcp_demo"),
        user=credentials.get("username", "postgres"),
        password=credentials.get("password", "postgres123")
    )
    return conn


# Define tool functions
async def _execute_query_impl(query: str) -> str:
    """Execute a SQL query and return results."""
    credentials = await get_credentials()
    conn = get_db_connection(credentials)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query)
            if query.strip().upper().startswith(('SELECT', 'WITH')):
                results = cursor.fetchall()
                # Convert to list of dicts for JSON serialization
                return json.dumps([dict(row) for row in results], indent=2, default=str)
            else:
                conn.commit()
                return json.dumps({"message": "Query executed successfully", "rows_affected": cursor.rowcount}, indent=2)
    except Exception as e:
        conn.rollback()
        raise ValueError(f"Database error: {str(e)}")
    finally:
        conn.close()


async def _list_tables_impl() -> str:
    """List all tables in the database."""
    credentials = await get_credentials()
    conn = get_db_connection(credentials)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT table_name, table_schema
                FROM information_schema.tables
                WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                ORDER BY table_schema, table_name
            """)
            results = cursor.fetchall()
            return json.dumps([dict(row) for row in results], indent=2, default=str)
    except Exception as e:
        raise ValueError(f"Database error: {str(e)}")
    finally:
        conn.close()


async def _describe_table_impl(table_name: str) -> str:
    """Describe the schema of a specific table."""
    credentials = await get_credentials()
    conn = get_db_connection(credentials)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT 
                    column_name,
                    data_type,
                    character_maximum_length,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position
            """, (table_name,))
            results = cursor.fetchall()
            if not results:
                raise ValueError(f"Table '{table_name}' not found")
            return json.dumps([dict(row) for row in results], indent=2, default=str)
    except Exception as e:
        raise ValueError(f"Database error: {str(e)}")
    finally:
        conn.close()


# Register with FastMCP
@mcp.tool()
async def execute_query(query: str) -> str:
    """Execute a SQL query and return results. Use SELECT for queries, INSERT/UPDATE/DELETE for modifications."""
    return await _execute_query_impl(query)


@mcp.tool()
async def list_tables() -> str:
    """List all tables in the database."""
    return await _list_tables_impl()


@mcp.tool()
async def describe_table(table_name: str) -> str:
    """Describe the schema of a specific table. Returns column names, types, and constraints."""
    return await _describe_table_impl(table_name)


# Create FastAPI app for custom endpoints
from fastapi import FastAPI

app = FastAPI(title="PostgreSQL MCP Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def auth_middleware(request: Request, call_next):
    """Middleware to extract JWT token from Authorization header"""
    # Skip authentication for health and debug endpoints
    if request.url.path in ["/health", "/debug/credentials"]:
        return await call_next(request)
    
    authorization = request.headers.get("Authorization", "")
    if authorization.startswith("Bearer "):
        token = authorization[7:]
        user_jwt_context.set(token)
    else:
        # For SSE endpoint, try to get token from query params or header
        if request.url.path == "/sse":
            # Allow SSE without auth for now (will be handled in endpoint)
            pass
    
    response = await call_next(request)
    return response


app.middleware("http")(auth_middleware)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "postgresql-mcp-server"}


@app.get("/debug/credentials")
async def debug_credentials(request: Request):
    """Debug endpoint to get current user's credentials and auth trace"""
    authorization = request.headers.get("Authorization", "")
    if authorization.startswith("Bearer "):
        user_jwt = authorization[7:]
    else:
        return JSONResponse(
            status_code=401,
            content={"error": "No authorization token provided"}
        )
    
    user_id, user_info = extract_user_id_from_jwt(user_jwt)
    vault_auth_info = await vault_client.get_vault_auth_info(user_jwt)
    
    jwt_details = {
        "sub": user_info.get("sub"),
        "preferred_username": user_info.get("preferred_username"),
        "email": user_info.get("email")
    }
    
    # Get credentials with error handling
    entity_name = None
    try:
        credentials, entity_name = await vault_client.get_credentials(user_jwt)
        secret_exists = True
        secret_error = None
        # Mask sensitive data
        masked_creds = {
            "host": credentials.get("host", ""),
            "port": credentials.get("port", ""),
            "database": credentials.get("database", ""),
            "username": credentials.get("username", ""),
            "password": "***" + credentials.get("password", "")[-4:] if credentials.get("password") else ""
        }
    except ValueError as e:
        if "Database role not found" in str(e) or "not found" in str(e).lower():
            credentials = None
            secret_exists = False
            secret_error = "Database role not found"
            masked_creds = None
            # Extract entity_name from error message
            if "role not found:" in str(e):
                try:
                    parts = str(e).split("role not found: ")
                    if len(parts) > 1:
                        entity_name = parts[1].strip()
                except:
                    pass
            if not entity_name:
                if vault_auth_info and vault_auth_info.get("entity_name"):
                    entity_name = vault_auth_info.get("entity_name")
                else:
                    entity_name = user_info.get("preferred_username", user_id)
        else:
            raise
    except Exception as e:
        credentials = None
        secret_exists = False
        secret_error = str(e)
        masked_creds = None
        if vault_auth_info and vault_auth_info.get("entity_name"):
            entity_name = vault_auth_info.get("entity_name")
        else:
            entity_name = user_info.get("preferred_username", user_id)
    
    if not entity_name:
        entity_name = user_info.get("preferred_username", user_id)
    
    return JSONResponse(content={
        "user_id": user_id,
        "user_info": user_info,
        "credentials": masked_creds,
        "vault_path": f"database/creds/{entity_name}",
        "jwt_details": jwt_details,
        "vault_auth_info": vault_auth_info,
        "secret_exists": secret_exists,
        "secret_error": secret_error
    })


@app.post("/sse")
async def sse_endpoint(request: Request):
    """SSE endpoint for backward compatibility"""
    # Extract JWT token
    authorization = request.headers.get("Authorization", "")
    if authorization.startswith("Bearer "):
        user_jwt = authorization[7:]
        user_jwt_context.set(user_jwt)
    else:
        return JSONResponse(
            status_code=401,
            content={"jsonrpc": "2.0", "id": None, "error": {"code": -32000, "message": "No authorization token provided"}}
        )
    
    # Get request body
    try:
        body = await request.json()
    except:
        return JSONResponse(
            status_code=400,
            content={"jsonrpc": "2.0", "id": body.get("id"), "error": {"code": -32700, "message": "Invalid JSON in request body"}}
        )
    
    # Handle MCP protocol
    method = body.get("method", "")
    params = body.get("params", {})
    
    try:
        if method == "tools/list":
            tools = [
                {
                    "name": "execute_query",
                    "description": "Execute a SQL query and return results. Use SELECT for queries, INSERT/UPDATE/DELETE for modifications.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "SQL query to execute"
                            }
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "list_tables",
                    "description": "List all tables in the database.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "name": "describe_table",
                    "description": "Describe the schema of a specific table. Returns column names, types, and constraints.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "table_name": {
                                "type": "string",
                                "description": "Name of the table to describe"
                            }
                        },
                        "required": ["table_name"]
                    }
                }
            ]
            return JSONResponse(content={
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "result": {"tools": tools}
            })
        
        elif method == "tools/call":
            tool_name = params.get("name", "")
            tool_args = params.get("arguments", {})
            
            try:
                if tool_name == "execute_query":
                    result = await _execute_query_impl(tool_args.get("query", ""))
                elif tool_name == "list_tables":
                    result = await _list_tables_impl()
                elif tool_name == "describe_table":
                    result = await _describe_table_impl(tool_args.get("table_name", ""))
                else:
                    return JSONResponse(content={
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}
                    }, status_code=400)
                
                return JSONResponse(content={
                    "jsonrpc": "2.0",
                    "id": body.get("id"),
                    "result": {"content": [{"type": "text", "text": result}]}
                })
            except ValueError as e:
                return JSONResponse(content={
                    "jsonrpc": "2.0",
                    "id": body.get("id"),
                    "error": {"code": -32602, "message": str(e)}
                }, status_code=400)
        else:
            return JSONResponse(content={
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "error": {"code": -32601, "message": f"Unknown method: {method}"}
            }, status_code=400)
    except Exception as e:
        logger.error(f"Error handling request: {e}")
        return JSONResponse(content={
            "jsonrpc": "2.0",
            "id": body.get("id"),
            "error": {"code": -32603, "message": f"Internal server error: {str(e)}"}
        }, status_code=500)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "3000"))
    uvicorn.run(app, host="0.0.0.0", port=port)

