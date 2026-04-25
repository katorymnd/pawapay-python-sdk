# src/setup_cli.py
import os
import sys
import json
import base64
import hashlib
import time
from pathlib import Path

# --- 1. CONFIGURATION & PATHS ---
# When installed, this file lives in site-packages/src/setup_cli.py
PACKAGE_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
VM_OUTPUT_DIR = os.path.join(PACKAGE_SRC_DIR, 'utils', 'vm')

# The developer's actual project folder where they run the command
USER_PROJECT_DIR = os.getcwd() 

def run_setup():
    print("\n" + "="*60)
    print("  PAWAPAY PYTHON SDK - SECURE INITIALIZATION")
    print("="*60)

    # --- 2. LOAD .ENV FROM USER'S FOLDER ---
    try:
        from dotenv import load_dotenv
        env_path = os.path.join(USER_PROJECT_DIR, '.env')
        if os.path.exists(env_path):
            print(f"[Setup] Loading .env from: {env_path}")
            load_dotenv(env_path)
        else:
            print(f"[Setup] Warning: No .env found at {env_path}")
    except ImportError:
        print("[Setup] Warning: 'python-dotenv' not installed.")

    # --- 2.1 ENFORCE REQUIRED VARIABLES ---
    required_env_vars = ["PAWAPAY_SDK_LICENSE_DOMAIN", "PAWAPAY_SDK_LICENSE_SECRET"]
    missing_vars = [var for var in required_env_vars if var not in os.environ]

    if missing_vars:
        print("\n[Setup] CRITICAL ERROR: Missing required environment variables.")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease define these in your .env file before running setup.")
        sys.exit(1)

    # --- 3. IMPORT SDK MODULES ---
    try:
        from src.utils.vm.bytecode_encoder import BytecodeEncoder
    except ImportError as e:
        print("\n[Setup] CRITICAL ERROR: Could not import BytecodeEncoder.")
        print(f"Detail: {e}")
        sys.exit(1)

    # 1. Ensure VM Directory exists inside the package
    if not os.path.exists(VM_OUTPUT_DIR):
        os.makedirs(VM_OUTPUT_DIR, exist_ok=True)
        print(f"[Setup] Verified internal VM directory: {VM_OUTPUT_DIR}")

    # 2. Initialize Encoder
    print("[Setup] Initializing Bytecode Encoder...")
    encoder = BytecodeEncoder()

    # 3. Generate VM Files internally
    print("[Setup] Generating Native VM Bytecode...")
    success = encoder.generate_client_files(VM_OUTPUT_DIR)

    if success:
        # 4. Generate Session File in the user's root directory
        print("[Setup] Generating Session Cache...")
        imprint_path = os.path.join(USER_PROJECT_DIR, '.pawapay-imprint')
        session_path = os.path.join(USER_PROJECT_DIR, '.pawapay-session')
        
        # Check if imprint was created by the encoder (you may need to ensure your encoder writes to USER_PROJECT_DIR)
        if not os.path.exists(imprint_path):
            # Fallback: create it if the encoder didn't put it in the user dir
            import uuid
            with open(imprint_path, 'w', encoding='utf-8') as f:
                f.write(str(uuid.uuid4()))

        try:
            with open(imprint_path, 'r', encoding='utf-8') as f:
                imprint = f.read().strip()
            
            timestamp = time.time()
            raw_sig = str(timestamp) + imprint
            signature = hashlib.sha256(raw_sig.encode('utf-8')).hexdigest()

            data = {'lastValidation': timestamp, 'signature': signature}
            json_str = json.dumps(data)
            content = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')

            with open(session_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"[Setup] Generated Session File: {session_path}")
        except Exception as e:
            print(f"[Setup] Failed to generate session file: {e}")

        print("\n" + "="*60)
        print("SUCCESS! SDK is fully bootstrapped and locked to this machine.")
        print("="*60)
        print(f"1. Imprint:   {imprint_path}")
        print(f"2. Session:   {session_path}")
        print("\n[Next Step] You can now import the ApiClient in your code!")
    else:
        print("\n[Setup] FAILED to generate VM files.")
        sys.exit(1)

if __name__ == "__main__":
    run_setup()