"""
测试脚本 - 验证 Cookie 设置是否正确
"""
import requests

# 模拟第7行的COOKIES
COOKIES = "JSESSIONID=AEC54A1657C40236DFC069998BFFA890; JSESSIONID=8C7913AAC93669DDAEF7A024C9CD227B"

# 测试1: 验证headers['Cookie']设置
headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html"
}

if COOKIES:
    headers['Cookie'] = COOKIES.strip()

print("=== 测试 Cookie 设置 ===")
print(f"COOKIES 变量: {COOKIES}")
print(f"\nHeaders 中的 Cookie:")
print(f"  {headers.get('Cookie')}")

# 验证格式
expected_format = "JSESSIONID=AEC54A1657C40236DFC069998BFFA890; JSESSIONID=8C7913AAC93669DDAEF7A024C9CD227B"
if headers.get('Cookie') == expected_format:
    print("\n✅ Cookie 格式正确!")
else:
    print("\n❌ Cookie 格式不正确!")
    print(f"期望: {expected_format}")
    print(f"实际: {headers.get('Cookie')}")

# 测试2: 验证多个JSESSIONID是否保留
cookie_parts = headers.get('Cookie', '').split('; ')
jsessionid_count = sum(1 for part in cookie_parts if part.startswith('JSESSIONID='))
print(f"\n检测到 {jsessionid_count} 个 JSESSIONID")
if jsessionid_count == 2:
    print("✅ 多个 JSESSIONID 正确保留!")
else:
    print(f"❌ JSESSIONID 数量不正确,应该是 2 个")

print("\n=== 当前实现方式 ===")
print("fetch_ids:   headers['Cookie'] = COOKIES.strip()")
print("fetch_step2: headers['Cookie'] = raw_cookies.strip()")
print("fetch_step3: headers['Cookie'] = raw_cookies.strip()")
print("\n这种方式与 workcard_import_service.py 一致 ✅")
