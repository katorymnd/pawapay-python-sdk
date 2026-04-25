import asyncio
import os
import sys
import logging
import json
from datetime import datetime
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
logger = logging.getLogger("TestConfig")

# --- DATA FOLDER SETUP ---
DATA_DIR = os.path.join(parent_dir, 'data')
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
    logger.info(f"Created data directory: {DATA_DIR}")

async def run_test():
    print("\n" + "="*60)
    print("   PAWAPAY PYTHON SDK - FULL CONFIG & AVAILABILITY FETCH")
    print("="*60 + "\n")

    # 1. SETUP
    api_token = os.environ.get("PAWAPAY_SANDBOX_API_TOKEN")
    license_key = os.environ.get("KATORYMND_PAWAPAY_SDK_LICENSE_KEY")

    if not api_token or not license_key:
        logger.error("MISSING CREDENTIALS! Check .env")
        return

    config = {
        'api_token': api_token,
        'environment': 'sandbox',
        'api_version': 'v1', 
        'license_key': license_key,
        'ssl_verify': True
    }

    client = None

    try:
        # 2. INITIALIZE
        logger.info("Initializing ApiClient...")
        client = ApiClient(config)

        # ---------------------------------------------------------
        # SCENARIO 1: V1 Active Configuration (ALL)
        # ---------------------------------------------------------
        logger.info("Fetching V1 Active Configuration (ALL)...")
        res_v1_conf = await client.check_active_conf()
        process_result("v1_active_conf", res_v1_conf)

        # ---------------------------------------------------------
        # SCENARIO 2: V1 Availability (ALL)
        # ---------------------------------------------------------
        logger.info("Fetching V1 Availability (ALL)...")
        res_v1_avail = await client.check_mno_availability()
        process_result("v1_availability", res_v1_avail)

        # ---------------------------------------------------------
        # SCENARIO 3: V2 Active Configuration (ALL)
        # ---------------------------------------------------------
        logger.info("Fetching V2 Active Configuration (ALL)...")
        # Removing arguments fetches ALL data
        res_v2_conf = await client.check_active_conf_v2() 
        process_result("v2_active_conf", res_v2_conf)

        # ---------------------------------------------------------
        # SCENARIO 4: V2 Availability (ALL)
        # ---------------------------------------------------------
        logger.info("Fetching V2 Availability (ALL)...")
        # Removing arguments fetches ALL data
        res_v2_avail = await client.check_mno_availability_v2()
        process_result("v2_availability", res_v2_avail)

    except Exception as e:
        logger.error(f"Test Execution Failed: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        if client:
            await client.close()
            logger.info("Client closed.")

def process_result(filename_prefix, response):
    """Logs summary and saves JSON to file"""
    status = response.get('status')
    data = response.get('response', [])
    
    # 1. Calculate Item Count
    count = 0
    if isinstance(data, list):
        count = len(data)
    elif isinstance(data, dict):
        # V2 often returns { "UG": [...], "ZM": [...] } so we count total sub-items or keys
        count = len(data.keys())
    
    # 2. Log Success/Failure
    if 200 <= status < 300:
        logger.info(f"SUCCESS [{filename_prefix}]: Status {status}, Items {count}")
    else:
        logger.error(f"FAILURE [{filename_prefix}]: Status {status}, Response: {data}")

    # 3. Save to JSON File
    try:
        # --- MODIFIED: Removed timestamp from filename ---
        filename = f"{filename_prefix}.json"
        filepath = os.path.join(DATA_DIR, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
            
        print(f"   -> Saved to: data\\{filename}")
        print("-" * 40)

    except Exception as save_err:
        logger.error(f"Failed to save file {filename}: {save_err}")

if __name__ == "__main__":
    asyncio.run(run_test())