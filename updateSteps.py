import requests
from bs4 import BeautifulSoup
import re
import urllib3

# 禁用SSL警告（VPN访问时可能需要）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- Configuration ---
# VPN访问模式配置
USE_VPN = False  # 设置为True使用VPN访问，False使用内网直连

# VPN Cookie（包含VPN认证cookie和应用cookie）
VPN_COOKIES = "selected_realm=ssl_vpn; ___fnbDropDownState=1; CPCVPN_CSHELL_SEQ_MODES=5; AMP_MKTG_5f4c1fb366=JTdCJTdE; CPCVPN_SESSION_ID=d3e32fc0252192d44a9bbb9ca589fa50dce6e1d2; CPCVPN_BASE_HOST=vpn.gameco.com.cn; CPCVPN_OBSCURE_KEY=44c140102fa383f01f645f010c4f4bed; CPCVPN_SDATA_VERSION=5; AMP_5f4c1fb366=JTdCJTIyb3B0T3V0JTIyJTNBZmFsc2UlMkMlMjJkZXZpY2VJZCUyMiUzQSUyMjQ3NGQ3NmVjLWZkYmQtNDkxOS05YTVhLWE3NmY5OTRlMTZlNiUyMiUyQyUyMmxhc3RFdmVudFRpbWUlMjIlM0ExNzY4NjE2MzU2NDY2JTJDJTIyc2Vzc2lvbklkJTIyJTNBMTc2ODYxNjEyNjA1NCUyQyUyMnVzZXJJZCUyMiUzQSUyMmI0OGFlN2UxLWFjNzQtZjlkMi0zNTBmLTUwZjFiZGJhMzkwYSUyMiU3RA=="
# 内网直连模式Cookie
COOKIES = "JSESSIONID=3A88A4B76F13C791F27559CD0CDBA08A; JSESSIONID=19A921FE4D1F076D758836CF3020FADE" 

# VPN配置
VPN_BASE_URL = "https://vpn.gameco.com.cn/Web"
VPN_HOST = "vpn.gameco.com.cn"
INTRANET_HOST = "10.240.2.131:9080"
INTRANET_PROTOCOL = "http"
VPN_ORG = "rel"

# 内网直连URL（已注释，保留备用）
# URL = "http://10.240.2.131:9080/trace/wsm/jc_in_out/stepIn.jsp"

def build_vpn_url(intranet_path, use_abs=False, include_trans_dest=False):
    """
    构建VPN代理URL
    格式: https://vpn.gameco.com.cn/Web/{内网路径},CVPNHost={主机}:{端口},CVPNProtocol={协议},CVPNOrg={rel/abs},CVPNExtension={扩展名}
    
    Args:
        intranet_path: 内网路径
        use_abs: 如果为True，使用CVPNOrg=abs（用于fgm.do等中间请求），否则使用CVPNOrg=rel
        include_trans_dest: 如果为True，包含CVPNTransDest=0（用于fgm.do等中间请求）
    """
    # 提取文件扩展名
    if '.' in intranet_path:
        extension = '.' + intranet_path.split('.')[-1]
    else:
        extension = '.jsp'
    
    # 选择CVPNOrg参数
    cvpn_org = "abs" if use_abs else VPN_ORG
    
    # 构建URL参数
    params = [
        f"CVPNHost={INTRANET_HOST}",
        f"CVPNProtocol={INTRANET_PROTOCOL}",
        f"CVPNOrg={cvpn_org}",
        f"CVPNExtension={extension}"
    ]
    
    # 如果需要，添加CVPNTransDest=0
    if include_trans_dest:
        params.insert(0, "CVPNTransDest=0")
    
    params_str = ",".join(params)
    vpn_url = f"{VPN_BASE_URL}/{intranet_path},{params_str}"
    return vpn_url

def apply_cookie_string_to_session(session, cookie_string, domain=None):
    if not session or not cookie_string:
        return
    for part in cookie_string.split(';'):
        part = part.strip()
        if not part or '=' not in part:
            continue
        name, value = part.split('=', 1)
        name = name.strip()
        value = value.strip()
        if domain:
            session.cookies.set(name, value, domain=domain)
        else:
            session.cookies.set(name, value)

