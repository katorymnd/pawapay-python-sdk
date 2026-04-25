# src/__init__.py
"""
PawaPay Python SDK
Official Premium Python SDK by Katorymnd Web Solutions.
"""
import os
import sys
from dotenv import load_dotenv

# 1. EAGER LOAD: We must load environment variables BEFORE any sub-modules
# are imported to satisfy strict license validation checks.
env_path = os.path.join(os.getcwd(), '.env')
load_dotenv(env_path)

__version__ = '2.1.1'
__author__ = 'Katorymnd Web Solutions'
__email__ = 'support@katorymnd.com'

# 2. CORE IMPORTS: Since the SDK relies on these, we import them directly.
# If they are missing from the build, the system should fail loudly here
# so the developer knows the installation is corrupt.
try:
    from .api.ApiClient import ApiClient
    from .config.Config import Config
    
    __all__ = ['ApiClient', 'Config']
    
except ImportError as e:
    # We catch the error only to provide a more helpful message for the CLI
    print(f"\n[SDK Error] Critical component missing: {e}")
    print("[SDK Error] Ensure the SDK was installed correctly with all modules.")
    # We do not allow the script to continue in a broken state
    if "katorymnd-pawapay-setup" in sys.argv[0]:
        pass # Allow the setup process to attempt recovery if possible
    else:
        raise