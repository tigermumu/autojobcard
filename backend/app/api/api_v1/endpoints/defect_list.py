"""
缺陷清单处理 API
提供索引表管理和缺陷表处理功能
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
import pandas as pd
import io
import os
import re
from bs4 import BeautifulSoup
import requests
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from app.services.updateSteps import (
    build_vpn_url,
    USE_VPN,
    VPN_COOKIES,
    COOKIES,
    VPN_HOST
)

from app.core.database import get_db
from app.models.defect_list_index import DefectListIndex, DefectListIndexItem

router = APIRouter()


# ==================== Pydantic 模型 ====================

class IndexItemResponse(BaseModel):
    id: int
    comp_pn: Optional[str]
    comp_desc: Optional[str]
    comp_cmm: Optional[str]
    comp_cmm_rev: Optional[str]
    remark: Optional[str]

    class Config:
        from_attributes = True


class IndexDataResponse(BaseModel):
    success: bool
    message: str
    id: Optional[int] = None
    sale_wo: Optional[str] = None
    ac_no: Optional[str] = None
    row_count: Optional[int] = None
    items: Optional[List[IndexItemResponse]] = None


class IndexListResponse(BaseModel):
    success: bool
    data: List[dict]


class IndexItemCreate(BaseModel):
    comp_pn: Optional[str] = None
    comp_desc: Optional[str] = None
    comp_cmm: Optional[str] = None
    comp_cmm_rev: Optional[str] = None
    remark: Optional[str] = None


class IndexItemUpdate(BaseModel):
    comp_pn: Optional[str] = None
    comp_desc: Optional[str] = None
    comp_cmm: Optional[str] = None
    comp_cmm_rev: Optional[str] = None
    remark: Optional[str] = None


# ==================== 工具函数 ====================

def fetch_jc_data(sale_wo: str, ac_no: str, jc_seq: str, field_name: str = "jcCheck", custom_cookie: str = None) -> Optional[str]:
    """复用 fetch_jc_workorder 的请求逻辑，解析指定字段"""
    print(f"[fetch_jc_data] 请求: sale_wo={sale_wo}, ac_no={ac_no}, jc_seq={jc_seq}")
    if USE_VPN:
        url = build_vpn_url("trace/fgm/workOrder/checkData.jsp")
        cookies = custom_cookie if custom_cookie else VPN_COOKIES
        host = VPN_HOST
        origin = f"https://{VPN_HOST}"
    else:
        url = "http://10.240.2.131:9080/trace/fgm/workOrder/checkData.jsp"
        cookies = custom_cookie if custom_cookie else COOKIES
        host = "10.240.2.131:9080"
        origin = "http://10.240.2.131:9080"
    
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
    
    try:
        response = requests.post(url, params={"from": "manage"}, data=payload, 
                                 headers=headers, timeout=15, verify=False)
        response.encoding = 'GBK'
        
        if response.status_code != 200:
            print(f"[fetch_jc_data] 请求失败，状态码: {response.status_code}")
            return None
        
        html = response.text
        if "j_acegi_security_check" in html or "验证码" in html:
            print(f"[fetch_jc_data] 需要登录验证，Cookie 可能已过期")
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        field_input = soup.find('input', {'name': field_name})
        if field_input and field_input.get('value'):
            value = field_input.get('value')
            print(f"[fetch_jc_data] 成功获取 {field_name}={value}")
            return value
        
        match = re.search(rf'name=["\']?{field_name}["\']?[^>]*value=["\']?([^"\'>\s]+)', html, re.IGNORECASE)
        if match:
            value = match.group(1)
            print(f"[fetch_jc_data] 正则匹配获取 {field_name}={value}")
            return value
        
        print(f"[fetch_jc_data] 未找到字段 {field_name}")
        return None
    except Exception as e:
        print(f"[fetch_jc_data] 异常: {e}")
        return None


def format_jc_seq(jc_seq_raw) -> Optional[str]:
    """将 jc_seq 转换为 5 位数字字符串"""
    if pd.isna(jc_seq_raw):
        return None
    try:
        jc_seq_int = int(float(jc_seq_raw))
        return str(jc_seq_int).zfill(5)
    except (ValueError, TypeError):
        return None


def match_keyword_in_text(text: str, keyword: str) -> bool:
    """检查文本中是否包含关键词（词边界匹配）"""
    if pd.isna(text) or pd.isna(keyword):
        return False
    text = str(text).upper()
    keyword = str(keyword).upper().strip()
    if not keyword:
        return False
    pattern = r'\b' + re.escape(keyword) + r'\b'
    return bool(re.search(pattern, text))


def find_matching_index_item(defect_desc: str, items: List[DefectListIndexItem]):
    """
    两级关键词匹配：
    1. 匹配 COMPONENT DESC
    2. 匹配 COMPONENT P/N
    """
    if pd.isna(defect_desc):
        return None
    
    defect_desc_upper = str(defect_desc).upper()
    
    # 遍历所有项目进行匹配
    for item in items:
        # 1. 尝试匹配 COMPONENT DESC
        if item.comp_desc and match_keyword_in_text(defect_desc_upper, item.comp_desc):
            return item
            
        # 2. 尝试匹配 COMPONENT P/N
        if item.comp_pn and match_keyword_in_text(defect_desc_upper, item.comp_pn):
            return item
    
    return None


# ==================== API 路由 ====================

@router.get("/index/list", response_model=IndexListResponse)
async def list_indexes(db: Session = Depends(get_db)):
    """获取所有索引表列表"""
    indexes = db.query(DefectListIndex).order_by(DefectListIndex.created_at.desc()).all()
    
    data = [{
        "id": idx.id,
        "name": idx.name,
        "sale_wo": idx.sale_wo,
        "ac_no": idx.ac_no,
        "row_count": idx.row_count,
        "created_at": idx.created_at.isoformat() if idx.created_at else None
    } for idx in indexes]
    
    return IndexListResponse(success=True, data=data)


@router.post("/index/upload", response_model=IndexDataResponse)
async def upload_index(
    file: UploadFile = File(...),
    sale_wo: str = Form(...),
    ac_no: str = Form(...),
    year_month: str = Form(...),
    db: Session = Depends(get_db)
):
    """上传并保存索引表到数据库"""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="请上传 Excel 文件 (.xlsx 或 .xls)")
    
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        
        # 验证必要列
        required_cols = ['COMPONENT P/N', 'COMPONENT DESC', 'COMPONENT MANUAL', 'COMPONENT MANUAL REV']
        
        # 标准化列名：转大写并去除首尾空格
        df.columns = [str(col).upper().strip() for col in df.columns]
        
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise HTTPException(status_code=400, detail=f"缺少必要列: {', '.join(missing)}")
        
        # 创建索引表记录，名称格式：飞机号_年月
        index_name = f"{ac_no}_{year_month}"
        index_record = DefectListIndex(
            name=index_name,
            sale_wo=sale_wo,
            ac_no=ac_no,
            row_count=len(df)
        )
        db.add(index_record)
        db.flush()  # 获取 ID
        
        # 创建索引项
        items = []
        for _, row in df.iterrows():
            item = DefectListIndexItem(
                index_id=index_record.id,
                comp_pn=str(row.get('COMPONENT P/N', '')) if pd.notna(row.get('COMPONENT P/N')) else None,
                comp_desc=str(row.get('COMPONENT DESC', '')) if pd.notna(row.get('COMPONENT DESC')) else None,
                comp_cmm=str(row.get('COMPONENT MANUAL', '')) if pd.notna(row.get('COMPONENT MANUAL')) else None,
                comp_cmm_rev=str(row.get('COMPONENT MANUAL REV', '')) if pd.notna(row.get('COMPONENT MANUAL REV')) else None,
                remark=str(row.get('REMARK', '')) if pd.notna(row.get('REMARK')) else None
            )
            items.append(item)
        
        db.add_all(items)
        db.commit()
        db.refresh(index_record)
        
        return IndexDataResponse(
            success=True,
            message="索引表上传成功",
            id=index_record.id,
            sale_wo=sale_wo,
            ac_no=ac_no,
            row_count=len(df)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"处理文件失败: {str(e)}")


@router.get("/index/{index_id}", response_model=IndexDataResponse)
async def get_index(index_id: int, db: Session = Depends(get_db)):
    """获取索引表详情（包含所有数据项）"""
    index_record = db.query(DefectListIndex).filter(DefectListIndex.id == index_id).first()
    
    if not index_record:
        raise HTTPException(status_code=404, detail="索引表不存在")
    
    items = [IndexItemResponse(
        id=item.id,
        comp_pn=item.comp_pn,
        comp_desc=item.comp_desc,
        comp_cmm=item.comp_cmm,
        comp_cmm_rev=item.comp_cmm_rev,
        remark=item.remark
    ) for item in index_record.items]
    
    return IndexDataResponse(
        success=True,
        message="获取成功",
        id=index_record.id,
        sale_wo=index_record.sale_wo,
        ac_no=index_record.ac_no,
        row_count=index_record.row_count,
        items=items
    )


@router.delete("/index/{index_id}")
async def delete_index(index_id: int, db: Session = Depends(get_db)):
    """删除索引表"""
    index_record = db.query(DefectListIndex).filter(DefectListIndex.id == index_id).first()
    
    if not index_record:
        raise HTTPException(status_code=404, detail="索引表不存在")
    
    db.delete(index_record)
    db.commit()
    
    return {"success": True, "message": "索引表已删除"}


# ==================== 索引项 CRUD ====================

@router.post("/index/{index_id}/item", response_model=IndexItemResponse)
async def create_index_item(
    index_id: int,
    item_data: IndexItemCreate,
    db: Session = Depends(get_db)
):
    """添加索引项"""
    index_record = db.query(DefectListIndex).filter(DefectListIndex.id == index_id).first()
    if not index_record:
        raise HTTPException(status_code=404, detail="索引表不存在")
    
    item = DefectListIndexItem(
        index_id=index_id,
        comp_pn=item_data.comp_pn,
        comp_desc=item_data.comp_desc,
        comp_cmm=item_data.comp_cmm,
        comp_cmm_rev=item_data.comp_cmm_rev,
        remark=item_data.remark
    )
    db.add(item)
    
    # 更新行数
    index_record.row_count = (index_record.row_count or 0) + 1
    
    db.commit()
    db.refresh(item)
    
    return IndexItemResponse(
        id=item.id,
        comp_pn=item.comp_pn,
        comp_desc=item.comp_desc,
        comp_cmm=item.comp_cmm,
        comp_cmm_rev=item.comp_cmm_rev,
        remark=item.remark
    )


@router.put("/index/item/{item_id}", response_model=IndexItemResponse)
async def update_index_item(
    item_id: int,
    item_data: IndexItemUpdate,
    db: Session = Depends(get_db)
):
    """更新索引项"""
    item = db.query(DefectListIndexItem).filter(DefectListIndexItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="索引项不存在")
    
    # 更新字段
    if item_data.comp_pn is not None:
        item.comp_pn = item_data.comp_pn
    if item_data.comp_desc is not None:
        item.comp_desc = item_data.comp_desc
    if item_data.comp_cmm is not None:
        item.comp_cmm = item_data.comp_cmm
    if item_data.comp_cmm_rev is not None:
        item.comp_cmm_rev = item_data.comp_cmm_rev
    if item_data.remark is not None:
        item.remark = item_data.remark
    
    db.commit()
    db.refresh(item)
    
    return IndexItemResponse(
        id=item.id,
        comp_pn=item.comp_pn,
        comp_desc=item.comp_desc,
        comp_cmm=item.comp_cmm,
        comp_cmm_rev=item.comp_cmm_rev,
        remark=item.remark
    )


@router.delete("/index/item/{item_id}")
async def delete_index_item(item_id: int, db: Session = Depends(get_db)):
    """删除索引项"""
    item = db.query(DefectListIndexItem).filter(DefectListIndexItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="索引项不存在")
    
    index_id = item.index_id
    db.delete(item)
    
    # 更新行数
    index_record = db.query(DefectListIndex).filter(DefectListIndex.id == index_id).first()
    if index_record and index_record.row_count:
        index_record.row_count = max(0, index_record.row_count - 1)
    
    db.commit()
    
    return {"success": True, "message": "索引项已删除"}


@router.post("/process/{index_id}")
async def process_defects(
    index_id: int,
    file: UploadFile = File(...),
    cookie: str = Form(default=""),
    db: Session = Depends(get_db)
):
    """使用指定索引表处理缺陷表，返回处理后的 Excel 文件"""
    # 获取索引表
    index_record = db.query(DefectListIndex).filter(DefectListIndex.id == index_id).first()
    
    if not index_record:
        raise HTTPException(status_code=404, detail="索引表不存在")
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="请上传 Excel 文件 (.xlsx 或 .xls)")
    
    sale_wo = index_record.sale_wo
    ac_no = index_record.ac_no
    items = index_record.items
    
    try:
        contents = await file.read()
        defects_df = pd.read_excel(io.BytesIO(contents))
        
        if '工卡描述英文' not in defects_df.columns:
            raise HTTPException(status_code=400, detail="缺陷表缺少 '工卡描述英文' 列")
        
        # 将目标列转换为字符串类型
        for col in ['参考手册', '相关工卡号', '相关工卡序号']:
            if col not in defects_df.columns:
                defects_df[col] = None
            defects_df[col] = defects_df[col].astype(object)
        
        matched_count = 0
        # api_success_count = 0
        # api_fail_count = 0
        
        for idx, row in defects_df.iterrows():
            defect_desc = row.get('工卡描述英文', '')
            
            if pd.isna(defect_desc) or str(defect_desc).strip() == '':
                continue
            
            matched_item = find_matching_index_item(defect_desc, items)
            
            if matched_item is None:
                continue
            
            matched_count += 1
            cmm = matched_item.comp_cmm
            cmm_rev = matched_item.comp_cmm_rev
            
            if cmm:
                defects_df.at[idx, '参考手册'] = cmm
                
            # 如果需要也可以填充版本号，这里暂时只填充手册
            # if cmm_rev:
            #     defects_df.at[idx, '手册版本'] = cmm_rev
            
            # 由于不再维护 relate_jc_seq，不再自动获取工卡号
            
        output = io.BytesIO()
        defects_df.to_excel(output, index=False)
        output.seek(0)
        
        filename = f"processed_{file.filename}"
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "X-Process-Total": str(len(defects_df)),
                "X-Process-Matched": str(matched_count),
                "X-Process-API-Success": "0", #str(api_success_count),
                "X-Process-API-Fail": "0" #str(api_fail_count)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")
