# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:\\honlabo2\\nekoDiary2\\src\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('D:\\honlabo2\\nekoDiary2\\src\\style.qss', 'src'), ('D:\\honlabo2\\nekoDiary2\\Sozai', 'Sozai')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='NekoDiary',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['D:\\honlabo2\\nekoDiary2\\app-icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='NekoDiary',
)
