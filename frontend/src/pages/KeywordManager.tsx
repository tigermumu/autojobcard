import React, { useEffect, useMemo, useState } from 'react'
import {
  Button, Card, Form, Input, message, Select, Space, Table, Tag, Upload, Typography,
  Layout, Menu, Row, Col, Descriptions, Modal, Popconfirm
} from 'antd'
import type { UploadProps } from 'antd'
import {
  UploadOutlined, ReloadOutlined, HomeOutlined,
  ReadOutlined, FileTextOutlined, BugOutlined, SafetyCertificateOutlined,
  ImportOutlined, PlayCircleOutlined,
  DownloadOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import * as XLSX from 'xlsx'

import { configApi, Configuration } from '../services/configApi'
import {
  localwashApi, KeywordDictDetail, KeywordDictSummary,
  LocalCleanedWorkcard, LocalCleanedDefect, LocalMatchResult,
  LocalMatchStatsResponse
} from '../services/localwashApi'
import { defectApi, DefectList } from '../services/defectApi'

const { Option } = Select
const { Title, Text } = Typography
const { Content, Sider } = Layout

type GroupRow = {
  key: string
  main_component: string
  sub_keywords: string
  location_keywords: string
  orientation_keywords: string
}

// Helper: Parse Excel to JSON
const parseExcel = (file: File): Promise<any[]> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const data = e.target?.result
        const workbook = XLSX.read(data, { type: 'binary' })
        const sheetName = workbook.SheetNames[0]
        const sheet = workbook.Sheets[sheetName]
        const json = XLSX.utils.sheet_to_json(sheet)
        resolve(json)
      } catch (err) {
        reject(err)
      }
    }
    reader.onerror = (err) => reject(err)
    reader.readAsBinaryString(file)
  })
}

