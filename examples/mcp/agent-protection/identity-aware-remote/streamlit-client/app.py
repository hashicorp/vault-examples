"""
Streamlit MCP Client
Web UI for selecting and using MCP servers with Keycloak authentication
"""
import streamlit as st
import httpx
import json
import os
import logging
from typing import Optional, Dict, Any

# Import authentication trace module for debugging
from auth_trace import display_auth_trace, get_vault_info_direct, decode_jwt_payload

logger = logging.getLogger(__name__)

# Configuration
# Use external URL for Keycloak (browser needs to access it)
if os.getenv("KEYCLOAK_URL"):
    KEYCLOAK_URL = os.getenv("KEYCLOAK_URL")
elif os.getenv("DOCKER_ENV"):
    # In Docker, use host machine's localhost
    KEYCLOAK_URL = "http://host.docker.internal:8080"
else:
    KEYCLOAK_URL = "http://localhost:8080"

REALM_NAME = os.getenv("REALM_NAME", "mcp-demo")
CLIENT_ID = os.getenv("CLIENT_ID", "mcp-client")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "mcp-client-secret")

# Vault configuration
if os.getenv("VAULT_ADDR"):
    VAULT_ADDR = os.getenv("VAULT_ADDR")
elif os.getenv("DOCKER_ENV"):
    VAULT_ADDR = "http://vault:8200"
else:
    VAULT_ADDR = "http://localhost:8200"

VAULT_TOKEN = os.getenv("VAULT_TOKEN", "root-token")

# MCP Server URLs - use internal Docker network URLs when in container
if os.getenv("JIRA_MCP_URL"):
    JIRA_MCP_URL = os.getenv("JIRA_MCP_URL")
elif os.getenv("DOCKER_ENV"):
    JIRA_MCP_URL = "http://jira-mcp-server:3000"
else:
    JIRA_MCP_URL = "http://localhost:3001"

if os.getenv("GITHUB_MCP_URL"):
    GITHUB_MCP_URL = os.getenv("GITHUB_MCP_URL")
elif os.getenv("DOCKER_ENV"):
    GITHUB_MCP_URL = "http://github-mcp-server:3000"
else:
    GITHUB_MCP_URL = "http://localhost:3002"

if os.getenv("POSTGRESQL_MCP_URL"):
    POSTGRESQL_MCP_URL = os.getenv("POSTGRESQL_MCP_URL")
elif os.getenv("DOCKER_ENV"):
    POSTGRESQL_MCP_URL = "http://postgresql-mcp-server:3000"
else:
    POSTGRESQL_MCP_URL = "http://localhost:3003"

# Available MCP servers
MCP_SERVERS = {
    "Jira": {
        "url": JIRA_MCP_URL,
        "description": "Manage Jira issues and projects"
    },
    "Github": {
        "url": GITHUB_MCP_URL,
        "description": "Manage GitHub repositories and issues"
    },
    "PostgreSQL": {
        "url": POSTGRESQL_MCP_URL,
        "description": "Query and manage PostgreSQL database"
    }
}


