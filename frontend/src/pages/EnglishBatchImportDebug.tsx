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
  Switch,
  Row,
  Col,
  Modal,
  Popconfirm,
  Upload
} from 'antd'
import {
  LeftOutlined,
  HomeOutlined,
  ReloadOutlined,
  RightOutlined,
  EditOutlined,
  FileTextOutlined,
  UploadOutlined,
  DeleteOutlined
} from '@ant-design/icons'
import type { UploadProps } from 'antd'
import * as XLSX from 'xlsx'
import type { ColumnsType } from 'antd/es/table'
import { defectApi, CandidateWorkCard } from '../services/defectApi'
import { workcardImportApi, PreviewResponse, RunResponse } from '../services/workcardImportApi'
import { importBatchApi, ImportBatchSummary, ImportBatchDetail } from '../services/importBatchApi'
import { WorkCardGroup } from '../services/workcardApi'

const { Title, Paragraph } = Typography
const { Option } = Select

interface MatchResult {
  defect_record_id: number
  defect_number: string
  description_cn?: string
  description_en?: string
  candidates: CandidateWorkCard[]
  selected_workcard_id?: number
  issued_workcard_number?: string  // 已开出的工卡号
  txtZoneTen?: string
  txtCRN?: string
  refNo?: string
  area?: string // 新增:区域
  candidate_workcard?: string // 新增:候选工卡(来自Excel)
}

interface LocationState {
  defectListId?: number
  defectListInfo?: { id: number; title: string; aircraft_number: string }
  workcardGroup?: WorkCardGroup
  matchResults?: MatchResult[]
  importBatchId?: number
}

