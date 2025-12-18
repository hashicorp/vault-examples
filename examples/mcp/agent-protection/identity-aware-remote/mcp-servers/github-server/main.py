"""
Github MCP Server using FastMCP
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
MOCK_GITHUB_URL = os.getenv("MOCK_GITHUB_URL", "http://localhost:8002")

# Initialize FastMCP server
mcp = FastMCP("Github MCP Server")


class VaultClient:
    """Helper class for Vault operations"""
    
    def __init__(self):
        self.vault_addr = VAULT_ADDR
    
    async def get_credentials(self, user_jwt: str) -> dict:
        """Authenticate with Vault using JWT and retrieve user credentials"""
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
                # First try to get entity_name from JWT (username)
                entity_id = lookup_data.get("entity_id")
                entity_name = None
                
                # Try to get entity_name from JWT first (username)
                _, user_info = extract_user_id_from_jwt(user_jwt)
                entity_name = user_info.get("preferred_username", "unknown")
                logger.info(f"Using entity name from JWT: {entity_name}")
                
                # Fetch entity information using entity name (not entity ID)
                if entity_name:
                    try:
                        entity_response = await client.get(
                            f"{self.vault_addr}/v1/identity/entity/name/{entity_name}",
                            headers={"X-Vault-Token": vault_token}
                        )
                        if entity_response.status_code == 200:
                            entity_data = entity_response.json().get("data", {})
                            # Verify the entity name matches
                            fetched_name = entity_data.get("name")
                            if fetched_name:
                                entity_name = fetched_name
                                logger.info(f"Verified entity name: {entity_name}")
                        else:
                            logger.warning(f"Failed to fetch entity: {entity_response.status_code}")
                    except Exception as e:
                        logger.error(f"Error fetching entity name: {e}")
                        pass
                
                # Get user-specific credentials from Vault using entity name (username)
                creds_response = await client.get(
                    f"{self.vault_addr}/v1/secret/data/users/{entity_name}/github",
                    headers={"X-Vault-Token": vault_token}
                )
                
                if creds_response.status_code == 404:
                    raise ValueError(f"Secret not found at path: secret/data/users/{entity_name}/github")
                
                creds_response.raise_for_status()
                credentials = creds_response.json()["data"]["data"]
                return credentials
                
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
                    pass
                # Re-raise with entity_name in the error message so debug_credentials can extract it
                raise ValueError(f"Secret not found at path: secret/data/users/{entity_name}/github")
            raise
        except Exception as e:
            logger.error(f"Error getting credentials from Vault: {e}")
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
                
                # Get token lookup info (includes entity information)
                lookup_response = await client.get(
                    f"{self.vault_addr}/v1/auth/token/lookup-self",
                    headers={"X-Vault-Token": vault_token}
                )
                lookup_response.raise_for_status()
                lookup_data = lookup_response.json()["data"]
                
                # Get entity name from JWT (username)
                entity_id = lookup_data.get("entity_id")
                entity_name = None
                
                # Try to get entity_name from JWT first (username)
                _, user_info = extract_user_id_from_jwt(user_jwt)
                entity_name = user_info.get("preferred_username", "unknown")
                
                # Fetch entity information using entity name (not entity ID)
                if entity_name:
                    try:
                        entity_response = await client.get(
                            f"{self.vault_addr}/v1/identity/entity/name/{entity_name}",
                            headers={"X-Vault-Token": vault_token}
                        )
                        if entity_response.status_code == 200:
                            entity_data = entity_response.json().get("data", {})
                            # Verify the entity name matches
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
    return await vault_client.get_credentials(user_jwt)


async def call_github_api(method: str, path: str, credentials: dict, **kwargs) -> dict:
    """Call Github API with credentials"""
    url = f"{MOCK_GITHUB_URL}{path}"
    token = credentials.get("token", "demo-token")
    
    headers = kwargs.get("headers", {})
    headers["Authorization"] = f"Bearer {token}"
    kwargs["headers"] = headers
    
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method,
            url,
            **kwargs
        )
        response.raise_for_status()
        return response.json()


# Define tool functions first (before decorator)
async def _list_repos_impl() -> str:
    """List GitHub repositories."""
    credentials = await get_credentials()
    result = await call_github_api("GET", "/user/repos", credentials)
    return json.dumps(result, indent=2)


async def _get_repo_impl(owner: str, repo: str) -> str:
    """Get a specific repository."""
    credentials = await get_credentials()
    result = await call_github_api("GET", f"/repos/{owner}/{repo}", credentials)
    return json.dumps(result, indent=2)


async def _list_issues_impl(owner: str, repo: str, state: Optional[str] = "open") -> str:
    """List issues in a repository."""
    credentials = await get_credentials()
    result = await call_github_api("GET", f"/repos/{owner}/{repo}/issues?state={state}", credentials)
    return json.dumps(result, indent=2)


async def _create_issue_impl(owner: str, repo: str, title: str, body: Optional[str] = None) -> str:
    """Create a new issue."""
    credentials = await get_credentials()
    result = await call_github_api(
        "POST",
        f"/repos/{owner}/{repo}/issues",
        credentials,
        json={
            "title": title,
            "body": body or ""
        }
    )
    return json.dumps(result, indent=2)


# Register with FastMCP
@mcp.tool()
async def list_repos() -> str:
    """List GitHub repositories."""
    return await _list_repos_impl()


@mcp.tool()
async def get_repo(owner: str, repo: str) -> str:
    """Get a specific repository."""
    return await _get_repo_impl(owner, repo)


@mcp.tool()
async def list_issues(owner: str, repo: str, state: Optional[str] = "open") -> str:
    """List issues in a repository."""
    return await _list_issues_impl(owner, repo, state)


@mcp.tool()
async def create_issue(owner: str, repo: str, title: str, body: Optional[str] = None) -> str:
    """Create a new issue."""
    return await _create_issue_impl(owner, repo, title, body)


# Create FastAPI app for custom endpoints
from fastapi import FastAPI

app = FastAPI(title="Github MCP Server")

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
    return {"status": "healthy", "service": "github-mcp-server"}


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
            
            # Get Vault auth info first (needed for entity_name fallback)
            vault_auth_info = await vault_client.get_vault_auth_info(user_jwt)
            
            # Get credentials with error handling (this will determine the actual entity_name used)
            entity_name = None
            try:
                credentials = await vault_client.get_credentials(user_jwt)
                secret_exists = True
                secret_error = None
                # Mask sensitive data
                masked_creds = {
                    "token": "***" + credentials.get("token", "")[-4:] if credentials.get("token") else "",
                    "username": credentials.get("username", "")
                }
                # Extract entity_name from vault_auth_info or JWT
                if vault_auth_info and vault_auth_info.get("entity_name"):
                    entity_name = vault_auth_info.get("entity_name")
                else:
                    entity_name = user_info.get("preferred_username", user_id)
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
                "vault_path": f"secret/data/users/{entity_name}/github",
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
        # Get tools from FastMCP's registered tools
        tools = [
            {
                "name": "list_repos",
                "description": "List GitHub repositories.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_repo",
                "description": "Get a specific repository.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string"},
                        "repo": {"type": "string"}
                    },
                    "required": ["owner", "repo"]
                }
            },
            {
                "name": "list_issues",
                "description": "List issues in a repository.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string"},
                        "repo": {"type": "string"},
                        "state": {"type": "string", "enum": ["open", "closed", "all"]}
                    },
                    "required": ["owner", "repo"]
                }
            },
            {
                "name": "create_issue",
                "description": "Create a new issue.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string"},
                        "repo": {"type": "string"},
                        "title": {"type": "string"},
                        "body": {"type": "string"}
                    },
                    "required": ["owner", "repo", "title"]
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
            if tool_name == "list_repos":
                result = await _list_repos_impl()
            elif tool_name == "get_repo":
                result = await _get_repo_impl(arguments.get("owner"), arguments.get("repo"))
            elif tool_name == "list_issues":
                result = await _list_issues_impl(
                    arguments.get("owner"),
                    arguments.get("repo"),
                    arguments.get("state", "open")
                )
            elif tool_name == "create_issue":
                result = await _create_issue_impl(
                    arguments.get("owner"),
                    arguments.get("repo"),
                    arguments.get("title"),
                    arguments.get("body")
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
