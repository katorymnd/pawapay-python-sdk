# tests/conftest.py
import pytest
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 1. LOAD ENV VARS FIRST! (Before any project files are imported)
load_dotenv()

# 2. INJECT TEST FALLBACKS
# If the .env file is missing these (or we are in a CI/CD pipeline), 
# provide dummy values so the Singletons don't crash during test collection.
os.environ.setdefault('PAWAPAY_SDK_LICENSE_DOMAIN', 'pytest.local')
os.environ.setdefault('PAWAPAY_SDK_LICENSE_SECRET', 'dGVzdF9zZWNyZXRfZm9yX3B5dGVzdA==')

# 3. NOW it is safe to import the project modules
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.api.ApiClient import ApiClient

@pytest.fixture
def api_config():
    """Provides valid configuration for the API Client"""
    return {
        'api_token': os.getenv('PAWAPAY_API_TOKEN', 'test_token'),
        'license_key': os.getenv('PAWAPAY_SDK_LICENSE_KEY', 'TEST-LICENSE-KEY'),
        'environment': 'sandbox',
        'api_version': 'v2',
        'ssl_verify': True
    }

@pytest.fixture
async def client(api_config):
    """Provides a thread-safe ApiClient instance"""
    client = ApiClient(api_config)
    yield client
    await client.close()