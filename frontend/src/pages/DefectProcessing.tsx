import React, { useState, useEffect, useRef } from 'react'
import { 
  Card, 
  Button, 
  Space, 
  Table, 
  message,
  Typography,
  Input,
  Select,
  Tag,
  Modal,
  Form,
  Upload,
  Steps,
  Radio,
  Progress,
  Divider,
  Empty,
  Row,
  Col,
  Popconfirm
} from 'antd'
import {
  UploadOutlined,
  ReloadOutlined,
  HomeOutlined,
  PlayCircleOutlined,
  CheckCircleOutlined,
  FileOutlined,
  SearchOutlined,
  LeftOutlined,
  RightOutlined,
  SaveOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { defectApi, DefectList, DefectRecord, CandidateWorkCard } from '../services/defectApi'
import { configApi, Configuration } from '../services/configApi'
import { workcardApi, WorkCardGroup } from '../services/workcardApi'
import { indexDataApi } from '../services/indexDataApi'
import { importBatchApi } from '../services/importBatchApi'

const { Title } = Typography
const { Option } = Select
const { Step } = Steps

interface MatchResult {
  defect_record_id: number
  defect_number: string
  description_cn?: string
  description_en?: string
  candidates: CandidateWorkCard[]
  selected_workcard_id?: number
}

const DefectProcessing: React.FC = () => {
  const navigate = useNavigate()
  const [currentStep, setCurrentStep] = useState(0)
  const [loading, setLoading] = useState(false)
  const [configurations, setConfigurations] = useState<Configuration[]>([])
  const [defectLists, setDefectLists] = useState<DefectList[]>([])
  const [currentDefectList, setCurrentDefectList] = useState<DefectList | null>(null)
  const [defectRecords, setDefectRecords] = useState<DefectRecord[]>([])
  const [cleanedData, setCleanedData] = useState<any[]>([])
  const [selectedIndexConfig, setSelectedIndexConfig] = useState<number | null>(null)
  const [selectedWorkcardGroup, setSelectedWorkcardGroup] = useState<WorkCardGroup | null>(null)
  const [workcardGroups, setWorkcardGroups] = useState<WorkCardGroup[]>([])
  const [matchResults, setMatchResults] = useState<MatchResult[]>([])
  const [uploading, setUploading] = useState(false)
  const [cleaning, setCleaning] = useState(false)
  const [matching, setMatching] = useState(false)
  const [loadingConfigurations, setLoadingConfigurations] = useState(false)
  const [cleaningProgress, setCleaningProgress] = useState({
    percent: 0,
    current: 0,
    total: 0,
    message: ''
  })
  const [matchingProgress, setMatchingProgress] = useState<{
    taskId: string | null
    status: 'idle' | 'processing' | 'completed' | 'failed'
    total: number
    completed: number
    current: { defect_number: string; description: string } | null
    matchedCount: number
    failedCount: number
    candidatesFound: number
  }>({
    taskId: null,
    status: 'idle',
    total: 0,
    completed: 0,
    current: null,
    matchedCount: 0,
    failedCount: 0,
    candidatesFound: 0
  })
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const hasShownCompletionMessageRef = useRef<boolean>(false)
  const [saveModalVisible, setSaveModalVisible] = useState(false)
  const [savingBatch, setSavingBatch] = useState(false)
  const [metadataForm] = Form.useForm()
  const [latestBatchId, setLatestBatchId] = useState<number | null>(null)

  const toSafeString = (value: any): string => {
    if (typeof value === 'string') {
      return value.trim()
    }
    if (value === null || value === undefined) {
      return ''
    }
    return String(value)
  }

  const normalizeCleanedRecord = (item: any) => {
    const descriptionCn = toSafeString(
      item?.description_cn ?? item?.['工卡描述（中文）'] ?? item?.title ?? item?.description ?? ''
    )
    const descriptionEn = toSafeString(
      item?.description_en ?? item?.['工卡描述（英文）'] ?? ''
    )
    return {
      ...item,
      description_cn: descriptionCn,
      description_en: descriptionEn,
      title: descriptionCn
    }
  }

  const normalizeMatchResult = (item: any): MatchResult => {
    const descriptionCn = toSafeString(item?.description_cn ?? item?.title ?? '')
    const descriptionEn = toSafeString(item?.description_en ?? item?.title_en ?? '')
    return {
      ...item,
      description_cn: descriptionCn,
      description_en: descriptionEn
    }
  }

  useEffect(() => {
    loadConfigurations()
    loadDefectLists()
    loadWorkcardGroups()
  }, [])

  // 清理轮询定时器
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current)
        pollingIntervalRef.current = null
      }
    }
  }, [])

  useEffect(() => {
    if (currentDefectList) {
      loadDefectRecords()
      // 切换缺陷清单时，清除之前选择的索引数据表和清洗数据，需要重新选择
      setSelectedIndexConfig(null)
      setCleanedData([])
      setMatchResults([])
      setSelectedWorkcardGroup(null)
    }
  }, [currentDefectList])

  const loadConfigurations = async () => {
    try {
      setLoadingConfigurations(true)
      const data = await configApi.getAll()
      console.log('加载到的配置列表:', data)
      setConfigurations(data as Configuration[])
      if (!data || data.length === 0) {
        message.warning('暂无可用构型配置，请先在构型管理页面创建构型')
      }
    } catch (error: any) {
      console.error('加载构型列表失败:', error)
      message.error('加载构型列表失败: ' + (error.message || error))
    } finally {
      setLoadingConfigurations(false)
    }
  }

  const loadDefectLists = async () => {
    try {
      const data = await defectApi.getLists()
      setDefectLists(data)
    } catch (error: any) {
      console.error('加载缺陷清单失败:', error)
    }
  }

  const loadWorkcardGroups = async () => {
    try {
      const data = await workcardApi.getGroups(true)
      setWorkcardGroups(data)
    } catch (error: any) {
      console.error('加载工卡分组失败:', error)
    }
  }

  const loadDefectRecords = async (defectListId?: number) => {
    const targetId = defectListId || currentDefectList?.id
    if (!targetId) return
    try {
      const records = await defectApi.getRecords(targetId)
      setDefectRecords(records)
      console.log('加载缺陷记录成功，数量:', records.length)
    } catch (error: any) {
      message.error('加载缺陷记录失败: ' + (error.message || error))
      console.error('加载缺陷记录失败:', error)
    }
  }

  const handleUpload = async (file: File) => {
    try {
      setUploading(true)
      
      // 从文件名提取基本信息
      const fileName = file.name.replace(/\.[^/.]+$/, '') // 去除扩展名
      
      // 尝试从文件名提取飞机号（例如：B-1234_缺陷清单.xlsx）
      const aircraftMatch = fileName.match(/B-[A-Z0-9]+/i)
      const aircraft_number = aircraftMatch ? aircraftMatch[0].toUpperCase() : 'B-XXXX'
      
      // 自动创建缺陷清单
      const newList = await defectApi.createList({
        aircraft_number: aircraft_number,
        title: fileName || '缺陷清单',
        description: undefined,
        configuration_id: configurations.length > 0 ? configurations[0].id : 1 // 使用第一个构型作为默认值
      })
      
      message.success('缺陷清单创建成功')
      setCurrentDefectList(newList)
      await loadDefectLists()
      
      // 上传缺陷数据
      const result = await defectApi.uploadDefectData(newList.id, file)
      if (result.imported_count > 0) {
        message.success(`成功上传 ${result.imported_count} 条缺陷记录`)
        // 直接传递缺陷清单ID，避免异步状态更新问题
        await loadDefectRecords(newList.id)
        // 确保状态更新后再设置步骤
        setCurrentStep(1)
        console.log('上传完成，当前缺陷清单:', newList.id, '缺陷记录数量:', result.imported_count)
      } else {
        message.error('上传失败: ' + (result.message || '未知错误'))
      }
    } catch (error: any) {
      message.error('上传失败: ' + (error.message || error))
    } finally {
      setUploading(false)
    }
    return false
  }

  const handleClean = async (limit?: number) => {
    if (!currentDefectList || !selectedIndexConfig) {
      message.warning('请先选择索引数据表')
      return
    }

    try {
      setCleaning(true)
      setCleaningProgress({
        percent: 0,
        current: 0,
        total: 0,
        message: '准备开始清洗...'
      })

      // 使用带进度条的方法
      defectApi.cleanDefectDataWithProgress(
        {
          defect_list_id: currentDefectList.id,
          configuration_id: selectedIndexConfig,
          limit: limit
        },
        (progressEvent) => {
          if (progressEvent.type === 'start') {
            setCleaningProgress({
              percent: 0,
              current: 0,
              total: 0,
              message: progressEvent.message || '开始清洗缺陷数据...'
            })
          } else if (progressEvent.type === 'progress') {
            setCleaningProgress({
              percent: progressEvent.percent || 0,
              current: progressEvent.current || 0,
              total: progressEvent.total || 0,
              message: progressEvent.message || `正在清洗第 ${progressEvent.current}/${progressEvent.total} 条...`
            })
          } else if (progressEvent.type === 'complete') {
            setCleaningProgress({
              percent: 100,
              current: progressEvent.total_count || 0,
              total: progressEvent.total_count || 0,
              message: progressEvent.message || '清洗完成'
            })
            
            const testMode = limit ? `（测试模式：仅清洗 ${limit} 条）` : ''
            message.success(`成功清洗 ${progressEvent.cleaned_count}/${progressEvent.total_count} 条缺陷数据${testMode}`)
            
            console.log('清洗后的数据:', progressEvent.cleaned_data)
            const normalizedCleaned = (progressEvent.cleaned_data || []).map(normalizeCleanedRecord)
            setCleanedData(normalizedCleaned)
            
            // 确保当前步骤至少是2，以便显示清洗后的数据表格
            if (currentStep < 2) {
              setCurrentStep(2)
            }
            
            setCleaning(false)
          } else if (progressEvent.type === 'error') {
            message.error('清洗失败: ' + (progressEvent.message || '未知错误'))
            setCleaning(false)
            setCleaningProgress({
              percent: 0,
              current: 0,
              total: 0,
              message: '清洗失败'
            })
          }
        },
        (error) => {
          message.error('清洗失败: ' + (error.message || error))
          setCleaning(false)
          setCleaningProgress({
            percent: 0,
            current: 0,
            total: 0,
            message: '清洗失败'
          })
        }
      )
    } catch (error: any) {
      message.error('清洗失败: ' + (error.message || error))
      setCleaning(false)
      setCleaningProgress({
        percent: 0,
        current: 0,
        total: 0,
        message: '清洗失败'
      })
    }
  }

  const handleMatch = async () => {
    if (!currentDefectList || !selectedWorkcardGroup) {
      message.warning('请先选择标准工卡数据表')
      return
    }

    try {
      setMatching(true)
      const result = await defectApi.matchDefectData({
        defect_list_id: currentDefectList.id,
        workcard_group: {
          aircraft_number: selectedWorkcardGroup.aircraft_number || undefined,
          aircraft_type: selectedWorkcardGroup.aircraft_type || undefined,
          msn: selectedWorkcardGroup.msn || undefined,
          amm_ipc_eff: selectedWorkcardGroup.amm_ipc_eff || undefined,
          configuration_id: selectedWorkcardGroup.configuration_id
        }
      })
      
      if (result.success && result.task_id) {
        // 异步任务，开始轮询进度
        message.info('匹配任务已启动')
        setMatchingProgress({
          taskId: result.task_id,
          status: 'processing',
          total: result.total || 0,
          completed: 0,
          current: null,
          matchedCount: 0,
          failedCount: 0,
          candidatesFound: 0
        })
        startPollingProgress(result.task_id)
      } else if (result.success && result.results) {
        // 同步返回结果（向后兼容）
        message.success('匹配完成')
        const normalizedResults = (result.results || []).map(normalizeMatchResult)
        setMatchResults(normalizedResults)
        setCurrentStep(4)
        setMatching(false)
      } else {
        message.error('匹配失败: ' + result.message)
        setMatching(false)
      }
    } catch (error: any) {
      message.error('匹配失败: ' + (error.message || error))
      setMatching(false)
    }
  }

  const startPollingProgress = (taskId: string) => {
    // 清除之前的轮询
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current)
      pollingIntervalRef.current = null
    }
    
    // 重置完成消息标志
    hasShownCompletionMessageRef.current = false
    
    // 立即查询一次
    pollProgress(taskId)
    
    // 每1秒轮询一次
    const interval = setInterval(() => {
      pollProgress(taskId)
    }, 1000)
    
    pollingIntervalRef.current = interval
  }

  const pollProgress = async (taskId: string) => {
    try {
      const progress = await defectApi.getMatchingProgress(taskId)
      
      if (progress.status === 'not_found') {
        message.warning('匹配任务不存在或已过期')
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current)
          pollingIntervalRef.current = null
        }
        setMatching(false)
        return
      }
      
      setMatchingProgress({
        taskId: progress.task_id,
        status: progress.status === 'processing' ? 'processing' : progress.status === 'completed' ? 'completed' : 'failed',
        total: progress.total,
        completed: progress.completed,
        current: progress.current ? {
          defect_number: progress.current.defect_number,
          description: progress.current.description
        } : null,
        matchedCount: progress.statistics?.matched || 0,
        failedCount: progress.statistics?.failed || 0,
        candidatesFound: progress.statistics?.candidates_found || 0
      })
      
      // 如果完成或失败，停止轮询
      if (progress.status === 'completed' || progress.status === 'failed') {
        // 先停止轮询
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current)
          pollingIntervalRef.current = null
        }
        setMatching(false)
        
        // 确保消息只显示一次
        if (!hasShownCompletionMessageRef.current) {
          hasShownCompletionMessageRef.current = true
          
          if (progress.status === 'completed') {
            message.success(`匹配完成！共处理 ${progress.total} 条记录，匹配成功 ${progress.statistics?.matched || 0} 条`)
            // 加载匹配结果
            loadMatchResults()
          } else {
            message.error('匹配失败: ' + (progress.error || '未知错误'))
          }
        }
      }
    } catch (error) {
      console.error('获取进度失败:', error)
    }
  }

  const loadMatchResults = async () => {
    if (!currentDefectList) return
    
    try {
      // 从数据库加载匹配结果
      const savedResults = await defectApi.getSavedResults(currentDefectList.id)
      if (savedResults.success && savedResults.results) {
        const normalizedResults = savedResults.results.map((r: any) => ({
          defect_record_id: r.defect_record_id,
          defect_number: r.defect_number,
          description_cn: r.description_cn,
          description_en: r.description_en,
          candidates: r.candidates || [],
          selected_workcard_id: r.selected_workcard_id
        }))
        setMatchResults(normalizedResults)
        setCurrentStep(4)
      }
    } catch (error) {
      console.error('加载匹配结果失败:', error)
    }
  }

  const handleSelectWorkcard = async (defectRecordId: number, workcardId: number) => {
    try {
      await defectApi.selectWorkcard(defectRecordId, workcardId)
      message.success('工卡选择成功')
      // 更新匹配结果中的选择状态
      setMatchResults(prev => prev.map(result => {
        if (result.defect_record_id === defectRecordId) {
          return { ...result, selected_workcard_id: workcardId }
        }
        return result
      }))
    } catch (error: any) {
      message.error('选择失败: ' + (error.message || error))
    }
  }

  // 全选最高评分
  const handleSelectAllHighest = async () => {
    if (matchResults.length === 0) {
      message.warning('没有匹配结果')
      return
    }

    let selectedCount = 0
    let skippedCount = 0

    try {
      setLoading(true)
      
      // 遍历所有匹配结果
      for (const result of matchResults) {
        // 如果已经有选中的工卡，跳过
        if (result.selected_workcard_id) {
          skippedCount++
          continue
        }

        // 如果没有候选工卡，跳过
        if (!result.candidates || result.candidates.length === 0) {
          skippedCount++
          continue
        }

        // 找到评分最高的候选工卡
        const highestCandidate = result.candidates.reduce((prev, current) => 
          (current.similarity_score > prev.similarity_score) ? current : prev
        )

        // 选择最高分的工卡
        try {
          await defectApi.selectWorkcard(result.defect_record_id, highestCandidate.id)
          selectedCount++
        } catch (error) {
          console.error(`选择缺陷 ${result.defect_number} 的工卡失败:`, error)
        }
      }

      // 刷新匹配结果
      if (currentDefectList && selectedWorkcardGroup) {
        const savedResults = await defectApi.getSavedResults(
          currentDefectList.id,
          selectedWorkcardGroup.configuration_id
        )
        if (savedResults.success && savedResults.results) {
          setMatchResults(savedResults.results)
        }
      }

      message.success(`已为 ${selectedCount} 条缺陷自动选择最高评分工卡${skippedCount > 0 ? `，跳过 ${skippedCount} 条` : ''}`)
    } catch (error: any) {
      message.error('全选操作失败: ' + (error.message || error))
    } finally {
      setLoading(false)
    }
  }

  // 删除缺陷记录
  const handleDeleteDefectRecord = async (defectRecordId: number, defectNumber: string) => {
    try {
      await defectApi.deleteDefectRecord(defectRecordId)
      message.success(`缺陷记录 ${defectNumber} 已删除`)
      
      // 从匹配结果中移除
      setMatchResults((prevResults) =>
        prevResults.filter((result) => result.defect_record_id !== defectRecordId)
      )
      
      // 从缺陷记录列表中移除
      setDefectRecords((prevRecords) =>
        prevRecords.filter((record) => record.id !== defectRecordId)
      )
    } catch (error: any) {
      message.error('删除失败: ' + (error.message || error))
    }
  }

  const handleOpenSaveModal = () => {
    if (matchResults.length === 0) {
      message.warning('暂无匹配结果可保存')
      return
    }
    const hasUnselected = matchResults.some((result) => !result.selected_workcard_id)
    if (hasUnselected) {
      message.warning('请先为所有缺陷选择候选工卡')
      return
    }
    metadataForm.resetFields()
    metadataForm.setFieldsValue({
      aircraft_number: currentDefectList?.aircraft_number || '',
      workcard_number: '',
      maintenance_level: '',
      aircraft_type: selectedWorkcardGroup?.aircraft_type || '',
      customer: ''
    })
    setSaveModalVisible(true)
  }

  const handleSaveBatch = async () => {
    try {
      const metadataValues = await metadataForm.validateFields()

      const items = matchResults.map((result, index) => {
        const selectedCandidate = result.candidates.find(
          (candidate) => candidate.id === result.selected_workcard_id
        )
        if (!selectedCandidate) {
          throw new Error(`缺陷 ${result.defect_number} 缺少已选候选工卡`)
        }
        return {
          defect_record_id: result.defect_record_id,
          defect_number: result.defect_number,
          description_cn: result.description_cn || '',
          description_en: result.description_en || '',
          workcard_number: selectedCandidate.workcard_number,
          selected_workcard_id: selectedCandidate.id,
          similarity_score: selectedCandidate.similarity_score ?? 0
        }
      })

      setSavingBatch(true)
      const payload = {
        metadata: {
          ...metadataValues,
          aircraft_number: metadataValues.aircraft_number.trim(),
          workcard_number: metadataValues.workcard_number.trim(),
          maintenance_level: metadataValues.maintenance_level.trim(),
          aircraft_type: metadataValues.aircraft_type.trim(),
          customer: metadataValues.customer.trim(),
          defect_list_id: currentDefectList?.id
        },
        items
      }

      const result = await importBatchApi.create(payload)
      setLatestBatchId(result.id)
      message.success('已保存到待导入工卡数据表')
      setSaveModalVisible(false)
    } catch (error: any) {
      if (error?.errorFields) {
        return
      }
      message.error(error?.message || '保存失败，请稍后再试')
    } finally {
      setSavingBatch(false)
    }
  }

  const getGroupTitle = (group: WorkCardGroup) => {
    const parts = []
    if (group.aircraft_number) parts.push(`飞机号: ${group.aircraft_number}`)
    if (group.aircraft_type) parts.push(`机型: ${group.aircraft_type}`)
    if (group.msn) parts.push(`MSN: ${group.msn}`)
    if (group.amm_ipc_eff) parts.push(`AMM/IPC EFF: ${group.amm_ipc_eff}`)
    return parts.length > 0 ? parts.join(' | ') : '未设置识别字段'
  }

  const defectColumns = [
    {
      title: '缺陷编号',
      dataIndex: 'defect_number',
      key: 'defect_number',
      width: 120,
    },
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      width: 200,
      ellipsis: true,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      width: 250,
      ellipsis: true,
    },
    {
      title: '系统',
      dataIndex: 'system',
      key: 'system',
      width: 120,
    },
    {
      title: '部件',
      dataIndex: 'component',
      key: 'component',
      width: 120,
    },
  ]

  const cleanedDataColumns = [
    {
      title: '缺陷编号',
      dataIndex: 'defect_number',
      key: 'defect_number',
      width: 120,
      fixed: 'left' as const,
      render: (text: string) => text || '-',
    },
    {
      title: '工卡描述（中文）',
      dataIndex: 'description_cn',
      key: 'description_cn',
      width: 300,
      ellipsis: true,
      render: (text: string) => text || '-',
    },
    {
      title: '工卡描述（英文）',
      dataIndex: 'description_en',
      key: 'description_en',
      width: 300,
      ellipsis: true,
      render: (text: string) => text || '-',
    },
    {
      title: '主区域',
      dataIndex: 'main_area',
      key: 'main_area',
      width: 120,
      render: (text: string) => text || '-',
    },
    {
      title: '主部件',
      dataIndex: 'main_component',
      key: 'main_component',
      width: 120,
      render: (text: string) => text || '-',
    },
    {
      title: '一级子部件',
      dataIndex: 'first_level_subcomponent',
      key: 'first_level_subcomponent',
      width: 150,
      render: (text: string) => text || '-',
    },
    {
      title: '二级子部件',
      dataIndex: 'second_level_subcomponent',
      key: 'second_level_subcomponent',
      width: 150,
      render: (text: string) => text || '-',
    },
    {
      title: '方位',
      dataIndex: 'orientation',
      key: 'orientation',
      width: 100,
      render: (text: string) => text || '-',
    },
    {
      title: '缺陷主体',
      dataIndex: 'defect_subject',
      key: 'defect_subject',
      width: 120,
      render: (text: string) => text || '-',
    },
    {
      title: '缺陷描述',
      dataIndex: 'defect_description',
      key: 'defect_description',
      width: 200,
      ellipsis: true,
      render: (text: string) => text || '-',
    },
    {
      title: '位置',
      dataIndex: 'location',
      key: 'location',
      width: 150,
      render: (text: string) => text || '-',
    },
    {
      title: '数量',
      dataIndex: 'quantity',
      key: 'quantity',
      width: 80,
      render: (text: string) => text || '-',
    },
  ]

  const matchResultColumns = [
    {
      title: '缺陷编号',
      dataIndex: 'defect_number',
      key: 'defect_number',
      width: 120,
      fixed: 'left' as const,
    },
    {
      title: '工卡描述（中文）',
      dataIndex: 'description_cn',
      key: 'description_cn',
      width: 300,
      ellipsis: true,
      render: (text: string) => text || '-',
    },
    {
      title: '工卡描述（英文）',
      dataIndex: 'description_en',
      key: 'description_en',
      width: 300,
      ellipsis: true,
      render: (text: string) => text || '-',
    },
    {
      title: '候选工卡',
      key: 'candidates',
      width: 600,
      render: (_: any, record: MatchResult) => (
        <Radio.Group
          name={`defect-${record.defect_record_id}`}
          value={record.selected_workcard_id}
          onChange={(e) => handleSelectWorkcard(record.defect_record_id, e.target.value)}
        >
          <Space direction="vertical" style={{ width: '100%' }}>
            {record.candidates.map((candidate) => (
              <Radio key={candidate.id} value={candidate.id}>
                <Space>
                  <Tag color="blue">工卡指令号: {candidate.workcard_number}</Tag>
                  <span>工卡描述: {candidate.description || '-'}</span>
                  <Tag color={candidate.similarity_score >= 80 ? 'green' : candidate.similarity_score >= 60 ? 'orange' : 'red'}>
                    相似度: {candidate.similarity_score.toFixed(1)}%
                  </Tag>
                </Space>
              </Radio>
            ))}
            {record.candidates.length === 0 && (
              <span style={{ color: '#999' }}>暂无候选工卡</span>
            )}
          </Space>
        </Radio.Group>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      fixed: 'right' as const,
      render: (_: any, record: MatchResult) => (
        <Popconfirm
          title="确定要删除这条缺陷记录吗？"
          description="删除后将无法恢复，相关的匹配结果和候选工卡也会被删除。"
          onConfirm={() => handleDeleteDefectRecord(record.defect_record_id, record.defect_number)}
          okText="确定"
          cancelText="取消"
          okButtonProps={{ danger: true }}
        >
          <Button type="link" danger size="small">
            删除
          </Button>
        </Popconfirm>
      ),
    },
  ]

  const handlePrevStep = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handleNextStep = () => {
    if (currentStep === 0 && defectRecords.length > 0) {
      setCurrentStep(1)
    } else if ((currentStep === 1 || currentStep === 2) && cleanedData.length > 0) {
      // 从步骤1或2跳转到步骤3（选择标准工卡数据表）
      setCurrentStep(3)
    } else if (currentStep === 3 && selectedWorkcardGroup) {
      // 从步骤3跳转到步骤4（匹配结果）
      // 注意：这里不会自动执行匹配，需要用户点击"开始匹配"按钮
      setCurrentStep(4)
    } else if (currentStep === 4) {
      // 已经是最后一步
      return
    }
  }

  const saveBatchDisabled =
    matchResults.length === 0 || matchResults.some((result) => !result.selected_workcard_id)

  return (
    <>
      <div style={{ padding: '24px', background: '#f0f2f5', minHeight: '100vh' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <Title level={2} style={{ margin: 0 }}>缺陷处理与匹配</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => {
            loadConfigurations()
            loadDefectLists()
            loadWorkcardGroups()
          }}>
            刷新
          </Button>
          <Button icon={<HomeOutlined />} onClick={() => navigate('/')}>
            返回首页
          </Button>
        </Space>
      </div>

      <Card style={{ marginBottom: '24px' }}>
        <Steps current={currentStep}>
          <Step title="上传缺陷清单" description="上传缺陷清单文件" />
          <Step title="选择索引数据表" description="选择用于清洗的索引数据" />
          <Step title="清洗缺陷数据" description="使用AI清洗缺陷数据" />
          <Step title="选择标准工卡数据表" description="选择匹配目标工卡数据表" />
          <Step title="匹配与选择" description="查看匹配结果并选择工卡" />
        </Steps>
      </Card>

      {/* 步骤1: 上传缺陷清单 */}
      {currentStep === 0 && (
        <Card title="上传缺陷清单" style={{ marginBottom: '24px' }}>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Upload
              accept=".xlsx,.xls"
              beforeUpload={handleUpload}
              showUploadList={false}
            >
              <Button icon={<UploadOutlined />} loading={uploading} type="primary" size="large">
                上传缺陷清单文件 (Excel)
              </Button>
            </Upload>
            <div style={{ color: '#999', fontSize: '14px' }}>
              提示：系统将自动从文件名提取飞机号信息
            </div>
            {currentDefectList && (
              <div style={{ marginTop: '16px' }}>
                <Tag color="blue">当前缺陷清单: {currentDefectList.title}</Tag>
                <Tag color="green">飞机号: {currentDefectList.aircraft_number}</Tag>
              </div>
            )}
            {defectRecords.length > 0 && (
              <div style={{ marginTop: '16px' }}>
                <Divider>已上传的缺陷记录 ({defectRecords.length} 条)</Divider>
                <Table
                  columns={defectColumns}
                  dataSource={defectRecords}
                  rowKey="id"
                  size="small"
                  pagination={{ pageSize: 10 }}
                />
              </div>
            )}
          </Space>
          <Divider />
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '16px' }}>
            <Button 
              icon={<LeftOutlined />}
              onClick={handlePrevStep}
              disabled={currentStep === 0}
            >
              上一步
            </Button>
            <Button 
              type="primary"
              icon={<RightOutlined />}
              onClick={handleNextStep}
              disabled={defectRecords.length === 0 || currentStep >= 4}
            >
              下一步
            </Button>
          </div>
        </Card>
      )}

      {/* 步骤2: 选择索引数据表并清洗 */}
      {(currentStep === 1 || currentStep === 2) && currentDefectList && defectRecords.length > 0 && (
        <Card title="选择索引数据表并清洗" style={{ marginBottom: '24px' }}>
          <Space direction="vertical" style={{ width: '100%' }}>
            <div>
              <div style={{ marginBottom: 8, color: '#666', fontSize: '14px' }}>
                请手动选择用于清洗缺陷数据的索引数据表（构型）。系统不会自动选择。
              </div>
              <Select
                style={{ width: 400 }}
                placeholder={loadingConfigurations ? "加载中..." : configurations.length === 0 ? "暂无可用构型，请先创建构型" : "请选择索引数据表（构型）"}
                value={selectedIndexConfig}
                onChange={(value) => {
                  setSelectedIndexConfig(value)
                  message.success(`已选择索引数据表: ${configurations.find(c => c.id === value)?.name || ''}`)
                }}
                loading={loadingConfigurations}
                disabled={loadingConfigurations || configurations.length === 0}
                notFoundContent={configurations.length === 0 ? "暂无可用构型配置" : null}
                allowClear
                showSearch
                optionFilterProp="children"
                filterOption={(input, option) =>
                  (option?.children as string)?.toLowerCase().includes(input.toLowerCase())
                }
              >
                {configurations.map(config => (
                  <Option key={config.id} value={config.id}>
                    {config.name} {config.aircraft_type ? `(${config.aircraft_type})` : ''} {config.msn ? `MSN: ${config.msn}` : ''}
                  </Option>
                ))}
              </Select>
              {configurations.length === 0 && (
                <div style={{ marginTop: 8, color: '#ff4d4f' }}>
                  <span>提示：请先在 </span>
                  <Button 
                    type="link" 
                    size="small" 
                    onClick={() => navigate('/configuration-index-data')}
                    style={{ padding: 0, height: 'auto' }}
                  >
                    构型管理页面
                  </Button>
                  <span> 创建构型配置并上传索引数据</span>
                </div>
              )}
              {selectedIndexConfig && (
                <div style={{ marginTop: 8 }}>
                  <Tag color="blue">已选择: {configurations.find(c => c.id === selectedIndexConfig)?.name || ''}</Tag>
                </div>
              )}
            </div>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Space>
                <Button
                  type="primary"
                  icon={<PlayCircleOutlined />}
                  onClick={() => handleClean()}
                  loading={cleaning}
                  disabled={!selectedIndexConfig || configurations.length === 0}
                >
                  清洗全部数据
                </Button>
                <Button
                  icon={<PlayCircleOutlined />}
                  onClick={() => handleClean(20)}
                  loading={cleaning}
                  disabled={!selectedIndexConfig || configurations.length === 0}
                >
                  测试清洗20条
                </Button>
              </Space>
              {cleaning && (
                <div style={{ width: '100%', marginTop: '16px' }}>
                  <Progress
                    percent={cleaningProgress.percent}
                    status={cleaningProgress.percent === 100 ? 'success' : 'active'}
                    format={(percent) => `${percent}%`}
                  />
                  <div style={{ marginTop: '8px', color: '#666', fontSize: '14px' }}>
                    {cleaningProgress.message}
                    {cleaningProgress.total > 0 && (
                      <span style={{ marginLeft: '8px' }}>
                        ({cleaningProgress.current} / {cleaningProgress.total})
                      </span>
                    )}
                  </div>
                </div>
              )}
            </Space>
            {cleanedData && cleanedData.length > 0 ? (
              <div style={{ marginTop: '24px' }}>
                <Divider>清洗后的数据 ({cleanedData.length} 条)</Divider>
                <Tag color="green" style={{ marginBottom: '16px' }}>清洗完成，可以进行下一步匹配</Tag>
                <Table
                  columns={cleanedDataColumns}
                  dataSource={cleanedData}
                  rowKey="id"
                  size="small"
                  scroll={{ x: 1500 }}
                  pagination={{
                    showSizeChanger: true,
                    showTotal: (total) => `共 ${total} 条清洗后的数据`,
                    pageSize: 10,
                  }}
                  locale={{
                    emptyText: <Empty description="暂无清洗后的数据" />
                  }}
                />
              </div>
            ) : (
              cleanedData && cleanedData.length === 0 && (
                <div style={{ marginTop: '24px', color: '#999' }}>
                  <Tag color="orange">暂无清洗后的数据，请先执行清洗操作</Tag>
                </div>
              )
            )}
          </Space>
          <Divider />
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '16px' }}>
            <Button 
              icon={<LeftOutlined />}
              onClick={handlePrevStep}
              disabled={currentStep === 0}
            >
              上一步
            </Button>
            <Button 
              type="primary"
              icon={<RightOutlined />}
              onClick={handleNextStep}
              disabled={!cleanedData || cleanedData.length === 0 || currentStep >= 4}
            >
              下一步
            </Button>
          </div>
        </Card>
      )}

      {/* 步骤3: 选择标准工卡数据表并匹配 */}
      {currentStep >= 3 && cleanedData.length > 0 && (
        <Card title="选择标准工卡数据表并匹配" style={{ marginBottom: '24px' }}>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Select
              style={{ width: 600 }}
              placeholder="选择标准工卡数据表"
              value={selectedWorkcardGroup ? `${selectedWorkcardGroup.aircraft_number || ''}_${selectedWorkcardGroup.configuration_id}` : null}
              onChange={(value) => {
                const group = workcardGroups.find(g => `${g.aircraft_number || ''}_${g.configuration_id}` === value)
                setSelectedWorkcardGroup(group || null)
              }}
              showSearch
              filterOption={(input, option) =>
                (option?.children as string)?.toLowerCase().includes(input.toLowerCase())
              }
            >
              {workcardGroups.map(group => (
                <Option key={`${group.aircraft_number || ''}_${group.configuration_id}`} value={`${group.aircraft_number || ''}_${group.configuration_id}`}>
                  {getGroupTitle(group)} (工卡数: {group.count})
                </Option>
              ))}
            </Select>
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={handleMatch}
              loading={matching}
              disabled={!selectedWorkcardGroup}
            >
              开始匹配
            </Button>
            
            {/* 匹配进度展示 */}
            {matchingProgress.status === 'processing' && (
              <Card style={{ marginTop: '16px', background: '#f5f5f5' }}>
                <div style={{ marginBottom: '16px' }}>
                  <Title level={5}>匹配进度</Title>
                </div>
                
                {/* 进度条 */}
                <Progress
                  percent={matchingProgress.total > 0 
                    ? Math.round((matchingProgress.completed / matchingProgress.total) * 100) 
                    : 0}
                  status="active"
                  strokeColor={{
                    '0%': '#108ee9',
                    '100%': '#87d068',
                  }}
                />
                
                {/* 详细信息 */}
                <div style={{ marginTop: '16px', fontSize: '14px', color: '#666' }}>
                  <Row gutter={16}>
                    <Col span={12}>
                      <div>总记录数: {matchingProgress.total}</div>
                      <div>已完成: {matchingProgress.completed}</div>
                      <div>剩余: {matchingProgress.total - matchingProgress.completed}</div>
                    </Col>
                    <Col span={12}>
                      <div>匹配成功: {matchingProgress.matchedCount}</div>
                      <div>失败: {matchingProgress.failedCount}</div>
                      <div>候选工卡总数: {matchingProgress.candidatesFound}</div>
                      {matchingProgress.current && (
                        <div style={{ marginTop: '8px', color: '#1890ff' }}>
                          当前处理: {matchingProgress.current.defect_number} - {matchingProgress.current.description}
                        </div>
                      )}
                    </Col>
                  </Row>
                </div>
              </Card>
            )}
          </Space>
          <Divider />
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '16px' }}>
            <Button 
              icon={<LeftOutlined />}
              onClick={handlePrevStep}
              disabled={currentStep === 0}
            >
              上一步
            </Button>
            <Button 
              type="primary"
              icon={<RightOutlined />}
              onClick={handleNextStep}
              disabled={!selectedWorkcardGroup || currentStep >= 4}
            >
              下一步
            </Button>
          </div>
        </Card>
      )}

      {/* 步骤4: 显示匹配结果 */}
      {currentStep >= 3 && matchResults.length > 0 && (
        <Card title="匹配结果" style={{ marginBottom: '24px' }}>
          <Table
            columns={matchResultColumns}
            dataSource={matchResults}
            rowKey="defect_record_id"
            scroll={{ x: 1000 }}
            pagination={{
              showSizeChanger: true,
              showTotal: (total) => `共 ${total} 条缺陷记录`,
              pageSize: 10,
            }}
            locale={{
              emptyText: <Empty description="暂无匹配结果" />
            }}
          />
          <Divider />
          <Space style={{ marginBottom: 24 }}>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={handleOpenSaveModal}
              disabled={saveBatchDisabled}
            >
              保存到待导入工卡数据表
            </Button>
            <Button
              onClick={handleSelectAllHighest}
              disabled={matchResults.length === 0 || loading}
              loading={loading}
            >
              全选最高评分
            </Button>
            <Button
              icon={<RightOutlined />}
              onClick={() =>
                navigate('/defect-processing/batch-open', {
                  state: latestBatchId ? { importBatchId: latestBatchId } : undefined
                })
              }
              disabled={matchResults.length === 0}
            >
              前往批量导入调试
            </Button>
          </Space>
          <Divider />
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '16px' }}>
            <Button 
              icon={<LeftOutlined />}
              onClick={handlePrevStep}
              disabled={currentStep === 0}
            >
              上一步
            </Button>
            <div />
          </div>
        </Card>
      )}
      </div>

      <Modal
        title="保存到待导入工卡数据表"
        open={saveModalVisible}
        onCancel={() => setSaveModalVisible(false)}
        onOk={handleSaveBatch}
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
            rules={[{ required: true, message: '请输入机型' }]}
          >
            <Input placeholder="请输入机型" />
          </Form.Item>
          <Form.Item
            label="客户"
            name="customer"
            rules={[{ required: true, message: '请输入客户信息' }]}
          >
            <Input placeholder="请输入客户信息" />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}

export default DefectProcessing

