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
  Row,
  Col,
  Modal,
  Popconfirm,
  Upload,
  Select,
  Divider,
  List,
  Checkbox,
  // Pagination,
  Layout,
  Menu,
  Statistic,
  Drawer,
  Descriptions,
  Tabs
} from 'antd'
import {
  ReloadOutlined,
  HomeOutlined,
  EditOutlined,
  UploadOutlined,
  DeleteOutlined,
  DownloadOutlined,
  AppstoreOutlined,
  BugOutlined,
  DatabaseOutlined,
  CloudUploadOutlined,
  EyeOutlined,
  PlusOutlined,
  SaveOutlined,
  CloseOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined
} from '@ant-design/icons'
import { 
  listIndexes,
  uploadIndex,
  getIndex,
  deleteIndex,
  processDefects,
  downloadBlob,
  createIndexItem,
  updateIndexItem,
  deleteIndexItem,
  type IndexInfo,
  type IndexItem,
  type ProcessStats,
  type IndexItemCreate
} from '../services/defectListApi'

const { Sider, Content } = Layout
import type { UploadProps, UploadFile, RcFile } from 'antd/es/upload/interface'
import * as XLSX from 'xlsx'
import type { ColumnsType } from 'antd/es/table'
import { defectApi, CandidateWorkCard } from '../services/defectApi'
import { workcardImportApi } from '../services/workcardImportApi'
import { importBatchApi, ImportBatchSummary, ImportBatchDetail } from '../services/importBatchApi'
import { WorkCardGroup } from '../services/workcardApi'
import { formatWorkcardNumberToShort } from '../utils/errorHandler'

const { Title, Text } = Typography
const { Option } = Select

interface SchemeStep {
  step_number: number
  content_cn: string
  content_en: string
  man_hours: string
  manpower: string
  trade?: string
  materials: {
    part_number: string
    quantity: number
  }[]
}

interface MatchResult {
  defect_record_id: number
  defect_number: string
  description_cn?: string
  description_en?: string
  candidates: (CandidateWorkCard & { workcard_number: string })[]
  selected_workcard_id?: number
  issued_workcard_number?: string  // 已开出的工卡号
  txtZoneTen?: string
  txtCRN?: string
  refNo?: string
  area?: string // 新增:区域
  candidate_workcard?: string // 新增:候选工卡(来自Excel)
  candidate_description_en?: string // 新增:历史工卡描述（英文），来自Excel的 Candidate Workcard Description (English) 列
  ref_manual?: string // 参考手册 (CMM_REFER)
  steps?: SchemeStep[] // 方案步骤
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

  const [importParamsForm] = Form.useForm()

  // 核心数据状态
  const [matchResults, setMatchResults] = useState<MatchResult[]>([])
  const [loadingMatchResults, setLoadingMatchResults] = useState(false)
  const [pendingSelections, setPendingSelections] = useState<Record<number, number | undefined>>({})
  
  const [selectedBatchIds, setSelectedBatchIds] = useState<number[]>([])
  const [importingRecordIds, setImportingRecordIds] = useState<number[]>([])

  // 导入/预览状态
  const [importLogs, setImportLogs] = useState<any[]>([])
  const setImportArtifacts = useState<any[]>([])[1]
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
  const setUpdatingWorkcardNumber = useState<number[]>([])[1]

  // Save Modal State
  const [saveModalVisible, setSaveModalVisible] = useState(false)
  const [savingBatch, setSavingBatch] = useState(false)
  const [metadataForm] = Form.useForm()

