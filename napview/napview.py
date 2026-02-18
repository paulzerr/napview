#!/usr/bin/env python

import os
from pathlib import Path
import sys


def main() -> None:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        resource_root = Path(sys._MEIPASS).resolve() / "napview"
    elif getattr(sys, "frozen", False):
        resource_root = Path(sys.executable).resolve().parent / "napview"
    else:
        resource_root = Path(__file__).resolve().parent

    lsl_lib_by_platform = {
        "linux": "libs/liblsl.so",
        "darwin": "libs/liblsl.dylib",
        "win32": "libs/lsl.dll",
    }
    lib_name = lsl_lib_by_platform.get(sys.platform)
    if lib_name:
        lsl_path = resource_root / lib_name
        if lsl_path.exists():
            os.environ["PYLSL_LIB"] = str(lsl_path)
            if sys.platform == "win32":
                os.environ["PATH"] = f"{lsl_path.parent}{os.pathsep}{os.environ.get('PATH', '')}"
        else:
            raise RuntimeError(f"{lib_name} not found at {lsl_path}")

    from napview.napview_backend import main as backend_main

    backend_main()


if __name__ == "__main__":
    main()
