import React, { useEffect, useMemo, useState } from 'react'
import {
  Button,
  Card,
  Checkbox,
  Col,
  Form,
  Input,
  Layout,
  Modal,
  Popconfirm,
  Row,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
  message,
} from 'antd'
import { HomeOutlined, ReloadOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { permissionGroups } from '../constants/permissions'
import { authApi, UserCreatePayload, UserProfile, UserUpdatePayload } from '../services/authApi'

const { Content } = Layout
const { Title, Text } = Typography

const collectAllPermissions = () =>
  permissionGroups.flatMap((group) => group.items.map((item) => item.code))

const AdminUserManagement: React.FC = () => {
  const navigate = useNavigate()
  const [users, setUsers] = useState<UserProfile[]>([])
  const [loading, setLoading] = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  const [editUser, setEditUser] = useState<UserProfile | null>(null)
  const [passwordUser, setPasswordUser] = useState<UserProfile | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [createForm] = Form.useForm<UserCreatePayload>()
  const [editForm] = Form.useForm<UserUpdatePayload & { allPermissions?: boolean }>()
  const [passwordForm] = Form.useForm<{ password: string }>()

  const loadUsers = async () => {
    setLoading(true)
    try {
      const result = await authApi.listUsers()
      setUsers(result.items)
    } catch (error) {
      console.error(error)
      message.error(error instanceof Error ? error.message : '获取用户列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadUsers()
  }, [])

  const allPermissions = useMemo(() => collectAllPermissions(), [])

  const openCreate = () => {
    createForm.resetFields()
    createForm.setFieldsValue({
      is_active: true,
      is_superuser: false,
      permissions: [],
    })
    setCreateOpen(true)
  }

  const openEdit = (user: UserProfile) => {
    editForm.setFieldsValue({
      display_name: user.display_name || '',
      role_name: user.role_name || '',
      is_active: user.is_active,
      is_superuser: user.is_superuser,
      permissions: user.permissions || [],
    })
    setEditUser(user)
  }

  const handleCreate = async () => {
    const values = await createForm.validateFields()
    setSubmitting(true)
    try {
      await authApi.createUser({
        username: values.username.trim(),
        display_name: values.display_name?.trim(),
        role_name: values.role_name?.trim(),
        password: values.password,
        permissions: values.permissions || [],
        is_active: values.is_active,
        is_superuser: values.is_superuser,
      })
      message.success('用户创建成功')
      setCreateOpen(false)
      await loadUsers()
    } catch (error) {
      console.error(error)
      message.error(error instanceof Error ? error.message : '创建用户失败')
    } finally {
      setSubmitting(false)
    }
  }

  const handleEdit = async () => {
    if (!editUser) return
    const values = await editForm.validateFields()
    setSubmitting(true)
    try {
      await authApi.updateUser(editUser.id, {
        display_name: values.display_name?.trim(),
        role_name: values.role_name?.trim(),
        permissions: values.permissions || [],
        is_active: values.is_active,
        is_superuser: values.is_superuser,
      })
      message.success('用户信息已更新')
      setEditUser(null)
      await loadUsers()
    } catch (error) {
      console.error(error)
      message.error(error instanceof Error ? error.message : '更新用户失败')
    } finally {
      setSubmitting(false)
    }
  }

  const handleResetPassword = async () => {
    if (!passwordUser) return
    const values = await passwordForm.validateFields()
    setSubmitting(true)
    try {
      await authApi.updatePassword(passwordUser.id, values.password)
      message.success('密码重置成功')
      setPasswordUser(null)
      passwordForm.resetFields()
    } catch (error) {
      console.error(error)
      message.error(error instanceof Error ? error.message : '重置密码失败')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async (user: UserProfile) => {
    try {
      await authApi.deleteUser(user.id)
      message.success('用户已删除')
      await loadUsers()
    } catch (error) {
      console.error(error)
      message.error(error instanceof Error ? error.message : '删除用户失败')
    }
  }

  return (
    <Layout style={{ minHeight: '100vh', background: '#f5f5f5' }}>
      <Content style={{ padding: 24 }}>
        <Card>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
            <div>
              <Title level={3} style={{ marginBottom: 8 }}>会员与权限管理</Title>
              <Text type="secondary">管理员可创建账号、分配模块权限与左侧功能页权限。</Text>
            </div>
            <Space wrap>
              <Button icon={<HomeOutlined />} onClick={() => navigate('/')}>返回首页</Button>
              <Button icon={<ReloadOutlined />} onClick={loadUsers} loading={loading}>刷新</Button>
              <Button type="primary" onClick={openCreate}>新增用户</Button>
            </Space>
          </div>

          <Table
            rowKey="id"
            loading={loading}
            dataSource={users}
            pagination={{ pageSize: 10 }}
            columns={[
              { title: '用户名', dataIndex: 'username', width: 160 },
              { title: '显示名', dataIndex: 'display_name', width: 160, render: (value) => value || '-' },
              { title: '身份', dataIndex: 'role_name', width: 140, render: (value) => value || '-' },
              {
                title: '状态',
                dataIndex: 'is_active',
                width: 100,
                render: (value) => value ? <Tag color="green">启用</Tag> : <Tag color="red">停用</Tag>,
              },
              {
                title: '管理员',
                dataIndex: 'is_superuser',
                width: 100,
                render: (value) => value ? <Tag color="blue">是</Tag> : <Tag>否</Tag>,
              },
              {
                title: '权限数',
                width: 100,
                render: (_, record) => record.is_superuser ? '全部' : (record.permissions?.length || 0),
              },
              {
                title: '操作',
                key: 'actions',
                width: 280,
                render: (_, record) => (
                  <Space wrap>
                    <Button size="small" onClick={() => openEdit(record)}>编辑</Button>
                    <Button size="small" onClick={() => {
                      passwordForm.resetFields()
                      setPasswordUser(record)
                    }}>
                      重置密码
                    </Button>
                    <Popconfirm
                      title="确认删除该用户？"
                      okText="删除"
                      cancelText="取消"
                      onConfirm={() => handleDelete(record)}
                    >
                      <Button size="small" danger>删除</Button>
                    </Popconfirm>
                  </Space>
                ),
              },
            ]}
          />
        </Card>
      </Content>

      <Modal
        title="新增用户"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onOk={handleCreate}
        okText="创建"
        confirmLoading={submitting}
        width={860}
        destroyOnClose
      >
        <Form form={createForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="username" label="用户名" rules={[{ required: true, message: '请输入用户名' }]}>
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="password" label="初始密码" rules={[{ required: true, message: '请输入初始密码' }, { min: 6, message: '至少 6 位' }]}>
                <Input.Password />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="display_name" label="显示名">
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="role_name" label="身份名称">
                <Input placeholder="如：管理员、工艺员、审核员" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="is_active" label="启用账号" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="is_superuser" label="超级管理员" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item shouldUpdate noStyle>
            {() => {
              const isSuperuser = createForm.getFieldValue('is_superuser')
              return (
                <Form.Item name="permissions" label="权限分配">
                  <Checkbox.Group style={{ width: '100%' }} disabled={isSuperuser}>
                    <Space direction="vertical" style={{ width: '100%' }}>
                      {permissionGroups.map((group) => (
                        <Card key={group.title} size="small" title={group.title}>
                          <Space wrap>
                            {group.items.map((item) => (
                              <Checkbox key={item.code} value={item.code}>
                                {item.label}
                              </Checkbox>
                            ))}
                          </Space>
                        </Card>
                      ))}
                    </Space>
                  </Checkbox.Group>
                </Form.Item>
              )
            }}
          </Form.Item>
          <Button
            type="link"
            onClick={() => createForm.setFieldValue('permissions', allPermissions)}
            style={{ paddingLeft: 0 }}
          >
            一键全选权限
          </Button>
        </Form>
      </Modal>

      <Modal
        title={editUser ? `编辑用户：${editUser.username}` : '编辑用户'}
        open={Boolean(editUser)}
        onCancel={() => setEditUser(null)}
        onOk={handleEdit}
        okText="保存"
        confirmLoading={submitting}
        width={860}
        destroyOnClose
      >
        <Form form={editForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="用户名">
                <Input value={editUser?.username} disabled />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="role_name" label="身份名称">
                <Input />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="display_name" label="显示名">
                <Input />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="is_active" label="启用账号" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="is_superuser" label="超级管理员" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item shouldUpdate noStyle>
            {() => {
              const isSuperuser = editForm.getFieldValue('is_superuser')
              return (
                <Form.Item name="permissions" label="权限分配">
                  <Checkbox.Group style={{ width: '100%' }} disabled={isSuperuser}>
                    <Space direction="vertical" style={{ width: '100%' }}>
                      {permissionGroups.map((group) => (
                        <Card key={group.title} size="small" title={group.title}>
                          <Space wrap>
                            {group.items.map((item) => (
                              <Checkbox key={item.code} value={item.code}>
                                {item.label}
                              </Checkbox>
                            ))}
                          </Space>
                        </Card>
                      ))}
                    </Space>
                  </Checkbox.Group>
                </Form.Item>
              )
            }}
          </Form.Item>
          <Button
            type="link"
            onClick={() => editForm.setFieldValue('permissions', allPermissions)}
            style={{ paddingLeft: 0 }}
          >
            一键全选权限
          </Button>
        </Form>
      </Modal>

      <Modal
        title={passwordUser ? `重置密码：${passwordUser.username}` : '重置密码'}
        open={Boolean(passwordUser)}
        onCancel={() => {
          setPasswordUser(null)
          passwordForm.resetFields()
        }}
        onOk={handleResetPassword}
        okText="保存"
        confirmLoading={submitting}
        destroyOnClose
      >
        <Form form={passwordForm} layout="vertical">
          <Form.Item name="password" label="新密码" rules={[{ required: true, message: '请输入新密码' }, { min: 6, message: '至少 6 位' }]}>
            <Input.Password />
          </Form.Item>
        </Form>
      </Modal>
    </Layout>
  )
}

export default AdminUserManagement
