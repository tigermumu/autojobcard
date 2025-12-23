import sys
import os
from sqlalchemy import create_engine, inspect

# Add local directory to sys.path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from backend.app.models.import_batch import ImportBatchItem

# ABSOLUTE PATH TO THE DATABASE
DB_URL = "sqlite:///f:/autojobcard/backend/aircraft_workcard.db"

print("=" * 60)
print("数据库表 import_batch_items 的字段信息:")
print("=" * 60)

engine = create_engine(DB_URL)
inspector = inspect(engine)

# 获取表结构
columns = inspector.get_columns('import_batch_items')

print(f"\n总字段数: {len(columns)}\n")
for i, col in enumerate(columns, 1):
    nullable = "可空" if col['nullable'] else "必填"
    col_type = str(col['type'])
    comment = f" ({col.get('comment', '')})" if col.get('comment') else ""
    print(f"{i}. {col['name']:30s} | 类型: {col_type:20s} | {nullable}{comment}")

print("\n" + "=" * 60)
print("从模型类 ImportBatchItem 的字段说明:")
print("=" * 60)

# 从模型获取字段信息
model_fields = [
    ("id", "主键ID", "Integer", False),
    ("batch_id", "批次ID", "Integer", False),
    ("defect_record_id", "缺陷记录ID", "Integer", True),
    ("defect_number", "缺陷编号", "String(100)", False),
    ("description_cn", "中文描述", "Text", True),
    ("description_en", "英文描述", "Text", True),
    ("workcard_number", "工卡号（候选）", "String(100)", False),
    ("issued_workcard_number", "已开出工卡号", "String(100)", True),
    ("selected_workcard_id", "选中的工卡ID", "Integer", True),
    ("similarity_score", "相似度分数", "Float", True),
    ("created_at", "创建时间", "DateTime", False),
    ("reference_workcard_number", "相关工卡号 (txtCRN)", "String(100)", True),
    ("reference_workcard_item", "相关工卡序号 (refNo)", "String(100)", True),
    ("area", "区域 (txtZoneName)", "String(100)", True),
    ("zone_number", "区域号 (txtZoneTen)", "String(100)", True),
]

print("\n")
for i, (field_name, description, field_type, nullable) in enumerate(model_fields, 1):
    nullable_str = "可空" if nullable else "必填"
    print(f"{i}. {field_name:30s} | {description:25s} | {field_type:15s} | {nullable_str}")