def fetch_jc_workorder(sale_wo, ac_no, jc_seq, session=None):
    """
    通过HTTP请求从内网获取jc_workorder_input
    URL: https://vpn.gameco.com.cn/Web/trace/fgm/workOrder/checkData.jsp,CVPNHost=10.240.2.131:9080,CVPNProtocol=http,CVPNOrg=rel,CVPNExtension=.jsp?from=manage
    从响应中提取name="jcWo"的input元素的值
    """
    # 根据USE_VPN选择URL
    if USE_VPN:
        # VPN访问模式
        intranet_path = "trace/fgm/workOrder/checkData.jsp"
        url = build_vpn_url(intranet_path)
    else:
        # 内网直连模式
        url = "http://10.240.2.131:9080/trace/fgm/workOrder/checkData.jsp"
    
    # Query参数
    query_params = {"from": "manage"}
    
    # 构建payload
    payload = [
        ('wgp', 'QRY'),
        ('printer', ''),
        ('txtMenuID', '14076'),
        ('txtFullReg', ac_no),  # ACNo
        ('qWorkorder', sale_wo),  # SaleWo
        ('txtFlight_Check_No', ''),
        ('txtIPC_Num', ''),
        ('txtVisit_Desc', ''),
        ('txtMpd', ''),
        ('txtType', ''),
        ('txtSeq', jc_seq),  # jc_seq
        ('txtJobcard', ''),
        ('txtJcDesc', ''),
        ('txtQcFinal', ''),
        ('txtJcStatus', ''),
        ('txtSlnStatus', ''),
        ('txtImport', ''),
        ('txtBoothAss', ''),
        ('txtSlnPrinted', ''),
        ('preWorkGrp', ''),
        ('curWorkGrp', ''),
        ('schemeGrp', ''),
        ('txtUpdatedBy', ''),
        ('txtDangerousCargo', ''),
        ('txtSchedPhase', ''),
        ('txtSchedZone', ''),
        ('txtLaborCode', ''),
        ('txtTransferMode', ''),
        ('txtme_unUpload', ''),
        ('txtRii', ''),
        ('txtMatStatus', ''),
        ('txtFilterTrace', ''),
        ('txtJcRob', ''),
        ('txtPrDateStart', ''),
        ('txtPrDateEnd', ''),
        ('txtRTrade', ''),
        ('txtHoldBy', ''),
        ('txtJcTransferDateStart', ''),
        ('txtJcTransferDateEnd', ''),
        ('txtJcWorkorder', ''),
        ('txtSlnReqDateStart', ''),
        ('txtSlnReqDateEnd', ''),
        ('txtFlagMpd', ''),
        ('txtFlagActive', ''),
        ('txtExternal', ''),
        ('txtExteriorDamag', ''),
        ('txtMajorMdo', ''),
        ('txtOutOfManual', ''),
        ('txtStrRepair', ''),
        ('txtPse', ''),
        ('txtFcs', ''),
        ('txtCauseStrr', ''),
        ('txtRplStrPart', ''),
        ('txtQcStamp', ''),
        ('txtNmfTrade', ''),
        ('txtForbidEsign', ''),
        ('txtFedexAmtStamp', ''),
        ('txtFeeRemark', ''),
        ('txtFlagFee', ''),
        ('txtInspector', ''),
    ]
    
    # Headers
    if USE_VPN:
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": VPN_HOST,
            "Origin": f"https://{VPN_HOST}",
            "Referer": url,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
            "sec-ch-ua": '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1"
        }
        # 设置Cookie
        if VPN_COOKIES:
            headers['Cookie'] = VPN_COOKIES.strip()
    else:
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": "10.240.2.131:9080",
            "Origin": "http://10.240.2.131:9080",
            "Referer": url,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
        }
        # 设置Cookie
        if COOKIES:
            headers['Cookie'] = COOKIES.strip()
    
    print(f"\n[获取jc_workorder] 发送请求到: {url}")
    print(f"[获取jc_workorder] SaleWo={sale_wo}, ACNo={ac_no}, jcSeq={jc_seq}")
    
    request_session = session if session else requests
    try:
        response = request_session.post(url, params=query_params, data=payload, headers=headers, timeout=15, verify=False)
        response.encoding = 'GBK'
        
        print(f"[获取jc_workorder] Response Status: {response.status_code}")
        
        if response.status_code != 200:
            print("[获取jc_workorder] Failed to get valid response.")
            return None
        
        html = response.text
        print(f"[获取jc_workorder] Response Length: {len(html)}")
        
        # 检查是否被重定向到登录页
        if "j_acegi_security_check" in html or "loginCode" in html or "验证码" in html or "登录" in html[:500]:
            print("[获取jc_workorder] ERROR: 检测到登录页面，身份验证失败！")
            return None
        
        # 解析HTML，查找name="jcWo"的input元素
        soup = BeautifulSoup(html, 'html.parser')
        jc_wo_input = soup.find('input', {'name': 'jcWo'})
        
        if jc_wo_input:
            jc_workorder = jc_wo_input.get('value')
            if jc_workorder:
                print(f"[获取jc_workorder] 成功获取 jcWo: {jc_workorder}")
                return jc_workorder
            else:
                print("[获取jc_workorder] 找到jcWo input但value为空")
        else:
            print("[获取jc_workorder] 未找到name='jcWo'的input元素")
            # 尝试使用正则表达式搜索
            jc_wo_match = re.search(r'name=["\']jcWo["\'][^>]*value=["\']?(\d+)', html, re.IGNORECASE)
            if jc_wo_match:
                jc_workorder = jc_wo_match.group(1)
                print(f"[获取jc_workorder] 使用正则表达式找到 jcWo: {jc_workorder}")
                return jc_workorder
        
        print("[获取jc_workorder] 无法从响应中提取jcWo值")
        return None
        
    except Exception as e:
        print(f"[获取jc_workorder] Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def fetch_ids(jc_workorder, session=None):
    # 根据USE_VPN选择URL和配置
    if USE_VPN:
        # VPN访问模式
        intranet_path = "trace/wsm/jc_in_out/stepIn.jsp"
        url = build_vpn_url(intranet_path)
        referer_path = "trace/wsm/jc_in_out/stepIn.jsp"
        referer = build_vpn_url(referer_path)
        cookies = VPN_COOKIES
        
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": VPN_HOST,
            "Origin": f"https://{VPN_HOST}",
            "Referer": referer,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
            "sec-ch-ua": '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1"
        }
        print(f"[VPN模式] Sending request to {url} with txtJcWorkorder={jc_workorder}...")
    else:
        # 内网直连模式
        url = "http://10.240.2.131:9080/trace/wsm/jc_in_out/stepIn.jsp"
        referer = "http://10.240.2.131:9080/trace/wsm/jc_in_out/stepIn.jsp"
        cookies = COOKIES
        
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": "10.240.2.131:9080",
            "Origin": "http://10.240.2.131:9080",
            "Referer": referer,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
        }
        print(f"[内网直连模式] Sending request to {url} with txtJcWorkorder={jc_workorder}...")
    
    # Construct Post Data based on user description
    # Note: Requests handles multiple values for the same key if we pass a list of tuples
    payload = [
        ('username', ''),
        ('userID', ''),
        ('historyJcWorkorder', ''),
        ('workOrderStatus', 'N'),
        ('jcStatus', 'N'),
        ('jcType', 'NR'),
        ('txtMessage', ''),
        ('showRmMsg', 'false'),
        ('jcWorkOrders', ''),
        ('txtJcWorkorder', jc_workorder),
        ('txtUserID', ''),
        ('txtQcUser', ''),
        # Repeated fields (rows?)
        ('stepStatus', 'Y'),
        ('isWorkDate', '0'),
        ('stepStatus', 'Y'),
        ('isWorkDate', '0'),
        ('stepStatus', 'N'),
        ('strStepWorkDate', ''),
        ('isWorkDate', '0'),
        ('stepStatus', 'N'),
        ('strStepWorkDate', ''),
        ('isWorkDate', '0'),
    ]
    
    # 直接设置Cookie头（仅在未传入session时使用）
    if not session:
        if cookies:
            headers['Cookie'] = cookies.strip()
            print(f"已设置Cookie: {cookies.strip()[:100]}...")
    else:
            print("WARNING: Cookie为空，请求可能失败（需要登录）")

    request_session = session if session else requests
    try:
        response = request_session.post(url, data=payload, headers=headers, timeout=15, verify=False)
        response.encoding = 'GBK' # Typical for this system

        print(f"Response Status: {response.status_code}")
        
        if response.status_code != 200:
            print("Failed to get valid response.")
            return None, None, None

        html = response.text
        print(f"Response Length: {len(html)}") 
        
        # 检查是否被重定向到登录页（身份验证失败）
        if "j_acegi_security_check" in html or "loginCode" in html or "验证码" in html or "登录" in html[:500]:
            print("ERROR: 检测到登录页面，身份验证失败！")
            print("可能原因：Cookie无效或已过期")
            print(f"响应内容预览: {html[:500]}")
            return None, None, None 

        # Extract woRid and jcRid
        soup = BeautifulSoup(html, 'html.parser')
        
        wo_rid = None
        jc_rid = None
        
        # Try finding inputs with these names
        input_wo = soup.find('input', {'name': 'woRid'})
        if input_wo: wo_rid = input_wo.get('value')
        
        input_jc = soup.find('input', {'name': 'jcRid'})
        if input_jc: jc_rid = input_jc.get('value')
        
        # If not in inputs, maybe in a link
        if not wo_rid or not jc_rid:
            print("Searching in links...")
            links = soup.find_all('a', href=True)
            for link in links:
                href = link['href']
                if 'woRid' in href and 'jcrid' in href.lower():
                    import urllib.parse
                    parsed = urllib.parse.urlparse(href)
                    params = urllib.parse.parse_qs(parsed.query)
                    
                    if 'woRid' in params: wo_rid = params['woRid'][0]
                    
                    for k in params.keys():
                        if k.lower() == 'jcrid':
                            jc_rid = params[k][0]
                            break
                    
                    if wo_rid and jc_rid:
                        print(f"Found IDs in link: {href}")
                        break
        
        # Try regex if still not found
        jc_seq = None
        if not wo_rid or not jc_rid:
            print("Searching with Regex...")
            wo_match = re.search(r'woRid[=:]\s*["\']?(\d+)', html, re.IGNORECASE)
            jc_match = re.search(r'jcRid[=:]\s*["\']?(\d+)', html, re.IGNORECASE)
            
            if wo_match: wo_rid = wo_match.group(1)
            if jc_match: jc_rid = jc_match.group(1)
        
        # Try to find jcSeq
        seq_match = re.search(r'jcSeq[=:]\s*["\']?(\d+)', html, re.IGNORECASE)
        if seq_match:
            jc_seq = seq_match.group(1)
        else:
            links = soup.find_all('a', href=True)
            for link in links:
                if 'jcSeq' in link['href']:
                     match = re.search(r'jcSeq=(\d+)', link['href'], re.IGNORECASE)
                     if match:
                         jc_seq = match.group(1)
                         break

        print("\n--- RESULTS ---")
        if wo_rid:
            print(f"woRid: {wo_rid}")
        else:
            print("woRid: NOT FOUND")
            
        if jc_rid:
            print(f"jcRid: {jc_rid}")
        else:
            print("jcRid: NOT FOUND")
            
        if jc_seq:
            print(f"jcSeq: {jc_seq}")
        else:
            print("jcSeq: NOT FOUND (Will use default)")

        return wo_rid, jc_rid, jc_seq

    except Exception as e:
        print(f"Error: {e}")
        return None, None, None

