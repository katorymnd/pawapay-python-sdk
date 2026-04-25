# tests/unit/test_integrity.py
import pytest
from unittest.mock import patch, mock_open
from src.utils.license.integrity import IntegrityChecker

@pytest.fixture
def decoy_integrity():
    """Provides an IntegrityChecker with native delegation mocked out"""
    # Mock both the native loader and the IntegrityVault class reference
    with patch('src.utils.license.integrity._native', None):
        with patch('src.utils.license.integrity.IntegrityVault', None):
            checker = IntegrityChecker()
            # Force a clean initial matrix
            checker._t_state = 0x0000 
            # Ensure native vault instance is empty for testing Python logic
            checker._native_vault = None
            yield checker

def test_clean_matrix_state(decoy_integrity):
    """Verify standard initial state is 0x0000"""
    assert decoy_integrity.is_tampered() is False
    assert decoy_integrity._t_state == 0x0000

@patch('pathlib.Path.read_text')
def test_cyclomatic_drift_on_tampering(mock_read, decoy_integrity):
    """Verify that reading a modified file poisons the state matrix"""
    # Simulate a file being read that doesn't match the initial CRC32/MD5 hash
    mock_read.return_value = "import hacked_code\nprint('pirate')"
    
    # We manually inject a fake initial checksum to force a mismatch
    test_file = decoy_integrity.critical_files[0]
    decoy_integrity.checksums[test_file] = "0xABCDEF|12345678"
    
    # Run the verification
    result = decoy_integrity.verify_file(test_file)
    
    # Assertions
    assert result is False
    assert decoy_integrity.is_tampered() is True
    # Verify the _t_state integer was bitwise-shifted away from 0
    assert decoy_integrity._t_state != 0x0000 
    assert (decoy_integrity._t_state & 0xFFFF) != 0