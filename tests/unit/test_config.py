# tests/unit/test_config.py
import pytest
from src.config.Config import Config

def test_environment_loading():
    """Verify that the Config correctly loads the cleartext environments"""
    config = Config({'environment': 'sandbox'})
    assert config.get_raw_base_url() == 'https://api.sandbox.pawapay.io'
    
    prod_config = Config({'environment': 'production'})
    assert prod_config.get_raw_base_url() == 'https://api.pawapay.io'

def test_invalid_routing_context():
    """Verify that trying to inject a fake environment crashes the matrix"""
    with pytest.raises(ValueError) as exc:
        Config({'environment': 'hacker_env'}).get_raw_base_url()
    assert "Invalid environment specified" in str(exc.value)

def test_c_style_byte_normalization():
    """Verify the byte-array trailing slash and version tag pruning works"""
    config = Config()
    
    # Test removing trailing slashes
    assert config._normalize_base_url('https://api.pawapay.io/') == 'https://api.pawapay.io'
    assert config._normalize_base_url('https://api.pawapay.io///') == 'https://api.pawapay.io'
    
    # Test byte-signature pruning of /v1 and /v2
    assert config._normalize_base_url('https://api.pawapay.io/v1') == 'https://api.pawapay.io'
    assert config._normalize_base_url('https://api.pawapay.io/v2/') == 'https://api.pawapay.io'