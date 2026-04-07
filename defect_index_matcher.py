"""
缺陷数据匹配与工卡信息获取脚本

功能：
1. 从 defects_test_upload.xlsx 的"工卡描述英文"列读取内容
2. 与 index_test_upload.xlsx 进行两级关键词匹配（AREA → COMPONENT）
3. 匹配成功后：
   - 将 CMM 值写入"参考手册"列
   - 调用 API 获取工卡号写入"相关工卡号"列
   - 将 jc_seq 写入"相关工卡序号"列
4. 原地更新 Excel 文件

作者：AutoJobCard
日期：2026-01-23
"""

import pandas as pd
import re
import sys
import os

# 添加当前目录到路径，以便导入 updateSteps
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入 updateSteps 中的核心函数和配置
from updateSteps import (
    fetch_jc_workorder,
    build_vpn_url,
    USE_VPN,
    VPN_COOKIES,
    COOKIES,
    VPN_HOST
)
import requests
from bs4 import BeautifulSoup
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================== 配置区 ====================

# 数据文件路径
DATA_PATH = r"F:\EK 777 local R1"
DEFECTS_FILE = "defects_test_upload.xlsx"
INDEX_FILE = "index_test_upload.xlsx"

# API 调用参数（写死的固定参数）
SALE_WO = "120000587070"  # 销售工单号
AC_NO = "A6-EUD"          # 飞机号

# ==================== 工具函数 ====================

