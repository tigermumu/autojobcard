import json
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Set

from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.models.localwash import (
    KeywordDict,
    KeywordDictItem,
    GlobalKeyword,
    WorkcardCleanLocal,
    WorkcardCleanLocalUpload,
    DefectCleanLocal,
    DefectMatchLocal,
)
from app.models.configuration import Configuration
from app.models.workcard import WorkCard
from app.models.defect import DefectRecord


@dataclass
class CompiledDict:
    dict_id: int
    version: str
    main_keywords: List[str]
    # per main_component
    sub_by_main: Dict[str, List[str]]
    location_by_main: Dict[str, List[str]]
    orientation_by_main: Dict[str, List[str]]
    # global status keywords
    status_keywords: List[str]
    # global action keywords
    action_keywords: List[str]


def _safe_str(v: Optional[str]) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    return str(v).strip()


def _maybe_json_load(v) -> Dict:
    if v is None:
        return {}
    if isinstance(v, dict):
        return v
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return {}
        try:
            return json.loads(s)
        except Exception:
            return {}
    return {}


def _word_match(text: str, keyword: str) -> bool:
    """
    单词级别匹配：使用正则表达式的单词边界 \b 确保只匹配完整单词。
    例如：'BIN' 能匹配 'THE BIN IS BROKEN' 但不能匹配 'CABIN'
    """
    if not text or not keyword:
        return False
    # 转义关键词中的特殊正则字符，然后用单词边界包裹
    pattern = r'\b' + re.escape(keyword) + r'\b'
    return bool(re.search(pattern, text, re.IGNORECASE))


def _contains_ci(text: str, keyword: str) -> bool:
    """使用单词边界匹配（兼容旧调用）"""
    return _word_match(text, keyword)


def _best_match_longest(text: str, keywords: List[str]) -> Optional[str]:
    """
    单值命中：返回"最长关键词优先"的命中结果；未命中返回 None。
    规则：case-insensitive 的**单词级别**匹配（使用 \b 边界）。
    """
    if not text:
        return None
    # longest-first for deterministic result
    for kw in sorted({k for k in keywords if k}, key=lambda x: len(x), reverse=True):
        if _word_match(text, kw):
            return kw
    return None


def _match_all(text: str, keywords: List[str]) -> List[str]:
    """
    多值命中：返回所有匹配的关键词列表（按长度降序）。
    规则：case-insensitive 的**单词级别**匹配（使用 \b 边界）。
    """
    if not text:
        return []
    matched = []
    # 按长度降序排列，确保长关键词优先
    for kw in sorted({k for k in keywords if k}, key=lambda x: len(x), reverse=True):
        if _word_match(text, kw):
            matched.append(kw)
    return matched


def _extract_words(text: str) -> Set[str]:
    """
    提取字符串中的所有单词（忽略分隔符如 "-", ",", " "）。
    例如：
    - "STOPPER-DOOR" -> {"STOPPER", "DOOR"}
    - "STOPPER, DOOR" -> {"STOPPER", "DOOR"}
    - "STOPPER DOOR" -> {"STOPPER", "DOOR"}
    """
    if not text:
        return set()
    # 使用正则表达式提取所有单词（字母数字组合）
    words = re.findall(r'\b\w+\b', text.upper())
    return set(words)


def _deduplicate_sub_components(sub_list: List[str]) -> List[str]:
    """
    去重 sub_component 列表，识别出像 "STOPPER-DOOR" 和 "STOPPER, DOOR" 这样的重复项。
    策略：
    1. 将每个 sub_component 拆分为单词集合
    2. 如果两个 sub_component 的单词集合相同，则认为是重复的（保留先出现的）
    3. 如果组合词（如 "STOPPER-DOOR"）和单独词（如 "STOPPER"、"DOOR"）都存在：
       - 优先保留单独词（关键词匹配优先，不考虑组合词）
       - 去除组合词
    4. 优先保留关键词匹配到的（即保留列表中先出现的，因为关键词匹配优先）
    
    例如：
    - "STOPPER-DOOR" 和 "STOPPER, DOOR" 的单词集合相同，保留先出现的
    - 如果同时有 "STOPPER-DOOR"、"STOPPER"、"DOOR"，保留 "STOPPER" 和 "DOOR"，去除 "STOPPER-DOOR"
    """
    if not sub_list:
        return []
    
    result = []
    
    for sub in sub_list:
        if not sub or not sub.strip():
            continue
        
        word_set = _extract_words(sub)
        
        # 如果单词集合为空（例如只有标点符号），直接跳过
        if not word_set:
            continue
        
        # 检查是否与已有结果重复
        is_duplicate = False
        items_to_remove = []
        
        # 检查是否与已有结果完全重复或部分重复
        for existing_sub in result:
            existing_word_set = _extract_words(existing_sub)
            
            # 情况1：单词集合完全相同（如 "STOPPER-DOOR" 和 "STOPPER, DOOR"）
            if word_set == existing_word_set:
                is_duplicate = True
                break
            
            # 情况2：当前项的单词集合被已有项包含（如 "STOPPER" 被 "STOPPER-DOOR" 包含）
            # 如果已有项是组合词，当前项是单独词，应该保留单独词，去除组合词
            if word_set.issubset(existing_word_set) and len(word_set) < len(existing_word_set):
                # 当前项是单独词，已有项是组合词，标记已有项待删除
                items_to_remove.append(existing_sub)
                # 继续处理当前项（不标记为重复）
                continue
            
            # 情况3：已有项的单词集合被当前项包含（如已有 "STOPPER"，当前是 "STOPPER-DOOR"）
            # 如果当前项是组合词，已有项是单独词，应该保留单独词，去除组合词
            if existing_word_set.issubset(word_set) and len(existing_word_set) < len(word_set):
                # 已有项是单独词，当前项是组合词，跳过当前项（保留已有项）
                is_duplicate = True
                break
        
        # 移除被单独词替代的组合词
        for item in items_to_remove:
            result.remove(item)
        
        if not is_duplicate:
            result.append(sub)
    
    return result


