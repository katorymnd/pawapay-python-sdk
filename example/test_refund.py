import asyncio
import os
import sys
from src.utils.helpers import Helpers
import logging
import json
import argparse
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
logger = logging.getLogger("TestRefund")

async def run_test(args):
    print("\n" + "="*50)
    print("      PAWAPAY PYTHON SDK - REFUND TEST")
    print("="*50 + "\n")

    # 1. SETUP
    api_token = os.environ.get("PAWAPAY_SANDBOX_API_TOKEN")
    license_key = os.environ.get("KATORYMND_PAWAPAY_SDK_LICENSE_KEY")

    if not api_token or not license_key:
        logger.error("MISSING CREDENTIALS! Check .env")
        return

    config = {
        'api_token': api_token,
        'environment': 'sandbox',
        'api_version': args.version,
        'license_key': license_key,
        'ssl_verify': True
    }

    client = None

    try:
        # 2. INITIALIZE
        logger.info(f"Initializing ApiClient ({args.version.upper()})...")
        client = ApiClient(config)

        # 3. PREPARE DATA
        refund_id = Helpers.generate_unique_id()
        deposit_id = args.deposit_id
        amount = args.amount
        currency = "UGX" 
        
        logger.info(f"Refund ID:   {refund_id}")
        logger.info(f"Deposit ID:  {deposit_id}")
        logger.info(f"Amount:      {amount} {currency}")

        # Metadata (Optional)
        meta_data = [
            {"fieldName": "reason", "fieldValue": "Customer request"},
            {"fieldName": "adminUser", "fieldValue": "Admin-01"}
        ]

        # 4. EXECUTE REQUEST
        response = None
        
        if config['api_version'] == 'v1':
            logger.info("Initiating Refund (V1)...")
            
            # V1: Does not require currency (infers from deposit)
            response = await client.initiate_refund(
                refund_id=refund_id,
                deposit_id=deposit_id,
                amount=amount,
                metadata=meta_data
            )
            
        else:
            logger.info("Initiating Refund (V2)...")
            
            # V2: Requires currency
            response = await client.initiate_refund_v2(
                refund_id=refund_id,
                deposit_id=deposit_id,
                amount=amount,
                currency=currency,
                metadata=meta_data
            )

        # 5. RESULT
        status_code = response.get('status')
        logger.info(f"API Status: {status_code}")

        if status_code not in [200, 201, 202]:
            logger.error(f"Refund Failed: {response}")
            return

        print("\n--- Refund Initiation Response ---")
        print(json.dumps(response.get('response'), indent=2))
        print("----------------------------------\n")

        # 6. CHECK STATUS
        logger.info("Checking Transaction Status...")
        await asyncio.sleep(2) 

        # Note: We check the status of the REFUND_ID, not the Deposit ID
        status_response = await client.check_transaction_status_auto(
            transaction_id=refund_id,
            type="refund"
        )
        
        print("\n--- Refund Status Check ---")
        print(json.dumps(status_response.get('response'), indent=2))
        print("---------------------------\n")

    except Exception as e:
        logger.error(f"Test Failed: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        if client:
            await client.close()
            logger.info("Client closed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test PawaPay Refund API')
    
    # Required: The ID of the deposit you want to refund
    parser.add_argument('deposit_id', help='The UUID of the successful deposit to refund')
    
    # Optional V1/V2
    parser.add_argument('--amount', '-a', default='500', help='Amount to refund')
    parser.add_argument('--version', '-v', choices=['v1', 'v2'], default='v1', help='API Version')
    
    args = parser.parse_args()
    
    asyncio.run(run_test(args))