def fetch_jc_data(sale_wo, ac_no, jc_seq, field_name="jcCheck"):
    """
    复用 fetch_jc_workorder 的请求逻辑，解析指定字段
    
    Args:
        sale_wo: 销售工单号
        ac_no: 飞机号
        jc_seq: 工卡序号（5位字符串）
        field_name: 要解析的字段名，默认 "jcCheck"
    
    Returns:
        str: 字段值，失败返回 None
    """
    # 根据USE_VPN选择URL和Cookie
    if USE_VPN:
        url = build_vpn_url("trace/fgm/workOrder/checkData.jsp")
        cookies = VPN_COOKIES
        host = VPN_HOST
        origin = f"https://{VPN_HOST}"
    else:
        url = "http://10.240.2.131:9080/trace/fgm/workOrder/checkData.jsp"
        cookies = COOKIES
        host = "10.240.2.131:9080"
        origin = "http://10.240.2.131:9080"
    
    # 构建请求（复用 fetch_jc_workorder 的 payload 结构）
    payload = {
        'wgp': 'QRY', 'printer': '', 'txtMenuID': '14076',
        'txtFullReg': ac_no, 'qWorkorder': sale_wo, 'txtSeq': jc_seq,
        'txtFlight_Check_No': '', 'txtIPC_Num': '', 'txtVisit_Desc': '',
        'txtMpd': '', 'txtType': '', 'txtJobcard': '', 'txtJcDesc': '',
        'txtQcFinal': '', 'txtJcStatus': '', 'txtSlnStatus': '', 'txtImport': '',
        'txtBoothAss': '', 'txtSlnPrinted': '', 'preWorkGrp': '', 'curWorkGrp': '',
        'schemeGrp': '', 'txtUpdatedBy': '', 'txtDangerousCargo': '',
        'txtSchedPhase': '', 'txtSchedZone': '', 'txtLaborCode': '',
        'txtTransferMode': '', 'txtme_unUpload': '', 'txtRii': '', 'txtMatStatus': '',
        'txtFilterTrace': '', 'txtJcRob': '', 'txtPrDateStart': '', 'txtPrDateEnd': '',
        'txtRTrade': '', 'txtHoldBy': '', 'txtJcTransferDateStart': '',
        'txtJcTransferDateEnd': '', 'txtJcWorkorder': '', 'txtSlnReqDateStart': '',
        'txtSlnReqDateEnd': '', 'txtFlagMpd': '', 'txtFlagActive': '', 'txtExternal': '',
        'txtExteriorDamag': '', 'txtMajorMdo': '', 'txtOutOfManual': '', 'txtStrRepair': '',
        'txtPse': '', 'txtFcs': '', 'txtCauseStrr': '', 'txtRplStrPart': '',
        'txtQcStamp': '', 'txtNmfTrade': '', 'txtForbidEsign': '', 'txtFedexAmtStamp': '',
        'txtFeeRemark': '', 'txtFlagFee': '', 'txtInspector': ''
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Host": host, "Origin": origin, "Referer": url,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    if cookies:
        headers['Cookie'] = cookies.strip()
    
    print(f"    [获取{field_name}] 请求: SaleWo={sale_wo}, ACNo={ac_no}, jcSeq={jc_seq}")
    
    try:
        response = requests.post(url, params={"from": "manage"}, data=payload, 
                                 headers=headers, timeout=15, verify=False)
        response.encoding = 'GBK'
        
        if response.status_code != 200:
            print(f"    [获取{field_name}] 请求失败，状态码: {response.status_code}")
            return None
        
        html = response.text
        
        # 检查登录页
        if "j_acegi_security_check" in html or "验证码" in html:
            print(f"    [获取{field_name}] 身份验证失败！")
            return None
        
        # 解析字段
        soup = BeautifulSoup(html, 'html.parser')
        
        # 方法1: name 属性
        field_input = soup.find('input', {'name': field_name})
        if field_input and field_input.get('value'):
            value = field_input.get('value')
            print(f"    [获取{field_name}] 成功: {value}")
            return value
        
        # 方法2: 正则
        match = re.search(rf'name=["\']?{field_name}["\']?[^>]*value=["\']?([^"\'>\s]+)', html, re.IGNORECASE)
        if match:
            value = match.group(1)
            print(f"    [获取{field_name}] 正则匹配: {value}")
            return value
        
        print(f"    [获取{field_name}] 未找到字段")
        return None
        
    except Exception as e:
        print(f"    [获取{field_name}] 异常: {e}")
        return None


def format_jc_seq(jc_seq_raw):
    """
    将 jc_seq 转换为 5 位数字字符串，前导补零
    
    Args:
        jc_seq_raw: 原始值（可能是 int、float 或 str）
    
    Returns:
        str: 5位数字字符串，如 "00775"
    """
    if pd.isna(jc_seq_raw):
        return None
    
    # 转为整数再转字符串，避免浮点数问题
    try:
        jc_seq_int = int(float(jc_seq_raw))
        return str(jc_seq_int).zfill(5)
    except (ValueError, TypeError):
        print(f"  [警告] 无法转换 jc_seq: {jc_seq_raw}")
        return None


def match_keyword_in_text(text, keyword):
    """
    检查文本中是否包含关键词（不区分大小写，词边界匹配）
    
    Args:
        text: 待搜索的文本
        keyword: 关键词
    
    Returns:
        bool: 是否匹配
    """
    if pd.isna(text) or pd.isna(keyword):
        return False
    
    text = str(text).upper()
    keyword = str(keyword).upper().strip()
    
    if not keyword:
        return False
    
    # 使用词边界匹配，确保是完整单词
    # 对于像 "F1", "F2" 这样的关键词，需要精确匹配
    pattern = r'\b' + re.escape(keyword) + r'\b'
    return bool(re.search(pattern, text))


def find_matching_index_row(defect_desc, index_df):
    """
    两级关键词匹配：先匹配 AREA，再匹配 COMPONENT
    
    Args:
        defect_desc: 缺陷描述英文
        index_df: 索引数据 DataFrame
    
    Returns:
        匹配的 index 行（Series），如果没有匹配返回 None
    """
    if pd.isna(defect_desc):
        return None
    
    defect_desc_upper = str(defect_desc).upper()
    
    # 获取所有唯一的 AREA 值
    unique_areas = index_df['AREA'].dropna().unique()
    
    # 第一级匹配：检查 AREA
    matched_areas = []
    for area in unique_areas:
        if match_keyword_in_text(defect_desc_upper, area):
            matched_areas.append(area)
    
    if not matched_areas:
        return None
    
    # 第二级匹配：在匹配的 AREA 中检查 COMPONENT
    for area in matched_areas:
        # 获取该 AREA 下的所有行
        area_rows = index_df[index_df['AREA'] == area]
        
        for _, row in area_rows.iterrows():
            component = row['COMPONENT']
            if match_keyword_in_text(defect_desc_upper, component):
                # 找到匹配，返回该行
                return row
    
    return None


# ==================== 主处理函数 ====================

def process_defects():
    """
    主处理流程
    """
    print("=" * 60)
    print("缺陷数据匹配与工卡信息获取脚本")
    print("=" * 60)
    
    # 1. 加载数据
    print("\n[1] 加载数据文件...")
    
    defects_path = os.path.join(DATA_PATH, DEFECTS_FILE)
    index_path = os.path.join(DATA_PATH, INDEX_FILE)
    
    if not os.path.exists(defects_path):
        print(f"  [错误] 文件不存在: {defects_path}")
        return
    
    if not os.path.exists(index_path):
        print(f"  [错误] 文件不存在: {index_path}")
        return
    
    defects_df = pd.read_excel(defects_path)
    index_df = pd.read_excel(index_path)
    
    print(f"  ✓ 加载 {DEFECTS_FILE}: {len(defects_df)} 行")
    print(f"  ✓ 加载 {INDEX_FILE}: {len(index_df)} 行")
    
    # 显示 index 数据的 AREA 和 COMPONENT 统计
    print(f"\n  Index 数据概览:")
    print(f"    AREA 种类: {index_df['AREA'].nunique()} 个 - {index_df['AREA'].unique().tolist()}")
    print(f"    COMPONENT 数量: {index_df['COMPONENT'].nunique()} 个")
    
    # 2. 处理每一行缺陷数据
    print(f"\n[2] 开始处理缺陷数据...")
    print(f"  API 参数: SALE_WO={SALE_WO}, AC_NO={AC_NO}")
    print("-" * 60)
    
    matched_count = 0
    api_success_count = 0
    api_fail_count = 0
    
    for idx, row in defects_df.iterrows():
        defect_id = row.get('缺陷编号', f'Row-{idx}')
        defect_desc = row.get('工卡描述英文', '')
        
        print(f"\n  [{idx + 1}/{len(defects_df)}] 处理: {defect_id}")
        
        if pd.isna(defect_desc) or str(defect_desc).strip() == '':
            print(f"    跳过: 工卡描述英文为空")
            continue
        
        # 截取显示
        desc_display = str(defect_desc)[:60] + "..." if len(str(defect_desc)) > 60 else str(defect_desc)
        print(f"    描述: {desc_display}")
        
        # 关键词匹配
        matched_row = find_matching_index_row(defect_desc, index_df)
        
        if matched_row is None:
            print(f"    匹配结果: 未匹配")
            continue
        
        matched_count += 1
        area = matched_row['AREA']
        component = matched_row['COMPONENT']
        cmm = matched_row['CMM']
        jc_seq_raw = matched_row['RELATE_JC_SEQ']
        
        print(f"    匹配成功: AREA={area}, COMPONENT={component}")
        print(f"    CMM: {cmm}")
        
        # 格式化 jc_seq
        jc_seq = format_jc_seq(jc_seq_raw)
        if jc_seq is None:
            print(f"    [警告] jc_seq 无效，跳过 API 调用")
            # 仍然写入 CMM
            if pd.notna(cmm):
                defects_df.at[idx, '参考手册'] = cmm
            continue
        
        print(f"    jc_seq: {jc_seq_raw} → {jc_seq}")
        
        # 写入 CMM 到参考手册
        if pd.notna(cmm):
            defects_df.at[idx, '参考手册'] = cmm
        
        # 写入 jc_seq 到相关工卡序号
        defects_df.at[idx, '相关工卡序号'] = jc_seq
        
        # 调用 API 获取 jcCheck（工卡号）
        try:
            jc_check = fetch_jc_data(SALE_WO, AC_NO, jc_seq, "jcCheck")
            
            if jc_check:
                defects_df.at[idx, '相关工卡号'] = jc_check
                api_success_count += 1
            else:
                api_fail_count += 1
                
        except Exception as e:
            print(f"    API 调用异常: {e}")
            api_fail_count += 1
    
    # 3. 保存结果
    print("\n" + "-" * 60)
    print(f"\n[3] 保存结果...")
    
    try:
        defects_df.to_excel(defects_path, index=False)
        print(f"  ✓ 已保存到: {defects_path}")
    except Exception as e:
        print(f"  [错误] 保存失败: {e}")
        # 尝试保存到备份文件
        backup_path = os.path.join(DATA_PATH, "defects_test_upload_updated.xlsx")
        try:
            defects_df.to_excel(backup_path, index=False)
            print(f"  ✓ 已保存到备份文件: {backup_path}")
        except Exception as e2:
            print(f"  [错误] 备份保存也失败: {e2}")
    
    # 4. 输出统计
    print("\n" + "=" * 60)
    print("处理完成 - 统计信息")
    print("=" * 60)
    print(f"  总行数:       {len(defects_df)}")
    print(f"  匹配成功:     {matched_count}")
    print(f"  API 成功:     {api_success_count}")
    print(f"  API 失败:     {api_fail_count}")
    print("=" * 60)


# ==================== 入口 ====================

if __name__ == "__main__":
    process_defects()