const KeywordManager: React.FC = () => {
  const navigate = useNavigate()
  const [activeMenu, setActiveMenu] = useState('dict')

  // --- Global State ---
  const [configurations, setConfigurations] = useState<Configuration[]>([])
  const [selectedConfigurationId, setSelectedConfigurationId] = useState<number | null>(null)

  const [dicts, setDicts] = useState<KeywordDictSummary[]>([])
  const [selectedDictId, setSelectedDictId] = useState<number | null>(null)
  const [dictDetail, setDictDetail] = useState<KeywordDictDetail | null>(null)

  // Loaders
  const [loadingConfigs, setLoadingConfigs] = useState(false)
  const [loadingDicts, setLoadingDicts] = useState(false)
  const [loadingDetail, setLoadingDetail] = useState(false)

  // --- 1. Dictionary State ---
  const [importDictForm] = Form.useForm()

  // --- 2. Workcards State ---
  const [workcardsList, setWorkcardsList] = useState<LocalCleanedWorkcard[]>([])
  const [workcardsTotal, setWorkcardsTotal] = useState(0)
  const [loadingWorkcards, setLoadingWorkcards] = useState(false)
  const [workcardSource, setWorkcardSource] = useState<'upload' | 'history'>('upload')
  const [previewWorkcards, setPreviewWorkcards] = useState<LocalCleanedWorkcard[]>([])  // 清洗预览结果
  const [showSaveModal, setShowSaveModal] = useState(false)  // 保存对话框
  const [cabinLayoutInput, setCabinLayoutInput] = useState<string>('')  // 保存时输入的客舱布局
  const [selectedCabinLayout, setSelectedCabinLayout] = useState<string | null>(null)  // 查看时筛选的客舱布局
  const [availableCabinLayouts, setAvailableCabinLayouts] = useState<string[]>([])  // 可用的客舱布局列表

  // --- 3. Defects State ---
  const [activeDefectListId, setActiveDefectListId] = useState<number | null>(null)
  const [defectLists, setDefectLists] = useState<DefectList[]>([])
  const [cleanedDefects, setCleanedDefects] = useState<LocalCleanedDefect[]>([])
  const [loadingDefects, setLoadingDefects] = useState(false)
  const [availableCleanedDefectLists, setAvailableCleanedDefectLists] = useState<{ id: number; title: string }[]>([])

  // --- 4. Matching State ---
  const [matchResults, setMatchResults] = useState<LocalMatchResult[]>([])
  const [loadingMatch, setLoadingMatch] = useState(false)
  const [matchStats, setMatchStats] = useState<LocalMatchStatsResponse | null>(null)


  // ================= INIT =================
  useEffect(() => {
    loadConfigurations()
  }, [])

  useEffect(() => {
    if (selectedConfigurationId) {
      loadDicts(selectedConfigurationId)
      loadDefectLists(selectedConfigurationId)
    } else {
      setDicts([])
      setDefectLists([])
      setDictDetail(null)
    }
  }, [selectedConfigurationId])

  useEffect(() => {
    if (selectedDictId) {
      loadDictDetail(selectedDictId)
    } else {
      setDictDetail(null)
    }
  }, [selectedDictId])

  useEffect(() => {
    if (activeMenu === 'match' && activeDefectListId && selectedConfigurationId && selectedDictId) {
      loadMatchStats()
    }
  }, [activeMenu, activeDefectListId, selectedConfigurationId, selectedDictId])


  // ================= API CALLS =================
  const loadConfigurations = async () => {
    setLoadingConfigs(true)
    try {
      const data = await configApi.getAll()
      setConfigurations(data as Configuration[])
    } catch (e: any) {
      message.error('加载构型失败: ' + (e.message || '未知错误'))
    } finally {
      setLoadingConfigs(false)
    }
  }

  const loadDicts = async (confId: number) => {
    setLoadingDicts(true)
    try {
      const data = await localwashApi.listDicts(confId)
      setDicts(data)
      if (data.length > 0) setSelectedDictId(data[0].id)
      else {
        setSelectedDictId(null)
        setMatchResults([]) // clear results if no dict
      }
    } catch (e: any) {
      message.error('加载词典列表失败')
    } finally {
      setLoadingDicts(false)
    }
  }

  const loadDictDetail = async (id: number) => {
    setLoadingDetail(true)
    try {
      const data = await localwashApi.getDict(id)
      setDictDetail(data)
    } catch (e: any) {
      message.error('加载词典详情失败')
    } finally {
      setLoadingDetail(false)
    }
  }

  const loadDefectLists = async (confId: number) => {
    try {
      const list = await defectApi.getLists({ configuration_id: confId })
      setDefectLists(list)
      // Auto select latest if available
      if (list.length > 0) {
        // sort by created_at desc
        const sorted = list.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        setActiveDefectListId(sorted[0].id)
      } else {
        setActiveDefectListId(null)
      }
    } catch (e) {
      console.error(e)
    }
  }


  // ================= MODULE 1: DICTIONARY =================
  const uploadDictProps: UploadProps = {
    accept: '.xlsx,.xls,.csv',
    showUploadList: false,
    customRequest: async (options) => {
      const { file, onSuccess, onError } = options
      try {
        const values = await importDictForm.validateFields()
        if (!selectedConfigurationId) {
          message.warning('请先选择构型')
          return
        }
        const res = await localwashApi.importDict({
          configuration_id: selectedConfigurationId,
          version: values.version,
          remark: values.remark,
          file: file as File,
        })
        
        // 从remark中提取去重信息
        const remark = res.remark || ""
        const dedupMatch = remark.match(/\[去重\]\s*去重前:\s*(\d+)\s*条，去重后:\s*(\d+)\s*条，去除重复:\s*(\d+)\s*条/)
        let successMsg = `导入成功：版本 ${res.version}，条目 ${res.items?.length ?? 0} 条`
        if (dedupMatch) {
          const [, before, , removed] = dedupMatch
          successMsg += `（去重前: ${before} 条，去除重复: ${removed} 条）`
        }
        
        message.success(successMsg)
        await loadDicts(selectedConfigurationId)
        onSuccess?.('ok', {} as any)
      } catch (e: any) {
        message.error('导入失败: ' + (e.message || '未知错误'))
        onError?.(e)
      }
    }
  }

  const dictGroupedRows: GroupRow[] = useMemo(() => {
    if (!dictDetail) return []
    const items = dictDetail.items || []
    const mains = items.filter((i) => i.dimension === 'main').map((i) => i.keyword).filter(Boolean)
    const mainSet = new Set<string>(mains)
    const byMain: Record<string, any> = {}
    for (const m of mains) byMain[m] = { sub: [], location: [], orientation: [] }

    for (const it of items) {
      if (['sub', 'location', 'orientation'].includes(it.dimension)) {
        const mc = (it.main_component || '').trim()
        if (mc && mainSet.has(mc)) {
          byMain[mc][it.dimension].push(it.keyword)
        }
      }
    }
    const safeJoin = (arr: string[]) => Array.from(new Set(arr)).join(', ')
    return mains.map(m => ({
      key: m,
      main_component: m,
      sub_keywords: safeJoin(byMain[m].sub),
      location_keywords: safeJoin(byMain[m].location),
      orientation_keywords: safeJoin(byMain[m].orientation),
    }))
  }, [dictDetail])

  // ================= MODULE 2: WORKCARDS =================
  const handleUploadWorkcards = async (file: File) => {
    if (!selectedDictId) return message.error('请先选择词典版本')
    try {
      setLoadingWorkcards(true)
      const json = await parseExcel(file)

      // 调试信息：显示实际的列名
      if (json.length > 0) {
        const actualColumns = Object.keys(json[0])
        console.log('Excel实际列名:', actualColumns)
      }

      // Normalize keys - 优先识别标准列名，支持全角和半角括号
      const rows = json.map((r: any) => {
        // 工卡号：优先识别"工卡指令号"
        const workcard_number = r['工卡指令号']
          || r['workcard_number']
          || r['工卡号']
          || r['Workcard Number']
          || r['WORKCARD_NUMBER']
          || r['工卡编号']
          || ''

        // 英文描述：优先识别"工卡描述(英文)"和"工卡描述（英文）"
        const description_en = r['工卡描述(英文)']
          || r['工卡描述（英文）']
          || r['description_en']
          || r['英文描述']
          || r['Description']
          || r['DESCRIPTION']
          || r['描述']
          || r['工卡描述']
          || ''

        // 中文描述：优先识别"工卡描述(中文)"和"工卡描述（中文）"
        const description_cn = r['工卡描述(中文)']
          || r['工卡描述（中文）']
          || r['description_cn']
          || r['中文描述']
          || r['中文']
          || r['描述（中文）']
          || r['描述(中文)']
          || ''

        return {
          workcard_number,
          description_en,
          description_cn
        }
      }).filter(r => r.workcard_number && r.description_en)

      if (rows.length === 0) {
        const sampleColumns = json.length > 0 ? Object.keys(json[0]).join(', ') : '无'
        message.error(
          `未解析到有效数据！\n` +
          `需要的列名：\n` +
          `  • 工卡指令号（必需）\n` +
          `  • 工卡描述(英文) 或 工卡描述（英文）（必需）\n` +
          `  • 工卡描述(中文) 或 工卡描述（中文）（可选）\n` +
          `实际找到的列名：${sampleColumns}\n` +
          `请确保Excel文件包含这些列，且数据行不为空。`,
          10  // 显示10秒
        )
        setLoadingWorkcards(false)
        return
      }

      // 调用清洗预览API（不保存到数据库）
      const res = await localwashApi.cleanWorkcardsUpload({
        dict_id: selectedDictId,
        rows
      })

      if (res.success) {
        setPreviewWorkcards(res.cleaned_data)
        message.success(`清洗完成：共 ${res.total} 条，成功 ${res.cleaned} 条`)
        setShowSaveModal(true)  // 显示保存对话框
      }
    } catch (e: any) {
      message.error('处理失败: ' + e.message)
    } finally {
      setLoadingWorkcards(false)
    }
  }

  // 保存清洗结果到数据库
  const handleSaveCleanedWorkcards = async () => {
    if (!selectedDictId || previewWorkcards.length === 0) return

    try {
      setLoadingWorkcards(true)
      const res = await localwashApi.saveCleanWorkcardsUpload({
        dict_id: selectedDictId,
        rows: previewWorkcards.map(w => ({
          workcard_number: w.workcard_number,
          description_en: w.description_en,
          description_cn: w.description_cn,
        })),
        cabin_layout: cabinLayoutInput || null  // 使用对话框中输入的客舱布局
      })

      if (res.success) {
        message.success(`保存成功：${res.cleaned} 条工卡已保存`)
        setShowSaveModal(false)
        setCabinLayoutInput('')
        setPreviewWorkcards([])
        setWorkcardSource('upload')
        loadCleanWorkcards(1, 20)
      }
    } catch (e: any) {
      message.error('保存失败: ' + e.message)
    } finally {
      setLoadingWorkcards(false)
    }
  }

  // Handle "History Clean"
  const handleHistoryClean = async () => {
    if (!selectedConfigurationId || !selectedDictId) return
    setLoadingWorkcards(true)
    try {
      const res = await localwashApi.cleanWorkcards({
        configuration_id: selectedConfigurationId,
        dict_id: selectedDictId,
        cabin_layout: null  // 历史清洗不使用cabin_layout，直接清洗到数据库
      })
      if (res.success) {
        message.success(`历史工卡清洗完成: ${res.cleaned} 条`)
        loadCleanWorkcards(1, 20)
      }
    } catch (e: any) {
      message.error('清洗失败: ' + e.message)
    } finally {
      setLoadingWorkcards(false)
    }
  }

  const loadCleanWorkcards = async (page = 1, pageSize = 20) => {
    if (!selectedConfigurationId) return
    setLoadingWorkcards(true)
    try {
      const skip = (page - 1) * pageSize
      const res = await localwashApi.getCleanWorkcards({
        configuration_id: selectedConfigurationId,
        dict_id: selectedDictId,
        skip,
        limit: pageSize,
        source: workcardSource,
        cabin_layout: selectedCabinLayout || null,  // 使用选中的客舱布局筛选
      })
      if (res.success) {
        setWorkcardsList(res.cleaned_data)
        setWorkcardsTotal(res.total)
      }
    } catch (e: any) {
      message.error(e.message)
    } finally {
      setLoadingWorkcards(false)
    }
  }

  // 导出已清洗的历史工卡客舱部件
  const handleExportCleanedWorkcards = async () => {
    if (!selectedConfigurationId) {
      message.error('请先选择构型')
      return
    }
    try {
      message.loading({ content: '正在导出...', key: 'exporting' })
      await localwashApi.exportCleanedWorkcards({
        configuration_id: selectedConfigurationId,
        dict_id: selectedDictId,
        source: workcardSource,
        cabin_layout: selectedCabinLayout
      })
      message.success({ content: '导出成功', key: 'exporting' })
    } catch (e: any) {
      message.error({ content: '导出失败: ' + e.message, key: 'exporting' })
    }
  }

  // Re-fetch when tab active
  useEffect(() => {
    if (activeMenu === 'workcards' && selectedConfigurationId) {
      loadCleanWorkcards()
      loadAvailableCabinLayouts()  // 加载可用布局列表
    }
  }, [activeMenu, selectedConfigurationId, selectedDictId, workcardSource, selectedCabinLayout])  // 添加 selectedCabinLayout 依赖

  // 加载可用的客舱布局列表
  const loadAvailableCabinLayouts = async () => {
    if (!selectedConfigurationId) return
    try {
      const res = await localwashApi.getAvailableCabinLayouts({
        configuration_id: selectedConfigurationId,
        source: workcardSource
      })
      setAvailableCabinLayouts(res.cabin_layouts || [])
    } catch (e: any) {
      console.error('获取客舱布局列表失败:', e)
    }
  }

  // 加载已执行本地清洗的缺陷清单列表
  const loadAvailableCleanedDefectLists = async () => {
    if (!selectedConfigurationId) return
    try {
      const res = await localwashApi.getAvailableCleanedDefectLists({
        configuration_id: selectedConfigurationId,
        dict_id: selectedDictId || undefined
      })
      if (res.success) {
        setAvailableCleanedDefectLists(res.defect_lists || [])
      }
    } catch (e) {
      console.error('获取已清洗缺陷清单列表失败:', e)
    }
  }

  // 加载指定清单的已保存清洗结果
  const loadCleanedDefectsByListId = async (listId: number) => {
    if (!selectedConfigurationId) return
    try {
      setLoadingDefects(true)
      const res = await localwashApi.getCleanedDefects({
        defect_list_id: listId,
        configuration_id: selectedConfigurationId,
        dict_id: selectedDictId || undefined
      })
      if (res.success) {
        setCleanedDefects(res.cleaned_data)
        setActiveDefectListId(listId)
      }
    } catch (e: any) {
      message.error('加载清洗结果失败: ' + e.message)
    } finally {
      setLoadingDefects(false)
    }
  }

  useEffect(() => {
    if (selectedConfigurationId) {
      loadAvailableCabinLayouts()
      loadAvailableCleanedDefectLists()
    }
  }, [selectedConfigurationId, workcardSource, selectedDictId])


  // ================= MODULE 3: DEFECTS =================
  const handleUploadDefect = async (file: File) => {
    if (!selectedConfigurationId) return message.error('请先选择飞机构型')
    try {
      setLoadingDefects(true)
      // Use uploaded file name as the defect list title
      const fileNameWithoutExt = file.name.replace(/\.(xlsx?|csv)$/i, '')
      const title = fileNameWithoutExt || `缺陷清单 ${new Date().toISOString().slice(0, 16).replace('T', ' ')}`

      const res = await defectApi.createList({
        aircraft_number: selectedConfigurationId.toString(),
        title,
        description: `从文件 ${file.name} 导入`,
        configuration_id: selectedConfigurationId
      })

      const uploadRes = await defectApi.uploadDefectData(res.id, file)

      if (uploadRes.imported_count > 0) {
        message.success(`成功导入 ${uploadRes.imported_count} 条缺陷数据`)
        await loadDefectLists(selectedConfigurationId)
        setActiveDefectListId(res.id)
      } else {
        message.warning('没有成功导入任何数据')
      }
    } catch (e: any) {
      message.error('上传失败: ' + e.message)
    } finally {
      setLoadingDefects(false)
    }
  }

  const handleCleanDefects = async () => {
    if (!activeDefectListId || !selectedConfigurationId || !selectedDictId) {
      return message.warning('缺少必要参数 (缺陷清单/构型/词典)')
    }
    setLoadingDefects(true)
    try {
      const res = await localwashApi.cleanDefects({
        defect_list_id: activeDefectListId,
        configuration_id: selectedConfigurationId,
        dict_id: selectedDictId
      })
      if (res.success) {
        message.success(`清洗完成: ${res.cleaned} 条`)
        setCleanedDefects(res.cleaned_data)
        loadAvailableCleanedDefectLists() // 刷新已清洗列表
      }
    } catch (e: any) {
      message.error('清洗失败: ' + e.message)
    } finally {
      setLoadingDefects(false)
    }
  }

  // ================= MODULE 4: MATCHING =================
  const handleMatch = async () => {
    if (!activeDefectListId || !selectedConfigurationId || !selectedDictId) {
      return message.warning('请先并在“新增缺陷”中选择一个缺陷清单')
    }
    setLoadingMatch(true)
    try {
      const res = await localwashApi.matchDefects({
        defect_list_id: activeDefectListId,
        configuration_id: selectedConfigurationId,
        dict_id: selectedDictId,
        source: workcardSource,
        cabin_layout: selectedCabinLayout
      })
      if (res.success) {
        message.success('匹配完成')
        setMatchResults(res.results)
        loadMatchStats()
      }
    } catch (e: any) {
      message.error('匹配失败: ' + e.message)
    } finally {
      setLoadingMatch(false)
    }
  }

  const loadMatchStats = async () => {
    if (!activeDefectListId || !selectedConfigurationId || !selectedDictId) return
    try {
      const stats = await localwashApi.getMatchStats({
        defect_list_id: activeDefectListId,
        configuration_id: selectedConfigurationId,
        dict_id: selectedDictId,
        cabin_layout: selectedCabinLayout
      })
      setMatchStats(stats)
    } catch (e) {
      console.error('Failed to load match stats', e)
    }
  }

  const handleExport = async () => {
    if (!activeDefectListId || !selectedConfigurationId || !selectedDictId) return
    try {
      message.loading({ content: '正在导出...', key: 'exporting' })
      await localwashApi.exportMatches({
        defect_list_id: activeDefectListId,
        configuration_id: selectedConfigurationId,
        dict_id: selectedDictId,
        cabin_layout: selectedCabinLayout
      })
      message.success({ content: '导出成功', key: 'exporting' })
    } catch (e: any) {
      message.error({ content: '导出失败: ' + e.message, key: 'exporting' })
    }
  }
  const handleDeleteLayout = async (layout: string) => {
    if (!selectedConfigurationId) return
    try {
      const res = await localwashApi.deleteCabinLayout({
        configuration_id: selectedConfigurationId,
        cabin_layout: layout,
        source: workcardSource
      })
      if (res.success) {
        message.success('布局数据已删除')
        if (selectedCabinLayout === layout) {
          setSelectedCabinLayout(null)
          setWorkcardsList([])
        }
        loadAvailableCabinLayouts()
      }
    } catch (e: any) {
      message.error('删除失败: ' + e.message)
    }
  }

  const handleDeleteCleanedList = async (listId: number) => {
    if (!selectedConfigurationId) return
    try {
      const res = await localwashApi.deleteCleanedDefectList({
        defect_list_id: listId,
        configuration_id: selectedConfigurationId,
        dict_id: selectedDictId || undefined
      })
      if (res.success) {
        message.success('清洗结果已删除')
        if (activeDefectListId === listId) {
          setCleanedDefects([])
        }
        loadAvailableCleanedDefectLists()
      }
    } catch (e: any) {
      message.error('删除失败: ' + e.message)
    }
  }


  // ================= RENDER HELPERS =================

  // Render: 1. Dictionary
  const renderDictionary = () => {
    const statusKws = dictDetail?.items.filter(i => i.dimension === 'status').map(i => i.keyword).join(', ')
    const actionKws = dictDetail?.items.filter(i => i.dimension === 'action').map(i => i.keyword).join(', ')

    return (
      <Space direction="vertical" style={{ width: '100%' }}>
        <Card title="导入词典" size="small">
          <Form form={importDictForm} layout="inline" initialValues={{ version: new Date().toISOString().slice(0, 10) }}>
            <Form.Item label="Version" name="version" rules={[{ required: true }]}>
              <Input placeholder="e.g. 2025-01-01" />
            </Form.Item>
            <Form.Item label="Remark" name="remark">
              <Input placeholder="Optional" />
            </Form.Item>
            <Form.Item>
              <Upload {...uploadDictProps}>
                <Button icon={<ImportOutlined />} style={{ color: '#13c2c2', borderColor: '#13c2c2' }}>上传 Excel/CSV</Button>
              </Upload>
            </Form.Item>
          </Form>
        </Card>

        {selectedDictId && (
          <Descriptions bordered size="small" column={1}>
            <Descriptions.Item label="Status Keywords">{statusKws || '-'}</Descriptions.Item>
            <Descriptions.Item label="Action Keywords">{actionKws || '-'}</Descriptions.Item>
          </Descriptions>
        )}

        <Table
          dataSource={dictGroupedRows}
          loading={loadingDetail}
          columns={[
            { title: '主部件 (Main)', dataIndex: 'main_component', render: t => <Tag color="cyan">{t}</Tag> },
            { title: '子部件 (Sub)', dataIndex: 'sub_keywords' },
            { title: '位置 (Location)', dataIndex: 'location_keywords' },
            { title: '方向 (Orientation)', dataIndex: 'orientation_keywords' },
          ]}
          pagination={{ pageSize: 15 }}
        />
      </Space>
    )
  }

  // Render: 2. Workcards
  const renderWorkcards = () => (
    <Space direction="vertical" style={{ width: '100%' }}>
      {/* 客舱布局列表卡片 */}
      {availableCabinLayouts.length > 0 && (
        <Card size="small" title="已保存的客舱布局">
          <Space wrap>
            {availableCabinLayouts.map(layout => (
              <Popconfirm
                key={layout}
                title="确定要删除该布局及其所有关联结果吗？"
                onConfirm={() => handleDeleteLayout(layout)}
                okText="确定"
                cancelText="取消"
              >
                <Tag
                  closable
                  onClose={(e) => { e.preventDefault(); e.stopPropagation(); }}
                  color={selectedCabinLayout === layout ? 'blue' : 'default'}
                  style={{ cursor: 'pointer', fontSize: 14, padding: '4px 12px' }}
                  onClick={() => setSelectedCabinLayout(selectedCabinLayout === layout ? null : layout)}
                >
                  {layout}
                </Tag>
              </Popconfirm>
            ))}
            {selectedCabinLayout && (
              <Button
                size="small"
                type="link"
                onClick={() => setSelectedCabinLayout(null)}
              >
                清除筛选
              </Button>
            )}
          </Space>
        </Card>
      )}

      <Card size="small">
        <Space>
          {/* 默认只使用上传库 (upload) */}
          <div style={{ fontWeight: 'bold', color: '#666', marginRight: 8 }}>当前目标：已清洗上传工卡 (Upload)</div>

          {workcardSource === 'upload' && (
            <Upload
              showUploadList={false}
              accept=".xlsx,.xls"
              beforeUpload={(file) => { handleUploadWorkcards(file); return false; }}
            >
              <Button
                type="primary"
                icon={<UploadOutlined />}
                loading={loadingWorkcards}
                style={{ background: '#13c2c2', borderColor: '#13c2c2' }}
              >
                上传并清洗
              </Button>
            </Upload>
          )}

          {workcardSource === 'history' && (
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={handleHistoryClean}
              loading={loadingWorkcards}
              style={{ background: '#13c2c2', borderColor: '#13c2c2' }}
            >
              执行全量清洗 (History)
            </Button>
          )}

          <Input
            placeholder="筛选客舱布局"
            value={selectedCabinLayout || ''}
            onChange={e => setSelectedCabinLayout(e.target.value || null)}
            style={{ width: 200 }}
            allowClear
          />

          <Button icon={<ReloadOutlined />} onClick={() => loadCleanWorkcards()}>刷新列表</Button>

          <Button 
            icon={<DownloadOutlined />} 
            onClick={handleExportCleanedWorkcards}
            disabled={!selectedConfigurationId || workcardsTotal === 0}
          >
            导出已清洗工卡
          </Button>

          {selectedCabinLayout && (
            <Tag color="blue" closable onClose={() => setSelectedCabinLayout(null)}>
              布局: {selectedCabinLayout}
            </Tag>
          )}
        </Space>
      </Card>

      <Table
        size="small"
        loading={loadingWorkcards}
        columns={[
          { title: 'Workcard No', dataIndex: 'workcard_number', width: 120, render: t => <Tag color="cyan">{t}</Tag> },
          { title: 'Main', dataIndex: 'main_component', width: 120, render: t => t ? <Tag>{t}</Tag> : '-' },
          { title: 'Sub', dataIndex: 'sub_component', width: 150 },
          { title: 'Loc', dataIndex: 'location', width: 80 },
          { title: 'Ori', dataIndex: 'orientation', width: 80 },
          { title: 'Status', dataIndex: 'status', width: 100 },
          { title: 'Action', dataIndex: 'action', width: 100 },
          { title: 'Description (EN)', dataIndex: 'description_en', ellipsis: true },
        ]}
        dataSource={workcardsList}
        rowKey={workcardSource === 'upload' ? 'workcard_number' : 'id'}
        pagination={{
          total: workcardsTotal,
          onChange: (p, s) => loadCleanWorkcards(p, s)
        }}
      />

      <Modal
        title="保存清洗结果"
        open={showSaveModal}
        onOk={handleSaveCleanedWorkcards}
        onCancel={() => {
          setShowSaveModal(false)
          setCabinLayoutInput('')
          setPreviewWorkcards([])
        }}
        okText="保存"
        cancelText="取消"
        confirmLoading={loadingWorkcards}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>
            <strong>清洗成功：</strong> {previewWorkcards.length} 条工卡
          </div>
          <div>
            <label>客舱布局名称（用于区分不同配置）：</label>
            <Input
              placeholder="例如：EK标准两舱布局、EK三舱豪华布局"
              value={cabinLayoutInput}
              onChange={e => setCabinLayoutInput(e.target.value)}
              style={{ marginTop: 8 }}
              allowClear
            />
            <div style={{ marginTop: 8, color: '#666', fontSize: 12 }}>
              提示：不同布局的工卡数据会分别保存，互不影响。留空则保存为默认布局。
            </div>
          </div>
        </Space>
      </Modal>
    </Space>
  )

  // Render: 3. Defects
  const renderDefects = () => (
    <Space direction="vertical" style={{ width: '100%' }}>
      {/* 已完成清洗的缺陷清单卡片 */}
      {availableCleanedDefectLists.length > 0 && (
        <Card size="small" title="已执行本地清洗的缺陷清单">
          <Space wrap>
            {availableCleanedDefectLists.map(list => (
              <Popconfirm
                key={list.id}
                title="确定要删除该清单的清洗结果及其所有关联匹配吗？"
                onConfirm={() => handleDeleteCleanedList(list.id)}
                okText="确定"
                cancelText="取消"
              >
                <Tag
                  closable
                  onClose={(e) => { e.preventDefault(); e.stopPropagation(); }}
                  color={activeDefectListId === list.id ? 'orange' : 'default'}
                  style={{ cursor: 'pointer', fontSize: 14, padding: '4px 12px' }}
                  onClick={() => loadCleanedDefectsByListId(list.id)}
                >
                  {list.title}
                </Tag>
              </Popconfirm>
            ))}
            {activeDefectListId && (
              <Button
                size="small"
                type="link"
                onClick={() => {
                  setActiveDefectListId(null)
                  setCleanedDefects([])
                }}
              >
                清除选择
              </Button>
            )}
          </Space>
        </Card>
      )}

      <Card size="small">
        <Row gutter={16} align="middle">
          <Col>
            <Select
              style={{ width: 300 }}
              placeholder="选择缺陷清单"
              value={activeDefectListId}
              onChange={setActiveDefectListId}
            >
              {defectLists.map(l => (
                <Option key={l.id} value={l.id}>{l.title} ({new Date(l.created_at).toLocaleDateString()})</Option>
              ))}
            </Select>
          </Col>
          <Col>
            <Upload
              showUploadList={false}
              accept=".xlsx,.xls"
              beforeUpload={(file) => { handleUploadDefect(file); return false; }}
            >
              <Button icon={<UploadOutlined />} loading={loadingDefects}>新增并上传缺陷</Button>
            </Upload>
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={handleCleanDefects}
              disabled={!activeDefectListId}
              style={{ background: '#13c2c2', borderColor: '#13c2c2' }}
            >
              执行本地清洗
            </Button>
          </Col>
        </Row>
      </Card>

      <div style={{ color: '#999', fontSize: 12, margin: '8px 0' }}>
        清洗结果预览 (Top 100)
      </div>

      <Table
        size="small"
        loading={loadingDefects}
        dataSource={cleanedDefects}
        rowKey="defect_record_id"
        columns={[
          { title: 'Defect No', dataIndex: 'defect_number', width: 120 },
          { title: 'Main', dataIndex: 'main_component', width: 120, render: t => t && <Tag color="orange">{t}</Tag> },
          { title: 'Sub', dataIndex: 'sub_component', width: 150 },
          { title: 'Loc', dataIndex: 'location', width: 80 },
          { title: 'Ori', dataIndex: 'orientation', width: 80 },
          { title: 'Status', dataIndex: 'status', width: 100 },
          { title: 'Action', dataIndex: 'action', width: 100 },
          { title: 'Description (EN)', dataIndex: 'description_en', ellipsis: true },
        ]}
      />
    </Space>
  )

  // Render: 4. Matching
  const renderMatching = () => (
    <Space direction="vertical" style={{ width: '100%' }}>
      <Card size="small">
        <Row gutter={[24, 16]} align="middle">
          <Col span={24}>
            <Space wrap size={16}>
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <span style={{ color: '#666', marginRight: 8 }}>待匹配缺陷:</span>
                <Select
                  style={{ width: 220 }}
                  placeholder="选择缺陷清单"
                  value={activeDefectListId}
                  onChange={setActiveDefectListId}
                >
                  {defectLists.map(l => (
                    <Option key={l.id} value={l.id}>{l.title}</Option>
                  ))}
                </Select>
              </div>

              <div style={{ display: 'flex', alignItems: 'center' }}>
                <span style={{ color: '#666', marginRight: 8 }}>目标库:</span>
                <Tag color="blue" style={{ fontSize: 13 }}>已清洗上传工卡 (Upload)</Tag>
              </div>

              {workcardSource === 'upload' && (
                <div style={{ display: 'flex', alignItems: 'center' }}>
                  <span style={{ color: '#666', marginRight: 8 }}>客舱布局:</span>
                  <Select
                    style={{ width: 220 }}
                    placeholder="默认全部布局"
                    allowClear
                    value={selectedCabinLayout}
                    onChange={setSelectedCabinLayout}
                  >
                    {availableCabinLayouts.map(layout => (
                      <Option key={layout} value={layout}>{layout}</Option>
                    ))}
                  </Select>
                </div>
              )}

              <Button
                type="primary"
                icon={<SafetyCertificateOutlined />}
                onClick={handleMatch}
                loading={loadingMatch}
                disabled={!activeDefectListId}
                style={{ background: '#13c2c2', borderColor: '#13c2c2' }}
              >
                开始智能匹配
              </Button>
            </Space>
          </Col>
          <Col span={24} style={{ textAlign: 'right', borderTop: '1px solid #f0f0f0', paddingTop: 16 }}>
            <Button icon={<ImportOutlined />} onClick={handleExport} disabled={!matchResults.length}>
              导出当前匹配结果
            </Button>
          </Col>
        </Row>
      </Card>

      {matchStats && (
        <Card size="small">
          <Descriptions title="匹配结果统计" column={4} size="small">
            <Descriptions.Item label="总缺陷数">{matchStats.total_defects}</Descriptions.Item>
            <Descriptions.Item label="成功匹配">{matchStats.matched_defects}</Descriptions.Item>
            <Descriptions.Item label="未匹配">{matchStats.unmatched_defects}</Descriptions.Item>
            <Descriptions.Item label="匹配率">{matchStats.match_rate}%</Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      <Table
        size="small"
        loading={loadingMatch}
        dataSource={matchResults}
        rowKey="defect_record_id"
        columns={[
          { title: 'Defect No', dataIndex: 'defect_number', width: 120 },
          { title: 'Main', dataIndex: 'main_component', width: 120, render: t => t && <Tag color="orange">{t}</Tag> },
          { title: 'Sub', dataIndex: 'sub_component', width: 120, ellipsis: true },
          { title: 'Loc', dataIndex: 'location', width: 80 },
          { title: 'Ori', dataIndex: 'orientation', width: 80 },
          { title: 'Status', dataIndex: 'status', width: 100 },
          { title: 'Action', dataIndex: 'action', width: 100 },
          {
            title: 'Top Match (Best)',
            width: 300,
            render: (_, r) => {
              // 只显示 >= 85 分的候选工卡（匹配成功的）
              const topMatch = r.candidates?.find(c => c.similarity_score >= 85)
              if (!topMatch) return <Tag>No Match</Tag>
              return (
                <Space direction="vertical" size={0}>
                  <Space>
                    <Tag color={topMatch.similarity_score >= 90 ? 'green' : 'orange'}>
                      {topMatch.workcard_number}
                    </Tag>
                    <b>{topMatch.similarity_score}分</b>
                  </Space>
                  <div style={{ fontSize: '11px', color: '#888', maxWidth: 280, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={topMatch.description_en}>
                    {topMatch.description_en}
                  </div>
                </Space>
              )
            }
          },
          { 
            title: 'Matches', 
            render: (_, record) => {
              // 显示匹配成功的数量（>= 85分）
              const successCount = record.candidates?.filter(c => c.similarity_score >= 85).length || 0
              const partialCount = record.candidates?.filter(c => c.similarity_score >= 50 && c.similarity_score < 85).length || 0
              return (
                <Space direction="vertical" size={0}>
                  <a>{successCount} 成功</a>
                  {partialCount > 0 && <span style={{ fontSize: '11px', color: '#999' }}>{partialCount} 部分匹配</span>}
                </Space>
              )
            }, 
            width: 100 
          },
        ]}
        expandable={{
          expandedRowRender: (record) => {
            // 分离匹配成功的（>= 85分）和部分匹配的（50-85分）
            const successCandidates = record.candidates?.filter(c => c.similarity_score >= 85) || []
            const partialCandidates = record.candidates?.filter(c => c.similarity_score >= 50 && c.similarity_score < 85) || []
            
            return (
              <Space direction="vertical" style={{ width: '100%' }}>
                {/* 匹配成功的候选工卡（>= 85分） */}
                {successCandidates.length > 0 && (
                  <div>
                    <div style={{ marginBottom: 8, fontWeight: 'bold', color: '#52c41a' }}>
                      匹配成功（≥85分）:
                    </div>
                    <Table
                      size="small"
                      columns={[
                        { title: 'Rank', render: (_, __, i) => i + 1, width: 60 },
                        { title: 'Candidate Workcard', dataIndex: 'workcard_number', width: 150, render: t => <a>{t}</a> },
                        { 
                          title: 'Score', 
                          dataIndex: 'similarity_score', 
                          width: 100, 
                          render: s => <b style={{ color: s >= 90 ? '#52c41a' : '#faad14' }}>{s}</b> 
                        },
                        { title: 'Description (EN)', dataIndex: 'description_en', ellipsis: true },
                        { title: 'Description (CN)', dataIndex: 'description', ellipsis: true },
                      ]}
                      dataSource={successCandidates}
                      pagination={false}
                      showHeader={true}
                    />
                  </div>
                )}
                
                {/* 部分匹配的候选工卡（50-85分） */}
                {partialCandidates.length > 0 && (
                  <div style={{ marginTop: successCandidates.length > 0 ? 16 : 0 }}>
                    <div style={{ marginBottom: 8, fontWeight: 'bold', color: '#faad14' }}>
                      部分匹配（50-85分）:
                    </div>
                    <Table
                      size="small"
                      columns={[
                        { title: 'Rank', render: (_, __, i) => i + 1, width: 60 },
                        { title: 'Candidate Workcard', dataIndex: 'workcard_number', width: 150, render: t => <a>{t}</a> },
                        { 
                          title: 'Score', 
                          dataIndex: 'similarity_score', 
                          width: 100, 
                          render: s => <b style={{ color: '#faad14' }}>{s}</b> 
                        },
                        { title: 'Description (EN)', dataIndex: 'description_en', ellipsis: true },
                        { title: 'Description (CN)', dataIndex: 'description', ellipsis: true },
                      ]}
                      dataSource={partialCandidates}
                      pagination={false}
                      showHeader={true}
                    />
                  </div>
                )}
                
                {/* 如果没有候选工卡 */}
                {successCandidates.length === 0 && partialCandidates.length === 0 && (
                  <div style={{ color: '#999', textAlign: 'center', padding: '20px' }}>
                    暂无候选工卡（分数 &lt; 50）
                  </div>
                )}
              </Space>
            )
          }
        }}
      />
    </Space>
  )

  return (
    <Layout style={{ minHeight: '100vh', background: '#fff', padding: '24px' }}>
      <Sider
        width={280}
        theme="light"
        style={{
          background: '#fff',
          borderRadius: '12px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
          height: 'calc(100vh - 48px)',
          position: 'fixed'
        }}
      >
        <div style={{ padding: '24px', borderBottom: '1px solid #f0f0f0' }}>
          <Title level={3} style={{ margin: 0, color: '#13c2c2' }}>本地清洗工作台</Title>
          <Button type="text" icon={<HomeOutlined />} onClick={() => navigate('/')} style={{ marginTop: 12, paddingLeft: 0 }}>
            返回首页
          </Button>
        </div>

        <div style={{ padding: '16px 16px' }}>
          <Text type="secondary" style={{ fontSize: 12 }}>CONFIGURATION</Text>
          <Select
            style={{ width: '100%', marginTop: 8 }}
            placeholder="选择构型"
            value={selectedConfigurationId}
            onChange={setSelectedConfigurationId}
            loading={loadingConfigs}
          >
            {configurations.map(c => <Option key={c.id} value={c.id}>{c.name}</Option>)}
          </Select>

          <Text type="secondary" style={{ fontSize: 12, display: 'block', marginTop: 16 }}>DICTIONARY VERSION</Text>
          <Select
            style={{ width: '100%', marginTop: 8 }}
            placeholder="选择词典"
            value={selectedDictId}
            onChange={setSelectedDictId}
            loading={loadingDicts}
            disabled={!selectedConfigurationId}
          >
            {dicts.map(d => <Option key={d.id} value={d.id}>{d.version}</Option>)}
          </Select>
        </div>

        <Menu
          mode="inline"
          selectedKeys={[activeMenu]}
          onClick={({ key }) => setActiveMenu(key)}
          style={{ borderRight: 0, borderRadius: '0 0 12px 12px' }}
          items={[
            { key: 'dict', icon: <ReadOutlined />, label: '词典管理 (Dictionary)' },
            { key: 'workcards', icon: <FileTextOutlined />, label: '历史工卡 (Workcards)' },
            { key: 'defects', icon: <BugOutlined />, label: '新增缺陷 (Defects)' },
            { key: 'matching', icon: <SafetyCertificateOutlined />, label: '智能匹配 (Matching)' },
          ]}
        />
      </Sider>

      <Layout style={{ marginLeft: 280, background: 'transparent' }}>
        <Content style={{ padding: '0 0 0 24px' }}>
          <div style={{ background: '#fff', padding: 24, borderRadius: 12, boxShadow: '0 2px 8px rgba(0,0,0,0.06)', minHeight: 'calc(100vh - 48px)' }}>
            {activeMenu === 'dict' && renderDictionary()}
            {activeMenu === 'workcards' && renderWorkcards()}
            {activeMenu === 'defects' && renderDefects()}
            {activeMenu === 'matching' && renderMatching()}
          </div>
        </Content>
      </Layout>
    </Layout>
  )
}

export default KeywordManager
