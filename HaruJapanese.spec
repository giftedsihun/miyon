# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['japanese_study.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['content', 'learning_services', 'progress_logic', 'quiz_session', 'storage', 'tts_service', 'study_logic', 'quiz_logic', 'ui_catalog', 'ui_dialogs', 'ui_quiz', 'ui_screens', 'ui_practice', 'app_info'],
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
    a.binaries,
    a.datas,
    [],
    name='HaruJapanese',
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
