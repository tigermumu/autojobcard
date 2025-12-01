#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单的 Qwen 网络连通性测试脚本
"""

import os
import requests
import json

# API 配置
API_KEY = os.getenv("QWEN_API_KEY", "sk-35f5e0a442d84007b1cf3c617d3220f6")
API_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"

# 请求数据
data = {
    "model": "qwen-turbo",
    "input": {
        "messages": [{"role": "user", "content": "你好"}]
    },
    "parameters": {
        "temperature": 0.7,
        "max_tokens": 100
    }
}

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

print("正在测试 Qwen API 连通性...")
print(f"URL: {API_URL}\n")

try:
    response = requests.post(API_URL, headers=headers, json=data, timeout=30)
    
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("✓ 连接成功！")
        print(f"\n响应数据:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"✗ 连接失败")
        print(f"响应内容: {response.text}")
        
except Exception as e:
    print(f"✗ 连接失败: {e}")
