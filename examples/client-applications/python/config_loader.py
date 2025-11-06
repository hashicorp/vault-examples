#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Vault Python Client Application Configuration Loader
Configuration file loading and environment variable override support
"""

import os
import configparser
from typing import Dict, Any, Optional


class VaultConfig:
    """Vault client configuration management class"""
    
    def __init__(self, config_file: str = "config.ini"):
        """
        Initialize configuration loader
        
        Args:
            config_file: Configuration file path
        """
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self._load_config()
    
    def _load_config(self):
        """Load configuration file"""
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"Configuration file not found: {self.config_file}")
        
        self.config.read(self.config_file, encoding='utf-8')
    
    def get_vault_config(self) -> Dict[str, Any]:
        """Return Vault server configuration"""
        return {
            'entity': self._get_with_env_override('vault', 'entity'),
            'url': self._get_with_env_override('vault', 'url'),
            'namespace': self._get_with_env_override('vault', 'namespace') or None,
            'role_id': self._get_with_env_override('vault', 'role_id'),
            'secret_id': self._get_with_env_override('vault', 'secret_id')
        }
    
    def get_kv_config(self) -> Dict[str, Any]:
        """Return KV secret configuration"""
        return {
            'enabled': self._get_boolean('kv_secret', 'enabled'),
            'path': self._get_with_env_override('kv_secret', 'path'),
            'refresh_interval': self._get_int('kv_secret', 'refresh_interval')
        }
    
    def get_database_dynamic_config(self) -> Dict[str, Any]:
        """Return Database Dynamic secret configuration"""
        return {
            'enabled': self._get_boolean('database_dynamic', 'enabled'),
            'role_id': self._get_with_env_override('database_dynamic', 'role_id')
        }
    
    def get_database_static_config(self) -> Dict[str, Any]:
        """Return Database Static secret configuration"""
        return {
            'enabled': self._get_boolean('database_static', 'enabled'),
            'role_id': self._get_with_env_override('database_static', 'role_id')
        }
    
    def get_http_config(self) -> Dict[str, Any]:
        """Return HTTP configuration"""
        return {
            'timeout': self._get_int('http', 'timeout'),
            'max_response_size': self._get_int('http', 'max_response_size')
        }
    
    def _get_with_env_override(self, section: str, key: str) -> str:
        """
        Return configuration value with environment variable override support
        
        Args:
            section: Configuration section
            key: Configuration key
            
        Returns:
            Configuration value (environment variable value if exists, otherwise file value)
        """
        # Generate environment variable key (e.g., VAULT_URL, VAULT_ROLE_ID)
        env_key = f"VAULT_{key.upper()}"
        
        # Check environment variable value
        env_value = os.getenv(env_key)
        if env_value is not None:
            return env_value
        
        # Read value from file
        return self.config.get(section, key)
    
    def _get_boolean(self, section: str, key: str) -> bool:
        """Return boolean value"""
        return self.config.getboolean(section, key)
    
    def _get_int(self, section: str, key: str) -> int:
        """Return integer value"""
        return self.config.getint(section, key)
    
    def get_all_config(self) -> Dict[str, Any]:
        """Return all configuration"""
        return {
            'vault': self.get_vault_config(),
            'kv_secret': self.get_kv_config(),
            'database_dynamic': self.get_database_dynamic_config(),
            'database_static': self.get_database_static_config(),
            'http': self.get_http_config()
        }
    
    def print_config(self):
        """Print current configuration"""
        print("⚙️ Current Configuration:")
        config = self.get_all_config()
        
        vault_config = config['vault']
        print(f"- Entity: {vault_config['entity']}")
        print(f"- Vault URL: {vault_config['url']}")
        print(f"- KV Enabled: {config['kv_secret']['enabled']}")
        print(f"- Database Dynamic Enabled: {config['database_dynamic']['enabled']}")
        print(f"- Database Static Enabled: {config['database_static']['enabled']}")


if __name__ == "__main__":
    """Configuration loader test"""
    try:
        config = VaultConfig()
        config.print_config()
    except Exception as e:
        print(f"Configuration load failed: {e}")
