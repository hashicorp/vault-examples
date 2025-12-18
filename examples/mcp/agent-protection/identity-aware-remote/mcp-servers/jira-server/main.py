"""
Jira MCP Server using FastMCP
Handles MCP requests and retrieves credentials from Vault
"""
import os
import json
import base64
import httpx
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
MOCK_JIRA_URL = os.getenv("MOCK_JIRA_URL", "http://localhost:8001")

# Initialize FastMCP server
mcp = FastMCP("Jira MCP Server")


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
                # Entity name is set to username (alice, bob) via pre-created entities
                lookup_response = await client.get(
                    f"{self.vault_addr}/v1/auth/token/lookup-self",
                    headers={"X-Vault-Token": vault_token}
                )
                lookup_response.raise_for_status()
                lookup_data = lookup_response.json()["data"]
                
                # Extract entity name (which is the username for pre-created entities)
                # First try to get entity_name from token lookup or JWT
                entity_id = lookup_data.get("entity_id")
                print(f"[DEBUG] get_credentials - Token lookup - entity_id: {entity_id}", flush=True)
                entity_name = None
                
                # Try to get entity_name from JWT first (username)
                _, user_info = extract_user_id_from_jwt(user_jwt)
                entity_name = user_info.get("preferred_username", "unknown")
                print(f"[DEBUG] get_credentials - Using entity name from JWT: {entity_name}", flush=True)
                
                # Fetch entity information using entity name (not entity ID)
                if entity_name:
                    try:
                        print(f"[DEBUG] get_credentials - Fetching entity info from entity name: {entity_name}", flush=True)
                        entity_response = await client.get(
                            f"{self.vault_addr}/v1/identity/entity/name/{entity_name}",
                            headers={"X-Vault-Token": vault_token}
                        )
                        print(f"[DEBUG] get_credentials - Entity response status: {entity_response.status_code}", flush=True)
                        if entity_response.status_code == 200:
                            entity_data = entity_response.json().get("data", {})
                            # Verify the entity name matches
                            fetched_name = entity_data.get("name")
                            if fetched_name:
                                entity_name = fetched_name
                                print(f"[DEBUG] get_credentials - Verified entity name: {entity_name}", flush=True)
                        else:
                            print(f"[DEBUG] get_credentials - Failed to fetch entity: {entity_response.status_code}, response: {entity_response.text[:200]}", flush=True)
                    except Exception as e:
                        print(f"[DEBUG] get_credentials - Error fetching entity name: {e}", flush=True)
                        import traceback
                        traceback.print_exc()
                        pass
                
                print(f"[DEBUG] get_credentials - Final entity_name to use: {entity_name}", flush=True)
                
                # Get user-specific credentials from Vault using entity name (username)
                creds_response = await client.get(
                    f"{self.vault_addr}/v1/secret/data/users/{entity_name}/jira",
                    headers={"X-Vault-Token": vault_token}
                )
                
                if creds_response.status_code == 404:
                    raise ValueError(f"Secret not found at path: secret/data/users/{entity_name}/jira")
                
                creds_response.raise_for_status()
                credentials = creds_response.json()["data"]["data"]
                return credentials, entity_name
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Extract entity name from error context if possible
                entity_name = "unknown"
                try:
                    # Try to get entity name from the request URL
                    if "/users/" in str(e.request.url):
                        parts = str(e.request.url).split("/users/")
                        if len(parts) > 1:
                            entity_name = parts[1].split("/")[0]
                except:
                    # If we can't extract from URL, try to get from the lookup we did earlier
                    # But we don't have access to entity_name here, so we'll use "unknown"
                    pass
                # Re-raise with entity_name in the error message so debug_credentials can extract it
                raise ValueError(f"Secret not found at path: secret/data/users/{entity_name}/jira")
            raise
        except Exception as e:
            logger.error(f"Error getting credentials from Vault: {e}")
            raise
    
    async def get_vault_auth_info(self, user_jwt: str) -> Optional[dict]:
        """Get Vault authentication and entity information"""
        print(f"[DEBUG] get_vault_auth_info - Method called", flush=True)
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
                
                # Get token lookup info (includes entity information)
                lookup_response = await client.get(
                    f"{self.vault_addr}/v1/auth/token/lookup-self",
                    headers={"X-Vault-Token": vault_token}
                )
                lookup_response.raise_for_status()
                lookup_data = lookup_response.json()["data"]
                
                # Get entity name from JWT (username)
                entity_id = lookup_data.get("entity_id")
                print(f"[DEBUG] get_vault_auth_info - Token lookup - entity_id: {entity_id}", flush=True)
                entity_name = None
                
                # Try to get entity_name from JWT first (username)
                _, user_info = extract_user_id_from_jwt(user_jwt)
                entity_name = user_info.get("preferred_username", "unknown")
                print(f"[DEBUG] get_vault_auth_info - Using entity name from JWT: {entity_name}", flush=True)
                
                # Fetch entity information using entity name (not entity ID)
                if entity_name:
                    try:
                        print(f"[DEBUG] get_vault_auth_info - Fetching entity info from entity name: {entity_name}", flush=True)
                        entity_response = await client.get(
                            f"{self.vault_addr}/v1/identity/entity/name/{entity_name}",
                            headers={"X-Vault-Token": vault_token}
                        )
                        print(f"[DEBUG] get_vault_auth_info - Entity response status: {entity_response.status_code}", flush=True)
                        if entity_response.status_code == 200:
                            entity_data = entity_response.json().get("data", {})
                            # Verify the entity name matches
                            fetched_name = entity_data.get("name")
                            if fetched_name:
                                entity_name = fetched_name
                                print(f"[DEBUG] get_vault_auth_info - Verified entity name: {entity_name}", flush=True)
                        else:
                            print(f"[DEBUG] get_vault_auth_info - Failed to fetch entity: {entity_response.status_code}, response: {entity_response.text[:200]}", flush=True)
                    except Exception as e:
                        print(f"[DEBUG] get_vault_auth_info - Error fetching entity name: {e}", flush=True)
                        import traceback
                        traceback.print_exc()
                        pass
                
                print(f"[DEBUG] get_vault_auth_info - Final entity_name to return: {entity_name}", flush=True)
                
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
            print(f"[DEBUG] get_vault_auth_info - Exception: {e}", flush=True)
            import traceback
            traceback.print_exc()
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


