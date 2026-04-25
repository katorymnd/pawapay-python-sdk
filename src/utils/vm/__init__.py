# src/utils/vm/__init__.py
"""
VM modules for license protection
"""

from .bytecode_encoder import BytecodeEncoder
from .degradation_manager import DegradationManager
from .interpreter import VMInterpreter, ImprintBoundVM

__all__ = ['BytecodeEncoder', 'DegradationManager', 'VMInterpreter', 'ImprintBoundVM']