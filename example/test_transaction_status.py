import asyncio
import os
import sys
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
logger = logging.getLogger("TestStatus")

async def run_test(args):
    print("\n" + "="*50)
    print("   PAWAPAY PYTHON SDK - STATUS CHECK")
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

        # 3. CHECK STATUS
        logger.info(f"Checking Status for ID: {args.deposit_id}")
        
        # We use the auto method which switches based on config['api_version']
        response = await client.check_transaction_status_auto(
            transaction_id=args.deposit_id,
            type=args.type
        )

        # 4. RESULT
        status_code = response.get('status')
        logger.info(f"API Status: {status_code}")

        if status_code == 404:
            print("\n[!] Transaction Not Found (404)")
        elif status_code not in [200]:
            print(f"\n[!] Error: {response}")
        else:
            print("\n--- Transaction Details ---")
            # Pretty print the JSON response
            print(json.dumps(response.get('response'), indent=2))
            print("---------------------------\n")

    except Exception as e:
        logger.error(f"Check Failed: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        if client:
            await client.close()
            logger.info("Client closed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Check PawaPay Transaction Status')
    
    # Required argument
    parser.add_argument('deposit_id', help='The UUID of the deposit/payout to check')
    
    # Optional arguments
    parser.add_argument('--version', '-v', choices=['v1', 'v2'], default='v2', help='API Version')
    parser.add_argument('--type', '-t', choices=['deposit', 'payout', 'refund'], default='deposit', help='Transaction Type')
    
    args = parser.parse_args()
    
    asyncio.run(run_test(args))