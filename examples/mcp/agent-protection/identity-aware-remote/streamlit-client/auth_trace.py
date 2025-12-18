"""
Authentication Flow Trace Module
디버깅용 인증 흐름 추적 기능
"""
import streamlit as st
import httpx
import json
import os
import logging
from typing import Optional, Dict, Any
import base64
from datetime import datetime

logger = logging.getLogger(__name__)

# Vault configuration
if os.getenv("VAULT_ADDR"):
    VAULT_ADDR = os.getenv("VAULT_ADDR")
elif os.getenv("DOCKER_ENV"):
    VAULT_ADDR = "http://vault:8200"
else:
    VAULT_ADDR = "http://localhost:8200"

# Keycloak configuration
REALM_NAME = os.getenv("REALM_NAME", "mcp-demo")


def decode_jwt_payload(token: str) -> Dict:
    """Decode JWT payload (for demo purposes)"""
    try:
        parts = token.split('.')
        if len(parts) >= 2:
            payload = json.loads(base64.urlsafe_b64decode(parts[1] + '=='))
            return payload
    except:
        pass
    return {}


def format_timestamp(timestamp: Optional[int]) -> str:
    """Format Unix timestamp to readable date"""
    if timestamp:
        try:
            return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        except:
            return str(timestamp)
    return "N/A"


