import React, { useEffect, useState } from 'react'
import {
  Table,
  Button,
  Space,
  Input,
  message,
  Popconfirm,
  Drawer,
  Form,
  Row,
  Col,
  Divider,
  Modal,
  InputNumber
} from 'antd'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ReloadOutlined
} from '@ant-design/icons'
import { defectSchemeApi, DefectScheme, DefectStep, DefectMaterial } from '../services/defectSchemeApi'

const DefectSchemeManager: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<DefectScheme[]>([])
  const [params, setParams] = useState({ skip: 0, limit: 100, comp_pn: '', keyword: '' })
  
  // Drawer & Form State
  const [drawerVisible, setDrawerVisible] = useState(false)
  const [editingScheme, setEditingScheme] = useState<DefectScheme | null>(null)
  const [schemeForm] = Form.useForm()
  
  // Steps State (local to the drawer)
  const [steps, setSteps] = useState<DefectStep[]>([])
  const [stepModalVisible, setStepModalVisible] = useState(false)
  const [editingStep, setEditingStep] = useState<DefectStep | null>(null)
  const [editingStepIndex, setEditingStepIndex] = useState<number>(-1)
  const [stepForm] = Form.useForm()

  // Material State (local to the step modal)
  const [materials, setMaterials] = useState<DefectMaterial[]>([])
  
  const loadData = async () => {
    setLoading(true)
    try {
      const result = await defectSchemeApi.list(params.skip, params.limit, params.comp_pn, params.keyword)
      setData(result)
      // Note: Backend currently returns list, not {items, total}. Assuming all for now or modify backend later.
    } catch (error) {
      message.error('加载数据失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [params])

  const handleSearch = (values: any) => {
    setParams({ ...params, ...values, skip: 0 })
  }

  const handleDelete = async (id: number) => {
    try {
      await defectSchemeApi.delete(id)
      message.success('删除成功')
      loadData()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const openDrawer = (scheme?: DefectScheme) => {
    setEditingScheme(scheme || null)
    if (scheme) {
      schemeForm.setFieldsValue(scheme)
      setSteps(scheme.steps || [])
    } else {
      schemeForm.resetFields()
      setSteps([])
    }
    setDrawerVisible(true)
  }

  const closeDrawer = () => {
    setDrawerVisible(false)
    setEditingScheme(null)
    schemeForm.resetFields()
  }

  const handleSaveScheme = async () => {
    try {
      const values = await schemeForm.validateFields()
      const schemeData: DefectScheme = {
        ...values,
        steps: steps
      }

      if (editingScheme && editingScheme.id) {
        await defectSchemeApi.update(editingScheme.id, schemeData)
        message.success('更新成功')
      } else {
        await defectSchemeApi.create(schemeData)
        message.success('创建成功')
      }
      closeDrawer()
      loadData()
    } catch (error) {
      message.error('保存失败')
    }
  }

  // --- Step Handling ---

  const openStepModal = (step?: DefectStep, index: number = -1) => {
    setEditingStep(step || null)
    setEditingStepIndex(index)
    if (step) {
      stepForm.setFieldsValue(step)
      setMaterials(step.materials || [])
    } else {
      stepForm.resetFields()
      // Auto-increment step number
      const nextNum = steps.length > 0 ? Math.max(...steps.map(s => s.step_number)) + 1 : 1
      stepForm.setFieldsValue({ step_number: nextNum, manhour: 0 })
      setMaterials([])
    }
    setStepModalVisible(true)
  }

  const handleSaveStep = async () => {
    try {
      const values = await stepForm.validateFields()
      const newStep: DefectStep = {
        ...values,
        materials: materials
      }

      const newSteps = [...steps]
      if (editingStepIndex > -1) {
        newSteps[editingStepIndex] = newStep
      } else {
        newSteps.push(newStep)
      }
      // Re-sort steps by step_number
      newSteps.sort((a, b) => a.step_number - b.step_number)
      
      setSteps(newSteps)
      setStepModalVisible(false)
    } catch (error) {
      // validation failed
    }
  }

  const handleDeleteStep = (index: number) => {
    const newSteps = [...steps]
    newSteps.splice(index, 1)
    setSteps(newSteps)
  }

  // --- Material Handling (Inside Step Modal) ---
  // For simplicity, let's use a small inline form or just editable table for materials?
  // Let's use a simple list with add/remove for now.
  
  const addMaterial = () => {
    setMaterials([...materials, { part_number: '', amount: 1, unit: 'EA', remark: '' }])
  }

  const updateMaterial = (index: number, field: keyof DefectMaterial, value: any) => {
    const newMats = [...materials]
    newMats[index] = { ...newMats[index], [field]: value }
    setMaterials(newMats)
  }

  const removeMaterial = (index: number) => {
    const newMats = [...materials]
    newMats.splice(index, 1)
    setMaterials(newMats)
  }

  const columns = [
    { title: '部件件号 (P/N)', dataIndex: 'comp_pn', key: 'comp_pn', width: 150 },
    { title: '缺陷目录号', dataIndex: 'defect_catalog', key: 'defect_catalog', width: 100 },
    { title: '机型', dataIndex: 'type', key: 'type', width: 100 },
    { title: '客户', dataIndex: 'cust', key: 'cust', width: 100 },
    { title: '部件名称', dataIndex: 'comp_name', key: 'comp_name', width: 140 },
    { title: '工卡描述 (英文)', dataIndex: 'jc_desc_en', key: 'jc_desc_en', ellipsis: true },
    { title: '工卡描述 (中文)', dataIndex: 'jc_desc_cn', key: 'jc_desc_cn', ellipsis: true },
    { title: '总工时', dataIndex: 'manhour', key: 'manhour', width: 100 },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_: any, record: DefectScheme) => (
        <Space size="middle">
          <Button type="link" icon={<EditOutlined />} onClick={() => openDrawer(record)}>编辑</Button>
          <Popconfirm title="确定删除?" onConfirm={() => handleDelete(record.id!)}>
            <Button type="link" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      )
    }
  ]

  const stepColumns = [
    { title: '#', dataIndex: 'step_number', key: 'step_number', width: 60 },
    { title: '步骤描述 (EN)', dataIndex: 'step_desc_en', key: 'step_desc_en', ellipsis: true },
    { title: '步骤描述 (CN)', dataIndex: 'step_desc', key: 'step_desc', ellipsis: true },
    { title: '工时', dataIndex: 'manhour', key: 'manhour', width: 80 },
    { 
      title: '航材数', 
      key: 'mat_count', 
      width: 80, 
      render: (_: any, r: DefectStep) => r.materials?.length || 0 
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_: any, record: DefectStep, index: number) => (
        <Space>
          <Button type="link" size="small" onClick={() => openStepModal(record, index)}>编辑</Button>
          <Button type="link" danger size="small" onClick={() => handleDeleteStep(index)}>删除</Button>
        </Space>
      )
    }
  ]

  return (
    <div style={{ padding: 24, background: '#fff' }}>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <Space>
          <Input.Search
            placeholder="搜索 P/N 或 关键词"
            onSearch={val => handleSearch({ keyword: val })}
            style={{ width: 300 }}
            allowClear
          />
          <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
        </Space>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => openDrawer()}>新增方案</Button>
      </div>

      <Table
        columns={columns}
        dataSource={data}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 20 }}
      />

      <Drawer
        title={editingScheme ? "编辑标准缺陷方案" : "新增标准缺陷方案"}
        width={800}
        onClose={closeDrawer}
        open={drawerVisible}
        extra={
          <Space>
            <Button onClick={closeDrawer}>取消</Button>
            <Button type="primary" onClick={handleSaveScheme}>保存</Button>
          </Space>
        }
      >
        <Form form={schemeForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="comp_pn" label="部件件号 (P/N)" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="defect_catalog" label="缺陷目录号 (Catalog)" rules={[{ required: true }]}>
                <InputNumber style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="jc_desc_en" label="工卡描述 (英文)">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="jc_desc_cn" label="工卡描述 (中文)">
            <Input.TextArea rows={2} />
          </Form.Item>
          
          <Row gutter={16}>
            <Col span={12}>
               <Form.Item name="candidate_history_wo" label="候选历史工卡指令号">
                 <Input />
               </Form.Item>
            </Col>
            <Col span={12}>
              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item name="type" label="机型">
                    <Input />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item name="cust" label="客户">
                    <Input />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item name="comp_name" label="部件名称">
                    <Input />
                  </Form.Item>
                </Col>
              </Row>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="key_words_1" label="关键词 1">
                <Input />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="key_words_2" label="关键词 2">
                <Input />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="manhour" label="总工时">
                <InputNumber style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          
          <Row gutter={16}>
             <Col span={8}>
                <Form.Item name="trade" label="工种">
                   <Input />
                </Form.Item>
             </Col>
             <Col span={8}>
                <Form.Item name="zone" label="区域 (Zone)">
                   <Input />
                </Form.Item>
             </Col>
             <Col span={8}>
                <Form.Item name="loc" label="位置 (Loc)">
                   <Input />
                </Form.Item>
             </Col>
          </Row>

          <Divider orientation="left">方案步骤 (Steps)</Divider>
          
          <Button type="dashed" onClick={() => openStepModal()} block icon={<PlusOutlined />} style={{ marginBottom: 16 }}>
            添加步骤
          </Button>
          
          <Table
            columns={stepColumns}
            dataSource={steps}
            rowKey="step_number"
            pagination={false}
            size="small"
          />
        </Form>
      </Drawer>

      <Modal
        title={editingStep ? `编辑步骤 #${editingStep.step_number}` : "新增步骤"}
        open={stepModalVisible}
        onCancel={() => setStepModalVisible(false)}
        onOk={handleSaveStep}
        width={700}
      >
        <Form form={stepForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="step_number" label="步骤序号" rules={[{ required: true }]}>
                <InputNumber />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="manhour" label="步骤工时">
                <InputNumber />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="refer_manual" label="参考手册">
            <Input />
          </Form.Item>
          <Form.Item name="step_desc_en" label="步骤描述 (英文)">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="step_desc" label="步骤描述 (中文)">
            <Input.TextArea rows={3} />
          </Form.Item>

          <Divider orientation="left" style={{ fontSize: 14 }}>航材列表 (Materials)</Divider>
          
          {materials.map((mat, idx) => (
            <div key={idx} style={{ display: 'flex', marginBottom: 8, gap: 8 }}>
              <Input 
                placeholder="件号" 
                value={mat.part_number} 
                onChange={e => updateMaterial(idx, 'part_number', e.target.value)} 
                style={{ flex: 2 }}
              />
              <InputNumber 
                placeholder="数量" 
                value={mat.amount} 
                onChange={val => updateMaterial(idx, 'amount', val)} 
                style={{ width: 80 }}
              />
              <Input 
                placeholder="单位" 
                value={mat.unit} 
                onChange={e => updateMaterial(idx, 'unit', e.target.value)} 
                style={{ width: 80 }}
              />
               <Input 
                placeholder="备注" 
                value={mat.remark} 
                onChange={e => updateMaterial(idx, 'remark', e.target.value)} 
                style={{ flex: 1 }}
              />
              <Button type="text" danger icon={<DeleteOutlined />} onClick={() => removeMaterial(idx)} />
            </div>
          ))}
          <Button type="dashed" onClick={addMaterial} block icon={<PlusOutlined />}>
            添加航材
          </Button>
        </Form>
      </Modal>
    </div>
  )
}

export default DefectSchemeManager
