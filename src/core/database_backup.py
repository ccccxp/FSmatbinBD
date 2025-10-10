#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
鏁版嵁搴撴搷浣滄ā鍧?- 鐢ㄤ簬绠＄悊鏉愯川搴撴暟鎹紙閲嶆瀯鐗堬級
"""

import sqlite3
import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

# 閰嶇疆鏃ュ織
logger = logging.getLogger(__name__)

class MaterialDatabase:
    """鏉愯川鏁版嵁搴撶鐞嗙被"""
    
    def __init__(self, db_path: str = "data/databases/materials.db"):
        """
        鍒濆鍖栨暟鎹簱杩炴帴
        
        Args:
            db_path: 鏁版嵁搴撴枃浠惰矾寰?
        """
        self.db_path = db_path
        
        # 纭繚鏁版嵁搴撶洰褰曞瓨鍦?
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # 鍒濆鍖栨暟鎹簱
        self._init_database()
    
    def _init_database(self):
        """鍒濆鍖栨暟鎹簱琛ㄧ粨鏋?""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 创建材质搴撹〃
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
                        FOREIGN KEY (material_id) REFERENCES materials (id)
                    )
                ''')
                
                # 创建索引
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_materials_library ON materials(library_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_materials_name ON materials(filename)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_params_material ON material_params(material_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_samplers_material ON material_samplers(material_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_samplers_type ON material_samplers(type)')
                
                conn.commit()
                logger.info("鏁版嵁搴撳垵濮嬪寲瀹屾垚")
                
        except sqlite3.Error as e:
            logger.error(f"鏁版嵁搴撳垵濮嬪寲失败: {str(e)}")
            raise
    
    def create_library(self, name: str, description: str = "", source_path: str = "") -> int:
        # Create new material library
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO material_libraries (name, description, source_path)
                    VALUES (?, ?, ?)
                ''', (name, description, source_path))
                
                library_id = cursor.lastrowid
                conn.commit()
                logger.info(f"创建材质搴撴垚鍔? {name} (ID: {library_id})")
                return library_id
                
        except sqlite3.IntegrityError:
            logger.error(f"鏉愯川搴撳悕绉板凡瀛樺湪: {name}")
            raise ValueError(f"鏉愯川搴撳悕绉?'{name}' 宸插瓨鍦?)
        except sqlite3.Error as e:
            logger.error(f"创建材质搴撳け璐? {str(e)}")
            raise
    
    def add_library(self, name: str, source_path: str = "", description: str = "") -> int:
        # Add new material library (alias for create_library for compatibility)
        return self.create_library(name, description, source_path)
    
    def get_libraries(self) -> List[Dict[str, Any]]:
        # Get all material libraries
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, name, description, source_path, created_time, updated_time
                    FROM material_libraries
                    ORDER BY created_time DESC
                ''')
                
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            logger.error(f"鑾峰彇鏉愯川搴撳け璐? {str(e)}")
            return []
    
    def update_library(self, library_id: int, name: str = None, description: str = None):
        """鏇存柊鏉愯川搴撲俊鎭?""
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
                
                if updates:
                    updates.append("updated_time = CURRENT_TIMESTAMP")
                    params.append(library_id)
                    
                    query = f"UPDATE material_libraries SET {', '.join(updates)} WHERE id = ?"
                    cursor.execute(query, params)
                    conn.commit()
                    logger.info(f"鏇存柊鏉愯川搴撴垚鍔? ID {library_id}")
                
        except sqlite3.Error as e:
            logger.error(f"鏇存柊鏉愯川搴撳け璐? {str(e)}")
            raise
    
    def delete_library(self, library_id: int):
        """删除材质搴撳強鍏舵墍鏈夋潗璐?""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 鑾峰彇搴撲腑鎵鏈夋潗璐↖D
                cursor.execute("SELECT id FROM materials WHERE library_id = ?", (library_id,))
                material_ids = [row[0] for row in cursor.fetchall()]
                
                # 删除材质鐨勫弬鏁板拰样例
                for material_id in material_ids:
                    cursor.execute("DELETE FROM material_params WHERE material_id = ?", (material_id,))
                    cursor.execute("DELETE FROM material_samplers WHERE material_id = ?", (material_id,))
                
                # 删除材质
                cursor.execute("DELETE FROM materials WHERE library_id = ?", (library_id,))
                
                # 删除材质库
                cursor.execute("DELETE FROM material_libraries WHERE id = ?", (library_id,))
                
                conn.commit()
                logger.info(f"删除材质搴撴垚鍔? ID {library_id}")
                
        except sqlite3.Error as e:
            logger.error(f"删除材质搴撳け璐? {str(e)}")
            raise
    
    def add_materials(self, library_id: int, materials_data: List[Dict[str, Any]]):
        """鎵归噺娣诲姞鏉愯川鍒版寚瀹氬簱"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for material_data in materials_data:
                    # 鎻掑叆鏉愯川鍩烘湰淇伅
                    cursor.execute('''
                        INSERT INTO materials (
                            library_id, file_path, file_name, filename, 
                            shader_path, source_path, compression, key_value
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
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
                    
                    # 鎻掑叆参数
                    for param in material_data.get('params', []):
                        cursor.execute('''
                            INSERT INTO material_params (material_id, name, type, value, key_value)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (
                            material_id,
                            param.get('name', ''),
                            param.get('type', ''),
                            json.dumps(param.get('value')),
                            param.get('key', '')
                        ))
                    
                    # 鎻掑叆样例
                    for sampler in material_data.get('samplers', []):
                        unk14 = sampler.get('unk14', {})
                        cursor.execute('''
                            INSERT INTO material_samplers (
                                material_id, type, path, key_value, unk14_x, unk14_y
                            ) VALUES (?, ?, ?, ?, ?, ?)
                        ''', (
                            material_id,
                            sampler.get('type', ''),
                            sampler.get('path', ''),
                            sampler.get('key', ''),
                            unk14.get('X', 0),
                            unk14.get('Y', 0)
                        ))
                
                conn.commit()
                logger.info(f"成功娣诲姞 {len(materials_data)} 涓潗璐ㄥ埌搴?{library_id}")
                
        except sqlite3.Error as e:
            logger.error(f"娣诲姞鏉愯川失败: {str(e)}")
            raise
    
    def add_material(self, material_data: Dict[str, Any], library_id: int):
        """娣诲姞鍗曚釜鏉愯川鍒版寚瀹氬簱"""
        self.add_materials(library_id, [material_data])
    
    def search_materials(self, library_id: int = None, keyword: str = "", 
                        material_type: str = "", material_path: str = "") -> List[Dict[str, Any]]:
        """鎼滅储鏉愯川"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # 鏋勫缓鍩虹鏌ヨ
                base_query = '''
                    SELECT DISTINCT m.id, m.library_id, m.file_path, m.file_name, 
                           m.filename, m.shader_path, m.source_path, m.compression, 
                           m.key_value, m.created_time, l.name as library_name
                    FROM materials m
                    LEFT JOIN material_libraries l ON m.library_id = l.id
                '''
                
                conditions = []
                params = []
                
                # 娣诲姞搴揑D鏉′欢
                if library_id is not None:
                    conditions.append("m.library_id = ?")
                    params.append(library_id)
                
                # 娣诲姞鍏抽敭瀛楁潯浠?
                if keyword:
                    conditions.append("(m.filename LIKE ? OR m.file_name LIKE ?)")
                    params.extend([f"%{keyword}%", f"%{keyword}%"])
                
                # 娣诲姞鏉愯川绫诲瀷鍜岃矾寰勬潯浠讹紙闇瑕佸叧鑱攕amplers琛級
                if material_type or material_path:
                    base_query += " LEFT JOIN material_samplers s ON m.id = s.material_id"
                    
                    if material_type:
                        conditions.append("s.type LIKE ?")
                        params.append(f"%{material_type}%")
                    
                    if material_path:
                        conditions.append("s.path LIKE ?")
                        params.append(f"%{material_path}%")
                
                # 缁勮鏈缁堟煡璇?
                if conditions:
                    base_query += " WHERE " + " AND ".join(conditions)
                
                base_query += " ORDER BY m.filename"
                
                cursor.execute(base_query, params)
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            logger.error(f"鎼滅储鏉愯川失败: {str(e)}")
            return []
    
    def search_materials_extended(self, library_id: int = None, keyword: str = "") -> List[Dict[str, Any]]:
        """鎵睍鎼滅储鏉愯川锛堟敮鎸佹潗璐ㄥ悕绉般佺潃鑹插櫒鍚嶇О銆佹牱渚嬪悕绉帮級"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # 鏋勫缓鏌ヨ
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
                
                # 娣诲姞搴揑D鏉′欢
                if library_id is not None:
                    conditions.append("m.library_id = ?")
                    params.append(library_id)
                
                # 娣诲姞鍏抽敭瀛楁悳绱㈡潯浠讹紙鏉愯川鍚嶇О銆佺潃鑹插櫒璺緞銆佹牱渚嬬被鍨嬶級
                if keyword:
                    search_conditions = [
                        "m.filename LIKE ?",
                        "m.shader_path LIKE ?", 
                        "s.type LIKE ?"
                    ]
                    conditions.append(f"({' OR '.join(search_conditions)})")
                    keyword_param = f"%{keyword}%"
                    params.extend([keyword_param, keyword_param, keyword_param])
                
                # 缁勮鏈缁堟煡璇?
                if conditions:
                    base_query += " WHERE " + " AND ".join(conditions)
                
                base_query += " ORDER BY m.filename"
                
                cursor.execute(base_query, params)
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            logger.error(f"鎵睍鎼滅储鏉愯川失败: {str(e)}")
            return []
    
    def get_material_detail(self, material_id: int) -> Optional[Dict[str, Any]]:
        """鑾峰彇鏉愯川璇粏淇伅"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # 鑾峰彇鍩烘湰淇伅
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
                # 鏄犲皠鏉愯川鏍筴ey_value瀛楁涓簁ey锛堝吋瀹筙ML鏍煎紡锛?
                if 'key_value' in material_data:
                    material_data['key'] = material_data.pop('key_value')
                
                # 鑾峰彇参数锛堟寜ID椤哄簭锛屼繚鎸佸師濮嬮『搴忥級
                cursor.execute('''
                    SELECT name, type, value, key_value
                    FROM material_params
                    WHERE material_id = ?
                    ORDER BY id
                ''', (material_id,))
                
                params = []
                for param_row in cursor.fetchall():
                    param_dict = dict(param_row)
                    # 鏄犲皠key_value瀛楁涓簁ey锛堝吋瀹筙ML鏍煎紡锛?
                    param_dict['key'] = param_dict.pop('key_value', '')
                    
                    # 瑙ｆ瀽JSON鍊?
                    try:
                        param_dict['value'] = json.loads(param_dict['value'])
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(f"JSON瑙ｆ瀽失败 - 参数鍚? {param_dict['name']}, 鍘熷鍊? {repr(param_dict['value'])}, 閿欒: {e}")
                        # 淇濇寔鍘熷鍊间笉鍙?
                    params.append(param_dict)
                
                material_data['params'] = params
                
                # 鑾峰彇样例锛堟寜ID椤哄簭锛屼繚鎸佸師濮嬮『搴忥級
                cursor.execute('''
                    SELECT type, path, key_value, unk14_x, unk14_y
                    FROM material_samplers
                    WHERE material_id = ?
                    ORDER BY id
                ''', (material_id,))
                
                samplers = []
                for sampler_row in cursor.fetchall():
                    sampler_dict = dict(sampler_row)
                    # 鏄犲皠key_value瀛楁涓簁ey锛堝吋瀹筙ML鏍煎紡锛?
                    sampler_dict['key'] = sampler_dict.pop('key_value', '')
                    sampler_dict['unk14'] = {
                        'X': sampler_dict.pop('unk14_x'),
                        'Y': sampler_dict.pop('unk14_y')
                    }
                    samplers.append(sampler_dict)
                
                material_data['samplers'] = samplers
                
                return material_data
                
        except sqlite3.Error as e:
            logger.error(f"鑾峰彇鏉愯川璇︽儏失败: {str(e)}")
            return None
    
    def update_material(self, material_id: int, material_data: Dict[str, Any]):
        """鏇存柊鏉愯川淇伅"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 鏇存柊鍩烘湰淇伅
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
                
                # 鍒犻櫎鏃у弬鏁?
                cursor.execute("DELETE FROM material_params WHERE material_id = ?", (material_id,))
                
                # 鎻掑叆鏂板弬鏁?
                for param in material_data.get('params', []):
                    cursor.execute('''
                        INSERT INTO material_params (material_id, name, type, value, key_value)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        material_id,
                        param.get('name', ''),
                        param.get('type', ''),
                        json.dumps(param.get('value')),
                        param.get('key', '')
                    ))
                
                # 钒犻櫎鏃ф牱渚?
                cursor.execute("DELETE FROM material_samplers WHERE material_id = ?", (material_id,))
                
                # 鎻掑叆鏂版牱渚?
                for sampler in material_data.get('samplers', []):
                    unk14 = sampler.get('unk14', {})
                    cursor.execute('''
                        INSERT INTO material_samplers (
                            material_id, type, path, key_value, unk14_x, unk14_y
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        material_id,
                        sampler.get('type', ''),
                        sampler.get('path', ''),
                        sampler.get('key', ''),
                        unk14.get('X', 0),
                        unk14.get('Y', 0)
                    ))
                
                conn.commit()
                logger.info(f"鏇存柊鏉愯川成功: ID {material_id}")
                
        except sqlite3.Error as e:
            logger.error(f"鏇存柊鏉愯川失败: {str(e)}")
            raise
    
    def get_statistics(self) -> Dict[str, Any]:
        """鑾峰彇鏁版嵁搴撶粺璁′俊鎭?""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 搴撴暟閲?
                cursor.execute("SELECT COUNT(*) FROM material_libraries")
                library_count = cursor.fetchone()[0]
                
                # 鏉愯川鏁伴噺
                cursor.execute("SELECT COUNT(*) FROM materials")
                material_count = cursor.fetchone()[0]
                
                # 姣忎釜搴撶殑鏉愯川鏁伴噺
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
            logger.error(f"鑾峰彇缁熻淇伅失败: {str(e)}")
            return {}
    
    def close(self):
        """鍏抽棴鏁版嵁搴撹繛鎺?""
        pass
    
    def get_material_count(self, library_id: int) -> int:
        """鑾峰彇鎸囧畾搴撲腑鐨勬潗璐ㄦ暟閲?""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM materials WHERE library_id = ?", (library_id,))
                result = cursor.fetchone()
                return result[0] if result else 0
        except sqlite3.Error as e:
            logger.error(f"鑾峰彇鏉愯川鏁伴噺失败: {str(e)}")
            return 0
    
    def get_library_by_id(self, library_id: int) -> Optional[Dict[str, Any]]:
        """鏍规嵁ID鑾峰彇搴撲俊鎭?""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM material_libraries WHERE id = ?", (library_id,))
                row = cursor.fetchone()
                
                if row:
                    return {
                        'id': row[0],
                        'name': row[1],
                        'description': row[2],
                        'path': row[3],  # source_path
                        'created_time': row[4],
                        'updated_time': row[5]
                    }
                return None
        except sqlite3.Error as e:
            logger.error(f"鑾峰彇搴撲俊鎭け璐? {str(e)}")
            return None
    
    def clear_library_materials(self, library_id: int):
        """娓呯┖鎸囧畾搴撲腑鐨勬墍鏈夋潗璐?""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM materials WHERE library_id = ?", (library_id,))
                conn.commit()
                logger.info(f"宸叉竻绌哄簱 {library_id} 涓殑鎵鏈夋潗璐?)
        except sqlite3.Error as e:
            logger.error(f"娓呯┖搴撴潗璐ㄥけ璐? {str(e)}")
            raise
    
    def delete_library(self, library_id: int):
        """鍒犻櫎搴撳強鍏舵墍鏈夋潗璐?""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # 鍏堝垹闄ゆ潗璐?
                cursor.execute("DELETE FROM materials WHERE library_id = ?", (library_id,))
                # 鍐嶅垹闄ゅ簱
                cursor.execute("DELETE FROM material_libraries WHERE id = ?", (library_id,))
                conn.commit()
                logger.info(f"宸插垹闄ゅ簱 {library_id}")
        except sqlite3.Error as e:
            logger.error(f"鍒犻櫎搴撳け璐? {str(e)}")
            raise
    
    def advanced_search(self, library_id, search_params):
        """高级搜索材质"""
        try:
            match_mode = search_params.get('match_mode', 'all')
            conditions = search_params.get('conditions', [])
            
            if not conditions:
                return []
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                if library_id:
                    cursor.execute("SELECT * FROM materials WHERE library_id = ?", (library_id,))
                else:
                    cursor.execute("SELECT * FROM materials")
                
                all_materials = [dict(row) for row in cursor.fetchall()]
                matched_materials = []
                
                for material in all_materials:
                    mat_match_count = 0
                    for condition in conditions:
                        if self._check_condition(cursor, material, condition):
                            mat_match_count += 1
                    
                    if match_mode == 'all':
                        if mat_match_count == len(conditions):
                            self._add_material_full_details(cursor, material)
                            matched_materials.append(material)
                    else:
                        if mat_match_count > 0:
                            self._add_material_full_details(cursor, material)
                            matched_materials.append(material)
                
                return matched_materials
        except Exception as e:
            logger.error(f"高级搜索失败: {str(e)}")
            return []
