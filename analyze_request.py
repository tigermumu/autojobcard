import json
import urllib.parse
import sys

# Helper to safe print
def safe_print(s):
    try:
        print(s)
    except UnicodeEncodeError:
        print(s.encode('utf-8', errors='replace').decode('utf-8'))

def main():
    print("Starting analysis...")
    
    # --- 1. Load MD Content ---
    md_path = r"f:\autojobcard\步骤修改.md"
    md_content_str = ""
    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        capture = False
        for line in lines:
            if "respone 中找出字段符合变量名内容" in line:
                capture = True
                continue
            if capture and line.strip():
                md_content_str = line.strip()
                break 
    
    if not md_content_str:
        print("ERROR: Could not find response content in MD file.")
        return

    # md_params will be {key: [val1, val2, ...]}
    md_params = urllib.parse.parse_qs(md_content_str, keep_blank_values=True)
    md_keys = set(md_params.keys())
    print(f"MD Keys Count: {len(md_keys)}")

    # --- 2. Load HAR Content ---
    har_path = r"f:\autojobcard\请求 修改步驟.har"
    with open(har_path, 'r', encoding='utf-8') as f:
        har_data = json.load(f)
    
    # Find the request
    target_entry = None
    target_url_part = "updateJCSTP.jsp"
    
    if 'log' in har_data and 'entries' in har_data['log']:
        for entry in har_data['log']['entries']:
            req = entry['request']
            if target_url_part in req['url'] and req['method'] == 'POST':
                target_entry = entry
                break
    
    if not target_entry:
        print("ERROR: Could not find HAR entry.")
        return

    req = target_entry['request']
    
    # Extract HAR Post Params (keep as list to match MD structure if needed, or set for keys)
    har_post_params_list = {} 
    
    if 'postData' in req:
        # Check params array first
        if 'params' in req['postData']:
             for p in req['postData']['params']:
                 if p['name'] not in har_post_params_list:
                     har_post_params_list[p['name']] = []
                 har_post_params_list[p['name']].append(p['value'])
        # If no params array valid, try text
        elif 'text' in req['postData']:
             har_post_params_list = urllib.parse.parse_qs(req['postData']['text'], keep_blank_values=True)

    har_post_keys = set(har_post_params_list.keys())

    # Extract HAR Query Params
    har_query_params = {}
    if 'queryString' in req:
        for p in req['queryString']:
            har_query_params[p['name']] = p['value']
    
    har_query_keys = set(har_query_params.keys())

    # --- 3. Comparison ---
    
    # We want to find variables required in HAR but NOT in MD Response
    # Required = HAR Post Keys + HAR Query Keys
    # Available = MD Keys
    
    all_har_keys = har_post_keys.union(har_query_keys)
    
    missing_in_md = all_har_keys - md_keys
    
    print("\n[RESULT] Variable names in HAR (Request) but NOT in MD (Response):")
    print("===================================================================")
    if not missing_in_md:
        print("(None)")
    else:
        for k in sorted(missing_in_md):
            # Check if it was a query param or post param
            src = []
            if k in har_query_params: src.append("QueryParam")
            if k in har_post_params_list: src.append("PostParam")
            
            val = ""
            if k in har_query_params: val = har_query_params[k]
            elif k in har_post_params_list: val = str(har_post_params_list[k])
            
            print(f"{k} ({', '.join(src)}) [Value: {val}]")
            
    # Also check specific values for single-value keys to be helpful
    print("\n[DEBUG] Value differences for common keys (First Value):")
    common_keys = har_post_keys.intersection(md_keys)
    for k in common_keys:
        # Compare full lists
        l_har = har_post_params_list[k]
        l_md = md_params[k]
        if l_har != l_md:
            # Check if encoding difference
            # Simple check: ignore encoding diff
            match = True
            if len(l_har) != len(l_md):
                match = False
            else:
                 # Check first element as sample
                 v1 = l_har[0]
                 v2 = l_md[0]
                 # If string, try to decode percent
                 if v1 != v2:
                      # try comparing unquoted
                      if urllib.parse.unquote(v1) != urllib.parse.unquote(v2):
                           match = False
            
            if not match:
                safe_print(f"Key: {k}")
                safe_print(f"  HAR: {l_har}")
                safe_print(f"  MD : {l_md}")

    print("\nAnalysis Complete.")

if __name__ == "__main__":
    main()
