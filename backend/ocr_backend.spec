# PyInstaller spec for the FastAPI desktop backend.
# Build from the repository root with:
#   pyinstaller --clean --noconfirm backend/ocr_backend.spec

from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

ROOT = Path.cwd()

hiddenimports = []
hiddenimports += collect_submodules("uvicorn")
hiddenimports += collect_submodules("fastapi")
hiddenimports += collect_submodules("pydantic")
hiddenimports += collect_submodules("sqlalchemy")

# OCR providers are intentionally not forced into the executable here. Remote Qwen OCR
# works without local model files. If you enable offline OCR, add model assets under
# backend/models and include them as datas below or download them to OCR_MODEL_DIR.
datas = []
if (ROOT / "backend" / "models").exists():
    datas.append((str(ROOT / "backend" / "models"), "backend/models"))

block_cipher = None

a = Analysis(
    [str(ROOT / "backend" / "desktop_server.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["notebook", "matplotlib"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="ocr-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
