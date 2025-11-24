import json
import logging
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode, quote

import requests
import urllib3

from app.core.config import settings

# 按需禁用SSL告警（默认VPN证书不受信任）
if not settings.WORKCARD_IMPORT_VERIFY_SSL:
    urllib3.disable_warnings()


@dataclass
class WorkcardInfo:
    rid: str
    index: int


@dataclass
class HistoryWorkcardInfo(WorkcardInfo):
    phase: str = ""
    zone: str = ""
    trade: str = ""


@dataclass
class StepInfo:
    """工卡步骤信息"""
    rid: str
    index: int
    phase: str = ""
    zone: str = ""
    trade: str = ""
    txt_area: str = ""


@dataclass
class LogEntry:
    step: str
    message: str
    detail: Optional[Any] = None


@dataclass
class Artifact:
    step: str
    filename: str
    path: str


@dataclass
class WorkCardImportPreview:
    workcards: List[WorkcardInfo] = field(default_factory=list)
    history_cards: List[HistoryWorkcardInfo] = field(default_factory=list)
    logs: List[LogEntry] = field(default_factory=list)
    artifacts: List[Artifact] = field(default_factory=list)

    def dict(self) -> Dict[str, Any]:
        return {
            "workcards": [asdict(item) for item in self.workcards],
            "history_cards": [asdict(item) for item in self.history_cards],
            "logs": [asdict(item) for item in self.logs],
            "artifacts": [asdict(item) for item in self.artifacts],
        }


@dataclass
class WorkCardImportResult:
    success: bool
    message: str
    logs: List[LogEntry] = field(default_factory=list)
    artifacts: List[Artifact] = field(default_factory=list)
    workcards: List[WorkcardInfo] = field(default_factory=list)
    history_cards: List[HistoryWorkcardInfo] = field(default_factory=list)
    selected_workcard: Optional[WorkcardInfo] = None
    selected_history_card: Optional[HistoryWorkcardInfo] = None

    def dict(self) -> Dict[str, Any]:
        result = {
            "success": self.success,
            "message": self.message,
            "logs": [asdict(item) for item in self.logs],
            "artifacts": [asdict(item) for item in self.artifacts],
            "workcards": [asdict(item) for item in self.workcards],
            "history_cards": [asdict(item) for item in self.history_cards],
        }
        if self.selected_workcard:
            result["selected_workcard"] = asdict(self.selected_workcard)
        if self.selected_history_card:
            result["selected_history_card"] = asdict(self.selected_history_card)
        return result


@dataclass
class WorkCardImportParams:
    tail_no: str
    src_work_order: str
    target_work_order: str
    work_group: str
    workcard_index: int = 0
    history_card_index: int = 0
    workcard_rid: Optional[str] = None
    history_rid: Optional[str] = None
    cookies: Optional[str] = None


