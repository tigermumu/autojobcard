import React, { useState, useEffect } from 'react'
import { 
  Card, 
  Button, 
  Space, 
  Modal, 
  Form, 
  Input, 
  Select, 
  message,
  Typography,
  Tag,
  Row,
  Col,
  Statistic,
  Table,
  Popconfirm
} from 'antd'
import { 
  PlusOutlined, 
  EditOutlined, 
  DeleteOutlined,
  BranchesOutlined,
  SaveOutlined,
  HomeOutlined,
  ReloadOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import IndexDataTreeEditor from './IndexDataTreeEditor'
import { configApi, Configuration as ApiConfiguration } from '../services/configApi'
import { indexDataApi, IndependentFields } from '../services/indexDataApi'
import { TreeNode, flatToTree, treeToFlat } from '../utils/treeConverter'

const { Title } = Typography
const { Option } = Select

// 扩展后端返回的Configuration接口
interface Configuration extends ApiConfiguration {
  msn?: string
  model?: string
  vartab?: string
  customer?: string
  amm_ipc_eff?: string
}

// 扩展IndependentFields以匹配前端命名
interface IndependentIndexFields {
  orientation: string[]
  defectSubject: string[]  // 注意：前端使用camelCase
  defectDescription: string[]
  location: string[]
  quantity: string[]
}

const ConfigurationIndexData: React.FC = () => {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  
  // 构型列表
  const [configurations, setConfigurations] = useState<Configuration[]>([])
  
  // 当前选中的构型
  const [currentConfig, setCurrentConfig] = useState<number | null>(null)
  
  // 树形数据（每个构型对应一个）
  const [treeData, setTreeData] = useState<Map<number, TreeNode[]>>(new Map())
  // 独立索引字段（每个构型对应一组）
  const [independentFieldsMap, setIndependentFieldsMap] = useState<Map<number, IndependentIndexFields>>(new Map())
  
  // 构型管理模态框
  const [isConfigModalVisible, setIsConfigModalVisible] = useState(false)
  const [editingConfig, setEditingConfig] = useState<Configuration | null>(null)
  const [configForm] = Form.useForm()
  
  // 编辑模式
  const [isEditing, setIsEditing] = useState(false)
  
  // 统计信息
  const [statistics, setStatistics] = useState({
    totalAreas: 0,
    totalComponents: 0,
    totalSub1: 0,
    totalSub2: 0
  })

  // 加载构型列表
  useEffect(() => {
    loadConfigurations()
  }, [])

  // 加载当前构型的索引数据
  useEffect(() => {
    if (currentConfig) {
      loadIndexData(currentConfig)
    }
  }, [currentConfig])

  // 加载构型列表
  const loadConfigurations = async () => {
    try {
      setLoading(true)
      const data = await configApi.getAll()
      setConfigurations(data as Configuration[])
      if (data.length > 0 && !currentConfig) {
        setCurrentConfig(data[0].id)
      }
    } catch (error: any) {
      console.error('加载构型失败:', error)
      message.error('加载构型列表失败: ' + error.message)
    } finally {
      setLoading(false)
    }
  }

  // 加载索引数据
  const loadIndexData = async (configurationId: number) => {
    try {
      setLoading(true)
      
      // 加载层级数据
      const hierarchyData = await indexDataApi.getHierarchy(configurationId)
      const flatData = await indexDataApi.getAll({ configuration_id: configurationId })
      
      // 转换为树形结构
      const tree = flatToTree(flatData)
      const updatedMap = new Map(treeData)
      updatedMap.set(configurationId, tree)
      setTreeData(updatedMap)
      
      // 加载构型信息以获取独立对照字段
      const config = await configApi.getById(configurationId)
      let independentFields: IndependentIndexFields = {
        orientation: [],
        defectSubject: [],
        defectDescription: [],
        location: [],
        quantity: [],
      }
      
      // 从field_mapping加载独立对照字段
      if (config.field_mapping && typeof config.field_mapping === 'object') {
        independentFields = {
          orientation: config.field_mapping.orientation || [],
          defectSubject: config.field_mapping.defectSubject || [],
          defectDescription: config.field_mapping.defectDescription || [],
          location: config.field_mapping.location || [],
          quantity: config.field_mapping.quantity || [],
        }
      }
      
      const fieldsMap = new Map(independentFieldsMap)
      fieldsMap.set(configurationId, independentFields)
      setIndependentFieldsMap(fieldsMap)
      
      // 更新统计
      updateStatistics(configurationId)
      
    } catch (error: any) {
      console.error('加载索引数据失败:', error)
      message.error('加载索引数据失败: ' + error.message)
    } finally {
      setLoading(false)
    }
  }

  // 更新统计信息
  const updateStatistics = (configId: number) => {
    const trees = treeData.get(configId) || []
    let totalAreas = 0
    let totalComponents = 0
    let totalSub1 = 0
    let totalSub2 = 0

    const countNodes = (nodes: TreeNode[]) => {
      nodes.forEach(node => {
        if (node.type === '主区域') totalAreas++
        if (node.type === '主部件') totalComponents++
        if (node.type === '一级子部件') totalSub1++
        if (node.type === '二级子部件') totalSub2++
        
        if (node.children) {
          countNodes(node.children)
        }
      })
    }

    countNodes(trees)
    
    setStatistics({
      totalAreas,
      totalComponents,
      totalSub1,
      totalSub2
    })
  }

  // 切换构型
  const handleConfigChange = (configId: number) => {
    setCurrentConfig(configId)
    updateStatistics(configId)
    setIsEditing(false)
  }

  // 树形数据更新回调
  const handleTreeDataChange = (newTreeData: TreeNode[]) => {
    if (currentConfig) {
      const updatedMap = new Map(treeData)
      updatedMap.set(currentConfig, newTreeData)
      setTreeData(updatedMap)
      updateStatistics(currentConfig)
    }
  }

  // 独立字段操作
  const addIndependentValue = (field: keyof IndependentIndexFields, value: string) => {
    if (!currentConfig || !value.trim()) return
    const map = new Map(independentFieldsMap)
    const current = map.get(currentConfig) as IndependentIndexFields
    if (!current[field].includes(value.trim())) {
      current[field] = [...current[field], value.trim()]
      map.set(currentConfig, { ...current })
      setIndependentFieldsMap(map)
    }
  }

  const removeIndependentValue = (field: keyof IndependentIndexFields, value: string) => {
    if (!currentConfig) return
    const map = new Map(independentFieldsMap)
    const current = map.get(currentConfig) as IndependentIndexFields
    current[field] = current[field].filter(v => v !== value)
    map.set(currentConfig, { ...current })
    setIndependentFieldsMap(map)
  }

  // 保存索引数据
  const handleSaveIndexData = async () => {
    if (!currentConfig) {
      return
    }

    try {
      setLoading(true)
      
      // 将树形数据转换为扁平数据
      const trees = treeData.get(currentConfig) || []
      const flatData = treeToFlat(trees, currentConfig)
      
      
      // 保存独立对照字段到构型的field_mapping
      const independentFields = independentFieldsMap.get(currentConfig)
      if (independentFields) {
        await configApi.update(currentConfig, {
          field_mapping: independentFields
        })
      }
      
      // 使用替换方法（删除旧的，创建新的）
      await indexDataApi.replaceIndexData(currentConfig, flatData)
      
      // 重新加载数据
      await loadIndexData(currentConfig)
      
      message.success('索引数据保存成功')
      setIsEditing(false)
    } catch (error: any) {
      console.error('保存索引数据失败:', error)
      message.error('保存索引数据失败: ' + error.message)
    } finally {
      setLoading(false)
    }
  }

  // 取消编辑
  const handleCancelEdit = () => {
    Modal.confirm({
      title: '确认取消',
      content: '未保存的更改将丢失，确定要取消吗？',
      onOk: () => {
        setIsEditing(false)
      }
    })
  }

  // 构型管理
  const handleAddConfig = () => {
    setEditingConfig(null)
    configForm.resetFields()
    setIsConfigModalVisible(true)
  }

  const handleEditConfig = (config: Configuration) => {
    setEditingConfig(config)
    configForm.setFieldsValue(config)
    setIsConfigModalVisible(true)
  }

  const handleDeleteConfig = async (id: number) => {
    try {
      await configApi.delete(id)
      
      setConfigurations(configurations.filter(c => c.id !== id))
      const updatedMap = new Map(treeData)
      updatedMap.delete(id)
      setTreeData(updatedMap)
      message.success('删除成功')
      if (currentConfig === id) {
        setCurrentConfig(null)
      }
    } catch (error: any) {
      console.error('删除构型失败:', error)
      message.error('删除构型失败: ' + error.message)
    }
  }

  const handleConfigModalOk = async () => {
    try {
      const values = await configForm.validateFields()
      
      if (editingConfig) {
        // 编辑
        const updated = await configApi.update(editingConfig.id, values)
        setConfigurations(configurations.map(config => 
          config.id === editingConfig.id ? (updated as Configuration) : config
        ))
        message.success('更新成功')
      } else {
        // 新增
        const newConfig = await configApi.create(values)
        setConfigurations([...configurations, newConfig as Configuration])
        message.success('创建成功')
      }
      setIsConfigModalVisible(false)
    } catch (error: any) {
      console.error('保存构型失败:', error)
      message.error('保存构型失败: ' + error.message)
    }
  }

  // 构型表格列
  const configColumns = [
    {
      title: '构型名称',
      dataIndex: 'name',
      key: 'name',
      width: 150,
    },
    {
      title: '机型',
      dataIndex: 'aircraft_type',
      key: 'aircraft_type',
      width: 100,
      render: (text: string) => text ? <Tag color="blue">{text}</Tag> : '-',
    },
    {
      title: 'MSN',
      dataIndex: 'msn',
      key: 'msn',
      width: 100,
    },
    {
      title: 'MODEL',
      dataIndex: 'model',
      key: 'model',
      width: 100,
    },
    {
      title: 'VARTAB',
      dataIndex: 'vartab',
      key: 'vartab',
      width: 100,
    },
    {
      title: '客户',
      dataIndex: 'customer',
      key: 'customer',
      width: 100,
    },
    {
      title: 'AMM/IPC EFF',
      dataIndex: 'amm_ipc_eff',
      key: 'amm_ipc_eff',
      width: 120,
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      render: (_: any, record: Configuration) => (
        <Space size="small">
          <Button 
            type="link" 
            icon={<EditOutlined />}
            onClick={() => handleEditConfig(record)}
            size="small"
          >
            编辑
          </Button>
          <Button 
            type="link" 
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDeleteConfig(record.id)}
            size="small"
          >
            删除
          </Button>
        </Space>
      ),
    },
  ]

  const currentConfigData = configurations.find(c => c.id === currentConfig)

  return (
    <div style={{ padding: '24px', background: '#f0f2f5', minHeight: '100vh' }}>
      {/* 页面头部 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <Title level={2} style={{ margin: 0 }}>构型与索引数据管理</Title>
        <Button icon={<HomeOutlined />} onClick={() => navigate('/')}>
          返回首页
        </Button>
      </div>

          {/* 构型管理卡片 */}
      <Card 
        title={<span><BranchesOutlined style={{ marginRight: 8 }} />飞机构型管理</span>}
        style={{ marginBottom: '24px' }}
        extra={
          <Space>
            <Button 
              icon={<ReloadOutlined />} 
              onClick={loadConfigurations}
              loading={loading}
            >
              刷新
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleAddConfig}>
              新增构型
            </Button>
          </Space>
        }
      >
        <Table
          columns={configColumns}
          dataSource={configurations}
          rowKey="id"
          size="middle"
          loading={loading}
          onRow={(record) => ({
            onClick: () => handleConfigChange(record.id),
            style: {
              cursor: 'pointer',
              backgroundColor: currentConfig === record.id ? '#e6f7ff' : undefined
            }
          })}
          pagination={false}
        />
      </Card>

      {/* 索引数据管理 */}
      {currentConfig && (
        <Card>
          {/* 构型选择和操作 */}
          <div style={{ marginBottom: '24px', padding: '16px', background: '#fafafa', borderRadius: '8px' }}>
            <Row gutter={16} align="middle">
              <Col span={8}>
                <Space direction="vertical" size="small" style={{ width: '100%' }}>
                  <span style={{ fontWeight: 'bold' }}>当前选择构型：</span>
                  <Select
                    value={currentConfig}
                    onChange={handleConfigChange}
                    style={{ width: '100%' }}
                    size="large"
                  >
                    {configurations.map(config => (
                      <Option key={config.id} value={config.id}>
                        {config.name} - {config.aircraft_type}
                      </Option>
                    ))}
                  </Select>
                </Space>
              </Col>
              <Col span={10}>
                <div style={{ padding: '8px 0' }}>
                  <div style={{ fontSize: '14px', color: '#666' }}>
                    <strong>构型信息：</strong>{currentConfigData?.description || currentConfigData?.aircraft_type} | 
                    版本: {currentConfigData?.version}
                  </div>
                </div>
              </Col>
              <Col span={6}>
                <Space size="middle">
                  {!isEditing ? (
                    <Button 
                      type="primary" 
                      icon={<EditOutlined />}
                      onClick={() => setIsEditing(true)}
                      size="large"
                      block
                    >
                      编辑索引数据
                    </Button>
                  ) : (
                    <>
                      <Button 
                        type="primary" 
                        icon={<SaveOutlined />}
                        onClick={handleSaveIndexData}
                        size="large"
                      >
                        保存
                      </Button>
                      <Button 
                        onClick={handleCancelEdit}
                        size="large"
                      >
                        取消
                      </Button>
                    </>
                  )}
                </Space>
              </Col>
            </Row>
          </div>

          {/* 统计信息 */}
          <Row gutter={16} style={{ marginBottom: '24px' }}>
            <Col span={6}>
              <Card>
                <Statistic
                  title="主区域"
                  value={statistics.totalAreas}
                  valueStyle={{ color: '#1890ff' }}
                  prefix={<Tag color="blue">主区域</Tag>}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="主部件"
                  value={statistics.totalComponents}
                  valueStyle={{ color: '#52c41a' }}
                  prefix={<Tag color="green">主部件</Tag>}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="一级子部件"
                  value={statistics.totalSub1}
                  valueStyle={{ color: '#fa8c16' }}
                  prefix={<Tag color="orange">一级</Tag>}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="二级子部件"
                  value={statistics.totalSub2}
                  valueStyle={{ color: '#722ed1' }}
                  prefix={<Tag color="purple">二级</Tag>}
                />
              </Card>
            </Col>
          </Row>

          {/* 树形编辑器 */}
          <Card style={{ background: 'white' }}>
            <IndexDataTreeEditor 
              initialData={treeData.get(currentConfig) || []}
              onDataChange={handleTreeDataChange}
              readOnly={!isEditing}
            />
          </Card>

          {/* 独立对照索引字段编辑框（与层级平级） */}
          <Card style={{ marginTop: 16 }} title="索引对照字段（与层级平级）" bordered>
            <Row gutter={16}>
              {(['orientation','defectSubject','defectDescription','location','quantity'] as (keyof IndependentIndexFields)[]).map((fieldKey) => {
                const fieldTitleMap: Record<keyof IndependentIndexFields, string> = {
                  orientation: '方位',
                  defectSubject: '缺陷主体',
                  defectDescription: '缺陷描述',
                  location: '位置',
                  quantity: '数量',
                }
                const values = (currentConfig && independentFieldsMap.get(currentConfig)) ? (independentFieldsMap.get(currentConfig) as IndependentIndexFields)[fieldKey] : []
                let inputRef: any
                return (
                  <Col span={12} key={fieldKey} style={{ marginBottom: 12 }}>
                    <Card size="small" title={fieldTitleMap[fieldKey]}>
                      <Space wrap size={[8,8]}>
                        {values.map((v) => (
                          <Tag
                            key={v}
                            closable={isEditing}
                            onClose={() => removeIndependentValue(fieldKey, v)}
                            color="geekblue"
                          >
                            {v}
                          </Tag>
                        ))}
                        {isEditing && (
                          <Input
                            placeholder={`添加${fieldTitleMap[fieldKey]}`}
                            style={{ width: 200 }}
                            onPressEnter={(e) => {
                              addIndependentValue(fieldKey, (e.target as HTMLInputElement).value)
                              ;(e.target as HTMLInputElement).value = ''
                            }}
                            allowClear
                          />
                        )}
                      </Space>
                    </Card>
                  </Col>
                )
              })}
            </Row>
          </Card>
        </Card>
      )}

      {/* 构型管理模态框 */}
      <Modal
        title={editingConfig ? '编辑构型' : '新增构型'}
        open={isConfigModalVisible}
        onOk={handleConfigModalOk}
        onCancel={() => setIsConfigModalVisible(false)}
        width={800}
      >
        <Form
          form={configForm}
          layout="vertical"
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label="构型名称"
                rules={[{ required: true, message: '请输入构型名称' }]}
              >
                <Input placeholder="例如：A320-200标准构型" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="aircraft_type"
                label="机型"
              >
                <Input placeholder="例如：A320-200" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="msn"
                label="MSN"
              >
                <Input placeholder="请输入MSN" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="model"
                label="MODEL"
              >
                <Input placeholder="请输入MODEL" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="vartab"
                label="VARTAB"
              >
                <Input placeholder="请输入VARTAB" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="customer"
                label="客户"
              >
                <Input placeholder="请输入客户" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={24}>
              <Form.Item
                name="amm_ipc_eff"
                label="AMM/IPC EFF"
              >
                <Input placeholder="请输入AMM/IPC EFF" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="description"
            label="描述"
          >
            <Input.TextArea 
              placeholder="请输入描述信息" 
              rows={3}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default ConfigurationIndexData
