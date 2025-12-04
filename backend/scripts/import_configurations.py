#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
构型数据导入脚本
导入configurations、index_data、index_files表数据以及相关文件
"""

import os
import sys
import subprocess
import tarfile
import shutil
import re
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.configuration import Configuration, IndexFile
from app.models.index_data import IndexData
from sqlalchemy import text


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


def find_export_directory(export_path: Optional[str] = None) -> Optional[Path]:
    """查找导出目录"""
    if export_path:
        path = Path(export_path)
        if path.exists() and path.is_dir():
            return path
        print(f"✗ 指定的路径不存在: {export_path}")
        return None
    
    # 查找最新的导出目录
    exports_dir = Path(__file__).parent.parent / "exports"
    if not exports_dir.exists():
        print(f"✗ 未找到导出目录: {exports_dir}")
        return None
    
    # 查找所有导出目录
    export_dirs = [d for d in exports_dir.iterdir() if d.is_dir() and d.name.startswith('configurations_')]
    
    if not export_dirs:
        print(f"✗ 在 {exports_dir} 中未找到导出目录")
        return None
    
    # 返回最新的目录
    latest_dir = max(export_dirs, key=lambda p: p.stat().st_mtime)
    print(f"✓ 找到最新导出目录: {latest_dir.name}")
    return latest_dir


def import_table_with_python(sql_file: Path, table_name: str) -> bool:
    """使用Python直接导入表数据（直接执行SQL）"""
    db = SessionLocal()
    
    try:
        # 读取SQL文件
        with open(sql_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 过滤掉注释行
        lines = []
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('--'):
                lines.append(line)
        
        sql_statements = '\n'.join(lines)
        
        if not sql_statements.strip():
            print(f"  ⚠ 警告: {table_name} SQL文件为空")
            return True
        
        # 执行SQL语句
        try:
            # 按分号分割语句
            statements = [s.strip() for s in sql_statements.split(';') if s.strip()]
            
            executed_count = 0
            for statement in statements:
                if statement:
                    try:
                        db.execute(text(statement))
                        executed_count += 1
                    except Exception as e:
                        # 如果是重复键错误，忽略
                        error_str = str(e).lower()
                        if 'duplicate key' in error_str or 'already exists' in error_str:
                            continue
                        # 其他错误打印但不中断
                        print(f"  ⚠ SQL执行警告: {str(e)[:100]}")
            
            db.commit()
            print(f"✓ 成功导入 {table_name} 表")
            print(f"  执行了 {executed_count} 条INSERT语句")
            return True
            
        except Exception as e:
            db.rollback()
            # 检查是否是重复数据错误
            error_str = str(e).lower()
            if 'duplicate key' in error_str or 'already exists' in error_str:
                print(f"  ⚠ 警告: 存在重复数据，但继续执行...")
                db.commit()
                return True
            raise
        
    except Exception as e:
        print(f"  ✗ Python导入失败: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def import_database_table(db_config: dict, sql_file: Path, table_name: str, use_python: bool = False) -> bool:
    """导入单个数据库表"""
    if not sql_file.exists():
        print(f"✗ SQL文件不存在: {sql_file}")
        return False
    
    print(f"\n正在导入表: {table_name}")
    
    # 如果使用Python方式
    if use_python:
        return import_table_with_python(sql_file, table_name)
    
    # 尝试使用psql
    env = os.environ.copy()
    if db_config['password']:
        env['PGPASSWORD'] = db_config['password']
    
    cmd = [
        'psql',
        '-h', db_config['host'],
        '-p', str(db_config['port']),
        '-U', db_config['user'],
        '-d', db_config['database'],
        '-f', str(sql_file),
        '-q'  # 安静模式
    ]
    
    try:
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            check=True
        )
        print(f"✓ 成功导入 {table_name} 表")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"✗ psql导入 {table_name} 表失败:")
        print(f"  错误信息: {e.stderr}")
        # 检查是否是重复数据错误（可以忽略）
        if 'duplicate key' in e.stderr.lower() or 'already exists' in e.stderr.lower():
            print("  ⚠ 警告: 可能存在重复数据，但继续执行...")
            return True
        # 如果psql失败，尝试Python方式
        print("  ⚠ 切换到Python导入方式...")
        return import_table_with_python(sql_file, table_name)
    except FileNotFoundError:
        print("⚠ 未找到 psql 命令，切换到Python导入方式...")
        return import_table_with_python(sql_file, table_name)


def reset_sequences_with_python():
    """使用Python重置数据库序列"""
    print("\n" + "=" * 60)
    print("重置数据库序列（Python方式）...")
    print("=" * 60)
    
    db = SessionLocal()
    
    sequences = [
        ('configurations_id_seq', 'configurations'),
        ('index_files_id_seq', 'index_files'),
        ('index_data_id_seq', 'index_data')
    ]
    
    try:
        for seq_name, table_name in sequences:
            print(f"\n正在重置序列: {seq_name}")
            
            # 构建SQL命令
            sql = text(f"SELECT setval('{seq_name}', COALESCE((SELECT MAX(id) FROM {table_name}), 1), true);")
            
            try:
                result = db.execute(sql)
                db.commit()
                print(f"✓ 成功重置 {seq_name}")
            except Exception as e:
                error_str = str(e).lower()
                if 'does not exist' in error_str or '不存在' in error_str:
                    print(f"  ⚠ 警告: 序列 {seq_name} 不存在，跳过...")
                else:
                    print(f"  ⚠ 警告: 重置序列失败: {e}")
                db.rollback()
    finally:
        db.close()


def reset_sequences(db_config: dict, use_python: bool = False):
    """重置数据库序列"""
    if use_python:
        reset_sequences_with_python()
        return
    
    print("\n" + "=" * 60)
    print("重置数据库序列...")
    print("=" * 60)
    
    sequences = [
        ('configurations_id_seq', 'configurations'),
        ('index_files_id_seq', 'index_files'),
        ('index_data_id_seq', 'index_data')
    ]
    
    # 设置环境变量
    env = os.environ.copy()
    if db_config['password']:
        env['PGPASSWORD'] = db_config['password']
    
    for seq_name, table_name in sequences:
        print(f"\n正在重置序列: {seq_name}")
        
        # 构建SQL命令
        sql = f"SELECT setval('{seq_name}', COALESCE((SELECT MAX(id) FROM {table_name}), 1), true);"
        
        cmd = [
            'psql',
            '-h', db_config['host'],
            '-p', str(db_config['port']),
            '-U', db_config['user'],
            '-d', db_config['database'],
            '-c', sql,
            '-q'
        ]
        
        try:
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                check=True
            )
            print(f"✓ 成功重置 {seq_name}")
        except subprocess.CalledProcessError as e:
            print(f"✗ psql重置 {seq_name} 失败: {e.stderr}")
            print("  ⚠ 切换到Python方式...")
            # 切换到Python方式
            reset_sequences_with_python()
            return
        except FileNotFoundError:
            print("⚠ 未找到 psql 命令，切换到Python方式...")
            reset_sequences_with_python()
            return


def import_index_files(export_dir: Path):
    """导入索引文件"""
    print("\n" + "=" * 60)
    print("导入索引文件...")
    print("=" * 60)
    
    tar_file = export_dir / "index_files_backup.tar.gz"
    
    if not tar_file.exists():
        print(f"⚠ 警告: 索引文件备份不存在: {tar_file}")
        print("  跳过文件导入")
        return
    
    # 目标目录
    target_dir = Path(__file__).parent.parent / "uploads" / "index_files"
    target_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n正在解压文件到: {target_dir}")
    
    try:
        with tarfile.open(tar_file, "r:gz") as tar:
            # 检查是否包含文件
            members = tar.getmembers()
            if not members:
                print("⚠ 警告: 压缩包为空")
                return
            
            # 解压文件
            tar.extractall(target_dir.parent)
            print(f"✓ 成功解压索引文件")
            
            # 统计文件数量
            extracted_dir = target_dir.parent / "index_files"
            if extracted_dir.exists():
                file_count = sum(1 for _ in extracted_dir.rglob('*') if _.is_file())
                print(f"  解压文件数: {file_count}")
            
    except Exception as e:
        print(f"✗ 解压索引文件失败: {e}")
        import traceback
        traceback.print_exc()


def verify_import(db_config: dict) -> bool:
    """验证导入结果"""
    print("\n" + "=" * 60)
    print("验证导入结果...")
    print("=" * 60)
    
    try:
        db = SessionLocal()
        
        # 检查表记录数
        tables = {
            'configurations': 'SELECT COUNT(*) FROM configurations',
            'index_files': 'SELECT COUNT(*) FROM index_files',
            'index_data': 'SELECT COUNT(*) FROM index_data'
        }
        
        all_ok = True
        
        for table_name, query in tables.items():
            try:
                result = db.execute(text(query))
                count = result.scalar()
                print(f"\n{table_name}: {count} 条记录")
                
                if count == 0:
                    print(f"  ⚠ 警告: {table_name} 表为空")
                else:
                    print(f"  ✓ {table_name} 表有数据")
                    
            except Exception as e:
                print(f"  ✗ 查询 {table_name} 表失败: {e}")
                all_ok = False
        
        # 检查外键关系
        print("\n检查外键关系...")
        try:
            # 检查index_data的configuration_id是否有效
            query = text("""
                SELECT COUNT(*) 
                FROM index_data id
                LEFT JOIN configurations c ON id.configuration_id = c.id
                WHERE id.configuration_id IS NOT NULL AND c.id IS NULL
            """)
            result = db.execute(query)
            orphan_count = result.scalar()
            
            if orphan_count > 0:
                print(f"  ⚠ 警告: 发现 {orphan_count} 条孤立记录（configuration_id无效）")
                all_ok = False
            else:
                print("  ✓ 外键关系正常")
                
            # 检查index_files的configuration_id是否有效
            query = text("""
                SELECT COUNT(*) 
                FROM index_files if
                LEFT JOIN configurations c ON if.configuration_id = c.id
                WHERE if.configuration_id IS NOT NULL AND c.id IS NULL
            """)
            result = db.execute(query)
            orphan_count = result.scalar()
            
            if orphan_count > 0:
                print(f"  ⚠ 警告: 发现 {orphan_count} 个孤立文件记录（configuration_id无效）")
                all_ok = False
            else:
                print("  ✓ 文件关联关系正常")
                
        except Exception as e:
            print(f"  ✗ 检查外键关系失败: {e}")
            all_ok = False
        
        db.close()
        
        return all_ok
        
    except Exception as e:
        print(f"✗ 验证过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='构型数据导入工具')
    parser.add_argument(
        '--export-dir',
        type=str,
        help='导出目录路径（如果不指定，将使用最新的导出目录）'
    )
    parser.add_argument(
        '--skip-files',
        action='store_true',
        help='跳过文件导入'
    )
    parser.add_argument(
        '--skip-verify',
        action='store_true',
        help='跳过验证步骤'
    )
    parser.add_argument(
        '--use-python',
        action='store_true',
        help='强制使用Python方式导入（不依赖psql）'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("构型数据导入工具")
    print("=" * 60)
    
    # 解析数据库配置
    db_config = parse_database_url(settings.DATABASE_URL)
    print(f"\n数据库配置:")
    print(f"  主机: {db_config['host']}:{db_config['port']}")
    print(f"  数据库: {db_config['database']}")
    print(f"  用户: {db_config['user']}")
    
    # 查找导出目录
    export_dir = find_export_directory(args.export_dir)
    if not export_dir:
        print("\n✗ 未找到导出目录，终止操作")
        return 1
    
    print(f"\n导出目录: {export_dir}")
    
    # 确认操作
    print("\n" + "=" * 60)
    print("警告: 此操作将导入数据到当前数据库")
    print("=" * 60)
    response = input("\n是否继续？(yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("操作已取消")
        return 0
    
    # 检查是否使用Python方式
    use_python = args.use_python
    
    # 按顺序导入表（先导入configurations，再导入关联表）
    tables_order = ['configurations', 'index_files', 'index_data']
    all_success = True
    
    for table in tables_order:
        sql_file = export_dir / f"{table}.sql"
        if not import_database_table(db_config, sql_file, table, use_python=use_python):
            print(f"\n⚠ 警告: {table} 表导入失败，但继续执行...")
            all_success = False
    
    # 重置序列
    reset_sequences(db_config, use_python=use_python)
    
    # 导入文件
    if not args.skip_files:
        import_index_files(export_dir)
    
    # 验证导入结果
    if not args.skip_verify:
        verify_success = verify_import(db_config)
        if not verify_success:
            print("\n⚠ 警告: 验证过程中发现问题，请检查数据")
    
    print("\n" + "=" * 60)
    if all_success:
        print("导入完成！")
    else:
        print("导入完成，但存在一些问题，请检查上述输出")
    print("=" * 60)
    
    return 0 if all_success else 1


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

