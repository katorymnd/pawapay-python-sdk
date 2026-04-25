# src/utils/vm/interpreter.py
"""
VM Interpreter with Imprint-bound bytecode and shuffled opcodes
"""
import json
import os
import hashlib
import uuid
import time
from pathlib import Path
from typing import Dict, Any, List

# Standard library for AES CTR decryption (requires 'cryptography' package usually used in SDKs)
try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
except ImportError:
    pass


from katorymnd_pawapay_core import (
    derive_vm_hardware_key, 
    execute_vm_core,
    verify_request_state,
    get_pawapay_base_url
)


class ImprintBoundVM:
    def __init__(self):
        self.bytecode_cache = None
        self.opcodes = None
        self.imprint_hash = None
        self._initialize_imprint()

    def _initialize_imprint(self):
        imprint_path = Path.cwd() / '.pawapay-imprint'
        try:
            if imprint_path.exists():
                self.imprint = imprint_path.read_text(encoding='utf-8').strip()
                print(f"[PawaPay][VM] Loaded imprint from: {imprint_path}")
            else:
                self.imprint = "temp-" + str(uuid.uuid4())
                print("[PawaPay][VM] Generated temporary imprint")

            project_path = str(Path.cwd())
            imprint_hash_input = f"IMPRINT-HASH:{self.imprint}:{project_path}"
            self.imprint_hash = hashlib.sha256(imprint_hash_input.encode('utf-8')).hexdigest()[:16]
            
        except Exception as err:
            self.imprint = f"error-{int(time.time())}"
            self.imprint_hash = "error"

    def _get_or_create_imprint(self) -> str:
        if self.imprint and not self.imprint.startswith('temp-') and not self.imprint.startswith('error-'):
            return self.imprint
        
        imprint_path = Path.cwd() / '.pawapay-imprint'
        try:
            if imprint_path.exists():
                return imprint_path.read_text(encoding='utf-8').strip()
        except:
            pass
            
        return self.imprint or "unknown-imprint"

    def _get_minimal_hardware_hint(self) -> str:
        try:
            import platform
            hostname = platform.node() or "unknown"
            return f"h:{hostname[:8]},a:{platform.machine()[:2]}"
        except:
            return "hw-unknown"

    def load_bytecode(self):
        if self.bytecode_cache:
            return

        try:
            bytecode_path = Path(__file__).parent / 'bytecode.bin'
            raw = bytecode_path.read_text(encoding='utf-8')
            compiled = json.loads(raw)

            if compiled.get('imprint') and compiled['imprint'] != self.imprint_hash:
                raise ValueError("Invalid installation")

            # 🚨 THE HEART SURGERY: Key derivation is now secure
            decryption_key_hex = self._generate_decryption_key()
            print("[PawaPay][VM] Native decryption key secured.")

            decryption_key = bytes.fromhex(decryption_key_hex)
            iv = bytes.fromhex(compiled['data']['iv'])
            cipher_content = bytes.fromhex(compiled['data']['content'])

            cipher = Cipher(algorithms.AES(decryption_key), modes.CTR(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            decrypted = decryptor.update(cipher_content) + decryptor.finalize()

            self.bytecode_cache = json.loads(decrypted.decode('utf-8'))
            self.opcodes = self._load_shuffled_opcodes()

        except Exception as error:
            print(f"[PawaPay][VM] Failed to load bytecode: {str(error)}")
            self.bytecode_cache = self._get_self_destruct_bytecode()
            self.opcodes = self._get_default_opcodes()

    def _load_shuffled_opcodes(self) -> Dict[str, int]:
        try:
            opcodes_path = Path(__file__).parent / 'opcodes.json'
            if opcodes_path.exists():
                cached = json.loads(opcodes_path.read_text(encoding='utf-8'))
                if cached.get('imprintHash') == self.imprint_hash:
                    return cached['opcodes']

            from .bytecode_encoder import BytecodeEncoder
            encoder = BytecodeEncoder()
            opcodes = encoder.generate_shuffled_opcodes()
            
            cache_data = {
                'imprintHash': self.imprint_hash,
                'generatedAt': int(time.time()),
                'opcodes': opcodes
            }
            opcodes_path.write_text(json.dumps(cache_data, indent=2), encoding='utf-8')
            return opcodes
            
        except Exception:
            return self._get_default_opcodes()

    def _generate_decryption_key(self) -> str:
        imprint = self._get_or_create_imprint()
        project_path = str(Path.cwd())
        hardware_hint = self._get_minimal_hardware_hint()

        if not derive_vm_hardware_key:
            raise RuntimeError("Native core missing")
            
        return derive_vm_hardware_key(imprint, project_path, hardware_hint)

    def _get_self_destruct_bytecode(self) -> Dict[str, Any]:
        default_ops = self._get_default_opcodes()
        return {
            'entry': 0,
            'code': [
                {'op': default_ops['PUSH_CONST'], 'arg': 2},
                {'op': default_ops['RETURN']}
            ]
        }

    def _get_default_opcodes(self) -> Dict[str, int]:
        return {
            'PUSH_CONST': 0x10, 'PUSH_STATE': 0x11, 'CMP_GT': 0x12, 'CMP_EQ': 0x13, 
            'AND': 0x14, 'OR': 0x15, 'NOT': 0x16, 'JUMP_IF_FALSE': 0x17, 
            'JUMP': 0x18, 'RETURN': 0x19
        }

vm_loader = ImprintBoundVM()

class VMInterpreter:
    def __init__(self, context: Dict[str, Any]):
        self.context = context
        self.vm_loader = vm_loader
        self.vm_loader.load_bytecode()
        self.code = self.vm_loader.bytecode_cache.get('code', [])
        self.opcodes = self.vm_loader.opcodes

    def run(self) -> int:
        try:
            if not execute_vm_core:
                raise RuntimeError("Native core missing")

            return execute_vm_core(
                json.dumps(self.code),
                json.dumps(self.opcodes or self.vm_loader._get_default_opcodes()),
                json.dumps(self.context or {})
            )
        except Exception as error:
            print(f"[PawaPay][VM] Core Execution Failed: {str(error)}")
            return 2  # Default to DESTROY signal on failure

    def debug_bytecode(self):
        print("\n[PawaPay][VM] Bytecode Native Link Active.")
        print(f"Context sent to core: {self.context}")