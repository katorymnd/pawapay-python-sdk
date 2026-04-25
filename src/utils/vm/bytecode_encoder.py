# src/utils/vm/bytecode_encoder.py
"""
Bytecode Encoder/Decoder
Uses the superior PawaPay Imprint system for key generation
Imprint is the SOUL - everything revolves around it
"""
import json
import os
import uuid
import hashlib
import time
from pathlib import Path
from typing import Dict, Any, Optional

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding
    from cryptography.hazmat.backends import default_backend
except ImportError:
    pass

class BytecodeEncoder:
    """Bytecode encoder/decoder for VM protection"""
    
    @staticmethod
    def _get_native():
        
        from src.core import loader as native_loader
        
        # Strict signature validation - fail loud if tampered or missing
        required_exports = ['get_internal_logic', 'derive_vm_hardware_key', 'generate_shuffled_opcodes']
        for export in required_exports:
            if not hasattr(native_loader, export):
                raise RuntimeError(f"FATAL: Native module missing required VM export: {export}")
            
        return native_loader
    
    def __init__(self, secret_key: Optional[str] = None):
        self.imprint_path = Path.cwd() / '.pawapay-imprint'
        self.secret_key = secret_key
        self.algorithm = 'AES'
        self.mode = 'CBC'
    
    def _get_key(self) -> str:
        if self.secret_key:
            return self.secret_key
        return self.generate_imprint_based_key()
    
    def generate_client_files(self, output_dir: str) -> bool:
        try:
            print("[PawaPay][VM] Initializing client-side protection...")
            
            imprint = self._get_or_create_imprint()
            print(f"[PawaPay][VM] Bound to Imprint: {imprint[:8]}...")
            
            shuffled_opcodes = self.generate_shuffled_opcodes()
            
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            opcodes_path = output_path / 'opcodes.json'
            self.save_shuffled_opcodes(str(opcodes_path), shuffled_opcodes)
            
            source_logic = self._get_internal_logic(shuffled_opcodes)
            
            bytecode_path = output_path / 'bytecode.bin'
            self.write_encrypted(str(bytecode_path), source_logic)
            
            print("[PawaPay][VM] Client protection successfully imprinted.")
            return True
            
        except Exception as err:
            print(f"[PawaPay][VM] Generation failed: {str(err)}")
            return False

    def _get_internal_logic(self, ops: Dict[str, int]) -> Dict[str, Any]:
        """The internal logic (Hidden Assembly) - STRICTLY NATIVE"""
        native = self._get_native()
        logic_json = native.get_internal_logic(json.dumps(ops))
        return json.loads(logic_json)
    
    def _get_or_create_imprint(self) -> str:
        try:
            if self.imprint_path.exists():
                existing_imprint = self.imprint_path.read_text(encoding='utf-8').strip()
                if existing_imprint: return existing_imprint
            
            print(f"[PawaPay][VM] Creating new imprint at: {self.imprint_path}")
            new_imprint = str(uuid.uuid4())
            
            try:
                self.imprint_path.write_text(new_imprint, encoding='utf-8')
                try: self.imprint_path.chmod(0o600)
                except: pass
                print("[PawaPay][VM] Created new VM bytecode imprint")
            except Exception as write_err:
                print(f"[PawaPay][VM] Write restricted failed: {str(write_err)}")
                self.imprint_path.write_text(new_imprint, encoding='utf-8')
            
            return new_imprint
        except Exception as err:
            print(f"[PawaPay][VM] Could not access imprint file, using in-memory: {str(err)}")
            return "mem-" + str(uuid.uuid4())
    
    def generate_imprint_based_key(self) -> str:
        try:
            imprint = self._get_or_create_imprint()
            return self._derive_key_from_imprint(imprint)
        except Exception as error:
            print(f"[PawaPay][VM] Key gen failed: {str(error)}")
            return self._generate_fallback_key()
    
    def _derive_key_from_imprint(self, imprint: str) -> str:
        """Derive hardware-locked key from imprint - STRICTLY NATIVE"""
        native = self._get_native()
        hw_hint = self._get_minimal_hardware_hint()
        project_path = str(Path.cwd())
        return native.derive_vm_hardware_key(imprint, project_path, hw_hint)
    
    def _get_minimal_hardware_hint(self) -> str:
        try:
            import platform
            hostname = platform.node() or "unknown"
            return f"h:{hostname[:8]},a:{platform.machine()[:2]}"
        except:
            return "hw-unknown"
    
    def _generate_fallback_key(self) -> str:
        fallback_raw = f"fallback:{Path.cwd()}:{int(time.time())}"
        return hashlib.sha256(fallback_raw.encode('utf-8')).hexdigest()[:32]
    
    def encrypt(self, text: str) -> Dict[str, Any]:
        key = self._get_key()
        key_bytes = bytes.fromhex(key)
        
        import secrets
        iv = secrets.token_bytes(16)
        
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(text.encode('utf-8')) + padder.finalize()
        
        cipher = Cipher(algorithms.AES(key_bytes), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        encrypted = encryptor.update(padded_data) + encryptor.finalize()
        
        return {
            'iv': iv.hex(),
            'content': encrypted.hex(),
            'imprint': self._get_imprint_hash()
        }
    
    def decrypt(self, encrypted_data: Dict[str, Any]) -> str:
        if encrypted_data.get('imprint') and encrypted_data['imprint'] != self._get_imprint_hash():
            raise ValueError("VM bytecode is not valid for this installation (Imprint Mismatch)")
        
        key = self._get_key()
        key_bytes = bytes.fromhex(key)
        iv = bytes.fromhex(encrypted_data['iv'])
        content = bytes.fromhex(encrypted_data['content'])
        
        cipher = Cipher(algorithms.AES(key_bytes), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted_padded = decryptor.update(content) + decryptor.finalize()
        
        unpadder = padding.PKCS7(128).unpadder()
        decrypted = unpadder.update(decrypted_padded) + unpadder.finalize()
        return decrypted.decode('utf-8')
    
    def _get_imprint_hash(self) -> str:
        imprint = self._get_or_create_imprint()
        project_path = str(Path.cwd())
        return hashlib.sha256(f"IMPRINT-HASH:{imprint}:{project_path}".encode('utf-8')).hexdigest()[:16]
    
    def compile(self, bytecode_json: Dict[str, Any]) -> Dict[str, Any]:
        json_str = json.dumps(bytecode_json)
        checksum_input = json_str + self._get_imprint_hash()
        checksum = hashlib.sha256(checksum_input.encode('utf-8')).hexdigest()
        
        return {
            'checksum': checksum,
            'timestamp': int(time.time()),
            'version': '2.0',
            'imprint': self._get_imprint_hash(),
            'data': self.encrypt(json_str)
        }
    
    def write_encrypted(self, output_path: str, bytecode_json: Dict[str, Any]):
        compiled = self.compile(bytecode_json)
        Path(output_path).write_text(json.dumps(compiled, indent=2), encoding='utf-8')
        print(f"[PawaPay][VM] Encrypted bytecode written to {output_path}")
    
    def read_encrypted(self, input_path: str) -> Dict[str, Any]:
        raw = Path(input_path).read_text(encoding='utf-8')
        compiled = json.loads(raw)
        
        decrypted = self.decrypt(compiled['data'])
        
        verify_checksum_input = decrypted + (compiled.get('imprint', ''))
        verify_checksum = hashlib.sha256(verify_checksum_input.encode('utf-8')).hexdigest()
        
        if verify_checksum != compiled['checksum']:
            raise ValueError("VM bytecode integrity check failed")
            
        return json.loads(decrypted)
    
    def generate_shuffled_opcodes(self) -> Dict[str, int]:
        """Generate shuffled opcodes based on imprint - STRICTLY NATIVE"""
        native = self._get_native()
        imprint = self._get_or_create_imprint()
        
        print(f"[PawaPay][VM] Shuffling opcodes based on imprint: {imprint[:8]}...")
        opcodes_json = native.generate_shuffled_opcodes(imprint)
        return json.loads(opcodes_json)
    
    def save_shuffled_opcodes(self, output_path: str, shuffled_opcodes: Dict[str, int]) -> bool:
        try:
            cache_data = {
                'imprintHash': self._get_imprint_hash(),
                'generatedAt': int(time.time()),
                'opcodes': shuffled_opcodes
            }
            path = Path(output_path)
            path.write_text(json.dumps(cache_data, indent=2), encoding='utf-8')
            try: path.chmod(0o600)
            except: pass
            print(f"[PawaPay][VM] Saved shuffled opcodes to {output_path}")
            return True
        except Exception as error:
            print(f"[PawaPay][VM] Could not save opcodes: {str(error)}")
            return False