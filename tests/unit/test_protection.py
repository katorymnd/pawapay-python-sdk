# tests/unit/test_protection.py
import pytest
import time
from unittest.mock import patch
from src.utils.license.protection import ProtectionLayer

@pytest.fixture
def decoy_protection():
    """Provides a fresh protection layer with native delegation mocked out"""
    with patch('src.utils.license.protection._native', None):
        layer = ProtectionLayer()
        # Reset any static state
        layer.destroyed = False
        layer.violations = []
        layer._consecutive_successes = 0
        yield layer

def test_violation_recording_triggers_destruction(decoy_protection):
    """Verify that hitting the max violations triggers the SDK destruction"""
    decoy_protection.max_violations = 3
    
    # Simulate 3 violations
    for i in range(3):
        # We patch the VM interpreter so it reliably triggers destruction
        with patch('src.utils.vm.interpreter.VMInterpreter.run', return_value=2):
            decoy_protection.record_violation(f"Test Violation {i}")
            
    assert decoy_protection.is_destroyed() is True
    assert len(decoy_protection.violations) == 3

def test_success_recovery_bitwise_mutation(decoy_protection):
    """Verify that recording success triggers the complex bit-shifting math"""
    decoy_protection._consecutive_successes = 2
    initial_val = decoy_protection._consecutive_successes
    
    decoy_protection.record_success()
    
    # Assert the value mutated. Because of the XOR time-hash in the decoy, 
    # it won't just be '3'. We just need to know the bitshift happened.
    assert decoy_protection._consecutive_successes != initial_val