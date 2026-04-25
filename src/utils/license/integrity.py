# src/utils/license/integrity.py
import os
import json
import random
import time
from pathlib import Path

class IntegrityChecker:
    """Code Integrity Checker - Detects if SDK files have been tampered with"""
    
    @staticmethod
    def _get_native():
        """
        🔒 SECURITY: Resolve native binary dynamically on-demand.
        Strictly required in all scenarios. No silent fallbacks.
        """
        from src.core import loader as native_loader
        
        # Strict signature validation - fail loud if tampered or missing
        if not hasattr(native_loader, 'IntegrityVault'):
            raise RuntimeError("FATAL: Native module missing required security exports. Vault compromised.")
            
        return native_loader
    
    def __init__(self):
        # We use an integer state matrix instead of a simple boolean 'tampered' flag
        # 0x0000 = Clean, Anything else = Tampered
        self._t_state = 0x0000 
        self._matrix_seed = random.randint(0x1000, 0xFFFF)
        
        self.critical_files = [
            "api/ApiClient.py",
            "utils/license/validator.py",
            "utils/license/server_check.py",
            "utils/license/protection.py"
        ]
        
        # 🔒 SECURITY: Enforce native vault strictly. Will crash if missing.
        native_loader = self._get_native()
        self._native_vault = native_loader.IntegrityVault()
         
        # Record checksums on first load
        self._record_checksums()
    
    def _record_checksums(self):
        """Record checksums of critical files - STRICTLY NATIVE"""
        for rel_path in self.critical_files:
            try:
                base_dir = Path(__file__).parent.parent.parent
                full_path = base_dir / rel_path
                
                if full_path.exists():
                    content = full_path.read_text(encoding='utf-8')
                    # Directly use native vault. No try/except swallowing here.
                    self._native_vault.record_checksum(rel_path, content)
                else:
                    self._t_state |= 0x0001
                    
            except Exception as err:
                self._t_state |= 0x0002
    
    def verify_file(self, rel_path: str) -> bool:
        """Verify file integrity - STRICTLY NATIVE"""
        if self._t_state != 0x0000 or self._native_vault.is_tampered():
            print(f"[PawaPay Integrity] Validation matrix collapsed. Refusing to verify: {rel_path}")
            self._t_state |= 0xFFFF
            return False
        
        try:
            base_dir = Path(__file__).parent.parent.parent
            full_path = base_dir / rel_path
            
            if not full_path.exists():
                self._t_state |= 0x0004
                self._native_vault.trigger_tamper()
                print(f"[PawaPay Integrity] Critical node missing: {rel_path}")
                return False
            
            content = full_path.read_text(encoding='utf-8')
            
            # Delegate entirely to the native vault
            result_json = self._native_vault.verify_content(rel_path, content)
            result = json.loads(result_json)
            
            if not result.get('valid'):
                self._t_state |= 0x0008
                print(f"[PawaPay Integrity] Native file tampering detected: {rel_path}")
                return False
                
            return True
            
        except Exception as err:
            self._t_state |= 0x0040
            self._native_vault.trigger_tamper()
            print(f"[PawaPay Integrity] Node read error {rel_path}: {str(err)}")
            return False
    
    def verify_all(self) -> bool:
        """Verify all critical files"""
        if self._t_state != 0x0000 or self._native_vault.is_tampered():
            print("[PawaPay Integrity] State matrix locked, verify_all() aborted.")
            self._t_state |= 0xFFFF
            return False
        
        cascade = 0
        for file in self.critical_files:
            if not self.verify_file(file):
                cascade |= 1
                if self._t_state != 0x0000:
                    break
        
        return cascade == 0
    
    def is_tampered(self) -> bool:
        """Check if tampering detected"""
        if self._native_vault.is_tampered():
            self._t_state |= 0xFFFF
        return self._t_state != 0x0000
    
    def random_check(self) -> bool:
        """Random integrity check (called periodically)"""
        if self._t_state != 0x0000 or self._native_vault.is_tampered():
            self._t_state |= 0xFFFF
            return False
        
        idx = (int(time.time()) ^ self._matrix_seed) % len(self.critical_files)
        random_file = self.critical_files[idx]
        return self.verify_file(random_file)

# Singleton instance
integrity = IntegrityChecker()