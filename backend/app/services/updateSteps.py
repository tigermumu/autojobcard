import requests
from bs4 import BeautifulSoup
import re
import urllib3
from typing import Optional

# 禁用SSL警告（VPN访问时可能需要）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 导入配置（与 workcard_import_service 保持一致）
try:
    from app.core.config import settings
    USE_SETTINGS = True
except ImportError:
    # 独立运行时使用本地配置
    USE_SETTINGS = False
    settings = None

# --- Configuration ---
# VPN访问模式配置
USE_VPN = False  # 设置为True使用VPN访问，False使用内网直连

# VPN Cookie（独立运行时的备用配置）
VPN_COOKIES = "selected_realm=ssl_vpn; ___fnbDropDownState=1; CPCVPN_CSHELL_SEQ_MODES=5; AMP_MKTG_5f4c1fb366=JTdCJTdE; CPCVPN_SESSION_ID=d3e32fc0252192d44a9bbb9ca589fa50dce6e1d2; CPCVPN_BASE_HOST=vpn.gameco.com.cn; CPCVPN_OBSCURE_KEY=44c140102fa383f01f645f010c4f4bed; CPCVPN_SDATA_VERSION=5; AMP_5f4c1fb366=JTdCJTIyb3B0T3V0JTIyJTNBZmFsc2UlMkMlMjJkZXZpY2VJZCUyMiUzQSUyMjQ3NGQ3NmVjLWZkYmQtNDkxOS05YTVhLWE3NmY5OTRlMTZlNiUyMiUyQyUyMmxhc3RFdmVudFRpbWUlMjIlM0ExNzY4NjE2MzU2NDY2JTJDJTIyc2Vzc2lvbklkJTIyJTNBMTc2ODYxNjEyNjA1NCUyQyUyMnVzZXJJZCUyMiUzQSUyMmI0OGFlN2UxLWFjNzQtZjlkMi0zNTBmLTUwZjFiZGJhMzkwYSUyMiU3RA=="
# 内网直连模式Cookie（独立运行时的备用配置）
COOKIES = "JSESSIONID=706795ADB33FD9AFC75089C0003F81B1; JSESSIONID=2E150DC00122B5C9DBF0E7354078C8B7" 

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

def get_default_cookies() -> str:
    """
    获取默认 Cookie 配置
    优先使用 settings.WORKCARD_IMPORT_COOKIES（与 workcard_import_service 一致）
    独立运行时使用脚本内的备用配置
    """
    if USE_SETTINGS and settings:
        cookie_str = getattr(settings, 'WORKCARD_IMPORT_COOKIES', '')
        if cookie_str:
            return cookie_str.strip()
    # 独立运行时使用本地配置
    return VPN_COOKIES.strip() if USE_VPN else COOKIES.strip()


