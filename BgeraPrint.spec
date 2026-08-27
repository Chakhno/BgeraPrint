# -*- mode: python ; coding: utf-8 -*-
#
# Build with:   pyinstaller BgeraPrint.spec
#
# The app is now a package (the bgera folder) rather than one long file.
# PyInstaller follows the imports from BgeraPrint.py on its own, but the
# modules are listed in hiddenimports as well so that a missing one shows up
# at build time rather than the first time a student types a command.

a = Analysis(
    ['BgeraPrint.py'],
    pathex=['.'],
    binaries=[
        ('C:\\Users\\Chakh\\anaconda3\\Library\\bin\\libssl-3-x64.dll', '.'),
        ('C:\\Users\\Chakh\\anaconda3\\Library\\bin\\libcrypto-3-x64.dll', '.'),
    ],
    datas=[('assets', 'assets')],
    hiddenimports=[
        'bgera',
        'bgera.app',
        'bgera.braille',
        'bgera.guided',
        'bgera.help',
        'bgera.keys',
        'bgera.menu',
        'bgera.model',
        'bgera.parser',
        'bgera.printing',
        'bgera.shapes',
        'bgera.texts',
        'bgera.transfer',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tests"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='BgeraPrint',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\Icon.ico'],
)
