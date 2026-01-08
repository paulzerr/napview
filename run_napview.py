#!/usr/bin/env python

import os
import pathlib
import sys

# Ensure pylsl can find the bundled liblsl before any imports.
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    RESOURCE_ROOT = pathlib.Path(sys._MEIPASS).resolve() / "napview"
elif getattr(sys, "frozen", False):
    RESOURCE_ROOT = pathlib.Path(sys.executable).resolve().parent / "napview"
else:
    RESOURCE_ROOT = pathlib.Path(__file__).resolve().parent / "napview"
LSL_LIB_BY_PLATFORM = {
    "linux": "libs/liblsl.so",
    "darwin": "libs/liblsl.dylib",
    "win32": "libs/lsl.dll",
}
lib_name = LSL_LIB_BY_PLATFORM.get(sys.platform)
if lib_name:
    lsl_path = RESOURCE_ROOT / lib_name
    if lsl_path.exists():
        os.environ["PYLSL_LIB"] = str(lsl_path)
        if sys.platform == "win32":
            os.environ["PATH"] = f"{lsl_path.parent}{os.pathsep}{os.environ.get('PATH', '')}"
    else:
        raise RuntimeError(f"{lib_name} not found at {lsl_path}")

from napview.napview_backend import main as backend_main

if __name__ == "__main__":
    backend_main()
