import requests
import json
import re
import sys
import os
from bs4 import BeautifulSoup

# --- Configuration ---
# 1. ENTER YOUR COOKIES HERE
COOKIES = "YOUR_COOKIES_HERE" 

BASE_URL = "http://10.240.2.131:9080"

def load_har_required_keys(har_path):
    print(f"Loading HAR: {har_path}")
    with open(har_path, 'r', encoding='utf-8') as f:
        har_data = json.load(f)
    
    target_url_fragment = "updateJCSTP.jsp"
    target_entry = None
    
    # 1. Scan for Cookies (any request to the domain)
    found_cookie = ""
    if 'log' in har_data and 'entries' in har_data['log']:
        for entry in har_data['log']['entries']:
            req = entry['request']
            if 'headers' in req:
                for h in req['headers']:
                    if h['name'].lower() == 'cookie':
                        found_cookie = h['value']

            if target_url_fragment in req['url'] and req['method'] == 'POST':
                target_entry = entry

    if found_cookie and not COOKIES:
        print("Found a Cookie in HAR from scanning all requests.")
    
    if not target_entry:
        print("Error: Could not find 'updateJCSTP.jsp' POST request in HAR.")
        return set(), set(), found_cookie

    req = target_entry['request']
    
    post_keys = set()
    if 'postData' in req:
        if 'params' in req['postData']:
             for p in req['postData']['params']:
                 post_keys.add(p['name'])
        elif 'text' in req['postData']:
             try:
                 import urllib.parse
                 parsed = urllib.parse.parse_qs(req['postData']['text'])
                 post_keys.update(parsed.keys())
             except:
                 pass
             
    query_keys = set()
    if 'queryString' in req:
        for p in req['queryString']:
            query_keys.add(p['name'])
            
    print(f"HAR Requirements: {len(post_keys)} Post Params, {len(query_keys)} Query Params.")
        
    return post_keys, query_keys, found_cookie

def fetch_and_parse_step2(url, cookies_str=""):
    print(f"Fetching URL: {url}")
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
    }
    
    cookies = {}
    if cookies_str:
        for part in cookies_str.split(';'):
            if '=' in part:
                k, v = part.strip().split('=', 1)
                cookies[k] = v

    try:
        resp = requests.get(url, headers=headers, cookies=cookies, timeout=10)
        print(f"Response Status: {resp.status_code}")
        resp.encoding = 'GBK' 
        
        if resp.status_code != 200:
            print("Warning: Response not 200 OK.")
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        found_keys = set()
        for tag in soup.find_all(['input', 'select', 'textarea']):
            name = tag.get('name')
            if name:
                found_keys.add(name)
        
        text_content = resp.text.strip()
        if text_content.startswith("url=") or "&" in text_content:
             import urllib.parse
             try:
                 parsed = urllib.parse.parse_qs(text_content)
                 if len(parsed) > 5: 
                     print("Detected response as Query String format.")
                     found_keys.update(parsed.keys())
             except:
                 pass

        print(f"Found {len(found_keys)} distinct keys in Response.")
        return found_keys

    except Exception as e:
        print(f"Error fetching/parsing: {e}")
        return set()

def main():
    # 1. Config
    har_path = r"f:\autojobcard\请求 修改步驟.har"
    
    # 2. Get Step 2 URL from MD
    md_path = r"f:\autojobcard\步骤修改.md"
    step2_url = None
    with open(md_path, 'r', encoding='utf-8') as f:
        for line in f:
            if "alterJCSTPNRC.jsp" in line and "http" in line:
                match = re.search(r'(http://[^\s]+)', line)
                if match:
                    step2_url = match.group(1)
                    break
    
    if not step2_url:
        print("Could not find Step 2 URL in MD file.")
        return

    # 3. Cookies
    cookies_str = COOKIES
    if cookies_str == "YOUR_COOKIES_HERE":
         cookies_str = "" # Clear placeholder if not changed

    # 4. Execute
    har_post_keys, har_query_keys, har_cookie = load_har_required_keys(har_path)
    
    # Use HAR cookie if no user cookie provided
    if not cookies_str and har_cookie:
        print("Using Cookies from HAR file (since COOKIES var is empty).")
        cookies_str = har_cookie

    if not cookies_str:
        print("WARNING: No cookies found! Request will likely fail (401/302). Please edit COOKIES variable in this script.")

    response_keys = fetch_and_parse_step2(step2_url, cookies_str)
    
    # 5. Compare
    required_keys = har_post_keys.union(har_query_keys)
    missing_vars = required_keys - response_keys
    
    print("\n[Analysis Result]")
    print("Variables required by HAR (Step 3) but NOT found in Step 2 Response:")
    print("====================================================================")
    if not missing_vars:
        print("(None - All required variables found)")
    else:
        for v in sorted(missing_vars):
            src = []
            if v in har_post_keys: src.append("POST")
            if v in har_query_keys: src.append("QUERY")
            print(f"{v} ({','.join(src)})")

if __name__ == "__main__":
    main()