async def call_jira_api(method: str, path: str, credentials: dict, **kwargs) -> dict:
    """Call Jira API with credentials"""
    url = f"{MOCK_JIRA_URL}{path}"
    auth = (credentials.get("username", "demo"), credentials.get("password", "demo"))
    
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method,
            url,
            auth=auth,
            **kwargs
        )
        response.raise_for_status()
        return response.json()


# Define tool functions first (before decorator)
async def _list_issues_impl(jql: Optional[str] = None) -> str:
    """List Jira issues. Optionally filter by JQL query."""
    credentials = await get_credentials()
    path = f"/rest/api/3/search?jql={jql}" if jql else "/rest/api/3/search"
    result = await call_jira_api("GET", path, credentials)
    return json.dumps(result, indent=2)


async def _get_issue_impl(issue_key: str) -> str:
    """Get a specific Jira issue by key (e.g., PROJ-1)."""
    credentials = await get_credentials()
    result = await call_jira_api("GET", f"/rest/api/3/issue/{issue_key}", credentials)
    return json.dumps(result, indent=2)


async def _create_issue_impl(summary: str, project: str, description: Optional[str] = None) -> str:
    """Create a new Jira issue."""
    credentials = await get_credentials()
    # Mock Jira API expects project as a string, not as {"key": project}
    result = await call_jira_api(
        "POST",
        "/rest/api/3/issue",
        credentials,
        json={
            "summary": summary,
            "description": description or "",
            "project": project  # Mock API expects string, not object
        }
    )
    return json.dumps(result, indent=2)


# Register with FastMCP
@mcp.tool()
async def list_issues(jql: Optional[str] = None) -> str:
    """List Jira issues. Optionally filter by JQL query."""
    return await _list_issues_impl(jql)


@mcp.tool()
async def get_issue(issue_key: str) -> str:
    """Get a specific Jira issue by key (e.g., PROJ-1)."""
    return await _get_issue_impl(issue_key)


@mcp.tool()
async def create_issue(summary: str, project: str, description: Optional[str] = None) -> str:
    """Create a new Jira issue."""
    return await _create_issue_impl(summary, project, description)


# Create FastAPI app for custom endpoints
from fastapi import FastAPI

