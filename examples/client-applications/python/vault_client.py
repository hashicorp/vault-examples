#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Vault Python Client
Vault client implementation using hvac library
"""

import time
import logging
from typing import Dict, Any, Optional, Tuple
import hvac
from hvac.exceptions import VaultError


class VaultClient:
    """Vault client class"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Vault client
        
        Args:
            config: Vault configuration information
        """
        self.config = config
        self.client = None
        self.token = None
        self.token_issued_time = 0
        self.token_ttl = 0
        
        # Cache storage
        self.kv_cache = {}
        self.db_dynamic_cache = {}
        self.db_static_cache = {}
        
        # Logging configuration
        self.logger = logging.getLogger(__name__)
        
        # Initialize Vault client
        self._init_client()
    
    def _init_client(self):
        """Initialize Vault client"""
        try:
            self.client = hvac.Client(
                url=self.config['url'],
                namespace=self.config.get('namespace')
            )
            self.logger.info(f"Vault client initialized: {self.config['url']}")
        except Exception as e:
            self.logger.error(f"Vault client initialization failed: {e}")
            raise
    
    def login(self) -> bool:
        """
        Vault login using AppRole
        
        Returns:
            Login success status
        """
        try:
            response = self.client.auth.approle.login(
                role_id=self.config['role_id'],
                secret_id=self.config['secret_id']
            )
            
            self.token = response['auth']['client_token']
            self.token_issued_time = time.time()
            self.token_ttl = response['auth']['lease_duration']
            
            # Set token to client
            self.client.token = self.token
            
            self.logger.info(f"Vault login successful (TTL: {self.token_ttl}s)")
            return True
            
        except VaultError as e:
            self.logger.error(f"Vault login failed: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error during login: {e}")
            return False
    
    def renew_token(self) -> bool:
        """
        Renew token
        
        Returns:
            Renewal success status
        """
        try:
            response = self.client.auth.token.renew_self()
            
            self.token_issued_time = time.time()
            self.token_ttl = response['auth']['lease_duration']
            
            self.logger.info(f"Token renewal successful (TTL: {self.token_ttl}s)")
            return True
            
        except VaultError as e:
            self.logger.error(f"Token renewal failed: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error during token renewal: {e}")
            return False
    
    def is_token_expired(self) -> bool:
        """
        Check if token is expired
        
        Returns:
            Token expiration status
        """
        if not self.token or self.token_ttl <= 0:
            return True
        
        elapsed_time = time.time() - self.token_issued_time
        # Renew at 4/5 point of TTL
        return elapsed_time >= (self.token_ttl * 0.8)
    
    def ensure_valid_token(self) -> bool:
        """
        Ensure valid token
        
        Returns:
            Token validity assurance success status
        """
        if not self.token or self.is_token_expired():
            return self.login()
        
        if self.is_token_expired():
            return self.renew_token()
        
        return True
    
    def get_kv_secret(self, path: str) -> Optional[Dict[str, Any]]:
        """
        Get KV v2 secret
        
        Args:
            path: Secret path
            
        Returns:
            Secret data or None
        """
        if not self.ensure_valid_token():
            return None
        
        try:
            # Check cache
            if path in self.kv_cache:
                cached_data = self.kv_cache[path]
                current_time = time.time()
                
                # Check if cache is valid (5 minutes)
                if current_time - cached_data['timestamp'] < 300:
                    self.logger.debug(f"Using cached KV secret: {path}")
                    return cached_data['data']
            
            # Get secret from Vault
            response = self.client.secrets.kv.v2.read_secret_version(
                path=path,
                mount_point=f"{self.config['entity']}-kv"
            )
            
            secret_data = response['data']['data']
            metadata = response['data']['metadata']
            
            # Store in cache
            self.kv_cache[path] = {
                'data': secret_data,
                'metadata': metadata,
                'timestamp': time.time()
            }
            
            self.logger.info(f"KV secret fetch successful (version: {metadata['version']})")
            return secret_data
            
        except VaultError as e:
            self.logger.error(f"KV secret fetch failed: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error fetching KV secret: {e}")
            return None
    
    def get_database_dynamic_secret(self, role_id: str) -> Optional[Dict[str, Any]]:
        """
        Get Database Dynamic secret
        
        Args:
            role_id: Database role ID
            
        Returns:
            Secret data or None
        """
        if not self.ensure_valid_token():
            return None
        
        try:
            # Check cache
            cache_key = f"{role_id}"
            if cache_key in self.db_dynamic_cache:
                cached_data = self.db_dynamic_cache[cache_key]
                current_time = time.time()
                
                # TTL-based cache check (10 second threshold)
                remaining_ttl = cached_data['ttl'] - (current_time - cached_data['timestamp'])
                if remaining_ttl > 10:
                    self.logger.debug(f"Using cached Database Dynamic secret (TTL: {int(remaining_ttl)}s)")
                    return {
                        'data': cached_data['data'],
                        'ttl': int(remaining_ttl)
                    }
            
            # Get secret from Vault
            response = self.client.secrets.database.generate_credentials(
                name=role_id,
                mount_point=f"{self.config['entity']}-database"
            )
            
            secret_data = response['data']
            ttl = response['lease_duration']
            
            # Store in cache
            self.db_dynamic_cache[cache_key] = {
                'data': secret_data,
                'ttl': ttl,
                'timestamp': time.time()
            }
            
            self.logger.info(f"Database Dynamic secret fetch successful (TTL: {ttl}s)")
            return {
                'data': secret_data,
                'ttl': ttl
            }
            
        except VaultError as e:
            self.logger.error(f"Database Dynamic secret fetch failed: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error fetching Database Dynamic secret: {e}")
            return None
    
    def get_database_static_secret(self, role_id: str) -> Optional[Dict[str, Any]]:
        """
        Get Database Static secret
        
        Args:
            role_id: Database role ID
            
        Returns:
            Secret data or None
        """
        if not self.ensure_valid_token():
            return None
        
        try:
            # Check cache
            cache_key = f"{role_id}"
            if cache_key in self.db_static_cache:
                cached_data = self.db_static_cache[cache_key]
                current_time = time.time()
                
                # Time-based cache check (5 minutes)
                if current_time - cached_data['timestamp'] < 300:
                    self.logger.debug(f"Using cached Database Static secret")
                    return cached_data['data']
            
            # Get secret from Vault
            response = self.client.secrets.database.get_static_credentials(
                name=role_id,
                mount_point=f"{self.config['entity']}-database"
            )
            
            secret_data = response['data']
            ttl = response.get('ttl', 3600)  # Default TTL 1 hour
            
            # Store in cache
            self.db_static_cache[cache_key] = {
                'data': secret_data,
                'ttl': ttl,
                'timestamp': time.time()
            }
            
            self.logger.info(f"Database Static secret fetch successful (TTL: {ttl}s)")
            return {
                'data': secret_data,
                'ttl': ttl
            }
            
        except VaultError as e:
            self.logger.error(f"Database Static secret fetch failed: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error fetching Database Static secret: {e}")
            return None
    
    def get_token_info(self) -> Optional[Dict[str, Any]]:
        """
        Get token information
        
        Returns:
            Token information or None
        """
        if not self.ensure_valid_token():
            return None
        
        try:
            response = self.client.auth.token.lookup_self()
            return response['data']
        except VaultError as e:
            self.logger.error(f"Token info fetch failed: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error fetching token info: {e}")
            return None


if __name__ == "__main__":
    """Vault client test"""
    import sys
    from config_loader import VaultConfig
    
    # Logging configuration
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Load configuration
        config_loader = VaultConfig()
        vault_config = config_loader.get_vault_config()
        
        # Create Vault client
        client = VaultClient(vault_config)
        
        # Login test
        if client.login():
            print("✅ Vault login successful")
            
            # Get token info
            token_info = client.get_token_info()
            if token_info:
                print(f"Token info: {token_info}")
        else:
            print("❌ Vault login failed")
            sys.exit(1)
            
    except Exception as e:
        print(f"Test failed: {e}")
        sys.exit(1)