def fetch_step2(wo_rid, jc_rid, jc_seq, raw_cookies, session=None):
    """
    Step 2: GET request to alterJCSTPNRC.jsp
    Scrapes all form field names and values from the response.
    """
    import time
    
    # 根据USE_VPN选择URL和配置
    if USE_VPN:
        # VPN访问模式
        intranet_path = "trace/fgm/workOrder/jobcard/alterJCSTPNRC.jsp"
        url_step2 = build_vpn_url(intranet_path)
        referer_path = "trace/wsm/jc_in_out/stepIn.jsp"
        referer = build_vpn_url(referer_path)
        
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
            "Host": VPN_HOST,
            "Referer": referer,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
            "sec-ch-ua": '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1"
        }
        print(f"[Step 2 VPN模式] Sending GET request...")
    else:
        # 内网直连模式
        url_step2 = "http://10.240.2.131:9080/trace/fgm/workOrder/jobcard/alterJCSTPNRC.jsp"
        referer = "http://10.240.2.131:9080/trace/wsm/jc_in_out/stepIn.jsp"
        
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
            "Host": "10.240.2.131:9080",
            "Referer": referer,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
        }
        print(f"[Step 2 内网直连模式] Sending GET request...")
    
    # Dynamic timestamp
    dt_val = str(int(time.time() * 1000))
    
    # Parameters from user
    params = {
        "wgp": "3_CABIN_TPG",
        "jcrid": jc_rid,
        "woRid": wo_rid,
        "jcType": "NR",
        "jcSeq": jc_seq,
        "jcmode": "E",
        "ownerCode": "EK",
        "eSign": "",
        "flagEPrt": "",
        "txtMenuID": "22800",
        "_dt": dt_val 
    }
    
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    print(f"\n[Step 2] Prepared URL: {url_step2}?{query_string}")
    
    # 直接设置Cookie头（仅在未传入session时使用）
    if not session and raw_cookies:
        headers['Cookie'] = raw_cookies.strip()
        print(f"[Step 2] 已设置Cookie: {raw_cookies.strip()[:100]}...")

    request_session = session if session else requests
    try:
        response = request_session.get(url_step2, params=params, headers=headers, timeout=15, verify=False)
        response.encoding = 'GBK'
        print(f"[Step 2] Response Status: {response.status_code}")
        
        # 调试：输出所有响应头
        print(f"\n[Step 2] 响应头信息:")
        for key, value in response.headers.items():
            if 'cookie' in key.lower() or 'set-cookie' in key.lower():
                print(f"  {key}: {value[:150]}...")
        
        # 检查响应中的Set-Cookie头，获取服务器返回的新Cookie
        response_cookies = []
        
        # 方法1: 检查响应头中的Set-Cookie（不区分大小写）
        set_cookie_keys = [k for k in response.headers.keys() if k.lower() == 'set-cookie']
        if set_cookie_keys:
            for key in set_cookie_keys:
                set_cookie_header = response.headers[key]
                print(f"[Step 2] 响应头中包含Set-Cookie: {set_cookie_header[:100]}...")
                response_cookies.append(set_cookie_header)
        
        # 方法2: 检查response.cookies对象（requests自动解析的）
        if hasattr(response, 'cookies') and response.cookies:
            print(f"[Step 2] response.cookies对象包含 {len(response.cookies)} 个Cookie")
            for cookie in response.cookies:
                cookie_str = f"{cookie.name}={cookie.value}"
                if cookie_str not in response_cookies:
                    response_cookies.append(cookie_str)
                print(f"  Cookie对象: {cookie.name}={cookie.value[:50]}...")
        
        # 方法3: 尝试获取所有Set-Cookie头（可能有多个）
        try:
            # requests的响应头是CaseInsensitiveDict，可能有多个Set-Cookie
            all_set_cookies = []
            for key in response.headers.keys():
                if key.lower() == 'set-cookie':
                    all_set_cookies.append(response.headers[key])
            
            if all_set_cookies:
                print(f"[Step 2] 找到 {len(all_set_cookies)} 个Set-Cookie头")
                for idx, cookie_header in enumerate(all_set_cookies):
                    print(f"  Set-Cookie[{idx}]: {cookie_header[:100]}...")
                    # 提取cookie名称和值
                    cookie_part = cookie_header.split(';')[0].strip()
                    if '=' in cookie_part and cookie_part not in response_cookies:
                        response_cookies.append(cookie_part)
        except Exception as e:
            print(f"[Step 2] 获取Set-Cookie头时出错: {e}")
        
        if response.status_code != 200:
            print("[Step 2] Failed to get valid response.")
            return [], []

        html = response.text
        print(f"[Step 2] Response Length: {len(html)}")
        
        # 检查是否被重定向到登录页（身份验证失败）
        if "j_acegi_security_check" in html or "loginCode" in html or "验证码" in html or "登录" in html[:500]:
            print("[Step 2] ERROR: 检测到登录页面，身份验证失败！")
            print("[Step 2] 可能原因：Cookie无效或已过期")
            return [], []
        
        # 方法4: 从HTML中提取JSESSIONID（如果响应中没有Set-Cookie）
        if not response_cookies:
            print("[Step 2] 未在响应头中找到Cookie，尝试从HTML中提取JSESSIONID...")
            # 查找JSESSIONID的常见模式
            jsessionid_patterns = [
                r'JSESSIONID[=:]\s*([A-F0-9]+)',
                r'jsessionid[=:]\s*([A-F0-9]+)',
                r'"jsessionid"\s*:\s*"([A-F0-9]+)"',
            ]
            for pattern in jsessionid_patterns:
                matches = re.finditer(pattern, html, re.IGNORECASE)
                for match in matches:
                    jsessionid_value = match.group(1)
                    cookie_str = f"JSESSIONID={jsessionid_value}"
                    if cookie_str not in response_cookies:
                        response_cookies.append(cookie_str)
                        print(f"  从HTML中提取到: JSESSIONID={jsessionid_value[:50]}...")
                        break
                if response_cookies:
                    break
        
        if not response_cookies:
            print("[Step 2] 警告: 未找到任何新Cookie")
        
        # Parse logic - extract ALL form field names and values
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find all input/select/textarea names and values in response
        actual_vars_list = []
        for tag in soup.find_all(['input', 'select', 'textarea']):
            name = tag.get('name')
            if not name:
                continue
                
            # Extract value
            value = ""
            
            if tag.name == "textarea":
                value = tag.get_text()
            elif tag.name == "select":
                # Find selected option
                selected = tag.find('option', selected=True)
                if selected:
                    value = selected.get('value', '')
                else:
                    # If none selected, use first option
                    first_opt = tag.find('option')
                    if first_opt:
                         value = first_opt.get('value', '')
            else:
                # input
                value = tag.get('value', '')

            actual_vars_list.append((name, value))
        
        print(f"[Step 2] Found {len(actual_vars_list)} variables/values in response.")
        
        # 返回数据和新Cookie
        return actual_vars_list, response_cookies

    except Exception as e:
        print(f"Step 2 Error: {e}")
        return []

def process_stepEnDesc(step2_data_list, cmm_refer, action_word=None):
    """
    处理 stepEnDesc 字段的修改规则：
    1. "REF TO "后面的到"," 之间的内容替换成 CMM_REFER 变量
    2. "," 之后的第一个单词保持不变
    3. "," 之后的第一个单词后的内容替换成 step2_data 中的 'jcendesc' 字段内容
    4. 'jcendesc' 内容的最后一个单词删掉
    """
    import re
    
    # 将列表转换为字典以便查找
    data_dict = dict(step2_data_list)
    
    # 获取 jcendesc 字段内容
    jcendesc = data_dict.get('jcendesc', '')
    if jcendesc:
        # 删除最后一个单词
        jcendesc_words = jcendesc.strip().split()
        if len(jcendesc_words) > 0:
            jcendesc_processed = ' '.join(jcendesc_words[:-1])
        else:
            jcendesc_processed = ''
    else:
        jcendesc_processed = ''
    
    def _replace_step_en_desc(new_value):
        updated_list = []
        replaced = False
        for name, value in step2_data_list:
            if name == 'stepEnDesc':
                updated_list.append((name, new_value))
                replaced = True
            else:
                updated_list.append((name, value))
        if not replaced:
            updated_list.append(('stepEnDesc', new_value))
        return updated_list

    # 获取 stepEnDesc 字段内容
    stepEnDesc = data_dict.get('stepEnDesc', '')
    if not stepEnDesc:
        if action_word:
            new_stepEnDesc = f"REF TO {cmm_refer}, {action_word} {jcendesc_processed}".strip()
            print("[处理stepEnDesc] 未找到stepEnDesc字段，使用默认模板生成")
            print(f"[处理stepEnDesc] 修改后内容: {new_stepEnDesc}")
            return _replace_step_en_desc(new_stepEnDesc)
        print("[处理stepEnDesc] 未找到stepEnDesc字段，跳过处理")
        return step2_data_list

    if action_word and stepEnDesc.strip().upper() == "TEST":
        new_stepEnDesc = f"REF TO {cmm_refer}, {action_word} {jcendesc_processed}".strip()
        print("[处理stepEnDesc] stepEnDesc为TEST，使用默认模板生成")
        print(f"[处理stepEnDesc] 修改后内容: {new_stepEnDesc}")
        return _replace_step_en_desc(new_stepEnDesc)
    
    print(f"[处理stepEnDesc] 原始内容: {stepEnDesc}")
    print(f"[处理stepEnDesc] jcendesc: {jcendesc}")
    print(f"[处理stepEnDesc] jcendesc处理后: {jcendesc_processed}")
    print(f"[处理stepEnDesc] CMM_REFER: {cmm_refer}")
    
    # 查找 "REF TO " 和 "," 的位置
    ref_to_pattern = r'REF TO\s+'
    ref_to_match = re.search(ref_to_pattern, stepEnDesc, re.IGNORECASE)
    
    if not ref_to_match:
        if action_word:
            new_stepEnDesc = f"REF TO {cmm_refer}, {action_word} {jcendesc_processed}".strip()
            print("[处理stepEnDesc] 未找到 'REF TO'，使用默认模板生成")
            print(f"[处理stepEnDesc] 修改后内容: {new_stepEnDesc}")
            return _replace_step_en_desc(new_stepEnDesc)
        print("[处理stepEnDesc] 未找到 'REF TO'，跳过处理")
        return step2_data_list
    
    ref_to_start = ref_to_match.end()
    
    # 查找 "," 的位置（在 "REF TO " 之后）
    comma_pos = stepEnDesc.find(',', ref_to_start)
    
    if comma_pos == -1:
        if action_word:
            new_stepEnDesc = f"REF TO {cmm_refer}, {action_word} {jcendesc_processed}".strip()
            print("[处理stepEnDesc] 未找到 ','，使用默认模板生成")
            print(f"[处理stepEnDesc] 修改后内容: {new_stepEnDesc}")
            return _replace_step_en_desc(new_stepEnDesc)
        print("[处理stepEnDesc] 未找到 ','，跳过处理")
        return step2_data_list
    
    # 提取 "," 之后的第一个单词
    after_comma = stepEnDesc[comma_pos + 1:].strip()
    first_word_match = re.match(r'(\S+)', after_comma)
    
    if not first_word_match:
        if action_word:
            new_stepEnDesc = f"REF TO {cmm_refer}, {action_word} {jcendesc_processed}".strip()
            print("[处理stepEnDesc] 未找到 ',' 后的第一个单词，使用默认模板生成")
            print(f"[处理stepEnDesc] 修改后内容: {new_stepEnDesc}")
            return _replace_step_en_desc(new_stepEnDesc)
        print("[处理stepEnDesc] 未找到 ',' 后的第一个单词，跳过处理")
        return step2_data_list
    
    first_word = first_word_match.group(1)
    
    # 构建新的 stepEnDesc
    # 1. "REF TO " 之前的部分
    before_ref_to = stepEnDesc[:ref_to_match.start()]
    
    # 2. "REF TO " + CMM_REFER + ","
    new_ref_part = f"REF TO {cmm_refer},"
    
    # 3. 第一个单词 + jcendesc处理后的内容
    new_after_comma = f"{first_word} {jcendesc_processed}".strip()
    
    # 组合新内容
    new_stepEnDesc = before_ref_to + new_ref_part + " " + new_after_comma
    
    print(f"[处理stepEnDesc] 修改后内容: {new_stepEnDesc}")
    
    # 更新 step2_data_list
    return _replace_step_en_desc(new_stepEnDesc)

