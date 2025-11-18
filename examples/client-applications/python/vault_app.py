#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Vault Python Client Application
Main application logic and scheduler
"""

import time
import signal
import threading
import logging
import json
from typing import Dict, Any
from config_loader import VaultConfig
from vault_client import VaultClient


class VaultApplication:
    """Vault client application"""
    
    def __init__(self, config_file: str = "config.ini"):
        """
        Initialize application
        
        Args:
            config_file: Configuration file path
        """
        self.config_loader = VaultConfig(config_file)
        self.config = self.config_loader.get_all_config()
        self.vault_client = VaultClient(self.config['vault'])
        
        # Scheduler state
        self.running = False
        self.threads = []
        
        # Logging configuration
        self.logger = logging.getLogger(__name__)
        self._setup_logging()
        
        # Signal handler setup
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _setup_logging(self):
        """Setup logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('vault-python-app.log')
            ]
        )
    
    def _signal_handler(self, signum, frame):
        """Signal handler"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
    
    def start(self):
        """Start application"""
        self.logger.info("🚀 Starting Vault Python Client Application")
        
        # Vault login
        if not self.vault_client.login():
            self.logger.error("Vault login failed")
            return False
        
        # Print configuration information
        self._print_startup_info()
        
        # Start schedulers
        self.running = True
        self._start_schedulers()
        
        # Main loop
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
        finally:
            self.stop()
        
        return True
    
    def stop(self):
        """Stop application"""
        self.logger.info("Stopping application...")
        self.running = False
        
        # Wait for all threads to terminate
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=5)
        
        self.logger.info("Application shutdown complete")
    
    def _print_startup_info(self):
        """Print startup information"""
        print("🚀 Starting Vault Python Client Application")
        print("✅ Vault login successful")
        
        # Print configuration information
        self.config_loader.print_config()
        
        print("\n📖 Example Purpose and Usage Scenarios")
        print("This example is a reference application for Vault integration development.")
        print("If needed only for initial application startup, it makes an API call once and then utilizes the cache for subsequent runs to reduce memory usage.")
        print("The example is implemented to periodically fetch and renew secrets.")
        
        print("\n🔧 Supported Features:")
        print("- KV v2 Secret Engine (version-based caching)")
        print("- Database Dynamic Secret Engine (TTL-based renewal)")
        print("- Database Static Secret Engine (time-based caching)")
        print("- Automatic Token Renewal")
        print("- Entity-based Permission Management")
        
        print("\n🔄 Starting secret renewal... (Press Ctrl+C to exit)")
    
    def _start_schedulers(self):
        """Start schedulers"""
        # KV secret renewal scheduler
        if self.config['kv_secret']['enabled']:
            kv_thread = threading.Thread(
                target=self._kv_secret_scheduler,
                name="KV-Secret-Scheduler"
            )
            kv_thread.daemon = True
            kv_thread.start()
            self.threads.append(kv_thread)
            self.logger.info(f"✅ KV secret renewal scheduler started (interval: {self.config['kv_secret']['refresh_interval']}s)")
        
        # Database Dynamic secret renewal scheduler
        if self.config['database_dynamic']['enabled']:
            db_dynamic_thread = threading.Thread(
                target=self._database_dynamic_scheduler,
                name="DB-Dynamic-Scheduler"
            )
            db_dynamic_thread.daemon = True
            db_dynamic_thread.start()
            self.threads.append(db_dynamic_thread)
            self.logger.info("✅ Database Dynamic secret renewal scheduler started (interval: 5s)")
        
        # Database Static secret renewal scheduler
        if self.config['database_static']['enabled']:
            db_static_thread = threading.Thread(
                target=self._database_static_scheduler,
                name="DB-Static-Scheduler"
            )
            db_static_thread.daemon = True
            db_static_thread.start()
            self.threads.append(db_static_thread)
            self.logger.info("✅ Database Static secret renewal scheduler started (interval: 10s)")
    
    def _kv_secret_scheduler(self):
        """KV secret renewal scheduler"""
        while self.running:
            try:
                print("\n=== KV Secret Refresh ===")
                
                secret_data = self.vault_client.get_kv_secret(
                    self.config['kv_secret']['path']
                )
                
                if secret_data:
                    print(f"✅ KV secret fetch successful")
                    print(f"📦 KV Secret Data:")
                    print(json.dumps(secret_data, indent=2, ensure_ascii=False))
                else:
                    print("❌ KV secret fetch failed")
                
                time.sleep(self.config['kv_secret']['refresh_interval'])
                
            except Exception as e:
                self.logger.error(f"Error refreshing KV secret: {e}")
                time.sleep(5)
    
    def _database_dynamic_scheduler(self):
        """Database Dynamic secret renewal scheduler"""
        while self.running:
            try:
                print("\n=== Database Dynamic Secret Refresh ===")
                
                secret_result = self.vault_client.get_database_dynamic_secret(
                    self.config['database_dynamic']['role_id']
                )
                
                if secret_result:
                    secret_data = secret_result['data']
                    ttl = secret_result['ttl']
                    
                    print(f"✅ Database Dynamic secret fetch successful (TTL: {ttl}s)")
                    print(f"🗄️ Database Dynamic Secret (TTL: {ttl}s):")
                    print(f"  username: {secret_data['username']}")
                    print(f"  password: {secret_data['password']}")
                else:
                    print("❌ Database Dynamic secret fetch failed")
                
                time.sleep(5)
                
            except Exception as e:
                self.logger.error(f"Error refreshing Database Dynamic secret: {e}")
                time.sleep(5)
    
    def _database_static_scheduler(self):
        """Database Static secret renewal scheduler"""
        while self.running:
            try:
                print("\n=== Database Static Secret Refresh ===")
                
                secret_result = self.vault_client.get_database_static_secret(
                    self.config['database_static']['role_id']
                )
                
                if secret_result:
                    secret_data = secret_result['data']
                    ttl = secret_result['ttl']
                    
                    print(f"✅ Database Static secret fetch successful (TTL: {ttl}s)")
                    print(f"🔒 Database Static Secret (TTL: {ttl}s):")
                    print(f"  username: {secret_data['username']}")
                    print(f"  password: {secret_data['password']}")
                else:
                    print("❌ Database Static secret fetch failed")
                
                time.sleep(10)
                
            except Exception as e:
                self.logger.error(f"Error refreshing Database Static secret: {e}")
                time.sleep(10)


def main():
    """Main function"""
    app = VaultApplication()
    app.start()


if __name__ == "__main__":
    main()