def get_vault_info_direct(jwt_token: str, mcp_name: Optional[str] = None) -> Dict[str, Any]:
    """Get Vault authentication and credential information directly using JWT
    
    Args:
        jwt_token: JWT token from Keycloak
        mcp_name: Optional MCP server name (e.g., "Jira", "Github") to get specific credentials
    """
    result = {
        "vault_auth_info": None,
        "vault_path": None,
        "credentials": None,
        "secret_exists": False,
        "secret_error": None,
        "entity_name": None
    }
    
    try:
        with httpx.Client(timeout=10.0) as client:
            # Step 1: Login to Vault with JWT
            login_response = client.post(
                f"{VAULT_ADDR}/v1/auth/jwt/login",
                json={"role": "user", "jwt": jwt_token}
            )
            login_response.raise_for_status()
            auth_data = login_response.json()["auth"]
            vault_token = auth_data["client_token"]
            
            # Step 2: Get token lookup info
            lookup_response = client.get(
                f"{VAULT_ADDR}/v1/auth/token/lookup-self",
                headers={"X-Vault-Token": vault_token}
            )
            lookup_response.raise_for_status()
            lookup_data = lookup_response.json()["data"]
            
            # Step 3: Get entity name from JWT (username)
            entity_id = lookup_data.get("entity_id")
            entity_name = None
            
            # Try to get entity_name from JWT first (username)
            user_info = decode_jwt_payload(jwt_token)
            entity_name = user_info.get("preferred_username", "unknown")
            logger.info(f"Using entity name from JWT: {entity_name}")
            
            # Fetch entity information using entity name (not entity ID)
            if entity_name:
                try:
                    entity_response = client.get(
                        f"{VAULT_ADDR}/v1/identity/entity/name/{entity_name}",
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
                    logger.error(f"Error fetching entity: {e}")
                    pass
            
            # Step 4: Get Vault auth info
            result["vault_auth_info"] = {
                "entity_id": entity_id,
                "entity_name": entity_name,
                "policies": lookup_data.get("policies", []),
                "metadata": lookup_data.get("meta", {}),
                "aliases": lookup_data.get("aliases", []),
                "lease_duration": auth_data.get("lease_duration"),
                "renewable": auth_data.get("renewable", False)
            }
            
            # Step 5: Try to get credentials
            # For PostgreSQL, check database role instead of KV secret
            if mcp_name == "PostgreSQL":
                # Check if database role exists
                role_path = f"database/roles/{entity_name}"
                logger.info(f"Checking PostgreSQL database role: {role_path}")
                
                try:
                    role_response = client.get(
                        f"{VAULT_ADDR}/v1/{role_path}",
                        headers={"X-Vault-Token": vault_token}
                    )
                    
                    if role_response.status_code == 200:
                        role_data = role_response.json()["data"]
                        result["secret_exists"] = True
                        result["vault_path"] = f"database/creds/{entity_name}"  # Show creds path for actual usage
                        
                        # Try to get actual credentials for display (they are dynamically generated)
                        try:
                            creds_response = client.get(
                                f"{VAULT_ADDR}/v1/database/creds/{entity_name}",
                                headers={"X-Vault-Token": vault_token}
                            )
                            if creds_response.status_code == 200:
                                creds_data = creds_response.json()["data"]
                                # Mask sensitive data
                                result["credentials"] = {
                                    "username": creds_data.get("username", ""),
                                    "password": "***" + creds_data.get("password", "")[-4:] if creds_data.get("password") else "",
                                    "lease_id": creds_data.get("lease_id", ""),
                                    "lease_duration": creds_data.get("lease_duration", ""),
                                    "role_name": role_data.get("db_name", ""),
                                    "default_ttl": role_data.get("default_ttl", ""),
                                    "max_ttl": role_data.get("max_ttl", "")
                                }
                            else:
                                # If we can't get credentials, at least show role info
                                result["credentials"] = {
                                    "role_name": role_data.get("db_name", ""),
                                    "default_ttl": role_data.get("default_ttl", ""),
                                    "max_ttl": role_data.get("max_ttl", ""),
                                    "note": "Credentials are dynamically generated when needed"
                                }
                        except Exception as e:
                            # If we can't get credentials, at least show role info
                            logger.warning(f"Could not fetch credentials for display: {e}")
                            result["credentials"] = {
                                "role_name": role_data.get("db_name", ""),
                                "default_ttl": role_data.get("default_ttl", ""),
                                "max_ttl": role_data.get("max_ttl", ""),
                                "note": "Credentials are dynamically generated when needed"
                            }
                    elif role_response.status_code == 404:
                        result["secret_exists"] = False
                        result["secret_error"] = "Database role not found"
                        # Even when role doesn't exist, show the correct path for debugging
                        result["vault_path"] = f"database/roles/{entity_name}"
                    else:
                        result["secret_exists"] = False
                        result["secret_error"] = f"HTTP {role_response.status_code}: {role_response.text[:200]}"
                        result["vault_path"] = f"database/roles/{entity_name}"
                except Exception as e:
                    result["secret_exists"] = False
                    result["secret_error"] = str(e)
                    result["vault_path"] = f"database/roles/{entity_name}"
            else:
                # For other MCPs (Jira, Github), use KV secrets
                secret_type = mcp_name.lower() if mcp_name else "jira"  # Default to jira for backward compatibility
                secret_path = f"secret/data/users/{entity_name}/{secret_type}"
                result["vault_path"] = secret_path
                logger.info(f"Final vault_path: {result['vault_path']}")
                
                try:
                    creds_response = client.get(
                        f"{VAULT_ADDR}/v1/{secret_path}",
                        headers={"X-Vault-Token": vault_token}
                    )
                    
                    if creds_response.status_code == 200:
                        credentials = creds_response.json()["data"]["data"]
                        # Mask sensitive data
                        result["credentials"] = {
                            "username": credentials.get("username", ""),
                            "password": "***" + credentials.get("password", "")[-4:] if credentials.get("password") else "",
                            "api_token": "***" + credentials.get("api_token", "")[-4:] if credentials.get("api_token") else ""
                        }
                        result["secret_exists"] = True
                    elif creds_response.status_code == 404:
                        result["secret_exists"] = False
                        result["secret_error"] = "Secret not found"
                    else:
                        result["secret_exists"] = False
                        result["secret_error"] = f"HTTP {creds_response.status_code}: {creds_response.text[:200]}"
                except Exception as e:
                    result["secret_exists"] = False
                    result["secret_error"] = str(e)
            
            result["entity_name"] = entity_name
                
    except Exception as e:
        result["secret_error"] = f"Error accessing Vault: {str(e)}"
        logger.error(f"Error getting Vault info directly: {e}")
    
    return result


def display_auth_trace(vault_info: Optional[Dict], mcp_info: Dict, username: str, jwt_token: str, completed_steps: list, current_step: int):
    """Display authentication flow trace using directly retrieved Vault information"""
    st.header("Authentication Flow Trace (Debug Info)")
    st.info("이 정보는 Streamlit에서 JWT를 사용하여 Vault에 직접 접근하여 가져온 것입니다. 실제 MCP Server에서는 각각의 서버가 자체적으로 Vault에 접근하여 자격증명을 가져옵니다.")
    st.markdown("인증 및 API 요청 흐름을 단계별로 추적합니다.")
    
    # Get failed steps from session state
    failed_steps = st.session_state.get("step_failed", {})
    
    # Step indicator (horizontal progress bar)
    st.markdown("### 진행 상태")
    step_names = [
        "User Login",
        "JWT Issued",
        "MCP Request",
        "Vault Auth",
        "Entity",
        "Credentials"
    ]
    
    # Create columns for step indicators
    cols = st.columns(6)
    for i, (col, step_name) in enumerate(zip(cols, step_names), 1):
        with col:
            is_completed = i in completed_steps
            is_current = current_step == i
            is_failed = i in failed_steps
            
            # For Step 6, check if any MCP failed (one failure = overall failure)
            if i == 6 and not is_failed:
                mcp_credentials = st.session_state.get("mcp_credentials", {})
                if mcp_credentials:
                    # Check if any MCP has failed credentials
                    for mcp_name, cred_info in mcp_credentials.items():
                        if not cred_info.get("secret_exists", False):
                            is_failed = True
                            break
            
            if is_failed:
                status_icon = "❌"
                status_color = "red"
                status_text = "실패"
            elif is_completed:
                status_icon = "✅"
                status_color = "green"
                status_text = "완료"
            elif is_current:
                status_icon = "🔄"
                status_color = "blue"
                status_text = "진행중"
            else:
                status_icon = "⏳"
                status_color = "gray"
                status_text = "대기중"
            
            # Create styled container for each step
            bg_color = '#ffebee' if is_failed else '#e8f5e9' if is_completed else '#e3f2fd' if is_current else '#f5f5f5'
            st.markdown(
                f"""
                <div style="
                    text-align: center;
                    padding: 10px;
                    border: 2px solid {status_color};
                    border-radius: 8px;
                    background-color: {bg_color};
                    margin: 5px;
                ">
                    <div style="font-size: 24px; margin-bottom: 5px;">{status_icon}</div>
                    <div style="font-weight: bold; font-size: 12px;">Step {i}</div>
                    <div style="font-size: 10px; color: {status_color};">{status_text}</div>
                    <div style="font-size: 9px; margin-top: 5px; color: #666;">{step_name}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()
    
    # Decode JWT for display (always available if authenticated)
    jwt_payload = decode_jwt_payload(jwt_token) if jwt_token else {}
    jwt_details = {
        "sub": jwt_payload.get("sub"),
        "iss": jwt_payload.get("iss"),
        "aud": jwt_payload.get("aud"),
        "exp": jwt_payload.get("exp"),
        "iat": jwt_payload.get("iat"),
        "preferred_username": jwt_payload.get("preferred_username"),
        "email": jwt_payload.get("email"),
        "groups": jwt_payload.get("groups", [])
    }
    user_info = {
        "sub": jwt_payload.get("sub"),
        "preferred_username": jwt_payload.get("preferred_username"),
        "email": jwt_payload.get("email")
    }
    
    vault_auth_info = vault_info.get("vault_auth_info", {}) if vault_info else {}
    
    # Create a container with max height for scrolling
    trace_container = st.container()
    
    with trace_container:
        # Step 1: User Login
        step_num = 1
        is_completed = step_num in completed_steps
        is_current = current_step == step_num
        
        if is_completed:
            status_icon = "✅"
            status_text = "완료"
            expander_label = f"{status_icon} Step {step_num}: User Login (Keycloak) - {status_text}"
        elif is_current:
            status_icon = "🔄"
            status_text = "진행 중"
            expander_label = f"{status_icon} Step {step_num}: User Login (Keycloak) - {status_text}"
        else:
            status_icon = "⏳"
            status_text = "대기 중"
            expander_label = f"{status_icon} Step {step_num}: User Login (Keycloak) - {status_text}"
        
        with st.expander(expander_label, expanded=is_current or is_completed):
            if not is_completed:
                st.info("이 단계는 아직 완료되지 않았습니다.")
            else:
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Username:**")
                    st.code(username, language=None)
                    st.markdown("**Keycloak Realm:**")
                    st.code(REALM_NAME, language=None)
                with col2:
                    st.markdown("**User ID (sub):**")
                    st.code(user_info.get("sub", "N/A"), language=None)
                    st.markdown("**Email:**")
                    st.code(user_info.get("email", "N/A"), language=None)
        
        # Step 2: JWT Token Issued
        step_num = 2
        is_completed = step_num in completed_steps
        is_current = current_step == step_num
        
        if is_completed:
            status_icon = "✅"
            status_text = "완료"
            expander_label = f"{status_icon} Step {step_num}: JWT Token Issued - {status_text}"
        elif is_current:
            status_icon = "🔄"
            status_text = "진행 중"
            expander_label = f"{status_icon} Step {step_num}: JWT Token Issued - {status_text}"
        else:
            status_icon = "⏳"
            status_text = "대기 중"
            expander_label = f"{status_icon} Step {step_num}: JWT Token Issued - {status_text}"
        
        with st.expander(expander_label, expanded=is_current or is_completed):
            if not is_completed:
                st.info("이 단계는 아직 완료되지 않았습니다.")
            else:
                st.markdown("**JWT Token (masked):**")
                token_preview = jwt_token[:20] + "..." + jwt_token[-20:] if jwt_token else "N/A"
                st.code(token_preview, language=None)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**JWT Claims:**")
                    jwt_claims = {
                        "sub": jwt_details.get("sub", "N/A"),
                        "iss": jwt_details.get("iss", "N/A"),
                        "aud": jwt_details.get("aud", "N/A"),
                        "preferred_username": jwt_details.get("preferred_username", "N/A"),
                        "email": jwt_details.get("email", "N/A")
                    }
                    st.json(jwt_claims)
                with col2:
                    st.markdown("**Token Expiry:**")
                    exp_time = format_timestamp(jwt_details.get("exp"))
                    iat_time = format_timestamp(jwt_details.get("iat"))
                    st.text(f"Issued At: {iat_time}")
                    st.text(f"Expires At: {exp_time}")
                    if jwt_details.get("exp") and jwt_details.get("iat"):
                        duration = jwt_details.get("exp") - jwt_details.get("iat")
                        st.text(f"Duration: {duration} seconds ({duration // 3600} hours)")
        
        # Step 3: MCP Server Request
        step_num = 3
        is_completed = step_num in completed_steps
        is_current = current_step == step_num
        
        if is_completed:
            status_icon = "✅"
            status_text = "완료"
            expander_label = f"{status_icon} Step {step_num}: MCP Server Request (with JWT) - {status_text}"
        elif is_current:
            status_icon = "🔄"
            status_text = "진행 중"
            expander_label = f"{status_icon} Step {step_num}: MCP Server Request (with JWT) - {status_text}"
        else:
            status_icon = "⏳"
            status_text = "대기 중"
            expander_label = f"{status_icon} Step {step_num}: MCP Server Request (with JWT) - {status_text}"
        
        with st.expander(expander_label, expanded=is_current or is_completed):
            if not is_completed:
                st.info("이 단계는 아직 완료되지 않았습니다.")
            else:
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**MCP Server:**")
                    st.code(mcp_info.get("description", "N/A"), language=None)
                    st.markdown("**Server URL:**")
                    st.code(mcp_info.get("url", "N/A"), language=None)
                with col2:
                    st.markdown("**Request Method:**")
                    st.code("POST /sse", language=None)
                    st.markdown("**Authorization:**")
                    st.code("Bearer <JWT_TOKEN>", language=None)
        
        # Step 4: Vault Authentication
        step_num = 4
        is_completed = step_num in completed_steps
        is_current = current_step == step_num
        
        if is_completed:
            status_icon = "✅"
            status_text = "완료"
            expander_label = f"{status_icon} Step {step_num}: Vault Authentication - {status_text}"
        elif is_current:
            status_icon = "🔄"
            status_text = "진행 중"
            expander_label = f"{status_icon} Step {step_num}: Vault Authentication - {status_text}"
        else:
            status_icon = "⏳"
            status_text = "대기 중"
            expander_label = f"{status_icon} Step {step_num}: Vault Authentication - {status_text}"
        
        with st.expander(expander_label, expanded=is_current or is_completed):
            if not is_completed:
                st.info("이 단계는 아직 완료되지 않았습니다.")
            else:
                if vault_auth_info:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Entity ID:**")
                        st.code(vault_auth_info.get("entity_id", "N/A"), language=None)
                        st.markdown("**Entity Name:**")
                        st.code(vault_auth_info.get("entity_name", "N/A"), language=None)
                        st.markdown("**Policies:**")
                        policies = vault_auth_info.get("policies", [])
                        if policies:
                            st.code("\n".join(policies), language=None)
                        else:
                            st.code("N/A", language=None)
                    with col2:
                        st.markdown("**Lease Duration:**")
                        lease_duration = vault_auth_info.get("lease_duration", "N/A")
                        if isinstance(lease_duration, int):
                            st.text(f"{lease_duration} seconds ({lease_duration // 3600} hours)")
                        else:
                            st.text(str(lease_duration))
                        st.markdown("**Renewable:**")
                        st.code(str(vault_auth_info.get("renewable", False)), language=None)
                        st.markdown("**Aliases:**")
                        aliases = vault_auth_info.get("aliases", [])
                        if aliases:
                            st.json(aliases)
                        else:
                            st.code("None", language=None)
                else:
                    st.warning("Vault authentication information not available")
        
        # Step 5: Entity Created/Retrieved
        step_num = 5
        is_completed = step_num in completed_steps
        is_current = current_step == step_num
        
        if is_completed:
            status_icon = "✅"
            status_text = "완료"
            expander_label = f"{status_icon} Step {step_num}: Entity Created/Retrieved - {status_text}"
        elif is_current:
            status_icon = "🔄"
            status_text = "진행 중"
            expander_label = f"{status_icon} Step {step_num}: Entity Created/Retrieved - {status_text}"
        else:
            status_icon = "⏳"
            status_text = "대기 중"
            expander_label = f"{status_icon} Step {step_num}: Entity Created/Retrieved - {status_text}"
        
        with st.expander(expander_label, expanded=is_current or is_completed):
            if not is_completed:
                st.info("이 단계는 아직 완료되지 않았습니다.")
            else:
                if vault_auth_info:
                    st.markdown("**Entity Aliases:**")
                    aliases = vault_auth_info.get("aliases", [])
                    if aliases:
                        for alias in aliases:
                            st.json(alias)
                    else:
                        st.code("No aliases", language=None)
                    
                    st.markdown("**Vault Path (Policy Templating):**")
                    entity_name = vault_info.get("entity_name", "N/A") if vault_info else "N/A"
                    vault_path = vault_info.get("vault_path", "N/A") if vault_info else "N/A"
                    st.code(vault_path, language=None)
                    
                    # Show policy info based on the path type
                    if vault_path and "database" in vault_path:
                        st.info(f"Policy allows access to: database/creds/{entity_name} and database/roles/{entity_name} (Entity name = username from pre-created entities)")
                    else:
                        st.info(f"Policy allows access to: secret/data/users/{entity_name}/* (Entity name = username from pre-created entities)")
                else:
                    st.warning("Entity information not available")
        
        # Step 6: Credentials Retrieved
        step_num = 6
        is_completed = step_num in completed_steps
        is_current = current_step == step_num
        is_failed = step_num in failed_steps
        
        if is_failed:
            status_icon = "❌"
            status_text = "실패"
            expander_label = f"{status_icon} Step {step_num}: Credentials Retrieved - {status_text}"
        elif is_completed:
            status_icon = "✅"
            status_text = "완료"
            expander_label = f"{status_icon} Step {step_num}: Credentials Retrieved - {status_text}"
        elif is_current:
            status_icon = "🔄"
            status_text = "진행 중"
            expander_label = f"{status_icon} Step {step_num}: Credentials Retrieved - {status_text}"
        else:
            status_icon = "⏳"
            status_text = "대기 중"
            expander_label = f"{status_icon} Step {step_num}: Credentials Retrieved - {status_text}"
        
        with st.expander(expander_label, expanded=is_current or is_completed or is_failed):
            # Get MCP credentials from session state
            mcp_credentials = st.session_state.get("mcp_credentials", {})
            selected_mcps = st.session_state.get("selected_mcps", [])
            
            if is_failed:
                error_msg = failed_steps.get(step_num, "Unknown error")
                st.error(f"❌ **실패**: {error_msg}")
                
                # Show credentials info for each MCP
                if mcp_credentials:
                    st.markdown("### MCP 서버별 자격증명 상태")
                    for mcp_name in selected_mcps:
                        if mcp_name in mcp_credentials:
                            cred_info = mcp_credentials[mcp_name]
                            with st.container():
                                col1, col2 = st.columns([1, 3])
                                with col1:
                                    if cred_info.get("secret_exists", False):
                                        st.success(f"✅ {mcp_name}")
                                    else:
                                        st.error(f"❌ {mcp_name}")
                                with col2:
                                    st.markdown(f"**Path:** `{cred_info.get('vault_path', 'N/A')}`")
                                    if not cred_info.get("secret_exists", False):
                                        error = cred_info.get("secret_error", "Secret not found")
                                        st.error(f"**오류:** {error}")
                else:
                    # Fallback to old vault_info for backward compatibility
                    if vault_info:
                        st.markdown("**Credentials Path:**")
                        st.code(vault_info.get("vault_path", "N/A"), language=None)
                        secret_error = vault_info.get("secret_error")
                        if secret_error:
                            st.code(secret_error, language=None)
                
                st.warning("⚠️ 일부 MCP 서버는 Vault에 자격증명이 저장되어 있지 않아 사용할 수 없습니다.")
            elif not is_completed:
                st.info("이 단계는 아직 완료되지 않았습니다.")
            else:
                # Show credentials info for each MCP
                if mcp_credentials:
                    st.markdown("### MCP 서버별 자격증명 상태")
                    all_success = True
                    
                    for mcp_name in selected_mcps:
                        if mcp_name in mcp_credentials:
                            cred_info = mcp_credentials[mcp_name]
                            
                            with st.container():
                                st.markdown(f"#### 🔧 {mcp_name}")
                                
                                st.markdown(f"**Credentials Path:**")
                                st.code(cred_info.get("vault_path", "N/A"), language=None)
                                
                                secret_exists = cred_info.get("secret_exists", False)
                                secret_error = cred_info.get("secret_error")
                                
                                if secret_exists:
                                    st.success(f"✅ Secret found in Vault")
                                    st.markdown("**Credentials (Masked):**")
                                    creds = cred_info.get("credentials", {})
                                    if creds:
                                        st.json(creds)
                                    else:
                                        st.warning("No credentials data available")
                                else:
                                    all_success = False
                                    st.error(f"❌ Secret not found: {secret_error or 'Secret does not exist in Vault'}")
                                    if secret_error:
                                        st.code(secret_error, language=None)
                                
                                st.divider()
                    
                    if all_success:
                        st.success("✅ 모든 선택된 MCP 서버의 자격증명이 정상적으로 로드되었습니다.")
                else:
                    # Fallback to old vault_info for backward compatibility
                    if vault_info:
                        st.markdown("**Credentials Path:**")
                        st.code(vault_info.get("vault_path", "N/A"), language=None)
                        
                        secret_exists = vault_info.get("secret_exists", False)
                        secret_error = vault_info.get("secret_error")
                        
                        if secret_exists:
                            st.success("Secret found in Vault")
                            st.markdown("**Credentials (Masked):**")
                            creds = vault_info.get("credentials", {})
                            if creds:
                                st.json(creds)
                            else:
                                st.warning("No credentials data available")
                        else:
                            st.error(f"Secret not found: {secret_error or 'Secret does not exist in Vault'}")
                            if secret_error:
                                st.code(secret_error, language=None)
                    else:
                        st.warning("Vault information not available")
        
        st.divider()
        st.markdown("**Note:** 실제 MCP Server (Jira, Github)에서는 각각의 서버가 독립적으로 Vault에 접근하여 자체 자격증명을 가져옵니다. 이 Debug Info는 Streamlit에서 직접 가져온 정보를 보여주는 것입니다.")

