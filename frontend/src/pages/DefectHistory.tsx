import React, { useState, useEffect } from 'react'
import {
  Card,
  Button,
  Space,
  Table,
  message,
  Typography,
  Tag,
  Progress,
  Row,
  Col,
  Statistic,
  Empty,
  Popconfirm
} from 'antd'
import {
  ReloadOutlined,
  HomeOutlined,
  DownloadOutlined,
  EyeOutlined,
  PlayCircleOutlined,
  DeleteOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { defectApi, DefectList } from '../services/defectApi'

const { Title } = Typography

interface ProcessingStatus {
  defect_list_id: number
  total_records: number
  cleaned_count: number
  matched_count: number
  cleaning_status: string
  cleaning_progress: number
  matching_status: string
  matching_progress: number
  processing_stage: string
  last_processed_at: string | null
}

const DefectHistory: React.FC = () => {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [defectLists, setDefectLists] = useState<DefectList[]>([])
  const [statusMap, setStatusMap] = useState<Map<number, ProcessingStatus>>(new Map())

  useEffect(() => {
    loadDefectLists()
  }, [])

  const loadDefectLists = async () => {
    try {
      setLoading(true)
      const lists = await defectApi.getLists()
      setDefectLists(lists)

      // 加载每个清单的处理状态
      for (const list of lists) {
        try {
          const status = await defectApi.getProcessingStatus(list.id)
          setStatusMap(prev => new Map(prev).set(list.id, status))
        } catch (error) {
          console.error(`加载清单 ${list.id} 状态失败:`, error)
        }
      }
    } catch (error: any) {
      message.error('加载缺陷清单失败: ' + (error.message || error))
    } finally {
      setLoading(false)
    }
  }

  const getStatusTag = (status: string) => {
    const statusMap: Record<string, { color: string; text: string }> = {
      pending: { color: 'default', text: '待处理' },
      processing: { color: 'processing', text: '处理中' },
      completed: { color: 'success', text: '已完成' },
      failed: { color: 'error', text: '失败' }
    }
    const config = statusMap[status] || statusMap.pending
    return <Tag color={config.color}>{config.text}</Tag>
  }

  const getStageText = (stage: string) => {
    const stageMap: Record<string, string> = {
      upload: '已上传',
      cleaning: '清洗中',
      matching: '匹配中',
      completed: '已完成'
    }
    return stageMap[stage] || stage
  }

  const handleExportCleaned = async (defectListId: number) => {
    try {
      await defectApi.exportCleanedData(defectListId)
      message.success('导出成功')
    } catch (error: any) {
      message.error('导出失败: ' + (error.message || error))
    }
  }

  const handleExportMatched = async (defectListId: number) => {
    try {
      await defectApi.exportMatchedData(defectListId)
      message.success('导出成功')
    } catch (error: any) {
      message.error('导出失败: ' + (error.message || error))
    }
  }

  const handleContinueProcessing = (defectListId: number) => {
    navigate(`/defect-processing?defectListId=${defectListId}`)
  }

  const handleDeleteDefectList = async (defectListId: number) => {
    try {
      setLoading(true)
      await defectApi.deleteDefectList(defectListId)
      message.success('删除成功')
      await loadDefectLists()
    } catch (error: any) {
      message.error('删除失败: ' + (error.message || error))
    } finally {
      setLoading(false)
    }
  }

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '飞机号',
      dataIndex: 'aircraft_number',
      key: 'aircraft_number',
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
      title: '总记录数',
      key: 'total_records',
      width: 100,
      render: (_: any, record: DefectList) => {
        const status = statusMap.get(record.id)
        return status?.total_records || 0
      }
    },
    {
      title: '清洗状态',
      key: 'cleaning_status',
      width: 120,
      render: (_: any, record: DefectList) => {
        const status = statusMap.get(record.id)
        if (!status) return '-'
        return (
          <Space direction="vertical" size="small">
            {getStatusTag(status.cleaning_status)}
            <Progress
              percent={Math.round(status.cleaning_progress)}
              size="small"
              status={status.cleaning_status === 'failed' ? 'exception' : 'active'}
            />
          </Space>
        )
      }
    },
    {
      title: '匹配状态',
      key: 'matching_status',
      width: 120,
      render: (_: any, record: DefectList) => {
        const status = statusMap.get(record.id)
        if (!status) return '-'
        return (
          <Space direction="vertical" size="small">
            {getStatusTag(status.matching_status)}
            <Progress
              percent={Math.round(status.matching_progress)}
              size="small"
              status={status.matching_status === 'failed' ? 'exception' : 'active'}
            />
          </Space>
        )
      }
    },
    {
      title: '处理阶段',
      key: 'processing_stage',
      width: 100,
      render: (_: any, record: DefectList) => {
        const status = statusMap.get(record.id)
        return status ? getStageText(status.processing_stage) : '-'
      }
    },
    {
      title: '最后处理时间',
      key: 'last_processed_at',
      width: 180,
      render: (_: any, record: DefectList) => {
        const status = statusMap.get(record.id)
        if (!status?.last_processed_at) return '-'
        return new Date(status.last_processed_at).toLocaleString('zh-CN')
      }
    },
    {
      title: '操作',
      key: 'action',
      width: 300,
      fixed: 'right' as const,
      render: (_: any, record: DefectList) => {
        const status = statusMap.get(record.id)
        const canContinue = status && (
          status.cleaning_status === 'processing' ||
          status.matching_status === 'processing' ||
          (status.cleaning_status === 'completed' && status.matching_status === 'pending')
        )
        const canDelete = !!status && ((status.cleaned_count || 0) > 0 || (status.matched_count || 0) > 0)

        return (
          <Space>
            <Button
              type="link"
              icon={<EyeOutlined />}
              onClick={() => navigate(`/defect-processing?defectListId=${record.id}`)}
            >
              查看详情
            </Button>
            {canContinue && (
              <Button
                type="link"
                icon={<PlayCircleOutlined />}
                onClick={() => handleContinueProcessing(record.id)}
              >
                继续处理
              </Button>
            )}
            {(status?.cleaned_count ?? 0) > 0 && (
              <Button
                type="link"
                icon={<DownloadOutlined />}
                onClick={() => handleExportCleaned(record.id)}
              >
                导出清洗数据
              </Button>
            )}
            {(status?.matched_count ?? 0) > 0 && (
              <Button
                type="link"
                icon={<DownloadOutlined />}
                onClick={() => handleExportMatched(record.id)}
              >
                导出匹配结果
              </Button>
            )}
            {canDelete && (
              <Popconfirm
                title="确定要删除这条记录吗？"
                description="将删除该缺陷清单及其所有缺陷记录、清洗数据、匹配结果、候选工卡、导入批次数据。此操作不可恢复。"
                okText="删除"
                cancelText="取消"
                okButtonProps={{ danger: true }}
                onConfirm={() => handleDeleteDefectList(record.id)}
              >
                <Button type="link" danger icon={<DeleteOutlined />}>
                  删除
                </Button>
              </Popconfirm>
            )}
          </Space>
        )
      }
    },
  ]

  // 统计信息
  const totalLists = defectLists.length
  const completedLists = Array.from(statusMap.values()).filter(s => s.processing_stage === 'completed').length
  const processingLists = Array.from(statusMap.values()).filter(s =>
    s.cleaning_status === 'processing' || s.matching_status === 'processing'
  ).length

  return (
    <div style={{ padding: '24px', background: '#f0f2f5', minHeight: '100vh' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <Title level={2} style={{ margin: 0 }}>缺陷处理历史记录</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadDefectLists} loading={loading}>
            刷新
          </Button>
          <Button icon={<HomeOutlined />} onClick={() => navigate('/')}>
            返回首页
          </Button>
        </Space>
      </div>

      {/* 统计信息 */}
      <Row gutter={16} style={{ marginBottom: '24px' }}>
        <Col span={8}>
          <Card>
            <Statistic
              title="总清单数"
              value={totalLists}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="已完成"
              value={completedLists}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="处理中"
              value={processingLists}
              valueStyle={{ color: '#fa8c16' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 缺陷清单列表 */}
      <Card>
        <Table
          columns={columns}
          dataSource={defectLists}
          rowKey="id"
          loading={loading}
          scroll={{ x: 1400 }}
          pagination={{
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条记录`,
            pageSize: 10,
          }}
          locale={{
            emptyText: <Empty description="暂无缺陷清单" />
          }}
        />
      </Card>
    </div>
  )
}

export default DefectHistory