class LocalWashService:
    def __init__(self, db: Session):
        self.db = db

    # ---------- keyword dict ----------
    def list_dicts(self, configuration_id: int) -> List[KeywordDict]:
        return (
            self.db.query(KeywordDict)
            .filter(KeywordDict.configuration_id == configuration_id)
            .order_by(desc(KeywordDict.created_at))
            .all()
        )

    def list_dict_options(self) -> List[Dict]:
        """
        返回所有可选的关键词字典版本（用于前端下拉“清洗引擎选择”）。
        这里返回 dict_id + configuration_id + configuration_name + version。
        """
        rows = (
            self.db.query(KeywordDict, Configuration)
            .join(Configuration, Configuration.id == KeywordDict.configuration_id)
            .order_by(desc(KeywordDict.created_at))
            .all()
        )
        return [
            {
                "dict_id": d.id,
                "configuration_id": d.configuration_id,
                "configuration_name": c.name,
                "version": d.version,
                "remark": d.remark,
                "created_at": d.created_at,
            }
            for d, c in rows
        ]

    def get_dict(self, dict_id: int) -> Optional[KeywordDict]:
        return self.db.query(KeywordDict).filter(KeywordDict.id == dict_id).first()

    def get_latest_dict_for_configuration(self, configuration_id: int) -> Optional[KeywordDict]:
        # 默认规则：优先 version（字符串）倒序；若 version 不可比较也无所谓，created_at 作为兜底排序
        return (
            self.db.query(KeywordDict)
            .filter(KeywordDict.configuration_id == configuration_id)
            .order_by(desc(KeywordDict.version), desc(KeywordDict.created_at))
            .first()
        )

    def create_dict(
        self,
        configuration_id: int,
        version: str,
        remark: Optional[str],
        items: List[Dict],
    ) -> KeywordDict:
        d = KeywordDict(configuration_id=configuration_id, version=version, remark=remark)
        self.db.add(d)
        self.db.flush()
        for item in items:
            self.db.add(
                KeywordDictItem(
                    dict_id=d.id,
                    dimension=item["dimension"],
                    main_component=_safe_str(item.get("main_component")) or None,
                    keyword=_safe_str(item.get("keyword")),
                    enabled=bool(item.get("enabled", True)),
                )
            )
        self.db.commit()
        self.db.refresh(d)
        return d

    def update_dict_item(self, item_id: int, patch: Dict) -> Optional[KeywordDictItem]:
        item = self.db.query(KeywordDictItem).filter(KeywordDictItem.id == item_id).first()
        if not item:
            return None
        if "keyword" in patch and patch["keyword"] is not None:
            item.keyword = _safe_str(patch["keyword"])
        if "main_component" in patch:
            mc = _safe_str(patch.get("main_component"))
            item.main_component = mc or None
        if "enabled" in patch and patch["enabled"] is not None:
            item.enabled = bool(patch["enabled"])
        self.db.commit()
        self.db.refresh(item)
        return item

    def create_dict_item(self, dict_id: int, item: Dict) -> KeywordDictItem:
        new_item = KeywordDictItem(
            dict_id=dict_id,
            dimension=_safe_str(item.get("dimension")).lower(),
            main_component=_safe_str(item.get("main_component")) or None,
            keyword=_safe_str(item.get("keyword")),
            enabled=bool(item.get("enabled", True)),
        )
        self.db.add(new_item)
        self.db.commit()
        self.db.refresh(new_item)
        return new_item

    def delete_dict_item(self, item_id: int) -> bool:
        item = self.db.query(KeywordDictItem).filter(KeywordDictItem.id == item_id).first()
        if not item:
            return False
        self.db.delete(item)
        self.db.commit()
        return True

    def list_global_keywords(self, query: Optional[str] = None) -> List[GlobalKeyword]:
        q = self.db.query(GlobalKeyword)
        if query:
            q = q.filter(GlobalKeyword.keyword.ilike(f"%{query}%"))
        return q.order_by(GlobalKeyword.id.desc()).all()

    def create_global_keyword(self, keyword: str, enabled: bool = True) -> GlobalKeyword:
        normalized = _safe_str(keyword)
        if not normalized:
            raise ValueError("keyword is required")
        exists = (
            self.db.query(GlobalKeyword)
            .filter(
                func.lower(GlobalKeyword.keyword) == normalized.lower(),
            )
            .first()
        )
        if exists:
            raise ValueError("keyword already exists")
        item = GlobalKeyword(
            keyword=normalized,
            enabled=bool(enabled),
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def update_global_keyword(self, item_id: int, patch: Dict) -> Optional[GlobalKeyword]:
        item = (
            self.db.query(GlobalKeyword)
            .filter(GlobalKeyword.id == item_id)
            .first()
        )
        if not item:
            return None
        if "keyword" in patch and patch["keyword"] is not None:
            normalized = _safe_str(patch["keyword"])
            if not normalized:
                raise ValueError("keyword is required")
            exists = (
                self.db.query(GlobalKeyword)
                .filter(
                    func.lower(GlobalKeyword.keyword) == normalized.lower(),
                    GlobalKeyword.id != item_id,
                )
                .first()
            )
            if exists:
                raise ValueError("keyword already exists")
            item.keyword = normalized
        if "enabled" in patch and patch["enabled"] is not None:
            item.enabled = bool(patch["enabled"])
        self.db.commit()
        self.db.refresh(item)
        return item

    def delete_global_keyword(self, item_id: int) -> bool:
        item = self.db.query(GlobalKeyword).filter(GlobalKeyword.id == item_id).first()
        if not item:
            return False
        self.db.delete(item)
        self.db.commit()
        return True

    def compile_dict(self, dict_id: int) -> CompiledDict:
        d = self.get_dict(dict_id)
        if not d:
            raise ValueError("keyword_dict not found")

        # 按文档要求：启用/停用不参与执行逻辑（全部条目视为生效）
        items = (
            self.db.query(KeywordDictItem)
            .filter(KeywordDictItem.dict_id == dict_id)
            .all()
        )

        main_keywords: List[str] = []
        sub_by_main: Dict[str, List[str]] = {}
        loc_by_main: Dict[str, List[str]] = {}
        ori_by_main: Dict[str, List[str]] = {}
        status_keywords: List[str] = []
        action_keywords: List[str] = []

        for it in items:
            dim = (it.dimension or "").strip().lower()
            kw = _safe_str(it.keyword)
            if not kw:
                continue
            if dim == "main":
                main_keywords.append(kw)
            elif dim == "status":
                status_keywords.append(kw)
            elif dim == "action":
                action_keywords.append(kw)
            elif dim in ("sub", "location", "orientation"):
                mc = _safe_str(it.main_component)
                if not mc:
                    # 子部件/位置/方向没有绑定主部件则忽略（避免串台）
                    continue
                target = sub_by_main if dim == "sub" else loc_by_main if dim == "location" else ori_by_main
                target.setdefault(mc, []).append(kw)

        # de-dup
        def dedup_map(m: Dict[str, List[str]]) -> Dict[str, List[str]]:
            return {k: list(dict.fromkeys(v)) for k, v in m.items()}

        return CompiledDict(
            dict_id=dict_id,
            version=d.version,
            main_keywords=list(dict.fromkeys(main_keywords)),
            sub_by_main=dedup_map(sub_by_main),
            location_by_main=dedup_map(loc_by_main),
            orientation_by_main=dedup_map(ori_by_main),
            status_keywords=list(dict.fromkeys(status_keywords)),
            action_keywords=list(dict.fromkeys(action_keywords)),
        )

    # ---------- cleaning ----------
    def clean_jobcard_en(self, text_en: str, compiled: CompiledDict) -> Dict[str, Optional[str]]:
        """
        本地清洗核心：仅英文参与（中文不参与抽取）。
        返回结构化字段：
        - main_component: 多值（逗号分隔，所有匹配的主部件关键词）
        - sub_component: 多值（逗号分隔，所有匹配的子部件关键词）
        - location, orientation, status, action: 单值
        """
        text_en = _safe_str(text_en)
        if not text_en:
            return {
                "main_component": None,
                "sub_component": None,
                "location": None,
                "orientation": None,
                "status": None,
                "action": None,
            }

        # main_component 使用多值匹配（所有匹配的关键词）
        main_list = _match_all(text_en, compiled.main_keywords)
        
        sub_list: List[str] = []
        loc_set: set = set()
        ori_set: set = set()
        
        # 对每个匹配的 main_component，查找对应的 sub、location、orientation
        for main in main_list:
            # sub_component 使用多值匹配
            sub_list.extend(_match_all(text_en, compiled.sub_by_main.get(main, [])))
            # location 和 orientation 取最长匹配（单值），但需要合并多个 main 的结果
            loc_match = _best_match_longest(text_en, compiled.location_by_main.get(main, []))
            if loc_match:
                loc_set.add(loc_match)
            ori_match = _best_match_longest(text_en, compiled.orientation_by_main.get(main, []))
            if ori_match:
                ori_set.add(ori_match)

        status = _best_match_longest(text_en, compiled.status_keywords)
        action = _best_match_longest(text_en, compiled.action_keywords)
        
        # main_component 多值用逗号分隔存储
        main = ", ".join(main_list) if main_list else None
        # sub_component 多值用逗号分隔存储（去重：包括识别组合词重复）
        sub_list_unique = _deduplicate_sub_components(sub_list)  # 智能去重，识别组合词重复
        sub = ", ".join(sub_list_unique) if sub_list_unique else None
        # location 和 orientation 取最长的一个（单值）
        loc = max(loc_set, key=len) if loc_set else None
        ori = max(ori_set, key=len) if ori_set else None
        
        return {
            "main_component": main,
            "sub_component": sub,
            "location": loc,
            "orientation": ori,
            "status": status,
            "action": action,
        }

    def _extract_workcard_descriptions(self, wc: WorkCard) -> Tuple[str, str]:
        """
        统一抽取 description_en/description_cn：
        - 优先使用 raw_data 中的 description_en/description_cn 或 工卡描述（英文/中文）
        - 兜底：description_en <- workcards.description；description_cn <- workcards.title
        """
        raw = _maybe_json_load(getattr(wc, "raw_data", None))
        
        # 英文变体
        en_keys = ["description_en", "工卡描述（英文）", "工卡描述(英文)", "工卡描述英文", "description", "Description"]
        en = ""
        for k in en_keys:
            variants = {k, k.lower(), k.upper(), k.replace("（", "(").replace("）", ")"), k.replace("(", "（").replace(")", "）")}
            for v in variants:
                val = _safe_str(raw.get(v))
                if val:
                    en = val
                    break
            if en: break
        if not en:
            en = _safe_str(wc.description)

        # 中文变体
        cn_keys = ["description_cn", "工卡描述（中文）", "工卡描述(中文)", "工卡描述中文", "描述", "工卡描述", "title", "Title"]
        cn = ""
        for k in cn_keys:
            variants = {k, k.lower(), k.upper(), k.replace("（", "(").replace("）", ")"), k.replace("(", "（").replace(")", "）")}
            for v in variants:
                val = _safe_str(raw.get(v))
                if val:
                    cn = val
                    break
            if cn: break
        if not cn:
            cn = _safe_str(wc.title)

        return en, cn

    def _extract_defect_descriptions(self, dr: DefectRecord) -> Tuple[str, str]:
        """
        统一抽取 description_en/description_cn：
        - 优先使用 raw_data 中的 description_en/description_cn 或 工卡描述（英文/中文）
        - 兜底：description_cn <- defect_records.title；description_en <- defect_records.description
        """
        raw = dr.raw_data or {}
        if isinstance(raw, str):
            raw = _maybe_json_load(raw)

        # 英文变体
        en_keys = ["description_en", "工卡描述（英文）", "工卡描述(英文)", "工卡描述英文", "description", "Description"]
        en = ""
        for k in en_keys:
            variants = {k, k.lower(), k.upper(), k.replace("（", "(").replace("）", ")"), k.replace("(", "（").replace(")", "）")}
            for v in variants:
                val = _safe_str(raw.get(v))
                if val:
                    en = val
                    break
            if en: break
        if not en:
            en = _safe_str(dr.description)

        # 中文变体
        cn_keys = ["description_cn", "工卡描述（中文）", "工卡描述(中文)", "工卡描述中文", "描述", "工卡描述", "title", "Title"]
        cn = ""
        for k in cn_keys:
            variants = {k, k.lower(), k.upper(), k.replace("（", "(").replace("）", ")"), k.replace("(", "（").replace(")", "）")}
            for v in variants:
                val = _safe_str(raw.get(v))
                if val:
                    cn = val
                    break
            if cn: break
        if not cn:
            cn = _safe_str(dr.title)

        return en, cn

    def clean_all_workcards(self, configuration_id: int, dict_id: Optional[int] = None, cabin_layout: Optional[str] = None) -> Tuple[CompiledDict, int, int, int]:
        d = self.get_dict(dict_id) if dict_id else self.get_latest_dict_for_configuration(configuration_id)
        if not d:
            raise ValueError("未找到该构型可用的关键词字典版本，请先在关键词管理中创建/导入词典")
        compiled = self.compile_dict(d.id)

        workcards = self.db.query(WorkCard).filter(WorkCard.configuration_id == configuration_id).all()

        # 为避免重复堆积，这里按 configuration+dict_id+cabin_layout 先清理旧数据
        delete_query = self.db.query(WorkcardCleanLocal).filter(
            WorkcardCleanLocal.configuration_id == configuration_id,
            WorkcardCleanLocal.dict_id == d.id,
        )
        if cabin_layout:
            delete_query = delete_query.filter(WorkcardCleanLocal.cabin_layout == cabin_layout)
        else:
            delete_query = delete_query.filter(WorkcardCleanLocal.cabin_layout.is_(None))
        delete_query.delete()
        self.db.flush()

        total = len(workcards)
        cleaned = 0
        skipped = 0

        for wc in workcards:
            desc_en, desc_cn = self._extract_workcard_descriptions(wc)
            if not _safe_str(desc_en):
                skipped += 1
                continue

            result = self.clean_jobcard_en(desc_en, compiled)
            self.db.add(
                WorkcardCleanLocal(
                    workcard_id=wc.id,
                    aircraft_type=wc.aircraft_type,
                    configuration_id=configuration_id,
                    dict_id=d.id,
                    dict_version=d.version,
                    description_en=desc_en,
                    description_cn=desc_cn,
                    workcard_number=wc.workcard_number,
                    main_component=result["main_component"],
                    sub_component=result["sub_component"],
                    location=result["location"],
                    orientation=result["orientation"],
                    status=result["status"],
                    action=result.get("action"),
                    cabin_layout=cabin_layout,
                )
            )
            cleaned += 1

        self.db.commit()
        return compiled, total, cleaned, skipped

    def clean_uploaded_workcards(
        self, dict_id: int, rows: List[Dict]
    ) -> Tuple[CompiledDict, int, int, int, List[Dict], int]:
        """
        本地清洗（历史工卡）：输入为“前端上传的 Excel 原始数据行”（不依赖 workcards 表）。
        - dict_id: 指定使用哪一版关键词字典
        - rows: [{workcard_number, description_en, description_cn}, ...]
        返回：compiled, total, cleaned, skipped, cleaned_rows, configuration_id
        """
        d = self.get_dict(dict_id)
        if not d:
            raise ValueError("关键词字典未找到，请重新选择或在关键词管理中导入词典")
        compiled = self.compile_dict(d.id)

        total = len(rows or [])
        cleaned = 0
        skipped = 0
        out_rows: List[Dict] = []

        for r in rows or []:
            wc_no = _safe_str(r.get("workcard_number"))
            desc_en = _safe_str(r.get("description_en"))
            desc_cn = _safe_str(r.get("description_cn"))
            if not desc_en:
                skipped += 1
                out_rows.append(
                    {
                        "workcard_number": wc_no,
                        "description_cn": desc_cn,
                        "description_en": desc_en,
                        "main_component": None,
                        "sub_component": None,
                        "location": None,
                        "orientation": None,
                        "status": None,
                    "action": None,
                        "error": "缺少英文描述(description_en)，跳过",
                    }
                )
                continue

            result = self.clean_jobcard_en(desc_en, compiled)
            err = None
            if not result.get("main_component") or not result.get("sub_component"):
                err = "匹配错误：缺失主部件或子部件"
                skipped += 1
            else:
                cleaned += 1

            out_rows.append(
                {
                    "workcard_number": wc_no,
                    "description_cn": desc_cn,
                    "description_en": desc_en,
                    "main_component": result.get("main_component"),
                    "sub_component": result.get("sub_component"),
                    "location": result.get("location"),
                    "orientation": result.get("orientation"),
                    "status": result.get("status"),
                    "action": result.get("action"),
                    "error": err,
                }
            )

        return compiled, total, cleaned, skipped, out_rows, d.configuration_id

    def save_uploaded_workcards_cleaned(self, dict_id: int, rows: List[Dict], cabin_layout: Optional[str] = None) -> Tuple[CompiledDict, int, int, int]:
        """
        对上传的历史工卡（Excel行）执行本地清洗并保存到本地表 workcard_clean_local_upload。
        会先清理同一 configuration_id + dict_id + cabin_layout 的旧数据，避免重复堆积。
        """
        compiled, total, cleaned, skipped, out_rows, configuration_id = self.clean_uploaded_workcards(
            dict_id=dict_id,
            rows=rows,
        )

        # 清理旧数据（同构型+同词典版本+同客舱布局）
        delete_query = self.db.query(WorkcardCleanLocalUpload).filter(
            WorkcardCleanLocalUpload.configuration_id == configuration_id,
            WorkcardCleanLocalUpload.dict_id == compiled.dict_id,
        )
        if cabin_layout:
            delete_query = delete_query.filter(WorkcardCleanLocalUpload.cabin_layout == cabin_layout)
        else:
            delete_query = delete_query.filter(WorkcardCleanLocalUpload.cabin_layout.is_(None))
        delete_query.delete(synchronize_session=False)
        self.db.flush()

        for r in out_rows:
            self.db.add(
                WorkcardCleanLocalUpload(
                    configuration_id=configuration_id,
                    dict_id=compiled.dict_id,
                    dict_version=compiled.version,
                    workcard_number=r.get("workcard_number"),
                    description_en=r.get("description_en"),
                    description_cn=r.get("description_cn"),
                    main_component=r.get("main_component"),
                    sub_component=r.get("sub_component"),
                    location=r.get("location"),
                    orientation=r.get("orientation"),
                    status=r.get("status"),
                    action=r.get("action"),
                    error=r.get("error"),
                    cabin_layout=cabin_layout,
                )
            )

        self.db.commit()
        return compiled, total, cleaned, skipped

    def clean_defects_in_list(
        self,
        defect_list_id: int,
        configuration_id: int,
        dict_id: Optional[int] = None,
    ) -> Tuple[CompiledDict, List[DefectCleanLocal], int, int, int]:
        d = self.get_dict(dict_id) if dict_id else self.get_latest_dict_for_configuration(configuration_id)
        if not d:
            raise ValueError("未找到该构型可用的关键词字典版本，请先在关键词管理中创建/导入词典")
        compiled = self.compile_dict(d.id)

        defects = self.db.query(DefectRecord).filter(DefectRecord.defect_list_id == defect_list_id).all()

        self.db.query(DefectCleanLocal).filter(
            DefectCleanLocal.configuration_id == configuration_id,
            DefectCleanLocal.dict_id == d.id,
            DefectCleanLocal.defect_record_id.in_([dr.id for dr in defects]) if defects else False,
        ).delete(synchronize_session=False)
        self.db.flush()

        total = len(defects)
        cleaned = 0
        skipped = 0
        created: List[DefectCleanLocal] = []

        for dr in defects:
            desc_en, desc_cn = self._extract_defect_descriptions(dr)
            if not _safe_str(desc_en):
                skipped += 1
                continue
            result = self.clean_jobcard_en(desc_en, compiled)
            row = DefectCleanLocal(
                defect_record_id=dr.id,
                aircraft_type=None,  # defect_records 不存 aircraft_type；需要时可从配置/批次信息补
                configuration_id=configuration_id,
                dict_id=d.id,
                dict_version=d.version,
                description_en=desc_en,
                description_cn=desc_cn,
                main_component=result["main_component"],
                sub_component=result["sub_component"],
                location=result["location"],
                orientation=result["orientation"],
                status=result["status"],
                action=result.get("action"),
            )
            self.db.add(row)
            created.append(row)
            cleaned += 1

        self.db.commit()
        return compiled, created, total, cleaned, skipped

    def get_available_cleaned_defect_lists(
        self,
        configuration_id: int,
        dict_id: Optional[int] = None,
    ) -> List[Dict]:
        """获取指定构型下所有已执行本地清洗的缺陷清单"""
        d = self.get_dict(dict_id) if dict_id else self.get_latest_dict_for_configuration(configuration_id)
        if not d:
            return []
            
        # 查询 defect_clean_local 中存在的 defect_record -> defect_list
        from app.models.defect import DefectList, DefectRecord
        query = (
            self.db.query(DefectList.id, DefectList.title)
            .join(DefectRecord, DefectRecord.defect_list_id == DefectList.id)
            .join(DefectCleanLocal, DefectCleanLocal.defect_record_id == DefectRecord.id)
            .filter(
                DefectCleanLocal.configuration_id == configuration_id,
                DefectCleanLocal.dict_id == d.id
            )
            .distinct()
        )
        
        rows = query.all()
        return [{"id": r.id, "title": r.title} for r in rows]

    def get_cleaned_defects(
        self,
        defect_list_id: int,
        configuration_id: int,
        dict_id: Optional[int] = None,
    ) -> List[DefectCleanLocal]:
        """直接获取已保存的本地清洗结果"""
        d = self.get_dict(dict_id) if dict_id else self.get_latest_dict_for_configuration(configuration_id)
        if not d:
            return []
            
        from app.models.defect import DefectRecord
        rows = (
            self.db.query(DefectCleanLocal)
            .join(DefectRecord, DefectRecord.id == DefectCleanLocal.defect_record_id)
            .filter(
                DefectRecord.defect_list_id == defect_list_id,
                DefectCleanLocal.configuration_id == configuration_id,
                DefectCleanLocal.dict_id == d.id
            )
            .all()
        )
        return rows

    def delete_cabin_layout(
        self,
        configuration_id: int,
        cabin_layout: str,
        source: str = "upload", # "upload" or "history"
    ) -> bool:
        """删除指定的客舱布局清洗数据，并同步清除相关的匹配结果"""
        Model = WorkcardCleanLocalUpload if source == "upload" else WorkcardCleanLocal
        
        # 1. 删除工卡清洗记录
        self.db.query(Model).filter(
            Model.configuration_id == configuration_id,
            Model.cabin_layout == cabin_layout
        ).delete(synchronize_session=False)

        # 2. 删除相关的匹配结果
        self.db.query(DefectMatchLocal).filter(
            DefectMatchLocal.configuration_id == configuration_id,
            DefectMatchLocal.cabin_layout == cabin_layout
        ).delete(synchronize_session=False)

        self.db.commit()
        return True

    def delete_cleaned_defect_list(
        self,
        defect_list_id: int,
        configuration_id: int,
        dict_id: Optional[int] = None,
    ) -> bool:
        """删除指定缺陷清单的结构化清洗结果，并同步清除相关的匹配结果"""
        d = self.get_dict(dict_id) if dict_id else self.get_latest_dict_for_configuration(configuration_id)
        if not d:
            return False
            
        from app.models.defect import DefectRecord
        
        # 1. 获取该清单下的记录ID
        dr_ids = [r.id for r in self.db.query(DefectRecord.id).filter(DefectRecord.defect_list_id == defect_list_id).all()]
        if not dr_ids:
            return True

        # 2. 删除清洗记录
        self.db.query(DefectCleanLocal).filter(
            DefectCleanLocal.defect_record_id.in_(dr_ids),
            DefectCleanLocal.configuration_id == configuration_id,
            DefectCleanLocal.dict_id == d.id
        ).delete(synchronize_session=False)

        # 3. 删除相关的匹配结果 (不分客舱布局，全部删掉)
        self.db.query(DefectMatchLocal).filter(
            DefectMatchLocal.defect_record_id.in_(dr_ids),
            DefectMatchLocal.configuration_id == configuration_id,
            DefectMatchLocal.dict_id == d.id
        ).delete(synchronize_session=False)

        self.db.commit()
        return True

    # ---------- matching ----------
    def _calculate_keyword_match_bonus(self, target_text: str, candidate_text: str) -> float:
        """
        计算智能关键词匹配奖分 (算法 2.0)
        1. 关键词覆盖率 (Recall): 目标词在候选词中的占比 (5分池)
        2. 描述紧凑度 (Precision): 匹配词在候选词中的比例 (2分池)
        总分7分，返回0-1的归一化值
        """
        if not target_text or not candidate_text:
            return 0.0
            
        def get_tokens(text):
            # 改进正则：保留单字母单词 (如 P, L, R)
            return set(re.findall(r'\b\w+\b', text.lower()))

        target_tokens = get_tokens(target_text)
        candidate_tokens = get_tokens(candidate_text)
        
        if not target_tokens:
            return 0.0
            
        # 计算交集
        intersection = target_tokens.intersection(candidate_tokens)
        
        # A. 覆盖率 (Recall) - 目标词被命中了多少
        recall_ratio = len(intersection) / len(target_tokens)
        coverage_score = 0.0
        if recall_ratio >= 0.8:
            coverage_score = 5.0
        elif recall_ratio >= 0.7:
            coverage_score = 3.0
            
        # B. 紧凑度 (Precision) - 候选词里有多少是多余的
        # 这里使用 2 分池，按比例分配
        precision_ratio = len(intersection) / len(candidate_tokens) if candidate_tokens else 0
        compactness_score = precision_ratio * 2.0
        
        # 总分为 7 分 (对应 0.07 的权重)
        # 将其归一化为 0-1 范围，乘以权重后即为最终得分贡献
        # 为了保证 100% 匹配时这部分拿满 7 分，返回 (5+2)/7 = 1.0
        total_bonus_points = coverage_score + compactness_score
        return total_bonus_points / 7.0

    def _score_pair(
        self,
        defect: DefectCleanLocal,
        wc: WorkcardCleanLocal,
    ) -> Optional[Dict[str, float]]:
        """
        匹配阈值：>=85 才算候选
        权重（调整后，腾出7分给智能匹配）：
        - main 32.55 (原35 * 0.93)
        - sub 46.5 (原50 * 0.93) - 支持混合策略
        - location 2.79 (原3 * 0.93)
        - orientation 1.86 (原2 * 0.93)
        - status 4.65 (原5 * 0.93)
        - action 4.65 (原5 * 0.93)
        - keyword_match_bonus 7.0 (新增智能匹配奖励)
        
        匹配规则：
        - main_component 支持多值匹配策略：
          * 双方都没有：返回 None（不匹配）
          * 只有一方有：给部分分 20.0（部分匹配）
          * 双方都有：按交集匹配
            - 完全匹配（所有关键词都匹配）：32.55 分（满分）
            - 匹配到 2 个及以上关键词：30.0 分（高分）
            - 匹配到 1 个关键词：25.0 分（中等分）
            - 无交集：返回 None（不匹配）
        - sub_component 支持混合策略：
          * 双方都没有：给基础分30.0（视为匹配）
          * 双方都有：按交集匹配（2个=46.5，1个=41.85，0个=0且返回None）
          * 只有一方有：给部分分20.0（视为部分匹配）
        """
        # main_component 多值匹配策略
        defect_has_main = defect.main_component and defect.main_component.strip()
        wc_has_main = wc.main_component and wc.main_component.strip()
        
        # 情况1：双方都没有（罕见情况，直接拒绝）
        if not defect_has_main and not wc_has_main:
            return None
        
        # 情况2：只有一方有（部分匹配）
        if not defect_has_main or not wc_has_main:
            score_main = 20.0
        else:
            # 情况3：双方都有，计算交集
            defect_mains = {m.strip().lower() for m in defect.main_component.split(",") if m.strip()}
            wc_mains = {m.strip().lower() for m in wc.main_component.split(",") if m.strip()}
            intersection = defect_mains & wc_mains
            
            match_count = len(intersection)
            
            if match_count == 0:
                # 无交集，不匹配
                return None
            
            # 完全匹配：所有关键词都匹配
            if defect_mains == wc_mains:
                score_main = round(35.0 * 0.93, 2)  # 32.55 满分
            elif match_count >= 2:
                # 多个关键词匹配，高分
                score_main = 30.0
            else:  # match_count == 1
                # 单个关键词匹配，中等分
                score_main = 25.0
        
        # 先计算其他字段的基础分数
        score_location = round(3.0 * 0.93, 2) if defect.location and wc.location and defect.location == wc.location else 0.0  # 2.79
        score_orientation = round(2.0 * 0.93, 2) if defect.orientation and wc.orientation and defect.orientation == wc.orientation else 0.0  # 1.86
        score_status = round(5.0 * 0.93, 2) if defect.status and wc.status and defect.status == wc.status else 0.0  # 4.65
        score_action = (
            round(5.0 * 0.93, 2)  # 4.65
            if getattr(defect, "action", None)
            and getattr(wc, "action", None)
            and defect.action == wc.action
            else 0.0
        )

        # 计算智能关键词匹配奖励（7分池）
        defect_desc_en = getattr(defect, "description_en", "") or ""
        wc_desc_en = getattr(wc, "description_en", "") or ""
        keyword_match_bonus_ratio = self._calculate_keyword_match_bonus(defect_desc_en, wc_desc_en)
        score_keyword_match = round(keyword_match_bonus_ratio * 7.0, 2)
        
        # sub_component 混合策略匹配
        defect_has_sub = defect.sub_component and defect.sub_component.strip()
        wc_has_sub = wc.sub_component and wc.sub_component.strip()
        
        if not defect_has_sub and not wc_has_sub:
            # 情况1：双方都没有 sub_component，将子部件分数上限（46.5分）分配给其他有匹配的字段
            sub_component_weight = round(50.0 * 0.93, 2)  # 46.5
            
            # 统计有匹配的字段（包括main）
            matched_fields = []
            matched_fields.append("main")  # main总是匹配的，也参与分配
            if score_location > 0:
                matched_fields.append("location")
            if score_orientation > 0:
                matched_fields.append("orientation")
            if score_status > 0:
                matched_fields.append("status")
            if score_action > 0:
                matched_fields.append("action")
            if score_keyword_match > 0:
                matched_fields.append("keyword_match")
            
            # 将子部件的分数上限（46.5分）平均分配给匹配的字段（精确到2位小数）
            bonus_per_field = round(sub_component_weight / len(matched_fields), 2)
            
            # 给匹配的字段增加分数上限（直接加到当前分数上）
            if "main" in matched_fields:
                score_main = round(score_main + bonus_per_field, 2)
            if "location" in matched_fields:
                score_location = round(score_location + bonus_per_field, 2)
            if "orientation" in matched_fields:
                score_orientation = round(score_orientation + bonus_per_field, 2)
            if "status" in matched_fields:
                score_status = round(score_status + bonus_per_field, 2)
            if "action" in matched_fields:
                score_action = round(score_action + bonus_per_field, 2)
            if "keyword_match" in matched_fields:
                score_keyword_match = round(score_keyword_match + bonus_per_field, 2)
            
            score_sub = 0.0  # sub_component 本身不给分，分数已分配给其他字段
        elif defect_has_sub and wc_has_sub:
            # 情况2：双方都有 sub_component，按交集匹配
            defect_subs = {s.strip().lower() for s in defect.sub_component.split(",") if s.strip()}
            wc_subs = {s.strip().lower() for s in wc.sub_component.split(",") if s.strip()}
            sub_intersection = defect_subs & wc_subs
            
            match_count = len(sub_intersection)
            if match_count >= 2:
                score_sub = round(50.0 * 0.93, 2)  # 46.5
            elif match_count == 1:
                score_sub = round(45.0 * 0.93, 2)  # 41.85
            else:
                # 双方都有但不匹配，视为不匹配
                score_sub = 0.0
                return None
        else:
            # 情况3：只有一方有 sub_component，给部分分数（视为部分匹配）
            score_sub = 25.0

        total = round(score_main + score_sub + score_location + score_orientation + score_status + score_action + score_keyword_match, 2)
        
        # 确保总分不超过100分
        if total > 100.0:
            total = 100.0
        
        # 返回50分以上的候选工卡（用于前端展示），但只有 >= 85 分的才会保存到数据库
        if total < 50.0:
            return None
        return {
            "score_total": total,
            "score_main": score_main,
            "score_sub": score_sub,
            "score_location": score_location,
            "score_orientation": score_orientation,
            "score_status": score_status,
            "score_action": score_action,
            "score_keyword_match": score_keyword_match,
        }

    def match_defects(
        self,
        defect_list_id: int,
        configuration_id: int,
        dict_id: Optional[int] = None,
        source: str = "upload",
        cabin_layout: Optional[str] = None,
    ) -> Tuple[CompiledDict, List[Dict]]:
        # ensure cleaned data exists (for dict/version)
        d = self.get_dict(dict_id) if dict_id else self.get_latest_dict_for_configuration(configuration_id)
        if not d:
            raise ValueError("未找到该构型可用的关键词字典版本，请先在关键词管理中创建/导入词典")
        compiled = self.compile_dict(d.id)

        defect_cleaned = (
            self.db.query(DefectCleanLocal)
            .join(DefectRecord, DefectRecord.id == DefectCleanLocal.defect_record_id)
            .filter(
                DefectRecord.defect_list_id == defect_list_id,
                DefectCleanLocal.configuration_id == configuration_id,
                DefectCleanLocal.dict_id == d.id,
            )
            .all()
        )

        Model = WorkcardCleanLocalUpload if source == "upload" else WorkcardCleanLocal
        workcard_query = self.db.query(Model).filter(
            Model.configuration_id == configuration_id,
            Model.dict_id == d.id,
        )
        if cabin_layout is not None:
            workcard_query = workcard_query.filter(Model.cabin_layout == cabin_layout)
        workcard_cleaned = workcard_query.all()

        # 清除旧候选（按 defect_list_id 对应 defect_record_id 集合 + cabin_layout）
        defect_record_ids = [r.defect_record_id for r in defect_cleaned]
        if defect_record_ids:
            self.db.query(DefectMatchLocal).filter(
                DefectMatchLocal.configuration_id == configuration_id,
                DefectMatchLocal.dict_id == d.id,
                DefectMatchLocal.defect_record_id.in_(defect_record_ids),
                DefectMatchLocal.cabin_layout == cabin_layout,
            ).delete(synchronize_session=False)
            self.db.flush()

        # build wc lookup by main_component for speed
        wc_by_main: Dict[str, List] = {}
        for wc in workcard_cleaned:
            if wc.main_component:
                wc_by_main.setdefault(wc.main_component, []).append(wc)

        results: List[Dict] = []

        for defect in defect_cleaned:
            dr = self.db.query(DefectRecord).filter(DefectRecord.id == defect.defect_record_id).first()
            defect_number = dr.defect_number if dr else ""

            candidates = []
            if defect.main_component and defect.main_component in wc_by_main:
                for wc in wc_by_main[defect.main_component]:
                    score = self._score_pair(defect, wc)
                    if not score:
                        continue
                    candidates.append((wc, score))

            # sort by total desc
            candidates.sort(key=lambda x: x[1]["score_total"], reverse=True)

            # persist candidates (only >= 85) and collect all candidates (>= 50) for UI
            out_candidates = []
            for wc, sc in candidates:
                # 如果是历史库，由 workcard_id 关联；如果是上传库，workcard_id 可能为空或 0
                wc_id = getattr(wc, "workcard_id", None)
                wc_no = getattr(wc, "workcard_number", "")
                
                # 为存储及 UI 准备描述
                wc_cn = getattr(wc, "description_cn", "") or ""
                wc_en = getattr(wc, "description_en", "") or ""
                
                if not wc_cn and not wc_en and wc_id:
                    w_obj = self.db.query(WorkCard).filter(WorkCard.id == wc_id).first()
                    if w_obj:
                        wc_cn = w_obj.title or ""
                        wc_en = w_obj.description or ""

                # 只有 >= 85 分的才保存到数据库
                if sc["score_total"] >= 85.0:
                    # 准备保存的分数字典（移除 score_keyword_match，因为模型中没有该字段）
                    score_dict = {k: v for k, v in sc.items() if k != "score_keyword_match"}
                    
                    self.db.add(
                        DefectMatchLocal(
                            defect_record_id=defect.defect_record_id,
                            workcard_id=wc_id,
                            aircraft_type=getattr(wc, "aircraft_type", None),
                            configuration_id=configuration_id,
                            dict_id=d.id,
                            dict_version=d.version,
                            description_en=defect.description_en,
                            description_cn=defect.description_cn,
                            candidate_desc_en=wc_en,
                            candidate_desc_cn=wc_cn,
                            workcard_number=wc_no,
                            cabin_layout=cabin_layout,
                            **score_dict,
                        )
                    )
                
                # 所有 >= 50 分的候选工卡都添加到返回结果中（用于前端展示）
                out_candidates.append(
                    {
                        "id": wc.id,
                        "workcard_number": wc_no,
                        "description": wc_cn,
                        "description_en": wc_en,
                        "similarity_score": sc["score_total"],
                    }
                )

            results.append(
                {
                    "defect_record_id": defect.defect_record_id,
                    "defect_number": defect_number,
                    "description_cn": defect.description_cn or "",
                    "description_en": defect.description_en or "",
                    "main_component": defect.main_component,
                    "sub_component": defect.sub_component,
                    "location": defect.location,
                    "orientation": defect.orientation,
                    "status": defect.status,
                    "action": defect.action,
                    "candidates": out_candidates,
                }
            )

        self.db.commit()
        return compiled, results




    def get_clean_workcards(
        self,
        configuration_id: int,
        dict_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
        source: str = "upload",  # "upload" or "history"
        cabin_layout: Optional[str] = None,
    ) -> Tuple[List, int]:
        """
        分页查询已清洗并落库的工卡数据。
        source="upload" -> 查询 WorkcardCleanLocalUpload
        source="history" -> 查询 WorkcardCleanLocal
        返回 (list_rows, total_count)
        """
        Model = WorkcardCleanLocalUpload if source == "upload" else WorkcardCleanLocal
        
        query = self.db.query(Model).filter(
            Model.configuration_id == configuration_id
        )
        if dict_id:
            query = query.filter(Model.dict_id == dict_id)
        if cabin_layout is not None:
            query = query.filter(Model.cabin_layout == cabin_layout)
            
        total = query.count()
        rows = query.offset(skip).limit(limit).all()
        return rows, total

    def get_available_cabin_layouts(
        self,
        configuration_id: int,
        source: str = "upload",
    ) -> List[str]:
        """
        获取指定配置下所有可用的客舱布局列表
        """
        Model = WorkcardCleanLocalUpload if source == "upload" else WorkcardCleanLocal
        
        # 查询所有不为NULL的cabin_layout，去重
        layouts = (
            self.db.query(Model.cabin_layout)
            .filter(
                Model.configuration_id == configuration_id,
                Model.cabin_layout.isnot(None),
                Model.cabin_layout != ''
            )
            .distinct()
            .all()
        )
        
        return [layout[0] for layout in layouts if layout[0]]

    def get_match_stats(
        self,
        defect_list_id: int,
        configuration_id: int,
        dict_id: int,
        cabin_layout: Optional[str] = None,
    ) -> Dict:
        """获取匹配统计信息"""
        total = self.db.query(DefectRecord).filter(DefectRecord.defect_list_id == defect_list_id).count()
        # 有匹配的个数（在 DefectMatchLocal 中有对应记录的 defect_record_id 个数）
        matched = (
            self.db.query(DefectMatchLocal.defect_record_id)
            .join(DefectRecord, DefectRecord.id == DefectMatchLocal.defect_record_id)
            .filter(
                DefectRecord.defect_list_id == defect_list_id,
                DefectMatchLocal.configuration_id == configuration_id,
                DefectMatchLocal.dict_id == dict_id,
                DefectMatchLocal.cabin_layout == cabin_layout,
            )
            .distinct()
            .count()
        )
        return {
            "total_defects": total,
            "matched_defects": matched,
            "unmatched_defects": total - matched,
            "match_rate": round(matched / total * 100, 2) if total > 0 else 0,
        }

    def export_matched_defects(
        self,
        defect_list_id: int,
        configuration_id: int,
        dict_id: int,
        cabin_layout: Optional[str] = None,
    ) -> bytes:
        """导出匹配结果 Excel"""
        import pandas as pd
        import io
        from sqlalchemy import func

        # 1. 获取所有缺陷记录
        dr_list = self.db.query(DefectRecord).filter(DefectRecord.defect_list_id == defect_list_id).all()
        
        # 2. 获取每个缺陷的最佳匹配（分值最高那个）
        subq = (
            self.db.query(
                DefectMatchLocal.defect_record_id,
                func.max(DefectMatchLocal.score_total).label("max_score")
            )
            .join(DefectRecord, DefectRecord.id == DefectMatchLocal.defect_record_id)
            .filter(
                DefectRecord.defect_list_id == defect_list_id,
                DefectMatchLocal.configuration_id == configuration_id,
                DefectMatchLocal.dict_id == dict_id,
                DefectMatchLocal.cabin_layout == cabin_layout
            )
            .group_by(DefectMatchLocal.defect_record_id)
            .subquery()
        )
        
        best_matches = (
            self.db.query(DefectMatchLocal)
            .join(subq, (DefectMatchLocal.defect_record_id == subq.c.defect_record_id) & (DefectMatchLocal.score_total == subq.c.max_score))
            .filter(
                DefectMatchLocal.configuration_id == configuration_id,
                DefectMatchLocal.dict_id == dict_id,
                DefectMatchLocal.cabin_layout == cabin_layout
            )
            .all()
        )
        
        # 转为 map 方便查找，去重
        match_map = {}
        for m in best_matches:
            if m.defect_record_id not in match_map:
                match_map[m.defect_record_id] = m
        
        rows = []
        for dr in dr_list:
            data = dr.raw_data if dr.raw_data else {}
            # 确保是 dict，如果是字符串则尝试解析
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except:
                    data = {"original_error": "JSON parse error", "raw": data}
            
            m = match_map.get(dr.id)
            if m:
                # 按照用户要求映射字段
                data["Candidate Workcard Instruction Number"] = m.workcard_number or ""
                data["Candidate Workcard Description (English)"] = m.candidate_desc_en or ""
                data["Candidate Workcard Description (Chinese)"] = m.candidate_desc_cn or ""
            else:
                # 没匹配上也填充空，保持列存在
                data.setdefault("Candidate Workcard Instruction Number", "")
                data.setdefault("Candidate Workcard Description (English)", "")
                data.setdefault("Candidate Workcard Description (Chinese)", "")
            
            # 重命名列：移除中文列名中的括号
            # 工卡描述（中文）或 工卡描述(中文) -> 工卡描述中文
            if "工卡描述（中文）" in data:
                data["工卡描述中文"] = data.pop("工卡描述（中文）")
            elif "工卡描述(中文)" in data:
                data["工卡描述中文"] = data.pop("工卡描述(中文)")
            
            # 工卡描述（英文）或 工卡描述(英文) -> 工卡描述英文
            if "工卡描述（英文）" in data:
                data["工卡描述英文"] = data.pop("工卡描述（英文）")
            elif "工卡描述(英文)" in data:
                data["工卡描述英文"] = data.pop("工卡描述(英文)")
            
            # 候选工卡列的内容应该是 Candidate Workcard Instruction Number 的值
            if "Candidate Workcard Instruction Number" in data:
                data["候选工卡"] = data["Candidate Workcard Instruction Number"]
            
            rows.append(data)
            
        if not rows:
            df = pd.DataFrame(columns=["Candidate Workcard Instruction Number", "Candidate Workcard Description (English)", "Candidate Workcard Description (Chinese)"])
        else:
            df = pd.DataFrame(rows)
        
        # 确保列名重命名也应用到DataFrame（处理可能存在的其他列名变体）
        column_rename_map = {}
        for col in df.columns:
            if col == "工卡描述（中文）" or col == "工卡描述(中文)":
                column_rename_map[col] = "工卡描述中文"
            elif col == "工卡描述（英文）" or col == "工卡描述(英文)":
                column_rename_map[col] = "工卡描述英文"
        
        if column_rename_map:
            df = df.rename(columns=column_rename_map)
        
        # 确保候选工卡列存在，内容来自 Candidate Workcard Instruction Number
        if "Candidate Workcard Instruction Number" in df.columns:
            df["候选工卡"] = df["Candidate Workcard Instruction Number"]
        
        # 定义列的顺序（按照用户要求的顺序）
        ordered_columns = [
            "缺陷编号",
            "工卡描述中文",
            "工卡描述英文",
            "相关工卡号",
            "相关工卡序号",
            "区域",
            "区域号",
            "候选工卡",
            "工卡描述",
            "工卡描述已开工卡号"
        ]
        
        # 确保所有ordered_columns中的列都存在（如果不存在则添加空列）
        for col in ordered_columns:
            if col not in df.columns:
                df[col] = ""
        
        # 删除 Candidate Workcard Instruction Number 列（如果存在）
        if "Candidate Workcard Instruction Number" in df.columns:
            df = df.drop(columns=["Candidate Workcard Instruction Number"])
        
        # 获取所有现有列（包括ordered_columns中没有的列）
        existing_columns = list(df.columns)
        
        # 先添加ordered_columns中存在的列（按顺序）
        final_columns = []
        for col in ordered_columns:
            if col in existing_columns:
                final_columns.append(col)
        
        # 然后添加其他未在ordered_columns中的列（保持原有顺序）
        for col in existing_columns:
            if col not in final_columns:
                final_columns.append(col)
        
        # 重新排列列的顺序
        df = df[final_columns]
        
        # 确保"相关工卡序号"列保持为字符串格式，保留前导零
        # 识别可能的列名变体
        workcard_item_keywords = [
            '相关工卡序号', 'Item No', 'Ref No', 'Reference Item',
            'item_no', 'ref_no', 'reference_item',
            'ItemNo', 'RefNo', 'ReferenceItem'
        ]
        
        def format_workcard_item(value):
            """格式化工卡序号，保留前导零"""
            if pd.isna(value) or value == '' or value is None:
                return ''
            # 如果已经是字符串，直接返回（保留原始格式）
            if isinstance(value, str):
                return value
            # 如果是数字，格式化为5位字符串（补零）
            try:
                num = int(float(value))
                return f"{num:05d}"  # 格式化为5位数字，不足补零
            except (ValueError, TypeError):
                return str(value)
        
        # 查找并处理"相关工卡序号"列（支持多种列名变体）
        for col in df.columns:
            col_str = str(col).strip()
            for keyword in workcard_item_keywords:
                if keyword.lower() in col_str.lower() or col_str == keyword:
                    df[col] = df[col].apply(format_workcard_item)
                    break
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        
        return output.getvalue()

    def export_cleaned_workcards(
        self,
        configuration_id: int,
        dict_id: Optional[int] = None,
        source: str = "history",
        cabin_layout: Optional[str] = None,
    ) -> bytes:
        """导出已清洗的历史工卡客舱部件到Excel"""
        import pandas as pd
        import io

        Model = WorkcardCleanLocalUpload if source == "upload" else WorkcardCleanLocal
        query = self.db.query(Model).filter(
            Model.configuration_id == configuration_id,
        )
        
        if dict_id:
            query = query.filter(Model.dict_id == dict_id)
        
        if cabin_layout:
            query = query.filter(Model.cabin_layout == cabin_layout)
        
        workcards = query.all()
        
        if not workcards:
            # 返回空Excel
            df = pd.DataFrame(columns=[
                "工卡号", "主部件", "子部件", "位置", "方位", "状态", "动作",
                "英文描述", "中文描述", "客舱布局"
            ])
        else:
            rows = []
            for wc in workcards:
                rows.append({
                    "工卡号": wc.workcard_number or "",
                    "主部件": wc.main_component or "",
                    "子部件": wc.sub_component or "",
                    "位置": wc.location or "",
                    "方位": wc.orientation or "",
                    "状态": wc.status or "",
                    "动作": getattr(wc, "action", None) or "",
                    "英文描述": wc.description_en or "",
                    "中文描述": wc.description_cn or "",
                    "客舱布局": getattr(wc, "cabin_layout", None) or "",
                })
            df = pd.DataFrame(rows)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='已清洗工卡')
        
        return output.getvalue()
