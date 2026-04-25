import asyncio
import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv  # Import this to load .env file

# --- PATH & ENV SETUP ---
# 1. Calculate paths
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))

# 2. Add parent directory to sys.path BEFORE any src imports
sys.path.insert(0, parent_dir)

# 3. Load .env file BEFORE importing the SDK
env_path = os.path.join(parent_dir, '.env')
load_dotenv(env_path)

# 4. CRITICAL: Ensure Domain exists before SDK loads
if "PAWAPAY_SDK_LICENSE_DOMAIN" not in os.environ:
    os.environ["PAWAPAY_SDK_LICENSE_DOMAIN"] = "localhost"

# 5. Now it is safe to import the SDK modules
from src.utils.helpers import Helpers
from src.api.ApiClient import ApiClient

# --- LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TestDeposit")

async def run_test():
    print("\n" + "="*50)
    print("   PAWAPAY PYTHON SDK - DEPOSIT TEST SCRIPT")
    print("="*50 + "\n")

    # 1. SETUP CONFIGURATION
    api_token = os.environ.get("PAWAPAY_SANDBOX_API_TOKEN")
    license_key = os.environ.get("KATORYMND_PAWAPAY_SDK_LICENSE_KEY")

    if not api_token or not license_key:
        logger.error("MISSING CREDENTIALS! Please check your .env file.")
        return

    config = {
        'api_token': api_token,
        'environment': 'sandbox',
        'api_version': 'v2', # Testing V2 / V1
        'license_key': license_key,
        'ssl_verify': True
    }

    client = None

    try:
        # 2. INITIALIZE CLIENT
        logger.info("Initializing ApiClient...")
        client = ApiClient(config)

        # Generate a Unique Deposit ID
        deposit_id = Helpers.generate_unique_id()
        logger.info(f"Generated Deposit ID: {deposit_id}")

        # 3. INITIATE DEPOSIT
        amount = "5000"
        currency = "UGX"
        payer_msisdn = "256783456789" # Valid Sandbox MSISDN
        
        # Determine arguments based on version
        if config['api_version'] == 'v1':
            logger.info("Initiating Deposit (V1)...")
            correspondent = "MTN_MOMO_UGA"
            
            response = await client.initiate_deposit(
                deposit_id=deposit_id,
                amount=amount,
                currency=currency,
                correspondent=correspondent,
                payer=payer_msisdn,
                statement_description="Python SDK Test"
            )
        else:
            logger.info("Initiating Deposit (V2)...")
            
            # --- FIX: Use 'MTN_MOMO_UGA' for V2 Provider in Sandbox ---
            # 'MTN' is rejected by the API. It must match the Correspondent ID.
            provider = "MTN_MOMO_UGA" 
            
            response = await client.initiate_deposit_v2(
                deposit_id=deposit_id,
                amount=amount,
                currency=currency,
                payer_msisdn=payer_msisdn,
                provider=provider,
                customer_message="Python SDK Test"
            )

        # 4. HANDLE RESPONSE
        status_code = response.get('status')
        logger.info(f"Initiation API Status: {status_code}")
        
        if status_code not in [200, 201, 202]:
            logger.error(f"Deposit Initiation Failed: {response}")
            return

        print("\n--- Initiation Response Data ---")
        print(response.get('response'))
        print("--------------------------------\n")

        # 5. CHECK STATUS
        logger.info("Checking Transaction Status...")
        
        # Small delay to allow Sandbox to process
        await asyncio.sleep(2) 

        status_response = await client.check_transaction_status_auto(
            transaction_id=deposit_id,
            type="deposit"
        )
        
        print("\n--- Status Check Response ---")
        print(status_response.get('response'))
        print("-----------------------------\n")

    except Exception as e:
        logger.error(f"Test Execution Failed: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        # 6. CLEANUP
        if client:
            await client.close()
            logger.info("Client connection closed.")

if __name__ == "__main__":
    asyncio.run(run_test())