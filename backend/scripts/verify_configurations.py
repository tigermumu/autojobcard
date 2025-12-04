#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
构型数据验证脚本
验证configurations、index_data、index_files表的数据完整性和关联关系
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.models.configuration import Configuration, IndexFile
from app.models.index_data import IndexData
from sqlalchemy import text, func


def check_table_counts(db) -> Dict[str, int]:
    """检查各表的记录数"""
    print("=" * 60)
    print("检查表记录数")
    print("=" * 60)
    
    counts = {}
    
    tables = {
        'configurations': Configuration,
        'index_files': IndexFile,
        'index_data': IndexData
    }
    
    for table_name, model in tables.items():
        count = db.query(model).count()
        counts[table_name] = count
        status = "✓" if count > 0 else "⚠"
        print(f"{status} {table_name}: {count} 条记录")
    
    return counts


def check_foreign_keys(db) -> List[str]:
    """检查外键关系"""
    print("\n" + "=" * 60)
    print("检查外键关系")
    print("=" * 60)
    
    issues = []
    
    # 检查index_data的configuration_id
    print("\n检查 index_data.configuration_id...")
    query = text("""
        SELECT COUNT(*) 
        FROM index_data id
        LEFT JOIN configurations c ON id.configuration_id = c.id
        WHERE id.configuration_id IS NOT NULL AND c.id IS NULL
    """)
    result = db.execute(query)
    orphan_count = result.scalar()
    
    if orphan_count > 0:
        issues.append(f"index_data表中有{orphan_count}条记录的configuration_id无效")
        print(f"  ✗ 发现 {orphan_count} 条孤立记录")
        
        # 显示详细信息
        query = text("""
            SELECT DISTINCT id.configuration_id
            FROM index_data id
            LEFT JOIN configurations c ON id.configuration_id = c.id
            WHERE id.configuration_id IS NOT NULL AND c.id IS NULL
            LIMIT 10
        """)
        result = db.execute(query)
        invalid_ids = [row[0] for row in result]
        print(f"  无效的configuration_id: {invalid_ids[:10]}")
    else:
        print("  ✓ 所有configuration_id都有效")
    
    # 检查index_files的configuration_id
    print("\n检查 index_files.configuration_id...")
    query = text("""
        SELECT COUNT(*) 
        FROM index_files if
        LEFT JOIN configurations c ON if.configuration_id = c.id
        WHERE if.configuration_id IS NOT NULL AND c.id IS NULL
    """)
    result = db.execute(query)
    orphan_count = result.scalar()
    
    if orphan_count > 0:
        issues.append(f"index_files表中有{orphan_count}条记录的configuration_id无效")
        print(f"  ✗ 发现 {orphan_count} 个孤立文件记录")
    else:
        print("  ✓ 所有文件记录的configuration_id都有效")
    
    return issues


def check_data_distribution(db) -> Dict[str, Dict]:
    """检查数据分布"""
    print("\n" + "=" * 60)
    print("检查数据分布")
    print("=" * 60)
    
    distribution = {}
    
    # 检查每个构型的索引数据数量
    print("\n各构型的索引数据分布:")
    query = text("""
        SELECT 
            c.id,
            c.name,
            COUNT(id.id) as index_data_count,
            COUNT(if.id) as index_file_count
        FROM configurations c
        LEFT JOIN index_data id ON c.id = id.configuration_id
        LEFT JOIN index_files if ON c.id = if.configuration_id
        GROUP BY c.id, c.name
        ORDER BY c.id
    """)
    result = db.execute(query)
    
    for row in result:
        config_id, config_name, data_count, file_count = row
        distribution[config_id] = {
            'name': config_name,
            'index_data_count': data_count,
            'index_file_count': file_count
        }
        print(f"  构型 {config_id} ({config_name}):")
        print(f"    - 索引数据: {data_count} 条")
        print(f"    - 索引文件: {file_count} 个")
    
    return distribution


def check_field_mapping(db) -> List[str]:
    """检查field_mapping字段"""
    print("\n" + "=" * 60)
    print("检查field_mapping字段")
    print("=" * 60)
    
    issues = []
    
    configurations = db.query(Configuration).all()
    
    for config in configurations:
        if config.field_mapping:
            # 检查是否为有效的JSON格式
            if isinstance(config.field_mapping, dict):
                # 检查必要的字段
                required_fields = ['orientation', 'defectSubject', 'defectDescription', 'location', 'quantity']
                missing_fields = [f for f in required_fields if f not in config.field_mapping]
                
                if missing_fields:
                    issues.append(f"构型 {config.id} ({config.name}) 的field_mapping缺少字段: {missing_fields}")
                    print(f"  ⚠ 构型 {config.id} ({config.name}) 缺少字段: {missing_fields}")
                else:
                    # 统计每个字段的值数量
                    field_counts = {k: len(v) if isinstance(v, list) else 0 
                                   for k, v in config.field_mapping.items()}
                    print(f"  ✓ 构型 {config.id} ({config.name}):")
                    for field, count in field_counts.items():
                        print(f"    - {field}: {count} 个值")
            else:
                issues.append(f"构型 {config.id} ({config.name}) 的field_mapping格式无效")
                print(f"  ✗ 构型 {config.id} ({config.name}) field_mapping格式无效")
        else:
            print(f"  ⚠ 构型 {config.id} ({config.name}) 没有field_mapping")
    
    return issues


