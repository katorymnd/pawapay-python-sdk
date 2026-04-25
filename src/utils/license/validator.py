# src/utils/license/validator.py
"""
Core license validation
"""
import os
import json

class LicenseValidator:
    """License validator for local validation"""
    
    @staticmethod
    def _get_native():
        
        from src.core import loader as native_loader
        
        # Strict signature validation - fail loud if tampered or missing
        if not hasattr(native_loader, 'validate_license_local'):
            raise RuntimeError("FATAL: Native module missing required license validation export.")
            
        return native_loader
    
    def __init__(self):
        self.validated_licenses = {} 
        self.last_check = 0
    
    def validate(self, license_key: str) -> dict:
        """Validate license key strictly via native core"""
        secret_env = os.environ.get('PAWAPAY_SDK_LICENSE_SECRET', '')
        
        if not license_key or not isinstance(license_key, str):
            return self._fail("Invalid license key format")
            
        if not secret_env:
            return self._fail("Environment variable PAWAPAY_SDK_LICENSE_SECRET is not set.")

        try:
            # 🔒 Delegate entirely to native evaluation. No try/except swallowing.
            native = self._get_native()
            result_json = native.validate_license_local(license_key, secret_env)
            return json.loads(result_json)
            
        except RuntimeError as err:
            # Catch the missing module error specifically
            raise err
        except Exception as err:
            # Catch internal execution errors but fail the validation securely
            return self._fail(f"Native cryptography failure: {str(err)}")
  
    def _fail(self, reason: str) -> dict:
        print(f"[PawaPay License] {reason}")
        return {'valid': False, 'reason': reason}

# Singleton instance
validator = LicenseValidator()