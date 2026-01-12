# -*- mode: python ; coding: utf-8 -*-
import glob

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

mne_datas = collect_data_files("mne", include_py_files=True)
mne_hiddenimports = collect_submodules("mne")

vc_redist_binaries = [(f, ".") for f in glob.glob("nidra/nidra/NIDRA/dll/*.dll")]
lsl_binaries = [(f, "napview/libs") for f in glob.glob("napview/libs/*")]

final_datas = [
    ("napview/templates", "napview/templates"),
    ("napview/static", "napview/static"),
    ("napview/assets", "napview/assets"),
    ("napview/CONFIG_DEFAULTS.txt", "napview"),
    ("nidra/nidra/NIDRA/models", "NIDRA/models"),
] + mne_datas

final_hiddenimports = [
    "flask",
    "jinja2",
    "werkzeug",
] + collect_submodules("scipy") + collect_submodules("pandas") + mne_hiddenimports

a = Analysis(
    ["run_napview.py"],
    pathex=[".", "napview", "nidra/nidra"],
    binaries=vc_redist_binaries + lsl_binaries,
    datas=final_datas,
    hiddenimports=final_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PyQt5", "notebook", "jupyter", "IPython"],
    noarchive=False,
    optimize=0,
    distpath="dist",
    workpath="build",
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    name="NAPVIEW",
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    manifest="NAPVIEW.manifest",
    icon="napview/assets/favicon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=True,
    upx=False,
    name="NAPVIEW",
    bindir="runtime",
)