def init_session_state():
    """Initialize session state variables"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "access_token" not in st.session_state:
        st.session_state.access_token = None
    if "user_info" not in st.session_state:
        st.session_state.user_info = None
    if "selected_mcp" not in st.session_state:
        st.session_state.selected_mcp = None
    if "selected_mcps" not in st.session_state:
        st.session_state.selected_mcps = []
    if "auth_steps_completed" not in st.session_state:
        st.session_state.auth_steps_completed = []
    if "current_step" not in st.session_state:
        st.session_state.current_step = 0
    if "vault_info_cache" not in st.session_state:
        st.session_state.vault_info_cache = None
    if "step_failed" not in st.session_state:
        st.session_state.step_failed = {}  # Track failed steps: {step_num: error_message}
    if "mcp_credentials" not in st.session_state:
        st.session_state.mcp_credentials = {}  # Track credentials per MCP: {mcp_name: {secret_exists, secret_error, vault_path}}


def get_keycloak_token(username: str, password: str) -> Optional[Dict]:
    """Get access token from Keycloak"""
    try:
        token_url = f"{KEYCLOAK_URL}/realms/{REALM_NAME}/protocol/openid-connect/token"
        
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                token_url,
                data={
                    "grant_type": "password",
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "username": username,
                    "password": password,
                }
            )
            response.raise_for_status()
            return response.json()
    except httpx.ConnectError as e:
        st.error(f"Connection error: Cannot connect to Keycloak at {KEYCLOAK_URL}. Error: {e}")
        return None
    except httpx.HTTPStatusError as e:
        st.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        st.error(f"Authentication failed: {e}")
        return None


# Authentication trace functions moved to auth_trace.py
# decode_jwt_payload is also imported at the top for use in main app logic


def call_mcp_server(mcp_url: str, method: str, params: Dict, access_token: str) -> Dict:
    """Call MCP server via JSON (changed from SSE to avoid timeout issues)"""
    try:
        with httpx.Client(timeout=15.0) as client:
            # Use regular POST request instead of SSE streaming
            response = client.post(
                f"{mcp_url}/sse",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": method,
                    "params": params
                },
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                timeout=15.0
            )
            response.raise_for_status()
            
            # Safely parse JSON response
            try:
                result = response.json()
            except (ValueError, TypeError) as e:
                return {"error": {"message": f"Invalid JSON response: {str(e)}"}}
            
            # Ensure we always return a dict
            if result is None:
                return {"error": {"message": "Empty response from server"}}
            if not isinstance(result, dict):
                return {"error": {"message": f"Unexpected response type: {type(result)}"}}
            return result
            
    except httpx.TimeoutException:
        return {"error": {"message": "Request timed out"}}
    except httpx.HTTPStatusError as e:
        error_text = e.response.text if e.response else "Unknown error"
        return {"error": {"message": f"HTTP {e.response.status_code}: {error_text}"}}
    except httpx.ConnectError as e:
        return {"error": {"message": f"Connection error: {str(e)}"}}
    except Exception as e:
        return {"error": {"message": f"Unexpected error: {str(e)}"}}


def main():
    st.set_page_config(
        page_title="MCP Remote Client",
        layout="wide"
    )
    
    init_session_state()
    
    st.title("MCP Remote Client with Vault")
    st.markdown("Select an MCP server and interact with backend services using Vault-managed credentials")
    
    # Debug links for Keycloak and Vault
    col1, col2 = st.columns(2)
    with col1:
        keycloak_url = "http://localhost:8080"
        st.link_button("🔐 Keycloak", f"{keycloak_url}/admin", use_container_width=True)
        st.caption("Admin: `admin` / `admin`")
    with col2:
        vault_url = "http://localhost:8200"
        st.link_button("🔑 Vault", f"{vault_url}/ui", use_container_width=True)
        st.caption("Root Token: `root-token`")
    
    st.divider()
    
    # Authentication Section
    if not st.session_state.authenticated:
        st.header("Login")
        st.markdown("**Demo Users:** alice/alice123 or bob/bob123")
        
        col1, col2 = st.columns(2)
        
        with col1:
            username = st.text_input("Username", value="alice")
        
        with col2:
            password = st.text_input("Password", type="password", value="alice123")
        
        if st.button("Login", type="primary"):
            token_data = get_keycloak_token(username, password)
            if token_data:
                st.session_state.authenticated = True
                st.session_state.access_token = token_data.get("access_token")
                
                # Decode user info from token
                user_info = decode_jwt_payload(st.session_state.access_token)
                st.session_state.user_info = user_info
                
                # Update step completion status
                st.session_state.auth_steps_completed = [1, 2]
                st.session_state.current_step = 2
                st.session_state.vault_info_cache = None  # Clear cache on new login
                
                st.success(f"Logged in as {username}")
                st.rerun()
    else:
        # User info
        user_info = st.session_state.user_info
        username = user_info.get("preferred_username", "unknown")
        
        # Create left-right layout (60:40)
        left_col, right_col = st.columns([0.6, 0.4])
        
        with left_col:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.info(f"Logged in as: **{username}**")
            with col2:
                if st.button("Logout"):
                    st.session_state.authenticated = False
                    st.session_state.access_token = None
                    st.session_state.user_info = None
                    st.session_state.selected_mcp = None
                    st.session_state.selected_mcps = []
                    st.session_state.auth_steps_completed = []
                    st.session_state.current_step = 0
                    st.session_state.vault_info_cache = None
                    st.session_state.step_failed = {}
                    st.rerun()
            
            st.divider()
            
            # MCP Selection
            st.header("Select MCP Server")
            st.info("💡 **Select MCP server(s) to use.** You can select one or more servers.")
            
            mcp_options = list(MCP_SERVERS.keys())
            selected_mcps = []
            
            # Create simple checkboxes for each MCP server
            for mcp_name in mcp_options:
                mcp_info = MCP_SERVERS[mcp_name]
                is_selected = mcp_name in st.session_state.selected_mcps
                
                checkbox_label = f"🔧 {mcp_name} - {mcp_info['description']}"
                is_selected = st.checkbox(
                    checkbox_label,
                    value=is_selected,
                    key=f"mcp_checkbox_{mcp_name}"
                )
                
                if is_selected:
                    selected_mcps.append(mcp_name)
            
            # Update selected MCPs
            if set(selected_mcps) != set(st.session_state.selected_mcps):
                st.session_state.selected_mcps = selected_mcps
                st.session_state.vault_info_cache = None  # Clear cache on MCP change
                # Reset steps 3-6 when MCP is changed (user needs to Load Tools again)
                if 3 in st.session_state.auth_steps_completed:
                    # Keep only steps 1 and 2 completed
                    st.session_state.auth_steps_completed = [1, 2]
                    st.session_state.current_step = 2
                    # Clear any failures for steps 3-6
                    for i in range(3, 7):
                        if i in st.session_state.step_failed:
                            del st.session_state.step_failed[i]
            
            # For backward compatibility, set selected_mcp to first selected
            st.session_state.selected_mcp = selected_mcps[0] if selected_mcps else None
        
            if selected_mcps:
                # List available tools
                if st.button("Load Tools", type="primary"):
                    with st.spinner("Loading tools..."):
                        # Load tools for each selected MCP server and get credentials
                        loaded_count = 0
                        failed_mcps = []
                        mcp_credentials_info = {}
                        
                        # Track which steps have been completed
                        step3_completed = False
                        step3_failed = False
                        step6_failed_mcps = []
                        
                        for mcp_name in selected_mcps:
                            mcp_info = MCP_SERVERS[mcp_name]
                            
                            # Get credentials for this MCP server (for Step 6 validation)
                            mcp_vault_info = get_vault_info_direct(st.session_state.access_token, mcp_name)
                            mcp_credentials_info[mcp_name] = {
                                "secret_exists": mcp_vault_info.get("secret_exists", False),
                                "secret_error": mcp_vault_info.get("secret_error"),
                                "vault_path": mcp_vault_info.get("vault_path"),
                                "credentials": mcp_vault_info.get("credentials"),
                                "entity_name": mcp_vault_info.get("entity_name")
                            }
                            
                            # Step 3: MCP Server Request - Try to load tools first
                            result = call_mcp_server(
                                mcp_info["url"],
                                "tools/list",
                                {},
                                st.session_state.access_token
                            )
                            
                            # Check if result is None or has error (Step 3 failure)
                            if result is None:
                                failed_mcps.append(mcp_name)
                                step3_failed = True
                                # Mark step 3 as failed
                                if 1 in st.session_state.auth_steps_completed and 2 in st.session_state.auth_steps_completed:
                                    st.session_state.auth_steps_completed = [1, 2]
                                    st.session_state.current_step = 3
                                    st.session_state.step_failed[3] = f"No response from {mcp_name} server"
                                # Clear tools if they were previously loaded
                                if f"{mcp_name}_tools" in st.session_state:
                                    del st.session_state[f"{mcp_name}_tools"]
                                continue
                            elif isinstance(result, dict) and "error" in result:
                                error_msg = result['error']['message']
                                failed_mcps.append(mcp_name)
                                step3_failed = True
                                # Mark step 3 as failed
                                if 1 in st.session_state.auth_steps_completed and 2 in st.session_state.auth_steps_completed:
                                    st.session_state.auth_steps_completed = [1, 2]
                                    st.session_state.current_step = 3
                                    st.session_state.step_failed[3] = f"{mcp_name}: {error_msg}"
                                # Clear tools if they were previously loaded
                                if f"{mcp_name}_tools" in st.session_state:
                                    del st.session_state[f"{mcp_name}_tools"]
                                continue
                            else:
                                # Step 3 succeeded for this MCP
                                step3_completed = True
                                tools = result.get("result", {}).get("tools", [])
                                st.session_state[f"{mcp_name}_tools"] = tools
                                loaded_count += 1
                                
                                # Step 6: Check credentials/role availability (after Step 3 succeeds)
                                if mcp_name == "Jira" and not mcp_vault_info.get("secret_exists", False):
                                    step6_failed_mcps.append(mcp_name)
                                    # Clear tools since credentials are not available
                                    if f"{mcp_name}_tools" in st.session_state:
                                        del st.session_state[f"{mcp_name}_tools"]
                                    loaded_count -= 1
                                
                                if mcp_name == "PostgreSQL" and not mcp_vault_info.get("secret_exists", False):
                                    step6_failed_mcps.append(mcp_name)
                                    # Clear tools since role is not available
                                    if f"{mcp_name}_tools" in st.session_state:
                                        del st.session_state[f"{mcp_name}_tools"]
                                    loaded_count -= 1
                        
                        # Store MCP credentials info in session state
                        st.session_state.mcp_credentials = mcp_credentials_info
                        
                        # For backward compatibility, also store first MCP's vault info
                        if selected_mcps:
                            first_mcp = selected_mcps[0]
                            first_mcp_info = get_vault_info_direct(st.session_state.access_token, first_mcp)
                            st.session_state.vault_info_cache = first_mcp_info
                        
                        # Update step completion status sequentially
                        if 1 in st.session_state.auth_steps_completed and 2 in st.session_state.auth_steps_completed:
                            # Step 3: MCP Server Request
                            if step3_failed:
                                # Step 3 failed - don't proceed to later steps
                                st.session_state.auth_steps_completed = [1, 2]
                                st.session_state.current_step = 3
                                # Clear failures for steps 4, 5, 6
                                for step in [4, 5, 6]:
                                    if step in st.session_state.step_failed:
                                        del st.session_state.step_failed[step]
                            elif step3_completed:
                                # Step 3 succeeded - mark it as completed
                                st.session_state.auth_steps_completed = [1, 2, 3]
                                st.session_state.current_step = 3
                                # Clear step 3 failure if any
                                if 3 in st.session_state.step_failed:
                                    del st.session_state.step_failed[3]
                                
                                # Step 4, 5: Vault authentication and entity retrieval
                                # These happen automatically when MCP server accesses Vault
                                # Mark as completed if Step 3 succeeded
                                st.session_state.auth_steps_completed = [1, 2, 3, 4, 5]
                                st.session_state.current_step = 5
                                
                                # Step 6: Credentials Retrieved
                                if step6_failed_mcps:
                                    # Step 6 failed for some MCPs
                                    st.session_state.current_step = 6
                                    # Create detailed error messages for each failed MCP
                                    error_messages = []
                                    for failed_mcp in step6_failed_mcps:
                                        cred_info = mcp_credentials_info.get(failed_mcp, {})
                                        error_msg = cred_info.get('secret_error', 'Credentials not found')
                                        if failed_mcp == "PostgreSQL":
                                            error_messages.append(f"{failed_mcp}: Database role not found")
                                        elif failed_mcp == "Jira":
                                            error_messages.append(f"{failed_mcp}: Secret not found")
                                        else:
                                            error_messages.append(f"{failed_mcp}: {error_msg}")
                                    st.session_state.step_failed[6] = "; ".join(error_messages)
                                else:
                                    # Step 6 succeeded
                                    st.session_state.auth_steps_completed = [1, 2, 3, 4, 5, 6]
                                    st.session_state.current_step = 6
                                    # Clear step 6 failure if any
                                    if 6 in st.session_state.step_failed:
                                        del st.session_state.step_failed[6]
                        
                        # Show results
                        if step3_failed:
                            # Step 3 failures (MCP server connection issues)
                            st.error(f"⚠️ Unable to connect to the following MCP server(s): {', '.join(failed_mcps)}")
                        elif step6_failed_mcps:
                            # Step 6 failures (credentials/role not found)
                            if "Jira" in step6_failed_mcps:
                                st.error(f"⚠️ Unavailable: This user ({st.session_state.user_info.get('preferred_username', 'unknown')}) does not have Jira credentials stored in Vault.")
                                st.info("💡 **Note**: In this demo, only the alice user has Jira credentials. The bob user does not have credentials and cannot use the MCP server.")
                            elif "PostgreSQL" in step6_failed_mcps:
                                st.error(f"⚠️ Unavailable: This user ({st.session_state.user_info.get('preferred_username', 'unknown')}) does not have a PostgreSQL database role created in Vault.")
                                st.info("💡 **Note**: The PostgreSQL MCP server uses roles from the Vault Database Secrets Engine. Without a role, dynamic credentials cannot be generated.")
                            else:
                                st.error(f"⚠️ Credential errors occurred for the following MCP server(s): {', '.join(step6_failed_mcps)}")
                        
                        if loaded_count > 0:
                            st.success(f"Loaded tools from {loaded_count} MCP server(s)")
                
                # Display tools and allow interaction
                loaded_mcps = [mcp for mcp in selected_mcps if f"{mcp}_tools" in st.session_state]
                
                if loaded_mcps:
                    st.divider()
                    st.header("Available Tools")
                    
                    # Create tabs for each loaded MCP server
                    tabs = st.tabs([mcp for mcp in loaded_mcps])
                    
                    for tab_idx, mcp in enumerate(loaded_mcps):
                        with tabs[tab_idx]:
                            tools = st.session_state[f"{mcp}_tools"]
                            
                            for tool in tools:
                                tool_name = tool['name']
                                # Use session state to maintain expander state
                                expander_key = f"tool_expander_{mcp}_{tool_name}"
                                if expander_key not in st.session_state:
                                    st.session_state[expander_key] = False
                                
                                # Check if this tool's button was just clicked
                                button_clicked_key = f"tool_button_clicked_{mcp}_{tool_name}"
                                if button_clicked_key not in st.session_state:
                                    st.session_state[button_clicked_key] = False
                                
                                # Store current expander state before rendering
                                # If button was clicked, force expander to stay open
                                current_expanded = st.session_state[expander_key]
                                if st.session_state[button_clicked_key]:
                                    current_expanded = True
                                    st.session_state[expander_key] = True
                                
                                with st.expander(f"{tool_name}", expanded=current_expanded):
                                    # Always save the expanded state when inside the expander
                                    # This ensures that if user manually opens it, state is saved
                                    st.session_state[expander_key] = True
                                    
                                    st.markdown(f"**Description:** {tool['description']}")
                                    
                                    # Build form based on input schema
                                    input_schema = tool.get('inputSchema', {})
                                    properties = input_schema.get('properties', {})
                                    required = input_schema.get('required', [])
                                    
                                    form_inputs = {}
                                    
                                    for prop_name, prop_schema in properties.items():
                                        prop_type = prop_schema.get('type', 'string')
                                        prop_desc = prop_schema.get('description', '')
                                        
                                        if prop_type == 'string':
                                            if 'enum' in prop_schema:
                                                form_inputs[prop_name] = st.selectbox(
                                                    f"{prop_name}*" if prop_name in required else prop_name,
                                                    options=prop_schema['enum'],
                                                    key=f"{mcp}_{tool_name}_{prop_name}_enum",
                                                    help=prop_desc
                                                )
                                            else:
                                                # Special handling for specific tools
                                                if tool_name == "get_issue" and prop_name == "issue_key":
                                                    # Use a two-part input: prefix + suffix
                                                    col1, col2 = st.columns([1, 3])
                                                    with col1:
                                                        prefix = st.text_input(
                                                            "Prefix",
                                                            value="PROJ-",
                                                            key=f"{mcp}_{tool_name}_prefix",
                                                            help="Project prefix (e.g., PROJ-)"
                                                        )
                                                    with col2:
                                                        suffix = st.text_input(
                                                            f"{prop_name}*" if prop_name in required else prop_name,
                                                            value="1",
                                                            key=f"{mcp}_{tool_name}_{prop_name}",
                                                            help=prop_desc or "Issue number (e.g., 1, 2, 123)"
                                                        )
                                                    form_inputs[prop_name] = prefix + suffix
                                                elif tool_name == "execute_query" and prop_name == "query":
                                                    # Default SQL query for execute_query (PostgreSQL)
                                                    form_inputs[prop_name] = st.text_input(
                                                        f"{prop_name}*" if prop_name in required else prop_name,
                                                        value="SELECT * FROM users LIMIT 10;",
                                                        key=f"{mcp}_{tool_name}_{prop_name}_input",
                                                        help=prop_desc or "SQL query to execute (e.g., SELECT * FROM users LIMIT 10;)"
                                                    )
                                                elif tool_name == "describe_table" and prop_name == "table_name":
                                                    # Default table name for describe_table (PostgreSQL)
                                                    form_inputs[prop_name] = st.text_input(
                                                        f"{prop_name}*" if prop_name in required else prop_name,
                                                        value="users",
                                                        key=f"{mcp}_{tool_name}_{prop_name}_input",
                                                        help=prop_desc or "Name of the table to describe (e.g., users, products, orders)"
                                                    )
                                                elif tool_name == "list_issues" and prop_name == "jql":
                                                    # Default JQL query for list_issues
                                                    form_inputs[prop_name] = st.text_input(
                                                        f"{prop_name}" if prop_name in required else prop_name,
                                                        value="project = PROJ ORDER BY created DESC",
                                                        key=f"{mcp}_{tool_name}_{prop_name}_input",
                                                        help=prop_desc or "JQL query (e.g., project = PROJ ORDER BY created DESC)"
                                                    )
                                                elif tool_name == "create_issue" and "owner" in properties and "project" not in properties:
                                                    # Default values for create_issue (GitHub) - check for owner but not project
                                                    if prop_name == "owner":
                                                        form_inputs[prop_name] = st.text_input(
                                                            f"{prop_name}*" if prop_name in required else prop_name,
                                                            value="user",
                                                            key=f"{mcp}_{tool_name}_{prop_name}_input",
                                                            help=prop_desc or "Repository owner (e.g., user)"
                                                        )
                                                    elif prop_name == "repo":
                                                        form_inputs[prop_name] = st.text_input(
                                                            f"{prop_name}*" if prop_name in required else prop_name,
                                                            value="repo1",
                                                            key=f"{mcp}_{tool_name}_{prop_name}_input",
                                                            help=prop_desc or "Repository name (e.g., repo1)"
                                                        )
                                                    elif prop_name == "title":
                                                        form_inputs[prop_name] = st.text_input(
                                                            f"{prop_name}*" if prop_name in required else prop_name,
                                                            value="Test Issue",
                                                            key=f"{mcp}_{tool_name}_{prop_name}_input",
                                                            help=prop_desc or "Issue title"
                                                        )
                                                    elif prop_name == "body":
                                                        form_inputs[prop_name] = st.text_input(
                                                            f"{prop_name}*" if prop_name in required else prop_name,
                                                            value="This is a test issue created from MCP client",
                                                            key=f"{mcp}_{tool_name}_{prop_name}_input",
                                                            help=prop_desc or "Issue body/description"
                                                        )
                                                    else:
                                                        form_inputs[prop_name] = st.text_input(
                                                            f"{prop_name}*" if prop_name in required else prop_name,
                                                            key=f"{mcp}_{tool_name}_{prop_name}_input",
                                                            help=prop_desc
                                                        )
                                                elif tool_name == "create_issue":
                                                    # Default values for create_issue (Jira)
                                                    if prop_name == "summary":
                                                        form_inputs[prop_name] = st.text_input(
                                                            f"{prop_name}*" if prop_name in required else prop_name,
                                                            value="Test Issue",
                                                            key=f"{mcp}_{tool_name}_{prop_name}_input",
                                                            help=prop_desc or "Issue summary"
                                                        )
                                                    elif prop_name == "project":
                                                        form_inputs[prop_name] = st.text_input(
                                                            f"{prop_name}*" if prop_name in required else prop_name,
                                                            value="PROJ",
                                                            key=f"{mcp}_{tool_name}_{prop_name}_input",
                                                            help=prop_desc or "Project key (e.g., PROJ)"
                                                        )
                                                    elif prop_name == "description":
                                                        form_inputs[prop_name] = st.text_input(
                                                            f"{prop_name}*" if prop_name in required else prop_name,
                                                            value="This is a test issue created from MCP client",
                                                            key=f"{mcp}_{tool_name}_{prop_name}_input",
                                                            help=prop_desc or "Issue description"
                                                        )
                                                    else:
                                                        form_inputs[prop_name] = st.text_input(
                                                            f"{prop_name}*" if prop_name in required else prop_name,
                                                            key=f"{mcp}_{tool_name}_{prop_name}_input",
                                                            help=prop_desc
                                                        )
                                                elif tool_name == "get_repo":
                                                    # Default values for get_repo (GitHub)
                                                    if prop_name == "owner":
                                                        form_inputs[prop_name] = st.text_input(
                                                            f"{prop_name}*" if prop_name in required else prop_name,
                                                            value="user",
                                                            key=f"{mcp}_{tool_name}_{prop_name}_input",
                                                            help=prop_desc or "Repository owner (e.g., user)"
                                                        )
                                                    elif prop_name == "repo":
                                                        form_inputs[prop_name] = st.text_input(
                                                            f"{prop_name}*" if prop_name in required else prop_name,
                                                            value="repo1",
                                                            key=f"{mcp}_{tool_name}_{prop_name}_input",
                                                            help=prop_desc or "Repository name (e.g., repo1)"
                                                        )
                                                    else:
                                                        form_inputs[prop_name] = st.text_input(
                                                            f"{prop_name}*" if prop_name in required else prop_name,
                                                            key=f"{mcp}_{tool_name}_{prop_name}_input",
                                                            help=prop_desc
                                                        )
                                                elif tool_name == "list_issues":
                                                    # Default values for list_issues (GitHub)
                                                    if prop_name == "owner":
                                                        form_inputs[prop_name] = st.text_input(
                                                            f"{prop_name}*" if prop_name in required else prop_name,
                                                            value="user",
                                                            key=f"{mcp}_{tool_name}_{prop_name}_input",
                                                            help=prop_desc or "Repository owner (e.g., user)"
                                                        )
                                                    elif prop_name == "repo":
                                                        form_inputs[prop_name] = st.text_input(
                                                            f"{prop_name}*" if prop_name in required else prop_name,
                                                            value="repo1",
                                                            key=f"{mcp}_{tool_name}_{prop_name}_input",
                                                            help=prop_desc or "Repository name (e.g., repo1)"
                                                        )
                                                    elif prop_name == "state":
                                                        # state is optional with default "open"
                                                        form_inputs[prop_name] = st.selectbox(
                                                            prop_name,
                                                            options=["open", "closed", "all"],
                                                            index=0,  # default to "open"
                                                            key=f"{mcp}_{tool_name}_{prop_name}_input",
                                                            help=prop_desc or "Issue state (open, closed, all)"
                                                        )
                                                    else:
                                                        form_inputs[prop_name] = st.text_input(
                                                            f"{prop_name}*" if prop_name in required else prop_name,
                                                            key=f"{mcp}_{tool_name}_{prop_name}_input",
                                                            help=prop_desc
                                                        )
                                                else:
                                                    form_inputs[prop_name] = st.text_input(
                                                        f"{prop_name}*" if prop_name in required else prop_name,
                                                        key=f"{mcp}_{tool_name}_{prop_name}_input",
                                                        help=prop_desc
                                                    )
                                        elif prop_type == 'number' or prop_type == 'integer':
                                            form_inputs[prop_name] = st.number_input(
                                                f"{prop_name}*" if prop_name in required else prop_name,
                                                key=f"{mcp}_{tool_name}_{prop_name}_number",
                                                help=prop_desc
                                            )
                                        elif prop_type == 'boolean':
                                            form_inputs[prop_name] = st.checkbox(
                                                prop_name,
                                                key=f"{mcp}_{tool_name}_{prop_name}_bool",
                                                help=prop_desc
                                            )
                                    
                                    # Before button click, save current expander state
                                    # Since we're inside the expander, it's currently open
                                    # So we should keep it open after button click
                                    st.session_state[expander_key] = True
                                    
                                    if st.button(f"Execute {tool_name}", key=f"exec_{mcp}_{tool_name}"):
                                        # Button was clicked - ensure expander stays open after rerun
                                        st.session_state[button_clicked_key] = True
                                        st.session_state[expander_key] = True
                                        
                                        # Validate required fields
                                        missing = [f for f in required if not form_inputs.get(f)]
                                        if missing:
                                            st.error(f"Missing required fields: {', '.join(missing)}")
                                        else:
                                            with st.spinner(f"Executing {tool_name}..."):
                                                mcp_info = MCP_SERVERS[mcp]
                                                result = call_mcp_server(
                                                    mcp_info["url"],
                                                    "tools/call",
                                                    {
                                                        "name": tool_name,
                                                        "arguments": form_inputs
                                                    },
                                                    st.session_state.access_token
                                                )
                                                
                                                if "error" in result:
                                                    st.error(f"Error: {result['error']['message']}")
                                                else:
                                                    content = result.get("result", {}).get("content", [])
                                                    if content:
                                                        for item in content:
                                                            if item.get('type') == 'text':
                                                                st.json(json.loads(item.get('text', '{}')))
                                                    else:
                                                        st.success("Command executed successfully")
                                                        st.json(result)
                                        
                                        # Reset button_clicked_key after processing
                                        # But keep expander_key as True to maintain open state
                                        st.session_state[button_clicked_key] = False
        
        with right_col:
            # Display authentication trace using direct Vault access
            if st.session_state.access_token:
                mcp_info = MCP_SERVERS.get(st.session_state.selected_mcp, {}) if st.session_state.selected_mcp else {}
                
                # Get or use cached Vault info
                # Only fetch Vault info if steps 4, 5, or 6 are completed (after Load Tools)
                vault_info = st.session_state.vault_info_cache
                if vault_info is None:
                    # Only fetch Vault info if we need it for steps 4, 5, 6
                    # Step 3 only needs MCP info, not Vault info
                    if (4 in st.session_state.auth_steps_completed or 
                        5 in st.session_state.auth_steps_completed or 
                        6 in st.session_state.auth_steps_completed):
                        if st.session_state.selected_mcp:
                            vault_info = get_vault_info_direct(st.session_state.access_token)
                            if vault_info:
                                st.session_state.vault_info_cache = vault_info
                
                # Always display trace, but Vault info is only available after Load Tools
                display_auth_trace(
                    vault_info,
                    mcp_info,
                    username,
                    st.session_state.access_token,
                    st.session_state.auth_steps_completed,
                    st.session_state.current_step
                )


if __name__ == "__main__":
    main()

