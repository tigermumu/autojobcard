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
  Modal
} from 'antd'
import {
  LeftOutlined,
  HomeOutlined,
  ReloadOutlined,
  RightOutlined,
  EditOutlined,
  FileTextOutlined
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { defectApi, CandidateWorkCard } from '../services/defectApi'
import { workcardImportApi, PreviewResponse, RunResponse, ImportStepsResponse } from '../services/workcardImportApi'
import { matchingApi } from '../services/matchingApi'
import { importBatchApi, ImportBatchSummary, ImportBatchDetail } from '../services/importBatchApi'

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
    locationState.defectListInfo ?? null
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
  const [importRunLoading, setImportRunLoading] = useState(false)
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
const [currentImportBatch, setCurrentImportBatch] = useState<ImportBatchDetail | null>(null)
const [editingWorkcardNumber, setEditingWorkcardNumber] = useState<{ defect_record_id: number; value: string } | null>(null)
const [updatingWorkcardNumber, setUpdatingWorkcardNumber] = useState<number[]>([])
  const [batchImportStepsLoading, setBatchImportStepsLoading] = useState(false)
  const [importingStepsRecordIds, setImportingStepsRecordIds] = useState<number[]>([])

const autoLoadTriggeredRef = useRef(false)

const readyForMatch = matchResults.length > 0 || selectedImportBatchId !== undefined

  useEffect(() => {
    if (initialMatchResults.length > 0) {
      autoLoadTriggeredRef.current = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    let cancelled = false
    const fetchImportBatches = async () => {
      try {
        setLoadingImportBatches(true)
        const batches = await importBatchApi.list()
        if (cancelled) {
          return
        }
        setImportBatches(batches)
        if (batches.length > 0) {
          const targetId = selectedImportBatchId ?? batches[0].id
          setSelectedImportBatchId(targetId)
          loadImportBatch(targetId)
        }
      } catch (error: any) {
        if (!cancelled) {
          message.error('获取待导入工卡数据表失败: ' + (error?.message || error))
        }
      } finally {
        if (!cancelled) {
          setLoadingImportBatches(false)
        }
      }
    }

    fetchImportBatches()
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
      setCurrentImportBatch(detail)
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
        const candidateId =
          item.selected_workcard_id ??
          (item.defect_record_id ? item.defect_record_id : index + 1)
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
          issued_workcard_number: (item as any).issued_workcard_number || 'NR/000'  // 默认值
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
      setImportRunLoading(false)
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

  const ensurePreviewData = async (values: any) => {
    if (importPreviewData) {
      return importPreviewData
    }
    return await fetchPreviewData(values)
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

  const handleRunImport = async () => {
    try {
      const values = await importForm.validateFields(['cookies'])
      const baseParams = getImportParams()
      const preview = await ensurePreviewData(values)
      if (!preview) {
        return
      }
      if (!selectedPreviewWorkcardRid) {
        message.warning('请在候选列表中选择要导入的工卡')
        return
      }
      if (!selectedPreviewHistoryRid) {
        message.warning('请在历史工卡列表中选择导入来源')
        return
      }
      setImportLogs([])
      setImportArtifacts([])
      setImportRunLoading(true)
      const workcardIndex = preview.workcards.findIndex(item => item.rid === selectedPreviewWorkcardRid)
      const historyIndex = preview.history_cards.findIndex(item => item.rid === selectedPreviewHistoryRid)

      const response = await workcardImportApi.run({
        ...baseParams,
        workcard_rid: selectedPreviewWorkcardRid,
        workcard_index: workcardIndex >= 0 ? workcardIndex : undefined,
        history_rid: selectedPreviewHistoryRid,
        history_card_index: historyIndex >= 0 ? historyIndex : undefined,
        cookies: composeCookies(values)
      })

      setImportResult(response)
      setImportLogs(response.logs)
      setImportArtifacts(response.artifacts)

      if (response.success) {
        message.success(response.message || '导入成功')
      } else {
        message.error(response.message || '导入失败')
      }
    } catch (error: any) {
      if (!error?.errorFields) {
        message.error('执行导入失败: ' + (error?.message || error))
      }
    } finally {
      setImportRunLoading(false)
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
    if (!record.selected_workcard_id) {
      message.warning(`请先保存缺陷 ${record.defect_number} 的候选工卡`)
      return
    }
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
              txtACNO: importParams.txtACNO,
              txtWO: importParams.txtWO,
              txtML: importParams.txtML,
              txtCust: importParams.txtCust,
              txtACType: importParams.txtACType || 'B737-300',
              txtCRN: importParams.txtCRN || '客户要求/CUSTOMER REQUIREMENT',
              txtDept: importParams.txtDept || '3_CABIN_TPG',
              selDocType: importParams.selDocType || 'NR',
              txtCorrosion: importParams.txtCorrosion || 'N',
              txtDescChn: record.description_cn || '',
              txtDescEng: record.description_en || '',
            }
            
            const response = await workcardImportApi.importDefect({
              defect_record_id: record.defect_record_id,
              params,
              cookies: composeCookies(cookieValues),
              is_test_mode: importParams.is_test_mode !== false
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
              if (!record.selected_workcard_id) {
                failureMessages.push(`缺陷 ${record.defect_number} 未保存候选工卡`)
                continue
              }
              try {
                // 构建导入参数
                const params = {
                  txtACNO: importParams.txtACNO,
                  txtWO: importParams.txtWO,
                  txtML: importParams.txtML,
                  txtCust: importParams.txtCust,
                  txtACType: importParams.txtACType || 'B737-300',
                  txtCRN: importParams.txtCRN || '客户要求/CUSTOMER REQUIREMENT',
                  txtDept: importParams.txtDept || '3_CABIN_TPG',
                  selDocType: importParams.selDocType || 'NR',
                  txtCorrosion: importParams.txtCorrosion || 'N',
                  txtDescChn: record.description_cn || '',
                  txtDescEng: record.description_en || '',
                }
                
                const response = await workcardImportApi.importDefect({
                  defect_record_id: record.defect_record_id,
                  params,
                  cookies,
                  is_test_mode: importParams.is_test_mode !== false
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
    if (!record.issued_workcard_number || record.issued_workcard_number === 'NR/000' || !record.selected_workcard_id) {
      message.warning(`缺陷 ${record.defect_number} 需要已开出工卡号且已保存候选工卡`)
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
    
    // 检查选中的记录是否都有已开出工卡号和候选工卡
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
    getCheckboxProps: (record: MatchResult) => ({
      disabled: !record.selected_workcard_id
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
                  setCurrentImportBatch(null)
                  setMatchResults([])
                  setPendingSelections({})
                  setSelectedBatchIds([])
                  setDefectListInfo(null)
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
          </Space>
        </div>
      </Card>

      <Card title="导入参数配置" style={{ marginBottom: '24px' }}>
        <Form form={importParamsForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="飞机号 (txtACNO)"
                name="txtACNO"
                rules={[{ required: true, message: '请输入飞机号' }]}
              >
                <Input placeholder="请输入飞机号" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="工作指令号 (txtWO)"
                name="txtWO"
                rules={[{ required: true, message: '请输入工作指令号' }]}
              >
                <Input placeholder="请输入工作指令号" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="维修级别 (txtML)"
                name="txtML"
                rules={[{ required: true, message: '请输入维修级别' }]}
              >
                <Input placeholder="请输入维修级别" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="客户 (txtCust)"
                name="txtCust"
                rules={[{ required: true, message: '请输入客户' }]}
              >
                <Input placeholder="请输入客户" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="机型 (txtACType)"
                name="txtACType"
                initialValue="B737-300"
                rules={[{ required: true, message: '请输入机型' }]}
              >
                <Input placeholder="请输入机型，默认B737-300" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="相关工卡号 (txtCRN)"
                name="txtCRN"
                initialValue="客户要求/CUSTOMER REQUIREMENT"
              >
                <Input placeholder="请输入相关工卡号" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="工艺组 (txtDept)"
                name="txtDept"
                initialValue="3_CABIN_TPG"
                rules={[{ required: true, message: '请输入工艺组' }]}
              >
                <Input placeholder="请输入工艺组" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="工卡类型 (selDocType)"
                name="selDocType"
                initialValue="NR"
                rules={[{ required: true, message: '请选择工卡类型' }]}
              >
                <Select>
                  <Option value="NR">NR</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="是否腐蚀 (txtCorrosion)"
                name="txtCorrosion"
                initialValue="N"
                rules={[{ required: true, message: '请选择是否腐蚀' }]}
              >
                <Select>
                  <Option value="Y">是</Option>
                  <Option value="N">否</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="测试模式"
                name="is_test_mode"
                valuePropName="checked"
                initialValue={true}
              >
                <Switch checkedChildren="开启" unCheckedChildren="关闭" />
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

