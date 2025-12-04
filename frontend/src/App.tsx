import React, { useEffect, useState } from 'react'
import { Routes, Route, useNavigate } from 'react-router-dom'
import { Layout, Typography, Card, Row, Col, Button, Select, message } from 'antd'
import ConfigurationIndexData from './pages/ConfigurationIndexData'
import WorkCardManagement from './pages/WorkCardManagement'
import AddWorkCardData from './pages/AddWorkCardData'
import DefectProcessing from './pages/DefectProcessing'
import BulkOpenWorkcards from './pages/BulkOpenWorkcards'
import EnglishBatchImportDebug from './pages/EnglishBatchImportDebug'
import { fetchLLMModels, selectLLMModel, LLMModelInfo } from './services/llmApi'

const { Content } = Layout
const { Title, Paragraph } = Typography

const Home: React.FC = () => {
  const navigate = useNavigate()
  const [currentModel, setCurrentModel] = useState<LLMModelInfo | null>(null)
  const [modelOptions, setModelOptions] = useState<LLMModelInfo[]>([])
  const [modelLoading, setModelLoading] = useState(false)

  const menuItems = [
    { title: '📁 构型与索引', path: '/configurations', color: '#1890ff', desc: '管理飞机构型及索引清单' },
    { title: '📋 标准工卡数据库管理', path: '/workcards', color: '#52c41a', desc: '管理标准工卡数据库' },
    { title: '🐛 缺陷处理与匹配', path: '/defect-processing', color: '#722ed1', desc: '缺陷清单处理、清洗与工卡匹配' },
    { title: '🔗 批量导入调试', path: '/defect-processing/batch-open', color: '#fa8c16', desc: '对接公司系统执行批量开卡导入' },
    { title: '🌍 英文工卡批量导入调试', path: '/english-batch-import', color: '#eb2f96', desc: '英文工卡批量导入调试与验证' }
  ]

  useEffect(() => {
    const loadModels = async () => {
      try {
        const response = await fetchLLMModels()
        setModelOptions(response.data)
        setCurrentModel(response.current_model)
      } catch (error) {
        console.error(error)
        message.error('获取大模型列表失败，请稍后重试')
      }
    }

    loadModels()
  }, [])

  const handleModelChange = async (value: string) => {
    setModelLoading(true)
    try {
      const response = await selectLLMModel(value)
      setCurrentModel(response.current_model)
      message.success(response.message || '已切换大模型')
    } catch (error) {
      console.error(error)
      message.error('切换大模型失败，请稍后再试')
    } finally {
      setModelLoading(false)
    }
  }

  const handleClick = (path: string) => {
    navigate(path)
  }

  return (
    <Layout style={{ minHeight: '100vh', background: '#f0f2f5' }}>
      <Content style={{ padding: '50px' }}>
        <div style={{ textAlign: 'center', marginBottom: '50px' }}>
          <Title level={1} style={{ color: '#1890ff' }}>
            🚀 飞机方案处理系统
          </Title>
          <Paragraph style={{ fontSize: '18px', color: '#666' }}>
            智能化的飞机方案处理系统 - 当前模型：{currentModel?.label ?? '加载中...'}
          </Paragraph>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '12px', marginTop: '16px' }}>
            <span style={{ fontSize: '14px', color: '#666' }}>选择大模型：</span>
            <Select
              value={currentModel?.value}
              style={{ width: 220 }}
              placeholder="请选择大模型"
              options={modelOptions.map((item) => ({
                label: `${item.label}（${item.description}）`,
                value: item.value
              }))}
              loading={modelLoading}
              onChange={handleModelChange}
              disabled={!modelOptions.length}
            />
          </div>
        </div>
        
        <Row gutter={[24, 24]} style={{ maxWidth: '1400px', margin: '0 auto' }}>
          {menuItems.map((item) => (
            <Col xs={24} sm={12} md={8} key={item.path}>
              <Card
                hoverable
                style={{
                  height: '200px',
                  borderRadius: '12px',
                  border: `2px solid ${item.color}`,
                  transition: 'all 0.3s ease',
                  cursor: 'pointer'
                }}
                bodyStyle={{
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'center',
                  alignItems: 'center',
                  height: '100%'
                }}
                onClick={() => handleClick(item.path)}
              >
                <Title level={3} style={{ color: item.color, marginBottom: '12px' }}>
                  {item.title}
                </Title>
                <Paragraph style={{ color: '#666', marginBottom: '16px' }}>
                  {item.desc}
                </Paragraph>
                <Button
                  type="primary"
                  size="large"
                  style={{
                    background: item.color,
                    borderColor: item.color,
                    borderRadius: '6px'
                  }}
                  onClick={(e) => {
                    e.stopPropagation()
                    handleClick(item.path)
                  }}
                >
                  立即进入 →
                </Button>
              </Card>
            </Col>
          ))}
        </Row>

      </Content>
    </Layout>
  )
}

const App: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/configurations" element={<ConfigurationIndexData />} />
      <Route path="/workcards" element={<WorkCardManagement />} />
      <Route path="/workcard/add" element={<AddWorkCardData />} />
      <Route path="/defect-processing" element={<DefectProcessing />} />
      <Route path="/defect-processing/batch-open" element={<BulkOpenWorkcards />} />
      <Route path="/english-batch-import" element={<EnglishBatchImportDebug />} />
    </Routes>
  )
}

export default App