const EnglishBatchImportDebug: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const locationState = (location.state as LocationState) || {}

  const [importForm] = Form.useForm()
  const [importParamsForm] = Form.useForm()

  // 核心数据状态
  const [matchResults, setMatchResults] = useState<MatchResult[]>([])
  const [loadingMatchResults, setLoadingMatchResults] = useState(false)
  const [pendingSelections, setPendingSelections] = useState<Record<number, number | undefined>>({})
  const [savingRecordIds, setSavingRecordIds] = useState<number[]>([])
  const [selectedBatchIds, setSelectedBatchIds] = useState<number[]>([])
  const [importingRecordIds, setImportingRecordIds] = useState<number[]>([])

  // 导入/预览状态
  const [importPreviewLoading, setImportPreviewLoading] = useState(false)
  const [importRunLoading, setImportRunLoading] = useState(false)
  const [importPreviewData, setImportPreviewData] = useState<PreviewResponse | null>(null)
  const [selectedPreviewWorkcardRid, setSelectedPreviewWorkcardRid] = useState<string | undefined>()
  const [selectedPreviewHistoryRid, setSelectedPreviewHistoryRid] = useState<string | undefined>()
  const [importLogs, setImportLogs] = useState<any[]>([])
  const [importArtifacts, setImportArtifacts] = useState<any[]>([])
  const [importResult, setImportResult] = useState<RunResponse | null>(null)
  const [testLoading, setTestLoading] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState<string | null>(null)
  const [batchImportLoading, setBatchImportLoading] = useState(false)

  // 批次管理状态
  const [importBatches, setImportBatches] = useState<ImportBatchSummary[]>([])
  const [loadingImportBatches, setLoadingImportBatches] = useState(false)
  const [selectedImportBatchId, setSelectedImportBatchId] = useState<number | undefined>(
    locationState.importBatchId
  )
  const [currentImportBatch, setCurrentImportBatch] = useState<ImportBatchDetail | null>(null)
  const [editingWorkcardNumber, setEditingWorkcardNumber] = useState<{ defect_record_id: number; value: string } | null>(null)
  const [updatingWorkcardNumber, setUpdatingWorkcardNumber] = useState<number[]>([])

  // Save Modal State
  const [saveModalVisible, setSaveModalVisible] = useState(false)
  const [savingBatch, setSavingBatch] = useState(false)
  const [metadataForm] = Form.useForm()


  // 步骤导入状态
  const [batchImportStepsLoading, setBatchImportStepsLoading] = useState(false)
  const [importingStepsRecordIds, setImportingStepsRecordIds] = useState<number[]>([])

  const autoLoadTriggeredRef = useRef(false)

  const readyForMatch = matchResults.length > 0 || selectedImportBatchId !== undefined

  const fetchImportBatches = async () => {
    try {
      setLoadingImportBatches(true)
      const batches = await importBatchApi.list()
      setImportBatches(batches)

      // Auto-select first if nothing selected and no state passed
      if (batches.length > 0 && !selectedImportBatchId && !locationState.importBatchId) {
        // Logic moved to useEffect to avoid side-effects during pure fetch
      }
      return batches
    } catch (error: any) {
      message.error('获取待导入工卡数据表失败: ' + (error?.message || error))
      return []
    } finally {
      setLoadingImportBatches(false)
    }
  }

  // 初始加载批次列表
  useEffect(() => {
    let cancelled = false
    const init = async () => {
      const batches = await fetchImportBatches()
      if (cancelled) return

      if (batches.length > 0) {
        const targetId = selectedImportBatchId ?? batches[0].id
        setSelectedImportBatchId(targetId)
        loadImportBatch(targetId)
      }
    }

    init()
    return () => {
      cancelled = true
    }
  }, [])

  const loadImportBatch = async (batchId: number) => {
    try {
      setLoadingMatchResults(true)
      const detail = await importBatchApi.getById(batchId)
      setCurrentImportBatch(detail)
      setSelectedImportBatchId(batchId)
      autoLoadTriggeredRef.current = true

      // 填充表单默认值
      importParamsForm.setFieldsValue({
        txtACNO: detail.aircraft_number || '',
        txtWO: detail.workcard_number || '',
        txtCust: detail.customer || "EK",
        txtML: detail.maintenance_level || "6C+6000D",
        txtACType: detail.aircraft_type || "B777-300",
        txtZoneName: "%BB%FA%C9%CF",
        txtRII: "N",
        txtCJC: "",
        txtRemark: "",
        txtDept: "3_CABIN_TPG",
        // txtStation removed (duplicate)
        txtFleet: detail.aircraft_type?.includes('777') ? "777" : "330", // Simple inference
        selDocType: "NR",
        txtMenuID: "15196",
        txtParentID: "13112"
      })

      const formatted: MatchResult[] = detail.items.map((item, index) => {
        const candidateId =
          item.selected_workcard_id ??
          (item.defect_record_id ? item.defect_record_id : index + 1)

        const itemAny = item as any

        // Debug logging - 只在第一行输出
        if (index === 0) {
          console.log('从数据库加载的第一条item数据:', item)
          console.log('item中的字段:', {
            workcard_number: item.workcard_number,
            zone_number: itemAny.zone_number,
            reference_workcard_number: itemAny.reference_workcard_number,
            reference_workcard_item: itemAny.reference_workcard_item,
            area: itemAny.area,
            issued_workcard_number: itemAny.issued_workcard_number
          })
        }

        return {
          defect_record_id: item.defect_record_id ?? -(index + 1),
          defect_number: item.defect_number,
          description_cn: item.description_cn || '',
          description_en: item.description_en || '',
          candidates: [
            {
              id: candidateId,
              workcard_number: item.workcard_number,
              description: item.description_cn || '',
              similarity_score: item.similarity_score ?? 0
            }
          ],
          selected_workcard_id: candidateId,
          issued_workcard_number: itemAny.issued_workcard_number || 'NR/000',
          txtZoneTen: itemAny.zone_number || itemAny.txtZoneTen || '',
          txtCRN: itemAny.reference_workcard_number || itemAny.txtCRN || '',
          refNo: itemAny.reference_workcard_item || itemAny.refNo || '',
          area: itemAny.area || '',
          candidate_workcard: item.workcard_number || '' // Use workcard_number as candidate
        }
      })

      console.log('加载的batch数据,第一条formatted:', formatted[0])

      setMatchResults(formatted)
      setPendingSelections({})
      setSelectedBatchIds([])
      resetImportState()
    } catch (error: any) {
      message.error('加载待导入工卡数据失败: ' + (error?.message || error))
    } finally {
      setLoadingMatchResults(false)
    }
  }

  // 同步选中状态
  useEffect(() => {
    setSelectedBatchIds((prev) =>
      prev.filter((id) => matchResults.some((item) => item.defect_record_id === id))
    )
  }, [matchResults])

  const composeCookies = (values: any) => {
    return (values.cookies || '').trim()
  }

  const getImportParams = () => ({
    tail_no: '',
    src_work_order: '',
    target_work_order: '',
    work_group: ''
  })

  const resetImportState = () => {
    setImportPreviewData(null)
    setImportLogs([])
    setImportArtifacts([])
    setSelectedPreviewWorkcardRid(undefined)
    setSelectedPreviewHistoryRid(undefined)
    setImportResult(null)
    setConnectionStatus(null)
    setImportingRecordIds([])
    setBatchImportLoading(false)
  }

  const handleTestConnection = async () => {
    try {
      const values = await importForm.validateFields(['cookies'])
      const baseParams = getImportParams() // 测试连接可能只需要cookies
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
      message.error('连接测试失败: ' + (error?.message || error))
    } finally {
      setTestLoading(false)
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
        setCurrentImportBatch(null)
      }
    } catch (error: any) {
      message.error('删除失败: ' + (error?.message || error))
    }
  }

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
          // 尝试映射字段,支持多种常见列名
          const defectNumber = row['缺陷编号'] || row['Defect Number'] || row['Defect'] || `IMP-${index + 1}`
          const descCn = row['工卡描述中文'] || row['Description (CN)'] || row['Description'] || ''
          const descEn = row['工卡描述英文'] || row['Description (EN)'] || ''

          // English specifics
          const zoneTen = row['区域号'] || row['Zone'] || row['Zone Number'] || ''
          const crn = row['相关工卡号'] || row['Ref Card'] || row['CRN'] || row['Reference Card'] || ''
          const refNo = row['相关工卡序号'] || row['Item No'] || row['Ref No'] || row['Reference Item'] || ''
          const area = row['区域'] || row['Area'] || row['Zone Name'] || ''

          // 候选工卡 (Simulate single candidate if provided)
          const candidateCard = row['候选工卡'] || row['Candidate'] || row['Workcard'] || row['候选工卡号'] || ''
          const candidates: CandidateWorkCard[] = []
          let selectedWorkcardId: number | undefined = undefined

          if (candidateCard) {
            // Mock a candidate
            const mockId = 999000 + index // Temporary ID
            candidates.push({
              id: mockId,
              workcard_number: candidateCard,
              title: candidateCard,
              exclude_reason: null,
              similarity_score: 100,
              source: 'import',
              description: descCn
            } as any)
            selectedWorkcardId = mockId
          }

          const issued = row['已开工卡号'] || row['Issued Card'] || ''

          // Debug logging - 只在第一行输出,避免刷屏
          if (index === 0) {
            console.log('Excel列名:', Object.keys(row))
            console.log('解析结果示例:', {
              defectNumber,
              descCn,
              descEn,
              zoneTen,
              crn,
              refNo,
              area,
              candidateCard,
              issued
            })
          }

          return {
            defect_record_id: -(index + 1), // Negative ID to indicate new/unsaved
            defect_number: defectNumber,
            description_cn: descCn,
            description_en: descEn,
            txtZoneTen: zoneTen,
            txtCRN: crn,
            refNo: refNo,
            area: area,
            candidate_workcard: candidateCard, // Store the Excel value directly
            candidates: candidates,
            selected_workcard_id: selectedWorkcardId,
            issued_workcard_number: issued,
          }
        })

        console.log('导入的matchResults数量:', newMatchResults.length)
        console.log('第一条数据:', newMatchResults[0])

        setMatchResults(newMatchResults)
        setSelectedImportBatchId(undefined) // 清除选中的数据库批次
        setPendingSelections({})
        setSelectedBatchIds([])

        // 尝试从文件名提取飞机号等信息
        const fileName = (file as File).name
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

  const handleOpenSaveModal = () => {
    if (matchResults.length === 0) {
      message.warning('没有可保存的数据')
      return
    }
    // 尝试填充默认值
    if (currentImportBatch) {
      metadataForm.setFieldsValue({
        aircraft_number: currentImportBatch.aircraft_number,
        workcard_number: currentImportBatch.workcard_number,
        maintenance_level: currentImportBatch.maintenance_level,
        aircraft_type: currentImportBatch.aircraft_type,
        customer: currentImportBatch.customer
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
        // Ensure data integrity for direct import
        if (!selectedCandidate && result.candidates.length > 0) {
          selectedCandidate = result.candidates[0]
        }


        // Use the candidate_workcard field (from Excel "候选工卡" column)
        // Don't fallback to txtCRN as they are different fields
        const workcardNumber = result.candidate_workcard || ''

        return {
          defect_record_id: result.defect_record_id > 0 ? result.defect_record_id : null,
          defect_number: result.defect_number,
          description_cn: result.description_cn,
          description_en: result.description_en,
          workcard_number: String(workcardNumber),
          issued_workcard_number: result.issued_workcard_number,
          selected_workcard_id: selectedCandidate?.id && selectedCandidate.id > 0 ? selectedCandidate.id : null,
          similarity_score: selectedCandidate?.similarity_score ?? 0,
          // Save new fields
          reference_workcard_number: result.txtCRN,
          reference_workcard_item: result.refNo,
          area: result.area,
          zone_number: result.txtZoneTen
        }
      })

      console.log('准备保存的第一条item数据:', items[0])
      console.log('保存payload包含的新字段:', {
        reference_workcard_number: items[0].reference_workcard_number,
        reference_workcard_item: items[0].reference_workcard_item,
        area: items[0].area,
        zone_number: items[0].zone_number
      })

      setSavingBatch(true)
      const payload = {
        metadata: {
          aircraft_number: values.aircraft_number,
          workcard_number: values.workcard_number,
          maintenance_level: values.maintenance_level,
          aircraft_type: values.aircraft_type,
          customer: values.customer,
          defect_list_id: locationState.defectListId
        },
        items
      }

      console.log('Batch Import Payload:', JSON.stringify(payload, null, 2))

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
        errorMsg = JSON.stringify(error)
      }
      message.error(`保存失败: ${errorMsg}`)
    } finally {
      setSavingBatch(false)
    }
  }

  const handleUpdateWorkcardNumber = async (defect_record_id: number, workcard_number: string) => {
    try {
      setUpdatingWorkcardNumber((prev) => [...prev, defect_record_id])
      await defectApi.updateIssuedWorkcardNumber(defect_record_id, workcard_number)

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

  // 构建英文工卡请求参数
  const buildEnglishImportParams = (importParams: any, record: MatchResult) => {
    return {
      txtCust: importParams.txtCust,
      txtACNO: importParams.txtACNO,
      txtWO: importParams.txtWO,
      txtML: importParams.txtML,
      txtACType: importParams.txtACType,
      // txtACType removed (duplicate)
      txtZoneName: record.area || importParams.txtZoneName || "", // Use record.area if available
      txtZoneTen: record.txtZoneTen || importParams.txtZoneTen || "",
      txtRII: importParams.txtRII,
      txtCJC: importParams.txtCJC,
      txtCRN: record.txtCRN || importParams.txtCRN || "",
      refNo: record.refNo || importParams.refNo || "",
      txtRemark: importParams.txtRemark,
      txtDescEng: record.description_en || record.description_cn || '',
      txtDept1: importParams.txtDept1,
      selDocType: importParams.selDocType,
      txtMenuID: importParams.txtMenuID,
      txtParentID: importParams.txtParentID,
      txtFleet: importParams.txtFleet,
      txtACPartNo: importParams.txtACPartNo,
      txtACSerialNo: importParams.txtACSerialNo,
      txtStation: importParams.txtStation,
      txtDept: importParams.txtDept,
    }
  }

  const handleImportSingle = async (record: MatchResult) => {
    if (!record.selected_workcard_id) {
      message.warning(`请先保存缺陷 ${record.defect_number} 的候选工卡`)
      return
    }
    try {
      const cookieValues = await importForm.validateFields(['cookies'])
      const importParams = await importParamsForm.validateFields()

      Modal.confirm({
        title: '确认开出英文工卡',
        content: `确定要为缺陷 ${record.defect_number} 开出英文工卡吗？`,
        okText: '确认开出',
        cancelText: '取消',
        onOk: async () => {
          try {
            setImportingRecordIds((prev) => [...prev, record.defect_record_id])

            const params = buildEnglishImportParams(importParams, record)

            const response = await workcardImportApi.importEnglishDefect({
              defect_record_id: record.defect_record_id,
              params,
              cookies: composeCookies(cookieValues),
              is_test_mode: false
            })

            setImportLogs(response.logs)
            setImportArtifacts(response.artifacts)

            if (response.success) {
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
            message.error(`开出工卡失败: ${error?.message || error}`)
          } finally {
            setImportingRecordIds((prev) => prev.filter((id) => id !== record.defect_record_id))
          }
        }
      })
    } catch (error: any) {
      // 表单验证失败
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

      Modal.confirm({
        title: '确认批量开出英文工卡',
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
              if (!record.selected_workcard_id) {
                failureMessages.push(`缺陷 ${record.defect_number} 未保存候选工卡`)
                continue
              }
              try {
                const params = buildEnglishImportParams(importParams, record)

                const response = await workcardImportApi.importEnglishDefect({
                  defect_record_id: record.defect_record_id,
                  params,
                  cookies,
                  is_test_mode: false
                })

                setImportLogs(response.logs)
                setImportArtifacts(response.artifacts)

                if (response.success) {
                  successCount += 1
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
            message.error('批量开出工卡失败: ' + (error?.message || error))
          } finally {
            setBatchImportLoading(false)
            setSelectedBatchIds([])
          }
        }
      })
    } catch (error: any) {
      // 表单验证失败
    }
  }

  // 沿用旧的步骤导入逻辑（假设通用）
  const handleImportStepsSingle = async (record: MatchResult) => {
    if (!record.issued_workcard_number || record.issued_workcard_number === 'NR/000' || !record.selected_workcard_id) {
      message.warning(`缺陷 ${record.defect_number} 需要已开出工卡号且已保存候选工卡`)
      return
    }

    try {
      const cookieValues = await importForm.validateFields(['cookies'])
      const importParams = await importParamsForm.validateFields()
      const cookies = composeCookies(cookieValues)

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
          target_work_order: candidateWorkOrder,
          source_work_order: importParams.txtWO || '',
          tail_no: importParams.txtACNO || '',
          work_group: importParams.txtDept || '3_CABIN_TPG',
          cookies,
        })

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
      // Validation error
    }
  }

  const handleBatchImportSteps = async () => {
    if (selectedBatchIds.length === 0) {
      message.warning('请先勾选需要批量导入步骤的缺陷记录')
      return
    }

    const validRecords = matchResults.filter(
      (item) =>
        selectedBatchIds.includes(item.defect_record_id) &&
        item.issued_workcard_number &&
        item.issued_workcard_number !== 'NR/000' &&
        item.selected_workcard_id
    )

    if (validRecords.length === 0) {
      message.warning('选中的记录中没有符合条件的记录（需要已开出工卡号且已保存候选工卡）')
      return
    }

    if (validRecords.length < selectedBatchIds.length) {
      message.warning(`选中的 ${selectedBatchIds.length} 条记录中，只有 ${validRecords.length} 条符合条件`)
    }

    try {
      const cookieValues = await importForm.validateFields(['cookies'])
      const importParams = await importParamsForm.validateFields()
      const cookies = composeCookies(cookieValues)

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

            for (const record of validRecords) {
              try {
                const selectedCandidate = record.candidates.find(
                  (candidate) => candidate.id === record.selected_workcard_id
                )
                const candidateWorkOrder = selectedCandidate?.workcard_number || ''

                if (!candidateWorkOrder) {
                  failureMessages.push(`缺陷 ${record.defect_number}: 未找到候选工卡的工卡指令号`)
                  continue
                }

                const response = await workcardImportApi.importSteps({
                  jobcard_number: record.issued_workcard_number || '',
                  target_work_order: candidateWorkOrder,
                  source_work_order: importParams.txtWO || '',
                  tail_no: importParams.txtACNO || '',
                  work_group: importParams.txtDept || '3_CABIN_TPG',
                  cookies,
                })

                if (response.logs) {
                  setImportLogs((prev) => [...prev, ...response.logs])
                }
                if (response.artifacts) {
                  setImportArtifacts((prev) => [...prev, ...response.artifacts])
                }

                if (response.success) {
                  successCount += 1
                  totalImportedSteps += response.imported_count || 0
                } else {
                  failureMessages.push(`缺陷 ${record.defect_number}: ${response.message || '导入失败'}`)
                }
              } catch (error: any) {
                failureMessages.push(`缺陷 ${record.defect_number}: ${error?.message || error}`)
              }
            }

            if (successCount > 0) {
              message.success(`批量导入步骤完成，成功 ${successCount} 条，共导入 ${totalImportedSteps} 个步骤`)
            }
            if (failureMessages.length > 0) {
              message.error(failureMessages.join('；'))
            }
          } catch (error: any) {
            message.error('批量导入步骤失败: ' + (error?.message || error))
          } finally {
            setBatchImportStepsLoading(false)
          }
        }
      })
    } catch (error: any) {
      // Form validation
    }
  }

  // 列表定义
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
      title: '工卡描述（英文）',
      dataIndex: 'description_en',
      key: 'description_en',
      width: 300,
      ellipsis: true,
      render: (text: string) => text || '-'
    },
    {
      title: '区域',
      dataIndex: 'area',
      key: 'area',
      width: 100,
      render: (text: string) => text || '-'
    },
    {
      title: '区域号',
      dataIndex: 'txtZoneTen',
      key: 'txtZoneTen',
      width: 100,
      render: (text: string) => text || '-'
    },
    {
      title: '相关工卡号',
      dataIndex: 'txtCRN',
      key: 'txtCRN',
      width: 150,
      ellipsis: true,
      render: (text: string) => text || '-'
    },
    {
      title: '相关工卡序号',
      dataIndex: 'refNo',
      key: 'refNo',
      width: 120,
      render: (text: string) => text || '-'
    },
    {
      title: '候选工卡',
      dataIndex: 'candidate_workcard',
      key: 'candidate_workcard',
      width: 200,
      ellipsis: true,
      render: (text: string) => text || '-'
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
    return (
      <div style={{ padding: '24px', background: '#f0f2f5', minHeight: '100vh' }}>
        <Result
          status="info"
          title="请选择待导入工卡数据表"
          subTitle="请在上方选择一个已保存的批次。"
          extra={[
            <Select
              style={{ width: 300, marginBottom: 16 }}
              placeholder="请选择待导入工卡数据表"
              onChange={(value) => handleImportBatchChange(Number(value))}
              loading={loadingImportBatches}
            >
              {importBatches.map((batch) => (
                <Option key={batch.id} value={batch.id}>
                  {`批次 #${batch.id} / 飞机号 ${batch.aircraft_number} / 工卡 ${batch.workcard_number}`}
                </Option>
              ))}
            </Select>,
            <br />,
            <Button key="back" icon={<LeftOutlined />} onClick={handleBack}>
              返回缺陷处理
            </Button>,
            <Button key="home" type="primary" icon={<HomeOutlined />} onClick={handleGoHome}>
              返回首页
            </Button>
          ]}
        />
      </div>
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
            }
          }}
          loading={loadingMatchResults}
        >
          刷新数据
        </Button>
      </div>

      <Card style={{ marginBottom: '24px' }}>
        <Title level={3} style={{ marginBottom: '16px' }}>
          英文工卡批量导入调试
        </Title>
        <Paragraph type="secondary" style={{ marginBottom: '16px' }}>
          此页面用于连接公司网络环境并执行英文工卡批量开卡操作。
        </Paragraph>
        <div style={{ marginBottom: '16px' }}>
          <Space>
            <span style={{ color: '#666' }}>选择待导入数据表：</span>
            <Select
              style={{ minWidth: 320 }}
              value={selectedImportBatchId}
              onChange={(value) => handleImportBatchChange(Number(value))}
              placeholder="请选择待导入工卡数据表"
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

      <Card title="导入参数配置 (English Workcard Params)" style={{ marginBottom: '24px' }}>
        <Form form={importParamsForm} layout="vertical">
          <Row gutter={16}>
            <Col span={6}>
              <Form.Item label="客户 (txtCust)" name="txtCust" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="飞机号 (txtACNO)" name="txtACNO" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="工作指令号 (txtWO)" name="txtWO" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="维修级别 (txtML)" name="txtML">
                <Input />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={6}>
              <Form.Item label="机型 (txtACType)" name="txtACType">
                <Input />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="开卡工艺组 (txtDept)" name="txtDept">
                <Input />
              </Form.Item>
            </Col>
          </Row>

          <Divider orientation="left" style={{ margin: '12px 0' }}>其他参数 (可折叠或保持默认)</Divider>

          <Row gutter={16}>
            <Col span={6}>
              <Form.Item label="Zone Name (txtZoneName)" name="txtZoneName">
                <Input />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="RII (txtRII)" name="txtRII">
                <Input />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="CJC (txtCJC)" name="txtCJC">
                <Input />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="备注 (txtRemark)" name="txtRemark">
                <Input />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={4}>
              <Form.Item label="Dept1" name="txtDept1"><Input /></Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item label="DocType" name="selDocType"><Input /></Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item label="MenuID" name="txtMenuID"><Input /></Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item label="ParentID" name="txtParentID"><Input /></Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item label="Station" name="txtStation"><Input /></Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item label="Fleet" name="txtFleet"><Input /></Form.Item>
            </Col>
          </Row>
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
          scroll={{ x: 1200 }}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条缺陷记录`
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

      <Card title="执行与日志">
        <Form form={importForm} layout="vertical">
          <Form.Item
            label="Cookie（可选）"
            name="cookies"
            tooltip="内网直连模式下，如果系统需要认证Cookie，请在此输入。"
          >
            <Input.TextArea rows={2} placeholder="JSESSIONID=..." />
          </Form.Item>
        </Form>

        <Space wrap style={{ marginBottom: 16 }}>
          <Button onClick={handleTestConnection} loading={testLoading}>
            测试连通性
          </Button>
          <Button
            type="primary"
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

        {connectionStatus && (
          <Alert
            style={{ marginBottom: 16 }}
            type={connectionStatus.includes('成功') ? 'success' : 'error'}
            message={connectionStatus}
            showIcon
          />
        )}

        {importLogs.length > 0 && (
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
                  {item.detail && <span style={{ color: '#999', fontSize: 12 }}>{item.detail}</span>}
                </Space>
              </List.Item>
            )}
          />
        )}
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
            initialValue="B777-300"
            rules={[{ required: true, message: '请输入机型' }]}
          >
            <Input placeholder="请输入机型" />
          </Form.Item>
          <Form.Item
            label="客户"
            name="customer"
            initialValue="EK"
            rules={[{ required: true, message: '请输入客户信息' }]}
          >
            <Input placeholder="请输入客户信息" />
          </Form.Item>
        </Form>
      </Modal>

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

export default EnglishBatchImportDebug