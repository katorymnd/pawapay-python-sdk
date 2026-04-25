"""
@file src/core/loader.py
Dynamic Cross-Platform Shadow Wrapper for the PawaPay Native Execution Engine
"""
import sys
import platform
import os
import importlib
import subprocess

def _is_musl() -> bool:
    """Helper function to detect Alpine Linux (musl) vs Standard Linux (glibc)"""
    # Using platform.system() prevents Pylance from falsely flagging this 
    # as unreachable code when developing on Windows or macOS.
    if platform.system().lower() != "linux":
        return False
    
    # 1. Fast path: Direct Alpine check
    if os.path.exists("/etc/alpine-release"):
        return True
        
    # 2. Fallback: ldd linker check
    try:
        output = subprocess.check_output(["ldd", "--version"], stderr=subprocess.STDOUT, text=True)
        return "musl" in output.lower()
    except Exception:
        # If ldd fails, default to false (standard glibc) unless we are certain
        return False
    
def _load_native_core():
    # 1. DEV-MODE SHORTCUT
    # If the developer used `maturin develop`, the binary is already in the virtual environment.
    try:
        return importlib.import_module("katorymnd_pawapay_core")
    except ImportError:
        pass # Proceed to dynamic folder loading

    # 2. SYSTEM DETECTION
    system = platform.system().lower()  # 'windows', 'linux', 'darwin'
    arch = platform.machine().lower()   # 'x86_64', 'amd64', 'aarch64', 'arm64'

    # Normalize architecture names across different platforms
    if arch in ["amd64", "x86_64", "x64"]:
        normalized_arch = "x86_64"
    elif arch in ["arm64", "aarch64"]:
        normalized_arch = "arm64"
    else:
        normalized_arch = arch

    # 3. ROUTING LOGIC: Determine the correct binary folder for this OS/Arch
    folder_name = ""
    if system == "windows":
        folder_name = f"win_{normalized_arch}"
    elif system == "darwin":
        folder_name = f"darwin_{normalized_arch}"
    elif system == "linux":
        libc_type = "musl" if _is_musl() else "gnu"
        folder_name = f"linux_{normalized_arch}_{libc_type}"
    else:
        print(f"🔥 [PawaPay SDK] FATAL ERROR: Unsupported operating system: {system}")
        sys.exit(1)

    # 🛡️ BUNDLER EVASION: Calculate path dynamically using __file__
    current_dir = os.path.dirname(os.path.abspath(__file__))
    target_bin_dir = os.path.join(current_dir, folder_name)

    if not os.path.exists(target_bin_dir):
        print("🔥 [PawaPay SDK] FATAL ERROR: The Secure Native Engine failed to load.")
        print(f"System info: {system} ({normalized_arch})")
        print(f"Error details: Native binary folder not found at: {target_bin_dir}")
        sys.exit(1)

    # 4. SURGICAL INJECTION
    # Temporarily add the binary folder to Python's system path to import the exact wheel
    sys.path.insert(0, target_bin_dir)

    try:
        core_module = importlib.import_module("katorymnd_pawapay_core")
        return core_module
    except ImportError as e:
        print("🔥 [PawaPay SDK] FATAL ERROR: The Secure Native Engine failed to load.")
        print(f"System info: {system} ({normalized_arch})")
        print(f"Error details: {str(e)}")
        # Fail closed. Do not allow the SDK to run without the protection engine.
        sys.exit(1)
    finally:
        # Clean up the path so we don't pollute the user's environment
        if sys.path and sys.path[0] == target_bin_dir:
            sys.path.pop(0)

# Initialize the core immediately upon import
NativeCore = _load_native_core()

# ==========================================
# PLATFORM DETECTION FUNCTIONS
# ==========================================

def get_native_platform_id() -> str:
    """Returns the platform identifier for the currently loaded native binary"""
    system = platform.system().lower()
    arch = platform.machine().lower()
    
    # Normalize architecture
    if arch in ["amd64", "x86_64", "x64"]:
        normalized_arch = "x86_64"
    elif arch in ["arm64", "aarch64"]:
        normalized_arch = "arm64"
    else:
        normalized_arch = arch
    
    if system == "windows":
        return f"win_{normalized_arch}"
    elif system == "darwin":
        return f"darwin_{normalized_arch}"
    elif system == "linux":
        libc_type = "musl" if _is_musl() else "gnu"
        return f"linux_{normalized_arch}_{libc_type}"
    else:
        raise Exception(f"Unsupported platform: {system}")

def get_native_binary_path() -> str:
    """Returns the actual path to the loaded native binary"""
    native = NativeCore
    if hasattr(native, '__file__'):
        return native.__file__
    
    # Fallback: construct path based on platform
    current_dir = os.path.dirname(os.path.abspath(__file__))
    platform_id = get_native_platform_id()
    
    if platform_id.startswith('win'):
        return os.path.join(current_dir, platform_id, "katorymnd_pawapay_core.pyd")
    else:
        return os.path.join(current_dir, platform_id, "katorymnd_pawapay_core.so")

# ==========================================
# EXPORT THE NATIVE MODULES
# ==========================================

# Classes
PawaPayCore = getattr(NativeCore, "PawaPayCore", None)
IntegrityVault = getattr(NativeCore, "IntegrityVault", None)

# Top-Level heart Functions (Maintained in snake_case per Python conventions)
get_pawapay_base_url = getattr(NativeCore, "get_pawapay_base_url", None)
normalize_api_url = getattr(NativeCore, "normalize_api_url", None)
verify_request_state = getattr(NativeCore, "verify_request_state", None)
evaluate_runtime_integrity = getattr(NativeCore, "evaluate_runtime_integrity", None)

# Protection Layer and Hardware Functions
validate_license_local = getattr(NativeCore, "validate_license_local", None)
derive_vm_hardware_key = getattr(NativeCore, "derive_vm_hardware_key", None)
execute_vm_core = getattr(NativeCore, "execute_vm_core", None)
calculate_degradation_action = getattr(NativeCore, "calculate_degradation_action", None)
corrupt_degradation_data = getattr(NativeCore, "corrupt_degradation_data", None)
generate_shuffled_opcodes = getattr(NativeCore, "generate_shuffled_opcodes", None)
get_internal_logic = getattr(NativeCore, "get_internal_logic", None)
generate_server_fingerprint = getattr(NativeCore, "generate_server_fingerprint", None)
create_signed_headers = getattr(NativeCore, "create_signed_headers", None)
sign_session_data = getattr(NativeCore, "sign_session_data", None)
evaluate_time_decay = getattr(NativeCore, "evaluate_time_decay", None)
evaluate_success_recovery = getattr(NativeCore, "evaluate_success_recovery", None)

# ==========================================
# EXPORT LIST
# ==========================================

__all__ = [
    "NativeCore",
    "PawaPayCore",
    "IntegrityVault",
    "get_pawapay_base_url",
    "normalize_api_url",
    "verify_request_state",
    "evaluate_runtime_integrity",
    "validate_license_local",
    "derive_vm_hardware_key",
    "execute_vm_core",
    "calculate_degradation_action",
    "corrupt_degradation_data",
    "generate_shuffled_opcodes",
    "get_internal_logic",
    "generate_server_fingerprint",
    "create_signed_headers",
    "sign_session_data",
    "evaluate_time_decay",
    "evaluate_success_recovery",
    # Platform detection functions
    "get_native_platform_id",
    "get_native_binary_path",
]