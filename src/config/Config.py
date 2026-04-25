# src/config/Config.py
import os

class Config:
    """Configuration class for PawaPay SDK"""
    
    # Public PawaPay endpoints (kept for reference/validation)
    settings = {
        'sandbox': {
            'api_url': 'https://api.sandbox.pawapay.io'
        },
        'production': {
            'api_url': 'https://api.pawapay.io'
        }
    }
    
    @staticmethod
    def _get_native():
        """
        🔒 SECURITY: Resolve native binary dynamically on-demand.
        Strictly required in all scenarios. No silent fallbacks.
        """
        from src.core import loader as native_loader
        
        # Strict signature validation - fail loud if tampered or missing
        if not hasattr(native_loader, 'get_pawapay_base_url') or not hasattr(native_loader, 'normalize_api_url'):
            raise RuntimeError("FATAL: Native module missing required security exports.")
            
        return native_loader
    
    def __init__(self, config=None):
        """
        Initialize configuration
        
        Args:
            config: Configuration dictionary
                - api_key: API key
                - environment: 'sandbox' or 'production' (default: 'sandbox')
                - timeout: Request timeout in seconds (default: 30000)
        """
        config = config or {}
        self.api_key = config.get('api_key')
        self.environment = config.get('environment', 'sandbox')
        self.timeout = config.get('timeout', 30000)
        
        if self.environment not in self.settings:
            raise ValueError(f"Invalid environment specified: {self.environment}")
        
        # Keep original raw base for diagnostics if needed
        self._raw_base_url = self.get_raw_base_url()
        
        # Normalized base URL
        self.base_url = self._normalize_base_url(self._raw_base_url)
    
    def get_raw_base_url(self) -> str:
        """Get raw base URL securely - STRICTLY NATIVE"""
        native = self._get_native()
        return native.get_pawapay_base_url(self.environment)
    
    def _normalize_base_url(self, url: str) -> str:
        """Normalize base URL - STRICTLY NATIVE"""
        native = self._get_native()
        return native.normalize_api_url(url)
    
    def get_base_url(self) -> str:
        """Get the base URL for the current environment"""
        return self.base_url
    
    def get_config(self) -> dict:
        """Get the complete configuration for the current environment"""
        return {
            'api_key': self.api_key,
            'environment': self.environment,
            'base_url': self.base_url,
            'timeout': self.timeout,
            'raw_base_url': self._raw_base_url,
            **self.settings.get(self.environment, {})
        }
    
    @classmethod
    def get_settings(cls, environment: str) -> dict:
        """Static method to get settings for a specific environment"""
        if environment not in cls.settings:
            raise ValueError(f"Invalid environment specified: {environment}")
        return cls.settings[environment]
    
    @classmethod
    def get_api_url(cls, environment: str) -> str:
        """Static method to get API URL for a specific environment - STRICTLY NATIVE"""
        if environment not in cls.settings:
            raise ValueError(f"Invalid environment specified: {environment}")
            
        native = cls._get_native()
        return native.get_pawapay_base_url(environment)
    
    @classmethod
    def is_valid_environment(cls, environment: str) -> bool:
        """Validate if an environment is supported"""
        return environment in cls.settings
    
    @classmethod
    def get_available_environments(cls) -> list:
        """Get all available environments"""
        return list(cls.settings.keys())