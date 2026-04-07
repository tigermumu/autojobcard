import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Layout, Menu, Typography, Card, Button, Table, message, Form, Select, List, Radio, Space, Grid, Input, Row, Col, Modal, InputNumber } from 'antd'
import { useNavigate } from 'react-router-dom'
import { HomeOutlined, FileSearchOutlined, FolderOpenOutlined, MenuOutlined, FileExcelOutlined, UploadOutlined, EyeOutlined } from '@ant-design/icons'
import * as XLSX from 'xlsx'

const { Sider, Content } = Layout
const { Title } = Typography
const { useBreakpoint } = Grid

type DefectDetailItem = {
  defect_status: string
  defect_positions: string
  defect_quantity: number
  local_photo_url?: string
  global_photo_url?: string
}

const defectStatusOptions = ['破损', '磨损', '起毛', '掉漆', '划伤', '裂纹', '断开']
const seatPositionOptions = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'R', 'M']
const seatPositionPreviewOrder = ['L', 'A', 'B', 'C', 'D', 'E', 'M', 'F', 'G', 'H', 'I', 'J', 'K', 'R']
const crewSeatPositionPresetMap: Record<string, string[]> = {
  驾驶员座椅: ['正驾驶', '副驾驶'],
  观察员座椅: ['第三观察员', '第四观察员', '第五观察员'],
}
const compNameWhitelistMap: Record<string, string[]> = {
  single: ['厨房', '厕所', '储物柜'],
  seat: ['公务舱座椅', '头等舱座椅', '经济舱座椅'],
  'crew-seat': ['驾驶员座椅', '乘务员座椅', '观察员座椅'],
  batch: ['天花板', '侧壁板', '行李箱'],
}

const normalizeDefectDetailList = (input: any): DefectDetailItem[] | undefined => {
  if (!input) return undefined
  if (Array.isArray(input)) {
    const list = input
      .map((d) => {
        if (!d || typeof d !== 'object') return null
        const defect_status = String(d.defect_status || '').trim()
        const defect_positions = String(d.defect_positions || '').trim()
        const defect_quantity = Number(d.defect_quantity ?? 0)
        const local_photo_url = String(d.local_photo_url || '').trim()
        const global_photo_url = String(d.global_photo_url || '').trim()
        const hasAny = Boolean(defect_status || defect_positions || local_photo_url || global_photo_url || (Number.isFinite(defect_quantity) && defect_quantity > 0))
        if (!hasAny) return null
        return {
          defect_status,
          defect_positions,
          defect_quantity: Number.isFinite(defect_quantity) && defect_quantity > 0 ? defect_quantity : splitDefectPositions(defect_positions).length,
          local_photo_url: local_photo_url || undefined,
          global_photo_url: global_photo_url || undefined,
        }
      })
      .filter(Boolean) as DefectDetailItem[]
    return list.length > 0 ? list : undefined
  }
  if (typeof input === 'object') {
    const defect_status = String((input as any).defect_status || '').trim()
    const defect_positions = String((input as any).defect_positions || '').trim()
    const defect_quantity = Number((input as any).defect_quantity ?? 0)
    const local_photo_url = String((input as any).local_photo_url || '').trim()
    const global_photo_url = String((input as any).global_photo_url || '').trim()
    const hasAny = Boolean(defect_status || defect_positions || local_photo_url || global_photo_url || (Number.isFinite(defect_quantity) && defect_quantity > 0))
    if (!hasAny) return undefined
    return [{
      defect_status,
      defect_positions,
      defect_quantity: Number.isFinite(defect_quantity) && defect_quantity > 0 ? defect_quantity : splitDefectPositions(defect_positions).length,
      local_photo_url: local_photo_url || undefined,
      global_photo_url: global_photo_url || undefined,
    }]
  }
  return undefined
}

const splitDefectPositions = (input: string): string[] => {
  const raw = String(input || '').trim()
  if (!raw) return []
  return raw
    .split(/[;；,，|、\n]+/g)
    .map((s) => s.trim())
    .filter(Boolean)
}

const splitSeatCustomPositions = (input: string): string[] => {
  const raw = String(input || '').trim()
  if (!raw) return []
  const uniq = new Set<string>()
  return raw
    .split(/[;；]+/g)
    .map((s) => s.trim())
    .filter(Boolean)
    .filter((s) => {
      if (uniq.has(s)) return false
      uniq.add(s)
      return true
    })
}

const sortSeatPreviewPositions = (positions: string[]): string[] => {
  const idx = new Map<string, number>(seatPositionPreviewOrder.map((p, i) => [p, i]))
  const uniq: string[] = []
  const seen = new Set<string>()
  for (const p of positions) {
    const v = String(p || '').trim()
    if (!v || seen.has(v)) continue
    seen.add(v)
    uniq.push(v)
  }
  const ranked = uniq.filter((p) => idx.has(p)).sort((a, b) => (idx.get(a) as number) - (idx.get(b) as number))
  const others = uniq.filter((p) => !idx.has(p))
  return [...ranked, ...others]
}

const parsePreviewParts = (previewLike: any): { descText: string, locText: string, qtyText: string } => {
  const preview = String(previewLike || '').trim()
  if (!preview) return { descText: '', locText: '', qtyText: '' }
  const locMarker = '，LOC：'
  const qtyMarker = '，QTY：'
  const locIndex = preview.indexOf(locMarker)
  const qtyIndex = preview.indexOf(qtyMarker)
  if (locIndex < 0 || qtyIndex < 0 || qtyIndex < locIndex) {
    return { descText: preview, locText: '', qtyText: '' }
  }
  return {
    descText: preview.slice(0, locIndex).trim(),
    locText: preview.slice(locIndex + locMarker.length, qtyIndex).trim(),
    qtyText: preview.slice(qtyIndex + qtyMarker.length).trim(),
  }
}

const buildFallbackDescText = (row: any): string => {
  const parsed = parsePreviewParts(row?.defect_desc_preview)
  if (parsed.descText) return parsed.descText
  return `${String(row?.standardized_desc || '').trim()}${String(row?.defect_status || '').trim()}`.trim()
}

const buildFallbackLocText = (source: string, row: any): string => {
  const parsed = parsePreviewParts(row?.defect_desc_preview)
  if (parsed.locText) return parsed.locText
  const positions = splitDefectPositions(String(row?.defect_positions || row?.position || ''))
  if (source === 'seat') {
    const seatLoc = String(row?.loc || '').trim()
    const combined = `${seatLoc}${sortSeatPreviewPositions(positions).join('')}`.trim()
    if (combined) return combined
  }
  const locText = String(row?.loc_text || '').trim()
  if (locText) return locText
  if (source === 'seat') {
    return ''
  }
  if (source === 'crew-seat') {
    return positions.join(' ').trim()
  }
  if (source === 'batch') {
    return positions.join(' ').trim() || String(row?.position || '').trim()
  }
  return positions.join(' ').trim() || String(row?.loc || '').trim()
}

const buildFallbackQtyValue = (row: any): number => {
  const direct = Number(row?.defect_quantity ?? row?.quantity ?? 0)
  if (Number.isFinite(direct) && direct > 0) return Math.trunc(direct)
  const parsed = parsePreviewParts(row?.defect_desc_preview)
  const qtyText = String(row?.qty_text || '').trim() || parsed.qtyText
  const matched = qtyText.match(/^(\d+)/)
  if (matched) return Number(matched[1]) || 0
  const positions = splitDefectPositions(String(row?.defect_positions || row?.position || ''))
  return positions.length > 0 ? positions.length : 0
}

