import pandas as pd
import sys
import os

# 查找Excel文件
excel_file = None
for root, dirs, files in os.walk('.'):
    for file in files:
        if 'defects list test5' in file and file.endswith('.xlsx'):
            excel_file = os.path.join(root, file)
            break
    if excel_file:
        break

if not excel_file:
    print("未找到Excel文件 'defects list test5 - 地面.xlsx'")
    sys.exit(1)

print(f"找到Excel文件: {excel_file}\n")
print("=" * 60)
print("Excel表的列名字段:")
print("=" * 60)

try:
    df = pd.read_excel(excel_file, engine='openpyxl')
    print(f"总列数: {len(df.columns)}\n")
    for i, col in enumerate(df.columns, 1):
        print(f"{i}. {col}")
    
    print("\n" + "=" * 60)
    print("前3行数据示例（用于参考）:")
    print("=" * 60)
    print(df.head(3).to_string())
    
except Exception as e:
    print(f"读取Excel文件时出错: {e}")
    import traceback
    traceback.print_exc()










