# -*- mode: python ; coding: utf-8 -*-
import os
block_cipher = None

a = Analysis(
    ['..\\main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['zoneinfo', 'tzdata', 'shiboken6', 'argparse', 'logging', 'difflib', 'textwrap', 'inspect', 'typing'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtWebEngineQuick',
        'PySide6.QtQuick', 'PySide6.QtQuick3D', 'PySide6.QtQml', 'PySide6.Qt3DCore',
        'PySide6.Qt3DRender', 'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets',
        'PySide6.QtCharts', 'PySide6.QtDataVisualization', 'PySide6.QtOpenGL',
        'PySide6.QtOpenGLWidgets', 'PySide6.QtPdf', 'PySide6.QtPdfWidgets',
        'PySide6.QtSql', 'PySide6.QtTest', 'PySide6.QtDesigner', 'PySide6.QtHelp',
        'PySide6.QtSerialPort', 'PySide6.QtBluetooth', 'PySide6.QtPositioning',
        'PySide6.QtRemoteObjects', 'PySide6.QtScxml', 'PySide6.QtSensors',
        'PySide6.QtSpatialAudio', 'PySide6.QtStateMachine', 'PySide6.QtTextToSpeech',
        'PySide6.QtWebChannel', 'PySide6.QtWebSockets', 'PySide6.QtNfc',
        'PySide6.QtUiTools', 'PySide6.QtXml', 'PySide6.QtConcurrent',
        'PySide6.QtNetwork', 'PySide6.QtSvg', 'PySide6.QtSvgWidgets',
        'PySide6.QtPrintSupport', 'PySide6.QtDBus', 'PySide6.QtQuickWidgets',
        'PySide6.QtQuickControls2', 'PySide6.QtHttpServer', 'PySide6.QtGraphs',
        'PySide6.support', 'PySide6.scripts',
        'tkinter', 'unittest', 'pydoc_data', 'test', 'distutils',
        'numpy', 'matplotlib', 'PIL', 'setuptools', 'pip', 'wheel',
        'sqlite3', 'email', 'http', 'xmlrpc', 'pickletools', 'lib2to3',
        'multiprocessing', 'asyncio', 'concurrent', 'curses', 'ssl',
        'bz2', 'lzma', 'hashlib', 'doctest',
    ],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='AuroraClock',
    debug=False, bootloader_ignore_signals=False, strip=False, upx=True,
    console=False,
    disable_windowed_traceback=False,
    icon='aurora.ico',
    version='version_info.txt',
)
coll = COLLECT(
    exe, a.binaries, a.datas,
    strip=False, upx=True,
    upx_exclude=['vcruntime140.dll', 'python311.dll', 'Qt6Core.dll', 'Qt6Gui.dll'],
    name='AuroraClock',
)
