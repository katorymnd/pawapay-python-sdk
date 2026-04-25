# tests/integration/test_payment_flows.py
import pytest
from src.utils.helpers import Helpers

@pytest.mark.asyncio
async def test_v2_deposit_initiation(client):
    """Test full cycle: Python -> Rust signing -> PawaPay Sandbox API"""
    
    # Wait for license validation
    if client._init_task:
        await client._init_task
        
    # Skip actual API call if we don't have a valid test environment license
    if not client._license_valid:
        pytest.skip("Valid license required to test live PawaPay endpoints.")
        
    deposit_id = Helpers.generate_unique_id()
    
    params = {
        'depositId': deposit_id,
        'amount': '1000',
        'currency': 'UGX',
        'payerMsisdn': '256783456789',
        'provider': 'MTN_MOMO_UGA',
        'customerMessage': 'Integration Test',
    }
    
    # This call passes through our bitmask cascade wrapper
    result = await client.initiate_deposit_v2(**params)
    
    assert result['status'] in [200, 202], f"API Error: {result['response']}"
    assert result['response']['depositId'] == deposit_id
    assert result['response']['status'] == 'ACCEPTED'

@pytest.mark.asyncio
async def test_transaction_status_check(client):
    """Test fetching status for a non-existent transaction"""
    
    if client._init_task:
        await client._init_task
        
    if not client._license_valid:
        pytest.skip("Valid license required to test live PawaPay endpoints.")
        
    fake_id = Helpers.generate_unique_id()
    result = await client.check_transaction_status_v2(fake_id, type="deposit")
    
    # PawaPay usually returns 404 for unknown IDs, meaning our SDK successfully routed the request
    assert result['status'] in [200, 404]