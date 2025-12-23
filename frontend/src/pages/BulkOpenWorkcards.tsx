import React, { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import {
  Card,
  Button,
  Space,
  Table,
  message,
  Typography,
  Tag,
  Form,
  Input,
  Alert,
  Select,
  Radio,
  Divider,
  List,
  Spin,
  Result,
  Row,
  Col,
  Modal,
  Popconfirm
} from 'antd'
import {
  LeftOutlined,
  HomeOutlined,
  ReloadOutlined,
  EditOutlined,
  FileTextOutlined,
  UploadOutlined,
  DeleteOutlined
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { UploadProps } from 'antd'
import { Upload } from 'antd'
import * as XLSX from 'xlsx'
import { defectApi, CandidateWorkCard } from '../services/defectApi'
import { workcardImportApi, PreviewResponse, RunResponse } from '../services/workcardImportApi'
import { matchingApi } from '../services/matchingApi'
import { WorkCardGroup } from '../services/workcardApi'
import { importBatchApi, ImportBatchSummary } from '../services/importBatchApi'

const { Title, Paragraph } = Typography
const { Option } = Select

interface MatchResult {
  item_id?: number // 导入Excel时使用，替代defect_record_id
  defect_record_id: number
  defect_number: string
  description_cn?: string
  description_en?: string
  relative_jobcard_number?: string // 相关工卡号 (txtCRN)
  relative_jobcard_sequence?: string // 相关工卡序号 (refNo)
  zone?: string // 区域 (txtZoneName)
  zone_ten?: string // 区域号 (txtZoneTen)
  candidates: CandidateWorkCard[]
  selected_workcard_id?: number
  issued_workcard_number?: string  // 已开出的工卡号
}

interface LocationState {
  defectListId?: number
  defectListInfo?: { id: number; title: string; aircraft_number: string }
  workcardGroup?: WorkCardGroup
  matchResults?: MatchResult[]
  importBatchId?: number
}

const BulkOpenWorkcards: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const locationState = (location.state as LocationState) || {}
  const searchParams = new URLSearchParams(location.search)
  const defectListIdFromQuery = searchParams.get('defectListId')
  const configurationIdFromQuery = searchParams.get('configurationId')
  const aircraftNumberFromQuery = searchParams.get('aircraftNumber')
  const aircraftTypeFromQuery = searchParams.get('aircraftType')
  const msnFromQuery = searchParams.get('msn')
  const ammIpcEffFromQuery = searchParams.get('ammIpcEff')

  const initialDefectListId =
    locationState.defectListId ?? (defectListIdFromQuery ? Number(defectListIdFromQuery) : undefined)

  const initialWorkcardGroup: WorkCardGroup | undefined =
    locationState.workcardGroup ??
    (configurationIdFromQuery
      ? {
        configuration_id: Number(configurationIdFromQuery),
        aircraft_number: aircraftNumberFromQuery || undefined,
        aircraft_type: aircraftTypeFromQuery || undefined,
        msn: msnFromQuery || undefined,
        amm_ipc_eff: ammIpcEffFromQuery || undefined,
        count: locationState.workcardGroup?.count ?? 0,
        min_id: locationState.workcardGroup?.min_id ?? 0
      }
      : undefined)

  const [importForm] = Form.useForm()
  const [importParamsForm] = Form.useForm()
  const [defectListInfo, setDefectListInfo] = useState<LocationState['defectListInfo']>(
    locationState.defectListInfo
  )
  const [defectListId, setDefectListId] = useState<number | undefined>(initialDefectListId)
  const [workcardGroup, setWorkcardGroup] = useState<WorkCardGroup | null>(initialWorkcardGroup ?? null)

  const initialMatchResults: MatchResult[] =
    locationState.matchResults && Array.isArray(locationState.matchResults)
      ? locationState.matchResults.map((item) => ({
        ...item,
        description_cn: item.description_cn || (item as any).title || '',
        description_en: item.description_en || ''
      }))
      : []

  const [matchResults, setMatchResults] = useState<MatchResult[]>(initialMatchResults)
  const [loadingMatchResults, setLoadingMatchResults] = useState(false)
  const [pendingSelections, setPendingSelections] = useState<Record<number, number | undefined>>({})
  const [savingRecordIds, setSavingRecordIds] = useState<number[]>([])
  const [selectedBatchIds, setSelectedBatchIds] = useState<number[]>([])
  const [importingRecordIds, setImportingRecordIds] = useState<number[]>([])

  const [importPreviewLoading, setImportPreviewLoading] = useState(false)
  const [importPreviewData, setImportPreviewData] = useState<PreviewResponse | null>(null)
  const [selectedPreviewWorkcardRid, setSelectedPreviewWorkcardRid] = useState<string | undefined>()
  const [selectedPreviewHistoryRid, setSelectedPreviewHistoryRid] = useState<string | undefined>()
  const [importLogs, setImportLogs] = useState<PreviewResponse['logs']>([])
  const [importArtifacts, setImportArtifacts] = useState<PreviewResponse['artifacts']>([])
  const [importResult, setImportResult] = useState<RunResponse | null>(null)
  const [testLoading, setTestLoading] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState<string | null>(null)
  const [batchImportLoading, setBatchImportLoading] = useState(false)

  const [importBatches, setImportBatches] = useState<ImportBatchSummary[]>([])
  const [loadingImportBatches, setLoadingImportBatches] = useState(false)
  const [selectedImportBatchId, setSelectedImportBatchId] = useState<number | undefined>(
    locationState.importBatchId
  )
  const [editingWorkcardNumber, setEditingWorkcardNumber] = useState<{ defect_record_id: number; value: string } | null>(null)
  const [updatingWorkcardNumber, setUpdatingWorkcardNumber] = useState<number[]>([])
  const [batchImportStepsLoading, setBatchImportStepsLoading] = useState(false)
  const [importingStepsRecordIds, setImportingStepsRecordIds] = useState<number[]>([])
  const [savingBatch, setSavingBatch] = useState(false)
  const [saveModalVisible, setSaveModalVisible] = useState(false)
  const [metadataForm] = Form.useForm()

  const [acInfoLoading, setAcInfoLoading] = useState(false)

  const handleGetACInfo = async () => {
    try {
      const values = await importParamsForm.validateFields(['txtACNO', 'txtWO'])
      const cookieValues = await importForm.validateFields(['cookies'])
      setAcInfoLoading(true)

      const response = await workcardImportApi.getACInfo({
        tail_no: values.txtACNO,
        work_order: values.txtWO,
        cookies: composeCookies(cookieValues)
      })

      if (response.success && response.data) {
        const info = response.data
        // Fleet mapping: user said "fleet = txtFleet" which is in response as 'fleet'
        // PartNo: 'partno'
        // SerialNo: 'serialno'
        // tsn: 'tsn'
        // csn: 'csn'

        importParamsForm.setFieldsValue({
          txtFleet: info.fleet,
          txtACPartNo: info.partno,
          txtACSerialNo: info.serialno,
          txtTsn: info.tsn,
          txtCsn: info.csn,
          csn: `CSN:${info.csn}`, // Auto-format CSN: e.g. CSN:22692
          // tsn: info.tsn, // User manually inputs formatted TSN (e.g. TSN:46564:21)
        })
        message.success('获取飞机信息成功 (请手动填写格式化的TSN)')
      } else {
        message.warning(response.message || '未获取到匹配的飞机信息')
      }
    } catch (error: any) {
      console.error('获取飞机信息失败', error)
      message.error('获取飞机信息失败: ' + (error.message || '未知错误'))
    } finally {
      setAcInfoLoading(false)
    }
  }

  const autoLoadTriggeredRef = useRef(false)

  const readyForMatch = matchResults.length > 0 || selectedImportBatchId !== undefined

  // 处理外部Excel文件导入
  const handleExternalImport: UploadProps['beforeUpload'] = (file) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const data = e.target?.result
        const workbook = XLSX.read(data, { type: 'binary' })
        const sheetName = workbook.SheetNames[0]
        const sheet = workbook.Sheets[sheetName]
        const jsonData = XLSX.utils.sheet_to_json(sheet) as any[]

        if (!jsonData || jsonData.length === 0) {
          message.error('文件中没有数据')
          return
        }

        const newMatchResults: MatchResult[] = jsonData.map((row, index) => {
          // 按照用户指定的对应关系映射字段
          const defectNumber = row['缺陷编号'] || row['Defect Number'] || `IMP-${index + 1}`
          const descriptionCn = row['工卡描述中文'] || row['工卡描述（中文）'] || row['缺陷描述'] || row['Description (CN)'] || ''
          const descriptionEn = row['工卡描述英文'] || row['工卡描述（英文）'] || row['Description (EN)'] || ''
          const relativeJobcardNumber = row['相关工卡号'] || row['relative jobcard'] || ''
          const relativeJobcardSequence = row['相关工卡序号'] || ''
          const zone = row['区域'] || row['Zone'] || ''
          const zoneTen = row['区域号'] || row['Zone Ten'] || ''

          // 关键字段：已开出工卡号
          // 根据用户指定的对应关系：Excel列名 '已开工卡号' 对应数据库字段 issued_workcard_number
          const issuedWorkcardNumber = row['已开工卡号'] || row['已开出工卡号'] || row['Issued Workcard'] || 'NR/000'

          // 关键字段：候选工卡指令号
          // 根据用户指定的对应关系：Excel列名 '候选工卡' 对应数据库字段 workcard_number
          const candidateWorkOrder = row['候选工卡'] || row['候选工卡指令号'] || row['Candidate Workcard'] || row['工卡指令号'] || ''

          // 如果有候选工卡指令号，构建一个虚拟的候选工卡对象
          const candidates: CandidateWorkCard[] = []
          let selectedWorkcardId: number | undefined = undefined

          if (candidateWorkOrder) {
            // 使用负数ID作为临时ID，避免与数据库ID冲突
            const mockCandidateId = -(index + 1000)
            candidates.push({
              id: mockCandidateId,
              workcard_number: candidateWorkOrder,
              description: descriptionCn || '导入数据',
              similarity_score: 100 // 默认给满分
            })
            selectedWorkcardId = mockCandidateId
          }

          return {
            defect_record_id: -(index + 1), // 使用负数ID
            defect_number: defectNumber,
            description_cn: descriptionCn,
            description_en: descriptionEn,
            relative_jobcard_number: relativeJobcardNumber,
            relative_jobcard_sequence: relativeJobcardSequence,
            zone: zone,
            zone_ten: zoneTen,
            candidates: candidates,
            selected_workcard_id: selectedWorkcardId,
            issued_workcard_number: issuedWorkcardNumber
          }
        })

        // 更新状态
        setMatchResults(newMatchResults)
        setSelectedImportBatchId(undefined) // 清除选中的数据库批次
        setPendingSelections({})
        setSelectedBatchIds([])

        // 尝试从文件名提取飞机号等信息
        const fileName = (file as File).name
        // 简单的正则匹配飞机号 (B-XXXX)
        const acMatch = fileName.match(/B-\d{4}/)
        if (acMatch) {
          importParamsForm.setFieldsValue({ txtACNO: acMatch[0] })
        }

        message.success(`成功导入 ${newMatchResults.length} 条数据`)
      } catch (error: any) {
        message.error('解析文件失败: ' + (error.message || error))
      }
    }
    reader.readAsBinaryString(file as File)
    return false // 阻止自动上传
  }

  useEffect(() => {
    if (initialMatchResults.length > 0) {
      autoLoadTriggeredRef.current = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const fetchImportBatches = async () => {
    try {
      setLoadingImportBatches(true)
      const batches = await importBatchApi.list()
      setImportBatches(batches)
      return batches
    } catch (error: any) {
      message.error('获取待导入工卡数据表失败: ' + (error?.message || error))
      return []
    } finally {
      setLoadingImportBatches(false)
    }
  }

  useEffect(() => {
    let cancelled = false
    const init = async () => {
      const batches = await fetchImportBatches()
      if (cancelled) return
      if (batches && batches.length > 0) {
        const targetId = selectedImportBatchId ?? batches[0].id
        setSelectedImportBatchId(targetId)
        loadImportBatch(targetId)
      }
    }
    init()
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!defectListId) {
      return
    }
    if (matchResults.length > 0) {
      return
    }
    if (autoLoadTriggeredRef.current) {
      return
    }
    autoLoadTriggeredRef.current = true
    const configurationId = workcardGroup?.configuration_id
    loadMatchResults(defectListId, configurationId)
  }, [defectListId, workcardGroup?.configuration_id, matchResults.length])

  useEffect(() => {
    const loadDefectListInfo = async () => {
      if (!defectListId || defectListInfo) {
        return
      }
      try {
        const info = await defectApi.getList(defectListId)
        setDefectListInfo({
          id: info.id,
          title: info.title,
          aircraft_number: info.aircraft_number
        })
      } catch (error: any) {
        message.error('获取缺陷清单信息失败: ' + (error?.message || error))
      }
    }
    loadDefectListInfo()
  }, [defectListId, defectListInfo])

  const loadMatchResults = async (listId: number, configurationId?: number) => {
    try {
      setLoadingMatchResults(true)
      const response = await matchingApi.getSavedResults({
        defect_list_id: listId,
        configuration_id: configurationId
      })
      if (!response.success) {
        message.error('加载匹配结果失败，请稍后再试')
        setMatchResults([])
        return
      }
      const formatted: MatchResult[] = response.results.map((item) => ({
        defect_record_id: item.defect_record_id,
        defect_number: item.defect_number,
        description_cn: item.description_cn || '',
        description_en: item.description_en || '',
        candidates: item.candidates.map((candidate) => ({
          id: candidate.id,
          workcard_number: candidate.workcard_number,
          description: candidate.description || '',
          similarity_score: candidate.similarity_score
        })),
        selected_workcard_id: item.selected_workcard_id || undefined,
        issued_workcard_number: (item as any).issued_workcard_number || 'NR/000'  // 默认值
      }))
      if (formatted.length === 0) {
        message.warning('未找到已保存的匹配结果，请先执行缺陷匹配流程')
      }
      setMatchResults(formatted)
      setPendingSelections({})
      setSelectedBatchIds([])
      resetImportState(true)
    } catch (error: any) {
      message.error('加载匹配结果失败: ' + (error?.message || error))
    } finally {
      setLoadingMatchResults(false)
    }
  }

  const loadImportBatch = async (batchId: number) => {
    try {
      setLoadingMatchResults(true)
      const detail = await importBatchApi.getById(batchId)
      setSelectedImportBatchId(batchId)
      autoLoadTriggeredRef.current = true

      if (detail.defect_list_id) {
        setDefectListId(detail.defect_list_id)
      } else {
        setDefectListId(undefined)
      }

      setDefectListInfo({
        id: detail.id,
        title: `待导入批次 #${detail.id}`,
        aircraft_number: detail.aircraft_number || ''
      })

      setWorkcardGroup({
        configuration_id: detail.defect_list_id ?? 0,
        aircraft_number: detail.aircraft_number || undefined,
        aircraft_type: detail.aircraft_type || undefined,
        msn: undefined,
        amm_ipc_eff: undefined,
        count: detail.items.length,
        min_id: 0
      })

      const formatted: MatchResult[] = detail.items.map((item, index) => {
        const candidates: CandidateWorkCard[] = []
        let selectedWorkcardId: number | undefined = undefined
        
        // 如果数据库中有候选工卡号，创建候选工卡对象
        if (item.workcard_number) {
          const candidateId =
            item.selected_workcard_id ??
            (item.defect_record_id ? item.defect_record_id : index + 1)
          candidates.push({
            id: candidateId,
            workcard_number: item.workcard_number,
            description: item.description_cn || '',
            similarity_score: item.similarity_score ?? 0
          })
          selectedWorkcardId = candidateId
        } else if (item.selected_workcard_id) {
          // 即使workcard_number为空，如果数据库中有selected_workcard_id，也保留它
          // 这可能是之前保存的数据，虽然候选工卡号被清空了，但选择状态还在
          selectedWorkcardId = item.selected_workcard_id
        }
        
        return {
          defect_record_id: item.defect_record_id ?? -(index + 1),
          defect_number: item.defect_number,
          description_cn: item.description_cn || '',
          description_en: item.description_en || '',
          candidates: candidates,
          selected_workcard_id: selectedWorkcardId,
          issued_workcard_number: (item as any).issued_workcard_number || 'NR/000',  // 默认值
          // Map newly added fields
          zone: (item as any).area || (item as any).zone || '',
          zone_ten: (item as any).zone_number || (item as any).txtZoneTen || '',
          relative_jobcard_number: (item as any).reference_workcard_number || (item as any).txtCRN || '',
          relative_jobcard_sequence: (item as any).reference_workcard_item || (item as any).refNo || ''
        }
      })

      setMatchResults(formatted)
      setPendingSelections({})
      setSelectedBatchIds([])
      resetImportState(true)
    } catch (error: any) {
      message.error('加载待导入工卡数据失败: ' + (error?.message || error))
    } finally {
      setLoadingMatchResults(false)
    }
  }

  useEffect(() => {
    setSelectedBatchIds((prev) =>
      prev.filter((id) => matchResults.some((item) => item.defect_record_id === id))
    )
  }, [matchResults])

  const composeCookies = (values: any) => {
    // 内网直连模式：如果提供了Cookie字符串，直接使用；否则返回空字符串
    const cookies = (values.cookies || '').trim()
    return cookies
  }

  const getImportParams = () => ({
    tail_no: '',
    src_work_order: '',
    target_work_order: '',
    work_group: ''
  })

  const resetImportState = (resetForm: boolean = false) => {
    setImportPreviewData(null)
    setImportLogs([])
    setImportArtifacts([])
    setSelectedPreviewWorkcardRid(undefined)
    setSelectedPreviewHistoryRid(undefined)
    setImportResult(null)
    setConnectionStatus(null)
    setImportingRecordIds([])
    setBatchImportLoading(false)
    if (resetForm) {
      importForm.resetFields()
    }
  }

  const fetchPreviewData = async (values: any) => {
    try {
      setImportPreviewLoading(true)
      // setImportRunLoading(false) removed
      setImportResult(null)
      setImportLogs([])
      setImportArtifacts([])
      setConnectionStatus(null)
      setImportPreviewData(null)
      setSelectedPreviewWorkcardRid(undefined)
      setSelectedPreviewHistoryRid(undefined)
      const baseParams = getImportParams()
      if (!baseParams.tail_no || !baseParams.src_work_order || !baseParams.target_work_order || !baseParams.work_group) {
        message.error('请在代码中配置默认的导入参数')
        return null
      }
      const response = await workcardImportApi.preview({
        ...baseParams,
        cookies: composeCookies(values)
      })
      setImportPreviewData(response)
      setImportLogs(response.logs)
      setImportArtifacts(response.artifacts)
      if (response.workcards.length > 0) {
        setSelectedPreviewWorkcardRid(response.workcards[0].rid)
      }
      if (response.history_cards.length > 0) {
        setSelectedPreviewHistoryRid(response.history_cards[0].rid)
      }
      if (response.workcards.length === 0) {
        message.warning('未查询到可导入的工卡，请检查源工单号与工作组设置')
      } else {
        message.success(`成功预加载 ${response.workcards.length} 条工卡`)
      }
      return response
    } catch (error: any) {
      message.error('预加载失败: ' + (error?.message || error))
      return null
    } finally {
      setImportPreviewLoading(false)
    }
  }

  const handlePreviewImport = async () => {
    try {
      const values = await importForm.validateFields(['cookies'])
      await fetchPreviewData(values)
    } catch (error: any) {
      if (!error?.errorFields) {
        message.error('预加载失败: ' + (error?.message || error))
      }
    }
  }

  const handleTestConnection = async () => {
    try {
      const values = await importForm.validateFields(['cookies'])
      const baseParams = getImportParams()
      setTestLoading(true)
      setConnectionStatus(null)
      setImportLogs([])
      setImportArtifacts([])
      const response = await workcardImportApi.testConnection({
        ...baseParams,
        cookies: composeCookies(values)
      })
      setImportLogs(response.logs)
      setImportArtifacts(response.artifacts)
      setConnectionStatus(response.message)
      if (response.success) {
        message.success(response.message || '连接成功')
      } else {
        message.error(response.message || '连接失败')
      }
    } catch (error: any) {
      if (!error?.errorFields) {
        message.error('连接测试失败: ' + (error?.message || error))
      }
    } finally {
      setTestLoading(false)
    }
  }

  const handleCandidateChange = (defectRecordId: number, workcardId: number) => {
    const record = matchResults.find((item) => item.defect_record_id === defectRecordId)
    const savedValue = record?.selected_workcard_id
    setPendingSelections((prev) => {
      const newMap = { ...prev }
      if (savedValue === workcardId) {
        delete newMap[defectRecordId]
      } else {
        newMap[defectRecordId] = workcardId
      }
      return newMap
    })
  }

  const handleSaveSelection = async (defectRecordId: number) => {
    const candidateId = pendingSelections[defectRecordId]
    if (!candidateId) {
      message.warning('请先选择候选工卡')
      return
    }
    try {
      setSavingRecordIds((prev) => [...prev, defectRecordId])
      await defectApi.selectWorkcard(defectRecordId, candidateId)
      message.success('已保存工卡选择')
      setMatchResults((prev) =>
        prev.map((result) =>
          result.defect_record_id === defectRecordId
            ? { ...result, selected_workcard_id: candidateId }
            : result
        )
      )
      setPendingSelections((prev) => {
        const newMap = { ...prev }
        delete newMap[defectRecordId]
        return newMap
      })
    } catch (error: any) {
      message.error('保存失败: ' + (error.message || error))
    } finally {
      setSavingRecordIds((prev) => prev.filter((id) => id !== defectRecordId))
    }
  }

  const handleImportBatchChange = async (value: number) => {
    setSelectedImportBatchId(value)
    await loadImportBatch(value)
  }

  const handleDeleteBatch = async (batchId: number) => {
    try {
      await importBatchApi.delete(batchId)
      message.success('删除成功')

      // Refresh list
      await fetchImportBatches()

      // Clean up selection if deleted batch was selected
      if (selectedImportBatchId === batchId) {
        setSelectedImportBatchId(undefined)
        setMatchResults([])
        setPendingSelections({})
        setSelectedBatchIds([])
        setDefectListInfo(undefined)
        setWorkcardGroup(null)
      }
    } catch (error: any) {
      message.error('删除失败: ' + (error?.message || error))
    }
  }

  const handleUpdateWorkcardNumber = async (defect_record_id: number, workcard_number: string) => {
    try {
      setUpdatingWorkcardNumber((prev) => [...prev, defect_record_id])
      await defectApi.updateIssuedWorkcardNumber(defect_record_id, workcard_number)

      // 更新本地状态
      setMatchResults((prev) =>
        prev.map((item) =>
          item.defect_record_id === defect_record_id
            ? { ...item, issued_workcard_number: workcard_number }
            : item
        )
      )

      message.success('工卡号更新成功')
      setEditingWorkcardNumber(null)
    } catch (error: any) {
      message.error('更新工卡号失败: ' + (error?.message || error))
    } finally {
      setUpdatingWorkcardNumber((prev) => prev.filter((id) => id !== defect_record_id))
    }
  }

  const handleImportSingle = async (record: MatchResult) => {
    // 开卡操作不需要候选工卡，候选工卡只用于导入步骤
    try {
      const cookieValues = await importForm.validateFields(['cookies'])
      const importParams = await importParamsForm.validateFields()

      // 确认是否开出工卡
      Modal.confirm({
        title: '确认开出工卡',
        content: `确定要为缺陷 ${record.defect_number} 开出工卡吗？`,
        okText: '确认开出',
        cancelText: '取消',
        onOk: async () => {
          try {
            setImportingRecordIds((prev) => [...prev, record.defect_record_id])

            // 构建导入参数
            const params = {
              'txtCust': importParams.txtCust || '',
              'txtACNO': importParams.txtACNO || '',
              'txtWO': importParams.txtWO || '',
              'txtML': importParams.txtML || '',
              'txtACType': importParams.txtACType || 'B737-300',
              'txtWorkContent': '',
              'txtZoneName': record.zone || '',
              'txtZoneTen': record.zone_ten || '',
              'txtRII': '',
              'txtCRN': record.relative_jobcard_number || '客户要求/CUSTOMER REQUIREMENT',
              'refNo': record.relative_jobcard_sequence || '',
              'txtEnginSn': '',
              'txtDescChn': record.description_cn || '',
              'txtDescEng': record.description_en || '',
              'txtDept': '3_CABIN_TPG',
              'selDocType': 'NR',
              'csn': importParams.csn || '',
              'tsn': importParams.tsn || '',
              'txtCorrosion': 'N',
              'txtMenuID': '13541',
              'txtParentID': '13112',
              'txtFleet': importParams.txtFleet || '',
              'txtACPartNo': importParams.txtACPartNo || '',
              'txtACSerialNo': importParams.txtACSerialNo || '',
              'txtTsn': importParams.txtTsn || '',
              'txtCsn': importParams.txtCsn || '',
              'jcMode': 'C',
              'flagEu': '',
              'txtFlag': '',
            }

            const response = await workcardImportApi.importDefect({
              defect_record_id: record.defect_record_id,
              params,
              cookies: composeCookies(cookieValues),
            })

            setImportLogs(response.logs)
            setImportArtifacts(response.artifacts)

            if (response.success) {
              // 更新匹配结果中的工卡号
              if (response.workcard_number) {
                setMatchResults((prev) =>
                  prev.map((item) =>
                    item.defect_record_id === record.defect_record_id
                      ? { ...item, issued_workcard_number: response.workcard_number || undefined }
                      : item
                  )
                )
              }
              message.success(`缺陷 ${record.defect_number} 开出工卡成功${response.workcard_number ? `，工卡号: ${response.workcard_number}` : ''}`)
            } else {
              message.error(`缺陷 ${record.defect_number} 开出工卡失败: ${response.message}`)
            }
          } catch (error: any) {
            if (!error?.errorFields) {
              message.error(`开出工卡失败: ${error?.message || error}`)
            }
          } finally {
            setImportingRecordIds((prev) => prev.filter((id) => id !== record.defect_record_id))
          }
        }
      })
    } catch (error: any) {
      if (!error?.errorFields) {
        // 表单验证失败，不需要处理
      }
    }
  }

  const handleBatchImport = async () => {
    if (selectedBatchIds.length === 0) {
      message.warning('请先勾选需要批量开出工卡的缺陷记录')
      return
    }
    try {
      const cookieValues = await importForm.validateFields(['cookies'])
      const importParams = await importParamsForm.validateFields()
      const cookies = composeCookies(cookieValues)

      // 确认是否批量开出工卡
      Modal.confirm({
        title: '确认批量开出工卡',
        content: `确定要为选中的 ${selectedBatchIds.length} 条缺陷记录批量开出工卡吗？`,
        okText: '确认开出',
        cancelText: '取消',
        onOk: async () => {
          try {
            setImportLogs([])
            setImportArtifacts([])
            setBatchImportLoading(true)
            let successCount = 0
            const failureMessages: string[] = []

            for (const recordId of selectedBatchIds) {
              const record = matchResults.find((item) => item.defect_record_id === recordId)
              if (!record) continue
              // 开卡操作不需要候选工卡，候选工卡只用于导入步骤
              try {
                // 构建导入参数
                const params = {
                  'txtCust': importParams.txtCust || '',
                  'txtACNO': importParams.txtACNO || '',
                  'txtWO': importParams.txtWO || '',
                  'txtML': importParams.txtML || '',
                  'txtACType': importParams.txtACType || 'B737-300',
                  'txtWorkContent': '',
                  'txtZoneName': record.zone || '',
                  'txtZoneTen': record.zone_ten || '',
                  'txtRII': '',
                  'txtCRN': record.relative_jobcard_number || '客户要求/CUSTOMER REQUIREMENT',
                  'refNo': record.relative_jobcard_sequence || '',
                  'txtEnginSn': '',
                  'txtDescChn': record.description_cn || '',
                  'txtDescEng': record.description_en || '',
                  'txtDept': '3_CABIN_TPG',
                  'selDocType': 'NR',
                  'csn': importParams.csn || '',
                  'tsn': importParams.tsn || '',
                  'txtCorrosion': 'N',
                  'txtMenuID': '13541',
                  'txtParentID': '13112',
                  'txtFleet': importParams.txtFleet || '',
                  'txtACPartNo': importParams.txtACPartNo || '',
                  'txtACSerialNo': importParams.txtACSerialNo || '',
                  'txtTsn': importParams.txtTsn || '',
                  'txtCsn': importParams.txtCsn || '',
                  'jcMode': 'C',
                  'flagEu': '',
                  'txtFlag': '',
                }

                const response = await workcardImportApi.importDefect({
                  defect_record_id: record.defect_record_id,
                  params,
                  cookies,
                })

                setImportLogs(response.logs)
                setImportArtifacts(response.artifacts)

                if (response.success) {
                  successCount += 1
                  // 更新匹配结果中的工卡号
                  if (response.workcard_number) {
                    setMatchResults((prev) =>
                      prev.map((item) =>
                        item.defect_record_id === recordId
                          ? { ...item, issued_workcard_number: response.workcard_number || undefined }
                          : item
                      )
                    )
                  }
                } else {
                  failureMessages.push(`缺陷 ${record.defect_number}: ${response.message || '开出工卡失败'}`)
                }
              } catch (error: any) {
                failureMessages.push(`缺陷 ${record.defect_number}: ${error?.message || error}`)
              }
            }

            if (successCount > 0) {
              message.success(`批量开出工卡完成，成功 ${successCount} 条`)
            }
            if (failureMessages.length > 0) {
              message.error(failureMessages.join('；'))
            }
          } catch (error: any) {
            if (!error?.errorFields) {
              message.error('批量开出工卡失败: ' + (error?.message || error))
            }
          } finally {
            setBatchImportLoading(false)
            setSelectedBatchIds([])
          }
        }
      })
    } catch (error: any) {
      if (!error?.errorFields) {
        // 表单验证失败，不需要处理
      }
    }
  }

  const handleImportStepsSingle = async (record: MatchResult) => {
    // 导入步骤需要已开出工卡号和候选工卡（用于获取工卡指令号）
    if (!record.issued_workcard_number || record.issued_workcard_number === 'NR/000') {
      message.warning(`缺陷 ${record.defect_number} 需要已开出工卡号`)
      return
    }
    if (!record.selected_workcard_id) {
      message.warning(`缺陷 ${record.defect_number} 需要先保存候选工卡（导入步骤需要候选工卡的工卡指令号）`)
      return
    }

    try {
      const cookieValues = await importForm.validateFields(['cookies'])
      const importParams = await importParamsForm.validateFields()
      const cookies = composeCookies(cookieValues)

      // 找到选中的候选工卡，获取其工卡指令号（workcard_number）
      const selectedCandidate = record.candidates.find(
        (candidate) => candidate.id === record.selected_workcard_id
      )
      const candidateWorkOrder = selectedCandidate?.workcard_number || ''

      if (!candidateWorkOrder) {
        message.error(`缺陷 ${record.defect_number}: 未找到候选工卡的工卡指令号`)
        return
      }

      setImportingStepsRecordIds((prev) => [...prev, record.defect_record_id])

      try {
        const response = await workcardImportApi.importSteps({
          jobcard_number: record.issued_workcard_number || '',
          target_work_order: candidateWorkOrder, // qJcWorkOrder: 候选工卡的工卡指令号
          source_work_order: importParams.txtWO || '', // qWorkorder: 导入参数配置的工作指令号 (txtWO)
          tail_no: importParams.txtACNO || '',
          work_group: importParams.txtDept || '3_CABIN_TPG',
          cookies,
        })

        // 合并日志和产物
        if (response.logs) {
          setImportLogs((prev) => [...prev, ...response.logs])
        }
        if (response.artifacts) {
          setImportArtifacts((prev) => [...prev, ...response.artifacts])
        }

        if (response.success) {
          message.success(`缺陷 ${record.defect_number} 步骤导入成功，共导入 ${response.imported_count || 0} 个步骤`)
        } else {
          message.error(`缺陷 ${record.defect_number} 步骤导入失败: ${response.message || '未知错误'}`)
        }
      } catch (error: any) {
        message.error(`缺陷 ${record.defect_number} 步骤导入失败: ${error?.message || error}`)
      } finally {
        setImportingStepsRecordIds((prev) => prev.filter((id) => id !== record.defect_record_id))
      }
    } catch (error: any) {
      if (!error?.errorFields) {
        message.error('导入步骤失败: ' + (error?.message || error))
      }
    }
  }

  const handleBatchImportSteps = async () => {
    if (selectedBatchIds.length === 0) {
      message.warning('请先勾选需要批量导入步骤的缺陷记录')
      return
    }

    // 检查选中的记录是否都有已开出工卡号和候选工卡（导入步骤需要候选工卡的工卡指令号）
    const validRecords = matchResults.filter(
      (item) =>
        selectedBatchIds.includes(item.defect_record_id) &&
        item.issued_workcard_number &&
        item.issued_workcard_number !== 'NR/000' &&
        item.selected_workcard_id  // 导入步骤需要候选工卡
    )

    if (validRecords.length === 0) {
      message.warning('选中的记录中没有符合条件的记录（需要已开出工卡号且已保存候选工卡，导入步骤需要候选工卡的工卡指令号）')
      return
    }

    if (validRecords.length < selectedBatchIds.length) {
      message.warning(`选中的 ${selectedBatchIds.length} 条记录中，只有 ${validRecords.length} 条符合条件`)
    }

    try {
      const cookieValues = await importForm.validateFields(['cookies'])
      const importParams = await importParamsForm.validateFields()
      const cookies = composeCookies(cookieValues)

      // 确认是否批量导入步骤
      Modal.confirm({
        title: '确认批量导入步骤',
        content: `确定要为选中的 ${validRecords.length} 条缺陷记录批量导入步骤吗？`,
        okText: '确认导入',
        cancelText: '取消',
        onOk: async () => {
          try {
            setBatchImportStepsLoading(true)
            setImportLogs([])
            setImportArtifacts([])

            let successCount = 0
            let totalImportedSteps = 0
            const failureMessages: string[] = []
            const results: Array<{
              defect_number: string
              success: boolean
              message: string
              imported_count?: number
              failed_count?: number
            }> = []

            for (const record of validRecords) {
              try {
                // 找到选中的候选工卡，获取其工卡指令号（workcard_number）
                const selectedCandidate = record.candidates.find(
                  (candidate) => candidate.id === record.selected_workcard_id
                )
                const candidateWorkOrder = selectedCandidate?.workcard_number || ''

                if (!candidateWorkOrder) {
                  failureMessages.push(`缺陷 ${record.defect_number}: 未找到候选工卡的工卡指令号`)
                  results.push({
                    defect_number: record.defect_number,
                    success: false,
                    message: '未找到候选工卡的工卡指令号'
                  })
                  continue
                }

                const response = await workcardImportApi.importSteps({
                  jobcard_number: record.issued_workcard_number || '',
                  target_work_order: candidateWorkOrder, // qJcWorkOrder: 候选工卡的工卡指令号
                  source_work_order: importParams.txtWO || '', // qWorkorder: 导入参数配置的工作指令号 (txtWO)
                  tail_no: importParams.txtACNO || '',
                  work_group: importParams.txtDept || '3_CABIN_TPG',
                  cookies,
                })

                // 合并日志和产物
                if (response.logs) {
                  setImportLogs((prev) => [...prev, ...response.logs])
                }
                if (response.artifacts) {
                  setImportArtifacts((prev) => [...prev, ...response.artifacts])
                }

                if (response.success) {
                  successCount += 1
                  totalImportedSteps += response.imported_count || 0
                  results.push({
                    defect_number: record.defect_number,
                    success: true,
                    message: response.message || '导入成功',
                    imported_count: response.imported_count,
                    failed_count: response.failed_count
                  })
                } else {
                  failureMessages.push(`缺陷 ${record.defect_number}: ${response.message || '导入失败'}`)
                  results.push({
                    defect_number: record.defect_number,
                    success: false,
                    message: response.message || '导入失败',
                    imported_count: response.imported_count,
                    failed_count: response.failed_count
                  })
                }
              } catch (error: any) {
                failureMessages.push(`缺陷 ${record.defect_number}: ${error?.message || error}`)
                results.push({
                  defect_number: record.defect_number,
                  success: false,
                  message: error?.message || '导入失败'
                })
              }
            }

            // 显示汇总结果
            if (successCount > 0) {
              message.success(`批量导入步骤完成，成功 ${successCount} 条，共导入 ${totalImportedSteps} 个步骤`)
            }
            if (failureMessages.length > 0) {
              message.error(failureMessages.join('；'))
            }

            // 显示详细结果Modal
            Modal.info({
              title: '批量导入步骤结果',
              width: 800,
              content: (
                <div>
                  <div style={{ marginBottom: 16 }}>
                    <Tag color="green">成功: {successCount} 条</Tag>
                    <Tag color="red">失败: {failureMessages.length} 条</Tag>
                    <Tag color="blue">共导入步骤: {totalImportedSteps} 个</Tag>
                  </div>
                  <List
                    dataSource={results}
                    renderItem={(item) => (
                      <List.Item>
                        <Space>
                          <Tag color={item.success ? 'green' : 'red'}>
                            {item.success ? '✓' : '✗'}
                          </Tag>
                          <span><strong>{item.defect_number}</strong></span>
                          <span>{item.message}</span>
                          {item.imported_count !== undefined && (
                            <Tag color="blue">导入: {item.imported_count}</Tag>
                          )}
                          {item.failed_count !== undefined && item.failed_count > 0 && (
                            <Tag color="red">失败: {item.failed_count}</Tag>
                          )}
                        </Space>
                      </List.Item>
                    )}
                  />
                </div>
              )
            })
          } catch (error: any) {
            if (!error?.errorFields) {
              message.error('批量导入步骤失败: ' + (error?.message || error))
            }
          } finally {
            setBatchImportStepsLoading(false)
          }
        }
      })
    } catch (error: any) {
      if (!error?.errorFields) {
        // 表单验证失败，不需要处理
      }
    }
  }



  const handleOpenSaveModal = () => {
    if (matchResults.length === 0) {
      message.warning('没有可保存的数据')
      return
    }
    // 尝试自动填充飞机号（如果有defectList信息）
    if (defectListInfo) {
      metadataForm.setFieldsValue({
        aircraft_number: defectListInfo.aircraft_number
      })
    }
    setSaveModalVisible(true)
  }

  const executeSaveBatch = async () => {
    try {
      const values = await metadataForm.validateFields()

      const items = matchResults.map((result) => {
        let selectedCandidate = result.candidates.find(
          (candidate) => candidate.id === result.selected_workcard_id
        )
        // fix: 如果是直接Excel导入的，candidate可能就是虚拟的，确保数据完整性
        if (!selectedCandidate && result.candidates.length > 0) {
          selectedCandidate = result.candidates[0]
        }

        return {
          defect_record_id: result.defect_record_id > 0 ? result.defect_record_id : null,
          defect_number: result.defect_number,
          description_cn: result.description_cn,
          description_en: result.description_en,
          // 候选工卡：只使用Excel中的"候选工卡"字段，如果没有数据则留空（null），不使用相关工卡号
          workcard_number: selectedCandidate?.workcard_number && selectedCandidate.workcard_number.trim() !== '' 
            ? selectedCandidate.workcard_number 
            : null,
          issued_workcard_number: result.issued_workcard_number,
          selected_workcard_id: selectedCandidate?.id && selectedCandidate.id > 0 ? selectedCandidate.id : null,
          similarity_score: selectedCandidate?.similarity_score ?? 0,
          // 按照用户指定的对应关系添加扩展字段
          reference_workcard_number: result.relative_jobcard_number || null,
          reference_workcard_item: result.relative_jobcard_sequence || null,
          area: result.zone || null,
          zone_number: result.zone_ten || null
        }
      })

      setSavingBatch(true)
      const payload = {
        metadata: {
          aircraft_number: values.aircraft_number,
          workcard_number: values.workcard_number,
          maintenance_level: values.maintenance_level,
          aircraft_type: values.aircraft_type,
          customer: values.customer,
          defect_list_id: defectListId
        },
        items
      }

      const result = await importBatchApi.create(payload)
      message.success('已保存到待导入工卡数据表')

      // Refresh the dropdown list and then select the new batch
      await fetchImportBatches()
      setSaveModalVisible(false)
      // Reload as a fresh batch
      setSelectedImportBatchId(result.id)
      loadImportBatch(result.id)

    } catch (error: any) {
      console.error('Save Batch Error:', error)
      if (error.errorFields) {
        return // Validation failed
      }
      let errorMsg = error.message || '未知错误'
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail
        if (typeof detail === 'string') {
          errorMsg = detail
        } else if (Array.isArray(detail)) {
          // Format Pydantic validation errors
          errorMsg = detail.map((e: any) => `${e.loc?.join('.')}: ${e.msg}`).join('; ')
        } else if (typeof detail === 'object') {
          errorMsg = JSON.stringify(detail)
        }
      } else if (typeof error === 'object' && Object.keys(error).length > 0) {
        // If error is just [object Object] with no message
        errorMsg = JSON.stringify(error)
      }

      message.error(`保存失败: ${errorMsg}`)
    } finally {
      setSavingBatch(false)
    }
  }

  const matchResultColumns: ColumnsType<MatchResult> = [
    {
      title: '缺陷编号',
      dataIndex: 'defect_number',
      key: 'defect_number',
      width: 160,
      fixed: 'left',
      render: (text: string) => <Tag color="blue">{text}</Tag>,
    },
    {
      title: '区域',
      dataIndex: 'zone',
      key: 'zone',
      width: 80,
      render: (text: string) => text || '-'
    },
    {
      title: '区域号',
      dataIndex: 'zone_ten',
      key: 'zone_ten',
      width: 80,
      render: (text: string) => text || '-'
    },
    {
      title: '工卡描述（中文）',
      dataIndex: 'description_cn',
      key: 'description_cn',
      width: 300,
      ellipsis: true,
      render: (text: string) => text || '-'
    },
    {
      title: '工卡描述（英文）',
      dataIndex: 'description_en',
      key: 'description_en',
      width: 300,
      ellipsis: true,
      render: (text: string) => text || '-'
    },
    {
      title: '相关工卡号',
      dataIndex: 'relative_jobcard_number',
      key: 'relative_jobcard_number',
      width: 150,
      render: (text: string) => text || '-'
    },
    {
      title: '相关工卡序号',
      dataIndex: 'relative_jobcard_sequence',
      key: 'relative_jobcard_sequence',
      width: 120,
      render: (text: string) => text || '-'
    },
    {
      title: '候选工卡',
      key: 'candidates',
      width: 480,
      render: (_: any, record: MatchResult) => (
        <Radio.Group
          value={
            pendingSelections[record.defect_record_id] !== undefined
              ? pendingSelections[record.defect_record_id]
              : record.selected_workcard_id
          }
          style={{ width: '100%' }}
          onChange={(e) => handleCandidateChange(record.defect_record_id, e.target.value)}
        >
          <Space direction="vertical" style={{ width: '100%' }}>
            {record.candidates.map((candidate) => (
              <Radio key={candidate.id} value={candidate.id}>
                <Space>
                  <Tag color="purple">工卡: {candidate.workcard_number}</Tag>
                  <span>描述: {candidate.description || '-'}</span>
                  <Tag
                    color={
                      candidate.similarity_score >= 80
                        ? 'green'
                        : candidate.similarity_score >= 60
                          ? 'orange'
                          : 'red'
                    }
                  >
                    相似度: {candidate.similarity_score.toFixed(1)}%
                  </Tag>
                </Space>
              </Radio>
            ))}
            {record.candidates.length === 0 && <span style={{ color: '#999' }}>暂无候选工卡</span>}
          </Space>
        </Radio.Group>
      )
    },
    {
      title: '已开出工卡号',
      dataIndex: 'issued_workcard_number',
      key: 'issued_workcard_number',
      width: 200,
      render: (text: string, record: MatchResult) => {
        const isUpdating = updatingWorkcardNumber.includes(record.defect_record_id)
        const displayValue = text || 'NR/000'
        return (
          <Space>
            <Tag color="green">{displayValue}</Tag>
            <Button
              type="link"
              size="small"
              icon={<EditOutlined />}
              loading={isUpdating}
              disabled={isUpdating}
              onClick={() => setEditingWorkcardNumber({ defect_record_id: record.defect_record_id, value: displayValue })}
            >
              修改
            </Button>
          </Space>
        )
      }
    },
    {
      title: '操作',
      key: 'actions',
      width: 280,
      fixed: 'right',
      render: (_: any, record: MatchResult) => {
        const pendingSelection = pendingSelections[record.defect_record_id]
        const savedSelection = record.selected_workcard_id
        const hasUnsaved = pendingSelection !== undefined && pendingSelection !== savedSelection
        const isSaving = savingRecordIds.includes(record.defect_record_id)
        const isImporting = importingRecordIds.includes(record.defect_record_id)
        return (
          <Space>
            <Button
              size="small"
              type="primary"
              ghost
              disabled={!hasUnsaved}
              loading={isSaving}
              onClick={() => handleSaveSelection(record.defect_record_id)}
            >
              保存
            </Button>
            <Button
              size="small"
              type="primary"
              loading={isImporting}
              disabled={isImporting}
              onClick={() => handleImportSingle(record)}
            >
              开卡
            </Button>
            <Button
              size="small"
              icon={<FileTextOutlined />}
              // 导入步骤需要已开出工卡号和候选工卡（用于获取工卡指令号）
              disabled={!record.issued_workcard_number || record.issued_workcard_number === 'NR/000' || !record.selected_workcard_id || importingStepsRecordIds.includes(record.defect_record_id)}
              loading={importingStepsRecordIds.includes(record.defect_record_id)}
              onClick={() => handleImportStepsSingle(record)}
            >
              导入步骤
            </Button>
          </Space>
        )
      },
    },
  ]

  const rowSelection = {
    selectedRowKeys: selectedBatchIds,
    onChange: (selectedRowKeys: React.Key[]) => {
      setSelectedBatchIds(selectedRowKeys as number[])
    },
    preserveSelectedRowKeys: true,
    // 允许选中所有行，即使没有候选工卡也可以选中（用于批量操作）
    // 候选工卡的验证会在实际执行操作时进行
    getCheckboxProps: (record: MatchResult) => ({
      disabled: false
    }),
  }

  const handleBack = () => {
    navigate('/defect-processing', { replace: false })
  }

  const handleGoHome = () => {
    navigate('/')
  }

  if (!readyForMatch) {
    if (loadingImportBatches) {
      return (
        <div style={{ padding: '64px', textAlign: 'center' }}>
          <Spin size="large" />
          <div style={{ marginTop: 16, color: '#666' }}>正在加载可用的待导入数据表...</div>
        </div>
      )
    }
    if (importBatches.length === 0 && matchResults.length === 0) {
      return (
        <Result
          status="info"
          title="未找到可用的批量开卡数据"
          subTitle="请先在缺陷处理流程中完成匹配并保存待导入数据表，或稍后再试。"
          extra={[
            <Button key="back" type="primary" icon={<LeftOutlined />} onClick={handleBack}>
              返回缺陷处理
            </Button>,
            <Button key="home" icon={<HomeOutlined />} onClick={handleGoHome}>
              返回首页
            </Button>
          ]}
        />
      )
    }
    return (
      <Result
        status="info"
        title="请选择待导入工卡数据表"
        subTitle="请在页面顶部的下拉框选择一个已保存的批次，或返回缺陷处理页面继续匹配。"
        extra={[
          <Button key="back" type="primary" icon={<LeftOutlined />} onClick={handleBack}>
            返回缺陷处理
          </Button>,
          <Button key="home" icon={<HomeOutlined />} onClick={handleGoHome}>
            返回首页
          </Button>
        ]}
      />
    )
  }

  return (
    <div style={{ padding: '24px', background: '#f0f2f5', minHeight: '100vh' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <Space>
          <Button icon={<LeftOutlined />} onClick={handleBack}>
            返回缺陷处理
          </Button>
          <Button icon={<HomeOutlined />} onClick={handleGoHome}>
            返回首页
          </Button>
        </Space>
        <Button
          icon={<ReloadOutlined />}
          onClick={() => {
            if (selectedImportBatchId) {
              loadImportBatch(selectedImportBatchId)
            } else if (defectListId) {
              autoLoadTriggeredRef.current = true
              loadMatchResults(defectListId, workcardGroup?.configuration_id)
            } else {
              message.warning('暂无可刷新的数据，请先选择待导入数据表或缺陷清单')
            }
          }}
          loading={loadingMatchResults}
        >
          刷新匹配结果
        </Button>
      </div>

      <Card style={{ marginBottom: '24px' }}>
        <Title level={3} style={{ marginBottom: '16px' }}>
          批量开卡 - 导入执行页面
        </Title>
        <Paragraph type="secondary" style={{ marginBottom: '16px' }}>
          此页面用于连接公司网络环境并执行批量开卡操作，请先确认缺陷候选关系已保存。
        </Paragraph>
        <div style={{ marginBottom: '16px' }}>
          <Space>
            <span style={{ color: '#666' }}>选择待导入数据表：</span>
            <Select
              style={{ minWidth: 320 }}
              value={selectedImportBatchId}
              onChange={(value) => {
                if (value === undefined) {
                  setSelectedImportBatchId(undefined)
                  setMatchResults([])
                  setPendingSelections({})
                  setSelectedBatchIds([])
                  setDefectListInfo(undefined)
                  setWorkcardGroup(null)
                  return
                }
                handleImportBatchChange(Number(value))
              }}
              placeholder="请选择已保存的待导入工卡数据表"
              loading={loadingImportBatches}
              allowClear
            >
              {importBatches.map((batch) => (
                <Option key={batch.id} value={batch.id}>
                  {`批次 #${batch.id} / 飞机号 ${batch.aircraft_number} / 工卡 ${batch.workcard_number} （${batch.item_count} 条）`}
                </Option>
              ))}
            </Select>
            {selectedImportBatchId && (
              <Popconfirm
                title="确定要删除这个待导入数据表吗？"
                description="删除后无法恢复"
                onConfirm={() => handleDeleteBatch(selectedImportBatchId)}
                okText="确定"
                cancelText="取消"
              >
                <Button icon={<DeleteOutlined />} danger title="删除选中数据表" />
              </Popconfirm>
            )}
            <Upload accept=".xlsx,.xls" showUploadList={false} beforeUpload={handleExternalImport}>
              <Button icon={<UploadOutlined />}>导入待开卡数据表</Button>
            </Upload>
            <Button
              type="primary"
              onClick={handleOpenSaveModal}
              disabled={matchResults.length === 0}
            >
              保存到待导入表
            </Button>
          </Space>
        </div>
      </Card>

      <Modal
        title="保存到待导入工卡数据表"
        open={saveModalVisible}
        onCancel={() => setSaveModalVisible(false)}
        onOk={executeSaveBatch}
        confirmLoading={savingBatch}
        okText="保存"
        cancelText="取消"
        destroyOnClose
      >
        <Form form={metadataForm} layout="vertical">
          <Form.Item
            label="飞机号"
            name="aircraft_number"
            rules={[{ required: true, message: '请输入飞机号' }]}
          >
            <Input placeholder="请输入飞机号" />
          </Form.Item>
          <Form.Item
            label="工卡指令号"
            name="workcard_number"
            rules={[{ required: true, message: '请输入工卡指令号' }]}
          >
            <Input placeholder="请输入工卡指令号" />
          </Form.Item>
          <Form.Item
            label="维修级别"
            name="maintenance_level"
            rules={[{ required: true, message: '请输入维修级别' }]}
          >
            <Input placeholder="请输入维修级别" />
          </Form.Item>
          <Form.Item
            label="机型"
            name="aircraft_type"
            initialValue="B737-300"
            rules={[{ required: true, message: '请输入机型' }]}
          >
            <Input placeholder="请输入机型" />
          </Form.Item>
          <Form.Item
            label="客户"
            name="customer"
            initialValue="CQAL"
            rules={[{ required: true, message: '请输入客户信息' }]}
          >
            <Input placeholder="请输入客户信息" />
          </Form.Item>
        </Form>
      </Modal>

      <Card title="导入参数配置" style={{ marginBottom: '24px' }}>
        <Form form={importParamsForm} layout="vertical">
          <Divider orientation="left">基本信息</Divider>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                label="飞机号 (txtACNO)"
                name="txtACNO"
                rules={[{ required: true, message: '请输入飞机号' }]}
              >
                <Input placeholder="请输入飞机号" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="工作指令号 (txtWO)"
                name="txtWO"
                rules={[{ required: true, message: '请输入工作指令号' }]}
              >
                <Input placeholder="请输入工作指令号" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="&nbsp;">
                <Button
                  type="primary"
                  onClick={handleGetACInfo}
                  loading={acInfoLoading}
                  icon={<ReloadOutlined />}
                >
                  获取飞机信息
                </Button>
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={6}>
              <Form.Item
                label="客户 (txtCust)"
                name="txtCust"
                rules={[{ required: true, message: '请输入客户' }]}
              >
                <Input placeholder="请输入客户" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item
                label="维修级别 (txtML)"
                name="txtML"
                rules={[{ required: true, message: '请输入维修级别' }]}
              >
                <Input placeholder="请输入维修级别" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item
                label="机型 (txtACType)"
                name="txtACType"
                initialValue="B737-300"
                rules={[{ required: true, message: '请输入机型' }]}
              >
                <Input placeholder="请输入机型" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item
                label="TSN (格式: TSN:XXXX:XX)"
                name="tsn"
              >
                <Input placeholder="请输入格式化TSN (如 TSN:46564:21)" />
              </Form.Item>
            </Col>
          </Row>

          <Divider orientation="left">飞机信息 (来自请求 - 原始数值)</Divider>
          <Row gutter={16}>
            <Col span={6}>
              <Form.Item label="Fleet (txtFleet)" name="txtFleet">
                <Input placeholder="自动获取" disabled />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="Part No (txtACPartNo)" name="txtACPartNo">
                <Input placeholder="自动获取" disabled />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="Serial No (txtACSerialNo)" name="txtACSerialNo">
                <Input placeholder="自动获取" disabled />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="CSN (格式: CSN:XXXX)" name="csn">
                <Input placeholder="自动生成 (CSN:XXXX)" disabled />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={6}>
              <Form.Item label="TSN Raw (txtTsn)" name="txtTsn">
                <Input placeholder="自动获取 (高精度)" disabled />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="CSN Raw (txtCsn)" name="txtCsn">
                <Input placeholder="自动获取 (纯数字)" disabled />
              </Form.Item>
            </Col>
          </Row>

          <Divider orientation="left">固定参数 (只读)</Divider>
          <Row gutter={16}>
            <Col span={4}>
              <Form.Item label="工艺组 (txtDept)" name="txtDept" initialValue="3_CABIN_TPG">
                <Input disabled />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item label="工卡类型 (selDocType)" name="selDocType" initialValue="NR">
                <Input disabled />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item label="是否腐蚀 (txtCorrosion)" name="txtCorrosion" initialValue="N">
                <Input disabled />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item label="MenuID" name="txtMenuID" initialValue="13541">
                <Input disabled />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item label="ParentID" name="txtParentID" initialValue="13112">
                <Input disabled />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item label="Mode" name="jcMode" initialValue="C">
                <Input disabled />
              </Form.Item>
            </Col>
          </Row>

          <Divider orientation="left">留空参数 (只读)</Divider>
          <Row gutter={16}>
            <Col span={4}>
              <Form.Item label="WorkContent" name="txtWorkContent" initialValue="">
                <Input disabled placeholder="留空" />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item label="RII" name="txtRII" initialValue="">
                <Input disabled placeholder="留空" />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item label="EnginSn" name="txtEnginSn" initialValue="">
                <Input disabled placeholder="留空" />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item label="Flag" name="txtFlag" initialValue="">
                <Input disabled placeholder="留空" />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item label="FlagEu" name="flagEu" initialValue="">
                <Input disabled placeholder="留空" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item>
            <Button type="primary" onClick={() => {
              importParamsForm.validateFields().then(() => {
                message.success('导入参数已保存')
              }).catch(() => {
                message.error('请填写完整的导入参数')
              })
            }}>
              保存导入参数
            </Button>
          </Form.Item>
        </Form>
      </Card>

      <Card
        title="缺陷匹配结果与候选工卡"
        style={{ marginBottom: '24px' }}
        extra={
          <Tag color={matchResults.length > 0 ? 'green' : 'orange'}>
            {matchResults.length > 0 ? `共 ${matchResults.length} 条缺陷` : '暂无匹配结果'}
          </Tag>
        }
      >
        <Table
          columns={matchResultColumns}
          dataSource={matchResults}
          rowKey="defect_record_id"
          rowSelection={rowSelection}
          loading={loadingMatchResults}
          scroll={{ x: 1000 }}
          pagination={{
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条缺陷记录`,
            pageSize: 10,
          }}
        />
        <Divider />
        <Alert
          type="info"
          showIcon
          message="提示"
          description="若需调整候选工卡，请先保存选择；批量操作需勾选左侧复选框并确保候选已保存。"
        />
      </Card>

      <Card title="批量导入设置与执行">
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Form form={importForm} layout="vertical">
            <Form.Item
              label="Cookie（可选）"
              name="cookies"
              tooltip="内网直连模式下，如果系统需要认证Cookie，请在此输入完整的Cookie字符串。如果看到两个JSESSIONID（如：JSESSIONID=xxx; JSESSIONID=yyy），这是正常的，请完整复制所有Cookie值。"
            >
              <Input.TextArea
                placeholder="请输入Cookie字符串（可选），例如：JSESSIONID=ABC123; JSESSIONID=XYZ789; other_cookie=value"
                rows={3}
              />
            </Form.Item>
          </Form>
          <Alert
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
            message="内网直连模式 - Cookie输入说明"
            description={
              <div>
                <p>系统已切换为内网直连模式，不再需要VPN Cookie。</p>
                <p><strong>重要提示：</strong>如果内网系统需要认证，请从浏览器开发者工具中复制完整的Cookie字符串。</p>
                <p>如果看到两个JSESSIONID（如：<code>JSESSIONID=ABC123; JSESSIONID=XYZ789</code>），这是<strong>正常现象</strong>，请完整复制所有Cookie值，系统会自动处理。</p>
              </div>
            }
          />
          <Space wrap>
            <Button onClick={handleTestConnection} loading={testLoading}>
              测试连通性
            </Button>
            <Button onClick={handlePreviewImport} loading={importPreviewLoading}>
              获取候选工卡
            </Button>
            <Button
              onClick={handleBatchImport}
              loading={batchImportLoading}
              disabled={selectedBatchIds.length === 0}
            >
              批量开出工卡
            </Button>
            <Button
              onClick={handleBatchImportSteps}
              loading={batchImportStepsLoading}
              disabled={selectedBatchIds.length === 0}
            >
              批量导入步骤
            </Button>
          </Space>
          {selectedBatchIds.length > 0 && (
            <Tag color="blue" style={{ marginTop: 8 }}>
              已选择 {selectedBatchIds.length} 条缺陷记录
            </Tag>
          )}
          {connectionStatus && (
            <Alert
              style={{ marginTop: 8 }}
              type={connectionStatus.includes('成功') ? 'success' : 'error'}
              message={connectionStatus}
              showIcon
            />
          )}
          {importPreviewLoading && (
            <div style={{ textAlign: 'center', padding: '24px 0' }}>
              <Spin />
              <div style={{ marginTop: 8, color: '#888' }}>正在从企业系统获取工卡数据...</div>
            </div>
          )}
          {importPreviewData && (
            <>
              <Alert
                type={importPreviewData.workcards.length > 0 ? 'success' : 'warning'}
                message={
                  importPreviewData.workcards.length > 0
                    ? `已加载 ${importPreviewData.workcards.length} 条待导入工卡`
                    : '未找到可导入的工卡，请检查参数后重试'
                }
                style={{ marginBottom: 16 }}
                showIcon
              />
              <Space direction="vertical" style={{ width: '100%' }} size="large">
                <div>
                  <div style={{ marginBottom: 6, color: '#666' }}>选择目标工卡（源系统未写方案工卡）</div>
                  <Select
                    value={selectedPreviewWorkcardRid}
                    onChange={(value) => setSelectedPreviewWorkcardRid(value)}
                    style={{ width: '100%' }}
                    placeholder="选择要导入的目标工卡"
                  >
                    {importPreviewData.workcards.map((card) => (
                      <Option key={card.rid} value={card.rid}>
                        工卡 {card.index} - RID: {card.rid}
                      </Option>
                    ))}
                  </Select>
                </div>
                <div>
                  <div style={{ marginBottom: 6, color: '#666' }}>选择历史工卡（作为导入来源）</div>
                  {importPreviewData.history_cards.length > 0 ? (
                    <Select
                      value={selectedPreviewHistoryRid}
                      onChange={(value) => setSelectedPreviewHistoryRid(value)}
                      style={{ width: '100%' }}
                      placeholder="选择历史工卡"
                    >
                      {importPreviewData.history_cards.map((card) => (
                        <Option key={card.rid} value={card.rid}>
                          历史工卡 {card.index} - RID: {card.rid} | 阶段: {card.phase || '-'} | 区域: {card.zone || '-'} | 工种: {card.trade || '-'}
                        </Option>
                      ))}
                    </Select>
                  ) : (
                    <Alert
                      type="warning"
                      showIcon
                      message="未查询到历史工卡，请确认目标工单号与工作组是否正确"
                    />
                  )}
                </div>
              </Space>
            </>
          )}
          {importResult && (
            <Alert
              style={{ marginTop: 16 }}
              type={importResult.success ? 'success' : 'error'}
              message={importResult.message}
              showIcon
            />
          )}
          {importLogs.length > 0 && (
            <>
              <Divider />
              <Title level={5}>执行日志</Title>
              <List
                size="small"
                bordered
                dataSource={importLogs}
                renderItem={(item) => (
                  <List.Item>
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <span>
                        <strong>[{item.step}]</strong> {item.message}
                      </span>
                      {item.detail && <span style={{ color: '#999' }}>{item.detail}</span>}
                    </Space>
                  </List.Item>
                )}
              />
            </>
          )}
          {importArtifacts.length > 0 && (
            <>
              <Divider />
              <Title level={5}>调试文件</Title>
              <List
                size="small"
                dataSource={importArtifacts}
                renderItem={(item) => (
                  <List.Item>
                    <Space>
                      <Tag color="blue">{item.step}</Tag>
                      <span>{item.filename}</span>
                      <Tag color="purple">{item.path}</Tag>
                    </Space>
                  </List.Item>
                )}
              />
            </>
          )}
        </Space>
      </Card>

      {/* 编辑工卡号Modal */}
      <Modal
        title="编辑已开出工卡号"
        open={editingWorkcardNumber !== null}
        onOk={() => {
          if (editingWorkcardNumber) {
            handleUpdateWorkcardNumber(editingWorkcardNumber.defect_record_id, editingWorkcardNumber.value)
          }
        }}
        onCancel={() => setEditingWorkcardNumber(null)}
        okText="保存"
        cancelText="取消"
      >
        <Form layout="vertical">
          <Form.Item label="工卡号">
            <Input
              value={editingWorkcardNumber?.value || ''}
              onChange={(e) => {
                if (editingWorkcardNumber) {
                  setEditingWorkcardNumber({ ...editingWorkcardNumber, value: e.target.value })
                }
              }}
              placeholder="请输入工卡号，如：NR/000000299"
            />
          </Form.Item>
        </Form>
      </Modal>

    </div>
  )
}

export default BulkOpenWorkcards

