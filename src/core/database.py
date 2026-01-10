#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库操作模块 - 用于管理材质库数据（重构版）
"""

import sqlite3
import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

# 导入资源路径辅助模块
from src.utils.resource_path import get_database_path

# 配置日志
logger = logging.getLogger(__name__)
# 临时设置为DEBUG级别进行调试
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(name)s:%(message)s')

class MaterialDatabase:
    """材质数据库管理类"""
    
    def __init__(self, db_path: str = None):
        """
        初始化数据库连接
        
        Args:
            db_path: 数据库文件路径，如果为 None 则使用默认路径
        """
        # 使用资源路径辅助模块获取默认数据库路径
        if db_path is None:
            db_path = get_database_path()
        self.db_path = db_path
        
        # 确保数据库目录存在
        if db_path != ":memory:":  # 内存数据库不需要创建目录
            db_dir = os.path.dirname(db_path)
            if db_dir:  # 如果有目录部分
                os.makedirs(db_dir, exist_ok=True)
        
        # 初始化数据库
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表结构"""
        try:
            # 调试：打印数据库路径信息
            import sys
            print(f"[DEBUG] 数据库路径: {self.db_path}")
            print(f"[DEBUG] 文件存在: {os.path.exists(self.db_path)}")
            if os.path.exists(self.db_path):
                print(f"[DEBUG] 文件大小: {os.path.getsize(self.db_path)} bytes")
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 创建材质库表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS material_libraries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE,
                        description TEXT,
                        source_path TEXT,
                        created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 创建材质表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS materials (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        library_id INTEGER NOT NULL,
                        file_path TEXT NOT NULL,
                        file_name TEXT NOT NULL,
                        filename TEXT,
                        shader_path TEXT,
                        source_path TEXT,
                        compression TEXT,
                        key_value TEXT,
                        created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (library_id) REFERENCES material_libraries (id)
                    )
                ''')
                
                # 创建参数表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS material_params (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        material_id INTEGER NOT NULL,
                        name TEXT NOT NULL,
                        type TEXT NOT NULL,
                        value TEXT,
                        key_value TEXT,
                        sort_order INTEGER DEFAULT 0,
                        FOREIGN KEY (material_id) REFERENCES materials (id)
                    )
                ''')
                
                # 创建样例表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS material_samplers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        material_id INTEGER NOT NULL,
                        type TEXT NOT NULL,
                        path TEXT,
                        key_value TEXT,
                        unk14_x INTEGER DEFAULT 0,
                        unk14_y INTEGER DEFAULT 0,
                        sort_order INTEGER DEFAULT 0,
                        FOREIGN KEY (material_id) REFERENCES materials (id)
                    )
                ''')
                
                # 创建索引
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_materials_library ON materials(library_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_materials_name ON materials(filename)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_params_material ON material_params(material_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_samplers_material ON material_samplers(material_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_samplers_type ON material_samplers(type)')
                
                # 性能优化索引：加速按sort_order排序的查询
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_params_material_sort ON material_params(material_id, sort_order)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_samplers_material_sort ON material_samplers(material_id, sort_order)')
                
                # 搜索优化索引
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_materials_shader ON materials(shader_path)')
                
                # 添加 display_order 列（如果不存在）- 用于控制库的显示顺序
                try:
                    cursor.execute('ALTER TABLE material_libraries ADD COLUMN display_order INTEGER DEFAULT 0')
                    # 为已有库初始化 display_order（按创建时间排序）
                    cursor.execute('''
                        UPDATE material_libraries SET display_order = (
                            SELECT COUNT(*) FROM material_libraries t2 
                            WHERE t2.created_time < material_libraries.created_time OR 
                                  (t2.created_time = material_libraries.created_time AND t2.id < material_libraries.id)
                        ) + 1
                    ''')
                    logger.info("添加 display_order 列成功")
                except sqlite3.OperationalError:
                    # 列已存在，忽略
                    pass
                
                conn.commit()
                logger.info("数据库初始化完成")
                
        except sqlite3.Error as e:
            logger.error(f"数据库初始化失败: {str(e)}")
            raise
    
    def create_library(self, name: str, description: str = "", source_path: str = "") -> int:
        """创建新的材质库"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO material_libraries (name, description, source_path, display_order)
                    VALUES (?, ?, ?, (SELECT COALESCE(MAX(display_order), 0) + 1 FROM material_libraries))
                ''', (name, description, source_path))
                
                library_id = cursor.lastrowid
                conn.commit()
                logger.info(f"创建材质库成功: {name} (ID: {library_id})")
                return library_id
                
        except sqlite3.IntegrityError:
            logger.error(f"材质库名称已存在: {name}")
            raise ValueError(f"材质库名称 '{name}' 已存在")
        except sqlite3.Error as e:
            logger.error(f"创建材质库失败: {str(e)}")
            raise

    # ===== compatibility aliases (for older UI / Qt UI) =====
    def add_library(self, name: str, source_path: str, description: str = "") -> int:
        """兼容旧接口：新增材质库。

        旧UI/部分脚本使用 add_library(name, path)。这里映射到 create_library。
        """
        return self.create_library(name=name, description=description, source_path=source_path)

    def remove_library(self, library_id: int):
        """兼容旧接口：删除材质库。"""
        return self.delete_library(library_id)

    def rescan_library(self, library_id: int):
        """兼容旧接口：重新扫描材质库。

        当前重构版数据库未内置扫描逻辑（扫描通常在导入阶段由上层完成）。
        这里保留占位，供Qt库管理弹窗调用；后续可接入实际扫描实现。
        """
        raise NotImplementedError("rescan_library 尚未接入扫描实现")
    
    def get_libraries(self) -> List[Dict[str, Any]]:
        """获取所有材质库"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, name, description, source_path, created_time, updated_time, 
                           COALESCE(display_order, id) as display_order
                    FROM material_libraries
                    ORDER BY display_order ASC
                ''')
                
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            logger.error(f"获取材质库失败: {str(e)}")
            return []
    
    def get_material_count(self, library_id: int) -> int:
        """获取指定库中的材质数量"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM materials WHERE library_id = ?
                ''', (library_id,))
                
                result = cursor.fetchone()
                return result[0] if result else 0
                
        except sqlite3.Error as e:
            logger.error(f"获取材质数量失败: {str(e)}")
            return 0
    
    def update_library(
        self,
        library_id: int,
        name: str = None,
        description: str = None,
        source_path: str = None,
    ):
        """更新材质库信息（支持更新 source_path）。"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                updates = []
                params = []
                
                if name is not None:
                    updates.append("name = ?")
                    params.append(name)
                
                if description is not None:
                    updates.append("description = ?")
                    params.append(description)

                if source_path is not None:
                    updates.append("source_path = ?")
                    params.append(source_path)
                
                if updates:
                    updates.append("updated_time = CURRENT_TIMESTAMP")
                    params.append(library_id)
                    
                    query = f"UPDATE material_libraries SET {', '.join(updates)} WHERE id = ?"
                    cursor.execute(query, params)
                    conn.commit()
                    logger.info(f"更新材质库成功: ID {library_id}")
                
        except sqlite3.Error as e:
            logger.error(f"更新材质库失败: {str(e)}")
            raise
    
    def delete_library(self, library_id: int):
        """删除材质库及其所有材质"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 获取库中所有材质ID
                cursor.execute("SELECT id FROM materials WHERE library_id = ?", (library_id,))
                material_ids = [row[0] for row in cursor.fetchall()]
                
                # 删除材质的参数和样例
                for material_id in material_ids:
                    cursor.execute("DELETE FROM material_params WHERE material_id = ?", (material_id,))
                    cursor.execute("DELETE FROM material_samplers WHERE material_id = ?", (material_id,))
                
                # 删除材质
                cursor.execute("DELETE FROM materials WHERE library_id = ?", (library_id,))
                
                # 删除材质库
                cursor.execute("DELETE FROM material_libraries WHERE id = ?", (library_id,))
                
                conn.commit()
                logger.info(f"删除材质库成功: ID {library_id}")
                
        except sqlite3.Error as e:
            logger.error(f"删除材质库失败: {str(e)}")
            raise
    
    def swap_library_order(self, library_id_1: int, library_id_2: int):
        """交换两个库的显示顺序"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 获取两个库的当前顺序
                cursor.execute(
                    "SELECT id, display_order FROM material_libraries WHERE id IN (?, ?)",
                    (library_id_1, library_id_2)
                )
                rows = cursor.fetchall()
                
                if len(rows) != 2:
                    raise ValueError("找不到指定的库")
                
                order_map = {row[0]: row[1] for row in rows}
                order1 = order_map.get(library_id_1)
                order2 = order_map.get(library_id_2)
                
                # 交换顺序
                cursor.execute(
                    "UPDATE material_libraries SET display_order = ? WHERE id = ?",
                    (order2, library_id_1)
                )
                cursor.execute(
                    "UPDATE material_libraries SET display_order = ? WHERE id = ?",
                    (order1, library_id_2)
                )
                
                conn.commit()
                logger.info(f"交换库顺序成功: {library_id_1} <-> {library_id_2}")
                
        except sqlite3.Error as e:
            logger.error(f"交换库顺序失败: {str(e)}")
            raise
    
    def reorder_libraries(self):
        """重新整理所有库的 display_order，使其从1开始连续"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 按当前 display_order 获取所有库
                cursor.execute(
                    "SELECT id FROM material_libraries ORDER BY COALESCE(display_order, id) ASC"
                )
                library_ids = [row[0] for row in cursor.fetchall()]
                
                # 重新分配 display_order
                for new_order, lib_id in enumerate(library_ids, start=1):
                    cursor.execute(
                        "UPDATE material_libraries SET display_order = ? WHERE id = ?",
                        (new_order, lib_id)
                    )
                
                conn.commit()
                logger.info(f"重新整理库顺序成功: 共 {len(library_ids)} 个库")
                
        except sqlite3.Error as e:
            logger.error(f"重新整理库顺序失败: {str(e)}")
            raise
    
    def add_materials(self, library_id: int, materials_data: List[Dict[str, Any]], 
                      progress_callback=None, batch_size: int = 100):
        """
        批量添加材质到指定库（优化版本）
        
        使用批量插入和事务优化，大幅提升导入速度
        
        Args:
            library_id: 目标材质库ID
            materials_data: 材质数据列表
            progress_callback: 进度回调函数 callback(current, total, message)
            batch_size: 批量提交大小，默认100
        """
        try:
            total = len(materials_data)
            logger.info(f"开始批量添加 {total} 个材质到库 {library_id}...")
            
            with sqlite3.connect(self.db_path) as conn:
                # 优化 SQLite 性能
                conn.execute("PRAGMA synchronous = OFF")
                conn.execute("PRAGMA journal_mode = MEMORY")
                conn.execute("PRAGMA cache_size = 10000")
                cursor = conn.cursor()
                
                # 预编译 SQL 语句
                material_sql = '''
                    INSERT INTO materials (
                        library_id, file_path, file_name, filename, 
                        shader_path, source_path, compression, key_value
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                '''
                param_sql = '''
                    INSERT INTO material_params (material_id, name, type, value, key_value, sort_order)
                    VALUES (?, ?, ?, ?, ?, ?)
                '''
                sampler_sql = '''
                    INSERT INTO material_samplers (
                        material_id, type, path, key_value, unk14_x, unk14_y, sort_order
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                '''
                
                processed = 0
                for i, material_data in enumerate(materials_data):
                    # 插入材质基本信息
                    cursor.execute(material_sql, (
                        library_id,
                        material_data.get('file_path', ''),
                        material_data.get('file_name', ''),
                        material_data.get('filename', ''),
                        material_data.get('shader_path', ''),
                        material_data.get('source_path', ''),
                        material_data.get('compression', ''),
                        material_data.get('key', '')
                    ))
                    
                    material_id = cursor.lastrowid
                    
                    # 批量准备参数数据
                    params_data = []
                    for param_index, param in enumerate(material_data.get('params', [])):
                        params_data.append((
                            material_id,
                            param.get('name', ''),
                            param.get('type', ''),
                            json.dumps(param.get('value')),
                            param.get('key', ''),
                            param_index
                        ))
                    
                    # 批量插入参数
                    if params_data:
                        cursor.executemany(param_sql, params_data)
                    
                    # 批量准备采样器数据
                    samplers_data = []
                    for sampler_index, sampler in enumerate(material_data.get('samplers', [])):
                        unk14 = sampler.get('unk14', {})
                        samplers_data.append((
                            material_id,
                            sampler.get('type', ''),
                            sampler.get('path', ''),
                            sampler.get('key', ''),
                            unk14.get('X', 0),
                            unk14.get('Y', 0),
                            sampler_index
                        ))
                    
                    # 批量插入采样器
                    if samplers_data:
                        cursor.executemany(sampler_sql, samplers_data)
                    
                    processed += 1
                    
                    # 每 batch_size 个材质提交一次，并报告进度
                    if processed % batch_size == 0:
                        conn.commit()
                        if progress_callback:
                            progress_callback(processed, total, f"已导入 {processed}/{total} 个材质")
                        logger.debug(f"批量提交: {processed}/{total}")
                
                # 最终提交
                conn.commit()
                
                if progress_callback:
                    progress_callback(total, total, f"完成导入 {total} 个材质")
                
                logger.info(f"成功添加 {total} 个材质到库 {library_id}")
                
        except sqlite3.Error as e:
            logger.error(f"添加材质失败: {str(e)}")
            raise
                
        except sqlite3.Error as e:
            logger.error(f"添加材质失败: {str(e)}")
            raise
    
    def search_materials(self, library_id: int = None, keyword: str = "", 
                        material_type: str = "", material_path: str = "") -> List[Dict[str, Any]]:
        """搜索材质（支持文件名、路径模糊搜索，自动提取路径中的文件名）"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # 构建基础查询
                base_query = '''
                    SELECT DISTINCT m.id, m.library_id, m.file_path, m.file_name, 
                           m.filename, m.shader_path, m.source_path, m.compression, 
                           m.key_value, m.created_time, l.name as library_name
                    FROM materials m
                    LEFT JOIN material_libraries l ON m.library_id = l.id
                '''
                
                conditions = []
                params = []
                
                # 添加库ID条件
                if library_id is not None:
                    conditions.append("m.library_id = ?")
                    params.append(library_id)
                
                # 添加关键字条件（增强：支持文件名、shader_path、source_path）
                if keyword:
                    # 自动提取文件名部分（支持完整路径输入）
                    import os
                    search_keyword = keyword
                    # 如果输入包含路径分隔符，提取文件名部分
                    if '\\' in keyword or '/' in keyword:
                        filename_part = os.path.basename(keyword.replace('\\', '/'))
                        if filename_part:
                            search_keyword = filename_part
                    
                    # 多字段模糊搜索
                    conditions.append("""(
                        m.filename LIKE ? OR 
                        m.file_name LIKE ? OR 
                        m.shader_path LIKE ? OR 
                        m.source_path LIKE ?
                    )""")
                    like_pattern = f"%{search_keyword}%"
                    params.extend([like_pattern, like_pattern, like_pattern, like_pattern])
                
                # 添加材质类型和路径条件（需要关联samplers表）
                if material_type or material_path:
                    base_query += " LEFT JOIN material_samplers s ON m.id = s.material_id"
                    
                    if material_type:
                        conditions.append("s.type LIKE ?")
                        params.append(f"%{material_type}%")
                    
                    if material_path:
                        conditions.append("s.path LIKE ?")
                        params.append(f"%{material_path}%")
                
                # 组装最终查询
                if conditions:
                    base_query += " WHERE " + " AND ".join(conditions)
                
                base_query += " ORDER BY m.filename"
                
                cursor.execute(base_query, params)
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            logger.error(f"搜索材质失败: {str(e)}")
            return []
    
    def search_materials_extended(self, library_id: int = None, keyword: str = "") -> List[Dict[str, Any]]:
        """扩展搜索材质（支持材质名称、着色器名称、样例名称）"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # 构建查询
                base_query = '''
                    SELECT DISTINCT m.id, m.library_id, m.file_path, m.file_name, 
                           m.filename, m.shader_path, m.source_path, m.compression, 
                           m.key_value, m.created_time, l.name as library_name
                    FROM materials m
                    LEFT JOIN material_libraries l ON m.library_id = l.id
                    LEFT JOIN material_samplers s ON m.id = s.material_id
                '''
                
                conditions = []
                params = []
                
                # 添加库ID条件
                if library_id is not None:
                    conditions.append("m.library_id = ?")
                    params.append(library_id)
                
                # 添加关键字搜索条件（材质名称、着色器路径、样例类型）
                if keyword:
                    search_conditions = [
                        "m.filename LIKE ?",
                        "m.shader_path LIKE ?", 
                        "s.type LIKE ?"
                    ]
                    conditions.append(f"({' OR '.join(search_conditions)})")
                    keyword_param = f"%{keyword}%"
                    params.extend([keyword_param, keyword_param, keyword_param])
                
                # 组装最终查询
                if conditions:
                    base_query += " WHERE " + " AND ".join(conditions)
                
                base_query += " ORDER BY m.filename"
                
                cursor.execute(base_query, params)
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            logger.error(f"扩展搜索材质失败: {str(e)}")
            return []
    
    def advanced_search_materials(self, search_criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """高级搜索材质（支持多条件和匹配模式）"""
        try:
            logger.debug(f"[数据库调试] 接收到的搜索条件: {search_criteria}")
            
            with sqlite3.connect(self.db_path) as conn:
                # 确保每次都重新设置row_factory
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # 基础查询
                base_query = '''
                    SELECT DISTINCT m.id, m.library_id, m.file_path, m.file_name, 
                           m.filename, m.shader_path, m.source_path, m.compression, 
                           m.key_value, m.created_time, l.name as library_name
                    FROM materials m
                    LEFT JOIN material_libraries l ON m.library_id = l.id
                    LEFT JOIN material_samplers s ON m.id = s.material_id
                    LEFT JOIN material_params p ON m.id = p.material_id
                '''
                
                conditions = []
                params = []
                
                # 库筛选
                if search_criteria.get('library_id'):
                    conditions.append("m.library_id = ?")
                    params.append(search_criteria['library_id'])
                
                # 获取匹配模式和模糊搜索设置
                match_mode = search_criteria.get('match_mode', 'any')  # 'any' 或 'all'
                fuzzy_search = search_criteria.get('fuzzy_search', True)
                
                # 按类型分组搜索条件，根据匹配模式决定同类型条件的连接方式
                conditions_by_type = {}
                
                # 处理从界面传来的搜索条件
                for condition in search_criteria.get('conditions', []):
                    logger.debug(f"处理搜索条件: {condition}")
                    condition_sql = self._build_single_condition(condition, fuzzy_search)
                    logger.debug(f"生成的SQL条件: {condition_sql}")
                    if condition_sql:
                        condition_type = condition.get('type', 'unknown')
                        if condition_type not in conditions_by_type:
                            conditions_by_type[condition_type] = {
                                'conditions': [],
                                'params': []
                            }
                        conditions_by_type[condition_type]['conditions'].append(condition_sql['condition'])
                        conditions_by_type[condition_type]['params'].extend(condition_sql['params'])
                    else:
                        logger.warning(f"条件被跳过（无有效SQL）: {condition}")
                
                logger.debug(f"按类型分组的条件: {conditions_by_type}")
                
                # 构建最终的搜索条件
                search_conditions = []
                final_params = []  # 重新创建参数列表，避免累积问题
                for condition_type, type_data in conditions_by_type.items():
                    if type_data['conditions']:
                        if match_mode == 'all' and condition_type in ['parameter', 'sampler']:
                            # 特殊处理：参数搜索和采样器搜索在AND模式下
                            # 因为多个条件针对的是不同的行，不能用AND连接
                            # 使用OR获取所有候选材质，后处理会验证每个材质是否满足所有条件
                            type_condition = f"({' OR '.join(type_data['conditions'])})"
                        elif match_mode == 'all':
                            # 其他类型（如材质名、着色器）：完全匹配模式使用AND连接
                            type_condition = f"({' AND '.join(type_data['conditions'])})"
                        else:
                            # 模糊匹配模式：同类型条件使用OR连接（任一条件匹配即可）
                            type_condition = f"({' OR '.join(type_data['conditions'])})"
                        
                        search_conditions.append(type_condition)
                        final_params.extend(type_data['params'])
                
                # 根据匹配模式组合不同类型的搜索条件
                if search_conditions:
                    if match_mode == 'all':
                        # 完全匹配模式：跨类型条件也使用AND连接（所有类型都要匹配）
                        conditions.append(f"({' AND '.join(search_conditions)})")
                    else:
                        # 模糊匹配模式：跨类型条件使用OR连接（任一类型匹配即可）
                        conditions.append(f"({' OR '.join(search_conditions)})")
                    
                    # 使用最终参数列表
                    params.extend(final_params)
                else:
                    # 如果没有有效的搜索条件，返回空结果
                    if search_criteria.get('conditions'):
                        logger.warning("搜索条件无效，返回空结果")
                        return []
                
                # 组装最终查询
                if conditions:
                    base_query += " WHERE " + " AND ".join(conditions)
                
                base_query += " ORDER BY m.filename"
                
                logger.debug(f"最终SQL查询: {base_query}")
                logger.debug(f"查询参数: {params}")
                
                cursor.execute(base_query, params)
                results = [dict(row) for row in cursor.fetchall()]
                
                logger.debug(f"SQL查询返回结果数: {len(results)}")
                
                # 对需要后处理的搜索进行精确过滤
                if search_criteria.get('conditions'):
                    results = self._post_process_advanced_search(results, search_criteria['conditions'], match_mode)
                    logger.debug(f"后处理后结果数: {len(results)}")
                
                return results
                
        except sqlite3.Error as e:
            logger.error(f"高级搜索失败: {str(e)}")
            return []

    def _build_search_pattern(self, value: str, fuzzy: bool) -> str:
        """
        构建搜索模式
        
        Args:
            value: 用户输入的搜索值
            fuzzy: 是否启用模糊搜索
            
        Returns:
            SQL LIKE 模式字符串
        """
        if not fuzzy:
            # 精确匹配模式：不添加额外的通配符
            return value
        
        # 模糊搜索模式：检查用户是否已经使用了通配符
        if '*' in value or '%' in value or '_' in value:
            # 用户已使用通配符，将*转换为%（SQL通配符）
            pattern = value.replace('*', '%')
            return pattern
        else:
            # 用户未使用通配符，默认在两端添加%进行包含匹配
            return f"%{value}%"

    def _build_single_condition(self, condition: Dict[str, Any], fuzzy: bool) -> Dict[str, Any]:
        """构建单个搜索条件"""
        search_type = condition.get('type')
        content = condition.get('content', '').strip()
        
        # 检查是否有有效的搜索条件
        has_content = bool(content)
        has_range = bool(condition.get('range'))
        has_sampler_details = bool(condition.get('sampler_details'))
        has_param_value = bool(condition.get('param_value', '').strip())
        
        # 检查采样器指定搜索条件
        has_specific_sampler = (
            condition.get('specific_search') and 
            (bool(condition.get('sampler_type', '').strip()) or bool(condition.get('sampler_path', '').strip()))
        )
        
        # 如果没有任何有效的搜索条件，返回空
        if not (has_content or has_range or has_sampler_details or has_param_value or has_specific_sampler):
            return {}
        
        condition_parts = []
        params = []
        
        if search_type == 'material_name':
            # 材质名称搜索始终使用LIKE进行包含匹配
            condition_parts.append("m.filename LIKE ?")
            params.append(f"%{content}%")
                
        elif search_type == 'shader':
            # 着色器搜索始终使用LIKE进行包含匹配
            condition_parts.append("m.shader_path LIKE ?")
            params.append(f"%{content}%")
                
        elif search_type == 'sampler':
            # 增强的采样器搜索
            sampler_conditions = []
            
            # 检查是否为指定搜索模式
            if condition.get('specific_search'):
                # 指定搜索模式：支持模糊搜索和通配符
                if condition.get('sampler_type') and condition['sampler_type'].strip():
                    type_value = condition['sampler_type'].strip()
                    type_pattern = self._build_search_pattern(type_value, fuzzy)
                    sampler_conditions.append("s.type LIKE ?")
                    params.append(type_pattern)
                
                if condition.get('sampler_path') and condition['sampler_path'].strip():
                    path_value = condition['sampler_path'].strip()
                    path_pattern = self._build_search_pattern(path_value, fuzzy)
                    sampler_conditions.append("s.path LIKE ?")
                    params.append(path_pattern)
            else:
                # 常规搜索模式：在类型和路径中搜索关键词
                if content:
                    content_condition = "(s.type LIKE ? OR s.path LIKE ?)"
                    sampler_conditions.append(content_condition)
                    params.extend([f"%{content}%", f"%{content}%"])
                
                # 兼容旧版本的详细搜索
                if condition.get('sampler_details'):
                    details = condition['sampler_details']
                    
                    # 特定类型搜索
                    if details.get('type') and details['type'].strip():
                        sampler_conditions.append("s.type LIKE ?")
                        params.append(f"%{details['type'].strip()}%")
                    
                    # 特定路径搜索
                    if details.get('path') and details['path'].strip():
                        sampler_conditions.append("s.path LIKE ?")
                        params.append(f"%{details['path'].strip()}%")
            
            if sampler_conditions:
                condition_parts.extend(sampler_conditions)
                    
        elif search_type == 'parameter':
            param_conditions = []
            
            # 参数名称匹配
            if content:
                param_conditions.append("p.name LIKE ?")
                params.append(f"%{content}%")
            
            # 参数值搜索（支持数组值的智能搜索）
            if condition.get('param_value') and condition['param_value'].strip():
                param_value = condition['param_value'].strip()
                array_conditions = self._build_array_value_conditions(param_value)
                if array_conditions:
                    param_conditions.append(array_conditions['condition'])
                    params.extend(array_conditions['params'])
            
            # 数值范围搜索（支持数组值的范围搜索）
            if condition.get('range'):
                range_data = condition['range']
                try:
                    range_conditions = self._build_array_range_conditions(range_data)
                    if range_conditions:
                        param_conditions.append(range_conditions['condition'])
                        params.extend(range_conditions['params'])
                except (ValueError, TypeError):
                    pass
            
            if param_conditions:
                condition_parts.extend(param_conditions)
        
        if condition_parts:
            return {
                'condition': f"({' AND '.join(condition_parts)})",
                'params': params
            }
        
        return {}
    
    def _build_material_name_conditions(self, keywords: List[str], fuzzy: bool) -> Dict[str, Any]:
        """构建材质名称搜索条件"""
        if not keywords:
            return {}
        
        conditions = []
        params = []
        
        for keyword in keywords:
            if fuzzy:
                conditions.append("m.filename LIKE ?")
                params.append(f"%{keyword}%")
            else:
                conditions.append("m.filename = ?")
                params.append(keyword)
        
        return {
            'condition': f"({' OR '.join(conditions)})",
            'params': params
        }
    
    def _build_shader_conditions(self, keywords: List[str], fuzzy: bool) -> Dict[str, Any]:
        """构建着色器搜索条件"""
        if not keywords:
            return {}
        
        conditions = []
        params = []
        
        for keyword in keywords:
            if fuzzy:
                conditions.append("m.shader_path LIKE ?")
                params.append(f"%{keyword}%")
            else:
                conditions.append("m.shader_path = ?")
                params.append(keyword)
        
        return {
            'condition': f"({' OR '.join(conditions)})",
            'params': params
        }
    
    def _build_sampler_conditions(self, samplers: List[Dict[str, str]], fuzzy: bool) -> Dict[str, Any]:
        """构建采样器搜索条件"""
        if not samplers:
            return {}
        
        conditions = []
        params = []
        
        for sampler in samplers:
            sampler_conditions = []
            
            if sampler.get('type'):
                if fuzzy:
                    sampler_conditions.append("s.type LIKE ?")
                    params.append(f"%{sampler['type']}%")
                else:
                    sampler_conditions.append("s.type = ?")
                    params.append(sampler['type'])
            
            if sampler.get('path'):
                if fuzzy:
                    sampler_conditions.append("s.path LIKE ?")
                    params.append(f"%{sampler['path']}%")
                else:
                    sampler_conditions.append("s.path = ?")
                    params.append(sampler['path'])
            
            if sampler_conditions:
                conditions.append(f"({' AND '.join(sampler_conditions)})")
        
        return {
            'condition': f"({' OR '.join(conditions)})",
            'params': params
        } if conditions else {}
    
    def _build_param_conditions(self, params_search: List[Dict[str, Any]], fuzzy: bool) -> Dict[str, Any]:
        """构建参数搜索条件（支持名称和数值范围搜索）"""
        if not params_search:
            return {}
        
        conditions = []
        params = []
        
        for param_search in params_search:
            param_conditions = []
            
            # 参数名称搜索
            if param_search.get('name'):
                if fuzzy:
                    param_conditions.append("p.name LIKE ?")
                    params.append(f"%{param_search['name']}%")
                else:
                    param_conditions.append("p.name = ?")
                    params.append(param_search['name'])
            
            # 参数值搜索
            if param_search.get('value'):
                if fuzzy:
                    param_conditions.append("p.value LIKE ?")
                    params.append(f"%{param_search['value']}%")
                else:
                    param_conditions.append("p.value = ?")
                    params.append(param_search['value'])
            
            # 数值范围搜索
            if param_search.get('min_value') is not None or param_search.get('max_value') is not None:
                try:
                    if param_search.get('min_value') is not None:
                        param_conditions.append("CAST(p.value AS REAL) >= ?")
                        params.append(float(param_search['min_value']))
                    
                    if param_search.get('max_value') is not None:
                        param_conditions.append("CAST(p.value AS REAL) <= ?")
                        params.append(float(param_search['max_value']))
                except (ValueError, TypeError):
                    # 跳过无效的数值
                    pass
            
            if param_conditions:
                conditions.append(f"({' AND '.join(param_conditions)})")
        
        return {
            'condition': f"({' OR '.join(conditions)})",
            'params': params
        } if conditions else {}
    
    def _build_array_value_conditions(self, param_value: str) -> Dict[str, Any]:
        """构建数组参数值搜索条件（支持单个值和多个值的数组匹配）"""
        if not param_value:
            return {}
        
        # 解析参数值：支持逗号分隔的多个值
        param_values = [v.strip() for v in param_value.split(',') if v.strip()]
        if not param_values:
            return {}
        
        logger.debug(f"解析的参数值: {param_values}")
        
        # 无论单个值还是多个值，都只进行基本的预筛选
        # 精确匹配将在后处理中完成
        conditions = []
        params = []
        
        # 只要参数值是数组格式就包含在预筛选中
        conditions.append("p.value LIKE '%[%' AND p.value LIKE '%]%'")
        
        if conditions:
            return {
                'condition': f"({' AND '.join(conditions)})",
                'params': params
            }
        
        return {}
    
    def _build_array_range_conditions(self, range_data: Dict[str, Any]) -> Dict[str, Any]:
        """构建数组参数范围搜索条件（检查数组中是否有值在指定范围内）"""
        if not range_data:
            return {}
        
        conditions = []
        params = []
        
        min_val = range_data.get('min')
        max_val = range_data.get('max')
        
        if min_val is not None or max_val is not None:
            try:
                # 使用正则表达式提取数组中的数值，然后检查范围
                # 由于SQLite的正则表达式支持有限，我们使用更简单的方法
                
                # 如果只有最小值
                if min_val is not None and max_val is None:
                    min_val = float(min_val)
                    # 这个查询比较复杂，我们先使用简单的LIKE匹配作为预筛选
                    # 然后在应用层进行精确的数组范围检查
                    conditions.append("p.value LIKE '%[%'")  # 确保是数组格式
                    
                # 如果只有最大值
                elif max_val is not None and min_val is None:
                    max_val = float(max_val)
                    conditions.append("p.value LIKE '%[%'")  # 确保是数组格式
                    
                # 如果有范围
                elif min_val is not None and max_val is not None:
                    min_val = float(min_val)
                    max_val = float(max_val)
                    conditions.append("p.value LIKE '%[%'")  # 确保是数组格式
                
                # 注意：由于SQLite在处理数组范围搜索上的限制，
                # 这里我们只是预筛选出数组格式的参数
                # 实际的范围检查需要在Python层面进行后处理
                
            except (ValueError, TypeError):
                pass
        
        if conditions:
            return {
                'condition': f"({' AND '.join(conditions)})",
                'params': params
            }
        
        return {}
    
    def get_material_detail(self, material_id: int) -> Optional[Dict[str, Any]]:
        """获取材质详细信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # 获取基本信息
                cursor.execute('''
                    SELECT m.*, l.name as library_name
                    FROM materials m
                    LEFT JOIN material_libraries l ON m.library_id = l.id
                    WHERE m.id = ?
                ''', (material_id,))
                
                material = cursor.fetchone()
                if not material:
                    return None
                
                material_data = dict(material)
                
                # 获取参数
                cursor.execute('''
                    SELECT name, type, value, key_value
                    FROM material_params
                    WHERE material_id = ?
                    ORDER BY sort_order, id
                ''', (material_id,))
                
                params = []
                for param_row in cursor.fetchall():
                    param_dict = dict(param_row)
                    # 解析JSON值
                    try:
                        param_dict['value'] = json.loads(param_dict['value'])
                    except (json.JSONDecodeError, TypeError):
                        pass
                    params.append(param_dict)
                
                material_data['params'] = params
                
                # 获取样例
                cursor.execute('''
                    SELECT type, path, key_value, unk14_x, unk14_y
                    FROM material_samplers
                    WHERE material_id = ?
                    ORDER BY sort_order, id
                ''', (material_id,))
                
                samplers = []
                for sampler_row in cursor.fetchall():
                    sampler_dict = dict(sampler_row)
                    sampler_dict['unk14'] = {
                        'X': sampler_dict.pop('unk14_x'),
                        'Y': sampler_dict.pop('unk14_y')
                    }
                    samplers.append(sampler_dict)
                
                material_data['samplers'] = samplers
                
                return material_data
                
        except sqlite3.Error as e:
            logger.error(f"获取材质详情失败: {str(e)}")
            return None
    
    def update_material(self, material_id: int, material_data: Dict[str, Any]):
        """更新材质信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 更新基本信息
                cursor.execute('''
                    UPDATE materials SET
                        filename = ?, shader_path = ?, source_path = ?, 
                        compression = ?, key_value = ?, updated_time = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (
                    material_data.get('filename', ''),
                    material_data.get('shader_path', ''),
                    material_data.get('source_path', ''),
                    material_data.get('compression', ''),
                    material_data.get('key', ''),
                    material_id
                ))
                
                # 删除旧参数
                cursor.execute("DELETE FROM material_params WHERE material_id = ?", (material_id,))
                
                # 插入新参数
                for param_index, param in enumerate(material_data.get('params', [])):
                    cursor.execute('''
                        INSERT INTO material_params (material_id, name, type, value, key_value, sort_order)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        material_id,
                        param.get('name', ''),
                        param.get('type', ''),
                        json.dumps(param.get('value')),
                        param.get('key', ''),
                        param_index
                    ))
                
                # 删除旧样例
                cursor.execute("DELETE FROM material_samplers WHERE material_id = ?", (material_id,))
                
                # 插入新样例
                for sampler_index, sampler in enumerate(material_data.get('samplers', [])):
                    unk14 = sampler.get('unk14', {})
                    cursor.execute('''
                        INSERT INTO material_samplers (
                            material_id, type, path, key_value, unk14_x, unk14_y, sort_order
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        material_id,
                        sampler.get('type', ''),
                        sampler.get('path', ''),
                        sampler.get('key', ''),
                        unk14.get('X', 0),
                        unk14.get('Y', 0),
                        sampler_index
                    ))
                
                conn.commit()
                logger.info(f"更新材质成功: ID {material_id}")
                
        except sqlite3.Error as e:
            logger.error(f"更新材质失败: {str(e)}")
            raise
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 库数量
                cursor.execute("SELECT COUNT(*) FROM material_libraries")
                library_count = cursor.fetchone()[0]
                
                # 材质数量
                cursor.execute("SELECT COUNT(*) FROM materials")
                material_count = cursor.fetchone()[0]
                
                # 每个库的材质数量
                cursor.execute('''
                    SELECT l.name, COUNT(m.id) as count
                    FROM material_libraries l
                    LEFT JOIN materials m ON l.id = m.library_id
                    GROUP BY l.id, l.name
                    ORDER BY count DESC
                ''')
                
                library_stats = cursor.fetchall()
                
                return {
                    'total_libraries': library_count,
                    'total_materials': material_count,
                    'library_stats': library_stats
                }
                
        except sqlite3.Error as e:
            logger.error(f"获取统计信息失败: {str(e)}")
            return {}
    
    def _post_process_parameter_search(self, results: List[Dict[str, Any]], 
                                     conditions: List[Dict[str, Any]],
                                     match_mode: str = 'any') -> List[Dict[str, Any]]:
        """对参数搜索结果进行后处理，精确过滤数组参数
        
        Args:
            results: SQL查询返回的结果列表
            conditions: 搜索条件列表
            match_mode: 匹配模式 - 'any'(OR逻辑) 或 'all'(AND逻辑)
        """
        if not results or not conditions:
            return results
        
        # 找出需要后处理的参数条件
        param_conditions_need_check = []
        param_conditions_no_check = []
        
        for c in conditions:
            if c.get('type') == 'parameter':
                # 有参数值搜索或范围搜索的需要后处理
                if (c.get('param_value') and c.get('param_value').strip()) or c.get('range'):
                    param_conditions_need_check.append(c)
                else:
                    # 只有参数名称搜索的：在AND模式下也需要后处理
                    if match_mode == 'all':
                        param_conditions_need_check.append(c)
                    else:
                        # OR模式下不需要后处理（SQL已经正确处理）
                        param_conditions_no_check.append(c)
        
        if not param_conditions_need_check:
            # 没有需要后处理的条件，直接返回SQL结果
            return results
        
        logger.debug(f"需要后处理的参数条件: {len(param_conditions_need_check)}，"
                    f"不需要后处理的: {len(param_conditions_no_check)}，"
                    f"匹配模式: {match_mode}")
        
        # 如果是OR模式且有不需要后处理的条件，说明SQL查询已经包含了这些条件
        # 我们只需要对需要后处理的条件进行额外检查
        if match_mode == 'any' and param_conditions_no_check:
            # OR模式：SQL已经正确处理了不需要后处理的条件
            # 后处理只需要验证需要精确匹配的条件
            # 但是SQL返回的结果可能包含：
            # 1. 满足不需要后处理的条件的结果（已经是正确的，应该保留）
            # 2. 满足需要后处理的条件的结果（需要验证是否真正匹配）
            # 
            # 关键问题：我们无法区分哪些结果是因为哪个条件匹配的！
            # 解决方案：在OR模式下，如果有混合条件，只验证需要后处理的条件
            # 对于那些已经被SQL正确匹配的结果，我们无法判断，所以保守策略是：
            # 如果材质满足至少一个需要后处理的条件，就保留
            pass
        
        # 获取所有材质的参数信息进行精确过滤
        filtered_results = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 确保独立的连接设置
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                for result in results:
                    material_id = result['id']
                    
                    # 根据匹配模式决定如何组合多个参数条件
                    if match_mode == 'all':
                        # AND逻辑：所有需要后处理的参数条件都必须满足
                        should_include = True
                        for condition in param_conditions_need_check:
                            if condition.get('param_value') and condition.get('param_value').strip():
                                # 参数值搜索检查
                                if not self._check_material_parameter_array_match(cursor, material_id, condition):
                                    should_include = False
                                    break
                            elif condition.get('range'):
                                # 范围搜索检查
                                if not self._check_material_parameter_range(cursor, material_id, condition):
                                    should_include = False
                                    break
                            elif condition.get('content'):
                                # 只有参数名称的搜索检查
                                if not self._check_material_has_parameter_name(cursor, material_id, condition):
                                    should_include = False
                                    break
                    else:
                        # OR逻辑：任一参数条件满足即可
                        should_include = False
                        
                        # 如果只有需要后处理的条件，那么必须满足其中之一
                        if param_conditions_no_check:
                            # 有不需要后处理的条件：
                            # SQL查询已经用OR连接了所有条件，所以results中的每个材质
                            # 都至少满足一个条件。我们只需要验证：
                            # - 对于需要后处理的条件，是否真正满足
                            # - 如果不满足任何需要后处理的条件，我们假设它满足不需要后处理的条件
                            #   （因为SQL已经筛选过了），所以也保留
                            
                            # 先检查是否满足需要后处理的条件
                            for condition in param_conditions_need_check:
                                if condition.get('param_value') and condition.get('param_value').strip():
                                    if self._check_material_parameter_array_match(cursor, material_id, condition):
                                        should_include = True
                                        break
                                elif condition.get('range'):
                                    if self._check_material_parameter_range(cursor, material_id, condition):
                                        should_include = True
                                        break
                            
                            # 如果不满足任何需要后处理的条件，我们假设它满足SQL处理的条件
                            # （虽然不够严谨，但这是OR逻辑下的合理假设）
                            if not should_include:
                                should_include = True  # 保留，假设满足SQL条件
                        else:
                            # 只有需要后处理的条件：必须满足其中之一
                            for condition in param_conditions_need_check:
                                if condition.get('param_value') and condition.get('param_value').strip():
                                    if self._check_material_parameter_array_match(cursor, material_id, condition):
                                        should_include = True
                                        break
                                elif condition.get('range'):
                                    if self._check_material_parameter_range(cursor, material_id, condition):
                                        should_include = True
                                        break
                    
                    if should_include:
                        filtered_results.append(result)
                        
                logger.debug(f"后处理前结果数: {len(results)}, 后处理后结果数: {len(filtered_results)}")
        
        except sqlite3.Error as e:
            logger.error(f"参数后处理失败: {str(e)}")
            return results
        
        return filtered_results
    
    def _check_material_has_parameter_name(self, cursor, material_id: int, 
                                          condition: Dict[str, Any]) -> bool:
        """检查单个材质是否有指定名称的参数
        
        用于AND模式下验证材质是否包含特定参数名称
        """
        content = condition.get('content', '').strip()
        
        if not content:
            return False
        
        # 查询材质是否有匹配的参数名称
        cursor.execute(
            "SELECT COUNT(*) FROM material_params WHERE material_id = ? AND name LIKE ?",
            (material_id, f"%{content}%")
        )
        count = cursor.fetchone()[0]
        
        logger.debug(f"材质 {material_id} 包含 '{content}' 参数: {count > 0} (找到 {count} 个)")
        return count > 0
    
    def _check_material_parameter_range(self, cursor, material_id: int, 
                                      condition: Dict[str, Any]) -> bool:
        """检查单个材质的参数是否满足范围条件"""
        import re
        import json
        
        content = condition.get('content', '').strip()
        range_data = condition.get('range', {})
        
        # 获取材质的参数
        cursor.execute("SELECT name, value FROM material_params WHERE material_id = ?", (material_id,))
        params = cursor.fetchall()
        
        for param_name, param_value in params:
            # 如果有参数名称过滤，检查是否匹配
            if content and content.lower() not in param_name.lower():
                continue
            
            # 检查是否为数组格式
            if not (param_value.startswith('[') and param_value.endswith(']')):
                continue
            
            try:
                # 解析数组值
                array_values = json.loads(param_value)
                if not isinstance(array_values, list):
                    continue
                
                # 检查数组中是否有值在指定范围内
                min_val = range_data.get('min')
                max_val = range_data.get('max')
                
                for value in array_values:
                    try:
                        numeric_value = float(value)
                        
                        # 检查范围
                        if min_val is not None and numeric_value < float(min_val):
                            continue
                        if max_val is not None and numeric_value > float(max_val):
                            continue
                        
                        # 如果有值在范围内，则匹配成功
                        return True
                        
                    except (ValueError, TypeError):
                        continue
                        
            except (json.JSONDecodeError, ValueError):
                # 如果JSON解析失败，尝试简单的数值提取
                try:
                    # 使用正则表达式提取数值
                    numbers = re.findall(r'-?\d+\.?\d*', param_value)
                    for num_str in numbers:
                        try:
                            numeric_value = float(num_str)
                            
                            # 检查范围
                            if min_val is not None and numeric_value < float(min_val):
                                continue
                            if max_val is not None and numeric_value > float(max_val):
                                continue
                            
                            # 如果有值在范围内，则匹配成功
                            return True
                            
                        except (ValueError, TypeError):
                            continue
                            
                except Exception:
                    continue
        
        return False
    
    def _check_material_parameter_array_match(self, cursor, material_id: int, 
                                            condition: Dict[str, Any]) -> bool:
        """检查单个材质的参数是否满足数组匹配条件（支持精确重复值匹配）"""
        import json
        from collections import Counter
        
        content = condition.get('content', '').strip()
        param_value = condition.get('param_value', '').strip()
        
        # 解析参数值
        target_values = [v.strip() for v in param_value.split(',') if v.strip()]
        if not target_values:
            return False
        
        # 统计目标值的出现次数（支持重复值）
        target_counter = Counter(target_values)
        
        logger.debug(f"检查材质 {material_id} 的数组匹配: {target_values}, 计数: {dict(target_counter)}")
        
        # 获取材质的参数
        cursor.execute("SELECT name, value FROM material_params WHERE material_id = ?", (material_id,))
        params = cursor.fetchall()
        
        for param_name, param_value_str in params:
            # 如果有参数名称过滤，检查是否匹配
            if content and content.lower() not in param_name.lower():
                continue
            
            # 检查是否为数组格式
            if not (param_value_str.startswith('[') and param_value_str.endswith(']')):
                continue
            
            try:
                # 解析数组值
                array_values = json.loads(param_value_str)
                if not isinstance(array_values, list):
                    continue
                
                logger.debug(f"检查参数 {param_name}: {array_values}")
                
                if len(target_values) == 1:
                    # 单个值搜索：检查数组中是否包含该值
                    target_value = target_values[0]
                    
                    # 尝试数值匹配
                    try:
                        target_numeric = float(target_value)
                        for array_value in array_values:
                            try:
                                array_numeric = float(array_value)
                                if abs(target_numeric - array_numeric) < 1e-6:  # 浮点数精度容错
                                    logger.debug(f"单值匹配成功: {target_value} 在 {array_values}")
                                    return True
                            except (ValueError, TypeError):
                                continue
                    except (ValueError, TypeError):
                        # 字符串匹配
                        target_str = str(target_value)
                        for array_value in array_values:
                            if str(array_value) == target_str:
                                logger.debug(f"单值字符串匹配成功: {target_value} 在 {array_values}")
                                return True
                
                else:
                    # 多个值搜索：检查数组是否包含所有目标值（包括重复值）
                    # 将数组值转换为字符串并统计
                    array_counter = Counter()
                    
                    for array_value in array_values:
                        # 尝试数值标准化
                        try:
                            numeric_value = float(array_value)
                            # 检查是否为整数
                            if numeric_value.is_integer():
                                normalized_value = str(int(numeric_value))
                            else:
                                normalized_value = str(numeric_value)
                            array_counter[normalized_value] += 1
                        except (ValueError, TypeError):
                            # 非数值，直接使用字符串
                            array_counter[str(array_value)] += 1
                    
                    # 标准化目标值
                    normalized_target_counter = Counter()
                    for target_value in target_values:
                        try:
                            numeric_value = float(target_value)
                            if numeric_value.is_integer():
                                normalized_value = str(int(numeric_value))
                            else:
                                normalized_value = str(numeric_value)
                            normalized_target_counter[normalized_value] += 1
                        except (ValueError, TypeError):
                            normalized_target_counter[str(target_value)] += 1
                    
                    logger.debug(f"数组计数: {dict(array_counter)}")
                    logger.debug(f"目标计数: {dict(normalized_target_counter)}")
                    
                    # 检查数组是否包含足够数量的每个目标值
                    match = True
                    for target_val, required_count in normalized_target_counter.items():
                        if array_counter.get(target_val, 0) < required_count:
                            match = False
                            break
                    
                    if match:
                        logger.debug(f"多值匹配成功: {target_values} 在 {array_values}")
                        return True
                    
            except (json.JSONDecodeError, ValueError) as e:
                logger.debug(f"JSON解析失败: {e}, 尝试字符串匹配")
                # 如果JSON解析失败，尝试简单的字符串匹配
                try:
                    if len(target_values) == 1:
                        # 单值字符串匹配
                        if target_values[0] in param_value_str:
                            return True
                    else:
                        # 多值字符串匹配：所有值都必须在参数值中出现
                        all_found = all(target_value in param_value_str for target_value in target_values)
                        if all_found:
                            return True
                except Exception:
                    continue
        
        return False
    
    def _post_process_advanced_search(self, results: List[Dict[str, Any]], 
                                    conditions: List[Dict[str, Any]],
                                    match_mode: str = 'any') -> List[Dict[str, Any]]:
        """对高级搜索结果进行后处理，精确过滤参数和采样器条件
        
        Args:
            results: SQL查询返回的结果列表
            conditions: 搜索条件列表
            match_mode: 匹配模式 - 'any'(OR逻辑) 或 'all'(AND逻辑)
        """
        if not results or not conditions:
            return results
        
        # 找出需要后处理的条件
        conditions_need_check = []
        
        for c in conditions:
            condition_type = c.get('type')
            
            if condition_type == 'parameter':
                # 参数搜索：有参数值搜索或范围搜索的需要后处理
                if (c.get('param_value') and c.get('param_value').strip()) or c.get('range'):
                    conditions_need_check.append(c)
                elif match_mode == 'all':
                    # AND模式下，只有参数名称搜索的也需要后处理
                    conditions_need_check.append(c)
            
            elif condition_type == 'sampler' and match_mode == 'all':
                # 采样器搜索：在AND模式下，多个采样器条件需要后处理
                conditions_need_check.append(c)
        
        if not conditions_need_check:
            # 没有需要后处理的条件，直接返回SQL结果
            return results
        
        logger.debug(f"需要后处理的条件数: {len(conditions_need_check)}，匹配模式: {match_mode}")
        
        # 获取所有材质的详细信息进行精确过滤
        filtered_results = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                for result in results:
                    material_id = result['id']
                    
                    # 根据匹配模式决定如何组合多个条件
                    if match_mode == 'all':
                        # AND逻辑：所有条件都必须满足
                        should_include = True
                        for condition in conditions_need_check:
                            if condition.get('type') == 'parameter':
                                if not self._check_material_parameter_condition(cursor, material_id, condition):
                                    should_include = False
                                    break
                            elif condition.get('type') == 'sampler':
                                if not self._check_material_sampler_condition(cursor, material_id, condition):
                                    should_include = False
                                    break
                        
                        if should_include:
                            filtered_results.append(result)
                    else:
                        # OR逻辑：至少一个条件满足即可
                        should_include = False
                        for condition in conditions_need_check:
                            if condition.get('type') == 'parameter':
                                if self._check_material_parameter_condition(cursor, material_id, condition):
                                    should_include = True
                                    break
                            elif condition.get('type') == 'sampler':
                                if self._check_material_sampler_condition(cursor, material_id, condition):
                                    should_include = True
                                    break
                        
                        if should_include:
                            filtered_results.append(result)
        
        except sqlite3.Error as e:
            logger.error(f"后处理时数据库错误: {e}")
            return results  # 如果后处理失败，返回原结果
        
        logger.debug(f"后处理前结果数: {len(results)}, 后处理后结果数: {len(filtered_results)}")
        return filtered_results
    
    def _check_material_parameter_condition(self, cursor, material_id: int, condition: Dict[str, Any]) -> bool:
        """检查材质是否满足参数条件"""
        content = condition.get('content', '').strip()
        param_value = condition.get('param_value', '').strip()
        range_data = condition.get('range')
        
        # 参数名称检查
        if content and not self._check_material_has_parameter_name(cursor, material_id, condition):
            return False
        
        # 参数值检查
        if param_value and not self._check_material_parameter_array_match(cursor, material_id, content, param_value):
            return False
        
        # 范围检查
        if range_data and not self._check_material_parameter_range(cursor, material_id, condition):
            return False
        
        return True
    
    def _check_material_sampler_condition(self, cursor, material_id: int, condition: Dict[str, Any]) -> bool:
        """检查材质是否满足采样器条件"""
        content = condition.get('content', '').strip()
        specific_search = condition.get('specific_search', False)
        sampler_type = condition.get('sampler_type', '').strip()
        sampler_path = condition.get('sampler_path', '').strip()
        
        # 查询材质的采样器信息
        cursor.execute("""
            SELECT type, path 
            FROM material_samplers 
            WHERE material_id = ?
        """, (material_id,))
        
        samplers = cursor.fetchall()
        if not samplers:
            return False
        
        # 检查采样器条件
        for sampler in samplers:
            s_type = sampler[0] or ''
            s_path = sampler[1] or ''
            
            if specific_search:
                # 指定搜索模式
                type_match = True
                path_match = True
                
                if sampler_type:
                    # 使用我们的模糊搜索模式
                    pattern = self._build_search_pattern(sampler_type, True)
                    if pattern.startswith('%') and pattern.endswith('%'):
                        # 包含匹配
                        type_match = sampler_type.replace('%', '').lower() in s_type.lower()
                    elif pattern.endswith('%'):
                        # 前缀匹配
                        type_match = s_type.lower().startswith(sampler_type.replace('%', '').lower())
                    elif pattern.startswith('%'):
                        # 后缀匹配
                        type_match = s_type.lower().endswith(sampler_type.replace('%', '').lower())
                    else:
                        # 精确匹配
                        type_match = s_type.lower() == sampler_type.lower()
                
                if sampler_path:
                    # 使用我们的模糊搜索模式
                    pattern = self._build_search_pattern(sampler_path, True)
                    if pattern.startswith('%') and pattern.endswith('%'):
                        # 包含匹配
                        path_match = sampler_path.replace('%', '').lower() in s_path.lower()
                    elif pattern.endswith('%'):
                        # 前缀匹配
                        path_match = s_path.lower().startswith(sampler_path.replace('%', '').lower())
                    elif pattern.startswith('%'):
                        # 后缀匹配
                        path_match = s_path.lower().endswith(sampler_path.replace('%', '').lower())
                    else:
                        # 精确匹配
                        path_match = s_path.lower() == sampler_path.lower()
                
                if type_match and path_match:
                    return True
            else:
                # 常规搜索模式：在类型和路径中搜索关键词
                if content:
                    if content.lower() in s_type.lower() or content.lower() in s_path.lower():
                        return True
        
        return False
    
    def search_materials_by_name(self, material_name: str, library_id: int = None) -> List[Dict[str, Any]]:
        """根据材质名称搜索材质"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if library_id:
                    query = '''
                        SELECT m.*, ml.name as library_name 
                        FROM materials m 
                        LEFT JOIN material_libraries ml ON m.library_id = ml.id 
                        WHERE m.filename LIKE ? AND m.library_id = ?
                        ORDER BY m.filename
                    '''
                    cursor.execute(query, (f'%{material_name}%', library_id))
                else:
                    query = '''
                        SELECT m.*, ml.name as library_name 
                        FROM materials m 
                        LEFT JOIN material_libraries ml ON m.library_id = ml.id 
                        WHERE m.filename LIKE ?
                        ORDER BY m.filename
                    '''
                    cursor.execute(query, (f'%{material_name}%',))
                
                columns = [description[0] for description in cursor.description]
                results = []
                for row in cursor.fetchall():
                    material = dict(zip(columns, row))
                    results.append(material)
                
                return results
                
        except sqlite3.Error as e:
            logger.error(f"搜索材质时发生数据库错误: {e}")
            return []
        except Exception as e:
            logger.error(f"搜索材质时发生错误: {e}")
            return []
    
    def get_material_by_id(self, material_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取单个材质"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT m.*, ml.name as library_name 
                    FROM materials m 
                    LEFT JOIN material_libraries ml ON m.library_id = ml.id 
                    WHERE m.id = ?
                '''
                cursor.execute(query, (material_id,))
                
                row = cursor.fetchone()
                if row:
                    columns = [description[0] for description in cursor.description]
                    return dict(zip(columns, row))
                
                return None
                
        except sqlite3.Error as e:
            logger.error(f"获取材质时发生数据库错误: {e}")
            return None
        except Exception as e:
            logger.error(f"获取材质时发生错误: {e}")
            return None
    
    def get_materials_by_library(self, library_id: int) -> List[Dict[str, Any]]:
        """获取指定库中的所有材质"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT m.*, ml.name as library_name 
                    FROM materials m 
                    LEFT JOIN material_libraries ml ON m.library_id = ml.id 
                    WHERE m.library_id = ?
                    ORDER BY m.file_name
                '''
                cursor.execute(query, (library_id,))
                
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                
                materials = []
                for row in rows:
                    material = dict(zip(columns, row))
                    # 添加material的name字段，用于匹配算法
                    material['name'] = material.get('file_name', '')
                    materials.append(material)
                
                return materials
                
        except sqlite3.Error as e:
            logger.error(f"获取库材质时发生数据库错误: {e}")
            return []
        except Exception as e:
            logger.error(f"获取库材质时发生错误: {e}")
            return []
    
    def get_samplers(self, material_id: int) -> List[Dict[str, Any]]:
        """获取材质的采样器信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT * FROM material_samplers 
                    WHERE material_id = ?
                    ORDER BY sort_order, id
                '''
                cursor.execute(query, (material_id,))
                
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                
                return [dict(zip(columns, row)) for row in rows]
                
        except sqlite3.Error as e:
            logger.error(f"获取采样器时发生数据库错误: {e}")
            return []
        except Exception as e:
            logger.error(f"获取采样器时发生错误: {e}")
            return []
    
    def get_parameters(self, material_id: int) -> List[Dict[str, Any]]:
        """获取材质的参数信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT * FROM material_params 
                    WHERE material_id = ?
                    ORDER BY sort_order, id
                '''
                cursor.execute(query, (material_id,))
                
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                
                return [dict(zip(columns, row)) for row in rows]
                
        except sqlite3.Error as e:
            logger.error(f"获取参数时发生数据库错误: {e}")
            return []
        except Exception as e:
            logger.error(f"获取参数时发生错误: {e}")
            return []
    
    def search_material_by_path(self, path_pattern: str, library_id: int = None) -> List[Dict[str, Any]]:
        """
        按材质路径模糊搜索（支持MTD路径和纹理路径）
        
        按设计文档8.1实现：
        - 支持搜索材质MTD路径
        - 支持搜索采样器纹理路径
        - 路径归一化处理
        
        Args:
            path_pattern: 路径模式（支持文件名或完整路径）
            library_id: 材质库ID，None表示搜索所有库
            
        Returns:
            匹配的材质列表
        """
        try:
            # 路径标准化并提取文件名
            normalized = path_pattern.replace('\\\\', '\\').replace('/', '\\')
            filename = normalized.split('\\')[-1]
            
            # 去掉.matxml后缀（如果有）
            if filename.lower().endswith('.matxml'):
                filename = filename[:-7]
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 构建查询：同时搜索材质MTD路径和采样器纹理路径
                if library_id:
                    query = '''
                        SELECT DISTINCT m.*, ml.name as library_name 
                        FROM materials m 
                        LEFT JOIN material_libraries ml ON m.library_id = ml.id 
                        LEFT JOIN material_samplers s ON m.id = s.material_id
                        WHERE (m.shader_path LIKE ? OR m.filename LIKE ? OR s.path LIKE ?)
                          AND m.library_id = ?
                        ORDER BY m.filename
                    '''
                    search_param = f'%{filename}%'
                    cursor.execute(query, (search_param, search_param, search_param, library_id))
                else:
                    query = '''
                        SELECT DISTINCT m.*, ml.name as library_name 
                        FROM materials m 
                        LEFT JOIN material_libraries ml ON m.library_id = ml.id 
                        LEFT JOIN material_samplers s ON m.id = s.material_id
                        WHERE (m.shader_path LIKE ? OR m.filename LIKE ? OR s.path LIKE ?)
                        ORDER BY m.filename
                    '''
                    search_param = f'%{filename}%'
                    cursor.execute(query, (search_param, search_param, search_param))
                
                columns = [description[0] for description in cursor.description]
                results = []
                for row in cursor.fetchall():
                    material = dict(zip(columns, row))
                    results.append(material)
                
                return results
                
        except sqlite3.Error as e:
            logger.error(f"按路径搜索材质时发生数据库错误: {e}")
            return []
        except Exception as e:
            logger.error(f"按路径搜索材质时发生错误: {e}")
            return []
    
    def auto_match_material(self, mtd_path: str) -> Dict[str, Any]:
        """
        自动匹配材质，返回匹配结果和所在库
        
        按设计文档8.2实现：
        - 自动查找匹配的材质
        - 返回是否需要用户确认
        
        Args:
            mtd_path: 材质MTD路径
            
        Returns:
            匹配结果字典，包含：
            - matched: 是否找到匹配
            - material: 匹配的材质（如果有）
            - library_id: 所属库ID
            - needs_confirm: 是否需要用户确认（多个结果时）
            - alternatives: 其他候选材质（如果有多个匹配）
        """
        results = self.search_material_by_path(mtd_path)
        
        if len(results) == 1:
            return {
                'matched': True,
                'material': results[0],
                'library_id': results[0].get('library_id'),
                'needs_confirm': False,
                'alternatives': []
            }
        elif len(results) > 1:
            return {
                'matched': True,
                'material': results[0],
                'library_id': results[0].get('library_id'),
                'needs_confirm': True,
                'alternatives': results[1:]
            }
        else:
            return {
                'matched': False,
                'material': None,
                'library_id': None,
                'needs_confirm': True,
                'alternatives': []
            }
    
    def close(self):
        """关闭数据库连接"""
        pass