  // Detail Drawer State
  const [detailDrawerOpen, setDetailDrawerOpen] = useState(false)
  const [activeDetailItem, setActiveDetailItem] = useState<MatchResult | null>(null)
  const [drawerWidth, setDrawerWidth] = useState(600)
  const isResizingRef = useRef(false)

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizingRef.current) return
      const newWidth = document.body.clientWidth - e.clientX
      // Limit width between 300px and 90% of screen width
      const maxWidth = document.body.clientWidth * 0.9
      if (newWidth > 300 && newWidth < maxWidth) {
        setDrawerWidth(newWidth)
      }
    }

    const handleMouseUp = () => {
      isResizingRef.current = false
      document.body.style.cursor = 'default'
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)


  return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [])


  // 步骤导入状态
  const [batchImportStepsLoading, setBatchImportStepsLoading] = useState(false)
  const [importingStepsRecordIds, setImportingStepsRecordIds] = useState<number[]>([])

  // Sidebar State
  const [collapsed, setCollapsed] = useState(false)
  const [selectedKey, setSelectedKey] = useState('1')

  // ==================== 缺陷列表处理 & 索引表管理 State ====================
  const [indexUploadForm] = Form.useForm()
  
  // 索引表列表状态
  const [indexList, setIndexList] = useState<IndexInfo[]>([])
  const [listLoading, setListLoading] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState<IndexInfo | null>(null)

  // 索引表详情状态
  const [indexItems, setIndexItems] = useState<IndexItem[]>([])
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailModalOpen, setDetailModalOpen] = useState(false)
  const [currentIndexId, setCurrentIndexId] = useState<number | null>(null)

  // 编辑状态
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editItemForm] = Form.useForm()
  const [addingNew, setAddingNew] = useState(false)
  const [newItemForm] = Form.useForm()

  // 上传状态
  const [indexFile, setIndexFile] = useState<UploadFile | null>(null)
  const [uploadingIndex, setUploadingIndex] = useState(false)

  // 缺陷表状态
  const [defectFile, setDefectFile] = useState<UploadFile | null>(null)
  const [processingDefect, setProcessingDefect] = useState(false)
  const [processStats, setProcessStats] = useState<ProcessStats | null>(null)
  
  // Global Cookie State (Persisted)
  const [globalCookie, setGlobalCookie] = useState<string>(() => {
    return localStorage.getItem('ajc_global_cookie') || ''
  })

  // Persist cookie changes
  useEffect(() => {
    localStorage.setItem('ajc_global_cookie', globalCookie)
  }, [globalCookie])

  const autoLoadTriggeredRef = useRef(false)

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
        txtRII: "",
        txtCJC: "",
        txtRemark: "",
        txtDept: "3_CABIN_TPG",
        txtStation: "CAN",
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

        // 辅助函数：确保值转换为字符串
        const ensureString = (value: any): string => {
          if (value === null || value === undefined) return ''
          return String(value)
        }

        return {
          defect_record_id: item.defect_record_id ?? -(index + 1),
          defect_number: item.defect_number,
          description_cn: item.description_cn || '',
          description_en: item.description_en || '',
          candidates: [
            {
              id: candidateId,
              workcard_number: item.workcard_number || '',
              description: item.description_cn || '',
              similarity_score: item.similarity_score ?? 0
            }
          ],
          selected_workcard_id: candidateId,
          issued_workcard_number: formatWorkcardNumberToShort(itemAny.issued_workcard_number) || '',
          txtZoneTen: ensureString(itemAny.zone_number || itemAny.txtZoneTen), // 确保转换为字符串
          txtCRN: ensureString(itemAny.reference_workcard_number || itemAny.txtCRN),
          refNo: ensureString(itemAny.reference_workcard_item || itemAny.refNo), // 确保转换为字符串
          area: ensureString(itemAny.area),
          candidate_workcard: item.workcard_number || '', // Use workcard_number as candidate
          candidate_description_en: itemAny.candidate_description_en || '', // 历史工卡描述（英文）
          ref_manual: ensureString(itemAny.ref_manual) // 参考手册 (CMM_REFER)
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

  const getImportParams = () => ({
    tail_no: '',
    src_work_order: '',
    target_work_order: '',
    work_group: ''
  })

  const resetImportState = () => {
    setImportLogs([])
    setConnectionStatus(null)
    setImportingRecordIds([])
    setBatchImportLoading(false)
  }

  const handleTestConnection = async () => {
    try {
      const baseParams = getImportParams() // 测试连接可能只需要cookies
      setTestLoading(true)
      setConnectionStatus(null)
      setImportLogs([])
      const response = await workcardImportApi.testConnection({
        ...baseParams,
        cookies: globalCookie.trim()
      })
      setImportLogs(response.logs)
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


        const newItemsFromExcel: MatchResult[] = jsonData.map((row, index) => {
          // 尝试映射字段,支持多种常见列名
          const defectNumber = row['缺陷编号'] || row['Defect Number'] || row['Defect'] || `IMP-${index + 1}`
          const descCn = row['工卡描述中文'] || row['Description (CN)'] || row['Description'] || ''
          const descEn = row['工卡描述英文'] || row['Description (EN)'] || ''

          // English specifics - 确保数字类型转换为字符串
          const zoneTen = row['区域号'] || row['Zone'] || row['Zone Number'] || ''
          const crn = row['相关工卡号'] || row['Ref Card'] || row['CRN'] || row['Reference Card'] || ''
          const refNo = row['相关工卡序号'] || row['Item No'] || row['Ref No'] || row['Reference Item'] || ''
          const area = row['区域'] || row['Area'] || row['Zone Name'] || ''
          
          // 确保数字类型转换为字符串（Excel 可能将数字列解析为数字类型）
          const zoneTenStr = zoneTen !== '' && zoneTen !== null && zoneTen !== undefined ? String(zoneTen) : ''
          const refNoStr = refNo !== '' && refNo !== null && refNo !== undefined ? String(refNo) : ''

          // 候选工卡 (Simulate single candidate if provided)
          const candidateCard = row['候选工卡'] || row['Candidate'] || row['Workcard'] || row['候选工卡号'] || ''
          
          // 历史工卡描述（英文）- 来自智能匹配模块导出的Excel
          const candidateDescEn = row['Candidate Workcard Description (English)'] || row['历史工卡描述'] || ''
          
          // 参考手册 (CMM_REFER)
          const refManual = row['参考手册'] || row['Reference Manual'] || row['REF_MANUAL'] || row['CMM_REFER'] || row['CMM'] || ''
          
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
              issued,
              refManual
            })
          }

          return {
            defect_record_id: -(index + 1), // Placeholder ID, will be updated in setMatchResults
            defect_number: defectNumber,
            description_cn: descCn,
            description_en: descEn,
            txtZoneTen: zoneTenStr, // 使用转换后的字符串
            txtCRN: crn,
            refNo: refNoStr, // 使用转换后的字符串
            area: area,
            candidate_workcard: candidateCard, // Store the Excel value directly
            candidate_description_en: candidateDescEn, // 历史工卡描述（英文）
            ref_manual: refManual, // 参考手册 (CMM_REFER)
            candidates: candidates,
            selected_workcard_id: selectedWorkcardId,
            issued_workcard_number: issued,
          }
        })

        console.log('导入的matchResults数量:', newItemsFromExcel.length)
        console.log('第一条数据:', newItemsFromExcel[0])

        setMatchResults(prev => {
             const minId = prev.length > 0 ? Math.min(0, ...prev.map(i => i.defect_record_id)) : 0
             const adjustedNewItems = newItemsFromExcel.map((item, idx) => ({
                 ...item,
                 defect_record_id: minId - 1 - idx
             }))
             return [...prev, ...adjustedNewItems]
        })
        // setSelectedImportBatchId(undefined) // REMOVED to allow mixing batch and new items
        // setPendingSelections({}) // Keep existing selections
        // setSelectedBatchIds([]) // Keep existing selections

        // 尝试从文件名提取飞机号等信息
        const fileName = (file as File).name
        const acMatch = fileName.match(/B-\d{4}/)
        if (acMatch) {
          importParamsForm.setFieldsValue({ txtACNO: acMatch[0] })
        }

        message.success(`成功导入 ${newItemsFromExcel.length} 条数据`)
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

  // 步骤编辑状态
  const [stepModalOpen, setStepModalOpen] = useState(false)
  const [editingStep, setEditingStep] = useState<SchemeStep | null>(null)
  const [stepForm] = Form.useForm()

  // 步骤增删改查
  const handleAddStep = () => {
    setEditingStep(null)
    stepForm.resetFields()
    // 自动填充序号
    const currentSteps = activeDetailItem?.steps || []
    const nextStepNum = currentSteps.length > 0 
      ? Math.max(...currentSteps.map(s => s.step_number)) + 1 
      : 1
    stepForm.setFieldsValue({
      step_number: nextStepNum,
      man_hours: '1.0',
      manpower: '1',
      trade: 'HM3_CABIN'
    })
    setStepModalOpen(true)
  }

  const handleEditStep = (step: SchemeStep) => {
    setEditingStep(step)
    stepForm.setFieldsValue(step)
    setStepModalOpen(true)
  }

  const handleDeleteStep = (stepNumber: number) => {
    if (!activeDetailItem) return
    
    const newSteps = (activeDetailItem.steps || []).filter(s => s.step_number !== stepNumber)
    // 重新排序
    const reorderedSteps = newSteps.map((s, index) => ({
      ...s,
      step_number: index + 1
    }))
    
    setActiveDetailItem({
      ...activeDetailItem,
      steps: reorderedSteps
    })
    
    // 同步到 matchResults
    setMatchResults(prev => prev.map(r => 
      r.defect_record_id === activeDetailItem.defect_record_id 
        ? { ...r, steps: reorderedSteps } 
        : r
    ))
    
    message.success('删除成功')
  }

  const handleSaveStep = async () => {
    try {
      const values = await stepForm.validateFields()
      if (!activeDetailItem) return

      let newSteps = [...(activeDetailItem.steps || [])]

      if (editingStep) {
        // 编辑模式
        const index = newSteps.findIndex(s => s.step_number === editingStep.step_number)
        if (index > -1) {
          newSteps[index] = { ...editingStep, ...values }
        }
      } else {
        // 新增模式
        newSteps.push({
          ...values,
          materials: [] // 暂不处理新增时的航材
        })
      }

      // 强制重置序号
      newSteps = newSteps.map((s, i) => ({ ...s, step_number: i + 1 }))

      setActiveDetailItem({
        ...activeDetailItem,
        steps: newSteps
      })

      // 同步到 matchResults
      setMatchResults(prev => prev.map(r => 
        r.defect_record_id === activeDetailItem.defect_record_id 
          ? { ...r, steps: newSteps } 
          : r
      ))

      setStepModalOpen(false)
      message.success('保存成功')
    } catch (error) {
      // Form validation error
    }
  }

  const handleOpenDetailDrawer = async (item: MatchResult) => {
    setActiveDetailItem(item)
    setDetailDrawerOpen(true)

    // 如果没有步骤数据，且有英文描述和参考手册，则尝试生成预览
    if ((!item.steps || item.steps.length === 0) && item.description_en && item.ref_manual) {
      try {
        const response = await workcardImportApi.previewSteps({
          description_en: item.description_en,
          ref_manual: item.ref_manual
        })
        
        if (response.success) {
           const newSteps: SchemeStep[] = response.steps.map(s => ({
             step_number: s.step_number,
             content_en: s.content_en,
             content_cn: s.content_cn || '',
             man_hours: s.man_hours,
             manpower: s.manpower,
             trade: s.trade,
             materials: s.materials
           }))
           
           setActiveDetailItem(prev => {
             if (prev && prev.defect_record_id === item.defect_record_id) {
               return { ...prev, steps: newSteps }
             }
             return prev
           })
           
           // Cache the steps in the main list so we don't fetch again
           setMatchResults(prev => prev.map(r => 
             r.defect_record_id === item.defect_record_id 
               ? { ...r, steps: newSteps } 
               : r
           ))
        }
      } catch (error) {
        console.error("Failed to preview steps", error)
      }
    }
  }

  const handleCloseDetailDrawer = () => {
    setDetailDrawerOpen(false)
    setActiveDetailItem(null)
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

        // 辅助函数：将值转换为字符串或 null
        const toStringOrNull = (value: any): string | null => {
          if (value === null || value === undefined || value === '') {
            return null
          }
          return String(value)
        }

        return {
          defect_record_id: result.defect_record_id > 0 ? result.defect_record_id : null,
          defect_number: result.defect_number || '',
          description_cn: result.description_cn || '',
          description_en: result.description_en || '',
          workcard_number: toStringOrNull(workcardNumber),
          issued_workcard_number: toStringOrNull(result.issued_workcard_number),
          selected_workcard_id: selectedCandidate?.id && selectedCandidate.id > 0 ? selectedCandidate.id : null,
          similarity_score: selectedCandidate?.similarity_score ?? null, // 使用 null 而不是 0
          // Save new fields - 确保所有字符串字段都转换为字符串类型
          reference_workcard_number: toStringOrNull(result.txtCRN),
          reference_workcard_item: toStringOrNull(result.refNo),
          area: toStringOrNull(result.area),
          zone_number: toStringOrNull(result.txtZoneTen), // 确保数字转换为字符串
          candidate_description_en: toStringOrNull(result.candidate_description_en), // 历史工卡描述（英文）
          ref_manual: toStringOrNull(result.ref_manual) // 参考手册 (CMM_REFER)
        }
      })

      console.log('准备保存的第一条item数据:', items[0])
      console.log('保存payload包含的新字段:', {
        reference_workcard_number: items[0].reference_workcard_number,
        reference_workcard_item: items[0].reference_workcard_item,
        area: items[0].area,
        zone_number: items[0].zone_number,
        ref_manual: items[0].ref_manual
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
      console.error('Error response:', error.response)
      if (error.errorFields) {
        return // Validation failed
      }
      let errorMsg = error.message || '未知错误'
      
      // 尝试从响应中提取详细错误信息
      if (error.response) {
        // 如果响应中有 data.detail
        if (error.response.data?.detail) {
          const detail = error.response.data.detail
          if (typeof detail === 'string') {
            errorMsg = detail
          } else if (Array.isArray(detail)) {
            // Format Pydantic validation errors
            errorMsg = detail.map((e: any) => {
              const loc = Array.isArray(e.loc) ? e.loc.join('.') : (e.loc || 'unknown')
              const msg = e.msg || JSON.stringify(e)
              return `${loc}: ${msg}`
            }).join('; ')
          } else if (typeof detail === 'object') {
            errorMsg = JSON.stringify(detail, null, 2)
          }
        } else if (error.response.status === 422) {
          // 422 是验证错误，尝试获取更详细的信息
          errorMsg = '数据验证失败，请检查必填字段是否正确填写'
          if (error.response.data) {
            console.error('Validation error details:', error.response.data)
            try {
              const detail = error.response.data.detail
              if (Array.isArray(detail)) {
                errorMsg = detail.map((e: any) => {
                  const loc = Array.isArray(e.loc) ? e.loc.join('.') : (e.loc || 'unknown')
                  const msg = e.msg || JSON.stringify(e)
                  return `${loc}: ${msg}`
                }).join('; ')
              } else if (typeof detail === 'string') {
                errorMsg = detail
              }
            } catch (e) {
              console.error('Failed to parse error details:', e)
            }
          }
        }
      }
      
      // 如果错误消息仍然是默认值，尝试从错误对象中提取
      if (errorMsg === '未知错误' || errorMsg === error.message) {
        if (error.response?.data) {
          errorMsg = JSON.stringify(error.response.data, null, 2)
        } else if (typeof error === 'object' && Object.keys(error).length > 0) {
          errorMsg = JSON.stringify(error, null, 2)
        }
      }
      
      message.error(`保存失败: ${errorMsg}`)
    } finally {
      setSavingBatch(false)
    }
  }

  const handleUpdateWorkcardNumber = async (defect_record_id: number, workcard_number: string) => {
    try {
      setUpdatingWorkcardNumber((prev) => [...prev, defect_record_id])
      
      // 统一转换为短格式存储（如 50324）
      const shortFormat = formatWorkcardNumberToShort(workcard_number)
      
      // 如果 defect_record_id 是负数，说明这是未保存到数据库的记录，只更新本地状态
      if (defect_record_id < 0) {
        setMatchResults((prev) =>
          prev.map((item) =>
            item.defect_record_id === defect_record_id
              ? { ...item, issued_workcard_number: shortFormat }
              : item
          )
        )
        message.success('工卡号更新成功（本地更新，请先保存到数据库）')
        setEditingWorkcardNumber(null)
        return
      }

      // 如果 defect_record_id 是正数，说明这是已保存的记录，调用后端API更新
      await defectApi.updateIssuedWorkcardNumber(defect_record_id, shortFormat)

      setMatchResults((prev) =>
        prev.map((item) =>
          item.defect_record_id === defect_record_id
            ? { ...item, issued_workcard_number: shortFormat }
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


  

  // 构建英文工卡请求参数
  const buildEnglishImportParams = (importParams: any, record: MatchResult) => {
    // txtZoneName 从表格的 area 字段读取
    // 如果 area 是中文"机上"，则转换为 URL 编码 '%BB%FA%C9%CF'
    // 如果已经是 '%BB%FA%C9%CF'，则直接使用
    const REQUIRED_ZONE_NAME = '%BB%FA%C9%CF'
    const areaValue = record.area || importParams.txtZoneName || ""
    let txtZoneName = areaValue
    
    // 如果 area 是中文"机上"，转换为 URL 编码
    if (areaValue === '机上') {
      txtZoneName = REQUIRED_ZONE_NAME
    }
    // 如果已经是 URL 编码，直接使用
    else if (areaValue === REQUIRED_ZONE_NAME) {
      txtZoneName = REQUIRED_ZONE_NAME
    }
    // 其他情况保持原值（后端会验证）
    
    return {
      txtCust: importParams.txtCust,
      txtACNO: importParams.txtACNO,
      txtWO: importParams.txtWO,
      txtML: importParams.txtML,
      txtACType: importParams.txtACType,
      // txtZoneName 来自表格的 area 字段，如果是"机上"则转换为 '%BB%FA%C9%CF'
      txtZoneName: txtZoneName,
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
    
    // 验证 txtZoneName 必须是 '%BB%FA%C9%CF'（机上）或中文"机上"
    const REQUIRED_ZONE_NAME = '%BB%FA%C9%CF'
    const areaValue = record.area || ''
    
    // 允许的值：'%BB%FA%C9%CF'（URL编码）或 '机上'（中文）
    if (areaValue !== REQUIRED_ZONE_NAME && areaValue !== '机上') {
      message.warning(`缺陷 ${record.defect_number} 的区域（area）必须是 '${REQUIRED_ZONE_NAME}'（URL编码）或 '机上'（中文），当前值为: '${areaValue}'，跳过该记录的开卡请求`)
      return
    }
    
    try {
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
              cookies: globalCookie.trim(),
              is_test_mode: false
            })

            setImportLogs(response.logs)

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
      const importParams = await importParamsForm.validateFields()
      const cookies = globalCookie.trim()

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

            // 验证 txtZoneName 必须是 '%BB%FA%C9%CF'（机上）或中文"机上"
            const REQUIRED_ZONE_NAME = '%BB%FA%C9%CF'
            
            for (const recordId of selectedBatchIds) {
              const record = matchResults.find((item) => item.defect_record_id === recordId)
              if (!record) continue
              if (!record.selected_workcard_id) {
                failureMessages.push(`缺陷 ${record.defect_number} 未保存候选工卡`)
                continue
              }
              
              // 验证区域（area）必须是 '%BB%FA%C9%CF'（URL编码）或 '机上'（中文）
              const areaValue = record.area || ''
              if (areaValue !== REQUIRED_ZONE_NAME && areaValue !== '机上') {
                failureMessages.push(`缺陷 ${record.defect_number} 的区域（area）必须是 '${REQUIRED_ZONE_NAME}'（URL编码）或 '机上'（中文），当前值为: '${areaValue}'，跳过该记录的开卡请求`)
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

                setImportLogs((prev) => [...prev, ...response.logs])
                if (response.artifacts) {
                  setImportArtifacts((prev) => [...prev, ...response.artifacts])
                }

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
    if (!record.issued_workcard_number || !record.selected_workcard_id) {
      message.warning(`缺陷 ${record.defect_number} 需要已开出工卡号且已保存候选工卡`)
      return
    }

    try {
      const importParams = await importParamsForm.validateFields()
      const cookies = globalCookie.trim()

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
          ref_manual: record.ref_manual || undefined,  // 参考手册 (CMM_REFER)
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
      const importParams = await importParamsForm.validateFields()
      const cookies = globalCookie.trim()

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
                  ref_manual: record.ref_manual || undefined,  // 参考手册 (CMM_REFER)
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

  // 单条编写方案
  const handleWriteStepsSingle = async (record: MatchResult) => {
    if (!record.issued_workcard_number) {
      message.warning(`缺陷 ${record.defect_number} 需要已开出工卡号`)
      return
    }

    if (!record.ref_manual) {
      message.warning(`缺陷 ${record.defect_number} 需要参考手册 (ref_manual)`)
      return
    }

    try {
      const importParams = await importParamsForm.validateFields()
      const cookies = globalCookie.trim()

      Modal.confirm({
        title: '确认编写方案',
        content: `确定要为缺陷 ${record.defect_number} 编写方案吗？\n工卡号: ${record.issued_workcard_number}\n参考手册: ${record.ref_manual}`,
        okText: '确认编写',
        cancelText: '取消',
        onOk: async () => {
          try {
            // 如果存在自定义步骤，提取步骤内容
            const customSteps = record.steps && record.steps.length > 0
              ? record.steps.map(s => ({
                  content_en: s.content_en,
                  trade: s.trade,
                  manpower: s.manpower,
                  man_hours: s.man_hours
                }))
              : undefined

            const response = await workcardImportApi.writeSteps({
              sale_wo: importParams.txtWO || '',
              ac_no: importParams.txtACNO || '',
              jc_seq: record.issued_workcard_number || '',
              cmm_refer: record.ref_manual || '',
              owner_code: importParams.txtCust || '',
              cookies,
              steps: customSteps,
            })

            if (response.logs) {
              setImportLogs(prev => [...prev, ...response.logs.map((log: string) => ({
                step: 'writeSteps',
                message: log,
                detail: null
              }))])
            }

            if (response.success) {
              message.success(`缺陷 ${record.defect_number} 编写方案成功，共 ${response.steps?.length || 0} 个步骤`)
            } else {
              message.error(`缺陷 ${record.defect_number} 编写方案失败: ${response.message}`)
            }
          } catch (error: any) {
            message.error(`编写方案失败: ${error?.message || error}`)
          }
        }
      })
    } catch (error: any) {
      // Form validation error
    }
  }

  // 批量编写方案
  const handleBatchWriteSteps = async () => {
    if (selectedBatchIds.length === 0) {
      message.warning('请先勾选需要批量编写方案的缺陷记录')
      return
    }

    const validRecords = matchResults.filter(
      (item) =>
        selectedBatchIds.includes(item.defect_record_id) &&
        item.issued_workcard_number &&
        item.ref_manual
    )

    if (validRecords.length === 0) {
      message.warning('选中的记录中没有符合条件的记录（需要已开出工卡号且有参考手册）')
      return
    }

    if (validRecords.length < selectedBatchIds.length) {
      message.warning(`选中的 ${selectedBatchIds.length} 条记录中，只有 ${validRecords.length} 条符合条件`)
    }

    try {
      const importParams = await importParamsForm.validateFields()
      const cookies = globalCookie.trim()

      Modal.confirm({
        title: '确认批量编写方案',
        content: `确定要为选中的 ${validRecords.length} 条缺陷记录批量编写方案吗？`,
        okText: '确认编写',
        cancelText: '取消',
        onOk: async () => {
          try {
            setImportLogs([])
            
            const items = validRecords.map(record => {
              // 如果存在自定义步骤，提取步骤内容
              const customSteps = record.steps && record.steps.length > 0
                ? record.steps.map(s => ({
                    content_en: s.content_en,
                    trade: s.trade,
                    manpower: s.manpower,
                    man_hours: s.man_hours
                  }))
                : undefined

              return {
                sale_wo: importParams.txtWO || '',
                ac_no: importParams.txtACNO || '',
                jc_seq: record.issued_workcard_number || '',
                cmm_refer: record.ref_manual || '',
                owner_code: importParams.txtCust || '',
                cookies,
                steps: customSteps,
              }
            })

            const response = await workcardImportApi.batchWriteSteps({ items })

            // 添加结果日志
            response.results?.forEach((result: any) => {
              setImportLogs(prev => [...prev, {
                step: 'batchWriteSteps',
                message: `工卡 ${result.jc_seq}: ${result.success ? '成功' : '失败'} - ${result.message}`,
                detail: result.steps?.join('; ') || null
              }])
            })

            if (response.success) {
              message.success(`批量编写方案完成，成功 ${response.success_count} 项`)
            } else {
              message.warning(`批量编写方案完成，成功 ${response.success_count} 项，失败 ${response.failed_count} 项`)
            }
          } catch (error: any) {
            message.error('批量编写方案失败: ' + (error?.message || error))
          }
        }
      })
    } catch (error: any) {
      // Form validation error
    }
  }

  // 列表定义
  

  // 全选所有页的处理函数
  const handleSelectAllPages = () => {
    const allIds = matchResults.map(row => row.defect_record_id)
    const allSelected = allIds.every(id => selectedBatchIds.includes(id))
    
    if (allSelected) {
      // 如果全部已选中，则取消全选
      setSelectedBatchIds([])
    } else {
      // 否则选中所有
      setSelectedBatchIds(allIds)
    }
  }

  

  const handleGoHome = () => {
    navigate('/')
  }

  // 加载索引表列表
  const loadIndexList = async () => {
    setListLoading(true)
    try {
      const result = await listIndexes()
      setIndexList(result.data)
      if (result.data.length > 0 && !selectedIndex) {
        setSelectedIndex(result.data[0])
      }
    } catch (error) {
      message.error('加载索引表列表失败')
    } finally {
      setListLoading(false)
    }
  }

  useEffect(() => {
    loadIndexList()
  }, [])

  // 查看索引表详情
  const handleViewDetail = async (record: IndexInfo) => {
    setDetailLoading(true)
    setDetailModalOpen(true)
    setCurrentIndexId(record.id)
    setEditingId(null)
    setAddingNew(false)
    try {
      const result = await getIndex(record.id)
      if (result.success && result.items) {
        setIndexItems(result.items)
      }
    } catch (error) {
      message.error('获取索引表详情失败')
    } finally {
      setDetailLoading(false)
    }
  }

  // 刷新详情
  const refreshDetail = async () => {
    if (!currentIndexId) return
    setDetailLoading(true)
    try {
      const result = await getIndex(currentIndexId)
      if (result.success && result.items) {
        setIndexItems(result.items)
      }
    } catch (error) {
      message.error('刷新失败')
    } finally {
      setDetailLoading(false)
    }
  }

  // 删除索引表
  const handleDeleteIndex = async (id: number) => {
    try {
      await deleteIndex(id)
      message.success('删除成功')
      if (selectedIndex?.id === id) {
        setSelectedIndex(null)
      }
      loadIndexList()
    } catch (error) {
      message.error('删除失败')
    }
  }

  // 上传索引表
  const handleUploadIndex = async (values: { sale_wo: string; ac_no: string; year_month: string }) => {
    if (!indexFile) {
      message.warning('请先选择索引表文件')
      return
    }

    setUploadingIndex(true)
    try {
      const result = await uploadIndex(
        indexFile.originFileObj as File,
        values.sale_wo,
        values.ac_no,
        values.year_month
      )
      if (result.success) {
        message.success(result.message)
        setIndexFile(null)
        indexUploadForm.resetFields()
        loadIndexList()
      }
    } catch (error: any) {
      message.error(error.response?.data?.detail || '上传失败')
    } finally {
      setUploadingIndex(false)
    }
  }

  // 处理缺陷表
  const handleProcessDefect = async () => {
    if (!defectFile) {
      message.warning('请先选择缺陷表文件')
      return
    }

    if (!selectedIndex) {
      message.warning('请先选择一个索引表')
      return
    }

    setProcessingDefect(true)
    setProcessStats(null)

    try {
      const { blob, stats } = await processDefects(selectedIndex.id, defectFile.originFileObj as File, globalCookie.trim())
      setProcessStats(stats)
      const filename = `processed_${defectFile.name}`
      downloadBlob(blob, filename)
      message.success('处理完成，文件已下载')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '处理失败')
    } finally {
      setProcessingDefect(false)
    }
  }

  // 文件选择处理
  const beforeUploadExcel = (file: RcFile) => {
    const isExcel = file.name.endsWith('.xlsx') || file.name.endsWith('.xls')
    if (!isExcel) {
      message.error('请上传 Excel 文件 (.xlsx 或 .xls)')
    }
    return false
  }

  // ==================== 索引项编辑功能 ====================

  // 开始编辑
  const startEdit = (record: IndexItem) => {
    setEditingId(record.id)
    editItemForm.setFieldsValue({
      comp_pn: record.comp_pn || '',
      comp_desc: record.comp_desc || '',
      comp_cmm: record.comp_cmm || '',
      comp_cmm_rev: record.comp_cmm_rev || '',
      remark: record.remark || ''
    })
  }

  // 取消编辑
  const cancelEdit = () => {
    setEditingId(null)
    editItemForm.resetFields()
  }

  // 保存编辑
  const saveEdit = async () => {
    if (!editingId) return
    try {
      const values = await editItemForm.validateFields()
      await updateIndexItem(editingId, values as IndexItemCreate)
      message.success('保存成功')
      setEditingId(null)
      refreshDetail()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '保存失败')
    }
  }

  // 删除索引项
  const handleDeleteItem = async (itemId: number) => {
    try {
      await deleteIndexItem(itemId)
      message.success('删除成功')
      refreshDetail()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '删除失败')
    }
  }

  // 开始添加新项
  const startAddNew = () => {
    setAddingNew(true)
    newItemForm.resetFields()
  }

  // 取消添加
  const cancelAddNew = () => {
    setAddingNew(false)
    newItemForm.resetFields()
  }

  // 保存新项
  const saveNewItem = async () => {
    if (!currentIndexId) return
    try {
      const values = await newItemForm.validateFields()
      await createIndexItem(currentIndexId, values as IndexItemCreate)
      message.success('添加成功')
      setAddingNew(false)
      newItemForm.resetFields()
      refreshDetail()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '添加失败')
    }
  }

  // 导出选定工卡列表
  const handleExportSelectedWorkcards = () => {
    if (selectedBatchIds.length === 0) {
      message.warning('请先选择要导出的记录')
      return
    }

    const selectedRecords = matchResults.filter((record) =>
      selectedBatchIds.includes(record.defect_record_id)
    )

    if (selectedRecords.length === 0) {
      message.warning('没有可导出的记录')
      return
    }

    // 准备导出数据
    const exportData = selectedRecords.map((record) => {
      const selectedCandidate = record.candidates.find(
        (candidate) => candidate.id === record.selected_workcard_id
      )

      return {
        缺陷编号: record.defect_number || '',
        工卡描述中文: record.description_cn || '',
        工卡描述英文: record.description_en || '',
        相关工卡号: record.txtCRN || '',
        相关工卡序号: record.refNo || '',
        区域: record.area || '',
        区域号: record.txtZoneTen || '',
        候选工卡: record.candidate_workcard || selectedCandidate?.workcard_number || '',
        工卡描述: selectedCandidate?.description || '',
        历史工卡描述: record.candidate_description_en || '', // 来自数据库的 candidate_description_en 字段
        已开出工卡号: record.issued_workcard_number || '',
        相似度: selectedCandidate?.similarity_score || 0
      }
    })

    // 创建工作簿
    const ws = XLSX.utils.json_to_sheet(exportData)
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, '选定工卡列表')

    // 导出文件
    const fileName = `选定工卡列表_${new Date().toISOString().slice(0, 10)}.xlsx`
    XLSX.writeFile(wb, fileName)

    message.success(`成功导出 ${selectedRecords.length} 条工卡记录`)
  }

  // 索引表列表列定义
  const indexColumns: ColumnsType<IndexInfo> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true
    },
    {
      title: '销售指令号',
      dataIndex: 'sale_wo',
      key: 'sale_wo',
      width: 140
    },
    {
      title: '飞机号',
      dataIndex: 'ac_no',
      key: 'ac_no',
      width: 100
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewDetail(record)}
          >
            查看
          </Button>
          <Popconfirm
            title="确定删除此索引表？"
            onConfirm={() => handleDeleteIndex(record.id)}
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      )
    }
  ]

  // 可编辑单元格渲染
  const renderEditableCell = (
    text: string | null,
    record: IndexItem,
    dataIndex: string
  ) => {
    if (editingId === record.id) {
      return (
        <Form.Item name={dataIndex} style={{ margin: 0 }}>
          <Input size="small" />
        </Form.Item>
      )
    }
    return text || '-'
  }

  // 索引项列定义（可编辑）
  const itemColumns: ColumnsType<IndexItem> = [
    {
      title: 'COMPONENT P/N',
      dataIndex: 'comp_pn',
      key: 'comp_pn',
      width: 150,
      render: (text, record) => renderEditableCell(text, record, 'comp_pn')
    },
    {
      title: 'COMPONENT DESC',
      dataIndex: 'comp_desc',
      key: 'comp_desc',
      width: 200,
      render: (text, record) => renderEditableCell(text, record, 'comp_desc')
    },
    {
      title: 'COMPONENT MANUAL',
      dataIndex: 'comp_cmm',
      key: 'comp_cmm',
      width: 180,
      render: (text, record) => renderEditableCell(text, record, 'comp_cmm')
    },
    {
      title: 'COMPONENT MANUAL REV',
      dataIndex: 'comp_cmm_rev',
      key: 'comp_cmm_rev',
      width: 150,
      render: (text, record) => renderEditableCell(text, record, 'comp_cmm_rev')
    },
    {
      title: 'REMARK',
      dataIndex: 'remark',
      key: 'remark',
      width: 150,
      render: (text, record) => renderEditableCell(text, record, 'remark')
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      fixed: 'right',
      render: (_, record) => {
        if (editingId === record.id) {
          return (
            <Space size="small">
              <Button type="link" size="small" icon={<SaveOutlined />} onClick={saveEdit}>
                保存
              </Button>
              <Button type="link" size="small" icon={<CloseOutlined />} onClick={cancelEdit}>
                取消
              </Button>
            </Space>
          )
        }
        return (
          <Space size="small">
            <Button
              type="link"
              size="small"
              icon={<EditOutlined />}
              onClick={() => startEdit(record)}
              disabled={editingId !== null}
            >
              编辑
            </Button>
            <Popconfirm title="确定删除？" onConfirm={() => handleDeleteItem(record.id)}>
              <Button type="link" size="small" danger icon={<DeleteOutlined />} disabled={editingId !== null}>
                删除
              </Button>
            </Popconfirm>
          </Space>
        )
      }
    }
  ]

  const renderContent = () => {
    if (selectedKey === '2') {
      return (
        <div style={{ padding: '24px' }}>
          <Row gutter={24}>
            <Col xs={24} lg={16}>
              <Card title="处理缺陷表">
                {!selectedIndex ? (
                  <Alert
                    type="warning"
                    showIcon
                    message="请先在「索引表管理」中选择一个索引表"
                    style={{ marginBottom: 16 }}
                  />
                ) : (
                  <Alert
                    type="info"
                    showIcon
                    message={`使用索引表: ${selectedIndex.name}`}
                    description={`销售指令号: ${selectedIndex.sale_wo}, 飞机号: ${selectedIndex.ac_no}`}
                    style={{ marginBottom: 16 }}
                  />
                )}

                <Form layout="vertical">
                  <Form.Item label="缺陷表文件">
                    <Upload
                      accept=".xlsx,.xls"
                      maxCount={1}
                      beforeUpload={beforeUploadExcel}
                      onChange={(info) => setDefectFile(info.fileList[info.fileList.length - 1] || null)}
                      fileList={defectFile ? [defectFile] : []}
                      disabled={!selectedIndex}
                    >
                      <Button icon={<UploadOutlined />} disabled={!selectedIndex}>
                        选择缺陷表
                      </Button>
                    </Upload>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      需包含 "工卡描述英文" 列
                    </Text>
                  </Form.Item>

                  <Button
                    type="primary"
                    size="large"
                    icon={processingDefect ? undefined : <DownloadOutlined />}
                    onClick={handleProcessDefect}
                    loading={processingDefect}
                    disabled={!selectedIndex || !defectFile}
                    block
                    style={{ marginTop: 16 }}
                  >
                    {processingDefect ? '处理中...' : '处理并下载'}
                  </Button>
                </Form>

                {processStats && (
                  <Card size="small" style={{ marginTop: 24 }}>
                    <Title level={5}>处理结果</Title>
                    <Row gutter={16}>
                      <Col span={6}>
                        <Statistic title="总行数" value={processStats.total} />
                      </Col>
                      <Col span={6}>
                        <Statistic
                          title="匹配成功"
                          value={processStats.matched}
                          valueStyle={{ color: '#3f8600' }}
                        />
                      </Col>
                      <Col span={6}>
                        <Statistic
                          title="API成功"
                          value={processStats.apiSuccess}
                          valueStyle={{ color: '#1890ff' }}
                          prefix={<CheckCircleOutlined />}
                        />
                      </Col>
                      <Col span={6}>
                        <Statistic
                          title="API失败"
                          value={processStats.apiFail}
                          valueStyle={{ color: '#cf1322' }}
                          prefix={<CloseCircleOutlined />}
                        />
                      </Col>
                    </Row>
                  </Card>
                )}
              </Card>
            </Col>
          </Row>
        </div>
      )
    }
    if (selectedKey === '3') {
      return (
        <div style={{ padding: '24px' }}>
          <Row gutter={24}>
            <Col xs={24} lg={14}>
              <Card
                title="已保存的索引表"
                extra={
                  <Button
                    icon={<ReloadOutlined />}
                    onClick={loadIndexList}
                    loading={listLoading}
                  >
                    刷新
                  </Button>
                }
              >
                <Table
                  columns={indexColumns}
                  dataSource={indexList}
                  rowKey="id"
                  loading={listLoading}
                  size="small"
                  pagination={{ pageSize: 10 }}
                  rowSelection={{
                    type: 'radio',
                    selectedRowKeys: selectedIndex ? [selectedIndex.id] : [],
                    onChange: (_, rows) => setSelectedIndex(rows[0] || null)
                  }}
                  onRow={(record) => ({
                    onClick: () => setSelectedIndex(record)
                  })}
                />
                {selectedIndex && (
                  <Alert
                    type="success"
                    showIcon
                    message={`当前选中: ${selectedIndex.name}`}
                    description={`销售指令号: ${selectedIndex.sale_wo}, 飞机号: ${selectedIndex.ac_no}`}
                    style={{ marginTop: 16 }}
                  />
                )}
              </Card>
            </Col>

            <Col xs={24} lg={10}>
              <Card title="上传新索引表">
                <Form form={indexUploadForm} layout="vertical" onFinish={handleUploadIndex}>
                  <Form.Item
                    name="year_month"
                    label="年月"
                    rules={[{ required: true, message: '请输入年月' }]}
                  >
                    <Input placeholder="例如: 202601" />
                  </Form.Item>

                  <Form.Item
                    name="sale_wo"
                    label="销售指令号 (SALE_WO)"
                    rules={[{ required: true, message: '请输入销售指令号' }]}
                  >
                    <Input placeholder="例如: 120000587070" />
                  </Form.Item>

                  <Form.Item
                    name="ac_no"
                    label="飞机号 (AC_NO)"
                    rules={[{ required: true, message: '请输入飞机号' }]}
                  >
                    <Input placeholder="例如: A6-EUD" />
                  </Form.Item>

                  <Form.Item label="索引表文件">
                    <Upload
                      accept=".xlsx,.xls"
                      maxCount={1}
                      beforeUpload={beforeUploadExcel}
                      onChange={(info) => setIndexFile(info.fileList[info.fileList.length - 1] || null)}
                      fileList={indexFile ? [indexFile] : []}
                    >
                      <Button icon={<UploadOutlined />}>选择文件</Button>
                    </Upload>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      需包含 AREA, COMPONENT, CMM, RELATE_JC_SEQ 列
                    </Text>
                  </Form.Item>

                  <Form.Item>
                    <Button
                      type="primary"
                      htmlType="submit"
                      icon={<CloudUploadOutlined />}
                      loading={uploadingIndex}
                      disabled={!indexFile}
                      block
                    >
                      上传并保存
                    </Button>
                  </Form.Item>
                </Form>
              </Card>
            </Col>
          </Row>

          {/* 详情弹窗（可编辑） */}
          <Modal
            title="索引表详情"
            open={detailModalOpen}
            onCancel={() => {
              setDetailModalOpen(false)
              setEditingId(null)
              setAddingNew(false)
            }}
            width={1200}
            footer={null}
          >
            <div style={{ marginBottom: 16 }}>
              <Space>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={startAddNew}
                  disabled={addingNew || editingId !== null}
                >
                  添加新项
                </Button>
                <Button icon={<ReloadOutlined />} onClick={refreshDetail} loading={detailLoading}>
                  刷新
                </Button>
              </Space>
            </div>

            {/* 添加新项表单 */}
            {addingNew && (
              <Card size="small" style={{ marginBottom: 16 }}>
                <Form form={newItemForm} layout="inline">
                  <Form.Item name="comp_pn" label="COMPONENT P/N">
                    <Input size="small" style={{ width: 120 }} />
                  </Form.Item>
                  <Form.Item name="comp_desc" label="COMPONENT DESC">
                    <Input size="small" style={{ width: 160 }} />
                  </Form.Item>
                  <Form.Item name="comp_cmm" label="COMPONENT MANUAL">
                    <Input size="small" style={{ width: 160 }} />
                  </Form.Item>
                  <Form.Item name="comp_cmm_rev" label="MANUAL REV">
                    <Input size="small" style={{ width: 100 }} />
                  </Form.Item>
                  <Form.Item name="remark" label="REMARK">
                    <Input size="small" style={{ width: 120 }} />
                  </Form.Item>
                  <Form.Item>
                    <Space>
                      <Button type="primary" size="small" icon={<SaveOutlined />} onClick={saveNewItem}>
                        保存
                      </Button>
                      <Button size="small" icon={<CloseOutlined />} onClick={cancelAddNew}>
                        取消
                      </Button>
                    </Space>
                  </Form.Item>
                </Form>
              </Card>
            )}

            <Form form={editItemForm} component={false}>
              <Table
                columns={itemColumns}
                dataSource={indexItems}
                rowKey="id"
                loading={detailLoading}
                size="small"
                scroll={{ x: 1000, y: 400 }}
                pagination={{ pageSize: 50 }}
              />
            </Form>
          </Modal>
        </div>
      )
    }

  const handleAddManualDefect = () => {
    // Generate a unique negative ID
    const minId = Math.min(0, ...matchResults.map(r => r.defect_record_id))
    const newId = minId - 1

    const newDefect: MatchResult = {
      defect_record_id: newId,
      defect_number: `NEW-${Math.abs(newId)}`, // Temporary number
      description_cn: '',
      description_en: 'New Defect Description', // Default text
      candidates: [],
      selected_workcard_id: undefined,
      issued_workcard_number: undefined,
      txtZoneTen: '',
      txtCRN: '',
      refNo: '',
      area: '',
      candidate_workcard: '',
      candidate_description_en: '',
      ref_manual: ''
    }

    setMatchResults(prev => [newDefect, ...prev])
    message.success('已添加新缺陷记录')
  }

  const handleDeleteDefect = (defectId: number, e: React.MouseEvent) => {
    e.stopPropagation()
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这条缺陷记录吗？此操作无法撤销。',
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: () => {
        setMatchResults(prev => prev.filter(item => item.defect_record_id !== defectId))
        message.success('删除成功')
      }
    })
  }

  const handleSaveNewDefects = async () => {
    // Implement save logic here
    // For now, just show a message as we need backend API support
    message.info('保存功能开发中...')
  }

  const renderDefectList = (dataSource: MatchResult[], isNewTab: boolean = false) => (
    <>
      {isNewTab && (
        <Space style={{ width: '100%', marginBottom: 16 }}>
          <Button
            type="dashed"
            icon={<PlusOutlined />}
            style={{ height: 64, fontSize: '16px', flex: 1 }}
            onClick={handleAddManualDefect}
          >
            添加新缺陷
          </Button>
          <Button
            type="primary"
            icon={<SaveOutlined />}
            style={{ height: 64, fontSize: '16px', width: 200 }}
            onClick={handleSaveNewDefects}
            disabled={dataSource.length === 0}
          >
            保存新增缺陷
          </Button>
        </Space>
      )}
      <List
        grid={{ gutter: 16, column: 3 }}
        dataSource={dataSource}
        loading={loadingMatchResults}
      pagination={{
        pageSize: 12,
        showSizeChanger: true,
        showTotal: (total) => `共 ${total} 条缺陷记录`
      }}
      renderItem={(item) => {
        const isSelected = selectedBatchIds.includes(item.defect_record_id)
        const isImporting = importingRecordIds.includes(item.defect_record_id)
        const isWritingSteps = importingStepsRecordIds.includes(item.defect_record_id)
        
        // Get selected candidate number
        const selectedCandidateId = pendingSelections[item.defect_record_id] ?? item.selected_workcard_id
        const selectedCandidate = item.candidates.find(c => c.id === selectedCandidateId)
        const candidateNo = selectedCandidate?.workcard_number

        return (
          <List.Item>
            <Card
              hoverable
              style={{ 
                border: isSelected ? '1px solid #40a9ff' : '1px solid #f0f0f0',
                backgroundColor: isSelected ? '#e6f7ff' : '#ffffff',
                cursor: 'pointer',
                borderRadius: '8px',
                boxShadow: isSelected ? '0 4px 12px rgba(24, 144, 255, 0.2)' : '0 2px 8px rgba(0, 0, 0, 0.08)',
                transition: 'all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1)',
                transform: isSelected ? 'translateY(-2px)' : 'none',
                height: '100%',
                display: 'flex',
                flexDirection: 'column'
              }}
              bodyStyle={{ 
                padding: '16px', 
                flex: 1, 
                display: 'flex', 
                flexDirection: 'column' 
              }}
              onClick={(e) => {
                // Prevent drawer opening when clicking specific elements
                const target = e.target as HTMLElement
                // Check if click is on or inside checkbox or button
                if (target.closest('.ant-checkbox-wrapper') || 
                    target.closest('.ant-btn') || 
                    target.closest('button') || 
                    target.closest('.ant-checkbox')) {
                  return
                }
                handleOpenDetailDrawer(item)
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-4px)'
                e.currentTarget.style.boxShadow = '0 8px 16px rgba(0, 0, 0, 0.12)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = isSelected ? 'translateY(-2px)' : 'none'
                e.currentTarget.style.boxShadow = isSelected ? '0 4px 12px rgba(24, 144, 255, 0.2)' : '0 2px 8px rgba(0, 0, 0, 0.08)'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <Space>
                  <Checkbox
                    checked={isSelected}
                    onChange={(e) => {
                      const checked = e.target.checked
                      setSelectedBatchIds(prev => 
                        checked 
                          ? [...prev, item.defect_record_id]
                          : prev.filter(id => id !== item.defect_record_id)
                      )
                    }}
                  />
                  <Text strong style={{ fontSize: 16, color: '#1890ff' }}>
                    {item.defect_number}
                  </Text>
                </Space>
                {item.issued_workcard_number && (
                  <Tag color="#52c41a" style={{ marginRight: 0, fontWeight: 'bold' }}>
                    {item.issued_workcard_number}
                  </Tag>
                )}
                <Button
                  type="text"
                  danger
                  icon={<DeleteOutlined />}
                  size="small"
                  onClick={(e) => handleDeleteDefect(item.defect_record_id, e)}
                />
              </div>

              <div style={{ 
                background: isSelected ? '#ffffff' : '#f0f5ff', 
                padding: '12px', 
                borderRadius: '6px',
                borderLeft: '4px solid #1890ff',
                marginBottom: '16px',
                boxShadow: 'inset 0 1px 3px rgba(0,0,0,0.05)',
                flex: 1,
                minHeight: '80px'
              }}>
                <Text 
                  style={{  
                    fontSize: 14, 
                    color: '#262626', 
                    lineHeight: 1.5, 
                    fontWeight: 500,
                    display: '-webkit-box',
                    WebkitLineClamp: 4,
                    WebkitBoxOrient: 'vertical',
                    overflow: 'hidden'
                  }}
                  title={item.description_en}
                >
                   {item.description_en || '无英文描述'}
                </Text>
              </div>

              {candidateNo && (
                <div style={{ 
                  marginBottom: 12, 
                  padding: '4px 8px', 
                  background: '#f6ffed', 
                  border: '1px solid #b7eb8f', 
                  borderRadius: '4px',
                  fontSize: 12,
                  color: '#389e0d',
                  display: 'inline-flex',
                  alignItems: 'center',
                  maxWidth: '100%',
                  alignSelf: 'flex-start'
                }}>
                  <span style={{ marginRight: 8, fontWeight: 500 }}>候选工卡:</span>
                  <span style={{ fontFamily: 'monospace', fontWeight: 'bold' }}>{candidateNo}</span>
                </div>
              )}

              <Space wrap size={[8, 8]} style={{ width: '100%', justifyContent: 'flex-end' }}>
                <Button 
                  type="primary"
                  size="small"
                  ghost
                  onClick={() => handleImportSingle(item)}
                  loading={isImporting}
                  disabled={isImporting}
                >
                  开出工卡
                </Button>
                <Button 
                  type="default" 
                  size="small"
                  onClick={() => handleWriteStepsSingle(item)}
                  disabled={isImporting}
                >
                  编写方案
                </Button>
                <Button 
                  type="default" 
                  size="small"
                  onClick={() => handleImportStepsSingle(item)}
                  loading={isWritingSteps}
                  disabled={isWritingSteps}
                >
                  导入步骤
                </Button>
              </Space>
            </Card>
          </List.Item>
        )
      }}
    />
    </>
  )

  return (
      <>
        <Card style={{ marginBottom: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <Title level={5} style={{ margin: 0 }}>
                  数据表操作
                </Title>
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
              <Form.Item label="Fleet (txtFleet)" name="txtFleet">
                <Input placeholder="默认: 777/330" />
              </Form.Item>
            </Col>
          </Row>

          <div style={{ display: 'none' }}>
          <Divider orientation="left" style={{ margin: '12px 0' }}>其他参数 (可折叠或保持默认)</Divider>

          <Row gutter={16}>
            <Col span={6}>
              <Form.Item label="Zone Name (txtZoneName)" name="txtZoneName">
                <Input placeholder="默认: %BB%FA%C9%CF" disabled />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="RII (txtRII)" name="txtRII">
                <Input disabled />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="CJC (txtCJC)" name="txtCJC">
                <Input disabled />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="备注 (txtRemark)" name="txtRemark">
                <Input disabled />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={6}>
              <Form.Item label="开卡工艺组 (txtDept)" name="txtDept" initialValue="3_CABIN_TPG">
                <Input placeholder="默认: 3_CABIN_TPG" disabled />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="Dept1 (txtDept1)" name="txtDept1">
                <Input disabled />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="DocType (selDocType)" name="selDocType">
                <Input placeholder="默认: NR" disabled />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="Station (txtStation)" name="txtStation" initialValue="CAN">
                <Input placeholder="默认: CAN" disabled />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={6}>
              <Form.Item label="MenuID (txtMenuID)" name="txtMenuID">
                <Input placeholder="默认: 15196" disabled />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="ParentID (txtParentID)" name="txtParentID">
                <Input placeholder="默认: 13112" disabled />
              </Form.Item>
            </Col>
          </Row>
          </div>
        </Form>
      </Card>

      <Card
        title="缺陷匹配结果与候选工卡"
        style={{ marginBottom: '24px' }}
        extra={
          <Space>
            <Tag color={matchResults.length > 0 ? 'green' : 'orange'}>
              {matchResults.length > 0 ? `共 ${matchResults.length} 条缺陷` : '暂无匹配结果'}
            </Tag>
            {matchResults.length > 0 && (
              <>
                <Button
                  size="small"
                  onClick={handleSelectAllPages}
                  disabled={matchResults.length === 0}
                >
                  {matchResults.every(row => selectedBatchIds.includes(row.defect_record_id))
                    ? '取消全选所有页'
                    : '全选所有页'}
                </Button>
                <Button
                  size="small"
                  icon={<DownloadOutlined />}
                  onClick={handleExportSelectedWorkcards}
                  disabled={selectedBatchIds.length === 0}
                  type="primary"
                >
                  导出选定工卡列表 ({selectedBatchIds.length})
                </Button>
              </>
            )}
          </Space>
        }
      >
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
            icon={<EditOutlined />}
            onClick={handleBatchWriteSteps}
            disabled={selectedBatchIds.length === 0}
          >
            批量编写方案
          </Button>
          <Button
            onClick={handleBatchImportSteps}
            loading={batchImportStepsLoading}
            disabled={selectedBatchIds.length === 0}
          >
            批量导入步骤
          </Button>
        </Space>
        <Tabs
          defaultActiveKey="imported"
          type="card"
          items={[
            {
              key: 'imported',
              label: `导入缺陷 (${matchResults.filter(r => r.defect_record_id > 0).length})`,
              children: renderDefectList(matchResults.filter(r => r.defect_record_id > 0))
            },
            {
              key: 'new',
              label: `新增缺陷 (${matchResults.filter(r => r.defect_record_id < 0).length})`,
              children: renderDefectList(matchResults.filter(r => r.defect_record_id < 0), true)
            }
          ]}
        />
      </Card>

      <Card title="执行与日志">
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
              placeholder="请输入工卡号，如：50299"
            />
          </Form.Item>
        </Form>
      </Modal>

      <Drawer
        title={activeDetailItem ? `缺陷详情: ${activeDetailItem.defect_number}` : '缺陷详情'}
        placement="right"
        width={drawerWidth}
        onClose={handleCloseDetailDrawer}
        open={detailDrawerOpen}
        bodyStyle={{ padding: 0, overflow: 'hidden' }}
      >
        <div style={{ display: 'flex', height: '100%' }}>
          {/* Resize Handle */}
          <div
            style={{
              width: 12,
              cursor: 'col-resize',
              height: '100%',
              backgroundColor: '#f5f5f5',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRight: '1px solid #e8e8e8',
              flexShrink: 0,
              transition: 'background-color 0.2s',
            }}
            onMouseDown={() => {
              isResizingRef.current = true
              document.body.style.cursor = 'col-resize'
            }}
            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#e6f7ff'}
            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#f5f5f5'}
          >
            <div style={{ width: 4, height: 24, borderLeft: '1px solid #d9d9d9', borderRight: '1px solid #d9d9d9' }} />
          </div>

          {/* Content */}
          <div style={{ flex: 1, padding: 24, overflowY: 'auto' }}>
            {activeDetailItem && (
              <Space direction="vertical" style={{ width: '100%' }} size={24}>
            
            {/* 英文描述 */}
            <div>
              <Text type="secondary">工卡描述 (英文)</Text>
              <div style={{ 
                marginTop: 8,
                padding: '12px',
                background: '#f5f5f5',
                borderRadius: '4px',
                borderLeft: '4px solid #1890ff',
                fontSize: 15
              }}>
                {activeDetailItem.description_en || '无英文描述'}
              </div>
            </div>

            {/* 中文描述 */}
            <div>
              <Text type="secondary">工卡描述 (中文)</Text>
              <div style={{ marginTop: 8, fontSize: 14 }}>
                {activeDetailItem.description_cn || '无中文描述'}
              </div>
            </div>

            <div style={{ marginTop: 16 }}>
              <Descriptions column={2} size="small" bordered>
                <Descriptions.Item label="Zone">{activeDetailItem.txtZoneTen || '-'}</Descriptions.Item>
                <Descriptions.Item label="Reference">{activeDetailItem.refNo || '-'}</Descriptions.Item>
                <Descriptions.Item label="Manual (CMM)" span={2}>{activeDetailItem.ref_manual || '-'}</Descriptions.Item>
                <Descriptions.Item label="Related Workcard" span={2}>{activeDetailItem.txtCRN || '-'}</Descriptions.Item>
              </Descriptions>
            </div>

            <Divider />

            {/* 方案步骤信息 */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Text strong style={{ fontSize: 16 }}>方案步骤信息</Text>
                <Button size="small" type="primary" icon={<PlusOutlined />} onClick={handleAddStep}>
                  新增步骤
                </Button>
              </div>
              <div style={{ marginTop: 16 }}>
                <Table 
                  dataSource={activeDetailItem.steps || []}
                  rowKey="step_number"
                  pagination={false}
                  size="small"
                  bordered
                  columns={[
                    { 
                      title: '#', 
                      dataIndex: 'step_number', 
                      width: 50,
                      align: 'center'
                    },
                    { 
                      title: '步骤内容', 
                      key: 'content',
                      render: (_, record: SchemeStep) => (
                        <div style={{ wordBreak: 'break-word' }}>
                          <div style={{ fontWeight: 500, marginBottom: 4 }}>{record.content_en}</div>
                          <div style={{ color: '#666', fontSize: 12 }}>{record.content_cn}</div>
                        </div>
                      )
                    },
                    { 
                      title: '工时/人力', 
                      key: 'labor',
                      width: 120,
                      render: (_, record: SchemeStep) => (
                        <div style={{ fontSize: 12, whiteSpace: 'nowrap' }}>
                          <div><span style={{color: '#8c8c8c'}}>工时:</span> {record.man_hours}</div>
                          <div><span style={{color: '#8c8c8c'}}>人力:</span> {record.manpower}</div>
                          {record.trade && <div><span style={{color: '#8c8c8c'}}>工种:</span> {record.trade}</div>}
                        </div>
                      )
                    },
                    { 
                      title: '航材', 
                      key: 'materials',
                      width: 140,
                      render: (_, record: SchemeStep) => (
                         <div style={{ fontSize: 12 }}>
                           {record.materials?.length > 0 ? (
                             record.materials.map((m, i) => (
                               <div key={i} style={{ marginBottom: 2 }}>
                                 <span style={{ fontWeight: 500 }}>{m.part_number}</span>
                                 <span style={{ marginLeft: 4, color: '#8c8c8c' }}>x{m.quantity}</span>
                               </div>
                             ))
                           ) : <span style={{ color: '#ccc' }}>-</span>}
                         </div>
                      )
                    },
                    {
                      title: '操作',
                      key: 'action',
                      width: 100,
                      align: 'center',
                      render: (_, record: SchemeStep) => (
                        <Space size="small">
                          <Button 
                            type="text" 
                            size="small" 
                            icon={<EditOutlined />} 
                            onClick={() => handleEditStep(record)}
                          />
                          <Popconfirm
                            title="确定删除此步骤吗?"
                            onConfirm={() => handleDeleteStep(record.step_number)}
                          >
                            <Button 
                              type="text" 
                              size="small" 
                              danger 
                              icon={<DeleteOutlined />} 
                            />
                          </Popconfirm>
                        </Space>
                      )
                    }
                  ]}
                  locale={{ emptyText: <div style={{ padding: '24px 0', color: '#999' }}>暂无方案步骤信息</div> }}
                />
              </div>
            </div>

            {/* 底部操作区 */}
            <div style={{ marginTop: 24, textAlign: 'right' }}>
               <Button onClick={handleCloseDetailDrawer}>关闭</Button>
            </div>
          </Space>
             )}
           </div>
         </div>
      </Drawer>

      {/* 步骤编辑弹窗 */}
      <Modal
        title={editingStep ? `编辑步骤 #${editingStep.step_number}` : '新增步骤'}
        open={stepModalOpen}
        onOk={handleSaveStep}
        onCancel={() => setStepModalOpen(false)}
        destroyOnClose
        width={600}
      >
        <Form form={stepForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
               <Form.Item label="步骤序号" name="step_number" rules={[{ required: true }]}>
                 <Input disabled={!!editingStep} type="number" />
               </Form.Item>
            </Col>
            <Col span={12}>
               <Form.Item label="工种 (Trade)" name="trade" rules={[{ required: true }]}>
                 <Input />
               </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
               <Form.Item label="工时 (Man Hours)" name="man_hours" rules={[{ required: true }]}>
                 <Input />
               </Form.Item>
            </Col>
            <Col span={12}>
               <Form.Item label="人力 (Manpower)" name="manpower" rules={[{ required: true }]}>
                 <Input />
               </Form.Item>
            </Col>
          </Row>
          <Form.Item label="英文内容 (Content EN)" name="content_en" rules={[{ required: true }]}>
            <Input.TextArea rows={4} />
          </Form.Item>
          <Form.Item label="中文内容 (Content CN)" name="content_cn">
            <Input.TextArea rows={4} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
  }

  const menuItems = [
    { key: '1', icon: <AppstoreOutlined />, label: '英文工卡批量导入' },
    { key: '2', icon: <BugOutlined />, label: '缺陷清单处理' },
    { key: '3', icon: <DatabaseOutlined />, label: '索引数据表管理' },
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider 
        collapsible 
        collapsed={collapsed} 
        onCollapse={setCollapsed}
        theme="light"
        width={250}
        style={{
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          boxShadow: '2px 0 8px 0 rgba(29,35,41,.05)',
          zIndex: 10
        }}
      >
        <div style={{ 
          height: 64, 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          borderBottom: '1px solid #f0f0f0'
        }}>
          <Title level={4} style={{ margin: 0, color: '#1890ff' }}>
            {collapsed ? 'AJC' : 'AutoJobCard'}
          </Title>
        </div>
        <Menu 
          theme="light" 
          mode="inline" 
          selectedKeys={[selectedKey]} 
          onClick={(e) => setSelectedKey(e.key)}
          items={menuItems}
          style={{ borderRight: 0 }}
        />
        
        {/* Global Cookie Configuration */}
        <div style={{ padding: '16px', borderTop: '1px solid #f0f0f0' }}>
          <Typography.Text strong style={{ fontSize: 14, display: 'block', marginBottom: 8 }}>
            cookie 选填
          </Typography.Text>
          <Input.TextArea 
            placeholder="Paste global cookie here..." 
            value={globalCookie}
            onChange={(e) => setGlobalCookie(e.target.value)}
            rows={3}
            style={{ fontSize: 12, resize: 'none' }}
          />
        </div>
      </Sider>
      <Layout style={{ marginLeft: collapsed ? 80 : 250, transition: 'all 0.2s' }}>
        <Layout.Header style={{ 
          padding: '0 24px', 
          background: '#fff', 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between',
          boxShadow: '0 1px 4px rgba(0,21,41,.08)',
          zIndex: 1
        }}>
          <Title level={4} style={{ margin: 0 }}>
            {menuItems.find(item => item.key === selectedKey)?.label}
          </Title>
          <Space>
             <Button type="text" icon={<HomeOutlined />} onClick={handleGoHome}>首页</Button>
          </Space>
        </Layout.Header>
        <Content style={{ margin: '24px 16px', overflow: 'initial' }}>
          {renderContent()}
        </Content>
      </Layout>
    </Layout>
  )
}

export default EnglishBatchImportDebug
