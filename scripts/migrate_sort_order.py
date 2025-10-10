#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本 - 添加sort_order字段确保数据顺序一致性
"""

import sqlite3
import os
import sys

# 添加src目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def migrate_database(db_path="data/databases/materials.db"):
    """迁移数据库，添加sort_order字段"""
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # 检查material_params表是否已有sort_order字段
            cursor.execute("PRAGMA table_info(material_params)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'sort_order' not in columns:
                print("为material_params表添加sort_order字段...")
                cursor.execute("ALTER TABLE material_params ADD COLUMN sort_order INTEGER DEFAULT 0")
                
                # 为现有数据设置顺序（按id排序，保持插入顺序）
                cursor.execute("""
                    UPDATE material_params 
                    SET sort_order = (
                        SELECT COUNT(*) 
                        FROM material_params p2 
                        WHERE p2.material_id = material_params.material_id 
                        AND p2.id <= material_params.id
                    ) - 1
                """)
                print("material_params表sort_order字段添加完成")
            else:
                print("material_params表已有sort_order字段")
            
            # 检查material_samplers表是否已有sort_order字段
            cursor.execute("PRAGMA table_info(material_samplers)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'sort_order' not in columns:
                print("为material_samplers表添加sort_order字段...")
                cursor.execute("ALTER TABLE material_samplers ADD COLUMN sort_order INTEGER DEFAULT 0")
                
                # 为现有数据设置顺序（按id排序，保持插入顺序）
                cursor.execute("""
                    UPDATE material_samplers 
                    SET sort_order = (
                        SELECT COUNT(*) 
                        FROM material_samplers s2 
                        WHERE s2.material_id = material_samplers.material_id 
                        AND s2.id <= material_samplers.id
                    ) - 1
                """)
                print("material_samplers表sort_order字段添加完成")
            else:
                print("material_samplers表已有sort_order字段")
            
            conn.commit()
            print("数据库迁移完成！所有数据的原始顺序已保持。")
            
    except sqlite3.Error as e:
        print(f"数据库迁移失败: {str(e)}")
        return False
    
    return True

def verify_migration(db_path="data/databases/materials.db"):
    """验证迁移结果"""
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # 验证material_params表
            cursor.execute("SELECT COUNT(*) FROM material_params WHERE sort_order IS NOT NULL")
            params_count = cursor.fetchone()[0]
            print(f"material_params表中有{params_count}条记录已设置sort_order")
            
            # 验证material_samplers表
            cursor.execute("SELECT COUNT(*) FROM material_samplers WHERE sort_order IS NOT NULL")
            samplers_count = cursor.fetchone()[0]
            print(f"material_samplers表中有{samplers_count}条记录已设置sort_order")
            
            # 检查材质数据顺序示例
            cursor.execute("""
                SELECT m.filename, COUNT(p.id) as param_count, COUNT(s.id) as sampler_count
                FROM materials m
                LEFT JOIN material_params p ON m.id = p.material_id
                LEFT JOIN material_samplers s ON m.id = s.material_id
                GROUP BY m.id
                LIMIT 5
            """)
            
            print("\n材质数据示例:")
            for row in cursor.fetchall():
                print(f"  {row[0]}: {row[1]}个参数, {row[2]}个采样器")
                
    except sqlite3.Error as e:
        print(f"验证失败: {str(e)}")

if __name__ == "__main__":
    print("开始数据库迁移...")
    print("=" * 50)
    
    # 确保数据库目录存在
    db_dir = "data/databases"
    if not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        print(f"创建数据库目录: {db_dir}")
    
    db_path = "data/databases/materials.db"
    
    if not os.path.exists(db_path):
        print("数据库文件不存在，将在首次运行应用程序时创建")
    else:
        print(f"找到数据库文件: {db_path}")
        
        # 执行迁移
        if migrate_database(db_path):
            print("\n验证迁移结果...")
            verify_migration(db_path)
        else:
            print("迁移失败！")
    
    print("=" * 50)
    print("迁移完成")