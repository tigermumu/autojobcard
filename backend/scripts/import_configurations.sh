#!/bin/bash
# 构型数据导入脚本（Linux/云服务器版本）

echo "========================================"
echo "构型数据导入工具（云服务器版）"
echo "========================================"
echo ""
echo "警告: 此操作将导入数据到当前数据库"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

# 进入backend目录
cd "$BACKEND_DIR" || exit 1

# 运行Python导入脚本
python3 scripts/import_configurations.py "$@"

if [ $? -eq 0 ]; then
    echo ""
    echo "导入成功！"
else
    echo ""
    echo "导入失败，请检查错误信息"
    echo ""
    echo "如果是因为 psql 未找到，可以尝试："
    echo "python3 scripts/import_configurations.py --use-python"
fi












