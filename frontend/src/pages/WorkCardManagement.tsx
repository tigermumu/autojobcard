import React, { useState, useEffect } from 'react'
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
  Descriptions,
  Popconfirm,
  Empty
} from 'antd'
import { 
  PlusOutlined, 
  EditOutlined, 
  DeleteOutlined,
  EyeOutlined,
  ReloadOutlined,
  HomeOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { workcardApi, WorkCard, WorkCardGroup } from '../services/workcardApi'
import { configApi, Configuration } from '../services/configApi'

const { Title } = Typography
const { Search } = Input
const { Option } = Select

const WorkCardManagement: React.FC = () => {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [groups, setGroups] = useState<WorkCardGroup[]>([])
  const [filteredGroups, setFilteredGroups] = useState<WorkCardGroup[]>([])
  const [searchText, setSearchText] = useState('')
  const [configurations, setConfigurations] = useState<Configuration[]>([])
  const [configFilter, setConfigFilter] = useState<string>('all')
  
  // 查看详情相关状态
  const [viewModalVisible, setViewModalVisible] = useState(false)
  const [editModalVisible, setEditModalVisible] = useState(false)
  const [currentGroup, setCurrentGroup] = useState<WorkCardGroup | null>(null)
  const [groupWorkCards, setGroupWorkCards] = useState<WorkCard[]>([])
  const [loadingGroupCards, setLoadingGroupCards] = useState(false)
  const [currentEditWorkCard, setCurrentEditWorkCard] = useState<WorkCard | null>(null)
  const [form] = Form.useForm()

  useEffect(() => {
    loadConfigurations()
    loadGroups()
  }, [])

  useEffect(() => {
    filterGroups()
  }, [groups, searchText, configFilter])

  const loadConfigurations = async () => {
    try {
      const data = await configApi.getAll()
      setConfigurations(data as Configuration[])
    } catch (error: any) {
      // 静默处理，不影响主流程
    }
  }

  const loadGroups = async () => {
    try {
      setLoading(true)
      // 只加载已清洗的工卡分组
      const data = await workcardApi.getGroups(true)
      setGroups(data)
      setFilteredGroups(data)
    } catch (error: any) {
      // 获取详细的错误信息
      let errorMessage = '加载工卡分组失败'
      if (error?.message) {
        errorMessage += ': ' + error.message
      } else if (error?.response?.data?.detail) {
        errorMessage += ': ' + error.response.data.detail
      } else if (typeof error === 'string') {
        errorMessage += ': ' + error
      } else {
        errorMessage += ': ' + JSON.stringify(error)
      }
      message.error(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const filterGroups = () => {
    let filtered = [...groups]

    // 按搜索文本过滤
    if (searchText) {
      const searchLower = searchText.toLowerCase()
      filtered = filtered.filter(group => 
        group.aircraft_number?.toLowerCase().includes(searchLower) ||
        group.aircraft_type?.toLowerCase().includes(searchLower) ||
        group.msn?.toLowerCase().includes(searchLower) ||
        group.amm_ipc_eff?.toLowerCase().includes(searchLower)
      )
    }

    // 按构型过滤
    if (configFilter !== 'all') {
      filtered = filtered.filter(group => group.configuration_id === Number(configFilter))
    }

    setFilteredGroups(filtered)
  }

  const handleView = async (group: WorkCardGroup) => {
    try {
      setCurrentGroup(group)
      setLoadingGroupCards(true)
      setViewModalVisible(true)
      
      // 加载该组下的所有工卡
      const workcards = await workcardApi.getByGroup({
        aircraft_number: group.aircraft_number || undefined,
        aircraft_type: group.aircraft_type || undefined,
        msn: group.msn || undefined,
        amm_ipc_eff: group.amm_ipc_eff || undefined,
        configuration_id: group.configuration_id
      })
      
      setGroupWorkCards(workcards)
    } catch (error: any) {
      message.error('加载工卡详情失败: ' + (error.message || error))
    } finally {
      setLoadingGroupCards(false)
    }
  }

  const handleEdit = async (workcard: WorkCard) => {
    try {
      setCurrentEditWorkCard(workcard)
      form.setFieldsValue(workcard)
      setEditModalVisible(true)
    } catch (error: any) {
      message.error('获取工卡详情失败: ' + (error.message || error))
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await workcardApi.delete(id)
      message.success('删除成功')
      // 重新加载该组的工卡列表
      if (currentGroup) {
        handleView(currentGroup)
      }
      // 重新加载分组列表
      loadGroups()
    } catch (error: any) {
      message.error('删除失败: ' + (error.message || error))
    }
  }

  const handleDeleteGroup = async (group: WorkCardGroup) => {
    try {
      const result = await workcardApi.deleteGroup({
        aircraft_number: group.aircraft_number || undefined,
        aircraft_type: group.aircraft_type || undefined,
        msn: group.msn || undefined,
        amm_ipc_eff: group.amm_ipc_eff || undefined,
        configuration_id: group.configuration_id
      })
      
      if (result.success) {
        message.success(result.message || '删除成功')
        // 如果当前正在查看该分组，关闭查看窗口
        if (currentGroup && getGroupKey(currentGroup) === getGroupKey(group)) {
          setViewModalVisible(false)
          setCurrentGroup(null)
        }
        // 重新加载分组列表
        loadGroups()
      } else {
        message.error(result.message || '删除失败')
      }
    } catch (error: any) {
      message.error('删除失败: ' + (error.message || error))
    }
  }

  const handleSaveEdit = async () => {
    try {
      if (!currentEditWorkCard) return
      
      const values = await form.validateFields()
      await workcardApi.update(currentEditWorkCard.id, values)
      message.success('更新成功')
      setEditModalVisible(false)
      setCurrentEditWorkCard(null)
      form.resetFields()
      
      // 重新加载该组的工卡列表
      if (currentGroup) {
        handleView(currentGroup)
      }
      // 重新加载分组列表（可能工卡数量发生变化）
      loadGroups()
    } catch (error: any) {
      if (error.errorFields) {
        // 表单验证错误
        return
      }
      message.error('更新失败: ' + (error.message || error))
    }
  }

  const getConfigName = (configId: number) => {
    const config = configurations.find(c => c.id === configId)
    return config?.name || `构型 ${configId}`
  }

  const getGroupKey = (group: WorkCardGroup) => {
    return `${group.aircraft_number || ''}_${group.aircraft_type || ''}_${group.msn || ''}_${group.amm_ipc_eff || ''}_${group.configuration_id}`
  }

  // 获取数据表标题（识别标题）
  const getGroupTitle = (group: WorkCardGroup) => {
    const parts = []
    if (group.aircraft_number) parts.push(`飞机号: ${group.aircraft_number}`)
    if (group.aircraft_type) parts.push(`机型: ${group.aircraft_type}`)
    if (group.msn) parts.push(`MSN: ${group.msn}`)
    if (group.amm_ipc_eff) parts.push(`AMM/IPC EFF: ${group.amm_ipc_eff}`)
    const configName = getConfigName(group.configuration_id)
    parts.push(`构型: ${configName}`)
    
    return parts.length > 0 ? parts.join(' | ') : `未设置识别字段 (构型: ${configName})`
  }

  const columns = [
    {
      title: '标准工卡数据表',
      key: 'title',
      width: 400,
      render: (_: any, record: WorkCardGroup) => (
        <div style={{ fontWeight: 500 }}>
          {getGroupTitle(record)}
        </div>
      ),
    },
    {
      title: '工卡数量',
      dataIndex: 'count',
      key: 'count',
      width: 120,
      align: 'center' as const,
      render: (count: number) => (
        <Tag color="blue" style={{ fontSize: '14px', fontWeight: 'bold' }}>
          {count} 条
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      fixed: 'right' as const,
      render: (_: any, record: WorkCardGroup) => (
        <Space size="small">
          <Button 
            type="primary"
            icon={<EyeOutlined />}
            size="small"
            onClick={() => handleView(record)}
          >
            查看
          </Button>
          <Popconfirm
            title="确定要删除这整张数据表吗？"
            description={`将删除 ${record.count} 条工卡数据，此操作不可恢复！`}
            onConfirm={() => handleDeleteGroup(record)}
            okText="确定删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button 
              type="primary"
              danger
              icon={<DeleteOutlined />}
              size="small"
            >
              删除数据表
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  // 组内工卡列表的列定义
  const workCardColumns = [
    {
      title: '工卡指令号',
      dataIndex: 'workcard_number',
      key: 'workcard_number',
      width: 150,
      fixed: 'left' as const,
      render: (text: string) => <Tag color="blue">{text}</Tag>,
    },
    {
      title: '工卡描述',
      dataIndex: 'description',
      key: 'description',
      width: 300,
      ellipsis: {
        showTitle: true,
      },
      render: (text: string, record: WorkCard) => {
        // 优先显示description，如果没有则显示title
        return text || record.title || '-'
      },
    },
    {
      title: '主区域',
      dataIndex: 'main_area',
      key: 'main_area',
      width: 120,
    },
    {
      title: '主部件',
      dataIndex: 'main_component',
      key: 'main_component',
      width: 120,
    },
    {
      title: '一级子部件',
      dataIndex: 'first_level_subcomponent',
      key: 'first_level_subcomponent',
      width: 130,
    },
    {
      title: '二级子部件',
      dataIndex: 'second_level_subcomponent',
      key: 'second_level_subcomponent',
      width: 130,
    },
    {
      title: '方位',
      dataIndex: 'orientation',
      key: 'orientation',
      width: 100,
    },
    {
      title: '位置',
      dataIndex: 'location_index',
      key: 'location_index',
      width: 150,
      ellipsis: {
        showTitle: true,
      },
    },
    {
      title: '缺陷主体',
      dataIndex: 'defect_subject',
      key: 'defect_subject',
      width: 150,
      ellipsis: {
        showTitle: true,
      },
    },
    {
      title: '缺陷描述',
      dataIndex: 'defect_description',
      key: 'defect_description',
      width: 250,
      ellipsis: {
        showTitle: true,
      },
    },
    {
      title: '数量',
      dataIndex: 'quantity',
      key: 'quantity',
      width: 80,
      align: 'center' as const,
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      fixed: 'right' as const,
      render: (_: any, record: WorkCard) => (
        <Space size="small">
          <Button 
            type="link" 
            icon={<EditOutlined />}
            size="small"
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定要删除这条工卡吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button 
              type="link" 
              danger
              icon={<DeleteOutlined />}
              size="small"
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: '24px', background: '#f0f2f5', minHeight: '100vh' }}>
      {/* 页面头部 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <Title level={2} style={{ margin: 0 }}>标准工卡数据库管理</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadGroups} loading={loading}>
            刷新
          </Button>
          <Button icon={<HomeOutlined />} onClick={() => navigate('/')}>
            返回首页
          </Button>
        </Space>
      </div>

      {/* 操作栏 */}
      <Card style={{ marginBottom: '24px' }}>
        <Space style={{ width: '100%', justifyContent: 'space-between', flexWrap: 'wrap' }}>
          <Space wrap>
            <Search 
              placeholder="搜索飞机号、机型、MSN、AMM/IPC EFF..." 
              allowClear
              style={{ width: 300 }}
              onSearch={(value) => setSearchText(value)}
              onChange={(e) => {
                if (!e.target.value) setSearchText('')
              }}
            />
            <Select 
              value={configFilter} 
              onChange={setConfigFilter}
              style={{ width: 200 }}
              placeholder="选择构型"
            >
              <Option value="all">全部构型</Option>
              {configurations.map(config => (
                <Option key={config.id} value={String(config.id)}>
                  {config.name}
                </Option>
              ))}
            </Select>
          </Space>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/workcard/add')}>
            新增标准工卡数据表
          </Button>
        </Space>
      </Card>

      {/* 工卡分组列表 */}
      <Card>
        <Table
          columns={columns}
          dataSource={filteredGroups}
          rowKey={getGroupKey}
          loading={loading}
          scroll={{ x: 800 }}
          pagination={{
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 个数据表`,
            pageSize: 20,
            showQuickJumper: true,
          }}
          locale={{
            emptyText: <Empty description="暂无数据表，请先添加标准工卡数据" />
          }}
        />
      </Card>

      {/* 查看分组详情模态框 */}
      <Modal
        title={
          currentGroup ? (
            <span>
              工卡数据表详情 - 
              <Tag color="blue" style={{ marginLeft: 8 }}>
                {getGroupTitle(currentGroup)}
              </Tag>
            </span>
          ) : '工卡数据表详情'
        }
        open={viewModalVisible}
        onCancel={() => {
          setViewModalVisible(false)
          setCurrentGroup(null)
          setGroupWorkCards([])
        }}
        footer={[
          <Button key="close" onClick={() => {
            setViewModalVisible(false)
            setCurrentGroup(null)
            setGroupWorkCards([])
          }}>
            关闭
          </Button>
        ]}
        width={1400}
      >
        {currentGroup && (
          <Descriptions column={2} bordered style={{ marginBottom: '24px' }}>
            <Descriptions.Item label="飞机号">
              {currentGroup.aircraft_number || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="机型">
              {currentGroup.aircraft_type || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="MSN">
              {currentGroup.msn || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="AMM/IPC EFF">
              {currentGroup.amm_ipc_eff || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="构型" span={2}>
              {getConfigName(currentGroup.configuration_id)}
            </Descriptions.Item>
            <Descriptions.Item label="工卡总数" span={2}>
              <Tag color="blue" style={{ fontSize: '16px' }}>
                {currentGroup.count} 条
              </Tag>
            </Descriptions.Item>
          </Descriptions>
        )}

        <Table
          columns={workCardColumns}
          dataSource={groupWorkCards}
          rowKey="id"
          loading={loadingGroupCards}
          scroll={{ x: 1700, y: 400 }}
          pagination={{
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
            pageSize: 10,
          }}
          locale={{
            emptyText: <Empty description="暂无工卡数据" />
          }}
        />
      </Modal>

      {/* 编辑工卡模态框 */}
      <Modal
        title="编辑工卡"
        open={editModalVisible}
        onOk={handleSaveEdit}
        onCancel={() => {
          setEditModalVisible(false)
          setCurrentEditWorkCard(null)
          form.resetFields()
        }}
        width={700}
        okText="保存"
        cancelText="取消"
      >
        <Form
          form={form}
          layout="vertical"
        >
          <Form.Item label="工卡编号" name="workcard_number" rules={[{ required: true, message: '请输入工卡编号' }]}>
            <Input />
          </Form.Item>
          <Form.Item label="标题" name="title" rules={[{ required: true, message: '请输入标题' }]}>
            <Input />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item label="飞机号" name="aircraft_number">
            <Input placeholder="例如：B-1234" />
          </Form.Item>
          <Form.Item label="机型" name="aircraft_type">
            <Input placeholder="例如：A320" />
          </Form.Item>
          <Form.Item label="MSN" name="msn">
            <Input />
          </Form.Item>
          <Form.Item label="AMM/IPC EFF" name="amm_ipc_eff">
            <Input />
          </Form.Item>
          <Form.Item label="系统" name="system" rules={[{ required: true, message: '请输入系统' }]}>
            <Input />
          </Form.Item>
          <Form.Item label="部件" name="component" rules={[{ required: true, message: '请输入部件' }]}>
            <Input />
          </Form.Item>
          <Form.Item label="主区域" name="main_area">
            <Input />
          </Form.Item>
          <Form.Item label="主部件" name="main_component">
            <Input />
          </Form.Item>
          <Form.Item label="一级子部件" name="first_level_subcomponent">
            <Input />
          </Form.Item>
          <Form.Item label="二级子部件" name="second_level_subcomponent">
            <Input />
          </Form.Item>
          <Form.Item label="方位" name="orientation">
            <Input />
          </Form.Item>
          <Form.Item label="缺陷主体" name="defect_subject">
            <Input />
          </Form.Item>
          <Form.Item label="缺陷描述" name="defect_description">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item label="位置" name="location_index">
            <Input />
          </Form.Item>
          <Form.Item label="数量" name="quantity">
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default WorkCardManagement
