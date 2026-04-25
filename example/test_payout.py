import asyncio
import os
import sys
from src.utils.helpers import Helpers
import logging
from dotenv import load_dotenv

# --- PATH & ENV SETUP ---
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
env_path = os.path.join(parent_dir, '.env')
load_dotenv(env_path)

# Ensure Domain exists
if "PAWAPAY_SDK_LICENSE_DOMAIN" not in os.environ:
    os.environ["PAWAPAY_SDK_LICENSE_DOMAIN"] = "localhost"

sys.path.append(parent_dir)
from src.api.ApiClient import ApiClient

# --- LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TestPayout")

async def run_test():
    print("\n" + "="*50)
    print("      PAWAPAY PYTHON SDK - PAYOUT TEST")
    print("="*50 + "\n")

    # 1. SETUP
    api_token = os.environ.get("PAWAPAY_SANDBOX_API_TOKEN")
    license_key = os.environ.get("KATORYMND_PAWAPAY_SDK_LICENSE_KEY")

    if not api_token or not license_key:
        logger.error("MISSING CREDENTIALS! Check .env")
        return

    # TOGGLE VERSION HERE: 'v1' or 'v2'
    TEST_VERSION = 'v2' 

    config = {
        'api_token': api_token,
        'environment': 'sandbox',
        'api_version': TEST_VERSION,
        'license_key': license_key,
        'ssl_verify': True
    }

    client = None

    try:
        # 2. INITIALIZE
        logger.info(f"Initializing ApiClient ({TEST_VERSION.upper()})...")
        client = ApiClient(config)

        # 3. PREPARE DATA
        payout_id = Helpers.generate_unique_id()
        amount = "5000"
        currency = "UGX"
        msisdn = "256783456789" # Valid Sandbox MSISDN
        description = "Python SDK Payout"

        # --- OPTIONAL METADATA ---
        # This helps you track the payment in your own system
        meta_data = [
            {"fieldName": "orderId", "fieldValue": "ORD-998877"},
            {"fieldName": "customerId", "fieldValue": "CUST-001"},
            {"fieldName": "reason", "fieldValue": "Refund for return"}
        ]

        logger.info(f"Generated Payout ID: {payout_id}")

        # 4. EXECUTE REQUEST
        response = None
        
        if config['api_version'] == 'v1':
            logger.info("Initiating Payout (V1)...")
            
            # V1 uses 'correspondent'
            correspondent = "MTN_MOMO_UGA"
            
            response = await client.initiate_payout(
                payout_id=payout_id,
                amount=amount,
                currency=currency,
                correspondent=correspondent,
                recipient=msisdn,
                statement_description=description,
                metadata=meta_data  # <--- PASSING METADATA
            )
            
        else:
            logger.info("Initiating Payout (V2)...")
            
            # V2 uses 'provider' (Must be MTN_MOMO_UGA in Sandbox)
            provider = "MTN_MOMO_UGA"
            
            response = await client.initiate_payout_v2(
                payout_id=payout_id,
                amount=amount,
                currency=currency,
                recipient_msisdn=msisdn,
                provider=provider,
                customer_message=description,
                metadata=meta_data  # <--- PASSING METADATA
            )

        # 5. RESULT
        status_code = response.get('status')
        logger.info(f"API Status: {status_code}")

        if status_code not in [200, 201, 202]:
            logger.error(f"Payout Failed: {response}")
            return

        print("\n--- Payout Initiation Response ---")
        print(response.get('response'))
        print("----------------------------------\n")

        # 6. CHECK STATUS
        logger.info("Checking Transaction Status...")
        await asyncio.sleep(2) # Wait for Sandbox

        status_response = await client.check_transaction_status_auto(
            transaction_id=payout_id,
            type="payout" # Important: specify type='payout'
        )
        
        print("\n--- Status Check Response ---")
        print(status_response.get('response'))
        print("-----------------------------\n")

    except Exception as e:
        logger.error(f"Test Failed: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        if client:
            await client.close()
            logger.info("Client closed.")

if __name__ == "__main__":
    asyncio.run(run_test())