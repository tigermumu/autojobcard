import React, { useState, useEffect } from 'react'
import {
  Card,
  Button,
  Space,
  Upload,
  message,
  Typography,
  Table,
  Select,
  Row,
  Col,
  Alert,
  Tag,
  Progress,
  Modal,
  Form,
  Input
} from 'antd'
import {
  UploadOutlined,
  ReloadOutlined,
  ArrowLeftOutlined,
  FileExcelOutlined,
  SaveOutlined
} from '@ant-design/icons'
import type { UploadProps } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useNavigate } from 'react-router-dom'
import { configApi, Configuration } from '../services/configApi'
import { indexDataApi, IndexData } from '../services/indexDataApi'
import { workcardApi } from '../services/workcardApi'
import * as XLSX from 'xlsx'

const { Title } = Typography
const { Option } = Select

interface ExcelData {
  key: number
  [key: string]: any
}


// 索引字段映射（英文到中文）
const INDEX_FIELD_MAP: Record<string, string> = {
  main_area: '主区域',
  main_component: '主部件',
  first_level_subcomponent: '一级子部件',
  second_level_subcomponent: '二级子部件',
  orientation: '方位',
  defect_subject: '缺陷主体',
  defectSubject: '缺陷主体',
  defect_description: '缺陷描述',
  defectDescription: '缺陷描述',
  location: '位置',
  quantity: '数量'
}

