import json
import urllib.parse

def main():
    # File paths
    har_path = r"f:\autojobcard\请求 修改步驟.har"
    md_path = r"f:\autojobcard\步骤修改.md"

    # 1. Parse the "Response Content" from markdown file
    response_content_str = ""
    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        # Look for the long line in step 2 (Line 48 in the view_file output, which might be different in actual file if view_file added line numbers, but view_file output says "The following code ... include a line number".
        # In the real file, it should be the line after "respone 中找出字段符合变量名内容。:"
        # Based on view_file, line 47 is "respone ...", line 48 is the content.
        # But I should search for it to be robust.
        found_marker = False
        for line in lines:
            if "respone 中找出字段符合变量名内容" in line:
                found_marker = True
                continue
            if found_marker and line.strip():
                response_content_str = line.strip()
                break
    
    # Parse the query string into a set of keys
    # The string looks like "key=value&key2=value2..."
    parsed_response = urllib.parse.parse_qs(response_content_str, keep_blank_values=True)
    response_keys = set(parsed_response.keys())

    print(f"Found {len(response_keys)} keys in Response Content.")

    # 2. Parse the HAR file request params
    with open(har_path, 'r', encoding='utf-8') as f:
        har_data = json.load(f)

    # We need to find the specific request. The user mentioned lines 5479-6156.
    # We can look for the request that matches the URL or characteristics in those lines.
    # Line 5481: "url": "http://10.240.2.131:9080/trace/fgm/workOrder/jobcard/updateJCSTP.jsp?sdrrFlag=false&flag41=true"
    
    target_url_fragment = "updateJCSTP.jsp"
    
    har_keys = set()
    found_entry = False

    if 'log' in har_data and 'entries' in har_data['log']:
        for entry in har_data['log']['entries']:
            req = entry['request']
            if target_url_fragment in req['url']:
                # verifying it's the POST request we saw
                if req['method'] == 'POST':
                    found_entry = True
                    # Add postData params
                    if 'postData' in req and 'params' in req['postData']:
                        for param in req['postData']['params']:
                            har_keys.add(param['name'])
                    # Add queryString params
                    if 'queryString' in req:
                        for param in req['queryString']:
                            har_keys.add(param['name'])
                    break
    
    if not found_entry:
        print("Error: Could not find the target request in HAR file.")
        return

    print(f"Found {len(har_keys)} keys in HAR Request (Post + Query).")

    # 3. specific requirement: "organize the variable names required in the .har file, but not specified in the response"
    # i.e. keys in HAR but NOT in Response
    
    missing_keys = har_keys - response_keys
    
    print("\nVariable names in HAR Request but NOT in Response Content:")
    print("========================================================")
    if not missing_keys:
        print("(None)")
    for key in sorted(missing_keys):
        print(key)

if __name__ == "__main__":
    main()
