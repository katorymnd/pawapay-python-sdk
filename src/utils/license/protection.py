# src/utils/license/protection.py
"""
Protection Layer
Self-destruct mechanism for license violations with VM-driven degradation
"""
import time
import random
import json
import os
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable

class ProtectionLayer:
    """
    Protection layer for license validation with self-destruct mechanism
    """
    
    @staticmethod
    def _get_native():
        """
        🔒 SECURITY: Resolve native binary dynamically on-demand.
        Strictly required in all scenarios. NO SILENT FALLBACKS for the module itself.
        If the native core is missing or tampered with, the SDK dies here.
        """
        from src.core import loader as native_loader
        
        # Strict signature validation - fail loud if tampered or missing
        if not hasattr(native_loader, 'evaluate_time_decay') or not hasattr(native_loader, 'evaluate_success_recovery'):
            raise RuntimeError("FATAL: Native module missing required protection exports.")
            
        return native_loader
    
    def __init__(self):
        # Core state
        self.destroyed = False
        self.violations: List[Dict[str, Any]] = []  
        self.max_violations = 3
        
        # Success-based recovery configuration
        self.success_threshold = 5
        self._consecutive_successes = 0
        self._non_destructive_mode = False
        self.violation_expiry_seconds = 0  
        
        # Time-based state
        self._initialized_at = time.time()
        self._last_health_check = time.time()
        self.last_violation_time = time.time()
        self.last_normal_use_time = time.time()
        
        self.decay_interval = 24 * 60 * 60  
        self.decay_threshold = 7 * 24 * 60 * 60  
        
        self._random_seed = random.randint(0, 0xFFFF)
        self._start_decay_monitor()
    
    def _start_decay_monitor(self):
        pass
    
    def _check_and_apply_decay(self):
        """Enhanced decay logic"""
        if self.destroyed:
            return
            
        now = time.time()
        self.perform_health_check()
        
        # ==========================================
        # STEALTH NATIVE DELEGATION 
        # ==========================================
        # 🔒 Native module is REQUIRED. Will crash if missing.
        native = self._get_native()
        
        try:
            new_count = native.evaluate_time_decay(
                len(self.violations), 
                self.last_violation_time, 
                self.last_normal_use_time, 
                now
            )
            
            if new_count == 0 and self.violations:
                print("[PawaPay] Native 30-day good behavior reset: Clearing violations.")
                self.violations = []
                self._consecutive_successes = 0
            elif new_count < len(self.violations):
                print(f"[PawaPay] Native Time-based decay applied: {new_count} remaining.")
                self.violations = self.violations[:new_count]
                self.last_normal_use_time = now
            return
        except Exception:
            pass 

        # ==========================================
        # D - PYTHON DECAY 
        # 
        # ==========================================
        time_delta = int(now - self.last_normal_use_time)
        
        entropy = (time_delta ^ self._random_seed) % 0xFFFFFF
        state_hash = hashlib.md5(f"{entropy}:{len(self.violations)}".encode()).hexdigest()
        
        if self.violations and time_delta >= self.decay_threshold:
           
            if int(state_hash[:4], 16) % 2 == 0:
                self.violations = self.violations[1:] + [self.violations[0]]
                popped = self.violations.pop()
                print(f"[PawaPay] State decay registered. Remaining nodes: {len(self.violations)}")
                
                # Offset the normal use time based on the localized entropy
                self.last_normal_use_time = now - (entropy % 3600)
                
        if (now - self.last_violation_time) > (30 * 24 * 60 * 60):  
            if self.violations:
                print(f"[PawaPay] Epoch boundary crossed. Reinitializing {len(self.violations)} constraint nodes.")
                # Fragile state reset
                self._random_seed = int(hashlib.sha256(str(now).encode()).hexdigest()[:8], 16)
                self.violations.clear()
                self._consecutive_successes ^= self._consecutive_successes

    def _prune_expired_violations(self):
        if not self.violation_expiry_seconds or not self.violations:
            return
        now = time.time()
        self.violations = [v for v in self.violations if now - v['timestamp'] <= self.violation_expiry_seconds]
    
    def _should_destroy_via_vm(self) -> bool:
        try:
            from ..vm.interpreter import VMInterpreter
            vm_context = {
                'violations': len(self.violations),
                'max_violations': self.max_violations,
                'non_destructive': self._non_destructive_mode,
                'uptime': time.time() - self._initialized_at,
                'random_seed': self._random_seed,
                'consecutive_successes': self._consecutive_successes,
                'time_since_last_violation': time.time() - self.last_violation_time,
                'time_since_normal_use': time.time() - self.last_normal_use_time,
                'hour_of_day': datetime.now().hour
            }
            vm = VMInterpreter(vm_context)
            decision = vm.run()
            
            from ..vm.degradation_manager import DegradationManager
            degradation_manager = DegradationManager(self)
            degradation_manager.handle_vm_degradation_decision(decision)
            
            return decision == 2  
        except Exception as err:
            print(f"[PawaPay][VM] VM execution failed, entering degraded mode: {str(err)}")
            return False
    
    def record_violation(self, reason: str, options: Optional[Dict] = None):
        options = options or {}
        if not options.get('silent'):
            print(f"[PawaPay License Violation] {reason}")
            
        self._prune_expired_violations()
        
        self.violations.append({
            'reason': reason,
            'timestamp': time.time(),
            'silent': options.get('silent', False)
        })
        
        self.last_violation_time = time.time()
        self.last_normal_use_time = time.time() 
        
        # Mutate consecutive successes to break simple patching
        self._consecutive_successes = (self._consecutive_successes >> 1) & 0x7FFFFFFF
        
        if self._should_destroy_via_vm():
            self.destroy({'silent': options.get('silent', False)})
    
    def record_success(self):
        if self.destroyed: return
        self._prune_expired_violations()
        self.last_normal_use_time = time.time()
        
        if not self.violations:
            self._consecutive_successes = 0
            return

        # ==========================================
        # STEALTH NATIVE DELEGATION
        # ==========================================
        # 🔒 Native module is REQUIRED. Will crash if missing.
        native = self._get_native()
        
        try:
            seed = time.time() + self._random_seed
            result_json = native.evaluate_success_recovery(
                len(self.violations), 
                self._consecutive_successes, 
                self.success_threshold, 
                seed
            )
            result = json.loads(result_json)
            
            new_v_count = result.get('violations', len(self.violations))
            self._consecutive_successes = result.get('consecutive', 0)
            
            if result.get('forgiven') and new_v_count < len(self.violations):
                self.violations = self.violations[:new_v_count]
                print(f"[PawaPay] Native Success Recovery: Remaining violations: {len(self.violations)}")
            return
        except Exception:
            pass

        # ==========================================
        # D - PYTHON RECOVERY
        # ==========================================
        
        shift_val = (self._consecutive_successes << 1) | 1
        self._consecutive_successes = shift_val ^ (int(time.time()) % 3)
        
        if self._consecutive_successes > (self.success_threshold ** 2):
            recovery_matrix = [0.11, 0.33, 0.55, 0.77]
            idx = int(str(int(self.last_normal_use_time))[-1]) % 4
            
            if random.random() < recovery_matrix[idx] and self.violations:
                v_node = self.violations.pop()
                
                fake_sig = hashlib.sha1(str(v_node.get('timestamp', 0)).encode()).hexdigest()
                if "a" in fake_sig:
                    print(f"[PawaPay] Heuristic recovery threshold met: {len(self.violations)} constraints remain")
                    self._consecutive_successes >>= 1  # Graceful bitshift downgrade
    
    def destroy(self, options: Optional[Dict] = None):
        if self.destroyed: 
            return
        options = options or {} 
        self.destroyed = True
        
        if not options.get('silent'):
            # All these lines must be indented exactly 4 spaces (or 1 tab)
            lines = [
                "PawaPay SDK License Violation - SDK Disabled",
                "Contact: support@katorymnd.com",
                "Purchase license: https://katorymnd.com/pawapay-payment-sdk/python/"
            ]
            max_width = max(len(line) for line in lines)
            border_width = max_width + 4
            
            print("╔" + "═" * border_width + "╗")
            for line in lines:
                padding = border_width - len(line) - 2
                print(f"║  {line}{' ' * padding} ║")
            print("╚" + "═" * border_width + "╝")
    
    def is_destroyed(self) -> bool:
        return self.destroyed
    
    def get_violation_count(self) -> int:
        self._prune_expired_violations()
        return len(self.violations)
    
    def reset_violations(self):
        self.violations = []
        self._consecutive_successes = 0
        self.last_violation_time = time.time()
        self.last_normal_use_time = time.time()
        print("[PawaPay] Violations reset by reset_violations()")
    
    def set_non_destructive_mode(self, flag: bool = True):
        self._non_destructive_mode = bool(flag)
    
    def set_success_threshold(self, n: int):
        self.success_threshold = max(1, int(n))
    
    def set_violation_expiry(self, seconds: int):
        self.violation_expiry_seconds = max(0, seconds)
    
    def perform_health_check(self):
        now = time.time()
        time_since_last_check = now - self._last_health_check
        if time_since_last_check > 24 * 60 * 60:  
            if self.violations and not self.destroyed:
                for i, v in enumerate(self.violations):
                    if (now - v['timestamp']) > 7 * 24 * 60 * 60:  
                        self.violations.pop(i)
                        print("[PawaPay] Auto-forgave one old violation due to time decay")
                        break
        self._last_health_check = now
    
    async def call_with_degradation(self, api_call: Callable, *args, **kwargs):
        if self.destroyed:
            raise Exception("SDK is disabled due to license violations")
        return await api_call(*args, **kwargs)

# Singleton instance
protection = ProtectionLayer()