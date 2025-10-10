#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动封包管理界面
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
from typing import Dict, List
from ..core.i18n import language_manager
from ..utils.helpers import show_multilingual_confirmation

def _(key: str, **kwargs) -> str:
    """获取翻译文本的辅助函数"""
    text = language_manager.get_text(key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except:
            return text
    return text

class AutoPackDialog:
    """自动封包对话框"""
    
    def __init__(self, parent, autopack_manager, on_complete=None):
        self.parent = parent
        self.autopack_manager = autopack_manager
        self.on_complete = on_complete
        
        # 创建对话框
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(_('autopack_management'))
        self.dialog.geometry("900x700")
        self.dialog.minsize(800, 600)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(True, True)
        
        # 居中显示
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        # 绑定关闭事件
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_window_close)
        
        # 创建界面
        self._create_ui()
        
        # 加载数据
        self._refresh_pending_list()
    
    def _create_ui(self):
        """创建用户界面"""
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 标题
        title_label = ttk.Label(main_frame, text=_('autopack_management'), 
                               font=('TkDefaultFont', 12, 'bold'))
        title_label.pack(pady=(0, 10))
        
        # 统计信息
        stats_frame = ttk.LabelFrame(main_frame, text=_('statistics_info'), padding=10)
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.stats_label = ttk.Label(stats_frame, text=_('loading'))
        self.stats_label.pack(anchor=tk.W)
        
        # 基础封包目录选择
        dir_frame = ttk.LabelFrame(main_frame, text=_('pack_settings'), padding=10)
        dir_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 目录选择
        dir_select_frame = ttk.Frame(dir_frame)
        dir_select_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(dir_select_frame, text=_('pack_base_dir')).pack(side=tk.LEFT)
        self.base_dir_var = tk.StringVar()
        dir_entry = ttk.Entry(dir_select_frame, textvariable=self.base_dir_var, width=50)
        dir_entry.pack(side=tk.LEFT, padx=(10, 5), fill=tk.X, expand=True)
        ttk.Button(dir_select_frame, text=_('browse'), command=self._select_base_dir).pack(side=tk.RIGHT)
        
        # 操作按钮
        button_frame = ttk.Frame(dir_frame)
        button_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(button_frame, text=_('refresh_list'), command=self._refresh_pending_list).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text=_('clear_autopack_dir'), command=self._clear_autopack_dir).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text=_('execute_pack'), command=self._execute_pack, 
                  style='Primary.TButton').pack(side=tk.RIGHT)
        
        # 待封包列表
        list_frame = ttk.LabelFrame(main_frame, text=_('pending_pack_list'), padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 列表控制
        list_control_frame = ttk.Frame(list_frame)
        list_control_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(list_control_frame, text=_('target_path')).pack(side=tk.LEFT)
        self.target_path_var = tk.StringVar()
        path_entry = ttk.Entry(list_control_frame, textvariable=self.target_path_var, width=30)
        path_entry.pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(list_control_frame, text=_('set_selected'), command=self._set_target_path).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(list_control_frame, text=_('remove_selected'), command=self._remove_selected).pack(side=tk.LEFT)
        
        # 创建Treeview
        columns = ('ID', 'filename', 'target_path', 'added_time')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        
        # 设置列标题
        self.tree.heading('ID', text=_('id_column'))
        self.tree.heading('filename', text=_('filename_column'))
        self.tree.heading('target_path', text=_('target_path_column'))
        self.tree.heading('added_time', text=_('added_time_column'))
        
        # 设置列宽
        self.tree.column('ID', width=50, anchor=tk.CENTER)
        self.tree.column('filename', width=200)
        self.tree.column('target_path', width=200)
        self.tree.column('added_time', width=150, anchor=tk.CENTER)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # 布局
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 状态栏
        self.status_var = tk.StringVar(value=_('ready'))
        status_label = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_label.pack(fill=tk.X, pady=(5, 0))
    
    def _select_base_dir(self):
        """选择基础封包目录"""
        directory = filedialog.askdirectory(title=_('select_pack_base_dir'))
        if directory:
            self.base_dir_var.set(directory)
    
    def _refresh_pending_list(self):
        """刷新待封包列表"""
        # 清空现有项目
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 加载待封包项目
        pending_list = self.autopack_manager.get_pending_list()
        for item in pending_list:
            self.tree.insert('', tk.END, values=(
                item['id'],
                item['filename'],
                item.get('target_path', ''),
                item['added_time'][:19]  # 只显示日期时间部分
            ))
        
        # 更新统计信息
        stats = self.autopack_manager.get_statistics()
        stats_text = _('total_with_without').format(total=stats['total_pending'], with_path=stats['with_target_path'], without_path=stats['without_target_path'])
        self.stats_label.config(text=stats_text)
        
        self.status_var.set(_('list_refreshed').format(count=len(pending_list)))
    
    def _set_target_path(self):
        """设置选中项的目标路径"""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning(_('warning'), _('warning_select_items'))
            return
        
        target_path = self.target_path_var.get().strip()
        if not target_path:
            messagebox.showwarning(_('warning'), _('warning_enter_path'))
            return
        
        # 获取选中项的ID
        item_ids = []
        for item in selected_items:
            values = self.tree.item(item)['values']
            item_ids.append(int(values[0]))  # ID在第一列
        
        # 更新目标路径
        self.autopack_manager.update_target_path(item_ids, target_path)
        
        # 刷新列表
        self._refresh_pending_list()
        
        self.status_var.set(_('set_target_path_result').format(count=len(item_ids), path=target_path))
    
    def _remove_selected(self):
        """删除选中项"""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning(_('warning'), _('warning_select_delete'))
            return
        
        if not show_multilingual_confirmation(_('warning'), _('confirm_delete').format(count=len(selected_items)), parent=self):
            return
        
        # 获取选中项的ID
        item_ids = []
        for item in selected_items:
            values = self.tree.item(item)['values']
            item_ids.append(int(values[0]))
        
        # 删除项目
        self.autopack_manager.remove_from_pending(item_ids)
        
        # 刷新列表
        self._refresh_pending_list()
        
        self.status_var.set(_('items_deleted').format(count=len(item_ids)))
    
    def _clear_autopack_dir(self):
        """清理autopack目录"""
        if not show_multilingual_confirmation(_('warning'), _('confirm_clear'), parent=self):
            return
        
        try:
            self.autopack_manager.clear_autopack_dir()
            self.status_var.set(_('autopack_cleared'))
            messagebox.showinfo(_('clear_success'), _('clear_complete'))
        except Exception as e:
            messagebox.showerror(_('error'), _('clear_error').format(error=str(e)))
    
    def _execute_pack(self):
        """执行封包"""
        base_dir = self.base_dir_var.get().strip()
        if not base_dir:
            messagebox.showwarning(_('warning'), _('warning_no_base_dir'))
            return
        
        if not os.path.exists(base_dir):
            messagebox.showerror(_('error'), _('error_base_dir_not_exist').format(path=base_dir))
            return
        
        # 检查是否有设置目标路径的项目
        stats = self.autopack_manager.get_statistics()
        if stats['with_target_path'] == 0:
            messagebox.showwarning(_('warning'), _('warning_no_target_path'))
            return
        
        if not show_multilingual_confirmation(_('warning'), _('confirm_pack').format(count=stats['with_target_path'], dir=base_dir), parent=self):
            return
        
        # 在后台线程中执行封包
        self.status_var.set(_('packing'))
        threading.Thread(target=self._pack_thread, args=(base_dir,), daemon=True).start()
    
    def _pack_thread(self, base_dir: str):
        """封包线程"""
        try:
            result = self.autopack_manager.execute_autopack(base_dir)
            
            # 在主线程中更新UI
            self.dialog.after(0, self._pack_complete, result)
            
        except Exception as e:
            error_result = {
                'success': False,
                'error': str(e),
                'packed_count': 0,
                'failed_count': 0
            }
            self.dialog.after(0, self._pack_complete, error_result)
    
    def _pack_complete(self, result: Dict):
        """封包完成回调"""
        # 添加调试信息
        print(f"封包完成回调: success={result.get('success')}, packed_count={result.get('packed_count')}, failed_count={result.get('failed_count')}")
        print(f"错误信息: {result.get('error', '无')}")
        
        if result['success']:
            message = _('pack_complete_detail').format(success=result['packed_count'], failed=result['failed_count'])
            if result['failed_files']:
                message += "\n\n" + _('failed_files') + ":\n" + "\n".join([f"- {f['filename']}: {f['error']}" for f in result['failed_files']])
            
            messagebox.showinfo(_('pack_complete'), message)
            self.status_var.set(_('pack_complete_status').format(success=result['packed_count'], failed=result['failed_count']))
        else:
            messagebox.showerror(_('pack_failed'), _('pack_error').format(error=result.get('error', _('unknown_error'))))
            self.status_var.set(_('pack_failed_status'))
        
        # 刷新列表
        self._refresh_pending_list()
        
        # 调用完成回调
        if self.on_complete:
            self.on_complete(result)
    
    def _on_window_close(self):
        """窗口关闭事件处理"""
        self.dialog.destroy()


class DCXImportDialog:
    """DCX导入对话框"""
    
    def __init__(self, parent, database, on_complete=None):
        self.parent = parent
        self.database = database
        self.on_complete = on_complete
        
        # 创建对话框
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(_('dcx_dialog_title'))
        self.dialog.geometry("650x750")  # 增加长度，减少宽度：650x750（原来800x600）
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(True, True)
        
        # 居中显示
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 100, parent.winfo_rooty() + 100))
        
        # 绑定关闭事件
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_window_close)
        
        # 创建界面
        self._create_ui()
    
    def _create_ui(self):
        """创建用户界面"""
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 标题
        title_label = ttk.Label(main_frame, text=_('import_dcx_library'), 
                               font=('TkDefaultFont', 12, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # 说明文本
        info_label = ttk.Label(main_frame, 
                               text=_('drop_dcx_here'),
                               font=('TkDefaultFont', 10),
                               foreground='gray')
        info_label.pack(pady=(0, 15))
        
        # DCX文件选择区域 - 优化为拖放区域
        file_frame = ttk.LabelFrame(main_frame, text=_('dcx_file_selection'), padding=15)
        file_frame.pack(fill=tk.X, pady=(0, 15))
        
        # 拖放区域
        drop_frame = ttk.Frame(file_frame, height=80)
        drop_frame.pack(fill=tk.X, pady=(0, 10))
        drop_frame.pack_propagate(False)
        
        drop_label = ttk.Label(drop_frame, 
                              text=_('drop_dcx_zone'),
                              anchor=tk.CENTER,
                              font=('TkDefaultFont', 10))
        drop_label.pack(expand=True, fill=tk.BOTH)
        
        # DCX文件路径显示
        ttk.Label(file_frame, text=_('selected_file')).pack(anchor=tk.W, pady=(0, 5))
        file_select_frame = ttk.Frame(file_frame)
        file_select_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.dcx_file_var = tk.StringVar()
        file_entry = ttk.Entry(file_select_frame, textvariable=self.dcx_file_var, state='readonly')
        file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        ttk.Button(file_select_frame, text=_('browse'), command=self._select_dcx_file).pack(side=tk.RIGHT)
        
        # 自动解包说明
        auto_info_frame = ttk.LabelFrame(main_frame, text=_('auto_unpack_info'), padding=15)
        auto_info_frame.pack(fill=tk.X, pady=(0, 15))
        
        info_text = _('auto_unpack_description')
        
        ttk.Label(auto_info_frame, text=info_text, justify=tk.LEFT).pack(anchor=tk.W)
        
        # 材质库信息
        info_frame = ttk.LabelFrame(main_frame, text=_('library_info'), padding=15)
        info_frame.pack(fill=tk.X, pady=(0, 15))
        
        # 库名称
        ttk.Label(info_frame, text=_('library_name_input')).pack(anchor=tk.W, pady=(0, 5))
        self.library_name_var = tk.StringVar()
        ttk.Entry(info_frame, textvariable=self.library_name_var).pack(fill=tk.X, pady=(0, 10))
        
        # 库描述
        ttk.Label(info_frame, text=_('description_input')).pack(anchor=tk.W, pady=(0, 5))
        self.description_text = tk.Text(info_frame, height=3, wrap=tk.WORD)
        self.description_text.pack(fill=tk.X, pady=(0, 10))
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(15, 0))
        
        ttk.Button(button_frame, text=_('cancel'), command=self._on_window_close).pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(button_frame, text=_('start_auto_unpack'), command=self._start_import, 
                  style='Primary.TButton').pack(side=tk.RIGHT)
        
        # 进度显示
        self.progress_frame = ttk.LabelFrame(main_frame, text=_('auto_unpack_progress'), padding=15)
        # 初始时隐藏
        
        self.progress_var = tk.StringVar(value=_('waiting_to_start'))
        self.progress_label = ttk.Label(self.progress_frame, textvariable=self.progress_var)
        self.progress_label.pack(pady=(0, 10))
        
        self.progress_bar = ttk.Progressbar(self.progress_frame, mode='indeterminate')
        self.progress_bar.pack(fill=tk.X)
        
        # 启用拖放功能（如果支持）
        self._setup_drag_drop(drop_frame)
    
    def _setup_drag_drop(self, widget):
        """设置拖放功能（简化版）"""
        try:
            # 为拖放区域添加视觉效果
            widget.bind("<Button-1>", lambda e: self._select_dcx_file())
            
            # 添加视觉提示
            def on_enter(event):
                widget.configure(cursor="hand2")
            
            def on_leave(event):
                widget.configure(cursor="")
            
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
            
        except Exception as e:
            # 如果拖放功能不可用，只记录日志但不影响正常使用
            print(_('drag_drop_init_failed').format(error=str(e)))
    
    def _select_dcx_file(self):
        """选择DCX文件"""
        file_path = filedialog.askopenfilename(
            title=_('select_dcx_file'),
            filetypes=[(_('dcx_files'), "*.dcx"), (_('all_files'), "*.*")]
        )
        if file_path:
            self.dcx_file_var.set(file_path)
            # 自动设置库名称
            if not self.library_name_var.get():
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                self.library_name_var.set(base_name)
    
    def _start_import(self):
        """开始导入"""
        dcx_file = self.dcx_file_var.get().strip()
        library_name = self.library_name_var.get().strip()
        description = self.description_text.get(1.0, tk.END).strip()
        
        # 验证输入
        if not dcx_file:
            messagebox.showwarning(_('warning'), _('please_select_dcx'))
            return
        
        if not os.path.exists(dcx_file):
            messagebox.showerror(_('error'), _('dcx_not_found', path=dcx_file))
            return
        
        if not library_name:
            messagebox.showwarning(_('warning'), _('please_enter_library_name'))
            return
        
        # 显示进度
        self.progress_frame.pack(fill=tk.X, pady=(15, 0))
        self.progress_bar.start()
        self.progress_var.set(_('unpacking_dcx'))
        
        # 在后台线程中执行导入
        threading.Thread(target=self._import_thread, args=(dcx_file, library_name, description), daemon=True).start()
    
    def _import_thread(self, dcx_file: str, library_name: str, description: str):
        """导入线程"""
        try:
            from ..core.witchybnd_processor import MaterialLibraryImporter
            
            importer = MaterialLibraryImporter(self.database)
            
            # 更新进度
            self.dialog.after(0, lambda: self.progress_var.set(_('unpacking_no_path')))
            
            result = importer.import_from_dcx(dcx_file, library_name, description)
            
            # 在主线程中更新UI
            self.dialog.after(0, self._import_complete, result)
            
        except Exception as e:
            error_result = {
                'success': False,
                'error': str(e),
                'library_id': None,
                'material_count': 0
            }
            self.dialog.after(0, self._import_complete, error_result)
    
    def _import_complete(self, result: Dict):
        """导入完成回调"""
        self.progress_bar.stop()
        
        if result['success']:
            message = _('dcx_import_complete', library_id=result['library_id'], material_count=result['material_count'])
            messagebox.showinfo(_('import_success'), message)
            
            # 调用完成回调
            if self.on_complete:
                self.on_complete(result)
            
            # 关闭对话框
            self.dialog.destroy()
        else:
            self.progress_var.set(_('import_failed'))
            messagebox.showerror(_('import_failed'), _('dcx_import_error', error=result.get('error', _('unknown_error'))))
    
    def _on_window_close(self):
        """窗口关闭事件处理"""
        self.dialog.destroy()