import React, { useState, useEffect } from 'react'
import {
  Layout,
  Typography,
  Card,
  Button,
  Upload,
  Form,
  Input,
  message,
  Space,
  Statistic,
  Row,
  Col,
  Alert,
  Table,
  Popconfirm,
  Modal,
  Tabs
} from 'antd'
import {
  UploadOutlined,
  CloudUploadOutlined,
  DownloadOutlined,
  DeleteOutlined,
  HomeOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  EyeOutlined,
  ReloadOutlined,
  PlusOutlined,
  EditOutlined,
  SaveOutlined,
  CloseOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import type { UploadFile, RcFile } from 'antd/es/upload/interface'
import type { ColumnsType } from 'antd/es/table'
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
  IndexInfo,
  IndexItem,
  ProcessStats,
  IndexItemCreate
} from '../services/defectListApi'

const { Content } = Layout
const { Title, Text } = Typography

const DefectListProcessing: React.FC = () => {
  const navigate = useNavigate()
  const [form] = Form.useForm()

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
  const [editForm] = Form.useForm()
  const [addingNew, setAddingNew] = useState(false)
  const [newItemForm] = Form.useForm()

  // 上传状态
  const [indexFile, setIndexFile] = useState<UploadFile | null>(null)
  const [uploading, setUploading] = useState(false)

  // 缺陷表状态
  const [defectFile, setDefectFile] = useState<UploadFile | null>(null)
  const [processing, setProcessing] = useState(false)
  const [processStats, setProcessStats] = useState<ProcessStats | null>(null)
  const [apiCookie, setApiCookie] = useState<string>('')

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
  const handleDelete = async (id: number) => {
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

    setUploading(true)
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
        form.resetFields()
        loadIndexList()
      }
    } catch (error: any) {
      message.error(error.response?.data?.detail || '上传失败')
    } finally {
      setUploading(false)
    }
  }

  // 处理缺陷表
  const handleProcess = async () => {
    if (!defectFile) {
      message.warning('请先选择缺陷表文件')
      return
    }

    if (!selectedIndex) {
      message.warning('请先选择一个索引表')
      return
    }

    setProcessing(true)
    setProcessStats(null)

    try {
      const { blob, stats } = await processDefects(selectedIndex.id, defectFile.originFileObj as File, apiCookie)
      setProcessStats(stats)
      const filename = `processed_${defectFile.name}`
      downloadBlob(blob, filename)
      message.success('处理完成，文件已下载')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '处理失败')
    } finally {
      setProcessing(false)
    }
  }

  // 文件选择处理
  const beforeUpload = (file: RcFile) => {
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
    editForm.setFieldsValue({
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
    editForm.resetFields()
  }

  // 保存编辑
  const saveEdit = async () => {
    if (!editingId) return
    try {
      const values = await editForm.validateFields()
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

  // 索引表列表列定义（移除行数列）
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
            onConfirm={() => handleDelete(record.id)}
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

  return (
    <Layout style={{ minHeight: '100vh', background: '#f0f2f5' }}>
      <Content style={{ padding: '24px 50px' }}>
        {/* 头部 */}
        <div style={{ marginBottom: 24 }}>
          <Button
            icon={<HomeOutlined />}
            onClick={() => navigate('/')}
            style={{ marginBottom: 16 }}
          >
            返回主页
          </Button>
          <Title level={2} style={{ margin: 0 }}>
            缺陷清单处理
          </Title>
          <Text type="secondary">
            上传索引表和缺陷清单，自动匹配并获取相关工卡信息
          </Text>
        </div>

        <Tabs
          defaultActiveKey="manage"
          items={[
            {
              key: 'manage',
              label: '索引表管理',
              children: (
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
                      <Form form={form} layout="vertical" onFinish={handleUploadIndex}>
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
                            beforeUpload={beforeUpload}
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
                            loading={uploading}
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
              )
            },
            {
              key: 'process',
              label: '缺陷表处理',
              children: (
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

                      <Form.Item label="API Cookie（可选）">
                        <Input.TextArea
                          placeholder="填写用于 API 请求的 Cookie，留空则使用默认配置"
                          value={apiCookie}
                          onChange={(e) => setApiCookie(e.target.value)}
                          rows={2}
                          disabled={!selectedIndex}
                        />
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          如 API 调用失败，请在浏览器登录系统后复制 Cookie 填入此处
                        </Text>
                      </Form.Item>

                      <Form.Item label="缺陷表文件">
                        <Upload
                          accept=".xlsx,.xls"
                          maxCount={1}
                          beforeUpload={beforeUpload}
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
                        icon={processing ? undefined : <DownloadOutlined />}
                        onClick={handleProcess}
                        loading={processing}
                        disabled={!selectedIndex || !defectFile}
                        block
                        style={{ marginTop: 16 }}
                      >
                        {processing ? '处理中...' : '处理并下载'}
                      </Button>

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
              )
            }
          ]}
        />

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

          <Form form={editForm} component={false}>
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
      </Content>
    </Layout>
  )
}

export default DefectListProcessing