def create_session(raw_cookies: Optional[str] = None) -> requests.Session:
    """
    创建 Session 并设置 Cookie（与 workcard_import_service._create_session 一致）
    
    关键：直接将 Cookie 设置到 headers['Cookie']，保留原始字符串
    这样可以正确处理多个同名 JSESSIONID 的情况
    
    Args:
        raw_cookies: Cookie 字符串，如果不提供则使用默认配置
        
    Returns:
        配置好的 requests.Session 对象
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
    })
    
    # 直接设置 Cookie 头，保留所有 Cookie 值（包括同名的多个 JSESSIONID）
    cookie_string = raw_cookies.strip() if raw_cookies else get_default_cookies()
    if cookie_string:
        session.headers['Cookie'] = cookie_string
    
    return session


def apply_cookie_string_to_session(session, cookie_string, domain=None):
    """
    [已废弃] 请使用 create_session() 代替
    保留此函数仅为兼容性考虑
    
    注意：此方法会导致同名 Cookie 被覆盖，不推荐使用
    """
    if not session or not cookie_string:
        return
    # 直接设置到 headers['Cookie']，保留完整字符串
    session.headers['Cookie'] = cookie_string.strip()

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
    
    # Cookie 处理：优先使用 session.headers 中的 Cookie，否则使用默认配置
    if session and 'Cookie' in session.headers:
        headers['Cookie'] = session.headers['Cookie']
    else:
        headers['Cookie'] = get_default_cookies()
    
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
    
    # Cookie 处理：优先使用 session.headers 中的 Cookie，否则使用默认配置
    if session and 'Cookie' in session.headers:
        headers['Cookie'] = session.headers['Cookie']
        print(f"使用 session.headers 中的 Cookie")
    else:
        headers['Cookie'] = get_default_cookies()
        print(f"使用默认 Cookie 配置")

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
    
    # Cookie 处理：优先使用 session.headers 中的 Cookie，其次使用 raw_cookies，最后使用默认配置
    if session and 'Cookie' in session.headers:
        headers['Cookie'] = session.headers['Cookie']
        print(f"[Step 2] 使用 session.headers 中的 Cookie")
    elif raw_cookies:
        headers['Cookie'] = raw_cookies.strip()
        print(f"[Step 2] 使用传入的 raw_cookies: {raw_cookies.strip()[:100]}...")
    else:
        headers['Cookie'] = get_default_cookies()
        print(f"[Step 2] 使用默认 Cookie 配置")

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

def normalize_cmm_refer(cmm_refer: str) -> str:
    """
    将 CMM_REFER 中的最后一位数字替换为 "____"
    
    例如:
        "CMM 25-06-35 REV.1" -> "CMM 25-06-35 REV.____"
        "CMM 25-06-35 REV.123" -> "CMM 25-06-35 REV.____"
        "CMM 25-06-35 REV.____" -> "CMM 25-06-35 REV.____" (不变)
    """
    if not cmm_refer:
        return cmm_refer
    
    # 如果已经以 ____ 结尾，不处理
    if cmm_refer.rstrip().endswith('____'):
        return cmm_refer
    
    # 匹配末尾的数字部分并替换为 ____
    # 支持格式如: REV.1, REV.123, REV 1, REV 123 等
    result = re.sub(r'(\d+)\s*$', '____', cmm_refer)
    
    return result


def process_jcendesc(jcendesc: str) -> str:
    """
    处理 jcendesc 字段：删除最后一个单词
    
    Args:
        jcendesc: 原始 jcendesc 内容
        
    Returns:
        处理后的内容（删除最后一个单词）
    """
    if not jcendesc:
        return ''
    
    words = jcendesc.strip().split()
    if len(words) > 1:
        return ' '.join(words[:-1])
    return ''


def process_stepEnDesc(step2_data_list, cmm_refer, action_word=None):
    """
    处理 stepEnDesc 和 referenceDesc 字段
    
    处理规则：
    1. referenceDesc 字段赋值为 cmm_refer
    2. stepEnDesc 字段修改规则：
       - 识别 "REF TO" 或 "REFER TO" 关键词，统一输出为 "REF TO"
       - "REF TO" 后面到 "," 之间的内容替换成 CMM_REFER（最后一位数字改为 "____"）
       - "," 之后的第一个单词保持不变
       - "," 之后的第一个单词后的内容替换成 jcendesc（删除最后一个单词）
    
    Args:
        step2_data_list: 表单数据列表 [(name, value), ...]
        cmm_refer: 参考手册值
        action_word: 动作词（可选，用于生成默认模板）
        
    Returns:
        处理后的数据列表
    """
    # 将列表转换为字典以便查找
    data_dict = dict(step2_data_list)
    
    # 处理 CMM_REFER：将最后一位数字改为 "____"
    cmm_refer_normalized = normalize_cmm_refer(cmm_refer)
    
    # 处理 jcendesc：删除最后一个单词
    jcendesc = data_dict.get('jcendesc', '')
    jcendesc_processed = process_jcendesc(jcendesc)
    
    def _update_field(data_list, field_name, new_value):
        """更新或添加指定字段"""
        updated_list = []
        replaced = False
        for name, value in data_list:
            if name == field_name:
                updated_list.append((name, new_value))
                replaced = True
            else:
                updated_list.append((name, value))
        if not replaced:
            updated_list.append((field_name, new_value))
        return updated_list
    
    # ===== 1. 处理 referenceDesc 字段：赋值为 cmm_refer =====
    result_list = _update_field(step2_data_list, 'referenceDesc', cmm_refer)
    print(f"[process_stepEnDesc] referenceDesc 设置为: {cmm_refer}")
    
    # ===== 2. 处理 stepEnDesc 字段 =====
    stepEnDesc = data_dict.get('stepEnDesc', '')
    
    print(f"[process_stepEnDesc] 原始 stepEnDesc: {stepEnDesc}")
    print(f"[process_stepEnDesc] CMM_REFER 原始值: {cmm_refer}")
    print(f"[process_stepEnDesc] CMM_REFER 标准化后: {cmm_refer_normalized}")
    print(f"[process_stepEnDesc] jcendesc 原始值: {jcendesc}")
    print(f"[process_stepEnDesc] jcendesc 处理后: {jcendesc_processed}")
    
    # 如果 stepEnDesc 为空或为 "TEST"，使用默认模板
    if not stepEnDesc or (action_word and stepEnDesc.strip().upper() == "TEST"):
        if action_word:
            new_stepEnDesc = f"REF TO {cmm_refer_normalized}, {action_word} {jcendesc_processed}".strip()
            print(f"[process_stepEnDesc] 使用默认模板生成: {new_stepEnDesc}")
            result_list = _update_field(result_list, 'stepEnDesc', new_stepEnDesc)
        else:
            print("[process_stepEnDesc] stepEnDesc 为空且无 action_word，跳过 stepEnDesc 处理")
        return result_list
    
    # 查找 "REF TO" 或 "REFER TO" 的位置（统一输出为 "REF TO"）
    ref_to_match = re.search(r'(?:REFER TO|REF TO)\s+', stepEnDesc, re.IGNORECASE)
    
    if not ref_to_match:
        if action_word:
            new_stepEnDesc = f"REF TO {cmm_refer_normalized}, {action_word} {jcendesc_processed}".strip()
            print(f"[process_stepEnDesc] 未找到 'REF TO' 或 'REFER TO'，使用默认模板: {new_stepEnDesc}")
            result_list = _update_field(result_list, 'stepEnDesc', new_stepEnDesc)
        else:
            print("[process_stepEnDesc] 未找到 'REF TO' 或 'REFER TO'，跳过 stepEnDesc 处理")
        return result_list
    
    # 查找 "," 的位置（在 "REF TO " 之后）
    comma_pos = stepEnDesc.find(',', ref_to_match.end())
    
    if comma_pos == -1:
        if action_word:
            new_stepEnDesc = f"REF TO {cmm_refer_normalized}, {action_word} {jcendesc_processed}".strip()
            print(f"[process_stepEnDesc] 未找到 ','，使用默认模板: {new_stepEnDesc}")
            result_list = _update_field(result_list, 'stepEnDesc', new_stepEnDesc)
        else:
            print("[process_stepEnDesc] 未找到 ','，跳过 stepEnDesc 处理")
        return result_list
    
    # 提取 "," 之后的第一个单词
    after_comma = stepEnDesc[comma_pos + 1:].strip()
    first_word_match = re.match(r'(\S+)', after_comma)
    
    if not first_word_match:
        if action_word:
            new_stepEnDesc = f"REF TO {cmm_refer_normalized}, {action_word} {jcendesc_processed}".strip()
            print(f"[process_stepEnDesc] 未找到逗号后的单词，使用默认模板: {new_stepEnDesc}")
            result_list = _update_field(result_list, 'stepEnDesc', new_stepEnDesc)
        else:
            print("[process_stepEnDesc] 未找到逗号后的单词，跳过 stepEnDesc 处理")
        return result_list
    
    first_word = first_word_match.group(1)
    
    # 构建新的 stepEnDesc
    before_ref_to = stepEnDesc[:ref_to_match.start()]
    new_stepEnDesc = f"{before_ref_to}REF TO {cmm_refer_normalized}, {first_word} {jcendesc_processed}".strip()
    
    print(f"[process_stepEnDesc] 修改后 stepEnDesc: {new_stepEnDesc}")
    
    result_list = _update_field(result_list, 'stepEnDesc', new_stepEnDesc)
    return result_list

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
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": "10.240.2.131:9080",
            "Origin": "http://10.240.2.131:9080",
            "Referer": referer,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
            "sec-ch-ua": '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "iframe",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1"
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
    
    # 强制设置 updjobcard 为 true（内网模式需要）
    def _set_field(field_name, field_value):
        for i, (n, _) in enumerate(final_payload):
            if n == field_name:
                final_payload[i] = (field_name, field_value)
                return True
        return False
    
    if not _set_field("updjobcard", "true"):
        final_payload.append(("updjobcard", "true"))
    print(f"[Step 3] 已设置 updjobcard=true")

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

    # ========== Cookie 处理（与 workcard_import_service 保持一致）==========
    # 关键：直接使用原始 Cookie 字符串，不进行解析和合并，保留多个同名 JSESSIONID
    
    # 如果传入了 session，优先使用 session.headers 中的 Cookie（由 create_session 设置）
    if session and 'Cookie' in session.headers:
        combined_cookies = session.headers['Cookie']
        print(f"\n[Step 3] 使用 session.headers 中的 Cookie")
    elif raw_cookies:
        combined_cookies = raw_cookies.strip()
        print(f"\n[Step 3] 使用传入的 raw_cookies")
    else:
        combined_cookies = get_default_cookies()
        print(f"\n[Step 3] 使用默认 Cookie 配置")
    
    # Step 2 返回的新 Cookie 追加到末尾（不覆盖，保留所有 Cookie）
    if step2_response_cookies:
        print(f"[Step 3] Step 2 返回了 {len(step2_response_cookies)} 个新 Cookie，追加到现有 Cookie")
        for cookie_str in step2_response_cookies:
            # 从 Set-Cookie 头中提取 cookie 名称和值
            cookie_parts = cookie_str.split(';')[0].strip()
            if '=' in cookie_parts:
                print(f"  + 追加: {cookie_parts[:50]}...")
                if combined_cookies:
                    combined_cookies = f"{combined_cookies}; {cookie_parts}"
                else:
                    combined_cookies = cookie_parts
    
    # 设置 Cookie 到 headers（不修改 session.headers，避免影响后续请求）
    if combined_cookies:
        headers['Cookie'] = combined_cookies
        print(f"\n[Step 3] 最终使用的 Cookie（前200字符）: {combined_cookies[:200]}...")
        print(f"[Step 3] Cookie 总长度: {len(combined_cookies)} 字符")
        
        # 统计 Cookie 项数
        cookie_count = len([c for c in combined_cookies.split(';') if c.strip()])
        print(f"[Step 3] Cookie 项数: {cookie_count}")
    else:
        print("\n[Step 3] ⚠⚠⚠ WARNING: Cookie 为空！这会导致身份验证失败！")
    
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
        
        # 保存完整响应到文件（用于调试）
        try:
            with open('response_step3.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
        except Exception as e:
            print(f"[Step 3] 保存响应文件失败: {e}")
        
        # 解析响应结果
        import urllib.parse
        success = False
        message = ""
        
        # 方法1: 从重定向历史中检查 message 参数
        if response.history:
            for hist in response.history:
                location = hist.headers.get("Location", "")
                if "message=" in location:
                    try:
                        parsed = urllib.parse.urlparse(location)
                        params = urllib.parse.parse_qs(parsed.query)
                        if 'message' in params:
                            msg_encoded = params['message'][0]
                            try:
                                message = urllib.parse.unquote(msg_encoded, encoding='gbk')
                            except:
                                message = msg_encoded
                            if "成功" in message:
                                success = True
                            break
                    except:
                        pass
        
        # 方法2: 从最终响应 URL 中检查 message 参数
        if not message and 'message=' in response.url:
            try:
                parsed = urllib.parse.urlparse(response.url)
                params = urllib.parse.parse_qs(parsed.query)
                if 'message' in params:
                    msg_encoded = params['message'][0]
                    try:
                        message = urllib.parse.unquote(msg_encoded, encoding='gbk')
                    except:
                        message = msg_encoded
                    if "成功" in message:
                        success = True
            except:
                pass
        
        # 方法3: 检查是否被重定向到登录页（身份验证失败）
        is_login_page = ("j_acegi_security_check" in response.text or 
                         "loginCode" in response.text or 
                         "验证码" in response.text)
        
        # 输出结果
        print("\n" + "="*80)
        print("[Step 3] 执行结果:")
        print("="*80)
        
        if success:
            print(f"  ✓ 操作成功: {message}")
        elif is_login_page and not message:
            print(f"  ✗ 身份验证失败（被重定向到登录页）")
            print(f"  提示: 请检查 Cookie 是否有效")
        elif message:
            print(f"  结果: {message}")
        else:
            print(f"  ? 无法确定结果，请查看 response_step3.html")
        
        print(f"  响应状态码: {response.status_code}")
        print(f"  响应长度: {len(response.text)} 字符")
        print("="*80)

    except Exception as e:
        print(f"[Step 3] 请求异常: {e}")


def run_update_steps(
    sale_wo: str,
    ac_no: str,
    jc_seq: str,
    cmm_refer: str,
    cookies: str = None
) -> dict:
    """
    执行更新工卡步骤的完整流程
    
    Args:
        sale_wo: 工作指令号 (SaleWo)，对应 import_batches.workcard_number
        ac_no: 飞机号 (ACNo)，对应 import_batches.aircraft_number
        jc_seq: 已开出工卡号 (jcSeq)，对应 import_batch_items.issued_workcard_number
        cmm_refer: 参考手册 (CMM_REFER)，对应 import_batch_items.ref_manual
        cookies: 可选的 Cookie 字符串，如果不提供则使用默认配置
        
    Returns:
        包含执行结果的字典:
        {
            "success": bool,
            "message": str,
            "jc_workorder_input": str | None,
            "wo_rid": str | None,
            "jc_rid": str | None,
            "logs": list[str]
        }
    """
    import logging
    logger = logging.getLogger(__name__)
    
    logs = []
    result = {
        "success": False,
        "message": "",
        "jc_workorder_input": None,
        "wo_rid": None,
        "jc_rid": None,
        "logs": logs
    }
    
    def log_msg(msg: str):
        logs.append(msg)
        logger.info(f"[updateSteps] {msg}")
        print(f"[updateSteps] {msg}")
    
    try:
        log_msg(f"开始执行更新步骤流程")
        log_msg(f"参数: SaleWo={sale_wo}, ACNo={ac_no}, jcSeq={jc_seq}, CMM_REFER={cmm_refer}")
        
        # 创建共享的Session（与 workcard_import_service 保持一致的 Cookie 处理方式）
        shared_session = create_session(cookies)
        
        # 获取实际使用的 Cookie（用于日志和传递给子函数）
        cookies_to_use = cookies if cookies else get_default_cookies()
        log_msg(f"已创建Session并设置Cookie到headers")
        
        # Step 0: 通过HTTP请求获取jc_workorder_input
        log_msg("Step 0: 获取jc_workorder_input")
        jc_workorder_input = fetch_jc_workorder(sale_wo, ac_no, jc_seq, session=shared_session)
        
        if not jc_workorder_input:
            result["message"] = "无法获取jc_workorder_input"
            log_msg(f"ERROR: {result['message']}")
            return result
        
        result["jc_workorder_input"] = jc_workorder_input
        log_msg(f"成功获取 jc_workorder_input: {jc_workorder_input}")
        
        # Step 1: 使用获取到的jc_workorder_input调用fetch_ids
        log_msg("Step 1: 获取woRid和jcRid")
        wo_rid, jc_rid, _ = fetch_ids(jc_workorder_input, session=shared_session)
        
        if not wo_rid or not jc_rid:
            result["message"] = "无法获取woRid或jcRid"
            log_msg(f"ERROR: {result['message']}")
            return result
        
        result["wo_rid"] = wo_rid
        result["jc_rid"] = jc_rid
        log_msg(f"获取到 woRid: {wo_rid}, jcRid: {jc_rid}")
        
        # Step 2: 获取表单数据
        log_msg("Step 2: 获取表单数据")
        step2_result = fetch_step2(wo_rid, jc_rid, jc_seq, cookies_to_use, session=shared_session)
        
        # 处理返回结果（可能是列表或元组）
        if isinstance(step2_result, tuple) and len(step2_result) == 2:
            step2_data, step2_response_cookies = step2_result
        else:
            step2_data = step2_result
            step2_response_cookies = []
        
        if not step2_data:
            result["message"] = "无法获取表单数据"
            log_msg(f"ERROR: {result['message']}")
            return result
        
        log_msg(f"获取到表单数据，字段数量: {len(step2_data)}")
        
        # 处理 stepEnDesc 字段
        log_msg("处理 stepEnDesc 字段")
        original_step_en_desc = None
        for name, value in step2_data:
            if name == 'stepEnDesc':
                original_step_en_desc = value
                break
        
        step2_data_processed = process_stepEnDesc(step2_data, cmm_refer)
        log_msg(f"stepEnDesc 处理完成，原始值: {original_step_en_desc[:50] if original_step_en_desc else 'N/A'}...")
        
        # Step 3: 提交数据
        log_msg("Step 3: 提交数据")
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
        
        result["success"] = True
        result["message"] = "更新步骤完成"
        log_msg("更新步骤流程执行完成")
        
        return result
        
    except Exception as e:
        result["message"] = f"执行更新步骤时发生错误: {str(e)}"
        log_msg(f"ERROR: {result['message']}")
        import traceback
        log_msg(f"堆栈: {traceback.format_exc()}")
        return result


if __name__ == "__main__":
    """
    独立测试入口 - 直接调用 run_update_steps() 函数
    
    测试参数说明：
        sale_wo: 工作指令号 (SaleWo)
        ac_no: 飞机号 (ACNo)
        jc_seq: 已开出工卡号 (jcSeq)
        cmm_refer: 参考手册 (CMM_REFER)
    """
    print("="*80)
    print("updateSteps 独立测试")
    print("="*80)
    
    # 测试参数
    test_params = {
        "sale_wo": "120000587070",
        "ac_no": "A6-EUD",
        "jc_seq": "51161",
        "cmm_refer": "CMM 25-06-35 REV.____"
    }
    
    print(f"测试参数: {test_params}")
    print("="*80)
    
    # 执行更新步骤
    result = run_update_steps(**test_params)
    
    # 输出结果
    print("\n" + "="*80)
    print("执行结果")
    print("="*80)
    print(f"成功: {result['success']}")
    print(f"消息: {result['message']}")
    print(f"jc_workorder_input: {result.get('jc_workorder_input', 'N/A')}")
    print(f"wo_rid: {result.get('wo_rid', 'N/A')}")
    print(f"jc_rid: {result.get('jc_rid', 'N/A')}")
    
    if result.get('logs'):
        print(f"\n日志 ({len(result['logs'])} 条):")
        for log in result['logs']:
            print(f"  - {log}")
    
    print("="*80)


'''
===== HTTP 请求示例（调试参考）=====

--- 内网直连模式 ---
Request URL: http://10.240.2.131:9080/trace/fgm/fgm.do?method=checkQAAuth&_=1768199499764&txtMenuID=22800
Request Method: GET
Status Code: 200 OK

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


--- VPN模式 ---
Request URL: https://vpn.gameco.com.cn/Web/trace/security/blank.jsp,CVPNHost=10.240.2.131:9080,CVPNProtocol=http,CVPNOrg=rel,CVPNExtension=.jsp
Request Method: GET
Status Code: 200 OK

Response Headers:
  connection: Keep-Alive
  content-type: text/html;charset=GB18030
  server: CPWS
  strict-transport-security: max-age=31536000; includeSubDomains
  x-frame-options: SAMEORIGIN

Request Headers:
  accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8
  accept-encoding: gzip, deflate, br, zstd
  accept-language: zh-CN,zh;q=0.9
  cookie: selected_realm=ssl_vpn; CPCVPN_SESSION_ID=...; CPCVPN_BASE_HOST=vpn.gameco.com.cn; ...
  host: vpn.gameco.com.cn
  referer: https://vpn.gameco.com.cn/Web/trace/security/rolesMenu.jsp,...
  sec-ch-ua: "Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"
  sec-ch-ua-mobile: ?0
  sec-ch-ua-platform: "Windows"
  sec-fetch-dest: frame
  sec-fetch-mode: navigate
  sec-fetch-site: same-origin
  user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36

'''