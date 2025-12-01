#!/bin/bash
# 解压并导入构型数据脚本

# 默认导出目录（最新的）
EXPORT_DIR="/opt/workshop/backend/exports"
BACKEND_DIR="/opt/workshop/backend"

echo "========================================"
echo "构型数据解压和导入工具"
echo "========================================"
echo ""

# 检查是否有压缩包
if [ -f "$EXPORT_DIR/configurations_*.tar.gz" ]; then
    echo "发现压缩包，开始解压..."
    cd "$EXPORT_DIR"
    
    # 查找最新的压缩包
    LATEST_TAR=$(ls -t configurations_*.tar.gz 2>/dev/null | head -1)
    
    if [ -n "$LATEST_TAR" ]; then
        echo "解压: $LATEST_TAR"
        tar -xzf "$LATEST_TAR"
        
        # 获取解压后的目录名
        EXTRACTED_DIR=$(basename "$LATEST_TAR" .tar.gz)
        echo "✓ 解压完成: $EXTRACTED_DIR"
        
        # 询问是否导入
        echo ""
        read -p "是否立即导入数据？(y/n): " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cd "$BACKEND_DIR"
            python3 scripts/import_configurations.py --use-python --export-dir "exports/$EXTRACTED_DIR"
        fi
    else
        echo "✗ 未找到压缩包"
    fi
else
    echo "未找到压缩包，检查是否有已解压的目录..."
    
    # 查找最新的导出目录
    LATEST_DIR=$(ls -td "$EXPORT_DIR"/configurations_* 2>/dev/null | head -1)
    
    if [ -n "$LATEST_DIR" ]; then
        EXTRACTED_DIR=$(basename "$LATEST_DIR")
        echo "找到目录: $EXTRACTED_DIR"
        echo ""
        read -p "是否立即导入数据？(y/n): " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cd "$BACKEND_DIR"
            python3 scripts/import_configurations.py --use-python --export-dir "exports/$EXTRACTED_DIR"
        fi
    else
        echo "✗ 未找到导出目录"
        echo ""
        echo "请检查:"
        echo "1. 文件是否已传输到: $EXPORT_DIR"
        echo "2. 目录名是否正确"
        ls -la "$EXPORT_DIR" | head -10
    fi
fi






