import React, { useState, useEffect } from 'react'
import { Card, Button, Input, Space, Typography, Empty, Modal, Form, InputNumber, Tag } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, CheckOutlined, CloseOutlined, SettingOutlined, CloseCircleOutlined } from '@ant-design/icons'

const { Title } = Typography

interface TreeNode {
  id: string
  name: string
  isExpanded: boolean
  isEditing?: boolean
  children?: TreeNode[]
  // 索引数据特有字段
  type?: '主区域' | '主部件' | '一级子部件' | '二级子部件'
  // 对照索引数据字段（与主区域平级，作为标准对照表）
  orientation?: string  // 方位
  defectSubject?: string  // 缺陷主体
  defectDescription?: string  // 缺陷描述
  location?: string  // 位置
  quantity?: string  // 数量
}

interface TreeNodeItemProps {
  node: TreeNode
  level: number
  onToggle: (id: string) => void
  onAdd: (parentId: string, type: TreeNode['type']) => void
  onEdit: (id: string) => void
  onDelete: (id: string) => void
  onSave: (id: string, newName: string) => void
  onCancel: (id: string) => void
  onEditAttributes: (id: string) => void
  readOnly?: boolean
}

const TreeNodeItem: React.FC<TreeNodeItemProps> = ({
  node,
  level,
  onToggle,
  onAdd,
  onEdit,
  onDelete,
  onSave,
  onCancel,
  onEditAttributes,
  readOnly = false,
}) => {
  const [editValue, setEditValue] = useState(node.name)
  const hasChildren = node.children && node.children.length > 0
  const indent = level * 24 + 12

  const handleSave = () => {
    if (editValue.trim()) {
      onSave(node.id, editValue.trim())
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSave()
    } else if (e.key === 'Escape') {
      onCancel(node.id)
      setEditValue(node.name)
    }
  }

  // 根据层级确定下一级的类型
  const getNextType = (): TreeNode['type'] => {
    if (!node.type) return '主部件'
    if (node.type === '主区域') return '主部件'
    if (node.type === '主部件') return '一级子部件'
    if (node.type === '一级子部件') return '二级子部件'
    return '二级子部件'
  }

  // 判断是否可以继续添加子节点
  const canAddChild = node.type !== '二级子部件'

  return (
    <div>
      <div
        className="tree-node-item"
        style={{
          display: 'flex',
          alignItems: 'center',
          padding: '8px 12px',
          marginBottom: '4px',
          borderRadius: '6px',
          transition: 'background-color 0.2s',
          paddingLeft: `${indent}px`,
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.backgroundColor = '#f0f8ff'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.backgroundColor = 'transparent'
        }}
      >
        {/* 展开/折叠按钮 */}
        {/* 非二级子部件都可以展开，即使没有子节点也可以展开以便添加子节点 */}
        {node.type !== '二级子部件' && (
          <Button
            type="text"
            size="small"
            icon={node.isExpanded ? '▼' : '▶'}
            onClick={() => onToggle(node.id)}
            style={{ minWidth: '24px', height: '24px', marginRight: '8px' }}
            title={hasChildren ? (node.isExpanded ? '收起' : '展开') : '展开以添加子节点'}
          />
        )}
        {node.type === '二级子部件' && (
          <span style={{ width: '24px', display: 'inline-block', marginRight: '8px' }} />
        )}

        {/* 编辑模式 */}
        {node.isEditing ? (
          <div style={{ display: 'flex', alignItems: 'center', flex: 1, gap: '8px', marginLeft: '8px' }}>
            <Input
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onKeyDown={handleKeyDown}
              style={{ flex: 1 }}
              autoFocus
              size="small"
            />
            <Button
              type="primary"
              icon={<CheckOutlined />}
              size="small"
              onClick={handleSave}
              style={{ backgroundColor: '#52c41a', borderColor: '#52c41a' }}
            />
            <Button
              icon={<CloseOutlined />}
              size="small"
              onClick={() => {
                onCancel(node.id)
                setEditValue(node.name)
              }}
            />
          </div>
        ) : (
          <>
            {/* 节点名称和类型标签 */}
            <div style={{ display: 'flex', alignItems: 'center', flex: 1, marginLeft: '8px' }}>
              <span style={{ fontSize: '14px', color: '#333', userSelect: 'none' }}>
                {node.name}
              </span>
              {node.type && (
                <span
                  style={{
                    marginLeft: '8px',
                    padding: '2px 8px',
                    backgroundColor:
                      node.type === '主区域'
                        ? '#1890ff'
                        : node.type === '主部件'
                        ? '#52c41a'
                        : node.type === '一级子部件'
                        ? '#fa8c16'
                        : '#722ed1',
                    color: 'white',
                    borderRadius: '4px',
                    fontSize: '12px',
                  }}
                >
                  {node.type}
                </span>
              )}
            </div>

            {/* 操作按钮 - 只读模式下隐藏 */}
            {!readOnly && (
              <Space size="small">
                {canAddChild && (
                  <Button
                    type="text"
                    size="small"
                    icon={<PlusOutlined />}
                    onClick={() => onAdd(node.id, getNextType())}
                    style={{ opacity: 0.7 }}
                    title="添加子节点"
                  />
                )}
                <Button
                  type="text"
                  size="small"
                  icon={<EditOutlined />}
                  onClick={() => onEdit(node.id)}
                  style={{ opacity: 0.7 }}
                  title="编辑名称"
                />
                {/* 独立索引字段已移至页面级统一编辑，此处不再提供属性编辑按钮 */}
                <Button
                  type="text"
                  size="small"
                  icon={<DeleteOutlined />}
                  onClick={() => onDelete(node.id)}
                  danger
                  style={{ opacity: 0.7 }}
                  title="删除"
                />
              </Space>
            )}
          </>
        )}
      </div>

      {/* 子节点 */}
      {/* 非二级子部件展开时显示子节点容器，即使没有子节点也可以添加 */}
      {node.isExpanded && node.type !== '二级子部件' && (
        <div>
          {(node.children || []).map((child) => (
            <TreeNodeItem
              key={child.id}
              node={child}
              level={level + 1}
              onToggle={onToggle}
              onAdd={onAdd}
              onEdit={onEdit}
              onDelete={onDelete}
              onSave={onSave}
              onCancel={onCancel}
              onEditAttributes={onEditAttributes}
              readOnly={readOnly}
            />
          ))}
        </div>
      )}
    </div>
  )
}

