"""
@file src/core/__init__.py
Exposes the dynamically loaded native heart binaries to the rest of the Python SDK.
"""

from .loader import (
    NativeCore,
    PawaPayCore,
    IntegrityVault,
    get_pawapay_base_url,
    normalize_api_url,
    verify_request_state,
    evaluate_runtime_integrity,
    validate_license_local,
    derive_vm_hardware_key,
    execute_vm_core,
    calculate_degradation_action,
    corrupt_degradation_data,
    generate_shuffled_opcodes,
    get_internal_logic,
    generate_server_fingerprint,
    create_signed_headers,
    sign_session_data,
    evaluate_time_decay,
    evaluate_success_recovery,
    # Platform detection functions
    get_native_platform_id,
    get_native_binary_path,
)

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