const DefectCheck: React.FC = () => {
  const navigate = useNavigate()
  const screens = useBreakpoint()
  const isMobile = !screens.md
  const [activeKey, setActiveKey] = useState('single')
  const [rows, setRows] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const [siderCollapsed, setSiderCollapsed] = useState(false)

  const [typeOptions, setTypeOptions] = useState<string[]>([])
  const [custOptions, setCustOptions] = useState<string[]>([])
  const [compNameOptions, setCompNameOptions] = useState<string[]>([])
  const [selectedType, setSelectedType] = useState<string | undefined>(undefined)
  const [selectedCust, setSelectedCust] = useState<string | undefined>(undefined)
  const [selectedCompName, setSelectedCompName] = useState<string | undefined>(undefined)
  const [checkItems, setCheckItems] = useState<any[]>([])
  const [checkLoading, setCheckLoading] = useState(false)
  const [answers, setAnswers] = useState<Record<string, 'yes' | 'no'>>({})
  const [submitting, setSubmitting] = useState(false)
  const [metaCompPn, setMetaCompPn] = useState('')
  const [metaAircraftNo, setMetaAircraftNo] = useState('')
  const [metaSaleWo, setMetaSaleWo] = useState('')
  const [metaPlanYearMonth, setMetaPlanYearMonth] = useState('')
  const [metaLoc, setMetaLoc] = useState('')
  const [metaInspector, setMetaInspector] = useState('')
  const [metaCollapsed, setMetaCollapsed] = useState(false)
  const [batchMetaCollapsed, setBatchMetaCollapsed] = useState(false)
  const [batchSubmitting, setBatchSubmitting] = useState(false)
  const [batchCheckLoading, setBatchCheckLoading] = useState(false)
  const [batchAnswers, setBatchAnswers] = useState<Record<string, 'yes' | 'no'>>({})
  const [batchDefectDetails, setBatchDefectDetails] = useState<Record<string, DefectDetailItem[]>>({})
  const [customModalOpen, setCustomModalOpen] = useState(false)
  const [customDraftSeq, setCustomDraftSeq] = useState('')
  const [customDraftDesc, setCustomDraftDesc] = useState('')
  const [defectDetails, setDefectDetails] = useState<Record<string, DefectDetailItem[]>>({})
  const [detailModalOpen, setDetailModalOpen] = useState(false)
  const [detailModalKey, setDetailModalKey] = useState<string | null>(null)
  const [detailModalScope, setDetailModalScope] = useState<'single' | 'batch'>('single')
  const [detailModalPrevAnswer, setDetailModalPrevAnswer] = useState<'yes' | 'no' | undefined>(undefined)
  const [detailDrafts, setDetailDrafts] = useState<Array<{ defect_status: string, defect_positions: string, defect_quantity?: number, local_photo_url: string, global_photo_url: string }>>([])
  const [exportAircraftNo, setExportAircraftNo] = useState('')
  const [exportSaleWo, setExportSaleWo] = useState('')
  const [exportCompName, setExportCompName] = useState('')
  const [exportCompPn, setExportCompPn] = useState('')
  const [exportInspector, setExportInspector] = useState('')
  const [exportPreviewRows, setExportPreviewRows] = useState<any[]>([])
  const [exportPreviewLoading, setExportPreviewLoading] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [exportPhotoModalOpen, setExportPhotoModalOpen] = useState(false)
  const [exportPhotoModalRow, setExportPhotoModalRow] = useState<any | null>(null)
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [editModalScope, setEditModalScope] = useState<'catalog' | 'single' | 'batch'>('catalog')
  const [editRow, setEditRow] = useState<any | null>(null)
  const [editDraft, setEditDraft] = useState<any>({})
  const [seatCheckItems, setSeatCheckItems] = useState<any[]>([])
  const [seatCheckLoading, setSeatCheckLoading] = useState(false)
  const [seatSubmitting, setSeatSubmitting] = useState(false)
  const [seatMetaCollapsed, setSeatMetaCollapsed] = useState(false)
  const [seatAnswers, setSeatAnswers] = useState<Record<string, 'yes' | 'no'>>({})
  const [seatDefectPositions, setSeatDefectPositions] = useState<Record<string, string[]>>({})
  const [seatDefectStatus, setSeatDefectStatus] = useState<Record<string, string>>({})
  const [seatDefectQuantity, setSeatDefectQuantity] = useState<Record<string, number>>({})
  const [seatDefectPhotos, setSeatDefectPhotos] = useState<Record<string, { local_photo_url?: string, global_photo_url?: string }>>({})
  const [seatPhotoModalOpen, setSeatPhotoModalOpen] = useState(false)
  const [seatPhotoModalKey, setSeatPhotoModalKey] = useState<string | null>(null)
  const [seatPhotoDraft, setSeatPhotoDraft] = useState<{ local_photo_url: string, global_photo_url: string }>({ local_photo_url: '', global_photo_url: '' })
  const [seatFilter, setSeatFilter] = useState<'all' | 'pending' | 'checked'>('pending')
  const [crewSeatCustomPositionsInput, setCrewSeatCustomPositionsInput] = useState('')
  const [singleFilter, setSingleFilter] = useState<'all' | 'pending' | 'checked'>('pending')
  const [batchFilter, setBatchFilter] = useState<'all' | 'pending' | 'checked'>('pending')

  const isRestoringDraftRef = useRef(false)
  const autosaveTimerRef = useRef<number | undefined>(undefined)
  const autosaveToastAtRef = useRef(0)
  const SINGLE_DRAFT_KEY = 'defectcheck:single:draft:v1'

  type SingleDraft = {
    v: 1
    updatedAt: number
    selectedType?: string
    selectedCust?: string
    selectedCompName?: string
    metaCompPn?: string
    metaAircraftNo?: string
    metaSaleWo?: string
    metaPlanYearMonth?: string
    metaLoc?: string
    metaInspector?: string
    metaCollapsed?: boolean
    answers?: Record<string, 'yes' | 'no'>
    checkItems?: any[]
    defectDetails?: Record<string, any>
  }

  const readSingleDraft = useCallback((): SingleDraft | null => {
    try {
      const raw = localStorage.getItem(SINGLE_DRAFT_KEY)
      if (!raw) return null
      const parsed = JSON.parse(raw)
      if (!parsed || parsed.v !== 1) return null
      return parsed as SingleDraft
    } catch {
      return null
    }
  }, [])

  const writeSingleDraft = useCallback((partial?: Partial<SingleDraft>, showToast?: boolean) => {
    if (activeKey !== 'single') return
    if (isRestoringDraftRef.current) return
    const draft: SingleDraft = {
      v: 1,
      updatedAt: Date.now(),
      selectedType,
      selectedCust,
      selectedCompName,
      metaCompPn,
      metaAircraftNo,
      metaSaleWo,
      metaPlanYearMonth,
      metaLoc,
      metaInspector,
      metaCollapsed,
      answers,
      checkItems,
      defectDetails,
      ...(partial || {}),
    }
    try {
      localStorage.setItem(SINGLE_DRAFT_KEY, JSON.stringify(draft))
    } catch {}
    if (showToast) {
      const now = Date.now()
      if (now - autosaveToastAtRef.current > 1500) {
        message.open({ type: 'success', content: '已自动保存', key: 'single-autosave', duration: 0.6 })
        autosaveToastAtRef.current = now
      }
    }
  }, [activeKey, answers, checkItems, defectDetails, metaAircraftNo, metaCollapsed, metaCompPn, metaInspector, metaLoc, metaPlanYearMonth, metaSaleWo, selectedCompName, selectedCust, selectedType])

  const clearSingleDraft = useCallback(() => {
    try {
      localStorage.removeItem(SINGLE_DRAFT_KEY)
    } catch {}
  }, [])

  const items = [
    { key: 'single', icon: <FileSearchOutlined />, label: '厨卫部件检查' },
    { key: 'seat', icon: <FileSearchOutlined />, label: '旅客座椅缺陷检查' },
    { key: 'crew-seat', icon: <FileSearchOutlined />, label: '机组座椅缺陷检查' },
    { key: 'batch', icon: <FolderOpenOutlined />, label: '天行侧部件检查' },
    { key: 'export', icon: <FileExcelOutlined />, label: '缺陷清单导出' },
    { key: 'catalog', icon: <FolderOpenOutlined />, label: '标准缺陷描述数据表' },
    { key: 'custom', icon: <FolderOpenOutlined />, label: '自定义缺陷描述' },
  ]

  const endpoint = useMemo(() => {
    if (activeKey === 'catalog') return '/api/v1/standard-defect-desc/'
    if (activeKey === 'custom') return '/api/v1/custom-defect-desc/'
    if (activeKey === 'batch') return '/api/v1/batch-defect-checks/'
    return '/api/v1/single-defect-checks/'
  }, [activeKey])

  const activeLabel = useMemo(() => items.find(i => i.key === activeKey)?.label || '', [activeKey])
  const activeCompNameOptions = useMemo(() => compNameWhitelistMap[activeKey] || compNameOptions, [activeKey, compNameOptions])
  const activeCompNameOptionsSet = useMemo(() => new Set(activeCompNameOptions), [activeCompNameOptions])
  const activeSeatPositionOptions = useMemo(() => {
    if (activeKey !== 'crew-seat') return seatPositionOptions
    const selected = String(selectedCompName || '').trim()
    if (!selected) return []
    if (selected === '乘务员座椅') return splitSeatCustomPositions(crewSeatCustomPositionsInput)
    return crewSeatPositionPresetMap[selected] || []
  }, [activeKey, crewSeatCustomPositionsInput, selectedCompName])
  const activeSeatPositionOptionSet = useMemo(() => new Set(activeSeatPositionOptions), [activeSeatPositionOptions])
  const filteredSeatCheckItems = useMemo(() => {
    if (seatFilter === 'all') return seatCheckItems
    if (seatFilter === 'pending') return seatCheckItems.filter((it) => !seatAnswers[String(it.id)])
    return seatCheckItems.filter((it) => Boolean(seatAnswers[String(it.id)]))
  }, [seatAnswers, seatCheckItems, seatFilter])
  const filteredSingleCheckItems = useMemo(() => {
    if (singleFilter === 'all') return checkItems
    if (singleFilter === 'pending') return checkItems.filter((it) => !answers[String(it.id)])
    return checkItems.filter((it) => Boolean(answers[String(it.id)]))
  }, [answers, checkItems, singleFilter])
  const filteredBatchCheckItems = useMemo(() => {
    if (batchFilter === 'all') return checkItems
    if (batchFilter === 'pending') return checkItems.filter((it) => !batchAnswers[String(it.id)])
    return checkItems.filter((it) => Boolean(batchAnswers[String(it.id)]))
  }, [batchAnswers, batchFilter, checkItems])

  const columns = useMemo(() => {
    const common = [
      { title: '序号', dataIndex: 'seq', key: 'seq', width: 80 },
      { title: '部件件号', dataIndex: 'comp_pn', key: 'comp_pn', width: 140 },
      { title: '标准化描述', dataIndex: 'standardized_desc', key: 'standardized_desc', width: 520 },
      { title: '机型', dataIndex: 'type', key: 'type', width: 120 },
      { title: '客户', dataIndex: 'cust', key: 'cust', width: 120 },
      { title: '部件名称', dataIndex: 'comp_name', key: 'comp_name', width: 200 },
    ]

    if (activeKey === 'catalog') {
      return [
        ...common,
        {
          title: '操作',
          key: 'actions',
          width: 220,
          fixed: 'right',
          render: (_: any, record: any) => {
            const id = record?.id
            return (
              <Space>
                <Button
                  type="link"
                  onClick={() => {
                    setEditRow(record)
                    setEditModalScope('catalog')
                    setEditDraft({
                      seq: record?.seq ?? '',
                      comp_pn: record?.comp_pn ?? '',
                      standardized_desc: record?.standardized_desc ?? '',
                      type: record?.type ?? '',
                      cust: record?.cust ?? '',
                      comp_name: record?.comp_name ?? '',
                    })
                    setEditModalOpen(true)
                  }}
                >
                  编辑
                </Button>
                <Button
                  type="link"
                  danger
                  onClick={() => {
                    if (!id) return
                    Modal.confirm({
                      title: '确认删除该条标准缺陷描述？',
                      okText: '删除',
                      cancelText: '取消',
                      okButtonProps: { danger: true },
                      onOk: async () => {
                        try {
                          const res = await fetch(`/api/v1/standard-defect-desc/${id}`, { method: 'DELETE' })
                          if (!res.ok) {
                            const text = await res.text().catch(() => '')
                            throw new Error(text || res.statusText)
                          }
                          message.success('已删除')
                          setRows((prev) => prev.filter((r) => r.id !== id))
                        } catch (e: any) {
                          message.error(e?.message || '删除失败')
                        }
                      },
                    })
                  }}
                >
                  删除
                </Button>
              </Space>
            )
          },
        },
      ]
    }

    if (activeKey === 'custom') {
      return [
        ...common,
        {
          title: '操作',
          key: 'actions',
          width: 220,
          fixed: 'right',
          render: (_: any, record: any) => {
            const id = record?.id
            return (
              <Space>
                <Button
                  type="link"
                  onClick={async () => {
                    if (!id) return
                    try {
                      const res = await fetch(`/api/v1/custom-defect-desc/${id}/move-to-standard?delete_source=true`, { method: 'POST' })
                      if (!res.ok) {
                        const text = await res.text().catch(() => '')
                        throw new Error(text || res.statusText)
                      }
                      const data = await res.json().catch(() => ({}))
                      if (data?.moved) {
                        message.success('已移入标准缺陷描述库')
                        setRows((prev) => prev.filter((r) => r.id !== id))
                      } else {
                        message.warning('标准库已存在相同记录，未移入')
                      }
                    } catch (e: any) {
                      message.error(e?.message || '移库失败')
                    }
                  }}
                >
                  移入标准库
                </Button>
                <Button
                  type="link"
                  danger
                  onClick={async () => {
                    if (!id) return
                    try {
                      const res = await fetch(`/api/v1/custom-defect-desc/${id}`, { method: 'DELETE' })
                      if (!res.ok) {
                        const text = await res.text().catch(() => '')
                        throw new Error(text || res.statusText)
                      }
                      message.success('已删除')
                      setRows((prev) => prev.filter((r) => r.id !== id))
                    } catch (e: any) {
                      message.error(e?.message || '删除失败')
                    }
                  }}
                >
                  删除
                </Button>
              </Space>
            )
          },
        },
      ]
    }

    if (activeKey === 'single') {
      return [
        ...common,
        { title: '位置', dataIndex: 'loc', key: 'loc', width: 200 },
        { title: '检查人', dataIndex: 'inspector', key: 'inspector', width: 120 },
        { title: '是', dataIndex: 'yes_flag', key: 'yes_flag', width: 80 },
        { title: '否', dataIndex: 'no_flag', key: 'no_flag', width: 80 },
        { title: '飞机号', dataIndex: 'aircraft_no', key: 'aircraft_no', width: 120 },
        { title: '销售指令号', dataIndex: 'sale_wo', key: 'sale_wo', width: 140 },
        { title: '定检年月', dataIndex: 'plan_year_month', key: 'plan_year_month', width: 120 },
        {
          title: '操作',
          key: 'actions',
          width: 140,
          fixed: 'right',
          render: (_: any, record: any) => (
            <Button
              type="link"
              onClick={() => {
                setEditRow(record)
                setEditModalScope('single')
                setEditDraft({
                  seq: record?.seq ?? '',
                  comp_pn: record?.comp_pn ?? '',
                  standardized_desc: record?.standardized_desc ?? '',
                  type: record?.type ?? '',
                  cust: record?.cust ?? '',
                  comp_name: record?.comp_name ?? '',
                  loc: record?.loc ?? '',
                  inspector: record?.inspector ?? '',
                  aircraft_no: record?.aircraft_no ?? '',
                  sale_wo: record?.sale_wo ?? '',
                  plan_year_month: record?.plan_year_month ?? '',
                  yes_flag: record?.yes_flag ? 1 : null,
                  no_flag: record?.no_flag ? 1 : null,
                  defect_status: record?.defect_status ?? '',
                  defect_positions: record?.defect_positions ?? '',
                  defect_quantity: record?.defect_quantity ?? undefined,
                  local_photo_url: record?.local_photo_url ?? '',
                  global_photo_url: record?.global_photo_url ?? '',
                })
                setEditModalOpen(true)
              }}
            >
              编辑
            </Button>
          ),
        },
      ]
    }

    return [
      ...common,
      { title: '位置', dataIndex: 'position', key: 'position', width: 200 },
      { title: '数量', dataIndex: 'quantity', key: 'quantity', width: 90 },
      { title: '飞机号', dataIndex: 'aircraft_no', key: 'aircraft_no', width: 120 },
      { title: '销售指令号', dataIndex: 'sale_wo', key: 'sale_wo', width: 140 },
      { title: '定检年月', dataIndex: 'plan_year_month', key: 'plan_year_month', width: 120 },
      {
        title: '操作',
        key: 'actions',
        width: 140,
        fixed: 'right',
        render: (_: any, record: any) => (
          <Button
            type="link"
            onClick={() => {
              setEditRow(record)
              setEditModalScope('batch')
              setEditDraft({
                seq: record?.seq ?? '',
                comp_pn: record?.comp_pn ?? '',
                standardized_desc: record?.standardized_desc ?? '',
                type: record?.type ?? '',
                cust: record?.cust ?? '',
                comp_name: record?.comp_name ?? '',
                aircraft_no: record?.aircraft_no ?? '',
                sale_wo: record?.sale_wo ?? '',
                plan_year_month: record?.plan_year_month ?? '',
                yes_flag: record?.yes_flag ? 1 : null,
                no_flag: record?.no_flag ? 1 : null,
                defect_status: record?.defect_status ?? '',
                defect_positions: record?.defect_positions ?? '',
                position: record?.position ?? '',
                defect_quantity: record?.defect_quantity ?? undefined,
                quantity: record?.quantity ?? undefined,
                local_photo_url: record?.local_photo_url ?? '',
                global_photo_url: record?.global_photo_url ?? '',
              })
              setEditModalOpen(true)
            }}
          >
            编辑
          </Button>
        ),
      },
    ]
  }, [activeKey])

  const exportHeaders = useMemo(() => {
    return [
      '缺陷编号',
      '部件件号',
      '工卡描述中文',
      '工卡描述英文',
      '位置',
      '数量',
      'global_photo',
      'local_photo',
      '相关工卡号',
      '相关工卡序号',
      '区域',
      '区域号',
      '参考手册',
      '候选工卡',
      '候选工卡描述英文',
      '候选工卡描述中文',
      '已开工卡号',
      'Candidate Workcard Description (English)',
      'Candidate Workcard Description (Chinese)',
    ]
  }, [])

  const exportPreviewColumns = useMemo(() => {
    return [
      { title: '部件件号', dataIndex: 'comp_pn', key: 'comp_pn', width: 140 },
      { title: '缺陷描述', dataIndex: 'defect_desc', key: 'defect_desc', width: 520 },
      { title: '位置', dataIndex: 'position', key: 'position', width: 260 },
      { title: '数量', dataIndex: 'quantity', key: 'quantity', width: 90 },
      {
        title: '照片',
        key: 'photos',
        width: 100,
        render: (_: any, record: any) => {
          const has = Boolean(String(record?.local_photo_url || '').trim() || String(record?.global_photo_url || '').trim())
          return (
            <Button
              type="link"
              icon={<EyeOutlined />}
              disabled={!has}
              onClick={() => {
                if (!has) return
                setExportPhotoModalRow(record)
                setExportPhotoModalOpen(true)
              }}
            >
              查看
            </Button>
          )
        },
      },
      {
        title: '操作',
        key: 'actions',
        width: 120,
        fixed: 'right',
        render: (_: any, record: any) => {
          const editable = record?.source === 'single' || record?.source === 'batch'
          if (!editable) return null
          return (
            <Button
              type="link"
              onClick={async () => {
                if (!record?.id || !record?.source) return
                const scope = record.source === 'single' ? 'single' : 'batch'
                setEditModalScope(scope)
                try {
                  const endpoint = scope === 'single' ? '/api/v1/single-defect-checks/' : '/api/v1/batch-defect-checks/'
                  const res = await fetch(`${endpoint}${record.id}`, { method: 'GET' })
                  if (!res.ok) {
                    const text = await res.text().catch(() => '')
                    throw new Error(text || res.statusText)
                  }
                  const data = await res.json().catch(() => ({}))
                  setEditRow(data)
                  if (scope === 'single') {
                    setEditDraft({
                      seq: data?.seq ?? '',
                      comp_pn: data?.comp_pn ?? '',
                      standardized_desc: data?.standardized_desc ?? '',
                      type: data?.type ?? '',
                      cust: data?.cust ?? '',
                      comp_name: data?.comp_name ?? '',
                      loc: data?.loc ?? '',
                      inspector: data?.inspector ?? '',
                      aircraft_no: data?.aircraft_no ?? '',
                      sale_wo: data?.sale_wo ?? '',
                      plan_year_month: data?.plan_year_month ?? '',
                      yes_flag: 1,
                      no_flag: null,
                      defect_status: data?.defect_status ?? '',
                      defect_positions: data?.defect_positions ?? data?.loc ?? '',
                      defect_quantity: data?.defect_quantity ?? record?.quantity ?? undefined,
                      local_photo_url: data?.local_photo_url ?? '',
                      global_photo_url: data?.global_photo_url ?? '',
                    })
                  } else {
                    setEditDraft({
                      seq: data?.seq ?? '',
                      comp_pn: data?.comp_pn ?? '',
                      standardized_desc: data?.standardized_desc ?? '',
                      type: data?.type ?? '',
                      cust: data?.cust ?? '',
                      comp_name: data?.comp_name ?? '',
                      aircraft_no: data?.aircraft_no ?? '',
                      sale_wo: data?.sale_wo ?? '',
                      plan_year_month: data?.plan_year_month ?? '',
                      yes_flag: 1,
                      no_flag: null,
                      defect_status: data?.defect_status ?? '',
                      defect_positions: data?.defect_positions ?? data?.position ?? '',
                      position: data?.position ?? data?.defect_positions ?? '',
                      defect_quantity: data?.defect_quantity ?? data?.quantity ?? undefined,
                      quantity: data?.quantity ?? data?.defect_quantity ?? undefined,
                      local_photo_url: data?.local_photo_url ?? '',
                      global_photo_url: data?.global_photo_url ?? '',
                    })
                  }
                } catch (e: any) {
                  message.error(e?.message || '加载记录详情失败')
                  return
                }
                setEditModalOpen(true)
              }}
            >
              编辑
            </Button>
          )
        },
      },
    ]
  }, [])

  const exportFetchAll = useCallback(async (baseUrl: string, keyword: string) => {
    const rows: any[] = []
    const limit = 1000
    for (let skip = 0; skip < 1000000; skip += limit) {
      const url = new URL(baseUrl, window.location.origin)
      url.searchParams.set('skip', String(skip))
      url.searchParams.set('limit', String(limit))
      const kw = keyword.trim()
      if (kw) url.searchParams.set('keyword', kw)
      const res = await fetch(url.toString(), { method: 'GET' })
      if (!res.ok) {
        const text = await res.text().catch(() => '')
        throw new Error(text || res.statusText)
      }
      const data = await res.json()
      const arr = Array.isArray(data) ? data : []
      rows.push(...arr)
      if (arr.length < limit) break
    }
    return rows
  }, [])

  const exportMatches = useCallback((v: any, needle: string) => {
    const n = needle.trim().toLowerCase()
    if (!n) return true
    return String(v ?? '').toLowerCase().includes(n)
  }, [])

  const runExportPreview = useCallback(async () => {
    const aircraftNo = exportAircraftNo.trim()
    const saleWo = exportSaleWo.trim()
    const compName = exportCompName.trim()
    const compPn = exportCompPn.trim()
    const inspector = exportInspector.trim()
    if (!aircraftNo && !saleWo && !compName && !compPn && !inspector) {
      message.error('请至少填写一个筛选条件')
      return
    }
    setExportPreviewLoading(true)
    try {
      const serverKeyword = aircraftNo || saleWo || compPn || compName || inspector
      const [singleRows, batchRows, seatRows, crewSeatRows] = await Promise.all([
        exportFetchAll('/api/v1/single-defect-checks/', serverKeyword),
        exportFetchAll('/api/v1/batch-defect-checks/', serverKeyword),
        exportFetchAll('/api/v1/seat-defect-checks/', serverKeyword),
        exportFetchAll('/api/v1/crew-seat-defect-checks/', serverKeyword),
      ])

      const applyFilters = (r: any) => {
        if (!exportMatches(r.aircraft_no, aircraftNo)) return false
        if (!exportMatches(r.sale_wo, saleWo)) return false
        if (!exportMatches(r.comp_name, compName)) return false
        if (!exportMatches(r.comp_pn, compPn)) return false
        if (!exportMatches(r.inspector, inspector)) return false
        return true
      }

      const allRows = [
        ...singleRows.filter(applyFilters).map((row: any) => ({ ...row, source: 'single' })),
        ...batchRows.filter(applyFilters).map((row: any) => ({ ...row, source: 'batch' })),
        ...seatRows.filter(applyFilters).map((row: any) => ({ ...row, source: 'seat' })),
        ...crewSeatRows.filter(applyFilters).map((row: any) => ({ ...row, source: 'crew-seat' })),
      ]

      const normalizedRows = allRows
        .filter((row: any) => {
          if (row?.yes_flag) return true
          if (row?.source !== 'batch') return false
          return !row?.no_flag && Boolean(String(row?.position || row?.defect_positions || '').trim())
        })
        .map((row: any) => {
          const source = String(row?.source || '').trim()
          const descText = buildFallbackDescText(row)
          const locText = buildFallbackLocText(source, row)
          const quantityValue = buildFallbackQtyValue(row)
          const qtyText = String(row?.qty_text || '').trim() || (quantityValue > 0 ? `${quantityValue} EA` : '')
          const defectDescPreview = String(row?.defect_desc_preview || '').trim() || `${descText}，LOC：${locText}，QTY：${qtyText}`
          return {
            id: row?.id,
            source,
            seq: row?.seq,
            comp_pn: String(row?.comp_pn || '').trim(),
            standardized_desc: String(row?.standardized_desc || '').trim(),
            type: String(row?.type || '').trim(),
            cust: String(row?.cust || '').trim(),
            comp_name: String(row?.comp_name || '').trim(),
            loc: String(row?.loc || '').trim(),
            inspector: String(row?.inspector || '').trim(),
            aircraft_no: String(row?.aircraft_no || '').trim(),
            sale_wo: String(row?.sale_wo || '').trim(),
            plan_year_month: String(row?.plan_year_month || '').trim(),
            yes_flag: row?.yes_flag ? 1 : null,
            no_flag: row?.no_flag ? 1 : null,
            defect_status: String(row?.defect_status || '').trim(),
            defect_positions: String(row?.defect_positions || '').trim(),
            defect_quantity: quantityValue || null,
            defect_desc: descText,
            defect_desc_preview: defectDescPreview,
            position: locText,
            quantity: quantityValue || null,
            local_photo_url: row?.local_photo_url || '',
            global_photo_url: row?.global_photo_url || '',
          }
        })
        .filter((row: any) => Boolean(row.defect_desc))

      const grouped = new Map<string, any>()
      for (const row of normalizedRows) {
        const groupKey = `${row.comp_pn}__${row.defect_desc}`
        const current = grouped.get(groupKey)
        if (!current) {
          grouped.set(groupKey, {
            ...row,
            _positions: row.position ? [row.position] : [],
            _quantityTotal: Number(row.quantity ?? 0) || 0,
          })
          continue
        }
        if (row.position && !current._positions.includes(row.position)) current._positions.push(row.position)
        current._quantityTotal += Number(row.quantity ?? 0) || 0
        if (!current.global_photo_url && row.global_photo_url) current.global_photo_url = row.global_photo_url
        if (!current.local_photo_url && row.local_photo_url) current.local_photo_url = row.local_photo_url
      }

      const previewRows = Array.from(grouped.values()).map((row: any, index: number) => {
        const position = row._positions.join('；')
        const quantity = row._quantityTotal > 0 ? row._quantityTotal : null
        return {
          ...row,
          id: row.id ?? `${row.source}-${index}`,
          position,
          quantity,
          defect_desc_preview: `${row.defect_desc}，LOC：${position}，QTY：${quantity ? `${quantity} EA` : ''}`,
        }
      })

      setExportPreviewRows(previewRows)
      message.success(`预览结果：${previewRows.length} 条`)
    } catch (e: any) {
      message.error(e?.message || '查询预览失败')
      setExportPreviewRows([])
    } finally {
      setExportPreviewLoading(false)
    }
  }, [exportAircraftNo, exportCompName, exportCompPn, exportFetchAll, exportInspector, exportMatches, exportSaleWo])

  const doExportExcel = useCallback(async () => {
    if (!exportPreviewRows.length) {
      message.error('请先查询预览结果')
      return
    }
    setExporting(true)
    try {
      const toAbsUrl = (u: string) => {
        const s = String(u || '').trim()
        if (!s) return ''
        try {
          return new URL(s, window.location.origin).toString()
        } catch {
          return s
        }
      }
      const wb = XLSX.utils.book_new()
      const aoa: any[][] = [
        exportHeaders,
        ...exportPreviewRows.map((r: any) =>
          exportHeaders.map((h) => {
            if (h === '部件件号') return r?.comp_pn || ''
            if (h === '工卡描述中文') return r?.defect_desc || r?.standardized_desc || ''
            if (h === '位置') return r?.position || ''
            if (h === '数量') return r?.quantity ? `${r.quantity} EA` : ''
            if (h === 'global_photo') return toAbsUrl(String(r?.global_photo_url || '').trim())
            if (h === 'local_photo') return toAbsUrl(String(r?.local_photo_url || '').trim())
            return ''
          })
        ),
      ]
      const ws = XLSX.utils.aoa_to_sheet(aoa)
      const globalPhotoCol = exportHeaders.indexOf('global_photo')
      const localPhotoCol = exportHeaders.indexOf('local_photo')
      if (globalPhotoCol >= 0 || localPhotoCol >= 0) {
        for (let i = 0; i < exportPreviewRows.length; i += 1) {
          const excelRowIndex = i + 1
          const r = exportPreviewRows[i]
          const globalUrl = toAbsUrl(String(r?.global_photo_url || '').trim())
          const localUrl = toAbsUrl(String(r?.local_photo_url || '').trim())
          if (globalPhotoCol >= 0 && globalUrl) {
            const addr = XLSX.utils.encode_cell({ r: excelRowIndex, c: globalPhotoCol })
            const cell = (ws as any)[addr] || { t: 's', v: globalUrl }
            cell.t = 's'
            cell.v = globalUrl
            cell.l = { Target: globalUrl }
            ;(ws as any)[addr] = cell
          }
          if (localPhotoCol >= 0 && localUrl) {
            const addr = XLSX.utils.encode_cell({ r: excelRowIndex, c: localPhotoCol })
            const cell = (ws as any)[addr] || { t: 's', v: localUrl }
            cell.t = 's'
            cell.v = localUrl
            cell.l = { Target: localUrl }
            ;(ws as any)[addr] = cell
          }
        }
      }
      XLSX.utils.book_append_sheet(wb, ws, '缺陷清单')
      const pad2 = (n: number) => String(n).padStart(2, '0')
      const d = new Date()
      const stamp = `${d.getFullYear()}${pad2(d.getMonth() + 1)}${pad2(d.getDate())}_${pad2(d.getHours())}${pad2(d.getMinutes())}`
      XLSX.writeFile(wb, `缺陷清单_${stamp}.xlsx`)
      message.success('已导出Excel')
    } catch (e: any) {
      message.error(e?.message || '导出失败')
    } finally {
      setExporting(false)
    }
  }, [exportHeaders, exportPreviewRows])

  const fetchOptions = useCallback(async (params: { type?: string, cust?: string }) => {
    const url = new URL('/api/v1/standard-defect-desc/options', window.location.origin)
    if (params.type) url.searchParams.set('type', params.type)
    if (params.cust) url.searchParams.set('cust', params.cust)
    const res = await fetch(url.toString(), { method: 'GET' })
    if (!res.ok) {
      const text = await res.text().catch(() => '')
      throw new Error(text || res.statusText)
    }
    const data = await res.json().catch(() => ({}))
    return {
      types: Array.isArray(data.types) ? data.types : [],
      custs: Array.isArray(data.custs) ? data.custs : [],
      comp_names: Array.isArray(data.comp_names) ? data.comp_names : [],
    }
  }, [])

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const url = new URL(endpoint, window.location.origin)
      url.searchParams.set('skip', '0')
      url.searchParams.set('limit', '200')
      const res = await fetch(url.toString(), { method: 'GET' })
      if (!res.ok) {
        const text = await res.text().catch(() => '')
        throw new Error(text || res.statusText)
      }
      const data = await res.json()
      setRows(Array.isArray(data) ? data : [])
    } catch (e: any) {
      message.error(e?.message || '加载失败')
      setRows([])
    } finally {
      setLoading(false)
    }
  }, [endpoint])

  const loadCheckItems = useCallback(async () => {
    if (!selectedType || !selectedCust || !selectedCompName) {
      message.error('请先选择机型、客户、部件名称')
      return
    }
    if (!activeCompNameOptionsSet.has(selectedCompName)) {
      message.error('当前功能栏仅允许选择指定的部件名称')
      return
    }
    setCheckLoading(true)
    try {
      const url = new URL('/api/v1/standard-defect-desc/match', window.location.origin)
      url.searchParams.set('type', selectedType)
      url.searchParams.set('cust', selectedCust)
      url.searchParams.set('comp_name', selectedCompName)
      const res = await fetch(url.toString(), { method: 'GET' })
      if (!res.ok) {
        const text = await res.text().catch(() => '')
        throw new Error(text || res.statusText)
      }
      const data = await res.json()
      const standardItems = Array.isArray(data) ? data : []
      const prevCustom = checkItems.filter((it) => it?.__custom)
      const nextItems = [...standardItems, ...prevCustom]
      const draft = readSingleDraft()
      const draftAnswers = draft?.answers || {}
      const draftDetails = draft?.defectDetails || {}
      const nextAnswers: Record<string, 'yes' | 'no'> = {}
      const nextDetails: Record<string, DefectDetailItem[]> = {}
      for (const it of nextItems) {
        const k = String(it.id)
        const v = draftAnswers[k] || answers[k]
        if (v === 'yes' || v === 'no') nextAnswers[k] = v
        const d = normalizeDefectDetailList(draftDetails[k] || defectDetails[k])
        if (d && (v === 'yes')) nextDetails[k] = d
      }
      setCheckItems(nextItems)
      setAnswers(nextAnswers)
      setDefectDetails(nextDetails)
      writeSingleDraft({ checkItems: nextItems, answers: nextAnswers, defectDetails: nextDetails }, false)
    } catch (e: any) {
      message.error(e?.message || '加载检查项失败')
      setCheckItems([])
      setAnswers({})
      setDefectDetails({})
    } finally {
      setCheckLoading(false)
    }
  }, [activeCompNameOptionsSet, answers, checkItems, defectDetails, readSingleDraft, selectedCompName, selectedCust, selectedType, writeSingleDraft])

  const loadBatchCheckItems = useCallback(async () => {
    if (!selectedType || !selectedCust || !selectedCompName) {
      message.error('请先选择机型、客户、部件名称')
      return
    }
    if (!activeCompNameOptionsSet.has(selectedCompName)) {
      message.error('当前功能栏仅允许选择指定的部件名称')
      return
    }
    setBatchCheckLoading(true)
    try {
      const url = new URL('/api/v1/standard-defect-desc/match', window.location.origin)
      url.searchParams.set('type', selectedType)
      url.searchParams.set('cust', selectedCust)
      url.searchParams.set('comp_name', selectedCompName)
      const res = await fetch(url.toString(), { method: 'GET' })
      if (!res.ok) {
        const text = await res.text().catch(() => '')
        throw new Error(text || res.statusText)
      }
      const data = await res.json()
      const standardItems = Array.isArray(data) ? data : []
      const prevCustom = checkItems.filter((it) => it?.__custom)
      const nextItems = [...standardItems, ...prevCustom]
      setCheckItems(nextItems)
      const nextIds = new Set(nextItems.map((it) => String(it?.id)))
      setBatchAnswers((prev) => {
        const next: Record<string, 'yes' | 'no'> = {}
        for (const [k, v] of Object.entries(prev)) {
          if (!nextIds.has(k)) continue
          if (v === 'yes' || v === 'no') next[k] = v
        }
        return next
      })
      setBatchDefectDetails((prev) => {
        const next: Record<string, DefectDetailItem[]> = {}
        for (const [k, v] of Object.entries(prev)) {
          if (!nextIds.has(k)) continue
          const list = normalizeDefectDetailList(v)
          if (list) next[k] = list
        }
        return next
      })
      message.success(`已加载检查项：${nextItems.length} 条`)
    } catch (e: any) {
      message.error(e?.message || '加载检查项失败')
      setCheckItems([])
      setBatchAnswers({})
      setBatchDefectDetails({})
    } finally {
      setBatchCheckLoading(false)
    }
  }, [activeCompNameOptionsSet, checkItems, selectedCompName, selectedCust, selectedType])

  const loadSeatCheckItems = useCallback(async () => {
    if (!selectedType || !selectedCust || !selectedCompName) {
      message.error('请先选择机型、客户、部件名称')
      return
    }
    if (!activeCompNameOptionsSet.has(selectedCompName)) {
      message.error('当前功能栏仅允许选择指定的部件名称')
      return
    }
    setSeatCheckLoading(true)
    try {
      const url = new URL('/api/v1/standard-defect-desc/match', window.location.origin)
      url.searchParams.set('type', selectedType)
      url.searchParams.set('cust', selectedCust)
      url.searchParams.set('comp_name', selectedCompName)
      const res = await fetch(url.toString(), { method: 'GET' })
      if (!res.ok) {
        const text = await res.text().catch(() => '')
        throw new Error(text || res.statusText)
      }
      const data = await res.json()
      const standardItems = Array.isArray(data) ? data : []
      setSeatCheckItems(standardItems)
      const nextIds = new Set(standardItems.map((it: any) => String(it?.id)))
      setSeatAnswers((prev) => {
        const next: Record<string, 'yes' | 'no'> = {}
        for (const [k, v] of Object.entries(prev)) {
          if (!nextIds.has(k)) continue
          if (v === 'yes' || v === 'no') next[k] = v
        }
        return next
      })
      setSeatDefectPositions((prev) => {
        const next: Record<string, string[]> = {}
        for (const [k, v] of Object.entries(prev)) {
          if (!nextIds.has(k)) continue
          const list = Array.isArray(v) ? v.filter((p) => activeSeatPositionOptionSet.has(String(p))) : []
          if (list.length > 0) next[k] = list
        }
        return next
      })
      setSeatDefectStatus((prev) => {
        const next: Record<string, string> = {}
        for (const [k, v] of Object.entries(prev)) {
          if (!nextIds.has(k)) continue
          const status = String(v || '').trim()
          if (status) next[k] = status
        }
        return next
      })
      setSeatDefectQuantity((prev) => {
        const next: Record<string, number> = {}
        for (const [k, v] of Object.entries(prev)) {
          if (!nextIds.has(k)) continue
          const qty = Number(v)
          if (Number.isFinite(qty) && qty > 0) next[k] = Math.trunc(qty)
        }
        return next
      })
      setSeatDefectPhotos((prev) => {
        const next: Record<string, { local_photo_url?: string, global_photo_url?: string }> = {}
        for (const [k, v] of Object.entries(prev)) {
          if (!nextIds.has(k)) continue
          const local = String(v?.local_photo_url || '').trim()
          const global = String(v?.global_photo_url || '').trim()
          if (local || global) next[k] = { local_photo_url: local || undefined, global_photo_url: global || undefined }
        }
        return next
      })
      message.success(`已加载检查项：${standardItems.length} 条`)
    } catch (e: any) {
      message.error(e?.message || '加载检查项失败')
      setSeatCheckItems([])
      setSeatAnswers({})
      setSeatDefectPositions({})
      setSeatDefectStatus({})
      setSeatDefectQuantity({})
      setSeatDefectPhotos({})
    } finally {
      setSeatCheckLoading(false)
    }
  }, [activeCompNameOptionsSet, activeSeatPositionOptionSet, selectedCompName, selectedCust, selectedType])

  const submitSeatCheck = useCallback(async () => {
    if (!selectedType || !selectedCust || !selectedCompName) {
      message.error('请先选择机型、客户、部件名称')
      return
    }
    if (!activeCompNameOptionsSet.has(selectedCompName)) {
      message.error('当前功能栏仅允许选择指定的部件名称')
      return
    }
    const compPn = metaCompPn.trim()
    const aircraftNo = metaAircraftNo.trim()
    const saleWo = metaSaleWo.trim()
    const planYearMonth = metaPlanYearMonth.trim()
    const loc = metaLoc.trim()
    const locForSubmit = activeKey === 'seat' ? loc : null
    const inspector = metaInspector.trim()
    if (!compPn || !aircraftNo || !saleWo || !planYearMonth || !inspector || (activeKey === 'seat' && !loc)) {
      message.error(`提交前请填写：部件件号、飞机号、销售指令号、定检年月${activeKey === 'seat' ? '、位置' : ''}、检查人`)
      return
    }
    if (seatCheckItems.length === 0) {
      message.error('没有可提交的检查项')
      return
    }
    const missingAnswer = seatCheckItems.filter((it) => !seatAnswers[String(it.id)]).length
    if (missingAnswer > 0) {
      message.error(`还有 ${missingAnswer} 条未选择 是/否`)
      return
    }
    const yesItems = seatCheckItems.filter((it) => seatAnswers[String(it.id)] === 'yes')
    const missingStatus = yesItems.filter((it) => !String(seatDefectStatus[String(it.id)] || '').trim()).length
    if (missingStatus > 0) {
      message.error(`还有 ${missingStatus} 条缺陷状态未选择`)
      return
    }
    const missingPositions = yesItems.filter((it) => (seatDefectPositions[String(it.id)] || []).length === 0).length
    if (missingPositions > 0) {
      message.error(`还有 ${missingPositions} 条缺陷位置未选择`)
      return
    }
    const payload = seatCheckItems.map((it) => {
      const k = String(it.id)
      const answer = seatAnswers[k]
      const base = {
        seq: it.seq ?? null,
        comp_pn: compPn,
        standardized_desc: it.standardized_desc ?? null,
        type: selectedType,
        cust: selectedCust,
        comp_name: selectedCompName,
        loc: locForSubmit,
        aircraft_no: aircraftNo,
        sale_wo: saleWo,
        plan_year_month: planYearMonth,
        inspector,
      }
      if (answer === 'yes') {
        const positions = (seatDefectPositions[k] || []).filter((p) => activeSeatPositionOptionSet.has(String(p)))
        const status = String(seatDefectStatus[k] || '').trim()
        const customQty = Number(seatDefectQuantity[k] ?? 0)
        const quantity = Number.isFinite(customQty) && customQty > 0 ? Math.trunc(customQty) : (positions.length > 0 ? positions.length : null)
        return {
          ...base,
          yes_flag: 1,
          no_flag: null,
          defect_status: status || null,
          defect_positions: positions.join(';') || null,
          defect_quantity: quantity,
          local_photo_url: String(seatDefectPhotos[k]?.local_photo_url || '').trim() || null,
          global_photo_url: String(seatDefectPhotos[k]?.global_photo_url || '').trim() || null,
          custom_positions_input: activeKey === 'crew-seat' ? String(crewSeatCustomPositionsInput || '').trim() || null : null,
        }
      }
      return {
        ...base,
        yes_flag: null,
        no_flag: 1,
        defect_status: null,
        defect_positions: null,
        defect_quantity: null,
        local_photo_url: null,
        global_photo_url: null,
        custom_positions_input: activeKey === 'crew-seat' ? String(crewSeatCustomPositionsInput || '').trim() || null : null,
      }
    })
    setSeatSubmitting(true)
    try {
      const endpoint = activeKey === 'crew-seat'
        ? '/api/v1/crew-seat-defect-checks/bulk?mode=replace'
        : '/api/v1/seat-defect-checks/bulk?mode=replace'
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) {
        const text = await res.text().catch(() => '')
        throw new Error(text || res.statusText)
      }
      const data = await res.json().catch(() => ({}))
      const inserted = typeof data.inserted === 'number' ? data.inserted : undefined
      const deleted = typeof data.deleted === 'number' ? data.deleted : undefined
      message.success(`提交成功${typeof inserted === 'number' ? `，写入 ${inserted} 条` : ''}${typeof deleted === 'number' ? `，覆盖删除 ${deleted} 条` : ''}`)
    } catch (e: any) {
      message.error(e?.message || '提交失败')
    } finally {
      setSeatSubmitting(false)
    }
  }, [activeCompNameOptionsSet, activeKey, activeSeatPositionOptionSet, crewSeatCustomPositionsInput, metaAircraftNo, metaCompPn, metaInspector, metaLoc, metaPlanYearMonth, metaSaleWo, seatAnswers, seatCheckItems, seatDefectPhotos, seatDefectPositions, seatDefectQuantity, seatDefectStatus, selectedCompName, selectedCust, selectedType])

  const submitBatchCheck = useCallback(async () => {
    if (!selectedType || !selectedCust || !selectedCompName) {
      message.error('请先选择机型、客户、部件名称')
      return
    }
    if (!activeCompNameOptionsSet.has(selectedCompName)) {
      message.error('当前功能栏仅允许选择指定的部件名称')
      return
    }
    const compPn = metaCompPn.trim()
    const aircraftNo = metaAircraftNo.trim()
    const saleWo = metaSaleWo.trim()
    const planYearMonth = metaPlanYearMonth.trim()
    if (!compPn || !aircraftNo || !saleWo || !planYearMonth) {
      message.error('提交前请填写：部件件号、飞机号、销售指令号、定检年月')
      return
    }
    if (checkItems.length === 0) {
      message.error('没有可提交的检查项')
      return
    }
    const missingDesc = checkItems.filter((it) => !String(it?.standardized_desc || '').trim()).length
    if (missingDesc > 0) {
      message.error(`还有 ${missingDesc} 条缺陷描述为空，请补全后再提交`)
      return
    }
    const missing = checkItems.filter((it) => !batchAnswers[String(it.id)]).length
    if (missing > 0) {
      message.error(`还有 ${missing} 条未选择 是/否`)
      return
    }
    const payload = checkItems.flatMap<any>((it) => {
      const k = String(it.id)
      const v = batchAnswers[k]
      const base = {
        seq: it.seq ?? null,
        comp_pn: compPn,
        standardized_desc: it.standardized_desc ?? null,
        type: selectedType,
        cust: selectedCust,
        comp_name: selectedCompName,
        aircraft_no: aircraftNo,
        sale_wo: saleWo,
        plan_year_month: planYearMonth,
      }
      if (v === 'yes') {
        const list = batchDefectDetails[k] || []
        if (list.length === 0) {
          return [{
            ...base,
            yes_flag: 1,
            no_flag: null,
            defect_status: null,
            defect_positions: null,
            defect_quantity: null,
            local_photo_url: null,
            global_photo_url: null,
          }]
        }
        return list.map((d) => ({
          ...base,
          yes_flag: 1,
          no_flag: null,
          defect_status: String(d.defect_status || '').trim() || null,
          defect_positions: String(d.defect_positions || '').trim() || null,
          defect_quantity: Number(d.defect_quantity) > 0 ? Number(d.defect_quantity) : null,
          local_photo_url: String(d.local_photo_url || '').trim() || null,
          global_photo_url: String(d.global_photo_url || '').trim() || null,
        }))
      }
      return [{
        ...base,
        yes_flag: null,
        no_flag: 1,
        defect_status: null,
        defect_positions: null,
        defect_quantity: null,
        local_photo_url: null,
        global_photo_url: null,
      }]
    })

    setBatchSubmitting(true)
    try {
      const res = await fetch('/api/v1/batch-defect-checks/bulk?mode=replace', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) {
        const text = await res.text().catch(() => '')
        throw new Error(text || res.statusText)
      }
      const data = await res.json().catch(() => ({}))
      const inserted = typeof data.inserted === 'number' ? data.inserted : undefined
      const deleted = typeof data.deleted === 'number' ? data.deleted : undefined
      message.success(`提交成功${typeof inserted === 'number' ? `，写入 ${inserted} 条` : ''}${typeof deleted === 'number' ? `，覆盖删除 ${deleted} 条` : ''}`)
    } catch (e: any) {
      message.error(e?.message || '提交失败')
    } finally {
      setBatchSubmitting(false)
    }
  }, [activeCompNameOptionsSet, batchAnswers, batchDefectDetails, checkItems, metaAircraftNo, metaCompPn, metaPlanYearMonth, metaSaleWo, selectedCompName, selectedCust, selectedType])

  const addCustomCheckItem = useCallback(() => {
    setCustomDraftSeq('')
    setCustomDraftDesc('')
    setCustomModalOpen(true)
  }, [])

  const saveCustomCheckItem = useCallback(() => {
    const desc = customDraftDesc.trim()
    if (!desc) {
      message.error('请输入自定义缺陷描述')
      return
    }
    const seqRaw = customDraftSeq.trim()
    let seq: number | null = null
    if (seqRaw) {
      const n = Number(seqRaw)
      if (!Number.isFinite(n)) {
        message.error('序号必须是数字')
        return
      }
      seq = Math.trunc(n)
    }
    const id = `custom-${Date.now()}-${Math.random().toString(16).slice(2)}`
    const item = {
      id,
      seq,
      comp_pn: null,
      standardized_desc: desc,
      type: null,
      cust: null,
      comp_name: null,
      __custom: true,
    }
    setCheckItems((prev) => {
      const next = [...prev, item]
      if (activeKey === 'single') writeSingleDraft({ checkItems: next }, true)
      return next
    })
    setCustomModalOpen(false)
    message.success('已添加到清单')
  }, [activeKey, customDraftDesc, customDraftSeq, writeSingleDraft])

  const submitSingleCheck = useCallback(async () => {
    if (!selectedType || !selectedCust || !selectedCompName) {
      message.error('请先选择机型、客户、部件名称')
      return
    }
    if (!activeCompNameOptionsSet.has(selectedCompName)) {
      message.error('当前功能栏仅允许选择指定的部件名称')
      return
    }
    const compPn = metaCompPn.trim()
    const aircraftNo = metaAircraftNo.trim()
    const saleWo = metaSaleWo.trim()
    const planYearMonth = metaPlanYearMonth.trim()
    const loc = metaLoc.trim()
    const inspector = metaInspector.trim()
    if (!compPn || !aircraftNo || !saleWo || !planYearMonth || !loc || !inspector) {
      message.error('提交前请填写：部件件号、飞机号、销售指令号、定检年月、位置、检查人')
      return
    }
    if (checkItems.length === 0) {
      message.error('没有可提交的检查项')
      return
    }
    const emptyCustom = checkItems.filter((it) => it?.__custom && !(String(it?.standardized_desc || '').trim())).length
    if (emptyCustom > 0) {
      message.error(`还有 ${emptyCustom} 条自定义描述未填写内容`)
      return
    }
    const missing = checkItems.filter((it) => !answers[String(it.id)]).length
    if (missing > 0) {
      message.error(`还有 ${missing} 条未选择 是/否`)
      return
    }
    setSubmitting(true)
    try {
      const payload = checkItems.flatMap<any>((it) => {
        const k = String(it.id)
        const v = answers[k]
        const base = {
          seq: it.seq ?? null,
          comp_pn: compPn,
          standardized_desc: it.standardized_desc ?? null,
          type: selectedType,
          cust: selectedCust,
          comp_name: selectedCompName,
          loc,
          aircraft_no: aircraftNo,
          sale_wo: saleWo,
          plan_year_month: planYearMonth,
          inspector,
        }
        if (v === 'yes') {
          const list = defectDetails[k] || []
          if (list.length === 0) {
            return [{
              ...base,
              yes_flag: 1,
              no_flag: null,
              defect_status: null,
              defect_positions: null,
              defect_quantity: null,
              local_photo_url: null,
              global_photo_url: null,
            }]
          }
          return list.map((d) => ({
            ...base,
            yes_flag: 1,
            no_flag: null,
            defect_status: String(d.defect_status || '').trim() || null,
            defect_positions: String(d.defect_positions || '').trim() || null,
            defect_quantity: Number(d.defect_quantity) > 0 ? Number(d.defect_quantity) : null,
            local_photo_url: String(d.local_photo_url || '').trim() || null,
            global_photo_url: String(d.global_photo_url || '').trim() || null,
          }))
        }
        return [{
          ...base,
          yes_flag: null,
          no_flag: 1,
          defect_status: null,
          defect_positions: null,
          defect_quantity: null,
          local_photo_url: null,
          global_photo_url: null,
        }]
      })
      const res = await fetch('/api/v1/single-defect-checks/bulk?mode=replace', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) {
        const text = await res.text().catch(() => '')
        throw new Error(text || res.statusText)
      }
      const data = await res.json().catch(() => ({}))
      const inserted = typeof data.inserted === 'number' ? data.inserted : undefined
      const deleted = typeof data.deleted === 'number' ? data.deleted : undefined
      message.success(`提交成功${typeof inserted === 'number' ? `，写入 ${inserted} 条` : ''}${typeof deleted === 'number' ? `，覆盖删除 ${deleted} 条` : ''}`)
      const customItems = checkItems.filter((it) => it?.__custom)
      if (customItems.length > 0) {
        const customPayload = customItems.map((it) => ({
          seq: it.seq ?? null,
          comp_pn: compPn,
          standardized_desc: String(it.standardized_desc || '').trim(),
          type: selectedType,
          cust: selectedCust,
          comp_name: selectedCompName,
        }))
        const cr = await fetch('/api/v1/custom-defect-desc/bulk', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(customPayload),
        })
        if (cr.ok) {
          const cd = await cr.json().catch(() => ({}))
          const ci = typeof cd.inserted === 'number' ? cd.inserted : 0
          const cs = typeof cd.skipped_duplicates === 'number' ? cd.skipped_duplicates : 0
          message.success(`自定义描述入库：新增 ${ci} 条${cs > 0 ? `，跳过重复 ${cs} 条` : ''}`)
        } else {
          const text = await cr.text().catch(() => '')
          message.warning(text || '自定义描述入库失败')
        }
      }
      clearSingleDraft()
    } catch (e: any) {
      message.error(e?.message || '提交失败')
    } finally {
      setSubmitting(false)
    }
  }, [activeCompNameOptionsSet, answers, checkItems, clearSingleDraft, defectDetails, metaAircraftNo, metaCompPn, metaInspector, metaLoc, metaPlanYearMonth, metaSaleWo, selectedCompName, selectedCust, selectedType])

  const openDetailModal = useCallback((scope: 'single' | 'batch', k: string, prevAnswer?: 'yes' | 'no') => {
    setDetailModalKey(k)
    setDetailModalScope(scope)
    setDetailModalPrevAnswer(prevAnswer)
    const existing = scope === 'single' ? defectDetails[k] : batchDefectDetails[k]
    const list = normalizeDefectDetailList(existing) || []
    if (list.length > 0) {
      setDetailDrafts(list.map((d) => ({
        defect_status: d.defect_status || '破损',
        defect_positions: d.defect_positions,
        defect_quantity: Number(d.defect_quantity) > 0 ? Number(d.defect_quantity) : splitDefectPositions(d.defect_positions).length,
        local_photo_url: String(d.local_photo_url || ''),
        global_photo_url: String(d.global_photo_url || ''),
      })))
    } else {
      setDetailDrafts([{ defect_status: '破损', defect_positions: '', defect_quantity: undefined, local_photo_url: '', global_photo_url: '' }])
    }
    setDetailModalOpen(true)
  }, [batchDefectDetails, defectDetails])

  const closeDetailModal = useCallback((opts?: { revertAnswer?: boolean }) => {
    const k = detailModalKey
    const prev = detailModalPrevAnswer
    const scope = detailModalScope
    setDetailModalOpen(false)
    setDetailModalKey(null)
    setDetailModalPrevAnswer(undefined)
    setDetailDrafts([])
    if (opts?.revertAnswer && k) {
      if (scope === 'single') {
        setAnswers((prevAnswers) => {
          const next = { ...prevAnswers }
          if (prev) next[k] = prev
          else delete next[k]
          writeSingleDraft({ answers: next }, true)
          return next
        })
      } else {
        setBatchAnswers((prevAnswers) => {
          const next = { ...prevAnswers }
          if (prev) next[k] = prev
          else delete next[k]
          return next
        })
      }
    }
  }, [detailModalKey, detailModalPrevAnswer, detailModalScope, writeSingleDraft])

  const resolvePhotoSrc = useCallback((u: string) => {
    const s = String(u || '').trim()
    if (!s) return ''
    try {
      return new URL(s, window.location.origin).toString()
    } catch {
      return s
    }
  }, [])

  const uploadDefectPhoto = useCallback(async (kind: 'local' | 'global', file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    const url = new URL('/api/v1/standard-defect-desc/defect-photos/upload', window.location.origin)
    url.searchParams.set('kind', kind)
    const res = await fetch(url.toString(), { method: 'POST', body: formData })
    if (!res.ok) {
      const text = await res.text().catch(() => '')
      throw new Error(text || res.statusText)
    }
    const data = await res.json().catch(() => ({}))
    const photoUrl = String(data?.url || '').trim()
    if (!photoUrl) throw new Error('上传失败：未返回图片地址')
    return photoUrl
  }, [])
  const saveEditModal = useCallback(async () => {
    if (!editRow) {
      setEditModalOpen(false)
      return
    }
    try {
      let url = ''
      let payload: any = {}
      if (editModalScope === 'catalog') {
        url = `/api/v1/standard-defect-desc/${editRow.id}`
        payload = {
          seq: editDraft.seq ?? null,
          comp_pn: String(editDraft.comp_pn || '').trim() || null,
          standardized_desc: String(editDraft.standardized_desc || '').trim() || null,
          type: String(editDraft.type || '').trim() || null,
          cust: String(editDraft.cust || '').trim() || null,
          comp_name: String(editDraft.comp_name || '').trim() || null,
        }
      } else if (editModalScope === 'single') {
        url = `/api/v1/single-defect-checks/${editRow.id}`
        const forceYes = activeKey === 'export'
        const yes = forceYes ? 1 : (editDraft.yes_flag ? 1 : 0)
        const no = forceYes ? 0 : (editDraft.no_flag ? 1 : 0)
        const pos = String(editDraft.defect_positions || '').trim()
        payload = {
          seq: editDraft.seq ?? null,
          comp_pn: String(editDraft.comp_pn || '').trim() || null,
          standardized_desc: String(editDraft.standardized_desc || '').trim() || null,
          type: String(editDraft.type || '').trim() || null,
          cust: String(editDraft.cust || '').trim() || null,
          comp_name: String(editDraft.comp_name || '').trim() || null,
          loc: String(editDraft.loc || '').trim() || null,
          inspector: String(editDraft.inspector || '').trim() || null,
          aircraft_no: String(editDraft.aircraft_no || '').trim() || null,
          sale_wo: String(editDraft.sale_wo || '').trim() || null,
          plan_year_month: String(editDraft.plan_year_month || '').trim() || null,
          yes_flag: yes ? 1 : null,
          no_flag: no ? 1 : null,
          defect_status: yes ? (String(editDraft.defect_status || '').trim() || null) : null,
          defect_positions: yes ? (pos || null) : null,
          defect_quantity: yes ? (Number(editDraft.defect_quantity ?? editDraft.quantity ?? 0) || null) : null,
          local_photo_url: yes ? (String(editDraft.local_photo_url || '').trim() || null) : null,
          global_photo_url: yes ? (String(editDraft.global_photo_url || '').trim() || null) : null,
        }
      } else {
        url = `/api/v1/batch-defect-checks/${editRow.id}`
        const forceYes = activeKey === 'export'
        const yes = forceYes ? 1 : (editDraft.yes_flag ? 1 : 0)
        const no = forceYes ? 0 : (editDraft.no_flag ? 1 : 0)
        const posRaw = String(editDraft.defect_positions || editDraft.position || '').trim()
        const pos = posRaw || null
        const qty = Number(editDraft.defect_quantity ?? editDraft.quantity ?? 0)
        payload = {
          seq: editDraft.seq ?? null,
          comp_pn: String(editDraft.comp_pn || '').trim() || null,
          standardized_desc: String(editDraft.standardized_desc || '').trim() || null,
          type: String(editDraft.type || '').trim() || null,
          cust: String(editDraft.cust || '').trim() || null,
          comp_name: String(editDraft.comp_name || '').trim() || null,
          aircraft_no: String(editDraft.aircraft_no || '').trim() || null,
          sale_wo: String(editDraft.sale_wo || '').trim() || null,
          plan_year_month: String(editDraft.plan_year_month || '').trim() || null,
          yes_flag: yes ? 1 : null,
          no_flag: no ? 1 : null,
          defect_status: yes ? (String(editDraft.defect_status || '').trim() || null) : null,
          defect_positions: yes ? pos : null,
          defect_quantity: yes ? (qty || null) : null,
          position: yes ? pos : null,
          quantity: yes ? (qty || null) : null,
          local_photo_url: yes ? (String(editDraft.local_photo_url || '').trim() || null) : null,
          global_photo_url: yes ? (String(editDraft.global_photo_url || '').trim() || null) : null,
        }
      }
      const res = await fetch(url, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) {
        const text = await res.text().catch(() => '')
        throw new Error(text || res.statusText)
      }
      const data = await res.json().catch(() => ({}))
      if (activeKey === 'export') {
        await runExportPreview()
      } else {
        setRows((prev) => prev.map((r) => (r.id === data?.id ? data : r)))
      }
      setEditModalOpen(false)
      setEditRow(null)
      setEditDraft({})
      message.success('已保存')
    } catch (e: any) {
      message.error(e?.message || '保存失败')
    }
  }, [activeKey, editDraft, editModalScope, editRow, runExportPreview])

  const pickAndUploadDefectPhoto = useCallback(async (opts: { kind: 'local' | 'global', capture?: 'environment' | 'user' }) => {
    return new Promise<string>((resolve, reject) => {
      const input = document.createElement('input')
      input.type = 'file'
      input.accept = 'image/*'
      input.multiple = false
      if (opts.capture) {
        input.setAttribute('capture', opts.capture)
      }
      input.onchange = async () => {
        try {
          const f = input.files?.[0]
          if (!f) {
            reject(new Error('未选择图片'))
            return
          }
          const url = await uploadDefectPhoto(opts.kind, f)
          resolve(url)
        } catch (e: any) {
          reject(e)
        } finally {
          input.value = ''
        }
      }
      input.click()
    })
  }, [uploadDefectPhoto])

  const saveDetailModal = useCallback(() => {
    const k = detailModalKey
    if (!k) return
    const list: DefectDetailItem[] = []
    for (const d of detailDrafts) {
      const status = String(d?.defect_status || '').trim()
      const positions = splitDefectPositions(String(d?.defect_positions || ''))
      const localPhotoUrl = String(d?.local_photo_url || '').trim()
      const globalPhotoUrl = String(d?.global_photo_url || '').trim()
      const inputQty = Number(d?.defect_quantity ?? 0)
      const quantity = Number.isFinite(inputQty) && inputQty > 0 ? Math.trunc(inputQty) : (positions.length > 0 ? positions.length : 0)
      list.push({
        defect_status: status,
        defect_positions: positions.join(';'),
        defect_quantity: quantity,
        local_photo_url: localPhotoUrl || undefined,
        global_photo_url: globalPhotoUrl || undefined,
      })
    }
    if (detailModalScope === 'single') {
      setDefectDetails((prev) => {
        const next = { ...prev, [k]: list }
        writeSingleDraft({ defectDetails: next }, true)
        return next
      })
    } else {
      setBatchDefectDetails((prev) => ({ ...prev, [k]: list }))
    }
    closeDetailModal()
  }, [closeDetailModal, detailDrafts, detailModalKey, detailModalScope, writeSingleDraft])

  const downloadCatalog = useCallback(async () => {
    try {
      const res = await fetch('/api/v1/standard-defect-desc/export', { method: 'GET' })
      if (!res.ok) {
        const text = await res.text().catch(() => '')
        throw new Error(text || res.statusText)
      }
      const blob = await res.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'standard_defect_desc.csv'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
    } catch (e: any) {
      message.error(e?.message || '下载失败')
    }
  }, [])

  const onChooseFile = useCallback(() => {
    fileInputRef.current?.click()
  }, [])

  const onUploadFile = useCallback(async (file: File) => {
    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await fetch('/api/v1/standard-defect-desc/import?mode=append', {
        method: 'POST',
        body: formData,
      })
      if (!res.ok) {
        const text = await res.text().catch(() => '')
        throw new Error(text || res.statusText)
      }
      const data = await res.json().catch(() => ({}))
      const inserted = typeof data.inserted === 'number' ? data.inserted : undefined
      const skippedDuplicates = typeof data.skipped_duplicates === 'number' ? data.skipped_duplicates : undefined
      const skippedInvalid = typeof data.skipped_invalid === 'number' ? data.skipped_invalid : undefined
      const parts: string[] = []
      if (typeof inserted === 'number') parts.push(`导入 ${inserted} 条`)
      if (typeof skippedDuplicates === 'number' && skippedDuplicates > 0) parts.push(`跳过重复 ${skippedDuplicates} 条`)
      if (typeof skippedInvalid === 'number' && skippedInvalid > 0) parts.push(`跳过缺字段 ${skippedInvalid} 条`)
      message.success(`上传成功${parts.length ? `，${parts.join('，')}` : ''}`)
      await loadData()
    } catch (e: any) {
      message.error(e?.message || '上传失败')
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }, [loadData])

  useEffect(() => {
    setSiderCollapsed(isMobile)
  }, [isMobile])

  useEffect(() => {
    if (activeKey !== 'single' && activeKey !== 'seat' && activeKey !== 'crew-seat' && activeKey !== 'export') {
      loadData()
    }
  }, [activeKey, loadData])

  useEffect(() => {
    if (activeKey !== 'single') return
    isRestoringDraftRef.current = true
    const draft = readSingleDraft()
    if (draft) {
      setSelectedType(draft.selectedType || undefined)
      setSelectedCust(draft.selectedCust || undefined)
      setSelectedCompName(draft.selectedCompName || undefined)
      setMetaCompPn(draft.metaCompPn || '')
      setMetaAircraftNo(draft.metaAircraftNo || '')
      setMetaSaleWo(draft.metaSaleWo || '')
      setMetaPlanYearMonth(draft.metaPlanYearMonth || '')
      setMetaLoc(draft.metaLoc || '')
      setMetaInspector(draft.metaInspector || '')
      setMetaCollapsed(Boolean(draft.metaCollapsed))
      setCheckItems(Array.isArray(draft.checkItems) ? draft.checkItems : [])
      setAnswers(draft.answers || {})
      const next: Record<string, DefectDetailItem[]> = {}
      const raw = draft.defectDetails || {}
      if (raw && typeof raw === 'object') {
        for (const [k, v] of Object.entries(raw)) {
          const list = normalizeDefectDetailList(v)
          if (list) next[k] = list
        }
      }
      setDefectDetails(next)
    } else {
      setSelectedType(undefined)
      setSelectedCust(undefined)
      setSelectedCompName(undefined)
      setMetaCompPn('')
      setMetaAircraftNo('')
      setMetaSaleWo('')
      setMetaPlanYearMonth('')
      setMetaLoc('')
      setMetaInspector('')
      setMetaCollapsed(false)
      setCustOptions([])
      setCompNameOptions([])
      setCheckItems([])
      setAnswers({})
      setDefectDetails({})
    }
    ;(async () => {
      try {
        const opts = await fetchOptions({})
        setTypeOptions(opts.types)
      } catch (e: any) {
        message.error(e?.message || '加载选项失败')
        setTypeOptions([])
      }
    })()
    window.setTimeout(() => {
      isRestoringDraftRef.current = false
    }, 0)
  }, [activeKey, fetchOptions, readSingleDraft])

  useEffect(() => {
    if (activeKey !== 'single' && activeKey !== 'batch' && activeKey !== 'seat' && activeKey !== 'crew-seat') return
    if (!selectedType || custOptions.length > 0) return
    ;(async () => {
      try {
        const opts = await fetchOptions({ type: selectedType })
        setCustOptions(opts.custs)
      } catch {
        setCustOptions([])
      }
    })()
  }, [activeKey, custOptions.length, fetchOptions, selectedType])

  useEffect(() => {
    if (activeKey !== 'single' && activeKey !== 'batch' && activeKey !== 'seat' && activeKey !== 'crew-seat') return
    if (!selectedType || !selectedCust || compNameOptions.length > 0) return
    ;(async () => {
      try {
        const opts = await fetchOptions({ type: selectedType, cust: selectedCust })
        setCompNameOptions(opts.comp_names)
      } catch {
        setCompNameOptions([])
      }
    })()
  }, [activeKey, compNameOptions.length, fetchOptions, selectedCust, selectedType])

  useEffect(() => {
    if (activeKey !== 'single') return
    if (isRestoringDraftRef.current) return
    if (autosaveTimerRef.current) window.clearTimeout(autosaveTimerRef.current)
    autosaveTimerRef.current = window.setTimeout(() => {
      writeSingleDraft(undefined, false)
    }, 350)
    return () => {
      if (autosaveTimerRef.current) window.clearTimeout(autosaveTimerRef.current)
    }
  }, [activeKey, answers, checkItems, defectDetails, metaAircraftNo, metaCollapsed, metaCompPn, metaInspector, metaLoc, metaPlanYearMonth, metaSaleWo, selectedCompName, selectedCust, selectedType, writeSingleDraft])

  useEffect(() => {
    if (activeKey !== 'seat' && activeKey !== 'crew-seat') return
    if (typeOptions.length > 0) return
    ;(async () => {
      try {
        const opts = await fetchOptions({})
        setTypeOptions(opts.types)
      } catch {
        setTypeOptions([])
      }
    })()
  }, [activeKey, fetchOptions, typeOptions.length])

  useEffect(() => {
    if (!selectedCompName) return
    if (activeCompNameOptionsSet.has(selectedCompName)) return
    setSelectedCompName(undefined)
  }, [activeCompNameOptionsSet, selectedCompName])

  useEffect(() => {
    if (activeKey !== 'seat' && activeKey !== 'crew-seat') return
    setSeatDefectPositions((prev) => {
      let changed = false
      const next: Record<string, string[]> = {}
      for (const [k, vals] of Object.entries(prev)) {
        const filtered = vals.filter((v) => activeSeatPositionOptionSet.has(v))
        if (filtered.length !== vals.length) changed = true
        if (filtered.length > 0) next[k] = filtered
      }
      return changed ? next : prev
    })
  }, [activeKey, activeSeatPositionOptionSet])

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        theme="light"
        width={260}
        style={{
          overflow: 'auto',
          borderRight: '1px solid #f0f0f0'
        }}
        breakpoint="md"
        collapsedWidth={0}
        collapsed={siderCollapsed}
        onCollapse={(collapsed) => setSiderCollapsed(collapsed)}
      >
        <div style={{ height: 64, display: 'flex', alignItems: 'center', padding: '0 16px', borderBottom: '1px solid #f0f0f0' }}>
          <Title level={4} style={{ margin: 0 }}>缺陷检查</Title>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[activeKey]}
          onClick={(e) => {
            setActiveKey(e.key)
            if (isMobile) setSiderCollapsed(true)
          }}
          items={items}
          style={{ borderRight: 0 }}
        />
      </Sider>
      <Layout>
        <div style={{ padding: '16px 16px', background: '#fff', borderBottom: '1px solid #f0f0f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {isMobile && (
              <Button type="text" icon={<MenuOutlined />} onClick={() => setSiderCollapsed(false)} />
            )}
            <Title level={4} style={{ margin: 0 }}>
              {activeLabel}
            </Title>
          </div>
          <Button type="text" icon={<HomeOutlined />} onClick={() => navigate('/')} />
        </div>
        <Content style={{ padding: 24, background: '#f0f2f5', minHeight: 'calc(100vh - 64px)' }}>
          <Modal
            title="编辑记录"
            open={editModalOpen}
            onOk={saveEditModal}
            onCancel={() => {
              setEditModalOpen(false)
              setEditRow(null)
            }}
            okText="保存"
            cancelText="取消"
            destroyOnClose
          >
            <Form layout="vertical">
              {editModalScope === 'catalog' && (
                <>
                  <Form.Item label="序号">
                    <InputNumber value={editDraft.seq} onChange={(v) => setEditDraft((p: any) => ({ ...p, seq: v }))} style={{ width: '100%' }} />
                  </Form.Item>
                  <Form.Item label="部件件号">
                    <Input value={editDraft.comp_pn} onChange={(e) => setEditDraft((p: any) => ({ ...p, comp_pn: e.target.value }))} />
                  </Form.Item>
                  <Form.Item label="标准化描述">
                    <Input.TextArea value={editDraft.standardized_desc} onChange={(e) => setEditDraft((p: any) => ({ ...p, standardized_desc: e.target.value }))} autoSize={{ minRows: 3, maxRows: 8 }} />
                  </Form.Item>
                  <Row gutter={12}>
                    <Col span={8}>
                      <Form.Item label="机型">
                        <Input value={editDraft.type} onChange={(e) => setEditDraft((p: any) => ({ ...p, type: e.target.value }))} />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item label="客户">
                        <Input value={editDraft.cust} onChange={(e) => setEditDraft((p: any) => ({ ...p, cust: e.target.value }))} />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item label="部件名称">
                        <Input value={editDraft.comp_name} onChange={(e) => setEditDraft((p: any) => ({ ...p, comp_name: e.target.value }))} />
                      </Form.Item>
                    </Col>
                  </Row>
                </>
              )}
              {editModalScope === 'single' && (
                <>
                  <Form.Item label="部件件号">
                    <Input value={editDraft.comp_pn} onChange={(e) => setEditDraft((p: any) => ({ ...p, comp_pn: e.target.value }))} />
                  </Form.Item>
                  <Form.Item label="缺陷描述">
                    <Input.TextArea value={editDraft.standardized_desc} onChange={(e) => setEditDraft((p: any) => ({ ...p, standardized_desc: e.target.value }))} autoSize={{ minRows: 2, maxRows: 6 }} />
                  </Form.Item>
                  <Row gutter={12}>
                    <Col span={8}>
                      <Form.Item label="机型">
                        <Input value={editDraft.type} onChange={(e) => setEditDraft((p: any) => ({ ...p, type: e.target.value }))} />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item label="客户">
                        <Input value={editDraft.cust} onChange={(e) => setEditDraft((p: any) => ({ ...p, cust: e.target.value }))} />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item label="部件名称">
                        <Input value={editDraft.comp_name} onChange={(e) => setEditDraft((p: any) => ({ ...p, comp_name: e.target.value }))} />
                      </Form.Item>
                    </Col>
                  </Row>
                  <Row gutter={12}>
                    <Col span={12}>
                      <Form.Item label="检查位置">
                        <Input value={editDraft.loc} onChange={(e) => setEditDraft((p: any) => ({ ...p, loc: e.target.value }))} />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item label="检查人">
                        <Input value={editDraft.inspector} onChange={(e) => setEditDraft((p: any) => ({ ...p, inspector: e.target.value }))} />
                      </Form.Item>
                    </Col>
                  </Row>
                  <Row gutter={12}>
                    <Col span={8}>
                      <Form.Item label="飞机号">
                        <Input value={editDraft.aircraft_no} onChange={(e) => setEditDraft((p: any) => ({ ...p, aircraft_no: e.target.value }))} />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item label="销售指令号">
                        <Input value={editDraft.sale_wo} onChange={(e) => setEditDraft((p: any) => ({ ...p, sale_wo: e.target.value }))} />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item label="定检年月">
                        <Input value={editDraft.plan_year_month} onChange={(e) => setEditDraft((p: any) => ({ ...p, plan_year_month: e.target.value }))} />
                      </Form.Item>
                    </Col>
                  </Row>
                  {!(activeKey === 'export') && (
                    <Form.Item label="是否缺陷">
                      <Radio.Group
                        value={editDraft.yes_flag ? 'yes' : 'no'}
                        onChange={(e) => {
                          const v = e.target.value
                          setEditDraft((p: any) => ({
                            ...p,
                            yes_flag: v === 'yes' ? 1 : null,
                            no_flag: v === 'no' ? 1 : null,
                          }))
                        }}
                      >
                        <Radio value="yes">是</Radio>
                        <Radio value="no">否</Radio>
                      </Radio.Group>
                    </Form.Item>
                  )}
                  {(activeKey === 'export' || editDraft.yes_flag) ? (
                    <>
                      <Form.Item label="缺陷状态">
                        <Input value={editDraft.defect_status} onChange={(e) => setEditDraft((p: any) => ({ ...p, defect_status: e.target.value }))} />
                      </Form.Item>
                      <Form.Item label="缺陷位置">
                        <Input.TextArea value={editDraft.defect_positions} onChange={(e) => setEditDraft((p: any) => ({ ...p, defect_positions: e.target.value }))} autoSize={{ minRows: 2, maxRows: 6 }} />
                      </Form.Item>
                      <Row gutter={12}>
                        <Col span={12}>
                          <Form.Item label="局部照片">
                            <Input value={editDraft.local_photo_url} onChange={(e) => setEditDraft((p: any) => ({ ...p, local_photo_url: e.target.value }))} />
                          </Form.Item>
                        </Col>
                        <Col span={12}>
                          <Form.Item label="全局照片">
                            <Input value={editDraft.global_photo_url} onChange={(e) => setEditDraft((p: any) => ({ ...p, global_photo_url: e.target.value }))} />
                          </Form.Item>
                        </Col>
                      </Row>
                    </>
                  ) : null}
                </>
              )}
              {editModalScope === 'batch' && (
                <>
                  <Form.Item label="部件件号">
                    <Input value={editDraft.comp_pn} onChange={(e) => setEditDraft((p: any) => ({ ...p, comp_pn: e.target.value }))} />
                  </Form.Item>
                  <Form.Item label="缺陷描述">
                    <Input.TextArea value={editDraft.standardized_desc} onChange={(e) => setEditDraft((p: any) => ({ ...p, standardized_desc: e.target.value }))} autoSize={{ minRows: 2, maxRows: 6 }} />
                  </Form.Item>
                  <Row gutter={12}>
                    <Col span={8}>
                      <Form.Item label="机型">
                        <Input value={editDraft.type} onChange={(e) => setEditDraft((p: any) => ({ ...p, type: e.target.value }))} />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item label="客户">
                        <Input value={editDraft.cust} onChange={(e) => setEditDraft((p: any) => ({ ...p, cust: e.target.value }))} />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item label="部件名称">
                        <Input value={editDraft.comp_name} onChange={(e) => setEditDraft((p: any) => ({ ...p, comp_name: e.target.value }))} />
                      </Form.Item>
                    </Col>
                  </Row>
                  <Row gutter={12}>
                    <Col span={8}>
                      <Form.Item label="飞机号">
                        <Input value={editDraft.aircraft_no} onChange={(e) => setEditDraft((p: any) => ({ ...p, aircraft_no: e.target.value }))} />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item label="销售指令号">
                        <Input value={editDraft.sale_wo} onChange={(e) => setEditDraft((p: any) => ({ ...p, sale_wo: e.target.value }))} />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item label="定检年月">
                        <Input value={editDraft.plan_year_month} onChange={(e) => setEditDraft((p: any) => ({ ...p, plan_year_month: e.target.value }))} />
                      </Form.Item>
                    </Col>
                  </Row>
                  <Row gutter={12}>
                    <Col span={16}>
                      <Form.Item label="位置">
                        <Input value={editDraft.position ?? editDraft.defect_positions} onChange={(e) => setEditDraft((p: any) => ({ ...p, position: e.target.value, defect_positions: e.target.value }))} />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item label="数量">
                        <InputNumber value={editDraft.quantity ?? editDraft.defect_quantity} min={0} style={{ width: '100%' }} onChange={(v) => setEditDraft((p: any) => ({ ...p, quantity: v, defect_quantity: v }))} />
                      </Form.Item>
                    </Col>
                  </Row>
                  {!(activeKey === 'export') && (
                    <Form.Item label="是否缺陷">
                      <Radio.Group
                        value={editDraft.yes_flag ? 'yes' : 'no'}
                        onChange={(e) => {
                          const v = e.target.value
                          setEditDraft((p: any) => ({
                            ...p,
                            yes_flag: v === 'yes' ? 1 : null,
                            no_flag: v === 'no' ? 1 : null,
                          }))
                        }}
                      >
                        <Radio value="yes">是</Radio>
                        <Radio value="no">否</Radio>
                      </Radio.Group>
                    </Form.Item>
                  )}
                  {(activeKey === 'export' || editDraft.yes_flag) ? (
                    <>
                      <Form.Item label="缺陷状态">
                        <Input value={editDraft.defect_status} onChange={(e) => setEditDraft((p: any) => ({ ...p, defect_status: e.target.value }))} />
                      </Form.Item>
                      <Row gutter={12}>
                        <Col span={12}>
                          <Form.Item label="局部照片">
                            <Input value={editDraft.local_photo_url} onChange={(e) => setEditDraft((p: any) => ({ ...p, local_photo_url: e.target.value }))} />
                          </Form.Item>
                        </Col>
                        <Col span={12}>
                          <Form.Item label="全局照片">
                            <Input value={editDraft.global_photo_url} onChange={(e) => setEditDraft((p: any) => ({ ...p, global_photo_url: e.target.value }))} />
                          </Form.Item>
                        </Col>
                      </Row>
                    </>
                  ) : null}
                </>
              )}
            </Form>
          </Modal>
          {activeKey === 'single' ? (
            <Space direction="vertical" size={12} style={{ width: '100%' }}>
              <Modal
                title="新增自定义缺陷描述"
                open={customModalOpen}
                onOk={saveCustomCheckItem}
                onCancel={() => setCustomModalOpen(false)}
                okText="保存"
                cancelText="取消"
                destroyOnClose
              >
                <Form layout="vertical">
                  <Form.Item label="序号（可选）">
                    <Input placeholder="例如：1" value={customDraftSeq} onChange={(e) => setCustomDraftSeq(e.target.value)} />
                  </Form.Item>
                  <Form.Item label="自定义缺陷描述" required>
                    <Input.TextArea
                      placeholder="请输入自定义缺陷描述"
                      value={customDraftDesc}
                      autoSize={{ minRows: 3, maxRows: 8 }}
                      onChange={(e) => setCustomDraftDesc(e.target.value)}
                    />
                  </Form.Item>
                </Form>
              </Modal>
              <Modal
                title="缺陷明细"
                open={detailModalOpen}
                onOk={saveDetailModal}
                onCancel={() => {
                  const k = detailModalKey
                  const prev = detailModalPrevAnswer
                  const hasExisting = k ? Boolean(defectDetails[k]?.length) : false
                  closeDetailModal({ revertAnswer: !hasExisting && prev !== 'yes' })
                }}
                okText="保存"
                cancelText="取消"
                destroyOnClose
              >
                <Form layout="vertical">
                  {detailDrafts.map((d, idx) => {
                    const autoQty = splitDefectPositions(d.defect_positions).length
                    const qty = Number(d.defect_quantity) > 0 ? Number(d.defect_quantity) : autoQty
                    return (
                      <div key={idx} style={{ border: '1px solid #f0f0f0', borderRadius: 8, padding: 12, marginBottom: 12 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                          <div style={{ fontWeight: 600 }}>明细 {idx + 1}</div>
                          <Button
                            size="small"
                            danger
                            disabled={detailDrafts.length <= 1}
                            onClick={() => setDetailDrafts((prev) => prev.filter((_, i) => i !== idx))}
                          >
                            删除
                          </Button>
                        </div>
                        <Form.Item label="缺陷状态" style={{ marginBottom: 12 }}>
                          <Row gutter={8}>
                            <Col span={10}>
                              <Select
                                placeholder="选择预设"
                                value={defectStatusOptions.includes(d.defect_status) ? d.defect_status : undefined}
                                allowClear
                                showSearch
                                optionFilterProp="label"
                                listHeight={160}
                                options={defectStatusOptions.map((v) => ({ label: v, value: v }))}
                                onChange={(v) => {
                                  setDetailDrafts((prev) => prev.map((p, i) => (i === idx ? { ...p, defect_status: String(v || '') } : p)))
                                }}
                              />
                            </Col>
                            <Col span={14}>
                              <Input
                                placeholder="或输入自定义缺陷状态"
                                value={defectStatusOptions.includes(d.defect_status) ? '' : d.defect_status}
                                onChange={(e) => {
                                  const v = e.target.value
                                  setDetailDrafts((prev) => prev.map((p, i) => (i === idx ? { ...p, defect_status: v } : p)))
                                }}
                              />
                            </Col>
                          </Row>
                        </Form.Item>
                        <Form.Item label="具体位置" style={{ marginBottom: 12 }}>
                          <Input.TextArea
                            placeholder="用 ; 或 | 或 换行分隔，例如：LH1;LH2;LH3"
                            value={d.defect_positions}
                            autoSize={{ minRows: 3, maxRows: 8 }}
                            onChange={(e) => {
                              const v = e.target.value
                              setDetailDrafts((prev) => prev.map((p, i) => {
                                if (i !== idx) return p
                                const prevAutoQty = splitDefectPositions(String(p.defect_positions || '')).length
                                const nextAutoQty = splitDefectPositions(v).length
                                const currentQty = Number(p.defect_quantity ?? 0)
                                if (!(currentQty > 0) || currentQty === prevAutoQty) {
                                  return { ...p, defect_positions: v, defect_quantity: nextAutoQty > 0 ? nextAutoQty : undefined }
                                }
                                return { ...p, defect_positions: v }
                              }))
                            }}
                          />
                        </Form.Item>
                        <Row gutter={12}>
                          <Col xs={24} sm={12}>
                            <Form.Item label="局部照片" style={{ marginBottom: 12 }}>
                              <Space>
                                <Button
                                  icon={<UploadOutlined />}
                                  onClick={async () => {
                                    try {
                                      const url = await pickAndUploadDefectPhoto({ kind: 'local', capture: 'environment' })
                                      setDetailDrafts((prev) => prev.map((p, i) => (i === idx ? { ...p, local_photo_url: url } : p)))
                                      message.success('局部照片已上传')
                                    } catch (e: any) {
                                      const msg = String(e?.message || '').trim()
                                      if (msg && msg !== '未选择图片') message.error(msg)
                                    }
                                  }}
                                >
                                  拍照
                                </Button>
                                <Button
                                  onClick={async () => {
                                    try {
                                      const url = await pickAndUploadDefectPhoto({ kind: 'local' })
                                      setDetailDrafts((prev) => prev.map((p, i) => (i === idx ? { ...p, local_photo_url: url } : p)))
                                      message.success('局部照片已上传')
                                    } catch (e: any) {
                                      const msg = String(e?.message || '').trim()
                                      if (msg && msg !== '未选择图片') message.error(msg)
                                    }
                                  }}
                                >
                                  相册
                                </Button>
                              </Space>
                              {d.local_photo_url && (
                                <div style={{ marginTop: 8 }}>
                                  <img
                                    src={resolvePhotoSrc(d.local_photo_url)}
                                    style={{ width: '100%', maxHeight: 160, objectFit: 'contain', border: '1px solid #f0f0f0', borderRadius: 6 }}
                                  />
                                  <Space size={8}>
                                    <Button type="link" onClick={() => window.open(resolvePhotoSrc(d.local_photo_url), '_blank')}>
                                      预览
                                    </Button>
                                    <Button
                                      type="link"
                                      danger
                                      onClick={() => setDetailDrafts((prev) => prev.map((p, i) => (i === idx ? { ...p, local_photo_url: '' } : p)))}
                                    >
                                      清除
                                    </Button>
                                  </Space>
                                </div>
                              )}
                            </Form.Item>
                          </Col>
                          <Col xs={24} sm={12}>
                            <Form.Item label="全局照片" style={{ marginBottom: 12 }}>
                              <Space>
                                <Button
                                  icon={<UploadOutlined />}
                                  onClick={async () => {
                                    try {
                                      const url = await pickAndUploadDefectPhoto({ kind: 'global', capture: 'environment' })
                                      setDetailDrafts((prev) => prev.map((p, i) => (i === idx ? { ...p, global_photo_url: url } : p)))
                                      message.success('全局照片已上传')
                                    } catch (e: any) {
                                      const msg = String(e?.message || '').trim()
                                      if (msg && msg !== '未选择图片') message.error(msg)
                                    }
                                  }}
                                >
                                  拍照
                                </Button>
                                <Button
                                  onClick={async () => {
                                    try {
                                      const url = await pickAndUploadDefectPhoto({ kind: 'global' })
                                      setDetailDrafts((prev) => prev.map((p, i) => (i === idx ? { ...p, global_photo_url: url } : p)))
                                      message.success('全局照片已上传')
                                    } catch (e: any) {
                                      const msg = String(e?.message || '').trim()
                                      if (msg && msg !== '未选择图片') message.error(msg)
                                    }
                                  }}
                                >
                                  相册
                                </Button>
                              </Space>
                              {d.global_photo_url && (
                                <div style={{ marginTop: 8 }}>
                                  <img
                                    src={resolvePhotoSrc(d.global_photo_url)}
                                    style={{ width: '100%', maxHeight: 160, objectFit: 'contain', border: '1px solid #f0f0f0', borderRadius: 6 }}
                                  />
                                  <Space size={8}>
                                    <Button type="link" onClick={() => window.open(resolvePhotoSrc(d.global_photo_url), '_blank')}>
                                      预览
                                    </Button>
                                    <Button
                                      type="link"
                                      danger
                                      onClick={() => setDetailDrafts((prev) => prev.map((p, i) => (i === idx ? { ...p, global_photo_url: '' } : p)))}
                                    >
                                      清除
                                    </Button>
                                  </Space>
                                </div>
                              )}
                            </Form.Item>
                          </Col>
                        </Row>
                        <Form.Item label="数量" style={{ marginBottom: 0 }}>
                          <InputNumber value={qty || undefined} min={0} precision={0} style={{ width: '100%' }} onChange={(v) => setDetailDrafts((prev) => prev.map((p, i) => (i === idx ? { ...p, defect_quantity: Number(v) > 0 ? Number(v) : undefined } : p)))} />
                        </Form.Item>
                      </div>
                    )
                  })}
                  <Button
                    onClick={() =>
                      setDetailDrafts((prev) => [
                        ...(prev.length ? prev : [{ defect_status: '破损', defect_positions: '', defect_quantity: undefined, local_photo_url: '', global_photo_url: '' }]),
                        { defect_status: '破损', defect_positions: '', defect_quantity: undefined, local_photo_url: '', global_photo_url: '' },
                      ])
                    }
                    style={{ width: '100%' }}
                  >
                    新增一条明细
                  </Button>
                </Form>
              </Modal>
              <Card
                title="飞机与部件信息"
                extra={
                  <Button
                    type="link"
                    onClick={() => {
                      setMetaCollapsed((v) => {
                        const next = !v
                        writeSingleDraft({ metaCollapsed: next }, false)
                        return next
                      })
                    }}
                  >
                    {metaCollapsed ? '展开' : '收起'}
                  </Button>
                }
              >
                {!metaCollapsed && (
                  <Form layout="vertical">
                    <Row gutter={12}>
                    <Col xs={12} sm={12}>
                      <Form.Item label="机型（type）" required>
                        <Select
                          placeholder="请选择机型"
                          value={selectedType}
                          allowClear
                          showSearch
                          optionFilterProp="label"
                          onChange={async (v) => {
                            const nextType = v || undefined
                            setSelectedType(nextType)
                            setSelectedCust(undefined)
                            setSelectedCompName(undefined)
                            setCustOptions([])
                            setCompNameOptions([])
                            setCheckItems([])
                            setAnswers({})
                            setDefectDetails({})
                            if (!nextType) return
                            try {
                              const opts = await fetchOptions({ type: nextType })
                              setCustOptions(opts.custs)
                            } catch (e: any) {
                              message.error(e?.message || '加载客户选项失败')
                              setCustOptions([])
                            }
                          }}
                          options={typeOptions.map((t) => ({ value: t, label: t }))}
                        />
                      </Form.Item>
                    </Col>
                    <Col xs={12} sm={12}>
                      <Form.Item label="客户（cust）" required>
                        <Select
                          placeholder="请选择客户"
                          value={selectedCust}
                          allowClear
                          showSearch
                          optionFilterProp="label"
                          disabled={!selectedType}
                          onChange={async (v) => {
                            const nextCust = v || undefined
                            setSelectedCust(nextCust)
                            setSelectedCompName(undefined)
                            setCompNameOptions([])
                            setCheckItems([])
                            setAnswers({})
                            setDefectDetails({})
                            if (!selectedType || !nextCust) return
                            try {
                              const opts = await fetchOptions({ type: selectedType, cust: nextCust })
                              setCompNameOptions(opts.comp_names)
                            } catch (e: any) {
                              message.error(e?.message || '加载部件名称选项失败')
                              setCompNameOptions([])
                            }
                          }}
                          options={custOptions.map((c) => ({ value: c, label: c }))}
                        />
                      </Form.Item>
                    </Col>
                    <Col xs={12} sm={12}>
                      <Form.Item label="部件名称（comp_name）" required>
                        <Select
                          placeholder="请选择部件名称"
                          value={selectedCompName}
                          allowClear
                          showSearch
                          optionFilterProp="label"
                          disabled={!selectedType || !selectedCust}
                          onChange={(v) => {
                            const nextName = v || undefined
                            setSelectedCompName(nextName)
                            setCheckItems([])
                            setAnswers({})
                            setDefectDetails({})
                          }}
                          options={activeCompNameOptions.map((n) => ({ value: n, label: n }))}
                        />
                      </Form.Item>
                    </Col>
                    <Col xs={12} sm={12}>
                      <Form.Item label="部件件号（comp_pn）" required>
                        <Input placeholder="请输入部件件号" value={metaCompPn} onChange={(e) => setMetaCompPn(e.target.value)} />
                      </Form.Item>
                    </Col>
                    <Col xs={12} sm={12}>
                      <Form.Item label="飞机号（aircraft_no）" required>
                        <Input placeholder="请输入飞机号" value={metaAircraftNo} onChange={(e) => setMetaAircraftNo(e.target.value)} />
                      </Form.Item>
                    </Col>
                    <Col xs={12} sm={12}>
                      <Form.Item label="销售指令号（sale_wo）" required>
                        <Input placeholder="请输入销售指令号" value={metaSaleWo} onChange={(e) => setMetaSaleWo(e.target.value)} />
                      </Form.Item>
                    </Col>
                    <Col xs={12} sm={12}>
                      <Form.Item label="定检年月（plan_year_month）" required>
                        <Input placeholder="例如：2026-03" value={metaPlanYearMonth} onChange={(e) => setMetaPlanYearMonth(e.target.value)} />
                      </Form.Item>
                    </Col>
                    <Col xs={12} sm={12}>
                      <Form.Item label="位置（loc）" required>
                        <Input placeholder="请输入位置" value={metaLoc} onChange={(e) => setMetaLoc(e.target.value)} />
                      </Form.Item>
                    </Col>
                    <Col xs={12} sm={12}>
                      <Form.Item label="检查人（inspector）" required>
                        <Input placeholder="请输入检查人" value={metaInspector} onChange={(e) => setMetaInspector(e.target.value)} />
                      </Form.Item>
                    </Col>
                    </Row>
                  </Form>
                )}
              </Card>

              <Card title="检查详情信息" bodyStyle={{ padding: 0 }}>
                <div style={{ position: 'sticky', top: 0, zIndex: 10, background: '#fff', borderBottom: '1px solid #f0f0f0' }}>
                  <div style={{ padding: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
                    <div style={{ color: '#666', whiteSpace: 'nowrap' }}>
                      {checkItems.length > 0 ? `共 ${checkItems.length} 条，已判断 ${Object.keys(answers).length} 条，未判断 ${checkItems.length - Object.keys(answers).length} 条` : '请选择后加载检查项'}
                    </div>
                    <Space wrap>
                      <Select
                        style={{ width: 150 }}
                        value={singleFilter}
                        onChange={(v) => setSingleFilter(v as 'all' | 'pending' | 'checked')}
                        options={[
                          { label: '全部', value: 'all' },
                          { label: '仅未判断', value: 'pending' },
                          { label: '仅已判断', value: 'checked' },
                        ]}
                      />
                      <Button
                        type="link"
                        onClick={() => {
                          setMetaCollapsed((v) => {
                            const next = !v
                            writeSingleDraft({ metaCollapsed: next }, false)
                            return next
                          })
                        }}
                      >
                        {metaCollapsed ? '展开信息' : '收起信息'}
                      </Button>
                      <Button onClick={loadCheckItems} loading={checkLoading} type="primary">
                        加载检查项
                      </Button>
                      <Button onClick={addCustomCheckItem} disabled={!selectedType || !selectedCust || !selectedCompName}>
                        新增自定义描述
                      </Button>
                      <Button
                        onClick={submitSingleCheck}
                        loading={submitting}
                        disabled={checkItems.length === 0}
                        type="primary"
                      >
                        提交
                      </Button>
                    </Space>
                  </div>
                </div>
                <List
                  loading={checkLoading}
                  dataSource={filteredSingleCheckItems}
                  renderItem={(item) => {
                    const k = String(item.id)
                    const value = answers[k]
                    const displayPn = metaCompPn.trim() || item.comp_pn
                    const seqPrefix = item.seq ? `${item.seq}、` : ''
                    const detailList = defectDetails[k] || []
                    const detailStatuses = Array.from(new Set(detailList.map((d) => String(d.defect_status || '').trim()).filter(Boolean)))
                    const detailLocs = Array.from(new Set(detailList.flatMap((d) => splitDefectPositions(String(d.defect_positions || '')))))
                    const singlePreview = `${String(item?.standardized_desc || '').trim()}${detailStatuses.length ? ` ${detailStatuses.join(' ')}` : ''}，loc：${detailLocs.length ? detailLocs.join(' ') : '未选择'}`
                    return (
                      <List.Item style={{ padding: isMobile ? 0 : 12, marginBottom: isMobile ? 12 : 0 }}>
                        <div style={{ width: '100%', ...(isMobile ? { border: '1px solid #f0f0f0', borderRadius: 10, padding: 12, background: '#fff' } : {}) }}>
                          <div style={{ fontWeight: 600 }}>
                            {displayPn ? `（${displayPn}）` : ''}
                          </div>
                          <div style={{ marginTop: 8, whiteSpace: 'pre-wrap' }}>
                            {item?.__custom ? (
                              <div style={{ display: 'flex', gap: 8 }}>
                                {seqPrefix ? <div style={{ whiteSpace: 'nowrap' }}>{seqPrefix}</div> : null}
                                <Input.TextArea
                                  placeholder="请输入自定义缺陷描述"
                                  value={String(item.standardized_desc || '')}
                                  autoSize={{ minRows: 2, maxRows: 6 }}
                                  style={{ flex: 1 }}
                                  onChange={(e) => {
                                    const v = e.target.value
                                    setCheckItems((prev) => {
                                      const next = prev.map((p) => (String(p.id) === k ? { ...p, standardized_desc: v } : p))
                                      writeSingleDraft({ checkItems: next }, false)
                                      return next
                                    })
                                  }}
                                />
                              </div>
                            ) : (
                              `${seqPrefix}${String(item.standardized_desc || '')}`
                            )}
                          </div>
                          <div style={{ marginTop: 10, display: 'flex', justifyContent: isMobile ? 'stretch' : 'flex-end' }}>
                            <Radio.Group
                              value={value}
                              onChange={(e) => {
                                const v = e.target.value as 'yes' | 'no'
                                if (v === 'no') {
                                  setAnswers((prev) => {
                                    const next = { ...prev, [k]: 'no' as const }
                                    writeSingleDraft({ answers: next }, true)
                                    return next
                                  })
                                  setDefectDetails((prev) => {
                                    if (!prev[k]) return prev
                                    const next = { ...prev }
                                    delete next[k]
                                    writeSingleDraft({ defectDetails: next }, true)
                                    return next
                                  })
                                  return
                                }
                                const prevAnswer = answers[k]
                                setAnswers((prev) => {
                                  const next = { ...prev, [k]: 'yes' as const }
                                  writeSingleDraft({ answers: next }, true)
                                  return next
                                })
                                openDetailModal('single', k, prevAnswer)
                              }}
                              optionType="button"
                              buttonStyle="solid"
                              style={{ width: isMobile ? '100%' : undefined, display: 'flex' }}
                            >
                              <Radio.Button value="yes" style={{ flex: isMobile ? 1 : undefined, textAlign: 'center' }}>是</Radio.Button>
                              <Radio.Button value="no" style={{ flex: isMobile ? 1 : undefined, textAlign: 'center' }}>否</Radio.Button>
                            </Radio.Group>
                          </div>
                          {value === 'yes' && (
                            <div style={{ marginTop: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
                              <div style={{ color: '#666' }}>
                                缺陷描述预览：{singlePreview}
                              </div>
                              <Button size="small" onClick={() => openDetailModal('single', k, 'yes')}>
                                {defectDetails[k]?.length ? '修改明细' : '填写明细'}
                              </Button>
                            </div>
                          )}
                          {item?.__custom && (
                            <div style={{ marginTop: 8, display: 'flex', justifyContent: 'flex-end' }}>
                              <Button
                                size="small"
                                danger
                                onClick={() => {
                                  setCheckItems((prev) => prev.filter((p) => String(p.id) !== k))
                                  setAnswers((prev) => {
                                    const next = { ...prev }
                                    delete next[k]
                                    return next
                                  })
                                  setDefectDetails((prev) => {
                                    if (!prev[k]) return prev
                                    const next = { ...prev }
                                    delete next[k]
                                    writeSingleDraft({ defectDetails: next }, true)
                                    return next
                                  })
                                }}
                              >
                                移除
                              </Button>
                            </div>
                          )}
                        </div>
                      </List.Item>
                    )
                  }}
                />
              </Card>
            </Space>
          ) : activeKey === 'seat' || activeKey === 'crew-seat' ? (
            <Space direction="vertical" size={12} style={{ width: '100%' }}>
              <Card
                title="飞机与部件信息"
                extra={
                  <Button
                    type="link"
                    onClick={() => {
                      setSeatMetaCollapsed((v) => !v)
                    }}
                  >
                    {seatMetaCollapsed ? '展开' : '收起'}
                  </Button>
                }
              >
                {!seatMetaCollapsed && (
                  <Form layout="vertical">
                    <Row gutter={12}>
                      <Col xs={12} sm={12}>
                        <Form.Item label="机型（type）" required>
                          <Select
                            placeholder="请选择机型"
                            value={selectedType}
                            allowClear
                            showSearch
                            optionFilterProp="label"
                            onChange={async (v) => {
                              const nextType = v || undefined
                              setSelectedType(nextType)
                              setSelectedCust(undefined)
                              setSelectedCompName(undefined)
                              setCustOptions([])
                              setCompNameOptions([])
                              setSeatCheckItems([])
                              setSeatAnswers({})
                              setSeatDefectPositions({})
                              setSeatDefectStatus({})
                              setSeatDefectQuantity({})
                              setSeatDefectPhotos({})
                              if (!nextType) return
                              try {
                                const opts = await fetchOptions({ type: nextType })
                                setCustOptions(opts.custs)
                              } catch (e: any) {
                                message.error(e?.message || '加载客户选项失败')
                                setCustOptions([])
                              }
                            }}
                            options={typeOptions.map((t) => ({ value: t, label: t }))}
                          />
                        </Form.Item>
                      </Col>
                      <Col xs={12} sm={12}>
                        <Form.Item label="客户（cust）" required>
                          <Select
                            placeholder="请选择客户"
                            value={selectedCust}
                            allowClear
                            showSearch
                            optionFilterProp="label"
                            disabled={!selectedType}
                            onChange={async (v) => {
                              const nextCust = v || undefined
                              setSelectedCust(nextCust)
                              setSelectedCompName(undefined)
                              setCompNameOptions([])
                              setSeatCheckItems([])
                              setSeatAnswers({})
                              setSeatDefectPositions({})
                              setSeatDefectStatus({})
                              setSeatDefectQuantity({})
                              setSeatDefectPhotos({})
                              if (!selectedType || !nextCust) return
                              try {
                                const opts = await fetchOptions({ type: selectedType, cust: nextCust })
                                setCompNameOptions(opts.comp_names)
                              } catch (e: any) {
                                message.error(e?.message || '加载部件名称选项失败')
                                setCompNameOptions([])
                              }
                            }}
                            options={custOptions.map((c) => ({ value: c, label: c }))}
                          />
                        </Form.Item>
                      </Col>
                      <Col xs={12} sm={12}>
                        <Form.Item label="部件名称（comp_name）" required>
                          <Select
                            placeholder="请选择部件名称"
                            value={selectedCompName}
                            allowClear
                            showSearch
                            optionFilterProp="label"
                            disabled={!selectedType || !selectedCust}
                            onChange={(v) => {
                              const nextName = v || undefined
                              setSelectedCompName(nextName)
                              setSeatCheckItems([])
                              setSeatAnswers({})
                              setSeatDefectPositions({})
                              setSeatDefectStatus({})
                              setSeatDefectQuantity({})
                              setSeatDefectPhotos({})
                              if (activeKey === 'crew-seat') setCrewSeatCustomPositionsInput('')
                            }}
                            options={activeCompNameOptions.map((n) => ({ value: n, label: n }))}
                          />
                        </Form.Item>
                      </Col>
                      <Col xs={12} sm={12}>
                        <Form.Item label="部件件号（comp_pn）" required>
                          <Input placeholder="请输入部件件号" value={metaCompPn} onChange={(e) => setMetaCompPn(e.target.value)} />
                        </Form.Item>
                      </Col>
                      <Col xs={12} sm={12}>
                        <Form.Item label="飞机号（aircraft_no）" required>
                          <Input placeholder="请输入飞机号" value={metaAircraftNo} onChange={(e) => setMetaAircraftNo(e.target.value)} />
                        </Form.Item>
                      </Col>
                      <Col xs={12} sm={12}>
                        <Form.Item label="销售指令号（sale_wo）" required>
                          <Input placeholder="请输入销售指令号" value={metaSaleWo} onChange={(e) => setMetaSaleWo(e.target.value)} />
                        </Form.Item>
                      </Col>
                      <Col xs={12} sm={12}>
                        <Form.Item label="定检年月（plan_year_month）" required>
                          <Input placeholder="例如：2026-03" value={metaPlanYearMonth} onChange={(e) => setMetaPlanYearMonth(e.target.value)} />
                        </Form.Item>
                      </Col>
                      {activeKey === 'seat' && (
                        <Col xs={12} sm={12}>
                          <Form.Item label="座椅位置（seat loc）" required>
                            <Input placeholder="请输入位置" value={metaLoc} onChange={(e) => setMetaLoc(e.target.value)} />
                          </Form.Item>
                        </Col>
                      )}
                      <Col xs={12} sm={12}>
                        <Form.Item label="检查人（inspector）" required>
                          <Input placeholder="请输入检查人" value={metaInspector} onChange={(e) => setMetaInspector(e.target.value)} />
                        </Form.Item>
                      </Col>
                    </Row>
                  </Form>
                )}
              </Card>

              <Card title="检查详情信息" bodyStyle={{ padding: 0 }}>
                <div style={{ position: 'sticky', top: 0, zIndex: 10, background: '#fff', borderBottom: '1px solid #f0f0f0' }}>
                  <div style={{ padding: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                    <div style={{ color: '#666' }}>
                      {seatCheckItems.length > 0 ? `共 ${seatCheckItems.length} 条，已判断 ${Object.keys(seatAnswers).length} 条，未判断 ${seatCheckItems.length - Object.keys(seatAnswers).length} 条` : '请选择后加载检查项'}
                    </div>
                    <Space wrap>
                      <Select
                        style={{ width: 150 }}
                        value={seatFilter}
                        onChange={(v) => setSeatFilter(v as 'all' | 'pending' | 'checked')}
                        options={[
                          { label: '全部', value: 'all' },
                          { label: '仅未判断', value: 'pending' },
                          { label: '仅已判断', value: 'checked' },
                        ]}
                      />
                      <Button onClick={loadSeatCheckItems} loading={seatCheckLoading} type="primary">
                        加载检查项
                      </Button>
                      <Button onClick={submitSeatCheck} loading={seatSubmitting} disabled={seatCheckItems.length === 0} type="primary">
                        提交
                      </Button>
                    </Space>
                  </div>
                  <div style={{ padding: '0 12px 12px', color: '#666' }}>
                    飞机与部件位置信息：{metaLoc.trim() || '未填写'}
                  </div>
                  {activeKey === 'crew-seat' && selectedCompName === '乘务员座椅' && (
                    <div style={{ padding: '0 12px 12px' }}>
                      <Form.Item label="自定义位置输入（用 ; 分隔）" style={{ marginBottom: 0 }}>
                        <Input
                          placeholder="例如：乘务员位1;乘务员位2;乘务员位3"
                          value={crewSeatCustomPositionsInput}
                          onChange={(e) => setCrewSeatCustomPositionsInput(e.target.value)}
                        />
                      </Form.Item>
                    </div>
                  )}
                </div>
                <List
                  loading={seatCheckLoading}
                  dataSource={filteredSeatCheckItems}
                  renderItem={(item) => {
                    const k = String(item.id)
                    const value = seatAnswers[k]
                    const displayPn = metaCompPn.trim() || item.comp_pn
                    const seqPrefix = item.seq ? `${item.seq}、` : ''
                    const status = seatDefectStatus[k] || ''
                    const selectedPositions = seatDefectPositions[k] || []
                    const customQty = Number(seatDefectQuantity[k] ?? 0)
                    const seatQty = Number.isFinite(customQty) && customQty > 0 ? Math.trunc(customQty) : selectedPositions.length
                    const seatLocBase = activeKey === 'seat' ? (metaLoc.trim() || '未填写') : ''
                    const seatLocDetail = activeKey === 'seat'
                      ? sortSeatPreviewPositions(selectedPositions).join('')
                      : (selectedPositions.length > 0 ? selectedPositions.join(' ') : '')
                    const seatLocPreview = activeKey === 'seat'
                      ? `${seatLocBase}${seatLocDetail}`
                      : (seatLocDetail || '未选择')
                    const seatPreview = `${String(item?.standardized_desc || '').trim()}${status ? `${status}` : ''}，LOC：${seatLocPreview}，QTY：${seatQty > 0 ? seatQty : 0} EA`
                    return (
                      <List.Item style={{ padding: isMobile ? 0 : 12, marginBottom: isMobile ? 12 : 0 }}>
                        <div style={{ width: '100%', ...(isMobile ? { border: '1px solid #f0f0f0', borderRadius: 10, padding: 12, background: '#fff' } : {}) }}>
                          <div style={{ fontWeight: 600 }}>
                            {displayPn ? `（${displayPn}）` : ''}
                          </div>
                          <div style={{ marginTop: 8, whiteSpace: 'pre-wrap' }}>
                            {`${seqPrefix}${String(item.standardized_desc || '')}`}
                          </div>
                          <div style={{ marginTop: 10, display: 'flex', justifyContent: isMobile ? 'stretch' : 'flex-end' }}>
                            <Radio.Group
                              value={value}
                              onChange={(e) => {
                                const v = e.target.value as 'yes' | 'no'
                                setSeatAnswers((prev) => ({ ...prev, [k]: v }))
                                if (v === 'no') {
                                  setSeatDefectPositions((prev) => {
                                    if (!prev[k]) return prev
                                    const next = { ...prev }
                                    delete next[k]
                                    return next
                                  })
                                  setSeatDefectStatus((prev) => {
                                    if (!prev[k]) return prev
                                    const next = { ...prev }
                                    delete next[k]
                                    return next
                                  })
                                  setSeatDefectQuantity((prev) => {
                                    if (!(k in prev)) return prev
                                    const next = { ...prev }
                                    delete next[k]
                                    return next
                                  })
                                  setSeatDefectPhotos((prev) => {
                                    if (!prev[k]) return prev
                                    const next = { ...prev }
                                    delete next[k]
                                    return next
                                  })
                                }
                              }}
                              optionType="button"
                              buttonStyle="solid"
                              style={{ width: isMobile ? '100%' : undefined, display: 'flex' }}
                            >
                              <Radio.Button value="yes" style={{ flex: isMobile ? 1 : undefined, textAlign: 'center' }}>是</Radio.Button>
                              <Radio.Button value="no" style={{ flex: isMobile ? 1 : undefined, textAlign: 'center' }}>否</Radio.Button>
                            </Radio.Group>
                          </div>
                          {value === 'yes' && (
                            <div style={{ marginTop: 10 }}>
                              <Form.Item label="缺陷照片（可选）" style={{ marginBottom: 8 }}>
                                <Space>
                                  <Button
                                    icon={<UploadOutlined />}
                                    onClick={() => {
                                      const draft = seatDefectPhotos[k] || {}
                                      setSeatPhotoModalKey(k)
                                      setSeatPhotoDraft({
                                        local_photo_url: String(draft.local_photo_url || ''),
                                        global_photo_url: String(draft.global_photo_url || ''),
                                      })
                                      setSeatPhotoModalOpen(true)
                                    }}
                                  >
                                    拍照/相册
                                  </Button>
                                  {(String(seatDefectPhotos[k]?.local_photo_url || '').trim() || String(seatDefectPhotos[k]?.global_photo_url || '').trim())
                                    ? <span style={{ color: '#52c41a' }}>已上传照片</span>
                                    : <span style={{ color: '#999' }}>可选上传局部/全局照片</span>}
                                </Space>
                              </Form.Item>
                              <Form.Item label="缺陷位置（可多选）" required style={{ marginBottom: 8 }}>
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                                  {activeSeatPositionOptions.map((p) => {
                                    const selected = selectedPositions.includes(p)
                                    return (
                                      <Button
                                        key={p}
                                        size="small"
                                        style={{
                                          minWidth: 34,
                                          background: selected ? '#1677ff' : '#fff',
                                          color: selected ? '#fff' : 'rgba(0,0,0,0.88)',
                                          borderColor: selected ? '#1677ff' : '#d9d9d9',
                                        }}
                                        onClick={() => {
                                          const current = seatDefectPositions[k] || []
                                          const next = current.includes(p) ? current.filter((x) => x !== p) : [...current, p]
                                          setSeatDefectPositions((prev) => ({ ...prev, [k]: next }))
                                        }}
                                      >
                                        {p}
                                      </Button>
                                    )
                                  })}
                                </div>
                              </Form.Item>
                              <Form.Item label="缺陷状态（必选一）" required style={{ marginBottom: 6 }}>
                                <Radio.Group
                                  value={status || undefined}
                                  onChange={(e) => {
                                    const v = String(e.target.value || '').trim()
                                    setSeatDefectStatus((prev) => ({ ...prev, [k]: v }))
                                  }}
                                >
                                  <Space wrap>
                                    {defectStatusOptions.map((s) => (
                                      <Radio key={s} value={s}>{s}</Radio>
                                    ))}
                                  </Space>
                                </Radio.Group>
                              </Form.Item>
                              <Form.Item label="缺陷数量（可自定义）" style={{ marginBottom: 6 }}>
                                <InputNumber
                                  min={1}
                                  precision={0}
                                  style={{ width: '100%' }}
                                  value={seatQty > 0 ? seatQty : undefined}
                                  onChange={(v) => {
                                    const qty = Number(v ?? 0)
                                    if (Number.isFinite(qty) && qty > 0) {
                                      setSeatDefectQuantity((prev) => ({ ...prev, [k]: Math.trunc(qty) }))
                                      return
                                    }
                                    setSeatDefectQuantity((prev) => {
                                      if (!(k in prev)) return prev
                                      const next = { ...prev }
                                      delete next[k]
                                      return next
                                    })
                                  }}
                                />
                              </Form.Item>
                              <div style={{ color: '#666' }}>
                                缺陷描述预览：{seatPreview}
                              </div>
                            </div>
                          )}
                        </div>
                      </List.Item>
                    )
                  }}
                />
              </Card>
              <Modal
                title="缺陷照片"
                open={seatPhotoModalOpen}
                onOk={() => {
                  const k = seatPhotoModalKey
                  if (!k) {
                    setSeatPhotoModalOpen(false)
                    return
                  }
                  const localPhoto = String(seatPhotoDraft.local_photo_url || '').trim()
                  const globalPhoto = String(seatPhotoDraft.global_photo_url || '').trim()
                  if (!localPhoto && !globalPhoto) {
                    setSeatDefectPhotos((prev) => {
                      if (!prev[k]) return prev
                      const next = { ...prev }
                      delete next[k]
                      return next
                    })
                  } else {
                    setSeatDefectPhotos((prev) => ({
                      ...prev,
                      [k]: {
                        local_photo_url: localPhoto || undefined,
                        global_photo_url: globalPhoto || undefined,
                      },
                    }))
                  }
                  setSeatPhotoModalOpen(false)
                  setSeatPhotoModalKey(null)
                  setSeatPhotoDraft({ local_photo_url: '', global_photo_url: '' })
                }}
                onCancel={() => {
                  setSeatPhotoModalOpen(false)
                  setSeatPhotoModalKey(null)
                  setSeatPhotoDraft({ local_photo_url: '', global_photo_url: '' })
                }}
                okText="保存"
                cancelText="取消"
                destroyOnClose
              >
                <Form layout="vertical">
                  <Row gutter={12}>
                    <Col xs={24} sm={12}>
                      <Form.Item label="局部照片（可选）" style={{ marginBottom: 12 }}>
                        <Space>
                          <Button
                            icon={<UploadOutlined />}
                            onClick={async () => {
                              try {
                                const url = await pickAndUploadDefectPhoto({ kind: 'local', capture: 'environment' })
                                setSeatPhotoDraft((prev) => ({ ...prev, local_photo_url: url }))
                                message.success('局部照片已上传')
                              } catch (e: any) {
                                const msg = String(e?.message || '').trim()
                                if (msg && msg !== '未选择图片') message.error(msg)
                              }
                            }}
                          >
                            拍照
                          </Button>
                          <Button
                            onClick={async () => {
                              try {
                                const url = await pickAndUploadDefectPhoto({ kind: 'local' })
                                setSeatPhotoDraft((prev) => ({ ...prev, local_photo_url: url }))
                                message.success('局部照片已上传')
                              } catch (e: any) {
                                const msg = String(e?.message || '').trim()
                                if (msg && msg !== '未选择图片') message.error(msg)
                              }
                            }}
                          >
                            相册
                          </Button>
                        </Space>
                        {seatPhotoDraft.local_photo_url && (
                          <div style={{ marginTop: 8 }}>
                            <img
                              src={resolvePhotoSrc(seatPhotoDraft.local_photo_url)}
                              style={{ width: '100%', maxHeight: 160, objectFit: 'contain', border: '1px solid #f0f0f0', borderRadius: 6 }}
                            />
                            <Space size={8}>
                              <Button type="link" onClick={() => window.open(resolvePhotoSrc(seatPhotoDraft.local_photo_url), '_blank')}>
                                预览
                              </Button>
                              <Button
                                type="link"
                                danger
                                onClick={() => setSeatPhotoDraft((prev) => ({ ...prev, local_photo_url: '' }))}
                              >
                                清除
                              </Button>
                            </Space>
                          </div>
                        )}
                      </Form.Item>
                    </Col>
                    <Col xs={24} sm={12}>
                      <Form.Item label="全局照片（可选）" style={{ marginBottom: 12 }}>
                        <Space>
                          <Button
                            icon={<UploadOutlined />}
                            onClick={async () => {
                              try {
                                const url = await pickAndUploadDefectPhoto({ kind: 'global', capture: 'environment' })
                                setSeatPhotoDraft((prev) => ({ ...prev, global_photo_url: url }))
                                message.success('全局照片已上传')
                              } catch (e: any) {
                                const msg = String(e?.message || '').trim()
                                if (msg && msg !== '未选择图片') message.error(msg)
                              }
                            }}
                          >
                            拍照
                          </Button>
                          <Button
                            onClick={async () => {
                              try {
                                const url = await pickAndUploadDefectPhoto({ kind: 'global' })
                                setSeatPhotoDraft((prev) => ({ ...prev, global_photo_url: url }))
                                message.success('全局照片已上传')
                              } catch (e: any) {
                                const msg = String(e?.message || '').trim()
                                if (msg && msg !== '未选择图片') message.error(msg)
                              }
                            }}
                          >
                            相册
                          </Button>
                        </Space>
                        {seatPhotoDraft.global_photo_url && (
                          <div style={{ marginTop: 8 }}>
                            <img
                              src={resolvePhotoSrc(seatPhotoDraft.global_photo_url)}
                              style={{ width: '100%', maxHeight: 160, objectFit: 'contain', border: '1px solid #f0f0f0', borderRadius: 6 }}
                            />
                            <Space size={8}>
                              <Button type="link" onClick={() => window.open(resolvePhotoSrc(seatPhotoDraft.global_photo_url), '_blank')}>
                                预览
                              </Button>
                              <Button
                                type="link"
                                danger
                                onClick={() => setSeatPhotoDraft((prev) => ({ ...prev, global_photo_url: '' }))}
                              >
                                清除
                              </Button>
                            </Space>
                          </div>
                        )}
                      </Form.Item>
                    </Col>
                  </Row>
                </Form>
              </Modal>
            </Space>
          ) : activeKey === 'batch' ? (
            <Space direction="vertical" size={12} style={{ width: '100%' }}>
              <Modal
                title="新增自定义缺陷描述"
                open={customModalOpen}
                onOk={saveCustomCheckItem}
                onCancel={() => setCustomModalOpen(false)}
                okText="保存"
                cancelText="取消"
                destroyOnClose
              >
                <Form layout="vertical">
                  <Form.Item label="序号（可选）">
                    <Input placeholder="例如：1" value={customDraftSeq} onChange={(e) => setCustomDraftSeq(e.target.value)} />
                  </Form.Item>
                  <Form.Item label="自定义缺陷描述" required>
                    <Input.TextArea
                      placeholder="请输入自定义缺陷描述"
                      value={customDraftDesc}
                      autoSize={{ minRows: 3, maxRows: 8 }}
                      onChange={(e) => setCustomDraftDesc(e.target.value)}
                    />
                  </Form.Item>
                </Form>
              </Modal>
              <Modal
                title="缺陷明细"
                open={detailModalOpen}
                onOk={saveDetailModal}
                onCancel={() => {
                  const k = detailModalKey
                  const prev = detailModalPrevAnswer
                  const hasExisting = k
                    ? Boolean((detailModalScope === 'single' ? defectDetails[k]?.length : batchDefectDetails[k]?.length))
                    : false
                  closeDetailModal({ revertAnswer: !hasExisting && prev !== 'yes' })
                }}
                okText="保存"
                cancelText="取消"
                destroyOnClose
              >
                <Form layout="vertical">
                  {detailDrafts.map((d, idx) => {
                    const autoQty = splitDefectPositions(d.defect_positions).length
                    const qty = Number(d.defect_quantity) > 0 ? Number(d.defect_quantity) : autoQty
                    return (
                      <div key={idx} style={{ border: '1px solid #f0f0f0', borderRadius: 8, padding: 12, marginBottom: 12 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                          <div style={{ fontWeight: 600 }}>明细 {idx + 1}</div>
                          <Button
                            size="small"
                            danger
                            disabled={detailDrafts.length <= 1}
                            onClick={() => setDetailDrafts((prev) => prev.filter((_, i) => i !== idx))}
                          >
                            删除
                          </Button>
                        </div>
                        <Form.Item label="缺陷状态" style={{ marginBottom: 12 }}>
                          <Row gutter={8}>
                            <Col span={10}>
                              <Select
                                placeholder="选择预设"
                                value={defectStatusOptions.includes(d.defect_status) ? d.defect_status : undefined}
                                allowClear
                                showSearch
                                optionFilterProp="label"
                                listHeight={160}
                                options={defectStatusOptions.map((v) => ({ label: v, value: v }))}
                                onChange={(v) => {
                                  setDetailDrafts((prev) => prev.map((p, i) => (i === idx ? { ...p, defect_status: String(v || '') } : p)))
                                }}
                              />
                            </Col>
                            <Col span={14}>
                              <Input
                                placeholder="或输入自定义缺陷状态"
                                value={defectStatusOptions.includes(d.defect_status) ? '' : d.defect_status}
                                onChange={(e) => {
                                  const v = e.target.value
                                  setDetailDrafts((prev) => prev.map((p, i) => (i === idx ? { ...p, defect_status: v } : p)))
                                }}
                              />
                            </Col>
                          </Row>
                        </Form.Item>
                        <Form.Item label="具体位置" style={{ marginBottom: 12 }}>
                          <Input.TextArea
                            placeholder="用 ; 或 | 或 换行分隔，例如：LH1;LH2;LH3"
                            value={d.defect_positions}
                            autoSize={{ minRows: 3, maxRows: 8 }}
                            onChange={(e) => {
                              const v = e.target.value
                              setDetailDrafts((prev) => prev.map((p, i) => {
                                if (i !== idx) return p
                                const prevAutoQty = splitDefectPositions(String(p.defect_positions || '')).length
                                const nextAutoQty = splitDefectPositions(v).length
                                const currentQty = Number(p.defect_quantity ?? 0)
                                if (!(currentQty > 0) || currentQty === prevAutoQty) {
                                  return { ...p, defect_positions: v, defect_quantity: nextAutoQty > 0 ? nextAutoQty : undefined }
                                }
                                return { ...p, defect_positions: v }
                              }))
                            }}
                          />
                        </Form.Item>
                        <Row gutter={12}>
                          <Col xs={24} sm={12}>
                            <Form.Item label="局部照片" style={{ marginBottom: 12 }}>
                              <Space>
                                <Button
                                  icon={<UploadOutlined />}
                                  onClick={async () => {
                                    try {
                                      const url = await pickAndUploadDefectPhoto({ kind: 'local', capture: 'environment' })
                                      setDetailDrafts((prev) => prev.map((p, i) => (i === idx ? { ...p, local_photo_url: url } : p)))
                                      message.success('局部照片已上传')
                                    } catch (e: any) {
                                      const msg = String(e?.message || '').trim()
                                      if (msg && msg !== '未选择图片') message.error(msg)
                                    }
                                  }}
                                >
                                  拍照
                                </Button>
                                <Button
                                  onClick={async () => {
                                    try {
                                      const url = await pickAndUploadDefectPhoto({ kind: 'local' })
                                      setDetailDrafts((prev) => prev.map((p, i) => (i === idx ? { ...p, local_photo_url: url } : p)))
                                      message.success('局部照片已上传')
                                    } catch (e: any) {
                                      const msg = String(e?.message || '').trim()
                                      if (msg && msg !== '未选择图片') message.error(msg)
                                    }
                                  }}
                                >
                                  相册
                                </Button>
                              </Space>
                              {d.local_photo_url && (
                                <div style={{ marginTop: 8 }}>
                                  <img
                                    src={resolvePhotoSrc(d.local_photo_url)}
                                    style={{ width: '100%', maxHeight: 160, objectFit: 'contain', border: '1px solid #f0f0f0', borderRadius: 6 }}
                                  />
                                  <Space size={8}>
                                    <Button type="link" onClick={() => window.open(resolvePhotoSrc(d.local_photo_url), '_blank')}>
                                      预览
                                    </Button>
                                    <Button
                                      type="link"
                                      danger
                                      onClick={() => setDetailDrafts((prev) => prev.map((p, i) => (i === idx ? { ...p, local_photo_url: '' } : p)))}
                                    >
                                      清除
                                    </Button>
                                  </Space>
                                </div>
                              )}
                            </Form.Item>
                          </Col>
                          <Col xs={24} sm={12}>
                            <Form.Item label="全局照片" style={{ marginBottom: 12 }}>
                              <Space>
                                <Button
                                  icon={<UploadOutlined />}
                                  onClick={async () => {
                                    try {
                                      const url = await pickAndUploadDefectPhoto({ kind: 'global', capture: 'environment' })
                                      setDetailDrafts((prev) => prev.map((p, i) => (i === idx ? { ...p, global_photo_url: url } : p)))
                                      message.success('全局照片已上传')
                                    } catch (e: any) {
                                      const msg = String(e?.message || '').trim()
                                      if (msg && msg !== '未选择图片') message.error(msg)
                                    }
                                  }}
                                >
                                  拍照
                                </Button>
                                <Button
                                  onClick={async () => {
                                    try {
                                      const url = await pickAndUploadDefectPhoto({ kind: 'global' })
                                      setDetailDrafts((prev) => prev.map((p, i) => (i === idx ? { ...p, global_photo_url: url } : p)))
                                      message.success('全局照片已上传')
                                    } catch (e: any) {
                                      const msg = String(e?.message || '').trim()
                                      if (msg && msg !== '未选择图片') message.error(msg)
                                    }
                                  }}
                                >
                                  相册
                                </Button>
                              </Space>
                              {d.global_photo_url && (
                                <div style={{ marginTop: 8 }}>
                                  <img
                                    src={resolvePhotoSrc(d.global_photo_url)}
                                    style={{ width: '100%', maxHeight: 160, objectFit: 'contain', border: '1px solid #f0f0f0', borderRadius: 6 }}
                                  />
                                  <Space size={8}>
                                    <Button type="link" onClick={() => window.open(resolvePhotoSrc(d.global_photo_url), '_blank')}>
                                      预览
                                    </Button>
                                    <Button
                                      type="link"
                                      danger
                                      onClick={() => setDetailDrafts((prev) => prev.map((p, i) => (i === idx ? { ...p, global_photo_url: '' } : p)))}
                                    >
                                      清除
                                    </Button>
                                  </Space>
                                </div>
                              )}
                            </Form.Item>
                          </Col>
                        </Row>
                        <Form.Item label="数量" style={{ marginBottom: 0 }}>
                          <InputNumber value={qty || undefined} min={0} precision={0} style={{ width: '100%' }} onChange={(v) => setDetailDrafts((prev) => prev.map((p, i) => (i === idx ? { ...p, defect_quantity: Number(v) > 0 ? Number(v) : undefined } : p)))} />
                        </Form.Item>
                      </div>
                    )
                  })}
                  <Button
                    onClick={() =>
                      setDetailDrafts((prev) => [
                        ...(prev.length ? prev : [{ defect_status: '破损', defect_positions: '', defect_quantity: undefined, local_photo_url: '', global_photo_url: '' }]),
                        { defect_status: '破损', defect_positions: '', defect_quantity: undefined, local_photo_url: '', global_photo_url: '' },
                      ])
                    }
                    style={{ width: '100%' }}
                  >
                    新增一条明细
                  </Button>
                </Form>
              </Modal>
              <Card
                title="飞机与部件信息"
                extra={
                  <Button
                    type="link"
                    onClick={() => {
                      setBatchMetaCollapsed((v) => !v)
                    }}
                  >
                    {batchMetaCollapsed ? '展开' : '收起'}
                  </Button>
                }
              >
                {!batchMetaCollapsed && (
                  <Form layout="vertical">
                    <Row gutter={12}>
                      <Col xs={12} sm={12}>
                        <Form.Item label="机型（type）" required>
                          <Select
                            placeholder="请选择机型"
                            value={selectedType}
                            allowClear
                            showSearch
                            optionFilterProp="label"
                            onChange={async (v) => {
                              const nextType = v || undefined
                              setSelectedType(nextType)
                              setSelectedCust(undefined)
                              setSelectedCompName(undefined)
                              setCustOptions([])
                              setCompNameOptions([])
                              setCheckItems([])
                              setBatchAnswers({})
                              setBatchDefectDetails({})
                              if (!nextType) return
                              try {
                                const opts = await fetchOptions({ type: nextType })
                                setCustOptions(opts.custs)
                              } catch (e: any) {
                                message.error(e?.message || '加载客户选项失败')
                                setCustOptions([])
                              }
                            }}
                            options={typeOptions.map((t) => ({ value: t, label: t }))}
                          />
                        </Form.Item>
                      </Col>
                      <Col xs={12} sm={12}>
                        <Form.Item label="客户（cust）" required>
                          <Select
                            placeholder="请选择客户"
                            value={selectedCust}
                            allowClear
                            showSearch
                            optionFilterProp="label"
                            disabled={!selectedType}
                            onChange={async (v) => {
                              const nextCust = v || undefined
                              setSelectedCust(nextCust)
                              setSelectedCompName(undefined)
                              setCompNameOptions([])
                              setCheckItems([])
                              setBatchAnswers({})
                              setBatchDefectDetails({})
                              if (!selectedType || !nextCust) return
                              try {
                                const opts = await fetchOptions({ type: selectedType, cust: nextCust })
                                setCompNameOptions(opts.comp_names)
                              } catch (e: any) {
                                message.error(e?.message || '加载部件名称选项失败')
                                setCompNameOptions([])
                              }
                            }}
                            options={custOptions.map((c) => ({ value: c, label: c }))}
                          />
                        </Form.Item>
                      </Col>
                      <Col xs={12} sm={12}>
                        <Form.Item label="部件名称（comp_name）" required>
                          <Select
                            placeholder="请选择部件名称"
                            value={selectedCompName}
                            allowClear
                            showSearch
                            optionFilterProp="label"
                            disabled={!selectedType || !selectedCust}
                            onChange={(v) => {
                              const nextName = v || undefined
                              setSelectedCompName(nextName)
                              setCheckItems([])
                              setBatchAnswers({})
                              setBatchDefectDetails({})
                            }}
                            options={activeCompNameOptions.map((n) => ({ value: n, label: n }))}
                          />
                        </Form.Item>
                      </Col>
                      <Col xs={12} sm={12}>
                        <Form.Item label="部件件号（comp_pn）" required>
                          <Input placeholder="请输入部件件号" value={metaCompPn} onChange={(e) => setMetaCompPn(e.target.value)} />
                        </Form.Item>
                      </Col>
                      <Col xs={12} sm={12}>
                        <Form.Item label="飞机号（aircraft_no）" required>
                          <Input placeholder="请输入飞机号" value={metaAircraftNo} onChange={(e) => setMetaAircraftNo(e.target.value)} />
                        </Form.Item>
                      </Col>
                      <Col xs={12} sm={12}>
                        <Form.Item label="销售指令号（sale_wo）" required>
                          <Input placeholder="请输入销售指令号" value={metaSaleWo} onChange={(e) => setMetaSaleWo(e.target.value)} />
                        </Form.Item>
                      </Col>
                      <Col xs={12} sm={12}>
                        <Form.Item label="定检年月（plan_year_month）" required>
                          <Input placeholder="例如：2026-03" value={metaPlanYearMonth} onChange={(e) => setMetaPlanYearMonth(e.target.value)} />
                        </Form.Item>
                      </Col>
                    </Row>
                  </Form>
                )}
              </Card>

              <Card title="检查详情信息" bodyStyle={{ padding: 0 }}>
                <div style={{ position: 'sticky', top: 0, zIndex: 10, background: '#fff', borderBottom: '1px solid #f0f0f0' }}>
                  <div style={{ padding: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
                    <div style={{ color: '#666', whiteSpace: 'nowrap' }}>
                      {checkItems.length > 0 ? `共 ${checkItems.length} 条，已判断 ${Object.keys(batchAnswers).length} 条，未判断 ${checkItems.length - Object.keys(batchAnswers).length} 条` : '请选择后加载检查项'}
                    </div>
                    <Space wrap>
                      <Select
                        style={{ width: 150 }}
                        value={batchFilter}
                        onChange={(v) => setBatchFilter(v as 'all' | 'pending' | 'checked')}
                        options={[
                          { label: '全部', value: 'all' },
                          { label: '仅未判断', value: 'pending' },
                          { label: '仅已判断', value: 'checked' },
                        ]}
                      />
                      <Button type="link" onClick={() => setBatchMetaCollapsed((v) => !v)}>
                        {batchMetaCollapsed ? '展开信息' : '收起信息'}
                      </Button>
                      <Button onClick={loadBatchCheckItems} loading={batchCheckLoading} type="primary">
                        加载检查项
                      </Button>
                      <Button onClick={addCustomCheckItem} disabled={!selectedType || !selectedCust || !selectedCompName}>
                        新增自定义描述
                      </Button>
                      <Button onClick={submitBatchCheck} loading={batchSubmitting} disabled={checkItems.length === 0} type="primary">
                        提交
                      </Button>
                    </Space>
                  </div>
                </div>

                <List
                  loading={batchCheckLoading}
                  dataSource={filteredBatchCheckItems}
                  renderItem={(item) => {
                    const k = String(item.id)
                    const displayPn = metaCompPn.trim() || item.comp_pn
                    const value = batchAnswers[k]
                    const seqPrefix = item.seq ? `${item.seq}、` : ''
                    const detailList = batchDefectDetails[k] || []
                    const detailStatuses = Array.from(new Set(detailList.map((d) => String(d.defect_status || '').trim()).filter(Boolean)))
                    const detailLocs = Array.from(new Set(detailList.flatMap((d) => splitDefectPositions(String(d.defect_positions || '')))))
                    const batchPreview = `${String(item?.standardized_desc || '').trim()}${detailStatuses.length ? ` ${detailStatuses.join(' ')}` : ''}，loc：${detailLocs.length ? detailLocs.join(' ') : '未选择'}`
                    return (
                      <List.Item style={{ padding: isMobile ? 0 : 12, marginBottom: isMobile ? 12 : 0 }}>
                        <div style={{ width: '100%', ...(isMobile ? { border: '1px solid #f0f0f0', borderRadius: 10, padding: 12, background: '#fff' } : {}) }}>
                          <div style={{ fontWeight: 600 }}>
                            {displayPn ? `（${displayPn}）` : ''}
                          </div>
                          <div style={{ marginTop: 8, whiteSpace: 'pre-wrap' }}>
                            {item?.__custom ? (
                              <div style={{ display: 'flex', gap: 8 }}>
                                {seqPrefix ? <div style={{ whiteSpace: 'nowrap' }}>{seqPrefix}</div> : null}
                                <Input.TextArea
                                  placeholder="请输入自定义缺陷描述"
                                  value={String(item.standardized_desc || '')}
                                  autoSize={{ minRows: 2, maxRows: 6 }}
                                  style={{ flex: 1 }}
                                  onChange={(e) => {
                                    const v = e.target.value
                                    setCheckItems((prev) => prev.map((p) => (String(p.id) === k ? { ...p, standardized_desc: v } : p)))
                                  }}
                                />
                              </div>
                            ) : (
                              `${seqPrefix}${String(item.standardized_desc || '')}`
                            )}
                          </div>
                          <div style={{ marginTop: 10, display: 'flex', justifyContent: isMobile ? 'stretch' : 'flex-end' }}>
                            <Radio.Group
                              value={value}
                              onChange={(e) => {
                                const v = e.target.value as 'yes' | 'no'
                                if (v === 'no') {
                                  setBatchAnswers((prev) => ({ ...prev, [k]: 'no' as const }))
                                  setBatchDefectDetails((prev) => {
                                    if (!prev[k]) return prev
                                    const next = { ...prev }
                                    delete next[k]
                                    return next
                                  })
                                  return
                                }
                                const prevAnswer = value
                                setBatchAnswers((prev) => ({ ...prev, [k]: 'yes' as const }))
                                openDetailModal('batch', k, prevAnswer)
                              }}
                              optionType="button"
                              buttonStyle="solid"
                              style={{ width: isMobile ? '100%' : undefined, display: 'flex' }}
                            >
                              <Radio.Button value="yes" style={{ flex: isMobile ? 1 : undefined, textAlign: 'center' }}>是</Radio.Button>
                              <Radio.Button value="no" style={{ flex: isMobile ? 1 : undefined, textAlign: 'center' }}>否</Radio.Button>
                            </Radio.Group>
                          </div>

                          {value === 'yes' && (
                            <div style={{ marginTop: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
                              <div style={{ color: '#666' }}>
                                缺陷描述预览：{batchPreview}
                              </div>
                              <Button size="small" onClick={() => openDetailModal('batch', k, 'yes')}>
                                {batchDefectDetails[k]?.length ? '修改明细' : '填写明细'}
                              </Button>
                            </div>
                          )}

                          {item?.__custom && (
                            <div style={{ marginTop: 8, display: 'flex', justifyContent: 'flex-end' }}>
                              <Button
                                size="small"
                                danger
                                onClick={() => {
                                  setCheckItems((prev) => prev.filter((p) => String(p.id) !== k))
                                  setBatchAnswers((prev) => {
                                    const next = { ...prev }
                                    delete next[k]
                                    return next
                                  })
                                  setBatchDefectDetails((prev) => {
                                    if (!prev[k]) return prev
                                    const next = { ...prev }
                                    delete next[k]
                                    return next
                                  })
                                }}
                              >
                                移除
                              </Button>
                            </div>
                          )}
                        </div>
                      </List.Item>
                    )
                  }}
                />
              </Card>
            </Space>
          ) : activeKey === 'export' ? (
            <Card title="缺陷清单Excel导出">
              <Modal
                title="照片预览"
                open={exportPhotoModalOpen}
                onCancel={() => {
                  setExportPhotoModalOpen(false)
                  setExportPhotoModalRow(null)
                }}
                footer={null}
                width={900}
                destroyOnClose
              >
                <Row gutter={12}>
                  <Col xs={24} sm={12}>
                    <div style={{ fontWeight: 600, marginBottom: 8 }}>局部照片</div>
                    {String(exportPhotoModalRow?.local_photo_url || '').trim() ? (
                      <>
                        <img
                          src={resolvePhotoSrc(String(exportPhotoModalRow?.local_photo_url || ''))}
                          style={{ width: '100%', maxHeight: 420, objectFit: 'contain', border: '1px solid #f0f0f0', borderRadius: 6 }}
                        />
                        <Button
                          type="link"
                          onClick={() => window.open(resolvePhotoSrc(String(exportPhotoModalRow?.local_photo_url || '')), '_blank')}
                          style={{ paddingLeft: 0 }}
                        >
                          新窗口打开
                        </Button>
                      </>
                    ) : (
                      <div style={{ color: '#999' }}>无</div>
                    )}
                  </Col>
                  <Col xs={24} sm={12}>
                    <div style={{ fontWeight: 600, marginBottom: 8 }}>全局照片</div>
                    {String(exportPhotoModalRow?.global_photo_url || '').trim() ? (
                      <>
                        <img
                          src={resolvePhotoSrc(String(exportPhotoModalRow?.global_photo_url || ''))}
                          style={{ width: '100%', maxHeight: 420, objectFit: 'contain', border: '1px solid #f0f0f0', borderRadius: 6 }}
                        />
                        <Button
                          type="link"
                          onClick={() => window.open(resolvePhotoSrc(String(exportPhotoModalRow?.global_photo_url || '')), '_blank')}
                          style={{ paddingLeft: 0 }}
                        >
                          新窗口打开
                        </Button>
                      </>
                    ) : (
                      <div style={{ color: '#999' }}>无</div>
                    )}
                  </Col>
                </Row>
              </Modal>
              <Form layout="vertical">
                <Row gutter={12}>
                  <Col xs={24} sm={12}>
                    <Form.Item label="飞机号（aircraft_no）">
                      <Input placeholder="模糊筛选" value={exportAircraftNo} onChange={(e) => setExportAircraftNo(e.target.value)} allowClear />
                    </Form.Item>
                  </Col>
                  <Col xs={24} sm={12}>
                    <Form.Item label="销售指令号（sale_wo）">
                      <Input placeholder="模糊筛选" value={exportSaleWo} onChange={(e) => setExportSaleWo(e.target.value)} allowClear />
                    </Form.Item>
                  </Col>
                  <Col xs={24} sm={12}>
                    <Form.Item label="部件名称（comp_name）">
                      <Input placeholder="模糊筛选" value={exportCompName} onChange={(e) => setExportCompName(e.target.value)} allowClear />
                    </Form.Item>
                  </Col>
                  <Col xs={24} sm={12}>
                    <Form.Item label="部件件号（comp_pn）">
                      <Input placeholder="模糊筛选" value={exportCompPn} onChange={(e) => setExportCompPn(e.target.value)} allowClear />
                    </Form.Item>
                  </Col>
                  <Col xs={24} sm={12}>
                    <Form.Item label="检查人（inspector）">
                      <Input placeholder="模糊筛选" value={exportInspector} onChange={(e) => setExportInspector(e.target.value)} allowClear />
                    </Form.Item>
                  </Col>
                </Row>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
                  <div style={{ color: '#666' }}>
                    预览结果：{exportPreviewRows.length} 条
                  </div>
                  <Space>
                    <Button onClick={runExportPreview} loading={exportPreviewLoading} type="primary">
                      查询预览
                    </Button>
                    <Button onClick={doExportExcel} loading={exporting} disabled={exportPreviewRows.length === 0} type="primary">
                      导出Excel
                    </Button>
                  </Space>
                </div>

                <div style={{ marginTop: 12 }}>
                  <Table
                    rowKey={(r: any, idx) => `${idx}-${String(r?.standardized_desc || '')}`}
                    loading={exportPreviewLoading}
                    columns={exportPreviewColumns as any}
                    dataSource={exportPreviewRows}
                    pagination={{ pageSize: 50, showSizeChanger: true }}
                    scroll={{ x: 'max-content' }}
                    size="small"
                  />
                </div>
              </Form>
            </Card>
          ) : (
            <Card>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <Title level={5} style={{ margin: 0 }}>
                  数据预览
                </Title>
                <div style={{ display: 'flex', gap: 8 }}>
                  {activeKey === 'catalog' && (
                    <>
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept=".csv,.xlsx,.xls"
                        style={{ display: 'none' }}
                        onChange={(e) => {
                          const f = e.target.files?.[0]
                          if (f) onUploadFile(f)
                        }}
                      />
                      <Button onClick={downloadCatalog}>
                        下载
                      </Button>
                      <Button onClick={onChooseFile} loading={uploading}>
                        上传
                      </Button>
                    </>
                  )}
                  <Button onClick={loadData} loading={loading}>
                    刷新
                  </Button>
                </div>
              </div>
              <Table
                rowKey="id"
                loading={loading}
                columns={columns as any}
                dataSource={rows}
                pagination={{ pageSize: 50, showSizeChanger: true }}
                scroll={{ x: 'max-content' }}
                size="small"
              />
            </Card>
          )}
        </Content>
      </Layout>
    </Layout>
  )
}

export default DefectCheck
