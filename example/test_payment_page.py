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
logger = logging.getLogger("TestPaymentPage")

async def run_test():
    print("\n" + "="*50)
    print("   PAWAPAY PYTHON SDK - PAYMENT PAGE TEST")
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
        deposit_id = Helpers.generate_unique_id()
        return_url = "https://katorymnd.com/payment-success"
        amount = "5000"
        currency = "UGX"
        msisdn = "256783456789"
        
        # Keep description short for V1 compatibility (max 22 chars)
        description = "Python SDK Test"

        logger.info(f"Generated Deposit ID: {deposit_id}")

        # 4. EXECUTE REQUEST
        response = None
        
        if config['api_version'] == 'v1':
            logger.info("Creating Payment Page Session (V1)...")
            
            # V1 Params
            params = {
                'depositId': deposit_id,
                'amount': amount,
                'returnUrl': return_url,
                'statementDescription': description,
                'reason': 'Payment',
                'msisdn': msisdn, 
                'country': 'UGA'
            }
            response = await client.create_payment_page_session(params)
            
        else:
            logger.info("Creating Payment Page Session (V2)...")
            
            # V2 Params
            params = {
                'depositId': deposit_id,
                'amount': amount,
                'currency': currency,
                'returnUrl': return_url,
                'customerMessage': description,
                'country': 'UGA',
                'phoneNumber': msisdn  # <--- ADDED: Pre-fills phone on V2 page
            }
            response = await client.create_payment_page_session_v2(params)

        # 5. RESULT
        status_code = response.get('status')
        logger.info(f"API Status: {status_code}")

        if status_code not in [200, 201]:
            logger.error(f"Creation Failed: {response}")
            return

        data = response.get('response', {})
        redirect_url = data.get('redirectUrl') or data.get('url')

        print("\n" + "-"*40)
        print(f" SUCCESS! Payment Page Created ({TEST_VERSION.upper()})")
        print("-" * 40)
        print(f" Deposit ID:   {deposit_id}")
        print(f" Redirect URL: {redirect_url}")
        print("-" * 40 + "\n")

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