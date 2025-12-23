#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""查询B-777构型的索引数据条数"""

import sys
import os

# 添加项目路径
script_dir = os.path.dirname(os.path.abspath(__file__))
# backend目录路径
backend_dir = os.path.join(script_dir, 'backend')
sys.path.insert(0, backend_dir)

# 切换到backend目录
os.chdir(backend_dir)

from app.core.database import SessionLocal, engine
from app.models.index_data import IndexData
from app.models.configuration import Configuration
from sqlalchemy import inspect

def check_tables_exist():
    """检查数据库表是否存在"""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    return 'configurations' in tables and 'index_data' in tables

def main():
    # 检查数据库表是否存在
    if not check_tables_exist():
        print("错误：数据库表不存在！")
        print("请先运行数据库迁移：")
        print("  cd backend")
        print("  python -m alembic upgrade head")
        print("\n或者检查数据库文件路径是否正确。")
        return
    
    db = SessionLocal()
    try:
        # 查找B-777构型（尝试多种匹配方式）
        config = db.query(Configuration).filter(
            Configuration.name.like('%B-777%')
        ).first()
        
        # 如果没找到，尝试查找机型
        if not config:
            config = db.query(Configuration).filter(
                Configuration.aircraft_type.like('%777%')
            ).first()
        
        if not config:
            print("未找到B-777构型")
            # 列出所有构型
            all_configs = db.query(Configuration).all()
            if all_configs:
                print("\n所有构型列表：")
                for c in all_configs:
                    print(f"  - ID: {c.id}, 名称: {c.name}, 机型: {c.aircraft_type}")
            else:
                print("\n数据库中没有任何构型数据")
            return
        
        print(f"构型ID: {config.id}")
        print(f"构型名称: {config.name}")
        print(f"机型: {config.aircraft_type}")
        
        # 统计索引数据条数
        count = db.query(IndexData).filter(
            IndexData.configuration_id == config.id
        ).count()
        
        print(f"\n索引数据条数: {count}")
        
    except Exception as e:
        print(f"查询出错: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()

