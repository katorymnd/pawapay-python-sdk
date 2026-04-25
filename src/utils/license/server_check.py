# src/utils/license/server_check.py
"""
Katorymnd License Server Integration
Validates license with https://katorymnd.com/api/appLicense/
"""
import os  
import json
import ssl
import uuid
import hashlib
import hmac
import base64
import time
import socket
import platform
from pathlib import Path
from typing import Dict, Any, Optional
import aiohttp
import certifi

class ServerValidator:
    """Server-side license validator"""
    
    @staticmethod
    def _get_native():
        
        from src.core import loader as native_loader
        
        # Strict signature validation - fail loud if tampered or missing
        required_exports = ['create_signed_headers', 'sign_session_data', 'generate_server_fingerprint']
        for export in required_exports:
            if not hasattr(native_loader, export):
                raise RuntimeError(f"FATAL: Native module missing required security export: {export}")
            
        return native_loader
    
    def __init__(self):
        self.base_url = "https://katorymnd.com/api/appLicense"
        
        # Configuration
        self.validation_interval = 24 * 60 * 60  
        self.heartbeat_interval = 60 * 60  
        self.grace_period = 7 * 24 * 60 * 60  
        
        # State
        self.activated = False
        self.domain = self._get_domain()
        
        self.installation_imprint = self._get_or_create_imprint()
        
        self.last_validation = self._load_session()
        self.last_heartbeat = time.time()
    
    def _create_signed_headers(self, payload_str: str, license_key: str) -> Dict[str, str]:
        """Helper to generate signed headers for Cloudflare bypass - STRICTLY NATIVE"""
        native = self._get_native()
        headers_json = native.create_signed_headers(payload_str, license_key, self.installation_imprint, "1.0.0")
        return json.loads(headers_json)
    
    async def validate_and_activate(self, license_key: str) -> Dict[str, Any]:
        """Validate license and activate domain"""
        try:
            validation_result = await self._validate_license(license_key)
            
            needs_activation = (
                not validation_result.get('valid') and
                (validation_result.get('reason') == 'activation_required' or
                 validation_result.get('status') == 422)
            )
            
            if not validation_result.get('valid') and not needs_activation:
                return validation_result
            
            if needs_activation:
                print("[PawaPay License] Activation required. Proceeding...")
            
            activation_result = await self._activate_domain(license_key)
            
            if not activation_result.get('success'):
                return {'valid': False, 'reason': activation_result.get('message')}
            
            self.activated = True
            self.last_validation = time.time()
            self.last_heartbeat = time.time()
            self._save_session() 
            
            return {
                'valid': True,
                'activated': True,
                'data': activation_result.get('data')
            }
            
        except Exception as error:
            print(f"[PawaPay License] Validation error: {str(error)}")
            if self._allow_offline_use():
                return {'valid': True, 'offline': True}
            else:
                return {
                    'valid': False,
                    'reason': 'License validation failed & Offline grace period expired'
                }
    
    async def _validate_license(self, license_key: str) -> Dict[str, Any]:
        payload = {
            'license_key': license_key,
            'product': 'pawapay-python-sdk',
            'version': '2.1.1',
            'metadata': {
                'pythonVersion': f"{os.sys.version_info.major}.{os.sys.version_info.minor}",
                'platform': os.sys.platform,
                'hostname': self.domain
            }
        }
        
        payload_str = json.dumps(payload)
        headers = self._create_signed_headers(payload_str, license_key)
        
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        timeout = aiohttp.ClientTimeout(total=10)
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.base_url}/validate",
                    data=payload_str,
                    headers=headers,
                    ssl=ssl_context,
                    timeout=timeout
                ) as response:
                    data = await response.text()
                    if response.status == 200:
                        result = json.loads(data)
                        if result.get('valid'):
                            return {'valid': True, 'data': result, 'status': 200}
                        else:
                            return {
                                'valid': False,
                                'reason': result.get('reason') or result.get('message') or 'License validation failed',
                                'status': response.status
                            }
                    else:
                        result = json.loads(data) if data else {}
                        return {
                            'valid': False,
                            'reason': result.get('reason') or result.get('message') or f'HTTP {response.status}',
                            'status': response.status
                        }
            except Exception as e:
                raise Exception(f"License validation failed: {str(e)}")
    
    async def _activate_domain(self, license_key: str) -> Dict[str, Any]:
        fingerprint = self._generate_server_fingerprint()
        
        payload = {
            'license_key': license_key,
            'domain': self.domain,
            'server_fingerprint': fingerprint,
            'installation_imprint': self.installation_imprint,
            'metadata': {
                'sdk_version': '2.1.1',
                'python_version': f"{os.sys.version_info.major}.{os.sys.version_info.minor}",
                'platform': os.sys.platform,
                'activated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            }
        }
        
        payload_str = json.dumps(payload)
        headers = self._create_signed_headers(payload_str, license_key)
        
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        timeout = aiohttp.ClientTimeout(total=10)
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.base_url}/activate-domain",
                    data=payload_str,
                    headers=headers,
                    ssl=ssl_context,
                    timeout=timeout
                ) as response:
                    data = await response.text()
                    if response.status in (200, 201):
                        result = json.loads(data) if data else {}
                        return {'success': True, 'data': result}
                    else:
                        result = json.loads(data) if data else {}
                        return {
                            'success': False,
                            'message': result.get('message', 'Activation failed')
                        }
            except Exception as e:
                raise Exception(f"Domain activation failed: {str(e)}")
    
    def _load_session(self) -> float:
        """Loads the last validation time from disk using strictly native signature validation."""
        session_path = Path.cwd() / '.pawapay-session'
        try:
            if session_path.exists():
                raw = session_path.read_text(encoding='utf-8')
                session_data = json.loads(base64.b64decode(raw).decode('utf-8'))
                
                native = self._get_native()
                expected_sig = native.sign_session_data(str(session_data['lastValidation']), self.installation_imprint)

                if session_data.get('signature') == expected_sig:
                    return session_data['lastValidation']
                else:
                    print("[PawaPay License] Session file tampering detected. Forcing validation.")
                    return 0  
        except Exception:
            pass
        return 0
    
    def _save_session(self):
        """Saves the current validation time to disk securely using native signatures."""
        session_path = Path.cwd() / '.pawapay-session'
        try:
            native = self._get_native()
            sig = native.sign_session_data(str(self.last_validation), self.installation_imprint)

            data = {
                'lastValidation': self.last_validation,
                'signature': sig
            }
            content = base64.b64encode(json.dumps(data).encode('utf-8')).decode('utf-8')
            session_path.write_text(content, encoding='utf-8')
            try:
                session_path.chmod(0o600)
            except:
                pass
        except Exception as err:
            print(f"[PawaPay License] Failed to persist session: {str(err)}")
    
    def _get_or_create_imprint(self) -> str:
        imprint_path = Path.cwd() / '.pawapay-imprint'
        try:
            if imprint_path.exists():
                return imprint_path.read_text(encoding='utf-8').strip()
            
            new_imprint = str(uuid.uuid4())
            imprint_path.write_text(new_imprint, encoding='utf-8')
            try:
                imprint_path.chmod(0o600)
            except:
                pass
            print("[PawaPay License] Initialized secure installation imprint.")
            return new_imprint
        except Exception as err:
            print(f"[PawaPay License] Could not access imprint file: {str(err)}")
            return "memory-" + str(uuid.uuid4())
    
    async def send_heartbeat(self, license_key: str) -> bool:
        try:
            fingerprint = self._generate_server_fingerprint()
            payload = {
                'license_key': license_key,
                'domain': self.domain,
                'server_fingerprint': fingerprint,
                'installation_imprint': self.installation_imprint,
                'metadata': {
                    'sdk_version': '2.1.1',
                    'uptime': time.time() - self.last_heartbeat
                }
            }
            
            payload_str = json.dumps(payload)
            headers = self._create_signed_headers(payload_str, license_key)
            
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            timeout = aiohttp.ClientTimeout(total=5)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/heartbeat",
                    data=payload_str,
                    headers=headers,
                    ssl=ssl_context,
                    timeout=timeout
                ) as response:
                    if response.status == 200:
                        data = await response.text()
                        result = json.loads(data) if data else {}
                        if result.get('ok'):
                            self.last_heartbeat = time.time()
                            self.last_validation = time.time()
                            self._save_session()
                            return True
            return False
            
        except Exception:
            return False
    
    async def check_status(self, license_key: str) -> Dict[str, Any]:
        if os.environ.get('PAWAPAY_DEV_MODE') == 'true':
            return {'active': True, 'valid': True}
        
        # Fixed authentication signature for status endpoint
        b64_key = base64.b64encode(license_key.encode('utf-8')).decode('utf-8')
        signature = hashlib.sha512(f"STATUS_CHECK:{b64_key}".encode('utf-8')).hexdigest()[:64]
        
        headers = {
            'User-Agent': 'PawaPay-PythonSDK/2.1.1',
            'X-PawaPay-Imprint': self.installation_imprint,
            'X-PawaPay-Signature': signature,
            'Accept': 'application/json'
        }
        
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        timeout = aiohttp.ClientTimeout(total=5)
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{self.base_url}/status/{license_key}",
                    headers=headers,
                    ssl=ssl_context,
                    timeout=timeout
                ) as response:
                    data = await response.text()
                    return json.loads(data) if data else {}
                    
            except Exception as e:
                raise Exception(f"Status check failed: {str(e)}")
    
    def _get_domain(self) -> str:
        domain = os.environ.get('PAWAPAY_SDK_LICENSE_DOMAIN', '').strip()
        if domain:
            return domain
        raise Exception("[PawaPay License] Missing PAWAPAY_SDK_LICENSE_DOMAIN.")
    
    def _allow_offline_use(self) -> bool:
        time_since_last_validation = time.time() - self.last_validation
        allowed = time_since_last_validation < self.grace_period
        
        if time_since_last_validation < 0:
            return False  # Anti-tamper check for future dates
        
        if not allowed:
            print("[PawaPay License] Offline grace period expired.")
        else:
            print("[PawaPay License] Operating in offline mode.")
        
        return allowed
    
    def _generate_server_fingerprint(self) -> str:
        """Generate server fingerprint - STRICTLY NATIVE"""
        try:
            project_path = str(Path.cwd())
            print(f"[PawaPay License] Path Locking active for: {project_path}")
            
            hostname = platform.node() or "unknown"
            
            try:
                mac_int = uuid.getnode()
                mac_address = ':'.join(('%012X' % mac_int)[i:i+2] for i in range(0, 12, 2))
            except Exception:
                mac_address = "nomac"
            
            machine_id = f"{platform.system()}-{platform.release()}-{platform.version()}"
            total_mem = "0" 
            
            native = self._get_native()
            return native.generate_server_fingerprint(project_path, hostname, mac_address, machine_id, total_mem)
            
        except Exception as err:
            print(f"[PawaPay License] Failed to generate server fingerprint: {str(err)}")
            fallback_raw = f"fbp-sys:{platform.node() or 'unknown'}-dir:{Path.cwd()}"
            return hashlib.sha256(fallback_raw.encode('utf-8')).hexdigest()

# Singleton instance
server_check = ServerValidator()