app = FastAPI(title="Jira MCP Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Add middleware for authentication
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Middleware to extract JWT token from Authorization header"""
    # Skip authentication for health and debug endpoints
    if request.url.path in ["/health", "/debug/credentials"]:
        # Still extract JWT for debug endpoint, but don't require it for health
        if request.url.path == "/debug/credentials":
            authorization = request.headers.get("Authorization", "")
            if authorization.startswith("Bearer "):
                user_jwt = authorization.replace("Bearer ", "")
                user_jwt_context.set(user_jwt)
        return await call_next(request)
    
    authorization = request.headers.get("Authorization", "")
    if authorization.startswith("Bearer "):
        user_jwt = authorization.replace("Bearer ", "")
        user_jwt_context.set(user_jwt)
    else:
        raise HTTPException(status_code=401, detail="Bearer token required")
    
    response = await call_next(request)
    return response


# Add health endpoint
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "jira-mcp-server"}


# Add debug endpoint to get current user's credentials (for debugging)
@app.get("/debug/credentials")
async def debug_credentials(request: Request):
    """Debug endpoint to get current user's credentials and auth trace"""
    authorization = request.headers.get("Authorization", "")
    if authorization.startswith("Bearer "):
        user_jwt = authorization.replace("Bearer ", "")
        user_jwt_context.set(user_jwt)
        
        try:
            # Extract user ID from JWT
            user_id, user_info = extract_user_id_from_jwt(user_jwt)
            
            # Parse JWT details
            jwt_details = {}
            try:
                parts = user_jwt.split('.')
                if len(parts) >= 2:
                    payload = json.loads(base64.urlsafe_b64decode(parts[1] + '=='))
                    jwt_details = {
                        "sub": payload.get("sub"),
                        "iss": payload.get("iss"),
                        "aud": payload.get("aud"),
                        "exp": payload.get("exp"),
                        "iat": payload.get("iat"),
                        "preferred_username": payload.get("preferred_username"),
                        "email": payload.get("email"),
                        "groups": payload.get("groups", [])
                    }
            except:
                pass
            
            # Get Vault auth info
            print(f"[DEBUG] debug_credentials - Calling get_vault_auth_info", flush=True)
            vault_auth_info = await vault_client.get_vault_auth_info(user_jwt)
            print(f"[DEBUG] debug_credentials - get_vault_auth_info returned: {vault_auth_info}", flush=True)
            
            # Get credentials with error handling (this will determine the actual entity_name used)
            # get_credentials now returns (credentials, entity_name) tuple
            entity_name = None
            print(f"[DEBUG] debug_credentials - About to call get_credentials", flush=True)
            try:
                credentials, entity_name = await vault_client.get_credentials(user_jwt)
                print(f"[DEBUG] debug_credentials - get_credentials returned entity_name: {entity_name}", flush=True)
                secret_exists = True
                secret_error = None
                # Mask sensitive data
                masked_creds = {
                    "username": credentials.get("username", ""),
                    "password": "***" + credentials.get("password", "")[-4:] if credentials.get("password") else "",
                    "api_token": "***" + credentials.get("api_token", "")[-4:] if credentials.get("api_token") else ""
                }
            except ValueError as e:
                if "Secret not found" in str(e):
                    credentials = None
                    secret_exists = False
                    secret_error = "Secret not found"
                    masked_creds = None
                    # Extract entity_name from error message
                    if "secret/data/users/" in str(e):
                        try:
                            parts = str(e).split("secret/data/users/")
                            if len(parts) > 1:
                                entity_name = parts[1].split("/")[0]
                        except:
                            pass
                    # Fallback to vault_auth_info or JWT username
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
                # Fallback to vault_auth_info or JWT username
                if vault_auth_info and vault_auth_info.get("entity_name"):
                    entity_name = vault_auth_info.get("entity_name")
                else:
                    entity_name = user_info.get("preferred_username", user_id)
            
            # Final fallback if entity_name is still None
            if not entity_name:
                entity_name = user_info.get("preferred_username", user_id)
            
            return JSONResponse(content={
                "user_id": user_id,
                "user_info": user_info,
                "credentials": masked_creds,
                "vault_path": f"secret/data/users/{entity_name}/jira",
                "jwt_details": jwt_details,
                "vault_auth_info": vault_auth_info,
                "secret_exists": secret_exists,
                "secret_error": secret_error
            })
        except Exception as e:
            logger.error(f"Error getting debug credentials: {e}")
            return JSONResponse(content={
                "error": str(e)
            }, status_code=500)
    else:
        raise HTTPException(status_code=401, detail="Bearer token required")


# For backward compatibility, add /sse endpoint
@app.post("/sse")
async def sse_endpoint(request: Request):
    """SSE endpoint for backward compatibility"""
    # Extract JWT token
    authorization = request.headers.get("Authorization", "")
    if authorization.startswith("Bearer "):
        user_jwt = authorization.replace("Bearer ", "")
        user_jwt_context.set(user_jwt)
    else:
        raise HTTPException(status_code=401, detail="Bearer token required")
    
    body = await request.json()
    method = body.get("method", "")
    params = body.get("params", {})
    
    # Handle MCP methods by directly calling FastMCP tools
    if method == "tools/list":
        tools = [
            {
                "name": "list_issues",
                "description": "List Jira issues. Optionally filter by JQL query.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "jql": {"type": "string", "description": "JQL query"}
                    }
                }
            },
            {
                "name": "get_issue",
                "description": "Get a specific Jira issue by key (e.g., PROJ-1).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "issue_key": {"type": "string", "description": "Issue key (e.g., PROJ-1)"}
                    },
                    "required": ["issue_key"]
                }
            },
            {
                "name": "create_issue",
                "description": "Create a new Jira issue.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string"},
                        "project": {"type": "string"},
                        "description": {"type": "string"}
                    },
                    "required": ["summary", "project"]
                }
            }
        ]
        return JSONResponse(content={
            "jsonrpc": "2.0",
            "id": body.get("id"),
            "result": {"tools": tools}
        })
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        try:
            # Call the appropriate tool function implementation (not the wrapped FunctionTool)
            if tool_name == "list_issues":
                result = await _list_issues_impl(arguments.get("jql"))
            elif tool_name == "get_issue":
                result = await _get_issue_impl(arguments.get("issue_key"))
            elif tool_name == "create_issue":
                result = await _create_issue_impl(
                    arguments.get("summary"),
                    arguments.get("project"),
                    arguments.get("description")
                )
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
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            return JSONResponse(content={
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "error": {"code": -32603, "message": str(e)}
            }, status_code=500)
    else:
        return JSONResponse(content={
            "jsonrpc": "2.0",
            "id": body.get("id"),
            "error": {"code": -32601, "message": f"Unknown method: {method}"}
        }, status_code=400)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 3000)))
