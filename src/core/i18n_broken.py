import locale
from typing import Dict

class LanguageManager:
    """多语言管理器"""
    
    def __init__(self):
        self.current_language = self._detect_system_language()
        self.translations = self._load_translations()
    
    def _detect_system_language(self) -> str:
        """检测系统语言"""
        try:
            system_locale = locale.getdefaultlocale()[0]
            if system_locale:
                if system_locale.startswith('zh'):
                    return 'zh_CN'
                elif system_locale.startswith('ja'):
                    return 'ja_JP'
                elif system_locale.startswith('ko'):
                    return 'ko_KR'
                else:
                    return 'en_US'
            else:
                return 'en_US'
        except:
            return 'en_US'
            'sampler_type': '샘플러 유형',
            'sampler_path': '샘플러 경로',
            'unk14_x': 'unk14_x',
            'unk14_y': 'unk14_y',                 return 'ko_KR'
                else:
                    return 'en_US'
            else:
                return 'en_US'
        except:
            return 'en_US'
    
    def _load_translations(self) -> Dict[str, Dict[str, str]]:
        """加载翻译字典"""
        translations = {
            'zh_CN': self._get_chinese_translations(),
            'en_US': self._get_english_translations(),
            'ja_JP': self._get_japanese_translations(),
            'ko_KR': self._get_korean_translations(),
        }
        return translations
    
    def _get_chinese_translations(self) -> Dict[str, str]:
        """中文翻译"""
        return {
            # 主窗口
            'app_title': 'FS材质库查询',
            'version': 'v1.0',
            
            # 菜单
            'menu_file': '文件',
            'menu_import': '导入材质库',
            'menu_import_xml': '导入XML文件',
            'menu_import_folder': '导入文件夹',
            'menu_export': '导出XML',
            'menu_exit': '退出',
            'menu_tools': '工具',
            'menu_refresh': '刷新',
            'menu_library_manager': '库管理',
            'menu_help': '帮助',
            'menu_about': '关于',
            'menu_language': '语言',
            
            # 主界面
            'search_placeholder': '搜索材质...',
            'search_button': '搜索',
            'clear_button': '清空',
            'export_button': '导出XML',
            'add_library_button': '添加库',
            'library_manager_button': '库管理',
            
            # 材质信息
            'material_info': '材质信息',
            'filename': '文件名',
            'file_path': '文件路径',
            'shader_name': '着色器名称',
            'material_size': '材质大小',
            'modification_time': '修改时间',
            'creation_time': '创建时间',
            'parameters': '参数',
            'param_name': '参数名',
            'param_value': '参数值',
            'param_type': '参数类型',
            
            # 面板标题
            'material_list': '材质列表',
            'material_info_panel': '材质信息',
            'sampler_info': '采样器信息',
            
            # 采样器信息
            'sampler_name': '采样器名称',
            'texture_path': '纹理路径',
            'wrap_u': 'Wrap U',
            'wrap_v': 'Wrap V',
            'filter_mode': '过滤模式',
            'mip_mode': 'Mip模式',
            
            # 采样器表格
            'material_samples': '材质采样器',
            'sequence_number': '序号',
            'sampler_type': '采样器类型',
            'sampler_path': '采样器路径',
            'unk14_x': 'unk14_x',
            'unk14_y': 'unk14_y',
            
            # 状态信息
            'status_ready': '就绪',
            'status_loading': '加载中...',
            'status_searching': '搜索中...',
            'status_exporting': '导出中...',
            'loading_library': '正在加载材质库: {name}',
            'library_loaded': '材质库已加载: {name}',
            'search_complete': '搜索完成，找到 {count} 个结果',
            'export_complete': '导出完成: {filename}',
            
            # 提示信息
            'select_library_hint': '请选择一个材质库',
            'select_material_hint': '请选择一个材质查看详细信息',
            'select_material_detail_hint': '请选择一个材质查看详细信息',
            'no_library_selected': '未选择材质库',
            'no_material_selected': '未选择材质',
            'search_hint': '搜索',
            'no_results': '未找到匹配的结果',
            'loading_hint': '正在加载...',
            'all_materials': '全部材质',
            'add_parameter': '添加参数',
            
            # 错误信息
            'error': '错误',
            'warning': '警告',
            'info': '信息',
            'file_not_found': '文件未找到',
            'invalid_file_format': '无效的文件格式',
            'import_failed': '导入失败',
            'export_failed': '导出失败',
            'save_failed': '保存失败',
            'load_failed': '加载失败',
            'search_failed': '搜索失败',
            'operation_cancelled': '操作已取消',
            
            # 对话框
            'confirm': '确认',
            'cancel': '取消',
            'yes': '是',
            'no': '否',
            'ok': '确定',
            'apply': '应用',
            'close': '关闭',
            'save': '保存',
            'open': '打开',
            'delete': '删除',
            'edit': '编辑',
            'new': '新建',
            'copy': '复制',
            'paste': '粘贴',
            'cut': '剪切',
            'undo': '撤销',
            'redo': '重做',
            'find': '查找',
            'replace': '替换',
            'select_all': '全选',
            
            # 库管理
            'library_manager': '材质库管理',
            'library_label': '材质库:',
            'library_name': '库名称',
            'library_path': '库路径',
            'library_description': '描述',
            'add_library': '添加库',
            'edit_library': '编辑库',
            'delete_library': '删除库',
            'browse': '浏览',
            
            # 状态栏
            'status_bar_ready': '就绪',
            'status_bar_total_materials': '总材质数: {count}',
            'status_bar_selected_library': '当前库: {name}',
            'total_materials': '总材质数',
            'current_library': '当前库',
            'no_library': '无库',
            'materials_loaded': '已加载 {count} 个材质',
            'libraries_loaded': '已加载 {count} 个库',
            'copy_success': '已复制到剪贴板',
            'copy_failed': '复制失败',
            'path_copied': '路径已复制到剪贴板:\n{path}',
            'material_name_copied': '材质名称已复制: {name}',
            'refresh_library_list_failed': '刷新库列表失败',
            'no_xml_files_in_folder': '所选文件夹中未找到XML文件',
            'import_success_multiple': '从文件夹成功导入 {count} 个材质',
            'no_material_data_in_file': '文件中未找到材质数据',
            'import_single_success': '成功导入 {count} 个材质',
            'library_not_found': '未找到库信息',
            'confirm_delete_library_dialog': '确定要删除材质库 \'{name}\' 吗？\n这将删除库中的所有材质数据。',
            'library_deleted': '材质库已删除',
            'delete_failed': '删除失败',
            
            # 标签框文本
            'basic_info': '📋 基本信息',
            'editable_params': '⚙️ 可编辑参数',
            'imported_libraries': '已导入的材质库',
            'filter': '筛选',
            
            # 表单标签
            'type_label': '类型:',
            'name_label': '名称:',
            'value_label': '值:',
            'library_name_label': '库名称:',
            'description_optional': '描述 (可选):',
            
            # 材质信息字段
            'material_name': '材质名称',
            'shader_path': '着色器路径',
            'material_file_path': '材质文件路径',
            'compression_type': '压缩类型',
            'key_value': '键值',
            
            # 统计信息
            'sampler_count': '共 {count} 个采样器',
            'material_count': '共 {count} 个材质',
            'library_count': '共 {count} 个材质库',
            'material_info_status': '材质信息：{name}',
            'status_material_library': '材质数: {material_count} 材质: {total_count}',
            'key_label': '键名：',
            
            # 对话框和表单
            'add_library_dialog': '添加材质库',
            'ok_button': '确定',
            'cancel_button': '取消',
            'save_as_button': '另存为',
            'location_label': '位置：',
            'browse_button': '浏览',
            
            'about_text': 'FS材质库查询工具\n\n版本: v1.0\n\n这是一个用于查询和管理FS材质库的工具。\n支持材质预览、参数编辑、XML导入导出等功能。',
        }
    
    def _get_english_translations(self) -> Dict[str, str]:
        """英文翻译"""
        return {
            # 主窗口
            'app_title': 'FS Material Library Query',
            'version': 'v1.0',
            
            # 菜单
            'menu_file': 'File',
            'menu_import': 'Import Material Library',
            'menu_import_xml': 'Import XML File',
            'menu_import_folder': 'Import Folder',
            'menu_export': 'Export XML',
            'menu_exit': 'Exit',
            'menu_tools': 'Tools',
            'menu_refresh': 'Refresh',
            'menu_library_manager': 'Library Manager',
            'menu_help': 'Help',
            'menu_about': 'About',
            'menu_language': 'Language',
            
            # 主界面
            'search_placeholder': 'Search materials...',
            'search_button': 'Search',
            'clear_button': 'Clear',
            'export_button': 'Export XML',
            'add_library_button': 'Add Library',
            'library_manager_button': 'Library Manager',
            
            # 材质信息
            'material_info': 'Material Information',
            'filename': 'Filename',
            'file_path': 'File Path',
            'shader_name': 'Shader Name',
            'material_size': 'Material Size',
            'modification_time': 'Modification Time',
            'creation_time': 'Creation Time',
            'parameters': 'Parameters',
            'param_name': 'Parameter Name',
            'param_value': 'Parameter Value',
            'param_type': 'Parameter Type',
            
            # 面板标题
            'material_list': 'Material List',
            'material_info_panel': 'Material Information',
            'sampler_info': 'Sampler Information',
            
            # 采样器信息
            'sampler_name': 'Sampler Name',
            'texture_path': 'Texture Path',
            'wrap_u': 'Wrap U',
            'wrap_v': 'Wrap V',
            'filter_mode': 'Filter Mode',
            'mip_mode': 'Mip Mode',
            
            # 采样器表格
            'material_samples': 'Material Samplers',
            'sequence_number': 'Seq#',
            'sampler_type': 'Sampler Type',
            'sampler_path': 'Sampler Path',
            'unk14_x': 'unk14_x',
            'unk14_y': 'unk14_y',
            
            # 状态信息
            'status_ready': 'Ready',
            'status_loading': 'Loading...',
            'status_searching': 'Searching...',
            'status_exporting': 'Exporting...',
            'loading_library': 'Loading material library: {name}',
            'library_loaded': 'Material library loaded: {name}',
            'search_complete': 'Search complete, found {count} results',
            'export_complete': 'Export complete: {filename}',
            
            # 提示信息
            'select_library_hint': 'Please select a material library',
            'select_material_hint': 'Please select a material to view details',
            'select_material_detail_hint': 'Please select a material to view details',
            'no_library_selected': 'No library selected',
            'no_material_selected': 'No material selected',
            'search_hint': 'Search',
            'no_results': 'No matching results found',
            'loading_hint': 'Loading...',
            'all_materials': 'All Materials',
            'add_parameter': 'Add Parameter',
            
            # 错误信息
            'error': 'Error',
            'warning': 'Warning',
            'info': 'Information',
            'file_not_found': 'File not found',
            'invalid_file_format': 'Invalid file format',
            'import_failed': 'Import failed',
            'export_failed': 'Export failed',
            'save_failed': 'Save failed',
            'load_failed': 'Load failed',
            'search_failed': 'Search failed',
            'operation_cancelled': 'Operation cancelled',
            
            # 对话框
            'confirm': 'Confirm',
            'cancel': 'Cancel',
            'yes': 'Yes',
            'no': 'No',
            'ok': 'OK',
            'apply': 'Apply',
            'close': 'Close',
            'save': 'Save',
            'open': 'Open',
            'delete': 'Delete',
            'edit': 'Edit',
            'new': 'New',
            'copy': 'Copy',
            'paste': 'Paste',
            'cut': 'Cut',
            'undo': 'Undo',
            'redo': 'Redo',
            'find': 'Find',
            'replace': 'Replace',
            'select_all': 'Select All',
            
            # 库管理
            'library_manager': 'Material Library Manager',
            'library_label': 'Material Library:',
            'library_name': 'Library Name',
            'library_path': 'Library Path',
            'library_description': 'Description',
            'add_library': 'Add Library',
            'edit_library': 'Edit Library',
            'delete_library': 'Delete Library',
            'browse': 'Browse',
            
            # 状态栏
            'status_bar_ready': 'Ready',
            'status_bar_total_materials': 'Total materials: {count}',
            'status_bar_selected_library': 'Current library: {name}',
            'total_materials': 'Total Materials',
            'current_library': 'Current Library',
            'no_library': 'No Library',
            'materials_loaded': 'Loaded {count} materials',
            'libraries_loaded': 'Loaded {count} libraries',
            'copy_success': 'Copied to clipboard',
            'copy_failed': 'Copy failed',
            'path_copied': 'Path copied to clipboard:\n{path}',
            'material_name_copied': 'Material name copied: {name}',
            'refresh_library_list_failed': 'Failed to refresh library list',
            'no_xml_files_in_folder': 'No XML files found in selected folder',
            'import_success_multiple': 'Successfully imported {count} materials from folder',
            'no_material_data_in_file': 'No material data found in file',
            'import_single_success': 'Successfully imported {count} materials',
            'library_not_found': 'Library information not found',
            'confirm_delete_library_dialog': 'Are you sure you want to delete material library \'{name}\'?\nThis will delete all material data in the library.',
            'library_deleted': 'Material library deleted',
            'delete_failed': 'Delete failed',
            
            # 标签框文本
            'basic_info': '📋 Basic Information',
            'editable_params': '⚙️ Editable Parameters',
            'imported_libraries': 'Imported Material Libraries',
            'filter': 'Filter',
            
            # 表单标签
            'type_label': 'Type:',
            'name_label': 'Name:',
            'value_label': 'Value:',
            'library_name_label': 'Library Name:',
            'description_optional': 'Description (optional):',
            
            # 材质信息字段
            'material_name': 'Material Name',
            'shader_path': 'Shader Path',
            'material_file_path': 'Material File Path',
            'compression_type': 'Compression Type',
            'key_value': 'Key Value',
            
            # 统计信息
            'sampler_count': 'Total {count} samplers',
            'material_count': 'Total {count} materials',
            'library_count': 'Total {count} libraries',
            'material_info_status': 'Material Info: {name}',
            'status_material_library': 'Materials: {material_count} Total: {total_count}',
            'key_label': 'Key:',
            
            # 对话框和表单
            'add_library_dialog': 'Add Material Library',
            'ok_button': 'OK',
            'cancel_button': 'Cancel',
            'save_as_button': 'Save As',
            'location_label': 'Location:',
            'browse_button': 'Browse',
            
            'about_text': 'FS Material Library Query Tool\n\nVersion: v1.0\n\nThis is a tool for querying and managing FS material libraries.\nSupports material preview, parameter editing, XML import/export and other functions.',
        }
    
    def _get_japanese_translations(self) -> Dict[str, str]:
        """日文翻译"""
        return {
            # 主窗口
            'app_title': 'FSマテリアルライブラリ検索',
            'version': 'v1.0',
            
            # 菜单
            'menu_file': 'ファイル',
            'menu_import': 'マテリアルライブラリをインポート',
            'menu_import_xml': 'XMLファイルをインポート',
            'menu_import_folder': 'フォルダをインポート',
            'menu_export': 'XMLをエクスポート',
            'menu_exit': '終了',
            'menu_tools': 'ツール',
            'menu_refresh': '更新',
            'menu_library_manager': 'ライブラリマネージャー',
            'menu_help': 'ヘルプ',
            'menu_about': 'バージョン情報',
            'menu_language': '言語',
            
            # 主界面
            'search_placeholder': 'マテリアルを検索...',
            'search_button': '検索',
            'clear_button': 'クリア',
            'export_button': 'XMLエクスポート',
            'add_library_button': 'ライブラリを追加',
            'library_manager_button': 'ライブラリマネージャー',
            
            # 材质信息
            'material_info': 'マテリアル情報',
            'filename': 'ファイル名',
            'file_path': 'ファイルパス',
            'shader_name': 'シェーダー名',
            'material_size': 'マテリアルサイズ',
            'modification_time': '更新時刻',
            'creation_time': '作成時刻',
            'parameters': 'パラメーター',
            'param_name': 'パラメーター名',
            'param_value': 'パラメーター値',
            'param_type': 'パラメータータイプ',
            
            # 面板标题
            'material_list': 'マテリアルリスト',
            'material_info_panel': 'マテリアル情報',
            'sampler_info': 'サンプラー情報',
            
            # 采样器信息
            'sampler_name': 'サンプラー名',
            'texture_path': 'テクスチャパス',
            'wrap_u': 'Wrap U',
            'wrap_v': 'Wrap V',
            'filter_mode': 'フィルターモード',
            'mip_mode': 'Mipモード',
            
            # 采样器表格
            'material_samples': 'マテリアルサンプラー',
            'sequence_number': 'シーケンス番号',
            'sampler_type': 'サンプラータイプ',
            'sampler_path': 'サンプラーパス',
            'unk14_x': 'unk14_x',
            'unk14_y': 'unk14_y',
            
            # 状态信息
            'status_ready': '準備完了',
            'status_loading': '読み込み中...',
            'status_searching': '検索中...',
            'status_exporting': 'エクスポート中...',
            'loading_library': 'マテリアルライブラリを読み込み中: {name}',
            'library_loaded': 'マテリアルライブラリが読み込まれました: {name}',
            'search_complete': '検索完了、{count} 件の結果が見つかりました',
            'export_complete': 'エクスポート完了: {filename}',
            
            # 提示信息
            'select_library_hint': 'マテリアルライブラリを選択してください',
            'select_material_hint': '詳細を表示するマテリアルを選択してください',
            'select_material_detail_hint': '詳細を表示するマテリアルを選択してください',
            'no_library_selected': 'ライブラリが選択されていません',
            'no_material_selected': 'マテリアルが選択されていません',
            'search_hint': '検索',
            'no_results': '一致する結果が見つかりません',
            'loading_hint': '読み込み中...',
            'all_materials': 'すべてのマテリアル',
            'add_parameter': 'パラメーターを追加',
            
            # 错误信息
            'error': 'エラー',
            'warning': '警告',
            'info': '情報',
            'file_not_found': 'ファイルが見つかりません',
            'invalid_file_format': '無効なファイル形式',
            'import_failed': 'インポートに失敗',
            'export_failed': 'エクスポートに失敗',
            'save_failed': '保存に失敗',
            'load_failed': '読み込みに失敗',
            'search_failed': '検索に失敗',
            'operation_cancelled': '操作がキャンセルされました',
            
            # 对话框
            'confirm': '確認',
            'cancel': 'キャンセル',
            'yes': 'はい',
            'no': 'いいえ',
            'ok': 'OK',
            'apply': '適用',
            'close': '閉じる',
            'save': '保存',
            'open': '開く',
            'delete': '削除',
            'edit': '編集',
            'new': '新規',
            'copy': 'コピー',
            'paste': '貼り付け',
            'cut': '切り取り',
            'undo': '元に戻す',
            'redo': 'やり直し',
            'find': '検索',
            'replace': '置換',
            'select_all': 'すべて選択',
            
            # 库管理
            'library_manager': 'マテリアルライブラリマネージャー',
            'library_label': 'マテリアルライブラリ:',
            'library_name': 'ライブラリ名',
            'library_path': 'ライブラリパス',
            'library_description': '説明',
            'add_library': 'ライブラリを追加',
            'edit_library': 'ライブラリを編集',
            'delete_library': 'ライブラリを削除',
            'browse': '参照',
            
            # 状态栏
            'status_bar_ready': '準備完了',
            'status_bar_total_materials': '総マテリアル数: {count}',
            'status_bar_selected_library': '現在のライブラリ: {name}',
            'total_materials': '総マテリアル数',
            'current_library': '現在のライブラリ',
            'no_library': 'ライブラリなし',
            'materials_loaded': '{count} 個のマテリアルが読み込まれました',
            'libraries_loaded': '{count} 個のライブラリが読み込まれました',
            'copy_success': 'クリップボードにコピーしました',
            'copy_failed': 'コピーに失敗',
            'path_copied': 'パスをクリップボードにコピーしました:\n{path}',
            'material_name_copied': 'マテリアル名をコピーしました: {name}',
            'refresh_library_list_failed': 'ライブラリリストの更新に失敗',
            'no_xml_files_in_folder': '選択したフォルダにXMLファイルが見つかりません',
            'import_success_multiple': 'フォルダから {count} 個のマテリアルを正常にインポートしました',
            'no_material_data_in_file': 'ファイルにマテリアルデータが見つかりません',
            'import_single_success': '{count} 個のマテリアルを正常にインポートしました',
            'library_not_found': 'ライブラリ情報が見つかりません',
            'confirm_delete_library_dialog': 'マテリアルライブラリ \'{name}\' を削除しますか？\nライブラリ内のすべてのマテリアルデータが削除されます。',
            'library_deleted': 'マテリアルライブラリを削除しました',
            'delete_failed': '削除に失敗',
            
            # 标签框文本
            'basic_info': '📋 基本情報',
            'editable_params': '⚙️ 編集可能なパラメーター',
            'imported_libraries': 'インポートされたマテリアルライブラリ',
            'filter': 'フィルター',
            
            # 表单标签
            'type_label': 'タイプ:',
            'name_label': '名前:',
            'value_label': '値:',
            'library_name_label': 'ライブラリ名:',
            'description_optional': '説明 (任意):',
            
            # 材质信息字段
            'material_name': 'マテリアル名',
            'shader_path': 'シェーダーパス',
            'material_file_path': 'マテリアルファイルパス',
            'compression_type': '圧縮タイプ',
            'key_value': 'キー値',
            
            # 统计信息
            'sampler_count': '合計 {count}個のサンプラー',
            'material_count': '合計 {count}個のマテリアル',
            'library_count': '合計 {count}個のライブラリ',
            'material_info_status': 'マテリアル情報：{name}',
            'status_material_library': 'マテリアル数: {material_count} 総数: {total_count}',
            'key_label': 'キー:',
            
            # 对话框和表单
            'add_library_dialog': 'マテリアルライブラリを追加',
            'ok_button': 'OK',
            'cancel_button': 'キャンセル',
            'save_as_button': '名前を付けて保存',
            'location_label': '場所:',
            'browse_button': '参照',
            
            'about_text': 'FSマテリアルライブラリ検索ツール\n\nバージョン: v1.0\n\nFSマテリアルライブラリの検索と管理を行うツールです。\nマテリアルプレビュー、パラメーター編集、XMLインポート/エクスポートなどの機能をサポートしています。',
        }
    
    def _get_korean_translations(self) -> Dict[str, str]:
        """韩文翻译"""
        return {
            # 主窗口
            'app_title': 'FS 재질 라이브러리 검색',
            'version': 'v1.0',
            
            # 菜单
            'menu_file': '파일',
            'menu_import': '재질 라이브러리 가져오기',
            'menu_import_xml': 'XML 파일 가져오기',
            'menu_import_folder': '폴더 가져오기',
            'menu_export': 'XML 내보내기',
            'menu_exit': '종료',
            'menu_tools': '도구',
            'menu_refresh': '새로고침',
            'menu_library_manager': '라이브러리 관리자',
            'menu_help': '도움말',
            'menu_about': '정보',
            'menu_language': '언어',
            
            # 主界面
            'search_placeholder': '재질 검색...',
            'search_button': '검색',
            'clear_button': '지우기',
            'export_button': 'XML 내보내기',
            'add_library_button': '라이브러리 추가',
            'library_manager_button': '라이브러리 관리자',
            
            # 材质信息
            'material_info': '재질 정보',
            'filename': '파일명',
            'file_path': '파일 경로',
            'shader_name': '셰이더 이름',
            'material_size': '재질 크기',
            'modification_time': '수정 시간',
            'creation_time': '생성 시간',
            'parameters': '매개변수',
            'param_name': '매개변수 이름',
            'param_value': '매개변수 값',
            'param_type': '매개변수 유형',
            
            # 面板标题
            'material_list': '재질 목록',
            'material_info_panel': '재질 정보',
            'sampler_info': '샘플러 정보',
            
            # 采样器信息
            'sampler_name': '샘플러 이름',
            'texture_path': '텍스처 경로',
            'wrap_u': 'Wrap U',
            'wrap_v': 'Wrap V',
            'filter_mode': '필터 모드',
            'mip_mode': 'Mip 모드',
            
            # 状态信息
            'status_ready': '준비',
            'status_loading': '로딩 중...',
            'status_searching': '검색 중...',
            'status_exporting': '내보내기 중...',
            'loading_library': '재질 라이브러리 로딩 중: {name}',
            'library_loaded': '재질 라이브러리 로드됨: {name}',
            'search_complete': '검색 완료, {count}개 결과 발견',
            'export_complete': '내보내기 완료: {filename}',
            
            # 提示信息
            'select_library_hint': '재질 라이브러리를 선택하세요',
            'select_material_hint': '세부 정보를 보려면 재질을 선택하세요',
            'select_material_detail_hint': '세부 정보를 보려면 재질을 선택하세요',
            'no_library_selected': '라이브러리가 선택되지 않음',
            'no_material_selected': '재질이 선택되지 않음',
            'search_hint': '검색',
            'no_results': '일치하는 결과를 찾을 수 없음',
            'loading_hint': '로딩 중...',
            'all_materials': '모든 재질',
            'add_parameter': '매개변수 추가',
            
            # 错误信息
            'error': '오류',
            'warning': '경고',
            'info': '정보',
            'file_not_found': '파일을 찾을 수 없음',
            'invalid_file_format': '잘못된 파일 형식',
            'import_failed': '가져오기 실패',
            'export_failed': '내보내기 실패',
            'save_failed': '저장 실패',
            'load_failed': '로드 실패',
            'search_failed': '검색 실패',
            'operation_cancelled': '작업이 취소됨',
            
            # 对话框
            'confirm': '확인',
            'cancel': '취소',
            'yes': '예',
            'no': '아니오',
            'ok': '확인',
            'apply': '적용',
            'close': '닫기',
            'save': '저장',
            'open': '열기',
            'delete': '삭제',
            'edit': '편집',
            'new': '새로 만들기',
            'copy': '복사',
            'paste': '붙여넣기',
            'cut': '잘라내기',
            'undo': '실행 취소',
            'redo': '다시 실행',
            'find': '찾기',
            'replace': '바꾸기',
            'select_all': '모두 선택',
            
            # 库管理
            'library_manager': '재질 라이브러리 관리자',
            'library_label': '재질 라이브러리:',
            'library_name': '라이브러리 이름',
            'library_path': '라이브러리 경로',
            'library_description': '설명',
            'add_library': '라이브러리 추가',
            'edit_library': '라이브러리 편집',
            'delete_library': '라이브러리 삭제',
            'browse': '찾아보기',
            
            # 状态栏
            'status_bar_ready': '준비',
            'status_bar_total_materials': '총 재질 수: {count}',
            'status_bar_selected_library': '현재 라이브러리: {name}',
            'total_materials': '총 재질 수',
            'current_library': '현재 라이브러리',
            'no_library': '라이브러리 없음',
            'materials_loaded': '{count}개 재질 로드됨',
            'libraries_loaded': '{count}개 라이브러리 로드됨',
            'copy_success': '클립보드에 복사됨',
            'copy_failed': '복사 실패',
            'path_copied': '경로를 클립보드에 복사했습니다:\n{path}',
            'search_failed': '검색 실패',
            'material_name_copied': '재질 이름을 복사했습니다: {name}',
            'refresh_library_list_failed': '라이브러리 목록 새로고침 실패',
            'no_xml_files_in_folder': '선택한 폴더에서 XML 파일을 찾을 수 없습니다',
            'import_success_multiple': '폴더에서 {count}개의 재질을 성공적으로 가져왔습니다',
            'no_material_data_in_file': '파일에서 재질 데이터를 찾을 수 없습니다',
            'import_single_success': '{count}개의 재질을 성공적으로 가져왔습니다',
            'library_not_found': '라이브러리 정보를 찾을 수 없습니다',
            'confirm_delete_library_dialog': '재질 라이브러리 \'{name}\'을(를) 삭제하시겠습니까?\n라이브러리의 모든 재질 데이터가 삭제됩니다.',
            'library_deleted': '재질 라이브러리가 삭제되었습니다',
            'delete_failed': '삭제 실패',
            
            # 标签框文本
            'basic_info': '📋 기본 정보',
            'editable_params': '⚙️ 편집 가능한 매개변수',
            'imported_libraries': '가져온 재질 라이브러리',
            'filter': '필터',
            
            # 表单标签
            'type_label': '유형:',
            'name_label': '이름:',
            'value_label': '값:',
            'library_name_label': '라이브러리 이름:',
            'description_optional': '설명 (선택사항):',
            
            # 材质信息字段
            'material_name': '재질 이름',
            'shader_path': '셰이더 경로',
            'material_file_path': '재질 파일 경로',
            'compression_type': '압축 유형',
            'key_value': '키 값',
            
            # 统计信息
            'sampler_count': '총 {count}개의 샘플러',
            'material_count': '총 {count}개의 재질',
            'library_count': '총 {count}개의 라이브러리',
            'material_info_status': '재질 정보: {name}',
            'status_material_library': '재질수: {material_count} 총수: {total_count}',
            'key_label': '키:',
            
            # 对话框和表单
            'add_library_dialog': '재질 라이브러리 추가',
            'ok_button': '확인',
            'cancel_button': '취소',
            'save_as_button': '다른 이름으로 저장',
            'location_label': '위치:',
            'browse_button': '찾아보기',
            
            'about_text': 'FS 재질 라이브러리 검색 도구\n\n버전: v1.0\n\nFS 재질 라이브러리 검색 및 관리를 위한 도구입니다.\n재질 미리보기, 매개변수 편집, XML 가져오기/내보내기 등의 기능을 지원합니다.',
        }
    
    def get_text(self, key: str) -> str:
        """获取指定键的翻译文本"""
        try:
            if self.current_language in self.translations:
                return self.translations[self.current_language].get(key, key)
            else:
                # 如果当前语言不存在，使用英文作为后备
                return self.translations['en_US'].get(key, key)
        except Exception:
            return key
    
    def set_language(self, language: str):
        """设置当前语言"""
        if language in self.translations:
            self.current_language = language
    
    def get_current_language(self) -> str:
        """获取当前语言"""
        return self.current_language
    
    def get_available_languages(self) -> Dict[str, str]:
        """获取可用语言列表"""
        return {
            'zh_CN': '中文',
            'en_US': 'English',
            'ja_JP': '日本語',
            'ko_KR': '한국어'
        }

# 创建全局语言管理器实例
language_manager = LanguageManager()

def _(key: str) -> str:
    """快捷翻译函数"""
    return language_manager.get_text(key)