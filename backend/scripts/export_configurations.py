#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
构型数据导出脚本
导出configurations、index_data、index_files表数据以及相关文件
"""

import os
import sys
import subprocess
import tarfile
import shutil
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.configuration import Configuration, IndexFile
from app.models.index_data import IndexData
from sqlalchemy import inspect


def parse_database_url(url: str) -> dict:
    """解析数据库URL"""
    parsed = urlparse(url)
    return {
        'host': parsed.hostname or 'localhost',
        'port': parsed.port or 5432,
        'user': parsed.username or 'postgres',
        'password': parsed.password or '',
        'database': parsed.path.lstrip('/') if parsed.path else 'aircraft_workcard'
    }


def escape_sql_string(value):
    """转义SQL字符串"""
    if value is None:
        return 'NULL'
    if isinstance(value, bool):
        return 'TRUE' if value else 'FALSE'
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, dict):
        return "'" + json.dumps(value, ensure_ascii=False).replace("'", "''") + "'"
    if isinstance(value, list):
        return "'" + json.dumps(value, ensure_ascii=False).replace("'", "''") + "'"
    # 字符串类型
    return "'" + str(value).replace("'", "''") + "'"


def export_table_with_python(model_class, table_name: str, output_dir: Path) -> Path:
    """使用Python直接导出表数据"""
    db = SessionLocal()
    sql_file = output_dir / f"{table_name}.sql"
    
    try:
        # 获取所有记录
        records = db.query(model_class).all()
        
        if not records:
            print(f"  ⚠ 警告: {table_name} 表为空")
            # 创建空文件
            with open(sql_file, 'w', encoding='utf-8') as f:
                f.write(f"-- {table_name} 表数据导出\n")
                f.write(f"-- 导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"-- 记录数: 0\n\n")
            return sql_file
        
        # 获取表结构（从模型类获取列名）
        mapper = inspect(model_class)
        columns = [col.key for col in mapper.columns]
        
        # 生成SQL INSERT语句
        with open(sql_file, 'w', encoding='utf-8') as f:
            f.write(f"-- {table_name} 表数据导出\n")
            f.write(f"-- 导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"-- 记录数: {len(records)}\n\n")
            
            for record in records:
                values = []
                for col in columns:
                    value = getattr(record, col, None)
                    values.append(escape_sql_string(value))
                
                column_names = ', '.join(columns)
                values_str = ', '.join(values)
                f.write(f"INSERT INTO {table_name} ({column_names}) VALUES ({values_str});\n")
        
        return sql_file
        
    except Exception as e:
        print(f"  ✗ Python导出失败: {e}")
        raise
    finally:
        db.close()


def export_database_tables(db_config: dict, output_dir: Path, use_python: bool = False) -> dict:
    """导出数据库表数据"""
    print("=" * 60)
    print("开始导出数据库表数据...")
    print("=" * 60)
    
    if use_python:
        print("\n使用Python方式导出（不依赖pg_dump）...")
    else:
        print("\n尝试使用pg_dump导出...")
    
    exported_files = {}
    
    # 表映射
    table_mapping = {
        'configurations': Configuration,
        'index_files': IndexFile,
        'index_data': IndexData
    }
    
    # 如果使用Python方式或pg_dump不可用，使用Python导出
    if use_python:
        for table_name, model_class in table_mapping.items():
            print(f"\n正在导出表: {table_name}")
            try:
                sql_file = export_table_with_python(model_class, table_name, output_dir)
                exported_files[table_name] = sql_file
                file_size = sql_file.stat().st_size
                print(f"✓ 成功导出 {table_name} 表到 {sql_file}")
                print(f"  文件大小: {file_size / 1024:.2f} KB")
            except Exception as e:
                print(f"✗ 导出 {table_name} 表失败: {e}")
                return None
        return exported_files
    
    # 尝试使用pg_dump
    env = os.environ.copy()
    if db_config['password']:
        env['PGPASSWORD'] = db_config['password']
    
    tables = ['configurations', 'index_files', 'index_data']
    pg_dump_available = True
    
    for table in tables:
        sql_file = output_dir / f"{table}.sql"
        print(f"\n正在导出表: {table}")
        
        cmd = [
            'pg_dump',
            '-h', db_config['host'],
            '-p', str(db_config['port']),
            '-U', db_config['user'],
            '-d', db_config['database'],
            '-t', table,
            '--data-only',
            '--column-inserts',
            '-f', str(sql_file)
        ]
        
        try:
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                check=True
            )
            exported_files[table] = sql_file
            print(f"✓ 成功导出 {table} 表到 {sql_file}")
            
            file_size = sql_file.stat().st_size
            print(f"  文件大小: {file_size / 1024:.2f} KB")
            
        except subprocess.CalledProcessError as e:
            print(f"✗ pg_dump导出 {table} 表失败:")
            print(f"  错误信息: {e.stderr}")
            pg_dump_available = False
            break
        except FileNotFoundError:
            print("⚠ 未找到 pg_dump 命令，切换到Python导出方式...")
            pg_dump_available = False
            break
    
    # 如果pg_dump失败，使用Python方式重新导出
    if not pg_dump_available:
        print("\n" + "=" * 60)
        print("切换到Python导出方式...")
        print("=" * 60)
        return export_database_tables(db_config, output_dir, use_python=True)
    
    return exported_files


def export_index_files(output_dir: Path) -> Path:
    """导出索引文件目录"""
    print("\n" + "=" * 60)
    print("开始导出索引文件...")
    print("=" * 60)
    
    uploads_dir = Path(__file__).parent.parent / "uploads" / "index_files"
    
    if not uploads_dir.exists():
        print(f"⚠ 警告: 索引文件目录不存在: {uploads_dir}")
        print("  将创建一个空的备份文件")
        # 创建空目录用于打包
        uploads_dir.mkdir(parents=True, exist_ok=True)
    
    tar_file = output_dir / "index_files_backup.tar.gz"
    
    print(f"\n正在打包目录: {uploads_dir}")
    
    try:
        with tarfile.open(tar_file, "w:gz") as tar:
            if uploads_dir.exists() and any(uploads_dir.iterdir()):
                tar.add(uploads_dir, arcname="index_files")
                print(f"✓ 成功打包索引文件到 {tar_file}")
                
                # 统计文件数量
                file_count = sum(1 for _ in uploads_dir.rglob('*') if _.is_file())
                print(f"  包含文件数: {file_count}")
            else:
                print("⚠ 警告: 索引文件目录为空")
        
        file_size = tar_file.stat().st_size
        print(f"  压缩包大小: {file_size / 1024:.2f} KB")
        
        return tar_file
        
    except Exception as e:
        print(f"✗ 打包索引文件失败: {e}")
        return None


def create_export_info(output_dir: Path, db_config: dict, exported_files: dict, tar_file: Path):
    """创建导出信息文件"""
    info_file = output_dir / "export_info.txt"
    
    with open(info_file, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("构型数据导出信息\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"数据库: {db_config['database']}\n")
        f.write(f"主机: {db_config['host']}:{db_config['port']}\n\n")
        f.write("导出的文件:\n")
        f.write("-" * 60 + "\n")
        for table, file_path in exported_files.items():
            if file_path.exists():
                size = file_path.stat().st_size
                f.write(f"  {table}.sql ({size / 1024:.2f} KB)\n")
        
        if tar_file and tar_file.exists():
            size = tar_file.stat().st_size
            f.write(f"  index_files_backup.tar.gz ({size / 1024:.2f} KB)\n")
        
        f.write("\n" + "=" * 60 + "\n")
        f.write("导入说明:\n")
        f.write("=" * 60 + "\n")
        f.write("1. 确保新服务器上已创建数据库并运行了迁移\n")
        f.write("2. 使用 import_configurations.py 脚本导入数据\n")
        f.write("3. 或手动执行以下步骤:\n")
        f.write("   a) 导入 configurations.sql\n")
        f.write("   b) 导入 index_files.sql\n")
        f.write("   c) 导入 index_data.sql\n")
        f.write("   d) 解压 index_files_backup.tar.gz\n")
        f.write("   e) 重置数据库序列\n")
    
    print(f"\n✓ 导出信息已保存到: {info_file}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='构型数据导出工具')
    parser.add_argument(
        '--use-python',
        action='store_true',
        help='强制使用Python方式导出（不依赖pg_dump）'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("构型数据导出工具")
    print("=" * 60)
    
    # 解析数据库配置
    db_config = parse_database_url(settings.DATABASE_URL)
    print(f"\n数据库配置:")
    print(f"  主机: {db_config['host']}:{db_config['port']}")
    print(f"  数据库: {db_config['database']}")
    print(f"  用户: {db_config['user']}")
    
    # 创建输出目录
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = Path(__file__).parent.parent / "exports" / f"configurations_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n输出目录: {output_dir}")
    
    # 导出数据库表
    exported_files = export_database_tables(db_config, output_dir, use_python=args.use_python)
    if not exported_files:
        print("\n✗ 数据库导出失败，终止操作")
        return 1
    
    # 导出索引文件
    tar_file = export_index_files(output_dir)
    
    # 创建导出信息文件
    create_export_info(output_dir, db_config, exported_files, tar_file)
    
    print("\n" + "=" * 60)
    print("导出完成！")
    print("=" * 60)
    print(f"\n所有文件已保存到: {output_dir}")
    print("\n下一步:")
    print("1. 将整个导出目录复制到新服务器")
    print("2. 在新服务器上运行 import_configurations.py 脚本")
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n操作已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