const AddWorkCardData: React.FC = () => {
  const navigate = useNavigate()
  const cleanMatchMode = 'ai'
  const [loading, setLoading] = useState(false)
  const [configLoading, setConfigLoading] = useState(false)
  const [uploadedData, setUploadedData] = useState<ExcelData[]>([])
  const [columns, setColumns] = useState<ColumnsType<ExcelData>>([])
  // AI 模式：选择索引配置（configurations.id）
  const [selectedAiConfigId, setSelectedAiConfigId] = useState<string>('')
  const [configurations, setConfigurations] = useState<Configuration[]>([])

  // 索引数据
  const [indexData, setIndexData] = useState<IndexData[]>([])
  const [indexColumns, setIndexColumns] = useState<ColumnsType<IndexData>>([])
  const [indexDataLoading, setIndexDataLoading] = useState(false)

  // 独立对照字段数据
  const [independentFields, setIndependentFields] = useState<{
    orientation: string[]
    defectSubject: string[]
    defectDescription: string[]
    location: string[]
    quantity: string[]
  }>({
    orientation: [],
    defectSubject: [],
    defectDescription: [],
    location: [],
    quantity: []
  })

  // 清洗后的数据
  const [cleanedData, setCleanedData] = useState<ExcelData[]>([])
  const [cleanedColumns, setCleanedColumns] = useState<ColumnsType<ExcelData>>([])

  // 进度条相关状态
  const [progressVisible, setProgressVisible] = useState(false)
  const [progressPercent, setProgressPercent] = useState(0)
  const [progressStatus, setProgressStatus] = useState<'normal' | 'active' | 'success' | 'exception'>('active')
  const [progressTotal, setProgressTotal] = useState(0) // 总数据量
  const [progressCurrent, setProgressCurrent] = useState(0) // 当前已处理数量

  // 保存到数据库相关状态
  const [saveModalVisible, setSaveModalVisible] = useState(false)
  const [saveLoading, setSaveLoading] = useState(false)
  const [saveFormData, setSaveFormData] = useState({
    aircraft_number: '',
    aircraft_type: '',
    msn: '',
    amm_ipc_eff: ''
  })

  // 加载构型列表
  useEffect(() => {
    loadConfigurations()
  }, [])

  // 当选择构型时，加载索引数据
  useEffect(() => {
    if (selectedAiConfigId) {
      loadIndexData(Number(selectedAiConfigId))
    }
  }, [selectedAiConfigId])

  const loadConfigurations = async () => {
    try {
      setConfigLoading(true)
      const data = await configApi.getAll()
      setConfigurations(data as Configuration[])
    } catch (error: any) {
      console.error('加载构型列表失败:', error)
      message.error('加载构型列表失败: ' + error.message)
    } finally {
      setConfigLoading(false)
    }
  }

  // 加载索引数据
  const loadIndexData = async (configurationId: number) => {
    try {
      setIndexDataLoading(true)
      const data = await indexDataApi.getAll({ configuration_id: configurationId })
      setIndexData(data)

      // 生成索引表格列 - 只显示层级字段
      if (data.length > 0) {
        const keys = Object.keys(data[0])
        const generatedColumns: ColumnsType<IndexData> = keys
          .filter(key => !['id', 'configuration_id', 'created_at', 'updated_at',
            'orientation', 'defect_subject', 'defect_description', 'location', 'quantity'].includes(key))
          .map(key => ({
            title: INDEX_FIELD_MAP[key] || key.replace(/_/g, ' '),
            dataIndex: key,
            key: key,
            width: 130,
            ellipsis: true
          }))
        setIndexColumns(generatedColumns)
      }

      // 从构型配置中加载独立对照字段
      const config = await configApi.getById(configurationId)
      let independent: any = {
        orientation: [],
        defectSubject: [],
        defectDescription: [],
        location: [],
        quantity: []
      }

      // 从field_mapping加载独立对照字段
      if (config.field_mapping && typeof config.field_mapping === 'object') {
        independent = {
          orientation: config.field_mapping.orientation || [],
          defectSubject: config.field_mapping.defectSubject || [],
          defectDescription: config.field_mapping.defectDescription || [],
          location: config.field_mapping.location || [],
          quantity: config.field_mapping.quantity || []
        }
      }

      setIndependentFields(independent)

    } catch (error: any) {
      console.error('加载索引数据失败:', error)
      message.error('加载索引数据失败: ' + error.message)
    } finally {
      setIndexDataLoading(false)
    }
  }

  // 打开保存到数据库模态框
  const handleOpenSaveModal = () => {
    if (cleanedData.length === 0) {
      message.warning('没有可保存的清洗后数据')
      return
    }
    if (!selectedAiConfigId) {
      message.warning('请先选择构型索引配置')
      return
    }

    // 尝试从选中的构型配置中获取默认值
    const selectedConfig = configurations.find(c => String(c.id) === selectedAiConfigId)
    if (selectedConfig) {
      setSaveFormData({
        aircraft_number: '',
        aircraft_type: selectedConfig.aircraft_type || '',
        msn: selectedConfig.msn || '',
        amm_ipc_eff: selectedConfig.amm_ipc_eff || ''
      })
    }

    setSaveModalVisible(true)
  }

  // 保存清洗后的数据到数据库
  const handleSaveToDatabase = async () => {
    if (cleanedData.length === 0) {
      message.warning('没有可保存的数据')
      return
    }

    if (!selectedAiConfigId) {
      message.warning('请先选择构型索引配置')
      return
    }

    try {
      setSaveLoading(true)

      // 移除key字段，因为key是前端添加的，不需要传给后端
      const dataToSave = cleanedData.map(item => {
        const { key: _key, ...rest } = item
        return rest
      })

      const response = await workcardApi.saveCleanedData({
        cleaned_data: dataToSave,
        configuration_id: Number(selectedAiConfigId),
        aircraft_number: saveFormData.aircraft_number || undefined,
        aircraft_type: saveFormData.aircraft_type || undefined,
        msn: saveFormData.msn || undefined,
        amm_ipc_eff: saveFormData.amm_ipc_eff || undefined
      })

      if (response.success) {
        message.success(response.message)
        setSaveModalVisible(false)
        // 清空表单
        setSaveFormData({
          aircraft_number: '',
          aircraft_type: '',
          msn: '',
          amm_ipc_eff: ''
        })
      } else {
        // 显示详细错误信息
        const errorMsg = response.message || '保存失败'
        const errorDetails = response.errors && response.errors.length > 0
          ? `\n错误详情:\n${response.errors.slice(0, 5).join('\n')}`
          : ''
        message.error(`${errorMsg}${errorDetails}`, 10)
        console.error('保存失败详情:', response)
      }

    } catch (error: any) {
      console.error('保存失败:', error)
      // 显示更详细的错误信息
      let errorMsg = '保存失败: '
      if (error.response?.data?.detail) {
        errorMsg += error.response.data.detail
      } else if (error.message) {
        errorMsg += error.message
      } else {
        errorMsg += '未知错误'
      }
      message.error(errorMsg, 10) // 显示10秒
    } finally {
      setSaveLoading(false)
    }
  }

  // 导出清洗后的数据到Excel
  const handleExportExcel = () => {
    if (cleanedData.length === 0) {
      message.warning('没有可导出的数据')
      return
    }

    try {
      // 准备Excel数据，按照列的顺序和标题
      const excelData: any[] = []

      // 添加表头（使用列的中文标题）
      const headers: string[] = []
      cleanedColumns.forEach((col: any) => {
        if (col.title && typeof col.title === 'string') {
          headers.push(col.title)
        } else {
          headers.push(String(col.dataIndex || ''))
        }
      })

      // 添加数据行
      cleanedData.forEach((item: any) => {
        const row: any = {}
        cleanedColumns.forEach((col: any) => {
          const dataIndex = col.dataIndex as string
          if (dataIndex) {
            // 获取列标题（用于表头）
            let header = ''
            if (col.title && typeof col.title === 'string') {
              header = col.title
            } else {
              header = dataIndex
            }
            row[header] = item[dataIndex] || ''
          }
        })
        excelData.push(row)
      })

      // 创建工作簿
      const ws = XLSX.utils.json_to_sheet(excelData)
      const wb = XLSX.utils.book_new()
      XLSX.utils.book_append_sheet(wb, ws, '清洗后数据')

      // 生成文件名（包含时间戳）
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5)
      const fileName = `清洗后数据_${timestamp}.xlsx`

      // 下载文件
      XLSX.writeFile(wb, fileName)

      message.success(`成功导出 ${cleanedData.length} 条数据到 ${fileName}`)
    } catch (error: any) {
      console.error('导出Excel失败:', error)
      message.error('导出Excel失败: ' + error.message)
    }
  }

  // 处理Excel文件上传
  const handleUpload: UploadProps['customRequest'] = async (options) => {
    const { file, onSuccess, onError } = options

    try {
      setLoading(true)

      // 读取Excel文件
      const fileReader = new FileReader()

      fileReader.onload = (e) => {
        try {
          const data = e.target?.result
          const workbook = XLSX.read(data, { type: 'binary' })

          // 获取第一个工作表
          const firstSheet = workbook.SheetNames[0]
          const worksheet = workbook.Sheets[firstSheet]

          // 转换为JSON数据
          const jsonData = XLSX.utils.sheet_to_json(worksheet)

          if (jsonData.length === 0) {
            throw new Error('Excel文件中没有数据')
          }

          // 处理数据，添加key字段
          const processedData: ExcelData[] = jsonData.map((row: any, index: number) => ({
            ...row,
            key: index + 1
          }))

          // 动态生成表格列
          if (processedData.length > 0) {
            const keys = Object.keys(processedData[0])
            const generatedColumns: ColumnsType<ExcelData> = keys
              .filter(key => key !== 'key')
              .map(key => ({
                title: key,
                dataIndex: key,
                key: key,
                width: 120,
                ellipsis: true
              }))
            setColumns(generatedColumns)
          }

          setUploadedData(processedData)
          message.success(`Excel文件上传成功！共加载 ${processedData.length} 条数据`)
          onSuccess?.('success', {} as any)

        } catch (error: any) {
          console.error('解析Excel失败:', error)
          message.error('解析Excel文件失败: ' + error.message)
          onError?.(error)
        } finally {
          setLoading(false)
        }
      }

      fileReader.onerror = (error) => {
        console.error('读取文件失败:', error)
        message.error('读取文件失败')
        onError?.(error as any)
        setLoading(false)
      }

      // 读取文件为二进制数据
      fileReader.readAsBinaryString(file as File)

    } catch (error: any) {
      console.error('上传失败:', error)
      message.error('上传失败: ' + error.message)
      onError?.(error)
      setLoading(false)
    }
  }

  // 测试清洗（随机20条）
  const handleDataCleanTest = async () => {
    if (uploadedData.length === 0) {
      message.warning('请先上传Excel文件')
      return
    }

    if (!selectedAiConfigId) {
      message.warning('请先选择构型索引配置')
      return
    }

    try {
      setLoading(true)
      setProgressVisible(true)
      setProgressPercent(0)
      setProgressStatus('active')
      setProgressCurrent(0)

      // 随机选择20条数据进行清洗测试
      const testCount = Math.min(20, uploadedData.length)
      const shuffled = [...uploadedData].sort(() => 0.5 - Math.random())
      const testData = shuffled.slice(0, testCount)

      // 设置总数据量用于显示
      setProgressTotal(testCount)

      // 分批处理数据以实现进度显示（每次处理5条）
      const batchSize = 5
      const allResults: any[] = []

      for (let i = 0; i < testData.length; i += batchSize) {
        const batch = testData.slice(i, i + batchSize)

        // 调用后端API进行数据清洗（每批）
        const response = await workcardApi.cleanData({
          raw_data: batch,
          configuration_id: Number(selectedAiConfigId)
        })

        if (response.success) {
          allResults.push(...response.data)
        }

        // 更新进度
        const processed = Math.min(i + batchSize, testData.length)
        const percent = Math.round((processed / testData.length) * 100)
        setProgressPercent(percent)
        setProgressCurrent(processed)
      }

      // 完成后更新进度为100%
      setProgressPercent(100)
      setProgressStatus('success')
      setTimeout(() => {
        setProgressVisible(false)
      }, 1000)

      // 继续处理结果
      const response = { success: true, data: allResults, cleaned_count: allResults.length }

      if (response.success) {
        // 定义必须保留的核心字段（优先级最高）
        const coreFields = [
          { key: '工卡指令号', title: '工卡指令号', width: 150 },
          { key: '工卡描述（中文）', title: '工卡描述（中文）', width: 200 },
          { key: '工卡描述（英文）', title: '工卡描述（英文）', width: 200 }
        ]

        // 定义9个索引字段的列配置（中英文映射）
        const indexColumnsMap: Record<string, string> = {
          main_area: '主区域',
          main_component: '主部件',
          first_level_subcomponent: '一级子部件',
          second_level_subcomponent: '二级子部件',
          orientation: '方位',
          defect_subject: '缺陷主体',
          defect_description: '缺陷描述',
          location: '位置',
          quantity: '数量'
        }

        // 生成清洗后的表格列（始终显示所有核心字段和9个索引字段）
        const cleanedColumns: ColumnsType<ExcelData> = []

        // 先添加核心字段（工卡指令号、工卡描述（中文）、工卡描述（英文））- 始终显示
        coreFields.forEach(field => {
          cleanedColumns.push({
            title: field.title,
            dataIndex: field.key,
            key: field.key,
            width: field.width,
            ellipsis: true
          })
        })

        // 再添加9个索引字段 - 始终显示
        Object.keys(indexColumnsMap).forEach(key => {
          cleanedColumns.push({
            title: indexColumnsMap[key],
            dataIndex: key,
            key: key,
            width: 130,
            ellipsis: true
          })
        })

        setCleanedData(response.data.map((item: any, idx: number) => ({ ...item, key: idx + 1000 })))
        setCleanedColumns(cleanedColumns)
        message.success(`测试清洗完成！共清洗 ${response.cleaned_count} 条数据`)
      } else {
        message.error('数据清洗失败: ' + ((response as any).error || '未知错误'))
        setProgressStatus('exception')
        setTimeout(() => {
          setProgressVisible(false)
        }, 2000)
      }

    } catch (error: any) {
      message.error('数据清洗失败: ' + error.message)
      setProgressStatus('exception')
      setTimeout(() => {
        setProgressVisible(false)
      }, 2000)
    } finally {
      setLoading(false)
    }
  }

  // 数据清洗
  const handleDataClean = async () => {
    if (uploadedData.length === 0) {
      message.warning('请先上传Excel文件')
      return
    }

    if (!selectedAiConfigId) {
      message.warning('请先选择构型索引配置')
      return
    }

    try {
      setLoading(true)
      setProgressVisible(true)
      setProgressPercent(0)
      setProgressStatus('active')
      setProgressCurrent(0)

      // 设置总数据量用于显示
      setProgressTotal(uploadedData.length)

      // 分批处理数据以实现进度显示（每次处理10条）
      const batchSize = 10
      const allResults: any[] = []

      for (let i = 0; i < uploadedData.length; i += batchSize) {
        const batch = uploadedData.slice(i, i + batchSize)

        // 调用后端API进行数据清洗（每批）
        const response = await workcardApi.cleanData({
          raw_data: batch,
          configuration_id: Number(selectedAiConfigId)
        })

        if (response.success) {
          allResults.push(...response.data)
        }

        // 更新进度
        const processed = Math.min(i + batchSize, uploadedData.length)
        const percent = Math.round((processed / uploadedData.length) * 100)
        setProgressPercent(percent)
        setProgressCurrent(processed)
      }

      // 完成后更新进度为100%
      setProgressPercent(100)
      setProgressStatus('success')
      setTimeout(() => {
        setProgressVisible(false)
      }, 1000)

      // 继续处理结果
      const response = { success: true, data: allResults, cleaned_count: allResults.length }

      if (response.success) {
        // 定义必须保留的核心字段（优先级最高）
        const coreFields = [
          { key: '工卡指令号', title: '工卡指令号', width: 150 },
          { key: '工卡描述（中文）', title: '工卡描述（中文）', width: 200 },
          { key: '工卡描述（英文）', title: '工卡描述（英文）', width: 200 }
        ]

        // 定义9个索引字段的列配置（中英文映射）
        const indexColumnsMap: Record<string, string> = {
          main_area: '主区域',
          main_component: '主部件',
          first_level_subcomponent: '一级子部件',
          second_level_subcomponent: '二级子部件',
          orientation: '方位',
          defect_subject: '缺陷主体',
          defect_description: '缺陷描述',
          location: '位置',
          quantity: '数量'
        }

        // 生成清洗后的表格列（始终显示所有核心字段和9个索引字段）
        const cleanedColumns: ColumnsType<ExcelData> = []

        // 先添加核心字段（工卡指令号、工卡描述（中文）、工卡描述（英文））- 始终显示
        coreFields.forEach(field => {
          cleanedColumns.push({
            title: field.title,
            dataIndex: field.key,
            key: field.key,
            width: field.width,
            ellipsis: true
          })
        })

        // 再添加9个索引字段 - 始终显示
        Object.keys(indexColumnsMap).forEach(key => {
          cleanedColumns.push({
            title: indexColumnsMap[key],
            dataIndex: key,
            key: key,
            width: 130,
            ellipsis: true
          })
        })

        setCleanedData(response.data.map((item: any, idx: number) => ({ ...item, key: idx + 1000 })))
        setCleanedColumns(cleanedColumns)
        message.success(`数据清洗完成！共清洗 ${response.cleaned_count} 条数据`)
      } else {
        message.error('数据清洗失败: ' + ((response as any).error || '未知错误'))
        setProgressStatus('exception')
        setTimeout(() => {
          setProgressVisible(false)
        }, 2000)
      }

    } catch (error: any) {
      message.error('数据清洗失败: ' + error.message)
      setProgressStatus('exception')
      setTimeout(() => {
        setProgressVisible(false)
      }, 2000)
    } finally {
      setLoading(false)
    }
  }



  const uploadProps: UploadProps = {
    name: 'file',
    accept: '.xlsx,.xls',
    showUploadList: false,
    customRequest: handleUpload,
    beforeUpload: (file) => {
      const isExcel = file.type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
        file.type === 'application/vnd.ms-excel'
      if (!isExcel) {
        message.error('只能上传Excel文件！')
        return false
      }
      return true
    }
  }

  return (
    <div style={{ padding: '24px', background: '#f0f2f5', minHeight: '100vh' }}>
      {/* 页面头部（整页） */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <Title level={2} style={{ margin: 0 }}>
          <ArrowLeftOutlined
            onClick={() => navigate('/workcards')}
            style={{ marginRight: '12px', cursor: 'pointer' }}
          />
          新增标准工卡数据表
        </Title>
      </div>

      {/* 上传和配置区域 */}
      <Card style={{ marginBottom: '24px' }}>
        <Row gutter={[16, 16]} align="middle">
          <Col span={8}>
            <Space>
              <Upload {...uploadProps}>
                <Button
                  type="primary"
                  icon={<UploadOutlined />}
                  loading={loading}
                  size="large"
                >
                  上传Excel原始数据表
                </Button>
              </Upload>
              {uploadedData.length > 0 && (
                <span style={{ color: '#52c41a' }}>
                  <FileExcelOutlined /> 已上传 {uploadedData.length} 条数据
                </span>
              )}
            </Space>
          </Col>
          <Col span={8}>
            <Space>
              <span style={{ marginRight: '8px' }}>清洗索引选择:</span>
              <Select
                value={selectedAiConfigId}
                onChange={setSelectedAiConfigId}
                placeholder="请选择构型索引配置"
                style={{ width: 250 }}
                showSearch
                optionFilterProp="children"
                loading={configLoading}
                allowClear
              >
                {configurations.map(config => (
                  <Option key={config.id} value={String(config.id)}>
                    {config.name}
                  </Option>
                ))}
              </Select>
            </Space>
          </Col>
          <Col span={8}>
            <Space wrap>
              <Button
                icon={<ReloadOutlined />}
                onClick={handleDataCleanTest}
                disabled={!selectedAiConfigId || uploadedData.length === 0}
                loading={loading}
              >
                测试清洗(20条)
              </Button>
              <Button
                type="primary"
                icon={<ReloadOutlined />}
                onClick={handleDataClean}
                disabled={!selectedAiConfigId || uploadedData.length === 0}
                loading={loading}
              >
                完整清洗
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 四个数据展示框 */}
      <Row gutter={[16, 16]} style={{ alignItems: 'flex-start' }}>
        {/* Excel原始数据展示框 */}
        <Col span={8}>
          <Card
            title="Excel原始数据"
            style={{ height: '620px' }}
            extra={<span style={{ color: '#52c41a' }}>共 {uploadedData.length} 条</span>}
          >
            {uploadedData.length > 0 ? (
              <Table
                columns={columns}
                dataSource={uploadedData}
                rowKey="key"
                loading={loading}
                pagination={{
                  showSizeChanger: true,
                  showTotal: (total) => `共 ${total} 条`,
                  pageSize: 8,
                  size: 'small'
                }}
                scroll={{ x: 'max-content', y: 450 }}
                size="small"
              />
            ) : (
              <div style={{
                textAlign: 'center',
                padding: '100px 0',
                color: '#999'
              }}>
                <FileExcelOutlined style={{ fontSize: '48px', marginBottom: '16px' }} />
                <div style={{ fontSize: '14px' }}>
                  请上传Excel文件以查看数据
                </div>
              </div>
            )}
          </Card>
        </Col>

        {/* 构型索引数据展示框 */}
        <Col span={8}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {/* 层级数据表格（AI索引表） */}
            <Card
              title="构型索引数据"
              style={{ height: '404px' }}
              extra={<span style={{ color: '#1890ff' }}>共 {indexData.length} 条</span>}
            >
              {indexData.length > 0 ? (
                <Table
                  columns={indexColumns}
                  dataSource={indexData}
                  rowKey="id"
                  loading={indexDataLoading}
                  pagination={{
                    showSizeChanger: true,
                    showTotal: (total) => `共 ${total} 条`,
                    pageSize: 8,
                    size: 'small'
                  }}
                  scroll={{ x: 'max-content', y: 234 }}
                  size="small"
                />
              ) : (
                <div style={{
                  textAlign: 'center',
                  padding: '60px 0',
                  color: '#999'
                }}>
                  <FileExcelOutlined style={{ fontSize: '48px', marginBottom: '16px' }} />
                  <div style={{ fontSize: '14px' }}>
                    请选择构型索引配置
                  </div>
                </div>
              )}
            </Card>

            {/* 独立对照字段展示（AI链路字段） */}
            <Card
              title="独立对照字段"
              size="small"
              style={{ height: '200px' }}
            >
              {(indexData.length > 0) ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', height: '150px', overflowY: 'auto' }}>
                  {['orientation', 'defectSubject', 'defectDescription', 'location', 'quantity'].map(fieldKey => {
                    const values = independentFields[fieldKey as keyof typeof independentFields]
                    if (values && values.length > 0) {
                      return (
                        <div key={fieldKey}>
                          <div style={{ fontWeight: 'bold', marginBottom: '4px', fontSize: '12px' }}>
                            {INDEX_FIELD_MAP[fieldKey]}:
                          </div>
                          <Space size={[8, 8]} wrap>
                            {values.map((value: string) => (
                              <Tag key={value} color="blue" style={{ marginBottom: '4px' }}>
                                {value}
                              </Tag>
                            ))}
                          </Space>
                        </div>
                      )
                    }
                    return null
                  })}
                </div>
              ) : (
                <div style={{
                  textAlign: 'center',
                  padding: '60px 0',
                  color: '#999',
                  fontSize: '12px'
                }}>
                  请先选择构型索引配置
                </div>
              )}
            </Card>
          </div>
        </Col>

        {/* 清洗后数据展示框 */}
        <Col span={8}>
          <Card
            title="清洗后数据"
            style={{ height: '620px' }}
            extra={
              <Space>
                <span style={{ color: '#722ed1' }}>共 {cleanedData.length} 条</span>
                {cleanedData.length > 0 && (
                  <>
                    <Button
                      size="small"
                      icon={<FileExcelOutlined />}
                      onClick={handleExportExcel}
                    >
                      导出Excel
                    </Button>
                    <Button
                      type="primary"
                      size="small"
                      icon={<SaveOutlined />}
                      onClick={handleOpenSaveModal}
                    >
                      保存到数据库
                    </Button>
                  </>
                )}
              </Space>
            }
          >
            {cleanedData.length > 0 ? (
              <Table
                columns={cleanedColumns}
                dataSource={cleanedData}
                rowKey="key"
                loading={loading}
                pagination={{
                  showSizeChanger: true,
                  showTotal: (total) => `共 ${total} 条`,
                  pageSize: 8,
                  size: 'small'
                }}
                scroll={{ x: 'max-content', y: 450 }}
                size="small"
              />
            ) : (
              <div style={{
                textAlign: 'center',
                padding: '100px 0',
                color: '#999'
              }}>
                <FileExcelOutlined style={{ fontSize: '48px', marginBottom: '16px' }} />
                <div style={{ fontSize: '14px' }}>
                  数据清洗后将在此展示
                </div>
              </div>
            )}
          </Card>
        </Col>
      </Row>

      {/* 进度条模态框 */}
      <Modal
        title="数据清洗中..."
        open={progressVisible}
        closable={false}
        maskClosable={false}
        footer={null}
        centered
        width={600}
      >
        <div style={{ padding: '20px 0' }}>
          <Progress
            percent={progressPercent}
            status={progressStatus}
            strokeColor={{
              '0%': '#108ee9',
              '100%': '#87d068',
            }}
            format={(percent) => `${percent}%`}
          />
          <div style={{ marginTop: '16px', textAlign: 'center', color: '#666' }}>
            {progressStatus === 'active' && (
              <div>
                <div>正在使用{cleanMatchMode === 'ai' ? 'AI' : '本地规则'}清洗数据</div>
                <div style={{ marginTop: '8px', fontSize: '14px' }}>
                  已处理: {progressCurrent} / {progressTotal} 条数据
                </div>
              </div>
            )}
            {progressStatus === 'success' && (
              <div>
                <div>清洗完成！</div>
                <div style={{ marginTop: '8px', fontSize: '14px' }}>
                  成功处理 {progressTotal} 条数据
                </div>
              </div>
            )}
            {progressStatus === 'exception' && (
              <span style={{ color: '#ff4d4f' }}>清洗失败，请重试</span>
            )}
          </div>
        </div>
      </Modal>

      {/* 保存到数据库模态框 */}
      <Modal
        title="保存清洗后的数据到数据库"
        open={saveModalVisible}
        onCancel={() => setSaveModalVisible(false)}
        onOk={handleSaveToDatabase}
        confirmLoading={saveLoading}
        okText="保存"
        cancelText="取消"
        width={600}
      >
        <Alert
          message="单机构型识别字段"
          description="请填写飞机号、机型、MSN、AMM/IPC EFF等识别字段。如果某些字段未填写，系统将从构型配置中自动获取。"
          type="info"
          showIcon
          style={{ marginBottom: '24px' }}
        />
        <Form layout="vertical">
          <Form.Item label="飞机号（如：B-XXXX）">
            <Input
              placeholder="请输入飞机号，例如：B-1234"
              value={saveFormData.aircraft_number}
              onChange={(e) => setSaveFormData({ ...saveFormData, aircraft_number: e.target.value })}
            />
          </Form.Item>
          <Form.Item label="机型">
            <Input
              placeholder="请输入机型，例如：A320"
              value={saveFormData.aircraft_type}
              onChange={(e) => setSaveFormData({ ...saveFormData, aircraft_type: e.target.value })}
            />
          </Form.Item>
          <Form.Item label="MSN">
            <Input
              placeholder="请输入MSN"
              value={saveFormData.msn}
              onChange={(e) => setSaveFormData({ ...saveFormData, msn: e.target.value })}
            />
          </Form.Item>
          <Form.Item label="AMM/IPC EFF">
            <Input
              placeholder="请输入AMM/IPC EFF"
              value={saveFormData.amm_ipc_eff}
              onChange={(e) => setSaveFormData({ ...saveFormData, amm_ipc_eff: e.target.value })}
            />
          </Form.Item>
        </Form>
        <div style={{ marginTop: '16px', padding: '12px', background: '#f5f5f5', borderRadius: '4px' }}>
          <div style={{ fontSize: '14px', color: '#666', marginBottom: '8px' }}>保存信息：</div>
          <div style={{ fontSize: '13px', color: '#999' }}>
            • 将保存 {cleanedData.length} 条清洗后的工卡数据
          </div>
          <div style={{ fontSize: '13px', color: '#999' }}>
            • 数据将按上述识别字段分类存储
          </div>
          <div style={{ fontSize: '13px', color: '#999' }}>
            • 系统会自动检查重复数据并跳过
          </div>
        </div>
      </Modal>
    </div>
  )
}

export default AddWorkCardData
