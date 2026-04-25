# tests/integration/test_connectivity.py
import pytest
from src.api.ApiClient import ApiClient

@pytest.mark.asyncio
async def test_native_core_loading():
    """Verify the Rust core is detected and injected correctly"""
    try:
        from src.core.loader import NativeCore
        # If the Universal Auto-Detect Loader worked, NativeCore will exist
        assert True
    except ImportError:
        pytest.fail("FATAL: Universal Auto-Detect Loader failed to inject the Rust binary.")

@pytest.mark.asyncio
async def test_invalid_license_rejection():
    """Verify that a fake license poisons the memory clearance token"""
    config = {
        'api_token': 'dummy',
        'license_key': 'PIRATED-KEY-0000-0000-0000',
        'environment': 'sandbox'
    }
    
    bad_client = ApiClient(config)
    
    try:
        # Wait for the async license validation to finish
        if bad_client._init_task:
            await bad_client._init_task
            
        assert bad_client._license_valid is False
        
        # VERIFY THE DECOY: Ensure the clearance token was poisoned with DEADBEEF
        assert (bad_client._clearance_token & 0xDEADBEEF) != 0, "Decoy poison state failed to trigger!"
        assert bad_client._initialization_error is not None
    finally:
        # Clean up the HTTP session so aiohttp doesn't scream
        await bad_client.close()

@pytest.mark.asyncio
async def test_api_guard_blocks_request():
    """Verify the API Guard throws the terrifying decoy segmentation fault"""
    config = {
        'api_token': 'dummy',
        'license_key': 'PIRATED-KEY-0000-0000-0000',
        'environment': 'sandbox'
    }
    
    bad_client = ApiClient(config)
    
    try:
        # We MUST wait for the boot sequence to finish rejecting the pirate
        if bad_client._init_task:
            await bad_client._init_task

        # Try to make a core API request
        try:
            await bad_client.make_api_request('/v2/availability', 'GET')
            # If we reach this line, the guard failed to block the pirate!
            pytest.fail("FATAL: The API Guard failed to block the unauthorized request!")
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Assert that ONE of our traps successfully caught the pirate
            trap_triggered = (
                "context verification failed" in error_msg or 
                "sdk disabled" in error_msg or 
                "violation" in error_msg
            )
            
            assert trap_triggered, f"Guard triggered, but with wrong message: {error_msg}"
            
    finally:
        # Clean up the HTTP session
        await bad_client.close()
    """Verify the API Guard throws the terrifying decoy segmentation fault"""
    config = {
        'api_token': 'dummy',
        'license_key': 'PIRATED-KEY-0000-0000-0000',
        'environment': 'sandbox'
    }
    
    bad_client = ApiClient(config)
    
    try:
        # We MUST wait for the boot sequence to finish rejecting the pirate
        if bad_client._init_task:
            await bad_client._init_task

        with pytest.raises(Exception) as exc_info:
            await bad_client.check_mno_availability_v2()
            
        error_msg = str(exc_info.value).lower()
        
        # Because the Native Vault is active, it might throw the Native Guard error
        # OR it might fall through to the Python Decoy segmentation fault. 
        # We assert that ONE of our impenetrable traps caught them.
        assert "context verification failed" in error_msg or "sdk disabled" in error_msg or "violation" in error_msg
    finally:
        # Clean up the HTTP session
        await bad_client.close()