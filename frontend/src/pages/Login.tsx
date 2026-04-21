import React, { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Button, Card, Form, Input, Layout, Typography, message } from 'antd'
import { LockOutlined, UserOutlined } from '@ant-design/icons'
import { useAuth } from '../contexts/AuthContext'

const { Content } = Layout
const { Title, Paragraph } = Typography

const Login: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { login } = useAuth()
  const [submitting, setSubmitting] = useState(false)

  const redirectTo = (location.state as { from?: string } | null)?.from || '/'

  const handleSubmit = async (values: { username: string; password: string }) => {
    setSubmitting(true)
    try {
      await login(values.username, values.password)
      message.success('登录成功')
      navigate(redirectTo, { replace: true })
    } catch (error) {
      console.error(error)
      message.error(error instanceof Error ? error.message : '登录失败，请重试')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Layout style={{ minHeight: '100vh', background: '#f0f2f5' }}>
      <Content style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
        <Card style={{ width: 420, borderRadius: 12 }}>
          <div style={{ textAlign: 'center', marginBottom: 24 }}>
            <Title level={2} style={{ marginBottom: 8 }}>飞机方案处理系统</Title>
            <Paragraph style={{ marginBottom: 0, color: '#666' }}>
              请先登录后再访问系统功能
            </Paragraph>
          </div>

          <Form layout="vertical" onFinish={handleSubmit}>
            <Form.Item
              name="username"
              label="用户名"
              rules={[{ required: true, message: '请输入用户名' }]}
            >
              <Input prefix={<UserOutlined />} placeholder="请输入用户名" autoComplete="username" />
            </Form.Item>
            <Form.Item
              name="password"
              label="密码"
              rules={[{ required: true, message: '请输入密码' }]}
            >
              <Input.Password prefix={<LockOutlined />} placeholder="请输入密码" autoComplete="current-password" />
            </Form.Item>
            <Button type="primary" htmlType="submit" loading={submitting} block size="large">
              登录
            </Button>
          </Form>
        </Card>
      </Content>
    </Layout>
  )
}

export default Login