def check_file_paths(db) -> List[str]:
    """检查文件路径"""
    print("\n" + "=" * 60)
    print("检查文件路径")
    print("=" * 60)
    
    issues = []
    
    index_files = db.query(IndexFile).all()
    
    missing_files = []
    for index_file in index_files:
        file_path = Path(index_file.file_path)
        if not file_path.exists():
            missing_files.append({
                'id': index_file.id,
                'path': index_file.file_path,
                'config_id': index_file.configuration_id
            })
    
    if missing_files:
        issues.append(f"发现{len(missing_files)}个文件路径不存在")
        print(f"  ✗ 发现 {len(missing_files)} 个文件不存在:")
        for file_info in missing_files[:10]:  # 只显示前10个
            print(f"    - ID {file_info['id']}: {file_info['path']}")
        if len(missing_files) > 10:
            print(f"    ... 还有 {len(missing_files) - 10} 个文件")
    else:
        print("  ✓ 所有文件路径都存在")
    
    return issues


def check_data_quality(db) -> List[str]:
    """检查数据质量"""
    print("\n" + "=" * 60)
    print("检查数据质量")
    print("=" * 60)
    
    issues = []
    
    # 检查空值
    print("\n检查空值...")
    
    # 检查index_data的必要字段
    query = text("""
        SELECT COUNT(*) 
        FROM index_data
        WHERE main_area IS NULL OR main_area = ''
           OR main_component IS NULL OR main_component = ''
           OR first_level_subcomponent IS NULL OR first_level_subcomponent = ''
           OR second_level_subcomponent IS NULL OR second_level_subcomponent = ''
    """)
    result = db.execute(query)
    empty_count = result.scalar()
    
    if empty_count > 0:
        issues.append(f"index_data表中有{empty_count}条记录的必要字段为空")
        print(f"  ⚠ 发现 {empty_count} 条记录的必要字段为空")
    else:
        print("  ✓ 所有必要字段都有值")
    
    # 检查重复数据
    print("\n检查重复数据...")
    query = text("""
        SELECT 
            configuration_id,
            main_area,
            main_component,
            first_level_subcomponent,
            second_level_subcomponent,
            COUNT(*) as count
        FROM index_data
        GROUP BY configuration_id, main_area, main_component, first_level_subcomponent, second_level_subcomponent
        HAVING COUNT(*) > 1
        LIMIT 10
    """)
    result = db.execute(query)
    duplicates = list(result)
    
    if duplicates:
        issues.append(f"发现{len(duplicates)}组重复的索引数据")
        print(f"  ⚠ 发现 {len(duplicates)} 组重复数据（显示前10组）:")
        for dup in duplicates[:10]:
            print(f"    构型{dup[0]}: {dup[1]} > {dup[2]} > {dup[3]} > {dup[4]} (出现{dup[5]}次)")
    else:
        print("  ✓ 未发现重复数据")
    
    return issues


def main():
    """主函数"""
    print("=" * 60)
    print("构型数据验证工具")
    print("=" * 60)
    
    db = SessionLocal()
    all_issues = []
    
    try:
        # 检查表记录数
        counts = check_table_counts(db)
        
        # 检查外键关系
        issues = check_foreign_keys(db)
        all_issues.extend(issues)
        
        # 检查数据分布
        distribution = check_data_distribution(db)
        
        # 检查field_mapping
        issues = check_field_mapping(db)
        all_issues.extend(issues)
        
        # 检查文件路径
        issues = check_file_paths(db)
        all_issues.extend(issues)
        
        # 检查数据质量
        issues = check_data_quality(db)
        all_issues.extend(issues)
        
        # 总结
        print("\n" + "=" * 60)
        print("验证总结")
        print("=" * 60)
        
        if all_issues:
            print(f"\n⚠ 发现 {len(all_issues)} 个问题:")
            for i, issue in enumerate(all_issues, 1):
                print(f"  {i}. {issue}")
            return 1
        else:
            print("\n✓ 所有检查通过，数据完整性良好！")
            return 0
            
    except Exception as e:
        print(f"\n✗ 验证过程出错: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()


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