class WorkCardImportService:
    """工卡批量导入工作流封装"""

    _STEP_QUERY = "query_workorder"
    _STEP_DIALOG = "open_import_dialog"
    _STEP_HISTORY = "query_history"
    _STEP_IMPORT = "import_workcard"
    _STEP_GET_JCRID = "get_jcrid_by_jobcard"
    _STEP_QUERY_STEPS = "query_steps"
    _STEP_IMPORT_STEP = "import_step"

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        base = settings.WORKCARD_IMPORT_BASE_URL.rstrip("/")
        self.urls = {
            "query": f"{base}/Web/trace/fgm/workOrder/checkData.jsp,CVPNHost=10.240.2.131:9080,CVPNProtocol=http,CVPNOrg=rel,CVPNExtension=.jsp?from=manage",
            "dialog": f"{base}/Web/trace/fgm/workOrder/jobcard/copy/bathImportNrcStep.jsp,CVPNHost=10.240.2.131:9080,CVPNProtocol=http,CVPNOrg=rel,CVPNExtension=.jsp",
            "import": f"{base}/Web/trace/fgm/workOrder/jobcard/copy/doBathImportNrcStep.jsp,CVPNHost=10.240.2.131:9080,CVPNProtocol=http,CVPNOrg=rel,CVPNExtension=.jsp",
        }
        output_dir = Path(settings.WORKCARD_IMPORT_OUTPUT_DIR)
        if settings.WORKCARD_IMPORT_SAVE_HTML:
            output_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir = output_dir

    # ------------------------------------------------------------------ #
    # 公共入口
    # ------------------------------------------------------------------ #
    def preview(self, params: WorkCardImportParams) -> WorkCardImportPreview:
        """获取可导入工卡及历史工卡信息"""
        session = self._create_session(params.cookies)
        logs: List[LogEntry] = []
        artifacts: List[Artifact] = []

        html, workcards = self._step_query_workorder(
            session,
            tail_no=params.tail_no,
            work_order=params.src_work_order,
            work_group=params.work_group,
            logs=logs,
            artifacts=artifacts,
        )

        if not workcards:
            return WorkCardImportPreview(workcards=[], history_cards=[], logs=logs, artifacts=artifacts)

        target = self._select_workcard(workcards, params.workcard_rid, params.workcard_index, logs)

        _, history_cards = self._step_query_history_workcards(
            session,
            jc_rid=target.rid,
            work_order=params.target_work_order,
            work_group=params.work_group,
            logs=logs,
            artifacts=artifacts,
        )

        return WorkCardImportPreview(
            workcards=workcards,
            history_cards=history_cards,
            logs=logs,
            artifacts=artifacts,
        )

    def run_workflow(self, params: WorkCardImportParams) -> WorkCardImportResult:
        """执行完整导入流程"""
        session = self._create_session(params.cookies)
        logs: List[LogEntry] = []
        artifacts: List[Artifact] = []

        html, workcards = self._step_query_workorder(
            session,
            tail_no=params.tail_no,
            work_order=params.src_work_order,
            work_group=params.work_group,
            logs=logs,
            artifacts=artifacts,
        )

        if not workcards:
            message = "未查询到可导入的工卡"
            self._log(logs, self._STEP_QUERY, message)
            return WorkCardImportResult(
                success=False,
                message=message,
                logs=logs,
                artifacts=artifacts,
            )

        selected_workcard = self._select_workcard(
            workcards,
            params.workcard_rid,
            params.workcard_index,
            logs,
        )

        self._step_open_import_dialog(session, selected_workcard.rid, logs, artifacts)

        _, history_cards = self._step_query_history_workcards(
            session,
            jc_rid=selected_workcard.rid,
            work_order=params.target_work_order,
            work_group=params.work_group,
            logs=logs,
            artifacts=artifacts,
        )

        if not history_cards:
            message = "未查询到历史工卡，请确认目标工单号/工作组"
            self._log(logs, self._STEP_HISTORY, message)
            return WorkCardImportResult(
                success=False,
                message=message,
                logs=logs,
                artifacts=artifacts,
                workcards=workcards,
                history_cards=[],
                selected_workcard=selected_workcard,
            )

        selected_history = self._select_history_workcard(
            history_cards,
            params.history_rid,
            params.history_card_index,
            logs,
        )

        success, message = self._step_import_workcard(
            session,
            jc_rid=selected_workcard.rid,
            history_card=selected_history,
            work_order=params.target_work_order,
            work_group=params.work_group,
            logs=logs,
            artifacts=artifacts,
        )

        return WorkCardImportResult(
            success=success,
            message=message,
            logs=logs,
            artifacts=artifacts,
            workcards=workcards,
            history_cards=history_cards,
            selected_workcard=selected_workcard,
            selected_history_card=selected_history,
        )

    def test_connection(self, params: WorkCardImportParams) -> WorkCardImportResult:
        """测试外部系统连通性（固定 URL 简单验证）"""
        logs: List[LogEntry] = []
        artifacts: List[Artifact] = []

        session = self._create_session(params.cookies)

        callback = f"jsonp{int(datetime.now().timestamp() * 1000)}"
        base_url = (
            "https://vpn.gameco.com.cn/Web/trace/nrc/getACInfo.jsp"
            ",CVPNTransDest=0,CVPNHost=10.240.2.131:9080"
            ",CVPNProtocol=http,CVPNOrg=rel,CVPNExtension=.jsp"
        )
        query_params = {
            "txtFlag": "",
            "txtACNO": "GAM-GAM",
            "txtWO": "",
            "jsoncallback": callback,
        }
        headers = {
            "Accept": "text/javascript, application/javascript, */*",
            "Referer": "https://vpn.gameco.com.cn/Web/trace/nrc/fault/faultAdd.jsp,CVPNHost=10.240.2.131:9080,CVPNProtocol=http,CVPNOrg=rel,CVPNExtension=.jsp?txtParentID=13112&txtMenuID=13541",
            "X-Requested-With": "XMLHttpRequest",
        }
        expected_token = '"customerworkorder":"","wo":"120000036656","reg":"GAM-GAM"'

        # 记录请求信息
        self.logger.info("=" * 80)
        self.logger.info("开始连通性测试")
        self.logger.info(f"请求URL: {base_url}")
        self.logger.info(f"请求参数: {query_params}")
        self.logger.info(f"请求头: {headers}")
        self._log(logs, "test_connection", f"准备发送GET请求到: {base_url}")
        self._log(logs, "test_connection", f"请求参数: {query_params}")

        try:
            self.logger.info("发送GET请求...")
            response = session.get(
                base_url,
                params=query_params,
                headers=headers,
                verify=settings.WORKCARD_IMPORT_VERIFY_SSL,
                timeout=10
            )
            
            self.logger.info(f"收到响应，状态码: {response.status_code}")
            self.logger.info(f"响应头: {dict(response.headers)}")
            self.logger.info(f"响应大小: {len(response.content)} 字节")
            
            response.raise_for_status()
            content = response.text
            
            self.logger.info(f"响应内容长度: {len(content)} 字符")
            self.logger.info(f"响应内容（完整）:\n{content}")
            self.logger.info("=" * 80)

            success = expected_token in content
            if success:
                message = "连通性测试成功，已获取企业系统数据"
            else:
                message = "连通性测试失败：响应中未包含预期的工卡信息"
                self.logger.warning(f"预期token未找到: {expected_token}")
                self.logger.warning(f"实际响应内容: {content}")

            # 记录响应内容（限制大小）
            content_preview = content[:2000] if len(content) > 2000 else content
            self._log(logs, "test_connection", f"收到响应，状态码: {response.status_code}, 响应长度: {len(content)} 字符")
            self._log(logs, "test_connection", f"响应内容预览（前2000字符）: {content_preview}", detail=content_preview)
            if len(content) > 2000:
                self._log(logs, "test_connection", f"响应内容过长，已截断。完整内容请查看后端日志。")
            self._log(logs, "test_connection", message)

            return WorkCardImportResult(
                success=success,
                message=message,
                logs=logs,
                artifacts=artifacts,
            )
        except Exception as exc:
            import traceback
            error_traceback = traceback.format_exc()
            error_msg = f"连通性测试失败: {exc}"
            
            self.logger.error("=" * 80)
            self.logger.error("连通性测试失败")
            self.logger.error(f"错误信息: {error_msg}")
            self.logger.error(f"完整错误堆栈:\n{error_traceback}")
            self.logger.error("=" * 80)
            
            error_detail = error_traceback[:1000] if len(error_traceback) > 1000 else error_traceback
            logs.append(LogEntry(step="test_connection", message=error_msg, detail=error_detail))
            self.logger.exception("连通性测试失败")
            return WorkCardImportResult(
                success=False,
                message=error_msg,
                logs=logs,
                artifacts=artifacts,
            )

    # ------------------------------------------------------------------ #
    # 内部步骤
    # ------------------------------------------------------------------ #
    def _step_query_workorder(
        self,
        session: requests.Session,
        *,
        tail_no: str,
        work_order: str,
        work_group: str,
        logs: List[LogEntry],
        artifacts: List[Artifact],
    ) -> Tuple[Optional[str], List[WorkcardInfo]]:
        post_data = {
            "wgp": work_group,
            "printer": settings.WORKCARD_IMPORT_PRINTER,
            "txtMenuID": "22800",
            "txtFullReg": tail_no,
            "qWorkorder": work_order,
            "txtFlight_Check_No": "CRC2022",
            "txtVisit_Desc": "CRC2022",
            "txtIPC_Num": "",
            "txtMpd": "",
            "txtType": "",
            "txtSeq": "",
            "txtJobcard": "",
            "txtJcDesc": "",
            "txtQcFinal": "",
            "txtJcStatus": "",
            "txtSlnStatus": "",
            "txtImport": "",
            "txtBoothAss": "",
            "txtSlnPrinted": "",
            "preWorkGrp": "",
            "curWorkGrp": "",
            "schemeGrp": "",
            "txtUpdatedBy": "",
            "txtDangerousCargo": "",
            "txtSchedPhase": "",
            "txtSchedZone": "",
            "txtLaborCode": "",
            "txtTransferMode": "",
            "txtme_unUpload": "",
            "txtRii": "",
            "txtMatStatus": "",
            "txtFilterTrace": "",
            "txtJcRob": "",
            "txtPrDateStart": "",
            "txtPrDateEnd": "",
            "txtRTrade": "",
            "txtHoldBy": "",
            "txtJcTransferDateStart": "",
            "txtJcTransferDateEnd": "",
            "txtJcWorkorder": "",
            "txtSlnReqDateStart": "",
            "txtSlnReqDateEnd": "",
            "txtFlagMpd": "",
            "txtFlagActive": "",
            "txtExternal": "",
            "txtExteriorDamag": "",
            "txtMajorMdo": "",
            "txtOutOfManual": "",
            "txtStrRepair": "",
            "txtPse": "",
            "txtFcs": "",
            "txtCauseStrr": "",
            "txtRplStrPart": "",
            "txtQcStamp": "",
            "txtNmfTrade": "",
            "txtForbidEsign": "",
            "txtFedexAmtStamp": "",
            "txtFeeRemark": "",
            "txtFlagFee": "",
            "txtInspector": "",
            "txtSubShop": "",
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": settings.WORKCARD_IMPORT_BASE_URL,
            "Referer": f"{settings.WORKCARD_IMPORT_BASE_URL}/Web/trace/fgm/workOrder/manageIndex.jsp,CVPNHost=10.240.2.131:9080,CVPNProtocol=http,CVPNOrg=rel,CVPNExtension=.jsp?wgp={work_group}&txtParentID=10008&txtMenuID=22800",
        }

        try:
            # 添加请求间隔，避免请求频率过高导致连接断开
            time.sleep(2)
            response = session.post(
                self.urls["query"],
                data=post_data,
                headers=headers,
                verify=settings.WORKCARD_IMPORT_VERIFY_SSL,
                timeout=30,
            )
            response.encoding = "GBK"
            html = response.text
            self._log(
                logs,
                self._STEP_QUERY,
                f"查询工单成功，状态码 {response.status_code}，响应大小 {len(response.content)} 字节",
            )

            artifact = self._save_artifact("step1_query_result.html", html)
            if artifact:
                artifacts.append(Artifact(step=self._STEP_QUERY, filename=artifact.name, path=str(artifact)))

            workcards = self._parse_workcards(html)
            self._log(logs, self._STEP_QUERY, f"解析到 {len(workcards)} 条工卡")
            return html, workcards
        except Exception as exc:
            message = f"查询工单失败: {exc}"
            self._log(logs, self._STEP_QUERY, message)
            self.logger.exception(message)
            return None, []

    def _step_open_import_dialog(
        self,
        session: requests.Session,
        jc_rid: str,
        logs: List[LogEntry],
        artifacts: List[Artifact],
    ) -> Optional[str]:
        params = {"jcRidArr": jc_rid}
        headers = {
            "Referer": f"{settings.WORKCARD_IMPORT_BASE_URL}/Web/trace/fgm/workOrder/checkData.jsp,CVPNHost=10.240.2.131:9080,CVPNProtocol=http,CVPNOrg=rel,CVPNExtension=.jsp?from=manage",
        }

        try:
            # 添加请求间隔，避免请求频率过高导致连接断开
            time.sleep(2)
            response = session.get(
                self.urls["dialog"],
                params=params,
                headers=headers,
                verify=settings.WORKCARD_IMPORT_VERIFY_SSL,
                timeout=30,
            )
            response.encoding = "GBK"
            html = response.text
            self._log(
                logs,
                self._STEP_DIALOG,
                f"打开导入对话框成功，状态码 {response.status_code}",
            )
            artifact = self._save_artifact("step2_import_dialog.html", html)
            if artifact:
                artifacts.append(Artifact(step=self._STEP_DIALOG, filename=artifact.name, path=str(artifact)))
            return html
        except Exception as exc:
            message = f"打开导入对话框失败: {exc}"
            self._log(logs, self._STEP_DIALOG, message)
            self.logger.exception(message)
            return None

    def _step_query_history_workcards(
        self,
        session: requests.Session,
        *,
        jc_rid: str,
        work_order: str,
        work_group: str,
        logs: List[LogEntry],
        artifacts: List[Artifact],
    ) -> Tuple[Optional[str], List[HistoryWorkcardInfo]]:
        current_version = self._get_current_version(session, jc_rid, logs)
        post_data = {
            "isFrist": "no",
            "jcRidArr": jc_rid,
            "jcVidArr": str(current_version),
            "flnum": "GAM-GAM",
            "stepCtrl": "Y",
            "qJcWorkOrder": work_order,
            "qJobcard": "",
            "workGroup": work_group,
            "qRii": "",
            "qJcDesc": "",
            "qTrade": "",
            "qRemark": "",
            "txtArea": "空调舱",
            "txtPage": "1",
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": settings.WORKCARD_IMPORT_BASE_URL,
            "Referer": f"{self.urls['dialog']}?jcRidArr={jc_rid}",
        }

        try:
            # 添加请求间隔，避免请求频率过高导致连接断开
            time.sleep(2)
            response = session.post(
                self.urls["dialog"],
                data=post_data,
                headers=headers,
                verify=settings.WORKCARD_IMPORT_VERIFY_SSL,
                timeout=30,
            )
            response.encoding = "GBK"
            html = response.text
            self._log(
                logs,
                self._STEP_HISTORY,
                f"查询历史工卡成功，状态码 {response.status_code}，版本号 {current_version}",
            )
            artifact = self._save_artifact("step3_history_workcards.html", html)
            if artifact:
                artifacts.append(Artifact(step=self._STEP_HISTORY, filename=artifact.name, path=str(artifact)))

            history_cards = self._parse_history_workcards(html)
            self._log(logs, self._STEP_HISTORY, f"解析到 {len(history_cards)} 条历史工卡")
            return html, history_cards
        except Exception as exc:
            message = f"查询历史工卡失败: {exc}"
            self._log(logs, self._STEP_HISTORY, message)
            self.logger.exception(message)
            return None, []

    def _step_import_workcard(
        self,
        session: requests.Session,
        *,
        jc_rid: str,
        history_card: HistoryWorkcardInfo,
        work_order: str,
        work_group: str,
        logs: List[LogEntry],
        artifacts: List[Artifact],
    ) -> Tuple[bool, str]:
        current_version = self._get_current_version(session, jc_rid, logs)
        post_data = {
            "isFrist": "no",
            "jcRidArr": jc_rid,
            "jcVidArr": str(current_version),
            "flnum": "GAM-GAM",
            "stepCtrl": "Y",
            "qJcWorkOrder": work_order,
            "qJobcard": "",
            "workGroup": work_group,
            "qRii": "",
            "qJcDesc": "",
            "qTrade": "",
            "qRemark": "",
            "txtArea": "空调舱",
            "phase": history_card.phase,
            "zone": history_card.zone,
            "trade": history_card.trade,
            "rid": history_card.rid,
            "txtPage": "1",
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": settings.WORKCARD_IMPORT_BASE_URL,
            "Referer": self.urls["dialog"],
        }

        try:
            # 添加请求间隔，避免请求频率过高导致连接断开
            time.sleep(2)
            response = session.post(
                self.urls["import"],
                data=post_data,
                headers=headers,
                verify=settings.WORKCARD_IMPORT_VERIFY_SSL,
                timeout=30,
            )
            response.encoding = "GBK"
            html = response.text
            artifact = self._save_artifact("step4_import_result.html", html)
            if artifact:
                artifacts.append(Artifact(step=self._STEP_IMPORT, filename=artifact.name, path=str(artifact)))

            message_match = re.search(r'id="messageId" value="([^"]*)"', html)
            message = message_match.group(1) if message_match else "未获取到服务器返回信息"
            self._log(
                logs,
                self._STEP_IMPORT,
                f"导入完成，状态码 {response.status_code}，服务器消息：{message}",
            )

            if any(keyword in message for keyword in ["失败", "错误"]):
                return False, message
            if "成功" in message or "保存" in message:
                return True, message
            return False, message
        except Exception as exc:
            message = f"导入工卡失败: {exc}"
            self._log(logs, self._STEP_IMPORT, message)
            self.logger.exception(message)
            return False, message

    # ------------------------------------------------------------------ #
    # 辅助函数
    # ------------------------------------------------------------------ #
    def _create_session(self, raw_cookies: Optional[str] = None) -> requests.Session:
        session = requests.Session()
        # 不设置 proxies，让 requests 使用默认行为
        # 如果系统没有配置代理，就不会尝试使用代理，避免触发代理检测逻辑导致 FileNotFoundError
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9",
            }
        )
        cookies = self._parse_cookies(raw_cookies)
        for name, value in cookies.items():
            session.cookies.set(name, value)
        return session

    def _parse_cookies(self, raw: Optional[str] = None) -> Dict[str, str]:
        source = raw.strip() if isinstance(raw, str) else settings.WORKCARD_IMPORT_COOKIES.strip()
        if not source:
            return {}
        try:
            if source.startswith("{"):
                data = json.loads(source)
                return {str(k): str(v) for k, v in data.items()}
        except json.JSONDecodeError:
            self.logger.warning("WORKCARD_IMPORT_COOKIES 解析JSON失败，将按分号分割继续处理")

        cookies: Dict[str, str] = {}
        for segment in source.split(";"):
            if "=" not in segment:
                continue
            name, value = segment.split("=", 1)
            cookies[name.strip()] = value.strip()
        return cookies

    def _save_artifact(self, filename: str, content: str) -> Optional[Path]:
        if not settings.WORKCARD_IMPORT_SAVE_HTML:
            return None
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safe_name = filename.replace(".", f"_{timestamp}.")
        path = self.output_dir / safe_name
        path.write_text(content, encoding="utf-8")
        return path

    def _log(self, logs: List[LogEntry], step: str, message: str, detail: Optional[Any] = None) -> None:
        logs.append(LogEntry(step=step, message=message, detail=detail))

    def _parse_workcards(self, html: str) -> List[WorkcardInfo]:
        pattern = r'<input[^>]*name="jcRid"[^>]*value="(\d+)"'
        matches = re.findall(pattern, html)
        workcards = [WorkcardInfo(rid=rid, index=i + 1) for i, rid in enumerate(matches)]
        return workcards

    def _parse_history_workcards(self, html: str) -> List[HistoryWorkcardInfo]:
        rid_pattern = r'<input type="checkbox" name="rid" value="(\d+)"'
        phase_pattern = r'<input type="hidden" name="phase" value="([^"]*)"'
        zone_pattern = r'<input type="hidden" name="zone" value="([^"]*)"'
        trade_pattern = r'<input type="hidden" name="trade" value="([^"]*)"'

        rids = re.findall(rid_pattern, html)
        phases = re.findall(phase_pattern, html)
        zones = re.findall(zone_pattern, html)
        trades = re.findall(trade_pattern, html)

        history_cards: List[HistoryWorkcardInfo] = []
        for idx, rid in enumerate(rids):
            history_cards.append(
                HistoryWorkcardInfo(
                    rid=rid,
                    index=idx + 1,
                    phase=phases[idx] if idx < len(phases) else "",
                    zone=zones[idx] if idx < len(zones) else "",
                    trade=trades[idx] if idx < len(trades) else "",
                )
            )
        return history_cards

    def _get_current_version(
        self, session: requests.Session, jc_rid: str, logs: List[LogEntry]
    ) -> int:
        try:
            # 记录请求关键信息
            self.logger.info("=" * 80)
            self.logger.info("[步骤B-1] 开始获取工卡版本号")
            self.logger.info(f"请求URL: bathImportNrcStep.jsp")
            self.logger.info(f"请求方法: GET")
            self.logger.info(f"请求参数: jcRidArr={jc_rid}")
            
            # 添加请求间隔，避免请求频率过高
            time.sleep(2)
            
            response = session.get(
                self.urls["dialog"],
                params={"jcRidArr": jc_rid},
                verify=settings.WORKCARD_IMPORT_VERIFY_SSL,
                timeout=30,
            )
            
            response.encoding = "GBK"
            matches = re.findall(r'jcVidArr[^>]*value="(\d+)"', response.text)
            if matches:
                current = max(int(value) for value in matches)
                self.logger.info(f"✓ 响应状态码: {response.status_code}, 获取到版本号: {current}")
                self.logger.info("=" * 80)
                self._log(logs, "get_current_version", f"获取到当前版本号 {current}")
                return current
            else:
                self.logger.warning(f"✓ 响应状态码: {response.status_code}, 未找到版本号，使用默认值 10")
                self.logger.info("=" * 80)
                return 10
        except Exception as exc:
            error_msg = f"获取版本号失败: {exc}"
            self.logger.error("=" * 80)
            self.logger.error("[_get_current_version] 获取版本号失败")
            self.logger.error(f"错误信息: {error_msg}")
            self.logger.error("=" * 80)
            self._log(logs, "get_current_version", error_msg)
            self.logger.exception("获取工卡版本号失败")
        # 默认返回10，保证流程可继续
        return 10

    def _select_workcard(
        self,
        workcards: List[WorkcardInfo],
        preferred_rid: Optional[str],
        preferred_index: int,
        logs: List[LogEntry],
    ) -> WorkcardInfo:
        if preferred_rid:
            for card in workcards:
                if card.rid == preferred_rid:
                    self._log(logs, "select_workcard", f"根据RID选择工卡 rid={card.rid}")
                    return card
        index = preferred_index if 0 <= preferred_index < len(workcards) else 0
        selected = workcards[index]
        self._log(logs, "select_workcard", f"根据索引选择工卡 index={index}, rid={selected.rid}")
        return selected

    def _select_history_workcard(
        self,
        history_cards: List[HistoryWorkcardInfo],
        preferred_rid: Optional[str],
        preferred_index: int,
        logs: List[LogEntry],
    ) -> HistoryWorkcardInfo:
        if preferred_rid:
            for card in history_cards:
                if card.rid == preferred_rid:
                    self._log(
                        logs,
                        "select_history_workcard",
                        f"根据RID选择历史工卡 rid={card.rid}",
                    )
                    return card
        index = preferred_index if 0 <= preferred_index < len(history_cards) else 0
        selected = history_cards[index]
        self._log(
            logs,
            "select_history_workcard",
            f"根据索引选择历史工卡 index={index}, rid={selected.rid}",
        )
        return selected

    def import_defect_to_nrc(
        self,
        params: Dict[str, Any],
        cookies: Optional[str] = None,
        is_test_mode: bool = True,
    ) -> Tuple[bool, str, Optional[str], List[LogEntry], List[Artifact]]:
        """
        导入缺陷到NRC系统（非例行工卡）
        
        Args:
            params: 导入参数字典，包含以下字段：
                - txtACNO: 飞机号
                - txtWO: 工卡指令号
                - txtML: 维修级别
                - txtCust: 客户
                - txtACType: 机型
                - txtCRN: 相关工卡号
                - txtDept: 工艺组
                - selDocType: 工卡类型（如 NR）
                - txtCorrosion: 是否腐蚀（Y/N）
                - txtDescChn: 缺陷中文描述
                - txtDescEng: 缺陷英文描述
            cookies: Cookie字符串
            is_test_mode: 是否为测试模式（测试模式下会在描述前加"测试"/"TEST"前缀）
        
        Returns:
            Tuple[success: bool, message: str, workcard_number: Optional[str], logs: List[LogEntry], artifacts: List[Artifact]]
            成功时返回工卡号（如 NR/000000299），失败时返回错误信息
        """
        logs: List[LogEntry] = []
        artifacts: List[Artifact] = []
        
        session = self._create_session(cookies)
        
        # 构建请求URL
        url = f"{settings.WORKCARD_IMPORT_BASE_URL}/Web/trace/nrc/fault/faultAddSend.jsp,CVPNHost=10.240.2.131:9080,CVPNProtocol=http,CVPNOrg=rel,CVPNExtension=.jsp"
        
        # 准备表单数据
        desc_chn = params.get('txtDescChn', '')
        desc_eng = params.get('txtDescEng', '')
        
        # 测试模式下添加前缀
        if is_test_mode:
            desc_chn = f"测试{desc_chn}" if desc_chn else "测试"
            desc_eng = f"TEST{desc_eng}" if desc_eng else "TEST"
        
        # 构建POST数据（需要GBK编码）
        post_data = {
            'txtCust': params.get('txtCust', ''),
            'txtACNO': params.get('txtACNO', ''),
            'txtWO': params.get('txtWO', ''),
            'txtML': params.get('txtML', ''),
            'txtACType': params.get('txtACType', 'B737-300'),
            'txtWorkContent': params.get('txtWorkContent', ''),
            'txtZoneName': params.get('txtZoneName', ''),
            'txtZoneTen': params.get('txtZoneTen', ''),
            'txtRII': params.get('txtRII', ''),
            'txtCRN': params.get('txtCRN', '客户要求/CUSTOMER REQUIREMENT'),
            'refNo': params.get('refNo', ''),
            'txtEnginSn': params.get('txtEnginSn', ''),
            'txtDescChn': desc_chn,
            'txtDescEng': desc_eng,
            'txtDept': params.get('txtDept', '3_CABIN_TPG'),
            'selDocType': params.get('selDocType', 'NR'),
            'csn': params.get('csn', ''),
            'tsn': params.get('tsn', ''),
            'txtCorrosion': params.get('txtCorrosion', 'N'),
            'txtMenuID': params.get('txtMenuID', '13541'),
            'txtParentID': params.get('txtParentID', '13112'),
            'txtFleet': params.get('txtFleet', ''),
            'txtACPartNo': params.get('txtACPartNo', ''),
            'txtACSerialNo': params.get('txtACSerialNo', ''),
            'txtTsn': params.get('txtTsn', ''),
            'txtCsn': params.get('txtCsn', ''),
            'jcMode': params.get('jcMode', 'C'),
            'flagEu': params.get('flagEu', ''),
            'txtFlag': params.get('txtFlag', ''),
        }
        
        # 构建请求头
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Host': 'vpn.gameco.com.cn',
            'Origin': settings.WORKCARD_IMPORT_BASE_URL,
            'Referer': f"{settings.WORKCARD_IMPORT_BASE_URL}/Web/trace/nrc/fault/faultAdd.jsp,CVPNHost=10.240.2.131:9080,CVPNProtocol=http,CVPNOrg=rel,CVPNExtension=.jsp?txtParentID={post_data['txtParentID']}&txtMenuID={post_data['txtMenuID']}",
            'Sec-Fetch-Dest': 'frame',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }
        
        try:
            # 将数据编码为GBK格式的URL编码字符串
            # 注意：requests会自动处理URL编码，但我们需要确保使用GBK编码
            self.logger.info(f"开始准备导入请求，参数数量: {len(post_data)}")
            self.logger.debug(f"POST数据: {post_data}")
            
            encoded_data = urlencode(post_data, encoding='gbk')
            self.logger.debug(f"URL编码后的数据长度: {len(encoded_data)} 字符")
            
            self._log(logs, "import_defect", f"开始导入缺陷到NRC系统，飞机号: {post_data['txtACNO']}, 工卡指令号: {post_data['txtWO']}")
            
            self.logger.info(f"发送POST请求到: {url}")
            self.logger.debug(f"请求头数量: {len(headers)}")
            
            # 添加请求间隔，避免请求频率过高导致连接断开
            time.sleep(2)
            response = session.post(
                url,
                data=encoded_data,
                headers=headers,
                verify=settings.WORKCARD_IMPORT_VERIFY_SSL,
                timeout=30,
            )
            
            self.logger.info(f"收到响应，状态码: {response.status_code}, 响应大小: {len(response.content)} 字节")
            
            response.encoding = 'GBK'
            html = response.text
            self.logger.debug(f"响应内容长度: {len(html)} 字符")
            
            # 保存响应HTML用于调试
            artifact = self._save_artifact("import_defect_response.html", html)
            if artifact:
                artifacts.append(Artifact(step="import_defect", filename=artifact.name, path=str(artifact)))
            
            self._log(logs, "import_defect", f"收到响应，状态码: {response.status_code}")
            # 记录响应内容预览（限制大小避免JSON序列化问题）
            # 只记录前2000个字符，避免detail字段过大导致序列化失败
            html_preview = html[:2000] if len(html) > 2000 else html
            self._log(logs, "import_defect", f"响应内容预览（前2000字符，总长度: {len(html)}）: {html_preview}")
            # 记录响应内容的关键部分（用于提取工卡号）
            if len(html) > 2000:
                self._log(logs, "import_defect", f"响应内容过长，已截断。完整内容已保存到文件。")
            
            # 解析响应，提取工卡号
            # 响应格式示例：window.alert('该非例行工卡号为: NR/000000299 !')
            workcard_number = None
            
            # 尝试多种匹配模式
            patterns = [
                # 模式1: window.alert('该非例行工卡号为: NR/000000299 !') - 最精确
                r"该非例行工卡号为[：:]\s*(NR/[\d]+)",
                # 模式2: alert('该非例行工卡号为: NR/000000299 !')
                r"alert\([^)]*?该非例行工卡号为[：:]\s*(NR/[\d]+)",
                # 模式3: 匹配 alert 中单引号内的工卡号
                r"alert\([^)]*?['\"](NR/[\d]+)['\"]",
                # 模式4: 直接匹配 NR/数字（在alert附近）
                r"alert\([^)]*?(NR/[\d]+)",
                # 模式5: 匹配所有NR/数字模式
                r"(NR/[\d]+)",
            ]
            
            for i, pattern in enumerate(patterns, 1):
                try:
                    match = re.search(pattern, html, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                    if match:
                        # 优先使用捕获组，如果没有捕获组则使用整个匹配
                        if match.lastindex and match.lastindex >= 1:
                            workcard_number = match.group(1).strip()
                        else:
                            workcard_number = match.group(0).strip()
                        
                        # 验证工卡号格式（NR/后跟数字）
                        if workcard_number and re.match(r'^NR/[\d]+$', workcard_number):
                            self._log(logs, "import_defect", f"通过模式{i}成功提取工卡号: {workcard_number}")
                            break
                        else:
                            # 如果提取的不是标准格式，尝试从匹配结果中再次提取
                            nr_match = re.search(r'NR/[\d]+', workcard_number)
                            if nr_match:
                                workcard_number = nr_match.group(0)
                                self._log(logs, "import_defect", f"通过模式{i}（二次提取）成功提取工卡号: {workcard_number}")
                                break
                            workcard_number = None
                except Exception as e:
                    self._log(logs, "import_defect", f"模式{i}匹配失败: {e}")
                    continue
            
            # 如果还没找到，尝试更宽松的匹配 - 查找所有NR/数字模式
            if not workcard_number:
                all_matches = re.findall(r'NR/[\d]+', html)
                if all_matches:
                    # 取第一个匹配的
                    workcard_number = all_matches[0]
                    self._log(logs, "import_defect", f"通过宽松模式提取工卡号: {workcard_number}")
                else:
                    self._log(logs, "import_defect", "未能从响应中提取工卡号，响应中可能不包含NR/格式的工卡号")
            
            if response.status_code == 200:
                if workcard_number:
                    message = f"导入成功，工卡号: {workcard_number}"
                    self._log(logs, "import_defect", message)
                    return True, message, workcard_number, logs, artifacts
                elif "成功" in html or "保存" in html:
                    message = "导入成功，但未能提取工卡号"
                    self._log(logs, "import_defect", message)
                    return True, message, None, logs, artifacts
                else:
                    # 检查是否有错误信息
                    error_pattern = r"错误|失败|异常"
                    if re.search(error_pattern, html):
                        error_msg = "导入失败，服务器返回错误信息"
                        self._log(logs, "import_defect", error_msg)
                        return False, error_msg, None, logs, artifacts
                    else:
                        message = "导入完成，但响应格式异常"
                        self._log(logs, "import_defect", message)
                        return False, message, None, logs, artifacts
            else:
                error_msg = f"导入失败，HTTP状态码: {response.status_code}"
                self._log(logs, "import_defect", error_msg)
                return False, error_msg, None, logs, artifacts
                
        except Exception as exc:
            import traceback
            error_msg = f"导入缺陷失败: {exc}"
            error_traceback = traceback.format_exc()
            self._log(logs, "import_defect", error_msg)
            # 记录错误堆栈（限制大小）
            error_detail = error_traceback[:1000] if len(error_traceback) > 1000 else error_traceback
            self._log(logs, "import_defect", f"错误堆栈（前1000字符）: {error_detail}", detail=error_detail)
            self.logger.exception(error_msg)
            self.logger.error(f"导入缺陷完整错误堆栈:\n{error_traceback}")
            self.logger.error(f"请求参数: {params}")
            return False, error_msg, None, logs, artifacts

    # ------------------------------------------------------------------ #
    # 工卡步骤导入功能
    # ------------------------------------------------------------------ #
    def get_jcrid_by_jobcard(
        self,
        session: requests.Session,
        *,
        jobcard_number: str,
        tail_no: str,
        work_order: str,
        work_group: str,
        logs: List[LogEntry],
        artifacts: List[Artifact],
    ) -> Optional[str]:
        """
        通过工卡号获取工卡ID (jcRid)
        
        Args:
            session: 请求会话
            jobcard_number: 工卡号（如 NR/000000300）
            tail_no: 飞机号
            work_order: 工单号
            work_group: 工作组
            logs: 日志列表
            artifacts: 文件列表
            
        Returns:
            工卡ID (jcRid)，如果未找到则返回 None
        """
        # 构建查询参数，使用工卡号进行查询
        # 参考 _step_query_workorder 方法，需要包含更多参数才能正确查询
        post_data = {
            "wgp": work_group,
            "printer": settings.WORKCARD_IMPORT_PRINTER,
            "txtMenuID": "22800",
            "txtFullReg": tail_no,
            "qWorkorder": work_order,
            "txtJobcard": jobcard_number,  # 关键：使用工卡号查询
            "txtPage": "1",
            "from": "manage",
            # 添加其他可能需要的空字段，保持与标准查询一致
            "txtFlight_Check_No": "",
            "txtVisit_Desc": "",
            "txtIPC_Num": "",
            "txtMpd": "",
            "txtType": "",
            "txtSeq": "",
            "txtJcDesc": "",
            "txtQcFinal": "",
            "txtJcStatus": "",
            "txtSlnStatus": "",
            "txtImport": "",
            "txtBoothAss": "",
            "txtSlnPrinted": "",
            "preWorkGrp": "",
            "curWorkGrp": "",
            "schemeGrp": "",
            "txtUpdatedBy": "",
            "txtDangerousCargo": "",
            "txtSchedPhase": "",
            "txtSchedZone": "",
            "txtLaborCode": "",
            "txtTransferMode": "",
            "txtme_unUpload": "",
            "txtRii": "",
            "txtMatStatus": "",
            "txtFilterTrace": "",
            "txtJcRob": "",
            "txtPrDateStart": "",
            "txtPrDateEnd": "",
            "txtRTrade": "",
            "txtHoldBy": "",
            "txtJcTransferDateStart": "",
            "txtJcTransferDateEnd": "",
            "txtJcWorkorder": "",
            "txtSlnReqDateStart": "",
            "txtSlnReqDateEnd": "",
            "txtFlagMpd": "",
            "txtFlagActive": "",
            "txtExternal": "",
            "txtExteriorDamag": "",
            "txtMajorMdo": "",
            "txtOutOfManual": "",
            "txtStrRepair": "",
            "txtPse": "",
            "txtFcs": "",
            "txtCauseStrr": "",
            "txtRplStrPart": "",
            "txtQcStamp": "",
            "txtNmfTrade": "",
            "txtForbidEsign": "",
            "txtFedexAmtStamp": "",
            "txtFeeRemark": "",
            "txtFlagFee": "",
            "txtInspector": "",
            "txtSubShop": "",
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": settings.WORKCARD_IMPORT_BASE_URL,
            "Referer": f"{settings.WORKCARD_IMPORT_BASE_URL}/Web/trace/fgm/workOrder/checkData.jsp,CVPNHost=10.240.2.131:9080,CVPNProtocol=http,CVPNOrg=rel,CVPNExtension=.jsp?from=manage",
        }
        
        # 记录请求关键信息
        self.logger.info("=" * 80)
        self.logger.info(f"[步骤A] 开始查询工卡ID")
        self.logger.info(f"请求URL: checkData.jsp")
        self.logger.info(f"请求方法: POST")
        self.logger.info(f"工卡号: {jobcard_number}, 工单号: {work_order}, 飞机号: {tail_no}, 工作组: {work_group}")
        
        try:
            # 添加请求间隔，避免请求频率过高导致连接断开
            time.sleep(2)
            response = session.post(
                self.urls["query"],
                data=post_data,
                headers=headers,
                verify=settings.WORKCARD_IMPORT_VERIFY_SSL,
                timeout=30,
            )
            
            # 记录响应关键信息
            self.logger.info(f"✓ 响应状态码: {response.status_code}")
            
            response.encoding = "GBK"
            html = response.text
            
            # 只检查关键错误信息
            if "该指令号没有相关数据" in html:
                self.logger.warning("✗ 服务器返回：该指令号没有相关数据")
            
            self._log(
                logs,
                self._STEP_GET_JCRID,
                f"查询工卡ID成功，状态码 {response.status_code}，工卡号: {jobcard_number}",
            )
            
            artifact = self._save_artifact("get_jcrid_by_jobcard.html", html)
            if artifact:
                artifacts.append(Artifact(step=self._STEP_GET_JCRID, filename=artifact.name, path=str(artifact)))
            
            # 解析HTML，查找工卡ID
            # 方法1: 查找 name="jcRid" 的 input 标签
            jcrid_pattern = r'<input[^>]*name="jcRid"[^>]*value="(\d+)"'
            matches = re.findall(jcrid_pattern, html)
            
            if matches:
                # 如果找到多个，尝试通过工卡号匹配
                jobcard_encoded = jobcard_number.replace("/", "%2F")
                for jcrid in matches:
                    pattern = rf'{jcrid}_jobcard[^>]*value="{re.escape(jobcard_encoded)}"'
                    if re.search(pattern, html):
                        self.logger.info(f"✓ 找到匹配的工卡ID: {jcrid} (工卡号: {jobcard_number})")
                        self.logger.info("=" * 80)
                        self._log(logs, self._STEP_GET_JCRID, f"找到匹配的工卡ID: {jcrid}")
                        return jcrid
                
                # 如果没有精确匹配，返回第一个
                self.logger.info(f"✓ 找到工卡ID: {matches[0]} (未精确匹配)")
                self.logger.info("=" * 80)
                self._log(logs, self._STEP_GET_JCRID, f"找到工卡ID: {matches[0]}")
                return matches[0]
            
            # 方法2: 查找 jcRidArr 参数
            jcridarr_pattern = r'jcRidArr[^>]*value="(\d+)"'
            matches2 = re.findall(jcridarr_pattern, html)
            
            if matches2:
                self.logger.info(f"✓ 找到工卡ID: {matches2[0]}")
                self.logger.info("=" * 80)
                self._log(logs, self._STEP_GET_JCRID, f"找到工卡ID: {matches2[0]}")
                return matches2[0]
            
            # 未找到
            self.logger.warning(f"✗ 未找到工卡ID，工卡号: {jobcard_number}")
            self.logger.info("=" * 80)
            
            self._log(logs, self._STEP_GET_JCRID, f"未找到工卡ID，工卡号: {jobcard_number}，响应已保存到文件")
            return None
            
        except requests.exceptions.RequestException as exc:
            error_msg = f"请求异常: {exc}"
            self.logger.error("=" * 80)
            self.logger.error(f"[{self._STEP_GET_JCRID}] 请求失败")
            self.logger.error(f"错误类型: {type(exc).__name__}")
            self.logger.error(f"错误信息: {error_msg}")
            if hasattr(exc, 'response') and exc.response is not None:
                self.logger.error(f"响应状态码: {exc.response.status_code}")
                self.logger.error(f"响应内容: {exc.response.text[:500]}")
            self.logger.error("=" * 80)
            self._log(logs, self._STEP_GET_JCRID, error_msg)
            return None
            
        except Exception as exc:
            import traceback
            error_msg = f"查询工卡ID失败: {exc}"
            error_traceback = traceback.format_exc()
            self.logger.error("=" * 80)
            self.logger.error(f"[{self._STEP_GET_JCRID}] 发生未预期的异常")
            self.logger.error(f"错误类型: {type(exc).__name__}")
            self.logger.error(f"错误信息: {error_msg}")
            self.logger.error(f"完整堆栈:\n{error_traceback}")
            self.logger.error("=" * 80)
            self._log(logs, self._STEP_GET_JCRID, error_msg)
            self.logger.exception(error_msg)
            return None

    def query_steps(
        self,
        session: requests.Session,
        *,
        jc_rid: str,
        jobcard_number: str,
        target_work_order: str,
        work_group: str,
        tail_no: str,
        logs: List[LogEntry],
        artifacts: List[Artifact],
    ) -> Tuple[Optional[str], Optional[str], List[StepInfo]]:
        """
        查询工卡的步骤信息
        
        Args:
            session: 请求会话
            jc_rid: 工卡ID
            jobcard_number: 工卡号（源工卡号）
            target_work_order: 目标工单号
            work_group: 工作组
            tail_no: 飞机号
            logs: 日志列表
            artifacts: 文件列表
            
        Returns:
            (jcVidArr, html, steps) 元组
            jcVidArr: 工卡版本ID
            html: 响应HTML
            steps: 步骤列表
        """
        # 先获取当前版本号
        current_version = self._get_current_version(session, jc_rid, logs)
        
        # 在获取版本号后，再等待2秒，避免连续请求导致连接断开
        self.logger.info("获取版本号后等待2秒，避免连续请求...")
        time.sleep(2)
        
        # 构建查询请求
        # 参考成功代码模板，确保包含所有必需字段
        post_data = {
            "isFrist": "no",
            "jcRidArr": jc_rid,
            "jcVidArr": str(current_version),
            "flnum": tail_no,
            "stepCtrl": "Y",
            "qJcWorkOrder": target_work_order,
            "qJobcard": "",  # 参考成功代码，这里应该是空字符串，不是工卡号
            "workGroup": work_group,
            "qRii": "",
            "qJcDesc": "",
            "qTrade": "",
            "qRemark": "",
            "txtArea": "空调舱",  # 关键：成功代码中有这个参数！
            "txtPage": "1",
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": settings.WORKCARD_IMPORT_BASE_URL,
            "Referer": f"{self.urls['dialog']}?jcRidArr={jc_rid}",
        }
        
        # 记录请求关键信息
        self.logger.info("=" * 80)
        self.logger.info("[步骤B-2] 开始查询步骤信息")
        self.logger.info(f"请求URL: bathImportNrcStep.jsp")
        self.logger.info(f"请求方法: POST")
        self.logger.info(f"关键参数: jcRidArr={jc_rid}, jcVidArr={current_version}, qJcWorkOrder={target_work_order}, qJobcard={jobcard_number}")
        
        try:
            # 添加请求间隔，避免请求频率过高导致连接断开
            time.sleep(2)
            
            response = session.post(
                self.urls["dialog"],
                data=post_data,
                headers=headers,
                verify=settings.WORKCARD_IMPORT_VERIFY_SSL,
                timeout=30,
            )
            
            self.logger.info(f"✓ 响应状态码: {response.status_code}")
            response.encoding = "GBK"
            html = response.text
            
            self._log(
                logs,
                self._STEP_QUERY_STEPS,
                f"查询步骤成功，状态码 {response.status_code}，版本号 {current_version}",
            )
            
            artifact = self._save_artifact("query_steps.html", html)
            if artifact:
                artifacts.append(Artifact(step=self._STEP_QUERY_STEPS, filename=artifact.name, path=str(artifact)))
            
            # 解析版本ID
            jcvid_pattern = r'<input[^>]*type="hidden"[^>]*name="jcVidArr"[^>]*value="(\d+)"'
            jcvid_matches = re.findall(jcvid_pattern, html)
            jcvid_arr = jcvid_matches[0] if jcvid_matches else str(current_version)
            
            # 解析步骤信息
            steps = self._parse_steps(html)
            self._log(logs, self._STEP_QUERY_STEPS, f"解析到 {len(steps)} 个步骤，版本ID: {jcvid_arr}")
            
            return jcvid_arr, html, steps
            
        except Exception as exc:
            message = f"查询步骤失败: {exc}"
            self._log(logs, self._STEP_QUERY_STEPS, message)
            self.logger.exception(message)
            return None, None, []

    def _build_batch_post_data(
        self,
        base_params: Dict[str, str],
        steps: List[StepInfo],
    ) -> str:
        """
        构建批量导入的POST数据（支持重复参数名）
        
        格式：基础参数 -> txtArea -> 每个步骤的 phase, zone, trade, rid -> txtPage
        
        Args:
            base_params: 基础参数（不重复的参数）
            steps: 步骤列表
            
        Returns:
            URL编码后的POST数据字符串
        """
        parts = []
        
        # 添加基础参数（不重复的参数）
        base_keys = ['isFrist', 'jcRidArr', 'jcVidArr', 'flnum', 'stepCtrl', 
                     'qJcWorkOrder', 'qJobcard', 'workGroup', 'qRii', 'qJcDesc', 
                     'qTrade', 'qRemark']
        for key in base_keys:
            if key in base_params:
                parts.append(f"{key}={quote(str(base_params[key]), safe='', encoding='gbk')}")
        
        # 添加 txtArea（全局参数，只出现一次）
        txt_area = base_params.get('txtArea', '空调舱')
        parts.append(f"txtArea={quote(txt_area, safe='', encoding='gbk')}")
        
        # 为每个步骤添加 phase, zone, trade, rid（重复参数）
        for step in steps:
            if step.phase:
                parts.append(f"phase={quote(step.phase, safe='', encoding='gbk')}")
            if step.zone:
                parts.append(f"zone={quote(step.zone, safe='', encoding='gbk')}")
            if step.trade:
                parts.append(f"trade={quote(step.trade, safe='', encoding='gbk')}")
            parts.append(f"rid={quote(step.rid, safe='', encoding='gbk')}")
        
        # 添加 txtPage
        if 'txtPage' in base_params:
            parts.append(f"txtPage={base_params['txtPage']}")
        
        return '&'.join(parts)

    def import_step(
        self,
        session: requests.Session,
        *,
        jc_rid: str,
        jc_vid: str,
        steps: List[StepInfo],  # 改为接受多个步骤
        target_work_order: str,
        work_group: str,
        tail_no: str,
        logs: List[LogEntry],
        artifacts: List[Artifact],
    ) -> Tuple[bool, str, List[Dict], List[Dict]]:
        """
        批量导入步骤（一次请求提交所有步骤）
        
        Args:
            session: 请求会话
            jc_rid: 工卡ID
            jc_vid: 工卡版本ID
            steps: 步骤信息列表（支持单个或多个步骤）
            target_work_order: 目标工单号
            work_group: 工作组
            tail_no: 飞机号
            logs: 日志列表
            artifacts: 文件列表
            
        Returns:
            (success, message, imported_steps, failed_steps) 元组
            success: 是否全部成功
            message: 服务器返回的消息
            imported_steps: 成功导入的步骤列表
            failed_steps: 失败的步骤列表
        """
        if not steps:
            return False, "没有要导入的步骤", [], []
        
        # 使用第一个步骤的 txt_area，如果没有则使用默认值
        txt_area = steps[0].txt_area if steps[0].txt_area else "空调舱"
        
        # 构建基础参数
        base_params = {
            "isFrist": "no",
            "jcRidArr": jc_rid,
            "jcVidArr": jc_vid,
            "flnum": tail_no,
            "stepCtrl": "Y",
            "qJcWorkOrder": target_work_order,
            "qJobcard": "",
            "workGroup": work_group,
            "qRii": "",
            "qJcDesc": "",
            "qTrade": "",
            "qRemark": "",
            "txtArea": txt_area,
            "txtPage": "1",
        }
        
        # 构建批量POST数据（支持重复参数）
        encoded_data = self._build_batch_post_data(base_params, steps)
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": settings.WORKCARD_IMPORT_BASE_URL,
            "Referer": self.urls["dialog"],
        }
        
        # 记录请求关键信息
        self.logger.info("=" * 80)
        self.logger.info(f"[步骤C] 准备批量导入步骤")
        self.logger.info(f"请求URL: doBathImportNrcStep.jsp")
        self.logger.info(f"请求方法: POST")
        self.logger.info(f"步骤数量: {len(steps)}")
        self.logger.info(f"关键参数: jcRidArr={jc_rid}, jcVidArr={jc_vid}, qJcWorkOrder={target_work_order}")
        self.logger.info(f"步骤列表:")
        for step in steps:
            self.logger.info(f"  步骤{step.index}: rid={step.rid}, phase={step.phase}, zone={step.zone}, trade={step.trade}")
        self.logger.info("=" * 80)
        
        try:
            # 添加请求间隔，避免请求频率过高导致连接断开
            time.sleep(2)
            
            response = session.post(
                self.urls["import"],
                data=encoded_data,
                headers=headers,
                verify=settings.WORKCARD_IMPORT_VERIFY_SSL,
                timeout=30,
            )
            
            self.logger.info(f"✓ 响应状态码: {response.status_code}")
            response.encoding = "GBK"
            html = response.text
            
            artifact = self._save_artifact("import_steps_batch_result.html", html)
            if artifact:
                artifacts.append(Artifact(step=self._STEP_IMPORT_STEP, filename=artifact.name, path=str(artifact)))
            
            # 解析响应消息
            message_match = re.search(r'id="messageId" value="([^"]*)"', html)
            message = message_match.group(1) if message_match else "未获取到服务器返回信息"
            
            # 判断是否成功
            imported_steps = []
            failed_steps = []
            
            if any(keyword in message for keyword in ["失败", "错误"]):
                # 如果失败，所有步骤都标记为失败
                for step in steps:
                    failed_steps.append({"rid": step.rid, "index": step.index, "message": message})
                self.logger.info(f"✗ 批量导入失败: {message}")
                self.logger.info("=" * 80)
                self._log(
                    logs,
                    self._STEP_IMPORT_STEP,
                    f"批量导入步骤失败，状态码 {response.status_code}，步骤数量: {len(steps)}，服务器消息：{message}",
                )
                return False, message, imported_steps, failed_steps
            elif "成功" in message or "保存" in message or "导入成功" in message:
                # 如果成功，所有步骤都标记为成功
                for step in steps:
                    imported_steps.append({"rid": step.rid, "index": step.index, "message": message})
                self.logger.info(f"✓ 批量导入成功: {message}")
                self.logger.info(f"  成功导入 {len(imported_steps)} 个步骤")
                self.logger.info("=" * 80)
                self._log(
                    logs,
                    self._STEP_IMPORT_STEP,
                    f"批量导入步骤成功，状态码 {response.status_code}，步骤数量: {len(steps)}，服务器消息：{message}",
                )
                return True, message, imported_steps, failed_steps
            else:
                # 未知状态，标记为失败
                for step in steps:
                    failed_steps.append({"rid": step.rid, "index": step.index, "message": f"未知状态: {message}"})
                self.logger.info(f"⚠ 批量导入结果未知: {message}")
                self.logger.info("=" * 80)
                self._log(
                    logs,
                    self._STEP_IMPORT_STEP,
                    f"批量导入步骤完成，状态码 {response.status_code}，步骤数量: {len(steps)}，服务器消息：{message}",
                )
                return False, message, imported_steps, failed_steps
            
        except Exception as exc:
            message = f"批量导入步骤失败: {exc}"
            failed_steps = [{"rid": step.rid, "index": step.index, "message": message} for step in steps]
            self._log(logs, self._STEP_IMPORT_STEP, message)
            self.logger.exception(message)
            return False, message, [], failed_steps

    def import_steps_workflow(
        self,
        jobcard_number: str,
        target_work_order: str,
        source_work_order: str,
        tail_no: str,
        work_group: str,
        step_rids: Optional[List[str]] = None,
        cookies: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        完整的步骤导入工作流
        
        Args:
            jobcard_number: 工卡号（如 NR/000000300）
            target_work_order: 目标工单号（候选工卡的工卡指令号，用于 qJcWorkOrder）
            source_work_order: 源工单号（导入参数配置的工作指令号 txtWO，用于 qWorkorder）
            tail_no: 飞机号
            work_group: 工作组
            step_rids: 要导入的步骤ID列表（如果为None，则导入所有步骤）
            cookies: Cookie字符串
            
        Returns:
            包含导入结果的字典
        """
        session = self._create_session(cookies)
        logs: List[LogEntry] = []
        artifacts: List[Artifact] = []
        
        try:
            # 步骤A: 通过工卡号获取工卡ID
            self.logger.info("=" * 80)
            self.logger.info("[import_steps_workflow] 开始执行步骤导入工作流")
            self.logger.info(f"工卡号: {jobcard_number}")
            self.logger.info(f"目标工单号（qJcWorkOrder）: {target_work_order}")
            self.logger.info(f"源工单号（qWorkorder）: {source_work_order}")
            self.logger.info(f"飞机号: {tail_no}")
            self.logger.info(f"工作组: {work_group}")
            self.logger.info(f"要导入的步骤ID: {step_rids}")
            self.logger.info("=" * 80)
            
            self._log(logs, self._STEP_GET_JCRID, f"开始查询工卡ID，工卡号: {jobcard_number}")
            jc_rid = self.get_jcrid_by_jobcard(
                session,
                jobcard_number=jobcard_number,
                tail_no=tail_no,
                work_order=source_work_order,  # qWorkorder: 使用导入参数配置的工作指令号
                work_group=work_group,
                logs=logs,
                artifacts=artifacts,
            )
            
            self.logger.info("=" * 80)
            self.logger.info(f"[import_steps_workflow] 步骤A完成，获取到的工卡ID: {jc_rid}")
            self.logger.info("=" * 80)
            
            if not jc_rid:
                error_msg = f"未找到工卡ID，工卡号: {jobcard_number}，源工单号（qWorkorder）: {source_work_order}"
                self.logger.error("=" * 80)
                self.logger.error("[import_steps_workflow] 步骤A失败：未找到工卡ID")
                self.logger.error(f"工卡号: {jobcard_number}")
                self.logger.error(f"源工单号（qWorkorder）: {source_work_order}")
                self.logger.error(f"飞机号: {tail_no}")
                self.logger.error(f"工作组: {work_group}")
                self.logger.error("可能的原因：")
                self.logger.error("1. 工卡号不存在或格式不正确")
                self.logger.error("2. 源工单号（工作指令号 txtWO）不正确")
                self.logger.error("3. 飞机号或工作组不匹配")
                self.logger.error("4. Cookie无效或已过期")
                self.logger.error("5. 网络连接问题")
                self.logger.error("请检查保存的HTML文件以获取更多信息")
                self.logger.error("=" * 80)
                return {
                    "success": False,
                    "message": error_msg,
                    "logs": [asdict(log) for log in logs],
                    "artifacts": [asdict(artifact) for artifact in artifacts],
                }
            
            # 步骤B: 查询步骤信息
            # 在查询步骤前等待2秒，避免与步骤A的请求间隔太短
            self.logger.info("=" * 80)
            self.logger.info("步骤A完成，等待2秒后开始步骤B（查询步骤信息）...")
            self.logger.info(f"工卡ID: {jc_rid}")
            self.logger.info("=" * 80)
            time.sleep(2)
            self._log(logs, self._STEP_QUERY_STEPS, f"开始查询步骤，工卡ID: {jc_rid}")
            jc_vid, html, steps = self.query_steps(
                session,
                jc_rid=jc_rid,
                jobcard_number=jobcard_number,
                target_work_order=target_work_order,
                work_group=work_group,
                tail_no=tail_no,
                logs=logs,
                artifacts=artifacts,
            )
            
            self.logger.info("=" * 80)
            self.logger.info(f"[import_steps_workflow] 步骤B完成")
            self.logger.info(f"获取到的版本ID: {jc_vid}")
            self.logger.info(f"获取到的步骤数量: {len(steps) if steps else 0}")
            if steps:
                for i, step in enumerate(steps[:5], 1):  # 只显示前5个步骤
                    self.logger.info(f"  步骤{i}: rid={step.rid}, index={step.index}, phase={step.phase}, zone={step.zone}, trade={step.trade}")
            self.logger.info("=" * 80)
            
            if not jc_vid or not steps:
                return {
                    "success": False,
                    "message": f"未找到步骤信息，工卡ID: {jc_rid}",
                    "logs": [asdict(log) for log in logs],
                    "artifacts": [asdict(artifact) for artifact in artifacts],
                    "steps": [],
                }
            
            # 步骤C: 执行导入
            imported_steps = []
            failed_steps = []
            
            # 确定要导入的步骤
            steps_to_import = steps
            if step_rids:
                steps_to_import = [s for s in steps if s.rid in step_rids]
            
            # 在开始导入步骤前等待2秒，避免与步骤B的请求间隔太短
            self.logger.info("=" * 80)
            self.logger.info(f"步骤B完成，等待2秒后开始步骤C（批量导入 {len(steps_to_import)} 个步骤）...")
            self.logger.info(f"要导入的步骤列表:")
            for step in steps_to_import:
                self.logger.info(f"  步骤{step.index}: rid={step.rid}, phase={step.phase}, zone={step.zone}, trade={step.trade}")
            self.logger.info("=" * 80)
            time.sleep(2)
            self._log(logs, self._STEP_IMPORT_STEP, f"开始批量导入 {len(steps_to_import)} 个步骤")
            
            # 批量导入所有步骤（一次请求）
            success, message, batch_imported, batch_failed = self.import_step(
                session,
                jc_rid=jc_rid,
                jc_vid=jc_vid,
                steps=steps_to_import,  # 传入所有步骤
                target_work_order=target_work_order,
                work_group=work_group,
                tail_no=tail_no,
                logs=logs,
                artifacts=artifacts,
            )
            
            # 合并结果
            imported_steps.extend(batch_imported)
            failed_steps.extend(batch_failed)
            
            # 构建返回结果
            total_success = len(failed_steps) == 0
            message = f"成功导入 {len(imported_steps)}/{len(steps_to_import)} 个步骤"
            if failed_steps:
                message += f"，失败 {len(failed_steps)} 个步骤"
            
            return {
                "success": total_success,
                "message": message,
                "jc_rid": jc_rid,
                "jc_vid": jc_vid,
                "total_steps": len(steps),
                "imported_count": len(imported_steps),
                "failed_count": len(failed_steps),
                "imported_steps": imported_steps,
                "failed_steps": failed_steps,
                "all_steps": [asdict(step) for step in steps],
                "logs": [asdict(log) for log in logs],
                "artifacts": [asdict(artifact) for artifact in artifacts],
            }
            
        except Exception as exc:
            error_msg = f"步骤导入工作流失败: {exc}"
            self._log(logs, "workflow", error_msg)
            self.logger.exception(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "logs": [asdict(log) for log in logs],
                "artifacts": [asdict(artifact) for artifact in artifacts],
            }

    def _parse_steps(self, html: str) -> List[StepInfo]:
        """解析HTML中的步骤信息"""
        steps: List[StepInfo] = []
        
        # 查找所有步骤的复选框
        rid_pattern = r'<input type="checkbox" name="rid" value="(\d+)"'
        rids = re.findall(rid_pattern, html)
        
        # 查找步骤属性（phase, zone, trade, txtArea）
        # 这些属性可能在隐藏字段中，也可能在表格中
        phase_pattern = r'<input[^>]*type="hidden"[^>]*name="phase"[^>]*value="([^"]*)"'
        zone_pattern = r'<input[^>]*type="hidden"[^>]*name="zone"[^>]*value="([^"]*)"'
        trade_pattern = r'<input[^>]*type="hidden"[^>]*name="trade"[^>]*value="([^"]*)"'
        txt_area_pattern = r'<input[^>]*type="hidden"[^>]*name="txtArea"[^>]*value="([^"]*)"'
        
        phases = re.findall(phase_pattern, html)
        zones = re.findall(zone_pattern, html)
        trades = re.findall(trade_pattern, html)
        txt_areas = re.findall(txt_area_pattern, html)
        
        # 如果隐藏字段数量与步骤数量不匹配，尝试从表格中解析
        # 这里先使用简单的索引匹配
        for idx, rid in enumerate(rids):
            step = StepInfo(
                rid=rid,
                index=idx + 1,
                phase=phases[idx] if idx < len(phases) else "",
                zone=zones[idx] if idx < len(zones) else "",
                trade=trades[idx] if idx < len(trades) else "",
                txt_area=txt_areas[idx] if idx < len(txt_areas) else "",
            )
            steps.append(step)
        
        return steps