interface IndexDataTreeEditorProps {
  initialData?: TreeNode[]
  onDataChange?: (data: TreeNode[]) => void
  readOnly?: boolean
}

const IndexDataTreeEditor: React.FC<IndexDataTreeEditorProps> = ({ 
  initialData = [],
  onDataChange,
  readOnly = false
}) => {
  const [treeData, setTreeData] = useState<TreeNode[]>(initialData)
  const [isAttributesModalVisible, setIsAttributesModalVisible] = useState(false)
  const [editingNodeId, setEditingNodeId] = useState<string | null>(null)
  const [attributesForm] = Form.useForm()

  // 当初始数据变化时更新
  useEffect(() => {
    setTreeData(initialData)
  }, [initialData])

  // 内部更新树数据并通知父组件
  const updateTreeData = (updated: TreeNode[]) => {
    setTreeData(updated)
    if (onDataChange) {
      onDataChange(updated)
    }
  }

  // 在树中更新节点
  const updateNodeInTree = (
    nodes: TreeNode[],
    id: string,
    updateFn: (node: TreeNode) => TreeNode
  ): TreeNode[] => {
    return nodes.map((node) => {
      if (node.id === id) {
        return updateFn(node)
      }
      if (node.children) {
        return {
          ...node,
          children: updateNodeInTree(node.children, id, updateFn),
        }
      }
      return node
    })
  }

  // 从树中删除节点
  const deleteNodeFromTree = (nodes: TreeNode[], id: string): TreeNode[] => {
    return nodes
      .filter((node) => node.id !== id)
      .map((node) => {
        if (node.children) {
          return {
            ...node,
            children: deleteNodeFromTree(node.children, id)
          }
        }
        return node
      })
  }

  // 添加节点到树
  const addNodeToTree = (nodes: TreeNode[], parentId: string, newNode: TreeNode): TreeNode[] => {
    return nodes.map((node) => {
      if (node.id === parentId) {
        return {
          ...node,
          isExpanded: true,
          children: [...(node.children || []), newNode],
        }
      }
      if (node.children) {
        return {
          ...node,
          children: addNodeToTree(node.children, parentId, newNode),
        }
      }
      return node
    })
  }

  // 处理展开/折叠
  const handleToggle = (id: string) => {
    const updated = updateNodeInTree(treeData, id, (node) => ({
      ...node,
      isExpanded: !node.isExpanded,
      // 展开时确保children数组存在
      children: node.children || [],
    }))
    updateTreeData(updated)
  }

  // 处理添加子节点
  const handleAdd = (parentId: string, type: TreeNode['type']) => {
    const newNode: TreeNode = {
      id: `${Date.now()}`,
      name: '新节点',
      type: type,
      isEditing: true,
      children: [],  // 明确初始化children数组
    }
    const updated = addNodeToTree(treeData, parentId, newNode)
    updateTreeData(updated)
  }

  // 处理编辑
  const handleEdit = (id: string) => {
    const updated = updateNodeInTree(treeData, id, (node) => ({
      ...node,
      isEditing: true,
    }))
    updateTreeData(updated)
  }

  // 处理删除
  const handleDelete = (id: string) => {
    const updated = deleteNodeFromTree(treeData, id)
    updateTreeData(updated)
  }

  // 处理保存
  const handleSave = (id: string, newName: string) => {
    const updated = updateNodeInTree(treeData, id, (node) => ({
      ...node,
      name: newName,
      isEditing: false,
    }))
    updateTreeData(updated)
  }

  // 处理取消
  const handleCancel = (id: string) => {
    const updated = updateNodeInTree(treeData, id, (node) => ({
      ...node,
      isEditing: false,
    }))
    updateTreeData(updated)
  }

  // 查找节点
  const findNode = (nodes: TreeNode[], id: string): TreeNode | null => {
    for (const node of nodes) {
      if (node.id === id) return node
      if (node.children) {
        const found = findNode(node.children, id)
        if (found) return found
      }
    }
    return null
  }

  // 处理属性编辑
  const handleEditAttributes = (id: string) => {
    const node = findNode(treeData, id)
    if (node) {
      setEditingNodeId(id)
      attributesForm.setFieldsValue({
        orientation: node.orientation || '',
        defectSubject: node.defectSubject || '',
        defectDescription: node.defectDescription || '',
        location: node.location || '',
        quantity: node.quantity || '',
      })
      setIsAttributesModalVisible(true)
    }
  }

  // 保存属性
  const handleSaveAttributes = () => {
    attributesForm.validateFields().then(values => {
      if (editingNodeId) {
        const updated = updateNodeInTree(treeData, editingNodeId, (node) => ({
          ...node,
          orientation: values.orientation || '',
          defectSubject: values.defectSubject || '',
          defectDescription: values.defectDescription || '',
          location: values.location || '',
          quantity: values.quantity || '',
        }))
        updateTreeData(updated)
        setIsAttributesModalVisible(false)
        setEditingNodeId(null)
      }
    })
  }

  // 处理添加根节点（主区域）
  const handleAddRoot = () => {
    const newNode: TreeNode = {
      id: `${Date.now()}`,
      name: '新主区域',
      type: '主区域',
      isEditing: true,
      children: [],  // 明确初始化children数组
    }
    const updated = [...treeData, newNode]
    updateTreeData(updated)
  }

  const editingNode = editingNodeId ? findNode(treeData, editingNodeId) : null

  return (
    <>
      <div style={{ background: 'white', borderRadius: '8px', padding: '16px' }}>
        {/* 添加主区域按钮 */}
        {!readOnly && (
          <div style={{ marginBottom: '16px' }}>
            <Button
              type="dashed"
              icon={<PlusOutlined />}
              onClick={handleAddRoot}
              size="large"
              block
            >
              添加主区域
            </Button>
          </div>
        )}
        
        {treeData.length === 0 ? (
          <Empty description="暂无数据，点击上方'添加主区域'按钮开始" />
        ) : (
          <div>
            {treeData.map((node) => (
              <TreeNodeItem
                key={node.id}
                node={node}
                level={0}
                onToggle={handleToggle}
                onAdd={handleAdd}
                onEdit={handleEdit}
                onDelete={handleDelete}
                onSave={handleSave}
                onCancel={handleCancel}
                onEditAttributes={handleEditAttributes}
                readOnly={readOnly}
              />
            ))}
          </div>
        )}
      </div>

      {/* 属性编辑模态框 */}
      <Modal
        title={`编辑对照索引数据：${editingNode?.name || ''}`}
        open={isAttributesModalVisible}
        onOk={handleSaveAttributes}
        onCancel={() => setIsAttributesModalVisible(false)}
        width={600}
      >
        <div style={{ marginBottom: '16px', padding: '12px', background: '#e6f7ff', borderRadius: '4px' }}>
          <Typography.Text type="secondary">
            这些字段用于定义对照索引数据标准，用于清洗缺陷清单数据。
          </Typography.Text>
        </div>
        <Form form={attributesForm} layout="vertical">
          <Form.Item
            name="orientation"
            label="方位"
          >
            <Input placeholder="例如：左侧" />
          </Form.Item>
          <Form.Item
            name="defectSubject"
            label="缺陷主体"
          >
            <Input placeholder="例如：裂纹" />
          </Form.Item>
          <Form.Item
            name="defectDescription"
            label="缺陷描述"
          >
            <Input.TextArea 
              placeholder="例如：出现裂纹" 
              rows={3}
            />
          </Form.Item>
          <Form.Item
            name="location"
            label="位置"
          >
            <Input placeholder="例如：发动机舱" />
          </Form.Item>
          <Form.Item
            name="quantity"
            label="数量"
          >
            <Input placeholder="例如：1" />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}

export default IndexDataTreeEditor
