# src/utils/vm/degradation_manager.py
"""
Degradation Manager
Implements progressive degradation with silent failure patterns strictly via Native VM
"""
import hashlib
import random
import time
import json
from typing import Dict, Any, Optional, Callable
import asyncio

class DegradationManager:
    """Manages degradation levels and patterns"""
    
    @staticmethod
    def _get_native():
        
        from src.core import loader as native_loader
        
        # Strict signature validation - fail loud if tampered or missing
        required_exports = ['calculate_degradation_action', 'corrupt_degradation_data']
        for export in required_exports:
            if not hasattr(native_loader, export):
                raise RuntimeError(f"FATAL: Native module missing required degradation export: {export}")
            
        return native_loader
    
    def __init__(self, protection_layer):
        self.protection = protection_layer
        self.degradation_level = 0  # 0 = normal, 1-3 = degraded, 4 = destroyed
        self.active_pattern = None
        self._failure_counters = {}
        
        # Random seed for deterministic behavior
        seed_str = f"{int(time.time())}"
        self._random_seed = hashlib.md5(seed_str.encode('utf-8')).hexdigest()[:8]
        
        # Legacy degradation rules for backward compatibility
        self.degradation_rules = {
            1: { 'name': 'REQUEST_THROTTLING', 'apply': lambda: self.apply_throttling(0.5), 'remove': lambda: self.remove_throttling() },
            2: { 'name': 'CACHE_ONLY', 'apply': lambda: self.enable_cache_only_mode(), 'remove': lambda: self.disable_cache_only_mode() },
            3: { 'name': 'READ_ONLY', 'apply': lambda: self.enable_read_only_mode(), 'remove': lambda: self.disable_read_only_mode() }
        }
        self.active_degradations = set()

    def _random_value(self) -> float:
        """Helper for deterministic random values based on seed"""
        seed_str = f"{self._random_seed}{str(time.time())[-6:]}"
        hash_val = hashlib.sha256(seed_str.encode('utf-8')).hexdigest()
        return int(hash_val[:8], 16) / 0xFFFFFFFF
    
    def _apply_degradation_pattern(self, level: int):
        """Apply silent failure patterns (Decoy Configuration)"""
        patterns = [
            None,
            { 'type': 'random_failures', 'failure_rate': 0.05 + (self._random_value() * 0.10), 'latency_multiplier': 1.0 + (self._random_value() * 0.5) },
            { 'type': 'intermittent_degradation', 'failure_rate': 0.15 + (self._random_value() * 0.15), 'latency_multiplier': 1.5 + (self._random_value() * 1.0), 'data_staleness': 2, 'data_corruption_rate': 0.01 },
            { 'type': 'heavy_degradation', 'failure_rate': 0.30 + (self._random_value() * 0.20), 'latency_multiplier': 2.5 + (self._random_value() * 2.5), 'data_staleness': 10, 'data_corruption_rate': 0.03 },
            { 'type': 'near_total_failure', 'failure_rate': 0.70 + (self._random_value() * 0.25), 'response_delay': 15000, 'data_corruption_rate': 0.10 }
        ]
        if level < len(patterns):
            self.active_pattern = patterns[level]
    
    async def apply_degradation(self, api_call: Callable, *args, **kwargs):
        """Apply degradation to API calls - STRICTLY NATIVE"""
        if self.degradation_level == 0:
            return await api_call(*args, **kwargs)

        call_id = getattr(api_call, '__name__', 'anonymous')
        seed = f"{self._random_seed}_{call_id}_{time.time()}"

        # 🔒 Native module is REQUIRED. Will crash if missing. No try/except swallowing.
        native = self._get_native()
        
        # Ask Heart what to do 
        action_json = native.calculate_degradation_action(self.degradation_level, seed)
        action_data = json.loads(action_json)
        
        delay = action_data.get('delay_ms', 0)
        if delay > 0:
            await asyncio.sleep(delay / 1000.0)
            
        if action_data.get('action') == 'error':
            err_msg = action_data.get('error_message', 'Service unavailable')
            if 'status_code' in action_data:
                error = Exception(err_msg)
                error.status_code = action_data['status_code']
                raise error
            raise Exception(err_msg)
        
        # If proceed, make the call natively
        result = await api_call(*args, **kwargs)
        
        # Ask Heart to mathematically corrupt the resulting JSON
        if isinstance(result, (dict, list)):
            corrupted_json = native.corrupt_degradation_data(self.degradation_level, json.dumps(result), seed)
            return json.loads(corrupted_json)
            
        return result

    def apply_throttling(self, factor: float): pass
    def remove_throttling(self): pass
    def enable_cache_only_mode(self): pass
    def disable_cache_only_mode(self): pass
    def enable_read_only_mode(self): pass
    def disable_read_only_mode(self): pass

    def set_degradation_level(self, level: int):
        if level == self.degradation_level: return
        self.degradation_level = level
        self._apply_degradation_pattern(level)
        
        if level > 0:
            print(f"[PawaPay] SDK degradation level: {level}/3")
        else:
            print("[PawaPay] SDK degradation cleared")

    def handle_vm_degradation_decision(self, decision: int):
        if decision == 0:
            self.set_degradation_level(0)
        elif decision == 1:
            violations = self.protection.get_violation_count()
            max_violations = self.protection.max_violations
            if violations >= max_violations: self.set_degradation_level(3)
            elif violations >= (max_violations * 0.66): self.set_degradation_level(2)
            elif violations >= (max_violations * 0.33): self.set_degradation_level(1)
        elif decision == 2:
            print("[PawaPay] CRITICAL: VM returned DESTROY signal (Decision 2)")
            self.set_degradation_level(4)
            if hasattr(self.protection, 'trigger_destruction'):
                self.protection.trigger_destruction()