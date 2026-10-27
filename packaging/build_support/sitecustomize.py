"""Preload system ICU in PyInstaller's isolated Qt introspection processes."""
import os
import sys
if sys.platform == 'win32':
    import ctypes
    _system_icu = ctypes.WinDLL(os.path.join(os.environ['SystemRoot'], 'System32', 'icuuc.dll'))