def fetch_step3(step2_data_list, raw_cookies, wo_rid=None, jc_rid=None, jc_seq=None, step2_response_cookies=None, session=None, original_step_en_desc=None):
    """
    Step 3: POST request to updateJCSTP.jsp
    Uses scraped data from Step 2 directly as the payload.
    
    Args:
        step2_data_list: 从Step 2获取的表单数据列表
        raw_cookies: Cookie字符串
        wo_rid: 工单ID（用于构建Referer）
        jc_rid: 工卡ID（用于构建Referer）
        jc_seq: 工卡序列号（用于构建Referer）
        step2_response_cookies: Step 2返回的Cookie列表
        session: requests.Session对象，用于保持会话状态
    """
    import time
    
    # ========== 检查 step 字段，如果值为 '2'，拒绝执行 ==========
    for name, value in step2_data_list:
        if name == 'step' and str(value).strip() == '2':
            print("\n" + "="*80)
            print("[Step 3] ✗ 拒绝执行！")
            print("="*80)
            print(f"[Step 3] 检测到 step 字段值为 '2'，不支持修改第2步骤")
            print("[Step 3] 当前脚本仅支持修改第1步骤 (step=1)")
            print("="*80)
            return None
    
    # ========== 确保 jc_rid 有值（从 step2_data_list 中提取 primaryJC 作为备用）==========
    # 如果 jc_rid 参数为空，尝试从 step2_data_list 中提取 primaryJC
    if not jc_rid:
        print("[Step 3] jc_rid 参数为空，尝试从 step2_data_list 中提取 primaryJC...")
        for name, value in step2_data_list:
            if name == 'primaryJC' and value:
                jc_rid = value
                print(f"[Step 3] ✓ 从 step2_data_list 中提取到 jc_rid (primaryJC): {jc_rid}")
                break
        if not jc_rid:
            print("[Step 3] ⚠ 警告: 无法获取 jc_rid，中间请求可能会失败")
    
    # 根据USE_VPN选择URL和配置
    if USE_VPN:
        # VPN访问模式
        intranet_path = "trace/fgm/workOrder/jobcard/updateJCSTP.jsp"
        url_step3 = build_vpn_url(intranet_path)
        
        # 构建Referer URL（包含查询参数，与HAR文件一致）
        referer_path = "trace/fgm/workOrder/jobcard/alterJCSTPNRC.jsp"
        referer_base = build_vpn_url(referer_path)
        
        # 如果提供了参数，构建完整的Referer URL（包含查询参数）
        if wo_rid and jc_rid and jc_seq:
            dt_val = str(int(time.time() * 1000))
            referer_params = {
                "wgp": "3_CABIN_TPG",
                "jcrid": jc_rid,
                "woRid": wo_rid,
                "jcType": "NR",
                "jcSeq": jc_seq,
                "jcmode": "E",
                "ownerCode": "EK",
                "eSign": "",
                "flagEPrt": "",
                "txtMenuID": "22800",
                "_dt": dt_val
            }
            referer_query = "&".join([f"{k}={v}" for k, v in referer_params.items()])
            referer = f"{referer_base}?{referer_query}"
        else:
            referer = referer_base
        
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Cache-Control": "max-age=0",  # HAR文件中包含此header，用于禁用缓存
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": VPN_HOST,
            "Origin": f"https://{VPN_HOST}",
            "Referer": referer,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
            "sec-ch-ua": '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "iframe",  # HAR文件中是iframe（表单提交到iframe），不是document
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1"
        }
        print(f"[Step 3 VPN模式] Preparing POST request to {url_step3}...")
    else:
        # 内网直连模式
        url_step3 = "http://10.240.2.131:9080/trace/fgm/workOrder/jobcard/updateJCSTP.jsp"
        
        # 构建Referer URL（包含查询参数）
        referer_base = "http://10.240.2.131:9080/trace/fgm/workOrder/jobcard/alterJCSTPNRC.jsp"
        if wo_rid and jc_rid and jc_seq:
            dt_val = str(int(time.time() * 1000))
            referer_params = {
                "wgp": "3_CABIN_TPG",
                "jcrid": jc_rid,
                "woRid": wo_rid,
                "jcType": "NR",
                "jcSeq": jc_seq,
                "jcmode": "E",
                "ownerCode": "EK",
                "eSign": "",
                "flagEPrt": "",
                "txtMenuID": "22800",
                "_dt": dt_val
            }
            referer_query = "&".join([f"{k}={v}" for k, v in referer_params.items()])
            referer = f"{referer_base}?{referer_query}"
        else:
            referer = referer_base
        
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": "10.240.2.131:9080",
            "Origin": "http://10.240.2.131:9080",
            "Referer": referer,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
        }
        print(f"[Step 3 内网直连模式] Preparing POST request to {url_step3}...")
    
    query_params = {
        "sdrrFlag": "false",
        "flag41": "true"
    }
    
    # Start with required fields that may not be in Step 2 form
    final_payload = []
    url_added = False
    
    # 记录Step 2原始stepEnDesc，便于判断是否修改
    if original_step_en_desc is None:
        for name, value in step2_data_list:
            if name == 'stepEnDesc':
                original_step_en_desc = value
                break
    
    # Add Step 2 data, preserving order and repeated fields
    for name, value in step2_data_list:
        if not name:
            continue
            
        # Override specific fields if needed
        if name == 'url':
            # 避免重复url字段，若为空则补默认值
            if not value:
                value = "alterJCSTPNRC.jsp"
            if url_added:
                continue
            url_added = True
        if name == 'stepEnDesc':
            # 如果处理后与原值不同，标记为已修改
            if original_step_en_desc is None or value != original_step_en_desc:
                step_desc_overridden = True
        if name == 'all_N':
            # 按浏览器提交行为，不传该控制字段
            continue
        if name == 'cb_prt_mat' and not value:
            # checkbox 按浏览器成功提交的值
            value = "on"
        
        final_payload.append((name, value))
    
    # 如果Step 2没有url字段，补一个默认值并放到最前
    if not url_added:
        final_payload.insert(0, ("url", "alterJCSTPNRC.jsp"))
    
    # Add final static fields only if missing (避免重复)
    def _append_if_missing(field_name, field_value):
        for n, _ in final_payload:
            if n == field_name:
                return
        final_payload.append((field_name, field_value))
    
    _append_if_missing("checkStepExist", "true")
    _append_if_missing("txtMenuID", "22800")
    _append_if_missing("nrcHdPrt", "")

    # 如果我们强制修改了 stepEnDesc，则标记为步骤已修改
    if 'step_desc_overridden' in locals() and step_desc_overridden:
        # 从 step2_data_list 中查找 updatedBy 的值
        updated_by_value = None
        for name, value in step2_data_list:
            if name == 'updatedBy':
                updated_by_value = value
                break
        
        # 如果 step2_data_list 中没有 updatedBy，尝试从 final_payload 中查找（可能已经包含）
        if updated_by_value is None:
            for name, value in final_payload:
                if name == 'updatedBy':
                    updated_by_value = value
                    break
        
        def _set_or_append(field_name, field_value):
            for i, (n, _) in enumerate(final_payload):
                if n == field_name:
                    final_payload[i] = (field_name, field_value)
                    return
            final_payload.append((field_name, field_value))
        
        _set_or_append("isupd", "true")
        _set_or_append("onlyUpdStep", "true")
        
        # 使用从 Step 2 响应中获取的 updatedBy 值
        if updated_by_value:
            _set_or_append("updatedBy", updated_by_value)
            print(f"[Step 3] 使用从 Step 2 响应中获取的 updatedBy 值: {updated_by_value}")
        else:
            print("[Step 3] ⚠ 警告: Step 2 响应中未找到 updatedBy 字段，保持现有值")
        
        _set_or_append("editorGrp", "3_CABIN_TPG")
    
    print(f"[Step 3] Payload constructed with {len(final_payload)} fields.")

    # 输出关键字段的值，确认修改是否正确
    print("\n[Step 3] 提交的关键字段值:")
    print("="*80)
    key_fields_to_check = ['stepEnDesc', 'jcendesc', 'transferRemark', 'jcVid']
    for name, value in final_payload:
        if name in key_fields_to_check:
            print(f"  {name}: {value}")
    print("="*80)
    
    # 查找 stepEnDesc 字段
    stepEnDesc_value = None
    for name, value in final_payload:
        if name == 'stepEnDesc':
            stepEnDesc_value = value
            break
    
    if stepEnDesc_value:
        print(f"\n[Step 3] 确认提交的 stepEnDesc 值:")
        print(f"  {stepEnDesc_value}")
    else:
        print("\n[Step 3] 警告: 未在payload中找到 stepEnDesc 字段")

    # 合并原始Cookie和Step 2响应中的新Cookie（以Step 2为准覆盖同名Cookie）
    combined_cookies = raw_cookies.strip() if raw_cookies else ""
    
    def _parse_cookie_pairs(cookie_str):
        pairs = []
        if not cookie_str:
            return pairs
        for part in cookie_str.split(';'):
            part = part.strip()
            if not part or '=' not in part:
                continue
            name, value = part.split('=', 1)
            pairs.append((name.strip(), value.strip()))
        return pairs
    
    combined_pairs = _parse_cookie_pairs(combined_cookies)
    
    # 如果Step 2返回了新的Cookie，合并它们（同名覆盖）
    if step2_response_cookies:
        print(f"\n[Step 3] Step 2返回了 {len(step2_response_cookies)} 个新Cookie")
        for cookie_str in step2_response_cookies:
            # 从Set-Cookie头中提取cookie名称和值
            # Set-Cookie格式: name=value; Path=/; Domain=...
            cookie_parts = cookie_str.split(';')[0].strip()  # 只取第一部分（name=value）
            if '=' in cookie_parts:
                cookie_name = cookie_parts.split('=')[0].strip()
                cookie_value = cookie_parts.split('=', 1)[1].strip()
                
                # 移除已存在的同名Cookie（不区分大小写），再追加新值
                before_len = len(combined_pairs)
                combined_pairs = [
                    (name, value)
                    for name, value in combined_pairs
                    if name.lower() != cookie_name.lower()
                ]
                if len(combined_pairs) < before_len:
                    print(f"  Cookie {cookie_name} 已存在，使用Step 2返回的新值覆盖")
                else:
                    print(f"  ✓ 添加新Cookie: {cookie_name}={cookie_value[:50]}...")
                
                combined_pairs.append((cookie_name, cookie_value))
    else:
        print(f"\n[Step 3] Step 2未返回新Cookie，使用原始Cookie")
    
    if combined_pairs:
        combined_cookies = "; ".join([f"{name}={value}" for name, value in combined_pairs])
    
    # 直接设置Cookie头（仅在未传入session时使用）
    if combined_cookies:
        if session:
            cookie_domain = VPN_HOST if USE_VPN else "10.240.2.131"
            apply_cookie_string_to_session(session, combined_cookies, domain=cookie_domain)
        else:
            headers['Cookie'] = combined_cookies
        print(f"\n[Step 3] 最终使用的Cookie（前200字符）: {combined_cookies[:200]}...")
        print(f"[Step 3] Cookie总长度: {len(combined_cookies)} 字符")
        
        # 统计Cookie项数
        cookie_count = len([c for c in combined_cookies.split(';') if c.strip()])
        print(f"[Step 3] Cookie项数: {cookie_count}")
    else:
        print("\n[Step 3] ⚠⚠⚠ WARNING: Cookie为空！这会导致身份验证失败！")
    
    # 使用传入的session或创建新的
    request_session = session if session else requests

    # ========== Step 3.1: 执行 checkQAAuth 身份验证 ==========
    print("\n" + "="*80)
    print("[Step 3.1] 执行 checkQAAuth 身份验证")
    print("="*80)
    
    # 构建checkQAAuth URL
    if USE_VPN:
        check_auth_path = "trace/fgm/fgm.do"
        # 中间请求需要使用CVPNOrg=abs和CVPNTransDest=0
        check_auth_url = build_vpn_url(check_auth_path, use_abs=True, include_trans_dest=True)
    else:
        check_auth_url = "http://10.240.2.131:9080/trace/fgm/fgm.do"
    
    # 构建checkQAAuth的Referer（与Step 3的Referer相同）
    # 确保referer变量已定义
    if USE_VPN:
        # VPN模式下，referer已经在上面定义
        check_auth_referer = referer
    else:
        # 内网模式下，referer也在上面定义
        check_auth_referer = referer
    
    # checkQAAuth请求参数
    dt_val_auth = str(int(time.time() * 1000))
    check_auth_params = {
        "method": "checkQAAuth",
        "_": dt_val_auth,
        "txtMenuID": "22800"
    }
    
    # checkQAAuth请求headers
    check_auth_headers = {
        "Accept": "application/json, text/javascript, */*",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded",
        "Host": VPN_HOST if USE_VPN else "10.240.2.131:9080",
        "Referer": check_auth_referer,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    # 设置Cookie
    if combined_cookies:
        check_auth_headers['Cookie'] = combined_cookies
    
    print(f"[Step 3.1] 发送checkQAAuth请求到: {check_auth_url}")
    print(f"[Step 3.1] 请求参数: {check_auth_params}")
    
    try:
        auth_response = request_session.get(check_auth_url, params=check_auth_params, headers=check_auth_headers, timeout=15, verify=False)
        auth_response.encoding = 'GBK'
        print(f"[Step 3.1] Response Status: {auth_response.status_code}")
        print(f"[Step 3.1] Response Length: {len(auth_response.text)}")
        
        if auth_response.status_code != 200:
            print("[Step 3.1] ✗ checkQAAuth请求失败，HTTP状态码异常")
            print("[Step 3.1] 将跳过身份验证，继续执行Step 3（可能失败）")
        else:
            # 解析响应（应该是JSON格式）
            try:
                import json
                auth_result = json.loads(auth_response.text)
                print(f"[Step 3.1] 响应内容: {auth_result}")
                
                if auth_result.get('flag') == True:
                    print("[Step 3.1] ✓ 身份验证成功！")
                    print(f"[Step 3.1] 用户: {auth_result.get('user', 'N/A')}")
                else:
                    print("[Step 3.1] ✗ 身份验证失败！flag不为true")
                    print("[Step 3.1] 将尝试继续执行Step 3（可能失败）")
            except json.JSONDecodeError:
                print(f"[Step 3.1] ⚠ 响应不是有效的JSON格式")
                print(f"[Step 3.1] 响应内容: {auth_response.text[:200]}")
                print("[Step 3.1] 将尝试继续执行Step 3")
    except Exception as e:
        print(f"[Step 3.1] ✗ checkQAAuth请求异常: {e}")
        print("[Step 3.1] 将尝试继续执行Step 3（可能失败）")
    
    print("="*80)
    
    # ========== Step 3.2: 执行 countAmtSignByJcRid (POST) ==========
    print("\n" + "="*80)
    print("[Step 3.2] 执行 countAmtSignByJcRid (POST)")
    print("="*80)
    
    if not jc_rid:
        print("[Step 3.2] ⚠ 警告: jc_rid 为空，跳过此请求")
    else:
        # 构建 countAmtSignByJcRid URL
        if USE_VPN:
            # 中间请求需要使用CVPNOrg=abs和CVPNTransDest=0
            count_amt_url = build_vpn_url("trace/fgm/fgm.do", use_abs=True, include_trans_dest=True)
        else:
            count_amt_url = "http://10.240.2.131:9080/trace/fgm/fgm.do"
        
        # countAmtSignByJcRid 请求参数（在 URL 中）
        count_amt_params = {
            "method": "countAmtSignByJcRid"
        }
        
        # countAmtSignByJcRid 请求 body（POST 数据）
        count_amt_data = {
            "jcRid": jc_rid,
            "txtMenuID": "22800"
        }
        
        # countAmtSignByJcRid 请求 headers
        count_amt_headers = {
            "Accept": "application/json, text/javascript, */*",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "Host": VPN_HOST if USE_VPN else "10.240.2.131:9080",
            "Origin": f"https://{VPN_HOST}" if USE_VPN else "http://10.240.2.131:9080",
            "Referer": check_auth_referer if 'check_auth_referer' in locals() else referer,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest"
        }
        
        # 设置Cookie
        if combined_cookies:
            count_amt_headers['Cookie'] = combined_cookies
        
        print(f"[Step 3.2] 发送 countAmtSignByJcRid POST 请求到: {count_amt_url}")
        print(f"[Step 3.2] URL参数: {count_amt_params}")
        print(f"[Step 3.2] POST数据: {count_amt_data}")
        
        try:
            count_amt_response = request_session.post(
                count_amt_url, 
                params=count_amt_params, 
                data=count_amt_data, 
                headers=count_amt_headers, 
                timeout=15, 
                verify=False
            )
            count_amt_response.encoding = 'GBK'
            print(f"[Step 3.2] Response Status: {count_amt_response.status_code}")
            print(f"[Step 3.2] Response Length: {len(count_amt_response.text)}")
            
            if count_amt_response.status_code == 200:
                try:
                    import json
                    count_amt_result = json.loads(count_amt_response.text)
                    print(f"[Step 3.2] ✓ 响应内容: {count_amt_result}")
                except json.JSONDecodeError:
                    print(f"[Step 3.2] ⚠ 响应不是有效的JSON格式: {count_amt_response.text[:200]}")
            else:
                print(f"[Step 3.2] ✗ HTTP状态码异常: {count_amt_response.status_code}")
        except Exception as e:
            print(f"[Step 3.2] ✗ countAmtSignByJcRid请求异常: {e}")
    
    print("="*80)
    
    # ========== Step 3.3: 执行 checkHasLockStep (GET) ==========
    print("\n" + "="*80)
    print("[Step 3.3] 执行 checkHasLockStep (GET)")
    print("="*80)
    
    if not jc_rid:
        print("[Step 3.3] ⚠ 警告: jc_rid 为空，跳过此请求")
    else:
        # 构建 checkHasLockStep URL
        if USE_VPN:
            # 中间请求需要使用CVPNOrg=abs和CVPNTransDest=0
            check_lock_url = build_vpn_url("trace/fgm/fgm.do", use_abs=True, include_trans_dest=True)
        else:
            check_lock_url = "http://10.240.2.131:9080/trace/fgm/fgm.do"
        
        # checkHasLockStep 请求参数
        dt_val_lock = str(int(time.time() * 1000))
        check_lock_params = {
            "method": "checkHasLockStep",
            "_": dt_val_lock,
            "jcRid": jc_rid,
            "txtMenuID": "22800"
        }
        
        # checkHasLockStep 请求 headers
        check_lock_headers = {
            "Accept": "application/json, text/javascript, */*",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": VPN_HOST if USE_VPN else "10.240.2.131:9080",
            "Referer": check_auth_referer if 'check_auth_referer' in locals() else referer,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest"
        }
        
        # 设置Cookie
        if combined_cookies:
            check_lock_headers['Cookie'] = combined_cookies
        
        print(f"[Step 3.3] 发送 checkHasLockStep GET 请求到: {check_lock_url}")
        print(f"[Step 3.3] 请求参数: {check_lock_params}")
        
        try:
            check_lock_response = request_session.get(
                check_lock_url, 
                params=check_lock_params, 
                headers=check_lock_headers, 
                timeout=15, 
                verify=False
            )
            check_lock_response.encoding = 'GBK'
            print(f"[Step 3.3] Response Status: {check_lock_response.status_code}")
            print(f"[Step 3.3] Response Length: {len(check_lock_response.text)}")
            
            if check_lock_response.status_code == 200:
                try:
                    import json
                    check_lock_result = json.loads(check_lock_response.text)
                    print(f"[Step 3.3] ✓ 响应内容: {check_lock_result}")
                except json.JSONDecodeError:
                    print(f"[Step 3.3] ⚠ 响应不是有效的JSON格式: {check_lock_response.text[:200]}")
            else:
                print(f"[Step 3.3] ✗ HTTP状态码异常: {check_lock_response.status_code}")
        except Exception as e:
            print(f"[Step 3.3] ✗ checkHasLockStep请求异常: {e}")
    
    print("="*80)
    
    # ========== Step 3.4: 执行 getNrcHdPrtStatus (GET) ==========
    print("\n" + "="*80)
    print("[Step 3.4] 执行 getNrcHdPrtStatus (GET)")
    print("="*80)
    
    if not jc_rid:
        print("[Step 3.4] ⚠ 警告: jc_rid 为空，跳过此请求")
    else:
        # 构建 getNrcHdPrtStatus URL
        if USE_VPN:
            # 中间请求需要使用CVPNOrg=abs和CVPNTransDest=0
            get_nrc_url = build_vpn_url("trace/fgm/fgm.do", use_abs=True, include_trans_dest=True)
        else:
            get_nrc_url = "http://10.240.2.131:9080/trace/fgm/fgm.do"
        
        # getNrcHdPrtStatus 请求参数
        get_nrc_params = {
            "method": "getNrcHdPrtStatus",
            "jcRid": jc_rid,
            "txtMenuID": "22800"
        }
        
        # getNrcHdPrtStatus 请求 headers
        get_nrc_headers = {
            "Accept": "application/json, text/javascript, */*",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": VPN_HOST if USE_VPN else "10.240.2.131:9080",
            "Referer": check_auth_referer if 'check_auth_referer' in locals() else referer,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest"
        }
        
        # 设置Cookie
        if combined_cookies:
            get_nrc_headers['Cookie'] = combined_cookies
        
        print(f"[Step 3.4] 发送 getNrcHdPrtStatus GET 请求到: {get_nrc_url}")
        print(f"[Step 3.4] 请求参数: {get_nrc_params}")
        print("[Step 3.4] 注意: 此请求可能需要较长时间（约300ms）")
        
        try:
            get_nrc_response = request_session.get(
                get_nrc_url, 
                params=get_nrc_params, 
                headers=get_nrc_headers, 
                timeout=15, 
                verify=False
            )
            get_nrc_response.encoding = 'GBK'
            print(f"[Step 3.4] Response Status: {get_nrc_response.status_code}")
            print(f"[Step 3.4] Response Length: {len(get_nrc_response.text)}")
            
            if get_nrc_response.status_code == 200:
                try:
                    import json
                    get_nrc_result = json.loads(get_nrc_response.text)
                    print(f"[Step 3.4] ✓ 响应内容: {get_nrc_result}")
                    
                    # 如果响应中包含 nrcHdPrt，可以更新到 payload 中
                    if isinstance(get_nrc_result, dict) and 'nrcHdPrt' in get_nrc_result:
                        nrc_hd_prt_value = get_nrc_result.get('nrcHdPrt', '')
                        # 更新 final_payload 中的 nrcHdPrt 字段
                        for i, (name, value) in enumerate(final_payload):
                            if name == 'nrcHdPrt':
                                final_payload[i] = (name, nrc_hd_prt_value)
                                print(f"[Step 3.4] ✓ 更新 final_payload 中的 nrcHdPrt 为: {nrc_hd_prt_value}")
                                break
                except json.JSONDecodeError:
                    print(f"[Step 3.4] ⚠ 响应不是有效的JSON格式: {get_nrc_response.text[:200]}")
            else:
                print(f"[Step 3.4] ✗ HTTP状态码异常: {get_nrc_response.status_code}")
        except Exception as e:
            print(f"[Step 3.4] ✗ getNrcHdPrtStatus请求异常: {e}")
    
    print("="*80)

    # Encode to GBK for Chinese characters
    try:
        import urllib.parse
        encoded_body = urllib.parse.urlencode(final_payload, encoding='gbk')
        print(f"\n[Step 3] Payload编码完成，长度: {len(encoded_body)} 字符")
    except Exception as e:
        print(f"Encoding error: {e}")
        return

    # 调试：输出请求的关键信息
    print(f"\n[Step 3] 请求调试信息:")
    print(f"  URL: {url_step3}")
    print(f"  Query Params: {query_params}")
    print(f"  paybody: {encoded_body}")
    print(f"  Referer: {headers.get('Referer', 'N/A')[:150]}")
    print(f"  Cookie in headers: {headers.get('Cookie', 'N/A')[:150]}")
    print(" step 3 headers beginning")
    print(headers," step 3 headers")
    try:
        # 使用传入的session或创建新的，Cookie已在headers中设置
        response = request_session.post(url_step3, params=query_params, data=encoded_body, headers=headers, timeout=30, verify=False)
        response.encoding = 'GBK'
        print(f"[Step 3] Response Status: {response.status_code}")
        print(f"[Step 3] Response Length: {len(response.text)}")
        print(f"[Step 3] Response URL: {response.url}")
        if response.history:
            print("[Step 3] Redirect history:")
            for idx, hist in enumerate(response.history):
                location = hist.headers.get("Location", "")
                print(f"  {idx+1}. {hist.status_code} -> {location}")
        
        # 保存完整响应到文件
        try:
            with open('response_step3.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            print(f"[Step 3] 完整响应已保存到: response_step3.html")
        except Exception as e:
            print(f"[Step 3] 保存响应文件失败: {e}")
        
        # 检查是否被重定向到登录页（身份验证失败）
        if "j_acegi_security_check" in response.text or "loginCode" in response.text or "验证码" in response.text or "登录" in response.text[:500]:
            print("[Step 3] ERROR: 检测到登录页面，身份验证失败！")
            print("[Step 3] 可能原因：Cookie无效或已过期")
            print(f"[Step 3] 响应内容预览: {response.text[:1000]}")
            return
        
        # 输出响应内容的关键部分
        print("\n" + "="*80)
        print("[Step 3] 响应内容预览（前5000字符）:")
        print("="*80)
        print(response.text[:5000])
        print("="*80)
        
        # 检查响应中是否包含成功或失败的提示
        # 改进：检查URL中的message参数（HAR文件中显示成功后会重定向到包含message的URL）
        import urllib.parse
        # re模块已在文件开头导入，直接使用
        parsed_url = urllib.parse.urlparse(response.url)
        url_params = urllib.parse.parse_qs(parsed_url.query)
        
        print("\n[Step 3] 响应内容分析:")
        found_success = False
        found_error = False
        
        # 检查URL中的message参数（最可靠的成功/失败指示）
        if 'message' in url_params:
            message = urllib.parse.unquote(url_params['message'][0])
            print(f"  URL中的message参数: {message}")
            if "成功" in message or "保存" in message:
                found_success = True
                print(f"  ✓ 从URL参数检测到成功: {message}")
            elif "失败" in message or "错误" in message:
                found_error = True
                print(f"  ✗ 从URL参数检测到失败: {message}")
        
        # 检查响应文本中的实际成功消息（不在script标签内）
        success_patterns = [
            r'保存成功',
            r'更新成功',
            r'修改成功',
            r'message[=:]["\']?[^"\']*成功',
            r'alert\(["\'][^"\']*成功',
        ]
        
        for pattern in success_patterns:
            matches = re.finditer(pattern, response.text, re.IGNORECASE)
            for match in matches:
                # 检查是否在script标签内
                match_start = match.start()
                # 查找最近的<script>和</script>标签
                before_text = response.text[:match_start]
                script_start = before_text.rfind('<script')
                script_end = before_text.rfind('</script>')
                
                # 如果最近的<script>标签在</script>之后，说明不在script内
                if script_start == -1 or (script_end != -1 and script_start < script_end):
                    print(f"  ✓ 找到成功消息: {match.group()[:100]}")
                    found_success = True
                    break
        
        # 检查响应文本中的实际错误消息（不在script标签内，且是实际的错误提示）
        error_patterns = [
            r'保存失败',
            r'更新失败',
            r'操作失败',
            r'错误[：:][^<]+',
            r'errorMsgDIV[^>]*>([^<]+)',
            r'alert\(["\'][^"\']*失败',
            r'message[=:]["\']?[^"\']*失败',
        ]
        
        for pattern in error_patterns:
            matches = re.finditer(pattern, response.text, re.IGNORECASE)
            for match in matches:
                # 检查是否在script标签内
                match_start = match.start()
                before_text = response.text[:match_start]
                script_start = before_text.rfind('<script')
                script_end = before_text.rfind('</script>')
                
                # 如果最近的<script>标签在</script>之后，说明不在script内
                if script_start == -1 or (script_end != -1 and script_start < script_end):
                    error_msg = match.group(1) if match.groups() else match.group()
                    print(f"  ✗ 找到错误消息: {error_msg[:100]}")
                    found_error = True
                    # 显示更多上下文
                    start = max(0, match_start - 50)
                    end = min(len(response.text), match_start + len(error_msg) + 50)
                    context = response.text[start:end].replace('\n', ' ').replace('\r', ' ')
                    print(f"    上下文: ...{context}...")
                    break
        
        # 检查是否有重定向到成功页面（HAR文件中显示成功后会重定向）
        if 'alterJCSTPNRC.jsp' in response.url and 'message=' in response.url:
            print(f"  ✓ 检测到重定向到alterJCSTPNRC.jsp（通常表示成功）")
            if not found_error:
                found_success = True
        
        # 检查 stepEnDesc 是否在响应中（确认修改是否生效）
        print("\n[Step 3] 检查 stepEnDesc 修改是否生效:")
        if 'stepEnDesc' in response.text.lower():
            # 查找 stepEnDesc 相关的内容
            # re模块已在文件开头导入，直接使用
            stepEnDesc_patterns = [
                r'stepEnDesc["\']?\s*[:=]\s*["\']?([^"\']+)',
                r'name=["\']stepEnDesc["\'][^>]*value=["\']?([^"\']+)',
                r'stepEnDesc[^>]*>([^<]+)',
            ]
            for pattern in stepEnDesc_patterns:
                matches = re.finditer(pattern, response.text, re.IGNORECASE)
                for match in matches:
                    value = match.group(1) if match.groups() else match.group(0)
                    print(f"  找到 stepEnDesc 相关内容: {value[:200]}")
        else:
            print("  未在响应中找到 stepEnDesc 相关内容")
        
        # 检查响应中是否包含提交的数据
        print("\n[Step 3] 检查提交的数据是否在响应中:")
        # 检查一些关键字段
        key_fields = ['transferRemark', 'stepEnDesc', 'jcendesc']
        for field in key_fields:
            if field in response.text:
                print(f"  ✓ 响应中包含字段: {field}")
            else:
                print(f"  ✗ 响应中未找到字段: {field}")
        
        # 检查响应URL（成功后会重定向）
        print(f"\n[Step 3] 响应URL: {response.url}")
        if 'alterJCSTPNRC.jsp' in response.url:
            print("  ✓ 响应URL包含alterJCSTPNRC.jsp（成功后会重定向到此页面）")
            if 'message=' in response.url:
                message_param = urllib.parse.parse_qs(urllib.parse.urlparse(response.url).query).get('message', [''])[0]
                if message_param:
                    decoded_message = urllib.parse.unquote(message_param)
                    print(f"  URL中的message: {decoded_message}")
                    if "成功" in decoded_message:
                        found_success = True
                        print("  ✓ 从URL message参数确认操作成功")
                    elif "失败" in decoded_message or "错误" in decoded_message:
                        found_error = True
                        print("  ✗ 从URL message参数确认操作失败")
        
        print("\n" + "="*80)
        
        if response.status_code == 200:
            if found_success and not found_error:
                print("[Step 3] ✓✓✓ 操作成功！")
            elif found_error:
                print("[Step 3] ✗✗✗ 操作失败！")
                print("请检查 response_step3.html 文件查看详细错误信息")
            elif found_success and found_error:
                print("[Step 3] ⚠ 检测到成功和失败信号，请检查 response_step3.html 文件确认")
            else:
                print("[Step 3] ? 无法从响应中明确判断操作结果")
                print("请检查 response_step3.html 文件")
                print(f"响应URL: {response.url}")
        else:
            print(f"[Step 3] ✗ HTTP状态码异常: {response.status_code}")

    except Exception as e:
        print(f"Step 3 Error: {e}")


if __name__ == "__main__":
    # 输入参数（用户设定值）
    SaleWo = "120000587070"
    ACNo = "A6-EUD"
    jc_seq = "51100"  # 用户设定的jcSeq值，整个流程都使用这个值
    CMM_REFER = "CMM 25-06-35 REV.____"
    # ACTION = "REINSTALL"  # 已取消，不再使用
    
    # 创建共享的Session，保持Cookie状态
    shared_session = requests.Session()
    cookies_to_use = VPN_COOKIES if USE_VPN else COOKIES
    if cookies_to_use:
        base_domain = VPN_HOST if USE_VPN else "10.240.2.131"
        apply_cookie_string_to_session(shared_session, cookies_to_use.strip(), domain=base_domain)
        print(f"[全局Session] 已写入Cookie到session: {cookies_to_use.strip()[:100]}...")
    
    # Step 0: 通过HTTP请求获取jc_workorder_input
    print("="*80)
    print("Step 0: 获取jc_workorder_input")
    print("="*80)
    print(f"使用参数: SaleWo={SaleWo}, ACNo={ACNo}, jcSeq={jc_seq}")
    jc_workorder_input = fetch_jc_workorder(SaleWo, ACNo, jc_seq, session=shared_session)
    
    if not jc_workorder_input:
        print("ERROR: 无法获取jc_workorder_input，程序终止")
        exit(1)
    
    print(f"\n成功获取 jc_workorder_input: {jc_workorder_input}")
    print("="*80)
    
    # Step 1: 使用获取到的jc_workorder_input调用fetch_ids
    print("\n" + "="*80)
    print("Step 1: 获取woRid和jcRid")
    print("="*80)
    wo_rid, jc_rid, _ = fetch_ids(jc_workorder_input, session=shared_session)
    
    if wo_rid and jc_rid:
        # jc_seq 使用用户设定的值，不从Step 1获取
        print(f"使用用户设定的jcSeq: {jc_seq}")
        
        # Step 2: 获取表单数据
        print("\n" + "="*80)
        print("Step 2: 获取表单数据")
        print("="*80)
        cookies_to_use = VPN_COOKIES if USE_VPN else COOKIES
        step2_result = fetch_step2(wo_rid, jc_rid, jc_seq, cookies_to_use, session=shared_session)
        
        # 处理返回结果（可能是列表或元组）
        if isinstance(step2_result, tuple) and len(step2_result) == 2:
            step2_data, step2_response_cookies = step2_result
        else:
            # 兼容旧版本（如果没有返回Cookie）
            step2_data = step2_result
            step2_response_cookies = []
        
        print(step2_data)
        
        # 处理 stepEnDesc 字段
        print("\n" + "="*80)
        print("处理 stepEnDesc 字段")
        print("="*80)
        original_step_en_desc = None
        for name, value in step2_data:
            if name == 'stepEnDesc':
                original_step_en_desc = value
                break
        step2_data_processed = process_stepEnDesc(step2_data, CMM_REFER)
        
        # Step 3: 提交数据
        print("\n" + "="*80)
        print("Step 3: 提交数据")
        print("="*80)
        cookies_to_use = VPN_COOKIES if USE_VPN else COOKIES
        fetch_step3(
            step2_data_processed,
            cookies_to_use,
            wo_rid,
            jc_rid,
            jc_seq,
            step2_response_cookies,
            session=shared_session,
            original_step_en_desc=original_step_en_desc
        )
        
        # Step 1 验证: 在Step 3之后再次执行Step 1，验证会话是否仍然有效
        print("\n" + "="*80)
        print("Step 1 验证: 验证会话有效性（执行完Step 3后再次执行Step 1）")
        print("="*80)
        print(f"[验证] 使用相同的参数再次执行 Step 1: jc_workorder={jc_workorder_input}")
        verification_wo_rid, verification_jc_rid, verification_jc_seq = fetch_ids(jc_workorder_input, session=shared_session)
        
        if verification_wo_rid and verification_jc_rid:
            print("\n" + "="*80)
            print("[验证] ✓✓✓ 会话验证成功！")
            print("="*80)
            print(f"[验证] 验证请求返回的 woRid: {verification_wo_rid}")
            print(f"[验证] 验证请求返回的 jcRid: {verification_jc_rid}")
            print(f"[验证] 验证请求返回的 jcSeq: {verification_jc_seq if verification_jc_seq else 'N/A'}")
            print(f"[验证] 原始 Step 1 返回的 woRid: {wo_rid}")
            print(f"[验证] 原始 Step 1 返回的 jcRid: {jc_rid}")
            
            # 比较验证结果和原始结果
            if verification_wo_rid == wo_rid and verification_jc_rid == jc_rid:
                print("[验证] ✓ 验证结果与原始结果一致，会话有效且稳定")
            else:
                print("[验证] ⚠ 验证结果与原始结果不一致")
                print(f"[验证]   - woRid 是否一致: {verification_wo_rid == wo_rid}")
                print(f"[验证]   - jcRid 是否一致: {verification_jc_rid == jc_rid}")
            print("="*80)
        else:
            print("\n" + "="*80)
            print("[验证] ✗✗✗ 会话验证失败！")
            print("="*80)
            print("[验证] Step 1 验证请求失败，可能的原因：")
            print("[验证]   1. VPN会话已过期")
            print("[验证]   2. Cookie已失效")
            print("[验证]   3. 服务器端会话已超时")
            print("[验证]   4. 网络连接问题")
            print("[验证]")
            print("[验证] 如果Step 3失败且验证也失败，说明会话在Step 3之前就已经失效")
            print("[验证] 如果Step 3失败但验证成功，说明问题出在Step 3的请求上")
            print("="*80)
        
    else:
        print("\nERROR: 无法获取woRid或jcRid，程序终止")


'''
Request URL
http://10.240.2.131:9080/trace/fgm/fgm.do?method=checkQAAuth&_=1768199499764&txtMenuID=22800
Request Method
GET
Status Code
200 OK
Remote Address
10.240.2.131:9080
Referrer Policy
strict-origin-when-cross-origin

HTTP/1.1 200 OK
Server: Apache-Coyote/1.1
Content-Length: 40
Date: Mon, 12 Jan 2026 06:31:39 GMT

GET /trace/fgm/fgm.do?method=checkQAAuth&_=1768199499764&txtMenuID=22800 HTTP/1.1
Accept: application/json, text/javascript, */*
Accept-Encoding: gzip, deflate
Accept-Language: zh-CN,zh;q=0.9
Connection: keep-alive
Content-Type: application/x-www-form-urlencoded
Cookie: JSESSIONID=AEC54A1657C40236DFC069998BFFA890; JSESSIONID=8C7913AAC93669DDAEF7A024C9CD227B
Host: 10.240.2.131:9080
Referer: http://10.240.2.131:9080/trace/fgm/workOrder/jobcard/alterJCSTPNRC.jsp?wgp=3_CABIN_TPG&jcrid=13015703&woRid=13757566&jcType=NR&jcSeq=50580&jcmode=E&ownerCode=EK&eSign=&flagEPrt=&txtMenuID=22800&_dt=1768199495602
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36
X-Requested-With: XMLHttpRequest




Request URL
https://vpn.gameco.com.cn/Web/trace/security/blank.jsp,CVPNHost=10.240.2.131:9080,CVPNProtocol=http,CVPNOrg=rel,CVPNExtension=.jsp
Request Method
GET
Status Code
200 OK
Remote Address
127.0.0.1:7897
Referrer Policy
strict-origin-when-cross-origin
connection
Keep-Alive
content-type
text/html;charset=GB18030
date
Tue, 13 Jan 2026 01:22:03 GMT
keep-alive
timeout=2, max=100
server
CPWS
strict-transport-security
max-age=31536000; includeSubDomains
transfer-encoding
chunked
vary
User-Agent
x-frame-options
SAMEORIGIN
accept
text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7
accept-encoding
gzip, deflate, br, zstd
accept-language
zh-CN,zh;q=0.9
connection
keep-alive
cookie
selected_realm=ssl_vpn; ___fnbDropDownState=1; CPCVPN_CSHELL_SEQ_MODES=5; AMP_MKTG_5f4c1fb366=JTdCJTdE; CPCVPN_SESSION_ID=af901cec0dd8a2b47475d5e742aa56f186b49cfb; CPCVPN_BASE_HOST=vpn.gameco.com.cn; CPCVPN_OBSCURE_KEY=44c140102fa383f01f645f010c4f4bed; CPCVPN_SDATA_VERSION=6; AMP_5f4c1fb366=JTdCJTIyb3B0T3V0JTIyJTNBZmFsc2UlMkMlMjJkZXZpY2VJZCUyMiUzQSUyMjQ3NGQ3NmVjLWZkYmQtNDkxOS05YTVhLWE3NmY5OTRlMTZlNiUyMiUyQyUyMmxhc3RFdmVudFRpbWUlMjIlM0ExNzY4MjY3MzE0MDY5JTJDJTIyc2Vzc2lvbklkJTIyJTNBMTc2ODI2NzE4NTg5NSUyQyUyMnVzZXJJZCUyMiUzQSUyMmI0OGFlN2UxLWFjNzQtZjlkMi0zNTBmLTUwZjFiZGJhMzkwYSUyMiU3RA==
host
vpn.gameco.com.cn
referer
https://vpn.gameco.com.cn/Web/trace/security/rolesMenu.jsp,CVPNHost=10.240.2.131:9080,CVPNProtocol=http,CVPNOrg=rel,CVPNExtension=.jsp
sec-ch-ua
"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"
sec-ch-ua-mobile
?0
sec-ch-ua-platform
"Windows"
sec-fetch-dest
frame
sec-fetch-mode
navigate
sec-fetch-site
same-origin
sec-fetch-user
?1
upgrade-insecure-requests
1
user-agent
Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36


'''