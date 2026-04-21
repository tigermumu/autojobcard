import React, { useEffect, useMemo, useState } from 'react'
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { Layout, Typography, Card, Row, Col, Select, Button, message, Result, Space, Tag, Modal, Form, Input } from 'antd'
import EnglishBatchImportDebug from './pages/EnglishBatchImportDebug'
import ChineseJobCardBatchProcess from './pages/ChineseJobCardBatchProcess'
import DefectCheck from './pages/DefectCheck'
import Login from './pages/Login'
import AdminUserManagement from './pages/AdminUserManagement'
import ProtectedRoute from './components/ProtectedRoute'
import { PermissionCodes } from './constants/permissions'
import { useAuth } from './contexts/AuthContext'
import { authApi } from './services/authApi'
import { fetchLLMModels, selectLLMModel, LLMModelInfo } from './services/llmApi'

const { Content } = Layout
const { Title, Paragraph } = Typography

const UserActionBar: React.FC = () => {
  const navigate = useNavigate()
  const { user, logout, loading, isAuthenticated } = useAuth()
  const [open, setOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [form] = Form.useForm()

  if (loading || !isAuthenticated) return null

  const close = () => {
    setOpen(false)
    form.resetFields()
  }

  const submit = async () => {
    try {
      const values = await form.validateFields()
      setSubmitting(true)
      const res = await authApi.changePassword({
        old_password: String(values.old_password || ''),
        new_password: String(values.new_password || ''),
      })
      message.success(res.message || '密码已修改')
      close()
    } catch (e: any) {
      if (e?.errorFields) return
      message.error(e?.message || '修改密码失败')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <div style={{ position: 'fixed', left: 12, bottom: 12, zIndex: 1100, maxWidth: 320 }}>
        <Card
          size="small"
          styles={{ body: { padding: 10 } }}
          style={{ background: 'rgba(255,255,255,0.92)', boxShadow: '0 6px 16px rgba(0,0,0,0.12)', borderRadius: 10 }}
        >
          <Space direction="vertical" size={8} style={{ width: '100%' }}>
            <Space wrap>
              <Tag color="blue">{user?.display_name || user?.username || '未登录用户'}</Tag>
              {user?.role_name && <Tag color="purple">{user.role_name}</Tag>}
            </Space>
            <Space wrap>
              <Button size="small" onClick={() => navigate('/')}>首页</Button>
              <Button size="small" onClick={() => setOpen(true)}>修改密码</Button>
              <Button size="small" danger onClick={logout}>退出登录</Button>
            </Space>
          </Space>
        </Card>
      </div>
      <Modal
        title="修改密码"
        open={open}
        onCancel={close}
        onOk={submit}
        okText="确认修改"
        cancelText="取消"
        okButtonProps={{ loading: submitting }}
        destroyOnClose
      >
        <Form form={form} layout="vertical" preserve={false}>
          <Form.Item
            name="old_password"
            label="原密码"
            rules={[{ required: true, message: '请输入原密码' }]}
          >
            <Input.Password autoComplete="current-password" />
          </Form.Item>
          <Form.Item
            name="new_password"
            label="新密码"
            rules={[
              { required: true, message: '请输入新密码' },
              { min: 6, message: '密码长度不能少于 6 位' },
            ]}
          >
            <Input.Password autoComplete="new-password" />
          </Form.Item>
          <Form.Item
            name="confirm_password"
            label="确认新密码"
            dependencies={['new_password']}
            rules={[
              { required: true, message: '请再次输入新密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('new_password') === value) {
                    return Promise.resolve()
                  }
                  return Promise.reject(new Error('两次输入的新密码不一致'))
                },
              }),
            ]}
          >
            <Input.Password autoComplete="new-password" />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}

const Home: React.FC = () => {
  const navigate = useNavigate()
  const { hasAnyPermission } = useAuth()
  const [currentModel, setCurrentModel] = useState<LLMModelInfo | null>(null)
  const [modelOptions, setModelOptions] = useState<LLMModelInfo[]>([])
  const [modelLoading, setModelLoading] = useState(false)

  const menuItems = useMemo(() => [
    {
      title: '🌍 英文工卡批量导入调试',
      path: '/english-batch-import',
      color: '#eb2f96',
      desc: '英文工卡批量导入调试与验证',
      visible: hasAnyPermission([PermissionCodes.MODULE_ENGLISH, PermissionCodes.ENGLISH_MAIN]),
    },
    {
      title: '🏮 中文工卡批量处理',
      path: '/chinese-batch-import',
      color: '#d4380d',
      desc: '中文工卡批量导入调试与验证',
      visible: hasAnyPermission([PermissionCodes.MODULE_CHINESE, PermissionCodes.CHINESE_MAIN]),
    },
    {
      title: '🛡️ 缺陷检查',
      path: '/defect-check',
      color: '#0958d9',
      desc: '单一部件与批量缺陷检查',
      visible: hasAnyPermission([PermissionCodes.MODULE_DEFECT_CHECK]),
    },
    {
      title: '👥 会员与权限管理',
      path: '/admin/users',
      color: '#531dab',
      desc: '管理员维护会员身份、密码和模块权限',
      visible: hasAnyPermission([PermissionCodes.MODULE_ADMIN, PermissionCodes.ADMIN_USER_MANAGEMENT]),
    }
  ].filter((item) => item.visible), [hasAnyPermission])

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
                  onClick={() => handleClick(item.path)}
                >
                  立即进入 →
                </Button>
              </Card>
            </Col>
          ))}
        </Row>
        {!menuItems.length && (
          <Result
            status="403"
            title="当前账号没有可访问模块"
            subTitle="请联系管理员为此账号分配模块与功能页权限。"
          />
        )}

      </Content>
    </Layout>
  )
}

const LoginRoute: React.FC = () => {
  const { isAuthenticated, loading } = useAuth()
  if (loading) return null
  return isAuthenticated ? <Navigate to="/" replace /> : <Login />
}

const App: React.FC = () => {
  return (
    <>
      <UserActionBar />
      <Routes>
        <Route path="/login" element={<LoginRoute />} />
        <Route path="/" element={<ProtectedRoute><Home /></ProtectedRoute>} />
        <Route
          path="/english-batch-import"
          element={
            <ProtectedRoute permissions={[PermissionCodes.ENGLISH_MAIN]}>
              <EnglishBatchImportDebug />
            </ProtectedRoute>
          }
        />
        <Route
          path="/chinese-batch-import"
          element={
            <ProtectedRoute permissions={[PermissionCodes.CHINESE_MAIN]}>
              <ChineseJobCardBatchProcess />
            </ProtectedRoute>
          }
        />
        <Route
          path="/defect-check"
          element={
            <ProtectedRoute permissions={[PermissionCodes.MODULE_DEFECT_CHECK]}>
              <DefectCheck />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/users"
          element={
            <ProtectedRoute permissions={[PermissionCodes.ADMIN_USER_MANAGEMENT]}>
              <AdminUserManagement />
            </ProtectedRoute>
          }
        />
      </Routes>
    </>
  )
}

export default App
