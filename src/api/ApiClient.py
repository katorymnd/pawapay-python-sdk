# src/api/ApiClient.py
import asyncio
import json
import random
import time
import sys
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
import aiohttp
import ssl
import certifi

from ..config.Config import Config
from ..utils.license import (
    validator,
    server_check,
    protection,
    integrity
)


class ApiClient:
    """
    PawaPay API Client with dual-stack V1 and V2 support
    Includes comprehensive license protection and integrity checks
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the API client
        
        Args:
            config: Configuration dictionary
                - api_token: PawaPay API token
                - environment: 'sandbox' or 'production'
                - ssl_verify: Enable TLS verification (default: True)
                - api_version: 'v1' or 'v2' (default: 'v1')
                - license_key: SDK license key (REQUIRED)
        """
        # CRITICAL: License validation
        self._is_initializing = True
        self._init_task = None
        self._initialization_error = None
        self._license_valid = False
        self._license = None
        self._activated = False
        self._clearance_token = 0x4B41544F
        
        # Store configuration FIRST (before native binding)
        self.api_token = config.get('api_token')
        self.environment = config.get('environment', 'sandbox')
        self.ssl_verify = config.get('ssl_verify', True)
        self.api_version = config.get('api_version', 'v1')
        if self.api_version not in ['v1', 'v2']:
            self.api_version = 'v1'
        
        # 🔒 SECURITY: Bind native inside class, not globally
        self.__native = None
        self.__native_bound = False
        self.__native_validated = False
        self._bind_native_module()
        
        # Set base URL (only if native module loaded successfully)
        if self.__native is not None:
            self.api_base_url = self._set_base_url(self.environment)
        else:
            # Fallback if native failed to load
            config_obj = Config({'environment': self.environment})
            self.api_base_url = config_obj.get_base_url()
        
        # Initialize HTTP client
        self.http_client = None
        self._initialize_http_client()
        
        # Initialize license (but don't await it here to avoid blocking constructor)
        license_key = config.get('license_key')
        if license_key:
            self._init_task = asyncio.create_task(self._initialize_license(license_key))
        
        # Wrap methods with protection
        self._wrap_methods()
        
        # Start background protection
        self._start_protection_loop()
    
    def __setattr__(self, name, value):
        """🔒 SECURITY: Prevent native module rebinding after validation"""
        # Allow initial setup
        if name == "_ApiClient__native":
            # Allow setting to None or initial binding
            if not hasattr(self, "_ApiClient__native_validated"):
                super().__setattr__(name, value)
                return
            
            # Block only if already validated and trying to change
            if hasattr(self, "_ApiClient__native_validated") and self.__native_validated:
                if hasattr(self, "_ApiClient__native") and self.__native is not None:
                    raise AttributeError("Native core is immutable and cannot be modified")
        
        super().__setattr__(name, value)
    
    def _bind_native_module(self):
        """Load and bind the native module"""
        try:
            # Dynamic import inside method
            from src.core import loader as native_loader
            
            # Basic validation - ensure it has required functions
            required_functions = ['get_pawapay_base_url', 'verify_request_state']
            for func in required_functions:
                if not hasattr(native_loader, func):
                    raise Exception(f"Native module missing required function: {func}")
            
            # Store as private attribute
            self.__native = native_loader
            self.__native_bound = True
            
            # Validate the module works
            self._validate_native_module()
            self.__native_validated = True
            
            # Get platform info for logging
            try:
                from src.core import get_native_platform_id
                platform_id = get_native_platform_id()
                print(f"[PawaPay] ✅ Native module loaded: {platform_id}")
            except:
                print("[PawaPay] ✅ Native module loaded")
                
        except ImportError as e:
            print(f"[PawaPay] ❌ FATAL: Native module not available: {e}")
            try:
                protection.destroy({'silent': True})
            except:
                pass
            raise Exception(f"FATAL: Native module not available: {e}")
            
        except Exception as e:
            print(f"[PawaPay] ❌ Native module validation failed: {e}")
            try:
                protection.destroy({'silent': True})
            except:
                pass
            raise

    def _validate_native_module(self):
        """🔒 SECURITY: Ensure native module is real, not a mock"""
        native = self.__native
        if native is None:
            return
        
        try:
            # Check for required functions
            required_functions = ['get_pawapay_base_url', 'verify_request_state']
            for func in required_functions:
                if not hasattr(native, func):
                    raise Exception(f"Native module missing required function: {func}")
            
            # Execute proof-of-authenticity test
            test_url = native.get_pawapay_base_url("sandbox")
            
            # Validate response looks legitimate
            if not test_url or not isinstance(test_url, str):
                raise Exception("Invalid native response type")
            
            if "pawapay" not in test_url.lower():
                raise Exception("Invalid native response content")
            
            # In production, be more strict with file extension checks
            if self.environment == 'production':
                # Check module origin
                if hasattr(native, '__file__'):
                    # Accept .pyd (Windows), .so (Linux), .dylib (macOS)
                    valid_extensions = ('.so', '.pyd', '.dylib')
                    if not any(native.__file__.endswith(ext) for ext in valid_extensions):
                        # Also accept .py in development but not production
                        if native.__file__.endswith('.py'):
                            raise Exception("Native module must be compiled for production")
                        else:
                            raise Exception(f"Native module has invalid file extension: {native.__file__}")
            
            print("[PawaPay] Native module validated successfully")
                
        except Exception as e:
            # Clear native reference on validation failure
            self.__native = None
            self.__native_bound = False
            raise Exception(f"Native module validation failed: {e}")
    
    def _require_native(self):
        """🔒 SECURITY: Mandatory native module access with validation"""
        # In development/sandbox, allow operation without native
        if self.environment == 'sandbox' and self.__native is None:
            # Return a dummy object for sandbox testing
            return self._create_sandbox_native_stub()
        
        # Check if we have the native module
        native = getattr(self, "_ApiClient__native", None)
        
        if native is None:
            if self.environment == 'production':
                protection.destroy({'silent': True})
                raise Exception("Native core missing - SDK cannot function in production")
            else:
                # In sandbox, return stub
                return self._create_sandbox_native_stub()
        
        # Random re-validation (25% chance)
        if random.random() < 0.25:
            try:
                test = native.get_pawapay_base_url("sandbox")
                if "pawapay" not in test:
                    raise Exception("Native validation failed")
            except Exception as e:
                if self.environment == 'production':
                    protection.destroy({'silent': True})
                    raise Exception(f"Native core integrity failure: {e}")
                else:
                    print(f"[PawaPay] Native validation warning: {e}")
        
        return native
    
    def _create_sandbox_native_stub(self):
        """Create a stub native module for sandbox/development testing"""
        class SandboxNativeStub:
            def get_pawapay_base_url(self, environment):
                return "https://api.sandbox.pawapay.io"
            
            def verify_request_state(self, *args, **kwargs):
                # No-op in sandbox
                pass
            
            def generate_server_fingerprint(self, *args, **kwargs):
                # Return dummy fingerprint
                return "sandbox_fingerprint_validation_passed"
            
            def normalize_api_url(self, url):
                # Simple normalization
                return url.rstrip('/')
        
        return SandboxNativeStub()
    
    def _initialize_http_client(self):
        """Initialize the HTTP client with proper configuration"""
        timeout = aiohttp.ClientTimeout(total=30)
        connector = None
        
        if not self.ssl_verify:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            connector = aiohttp.TCPConnector(ssl=ssl_context)
        else:
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        self.http_client = aiohttp.ClientSession(
            base_url=self.api_base_url,
            timeout=timeout,
            connector=connector,
            headers={
                'Authorization': f'Bearer {self.api_token}',
                'Content-Type': 'application/json'
            }
        )
    
    async def _initialize_license(self, license_key: str):
        """Initialize and validate license"""
        try:
            if protection.is_destroyed():
                raise Exception("SDK has been disabled due to previous violations")
            
            if not integrity.verify_all():
                protection.record_violation("Code tampering detected")
                protection.destroy()
                raise Exception("SDK integrity check failed - possible tampering detected")
            
            local_check = validator.validate(license_key)
            if not local_check.get('valid'):
                protection.record_violation(local_check.get('reason', 'Unknown'))
                raise Exception(f"License validation failed: {local_check.get('reason')}")
            
            server_result = await server_check.validate_and_activate(license_key)
            if not server_result.get('valid'):
                reason = server_result.get('reason', 'Server validation failed')
                protection.record_violation(reason)
                raise Exception(f"License validation failed: {reason}")
            
            if local_check.get('days_remaining') and local_check['days_remaining'] < 30:
                print(f"[PawaPay] License expires in {local_check['days_remaining']} days - please renew at https://katorymnd.com")
            
            # Success
            self._license = license_key
            self._license_valid = True
            self._activated = server_result.get('activated', False)
            
            # ✅ FIX: Keep clearance_token within 4 bytes
            self._clearance_token = ((self._clearance_token << 4) | 0x10) & 0xFFFFFFFF
            
            print("[PawaPay] License validated successfully")

        except Exception as error:
            print(f"[PawaPay] License initialization failed: {str(error)}")
            self._license_valid = False
            # ✅ FIX: Keep clearance_token within 4 bytes
            self._clearance_token = ((self._clearance_token >> 4) | 0xF0000000) & 0xFFFFFFFF
            self._initialization_error = str(error)

        finally:
            self._is_initializing = False
    
    def _wrap_methods(self):
        """Wrap API methods with protection checks"""
        method_names = [
            "initiate_deposit", "initiate_deposit_v2", "initiate_deposit_auto",
            "initiate_payout", "initiate_payout_v2", "initiate_payout_auto",
            "initiate_refund", "initiate_refund_v2", "initiate_refund_auto",
            "check_mno_availability", "check_mno_availability_v2", "check_mno_availability_auto",
            "check_active_conf", "check_active_conf_v2", "check_active_conf_auto",
            "check_transaction_status", "check_transaction_status_v2", "check_transaction_status_auto",
            "create_payment_page_session", "create_payment_page_session_v2", "create_payment_page_session_auto"
        ]
        
        for method_name in method_names:
            if hasattr(self, method_name):
                original_method = getattr(self, method_name)
                
                async def wrapped_method(*args, _orig=original_method, **kwargs):
                    # 🔒 SECURITY: Native validation (only if not initializing)
                    if not self._is_initializing:
                        try:
                            native = self._require_native()
                            # Only call verify_request_state if it exists
                            if hasattr(native, 'verify_request_state'):
                                native.verify_request_state(
                                    self._is_initializing,
                                    protection.is_destroyed(),
                                    self._license_valid,
                                    self._initialization_error or ""
                                )
                        except Exception as e:
                            if self.environment == 'production':
                                protection.destroy({'silent': True})
                                raise e
                            else:
                                print(f"[PawaPay] Native check warning: {e}")
                    
                    # Python-level security checks
                    if not self._is_initializing:                        
                        state_ptr = (id(self) ^ int(time.time())) & 0xFF
                        
                        if state_ptr % 17 == 0:  
                            prot_state = 1 if protection.is_destroyed() else 0
                            int_state = 0 if integrity.random_check() else 1
                            lic_state = 0 if self._license_valid else 1
                            
                            cascade_mask = (prot_state << 2) | (int_state << 1) | lic_state
                            
                            if cascade_mask != 0:
                                # ✅ FIX: Ensure clearance_token stays within 4 bytes
                                self._clearance_token = (self._clearance_token ^ cascade_mask) & 0xFFFFFFFF
                            
                            if random.random() < 0.3:
                                # ✅ FIX: Ensure value fits in 4 bytes before conversion
                                token_value = self._clearance_token & 0xFFFFFFFF
                                try:
                                    _katorymnd_yl8gfh2 = token_value.to_bytes(4, 'big')
                                except OverflowError:
                                    # Fallback if still too large (shouldn't happen with mask)
                                    _katorymnd_yl8gfh2 = b'\x00\x00\x00\x00'
                    
                    # 🔒 SECURITY: Random native re-validation (15% chance)
                    if random.random() < 0.15:
                        self._require_native()
                    
                    # Execute original method
                    return await _orig(*args, **kwargs)
                
                setattr(self, method_name, wrapped_method)
    
    def _start_protection_loop(self):
        """Start background protection loop"""
        pass
    
    async def _cleanup(self):
        """Cleanup intervals"""
        if self.http_client:
            await self.http_client.close()
    
    def _set_base_url(self, environment: str) -> str:
        """Set base URL from config using native loader"""
        # 🔒 SECURITY: Use validated native module
        try:
            native = self._require_native()
            base_url = native.get_pawapay_base_url(environment)
            # Normalize using native if available
            if hasattr(native, 'normalize_api_url'):
                base_url = native.normalize_api_url(base_url)
            return base_url
        except Exception:
            # Fallback to Python Config if native fails
            config = Config({'environment': environment})
            base_url = config.get_base_url()
            import re
            base_url = re.sub(r'/v[12]/?$', '', base_url, flags=re.IGNORECASE)
            base_url = base_url.rstrip('/')
            return base_url
    
    async def make_api_request(self, endpoint: str, method: str = "POST", data: Optional[Dict] = None):
        """Low level HTTP wrapper"""
        # Wait for initialization
        if self._is_initializing and self._init_task:
            try:
                await self._init_task
            except:
                pass
        
        # 🔒 SECURITY: Mandatory native validation
        try:
            native = self._require_native()
            
            # Primary security check (if method exists)
            if hasattr(native, 'verify_request_state'):
                native.verify_request_state(
                    self._is_initializing,
                    protection.is_destroyed(),
                    self._license_valid,
                    self._initialization_error or ""
                )
            
            # 🔒 SECURITY: Silent cryptographic dependency
            seed = int(time.time()) & 0xFFFF
            try:
                if hasattr(native, 'generate_server_fingerprint'):
                    fingerprint = native.generate_server_fingerprint(
                        endpoint, self.api_base_url, "mac", "machine", str(seed)
                    )
                    if not fingerprint or len(str(fingerprint)) < 10:
                        raise Exception("Runtime corruption detected")
                else:
                    test_url = native.get_pawapay_base_url("sandbox")
                    if not test_url or "pawapay" not in test_url:
                        raise Exception("Native validation failed")
            except Exception as e:
                # Always destroy and raise on cryptography failure
                protection.destroy({'silent': True})
                raise Exception(f"Native runtime validation failed: {e}")
                
        except Exception as e:
            # FIX 1: ALWAYS raise the exception to block the request!
            # Do not swallow it just because we are in the sandbox.
            protection.destroy({'silent': True})
            raise e
        
        # Python-level security blocks
        local_clearance = getattr(self, '_clearance_token', 0x4B41544F)
        
        # FIX 2: Use Bitwise OR (|=) to ensure the poison bits are hard-set
        if protection.is_destroyed():
            local_clearance |= 0xDEAD0000
            
        if not self._is_initializing and not self._license_valid:
            local_clearance |= 0x0000BEEF
        
        # FIX 3: Trigger if poison bits are explicitly detected
        if (local_clearance & 0xDEAD0000) == 0xDEAD0000 or (local_clearance & 0x0000BEEF) == 0x0000BEEF:
            err_code = hex(local_clearance & 0xFFFFFFFF)
            msg = self._initialization_error or "Segmentation fault in payload constructor"
            raise Exception(f"SDK Request Blocked: Context verification failed. Code: {err_code} - {msg}")
        
        # ✅ SURGICAL FIX: Prepare and execute the HTTP request (moved OUTSIDE the if block)
        # Ensure endpoint is a proper path
        if not endpoint.startswith('/'):
            endpoint = f'/{endpoint}'
        
        url = f"{self.api_base_url}{endpoint}"
        
        try:
            if method.upper() == "POST":
                async with self.http_client.post(url, json=data) as response:
                    response_data = await response.json()
                    
                    if 200 <= response.status < 300:
                        try:
                            protection.record_success()
                        except Exception:
                            pass
                    return {'status': response.status, 'response': response_data}
                    
            elif method.upper() == "GET":
                async with self.http_client.get(url, params=data) as response:
                    response_data = await response.json()
                    
                    if 200 <= response.status < 300:
                        try:
                            protection.record_success()
                        except Exception:
                            pass
                    return {'status': response.status, 'response': response_data}
            else:
                raise Exception(f"Unsupported HTTP method: {method}")
                
        except aiohttp.ClientError as error:
            if hasattr(error, 'response') and error.response:
                status = error.response.status
                resp_data = await error.response.json() if error.response.content else {}
                raise Exception(f"Request Error: Request failed with status code {status}, body: {json.dumps(resp_data)}")
            raise Exception(f"Request Error: {str(error)}")

    # V1 - Initiate Deposit
    
    async def initiate_deposit(self, deposit_id: str, amount: str, currency: str,
                               correspondent: str, payer: str,
                               statement_description: str = "Payment for order",
                               metadata: List = []):
        data = {
            'depositId': deposit_id,
            'amount': amount,
            'currency': currency,
            'correspondent': correspondent,
            'payer': {
                'type': 'MSISDN',
                'address': {'value': payer}
            },
            'customerTimestamp': datetime.utcnow().isoformat() + 'Z',
            'statementDescription': statement_description
        }
        
        if metadata and len(metadata) > 0:
            data['metadata'] = metadata
        
        return await self.make_api_request('/deposits', 'POST', data)
    
    # V2 - Initiate Deposit
    async def initiate_deposit_v2(self, deposit_id: str, amount: str, currency: str,
                                  payer_msisdn: str, provider: str,
                                  customer_message: Optional[str] = None,
                                  client_reference_id: Optional[str] = None,
                                  pre_authorisation_code: Optional[str] = None,
                                  metadata: List = []):
        payload = {
            'depositId': deposit_id,
            'payer': {
                'type': 'MMO',
                'accountDetails': {
                    'phoneNumber': payer_msisdn,
                    'provider': provider
                }
            },
            'amount': amount,
            'currency': currency
        }
        
        if customer_message:
            payload['customerMessage'] = customer_message
        if client_reference_id:
            payload['clientReferenceId'] = client_reference_id
        if pre_authorisation_code:
            payload['preAuthorisationCode'] = pre_authorisation_code
        if metadata and len(metadata) > 0:
            payload['metadata'] = metadata
        
        return await self.make_api_request('/v2/deposits', 'POST', payload)
    
    # Version-aware deposit initiation
    async def initiate_deposit_auto(self, args: Dict[str, Any]):
        if self.api_version == 'v2':
            return await self.initiate_deposit_v2(
                args.get('depositId'),
                args.get('amount'),
                args.get('currency'),
                args.get('payerMsisdn'),
                args.get('provider'),
                args.get('customerMessage'),
                args.get('clientReferenceId'),
                args.get('preAuthorisationCode'),
                args.get('metadata', [])
            )
        
        return await self.initiate_deposit(
            args.get('depositId'),
            args.get('amount'),
            args.get('currency'),
            args.get('correspondent'),
            args.get('payerMsisdn'),
            args.get('statementDescription', 'Payment for order'),
            args.get('metadata', [])
        )
    
    # V1 - Initiate Payout
    async def initiate_payout(self, payout_id: str, amount: str, currency: str,
                              correspondent: str, recipient: str,
                              statement_description: str = "Payout to customer",
                              metadata: List = []):
        data = {
            'payoutId': payout_id,
            'amount': amount,
            'currency': currency,
            'correspondent': correspondent,
            'recipient': {
                'type': 'MSISDN',
                'address': {'value': recipient}
            },
            'customerTimestamp': datetime.utcnow().isoformat() + 'Z',
            'statementDescription': statement_description
        }
        
        if metadata and len(metadata) > 0:
            data['metadata'] = metadata
        
        return await self.make_api_request('/payouts', 'POST', data)
    
    # V2 - Initiate Payout
    async def initiate_payout_v2(self, payout_id: str, amount: str, currency: str,
                                 recipient_msisdn: str, provider: str,
                                 customer_message: Optional[str] = None,
                                 metadata: List = []):
        payload = {
            'payoutId': payout_id,
            'recipient': {
                'type': 'MMO',
                'accountDetails': {
                    'phoneNumber': recipient_msisdn,
                    'provider': provider
                }
            },
            'amount': amount,
            'currency': currency
        }
        
        if customer_message:
            payload['customerMessage'] = customer_message
        
        if metadata and len(metadata) > 0:
            norm = []
            for item in metadata:
                if item and isinstance(item, dict):
                    if 'fieldName' in item and 'fieldValue' in item:
                        obj = {item['fieldName']: item['fieldValue']}
                        if 'isPII' in item:
                            obj['isPII'] = bool(item['isPII'])
                        norm.append(obj)
                    else:
                        norm.append(item)
            if norm:
                payload['metadata'] = norm
        
        return await self.make_api_request('/v2/payouts', 'POST', payload)
    
    # Version-aware payout initiation
    async def initiate_payout_auto(self, args: Dict[str, Any]):
        if self.api_version == 'v2':
            return await self.initiate_payout_v2(
                args.get('payoutId'),
                args.get('amount'),
                args.get('currency'),
                args.get('recipientMsisdn'),
                args.get('provider'),
                args.get('customerMessage'),
                args.get('metadata', [])
            )
        
        return await self.initiate_payout(
            args.get('payoutId'),
            args.get('amount'),
            args.get('currency'),
            args.get('correspondent'),
            args.get('recipientMsisdn'),
            args.get('statementDescription', 'Payout to customer'),
            args.get('metadata', [])
        )
    
    # V1 - Initiate Refund
    async def initiate_refund(self, refund_id: str, deposit_id: str, amount: str, metadata: List = []):
        data = {
            'refundId': refund_id,
            'depositId': deposit_id,
            'amount': amount
        }
        
        if metadata:
            data['metadata'] = metadata
        
        return await self.make_api_request('/refunds', 'POST', data)
    
    # V2 - Initiate Refund
    async def initiate_refund_v2(self, refund_id: str, deposit_id: str, amount: str,
                                 currency: str, metadata: List = []):
        payload = {
            'refundId': refund_id,
            'depositId': deposit_id,
            'amount': amount,
            'currency': currency
        }
        
        if metadata and len(metadata) > 0:
            norm = []
            for item in metadata:
                if item and isinstance(item, dict):
                    if 'fieldName' in item and 'fieldValue' in item:
                        obj = {item['fieldName']: item['fieldValue']}
                        if 'isPII' in item:
                            obj['isPII'] = bool(item['isPII'])
                        norm.append(obj)
                    else:
                        norm.append(item)
            if norm:
                payload['metadata'] = norm
        
        return await self.make_api_request('/v2/refunds', 'POST', payload)
    
    # Version-aware refund initiation
    async def initiate_refund_auto(self, args: Dict[str, Any]):
        if self.api_version == 'v2':
            return await self.initiate_refund_v2(
                args.get('refundId'),
                args.get('depositId'),
                args.get('amount'),
                args.get('currency'),
                args.get('metadata', [])
            )
        
        return await self.initiate_refund(
            args.get('refundId'),
            args.get('depositId'),
            args.get('amount'),
            args.get('metadata', [])
        )
    
    # Meta endpoints - V1
    async def check_mno_availability(self):
        return await self.make_api_request('/availability', 'GET')
    
    async def check_active_conf(self):
        return await self.make_api_request('/active-conf', 'GET')
    
    # Meta endpoints - V2
    async def check_mno_availability_v2(self, country: Optional[str] = None,
                                        operation_type: Optional[str] = None):
        query = {}
        if country:
            query['country'] = country
        if operation_type:
            query['operationType'] = operation_type
        
        return await self.make_api_request('/v2/availability', 'GET', query if query else None)
    
    async def check_active_conf_v2(self, country: Optional[str] = None,
                                   operation_type: Optional[str] = None):
        query = {}
        if country:
            query['country'] = country
        if operation_type:
            query['operationType'] = operation_type
        
        return await self.make_api_request('/v2/active-conf', 'GET', query if query else None)
    
    # Version-aware meta endpoints
    async def check_mno_availability_auto(self, country: Optional[str] = None,
                                          operation_type: Optional[str] = None):
        if self.api_version == 'v2':
            return await self.check_mno_availability_v2(country, operation_type)
        return await self.check_mno_availability()
    
    async def check_active_conf_auto(self, country: Optional[str] = None,
                                     operation_type: Optional[str] = None):
        if self.api_version == 'v2':
            return await self.check_active_conf_v2(country, operation_type)
        return await self.check_active_conf()
    
    # Transaction status - V1
    async def check_transaction_status(self, transaction_id: str, type: str = "deposit"):
        if type == "remittance":
            raise Exception("Remittance status is only available in API v2.")
        
        if type == "payout":
            endpoint = f'/payouts/{transaction_id}'
        elif type == "refund":
            endpoint = f'/refunds/{transaction_id}'
        else:
            endpoint = f'/deposits/{transaction_id}'
        
        return await self.make_api_request(endpoint, 'GET')
    
    # Transaction status - V2
    async def check_transaction_status_v2(self, transaction_id: str, type: str = "deposit"):
        if type == "payout":
            endpoint = f'/v2/payouts/{transaction_id}'
        elif type == "refund":
            endpoint = f'/v2/refunds/{transaction_id}'
        elif type == "remittance":
            endpoint = f'/v2/remittances/{transaction_id}'
        else:
            endpoint = f'/v2/deposits/{transaction_id}'
        
        return await self.make_api_request(endpoint, 'GET')
    
    # Version-aware transaction status
    async def check_transaction_status_auto(self, transaction_id: str, type: str = "deposit"):
        if self.api_version == 'v2':
            return await self.check_transaction_status_v2(transaction_id, type)
        return await self.check_transaction_status(transaction_id, type)
    
    # Payment Page Session - V1
    async def create_payment_page_session(self, params: Dict[str, Any]):
        required = ['depositId', 'returnUrl', 'statementDescription']
        for key in required:
            if not params.get(key):
                raise Exception(f"Missing required parameter: {key}")
        
        payload = {
            'depositId': str(params['depositId']),
            'returnUrl': str(params['returnUrl']),
            'statementDescription': str(params['statementDescription']),
            'language': params.get('language', 'EN')
        }
        
        optional = ['amount', 'msisdn', 'country', 'reason']
        for key in optional:
            if key in params and params[key] not in (None, ''):
                payload[key] = params[key]
        
        if 'metadata' in params and isinstance(params['metadata'], list):
            payload['metadata'] = params['metadata']
        
        return await self.make_api_request('/v1/widget/sessions', 'POST', payload)
    
    # Payment Page Session - V2
    async def create_payment_page_session_v2(self, params: Dict[str, Any]):
        required = ['depositId', 'returnUrl']
        for key in required:
            if not params.get(key):
                raise Exception(f"Missing required parameter: {key}")
        
        payload = {
            'depositId': str(params['depositId']),
            'returnUrl': str(params['returnUrl'])
        }
        
        # Customer message
        if params.get('customerMessage'):
            payload['customerMessage'] = str(params['customerMessage'])
        elif params.get('statementDescription'):
            payload['customerMessage'] = str(params['statementDescription'])
        
        # Amount details
        if params.get('amountDetails') and isinstance(params['amountDetails'], dict):
            ad = params['amountDetails']
            if ad.get('amount') and ad.get('currency'):
                payload['amountDetails'] = {
                    'amount': str(ad['amount']),
                    'currency': str(ad['currency'])
                }
        elif params.get('amount') and params.get('currency'):
            payload['amountDetails'] = {
                'amount': str(params['amount']),
                'currency': str(params['currency'])
            }
        
        # Phone number
        if params.get('phoneNumber'):
            import re
            payload['phoneNumber'] = re.sub(r'\D', '', str(params['phoneNumber']))
        elif params.get('msisdn'):
            import re
            payload['phoneNumber'] = re.sub(r'\D', '', str(params['msisdn']))
        
        # Optional fields
        optional = ['language', 'country', 'reason']
        for key in optional:
            if params.get(key):
                payload[key] = str(params[key])
        
        # Metadata
        if params.get('metadata') and isinstance(params['metadata'], list):
            norm = []
            for item in params['metadata']:
                if item and isinstance(item, dict):
                    if 'fieldName' in item and 'fieldValue' in item:
                        obj = {item['fieldName']: item['fieldValue']}
                        if 'isPII' in item:
                            obj['isPII'] = bool(item['isPII'])
                        norm.append(obj)
                    else:
                        norm.append(item)
            if norm:
                payload['metadata'] = norm
        
        return await self.make_api_request('/v2/paymentpage', 'POST', payload)
    
    # Version-aware payment page session
    async def create_payment_page_session_auto(self, params: Dict[str, Any]):
        if self.api_version == 'v2':
            return await self.create_payment_page_session_v2(params)
        return await self.create_payment_page_session(params)
    
    async def close(self):
        """Clean up resources"""
        await self._cleanup()
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        if hasattr(self, '_cleanup_task'):
            asyncio.create_task(self._cleanup())