# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['E:\\工程文件\\1.2.2VINS\\自制软件\\材质库查询V1.0\\FSmatbinBD_V1.1\\qt_main.py'],
    pathex=[],
    binaries=[],
    datas=[('E:\\工程文件\\1.2.2VINS\\自制软件\\材质库查询V1.0\\FSmatbinBD_V1.1\\src\\gui_qt\\assets', 'src/gui_qt/assets'), ('E:\\工程文件\\1.2.2VINS\\自制软件\\材质库查询V1.0\\FSmatbinBD_V1.1\\src\\gui_qt\\theme', 'src/gui_qt/theme'), ('E:\\工程文件\\1.2.2VINS\\自制软件\\材质库查询V1.0\\FSmatbinBD_V1.1\\tools', 'tools'), ('E:\\工程文件\\1.2.2VINS\\自制软件\\材质库查询V1.0\\FSmatbinBD_V1.1\\data', 'data'), ('E:\\工程文件\\1.2.2VINS\\自制软件\\材质库查询V1.0\\FSmatbinBD_V1.1\\autopack_config.json', '.'), ('E:\\工程文件\\1.2.2VINS\\自制软件\\材质库查询V1.0\\FSmatbinBD_V1.1\\version.json', '.')],
    hiddenimports=['PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets', 'PySide6.QtSvg', 'PySide6.QtSvgWidgets', 'src.core.i18n', 'src.core.database', 'src.core.xml_parser', 'src.core.autopack_manager', 'src.core.material_matcher', 'src.core.multi_thread_matcher', 'src.core.fast_material_matcher', 'src.core.multi_thread_fast_matcher', 'src.core.witchybnd_processor', 'src.core.witchybnd_drag_drop', 'src.core.version', 'src.core.about_secure', 'src.core.material_replacer', 'src.core.material_replace_models', 'src.core.material_json_parser', 'src.core.sampler_type_parser', 'src.core.undo_redo_manager', 'src.utils.resource_path', 'src.utils.config', 'src.utils.helpers', 'src.gui_qt.main_window', 'src.gui_qt.material_tree_panel', 'src.gui_qt.material_editor_panel', 'src.gui_qt.material_matching_dialog_qt', 'src.gui_qt.advanced_search_dialog_qt', 'src.gui_qt.autopack_dialog_qt', 'src.gui_qt.library_manager_dialog_qt', 'src.gui_qt.dcx_import_dialog_qt', 'src.gui_qt.import_dialogs_qt', 'src.gui_qt.sampler_panel', 'src.gui_qt.models', 'src.gui_qt.loading_overlay', 'src.gui_qt.smooth_scroll', 'src.gui_qt.color_picker_dialog', 'src.gui_qt.dark_titlebar', 'src.gui_qt.about_dialog_qt', 'src.gui_qt.batch_replace_dialog', 'src.gui_qt.material_replace_dialog', 'src.gui_qt.material_replace_editor', 'src.gui_qt.texture_edit_panel', 'src.gui_qt.standard_dialogs', 'src.gui_qt.theme.palette', 'src.gui_qt.theme.qss'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', '_tkinter', 'matplotlib', 'numpy', 'pandas', 'scipy', 'PIL', 'cv2', 'IPython', 'jupyter', 'notebook', 'pytest', 'setuptools', 'wheel', 'pip'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FSMatbinBD',
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
    icon=['E:\\工程文件\\1.2.2VINS\\自制软件\\材质库查询V1.0\\FSmatbinBD_V1.1\\src\\gui_qt\\assets\\app_icon.png'],
    contents_directory='internal',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='FSMatbinBD',
)
