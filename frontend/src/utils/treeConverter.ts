// 树形数据转换工具
import { IndexData } from '../services/indexDataApi'

export interface TreeNode {
  id: string
  name: string
  isExpanded: boolean
  isEditing?: boolean
  children?: TreeNode[]
  type?: '主区域' | '主部件' | '一级子部件' | '二级子部件'
  // 独立对照索引字段（仅二级子部件使用）
  orientation?: string
  defectSubject?: string
  defectDescription?: string
  location?: string
  quantity?: string
}

/**
 * 将扁平的索引数据转换为树形结构
 */
export function flatToTree(data: IndexData[]): TreeNode[] {
  const treeMap = new Map<string, TreeNode>()
  const result: TreeNode[] = []

  // 按层级顺序处理数据
  const sortedData = data.sort((a, b) => {
    // Helper function to safely compare strings (handle null/undefined)
    const safeCompare = (a: string | null | undefined, b: string | null | undefined): number => {
      const aStr = (a || '').toString()
      const bStr = (b || '').toString()
      return aStr.localeCompare(bStr)
    }
    
    return safeCompare(a.main_area, b.main_area) ||
           safeCompare(a.main_component, b.main_component) ||
           safeCompare(a.first_level_subcomponent, b.first_level_subcomponent) ||
           safeCompare(a.second_level_subcomponent, b.second_level_subcomponent)
  })

  for (const item of sortedData) {
    // 主区域
    const areaKey = `area_${item.main_area}`
    if (!treeMap.has(areaKey)) {
      const areaNode: TreeNode = {
        id: areaKey,
        name: item.main_area,
        type: '主区域',
        isExpanded: true,
        children: [],
      }
      treeMap.set(areaKey, areaNode)
      result.push(areaNode)
    }

    // 主部件
    const componentKey = `${areaKey}_component_${item.main_component}`
    let componentNode = treeMap.get(componentKey)
    if (!componentNode) {
      componentNode = {
        id: componentKey,
        name: item.main_component,
        type: '主部件',
        isExpanded: false,
        children: [],
      }
      treeMap.set(componentKey, componentNode)
      treeMap.get(areaKey)!.children!.push(componentNode)
    }

    // 一级子部件 - 只有当first_level_subcomponent不为空时才创建
    if (item.first_level_subcomponent && item.first_level_subcomponent.trim()) {
      const sub1Key = `${componentKey}_sub1_${item.first_level_subcomponent}`
      let sub1Node = treeMap.get(sub1Key)
      if (!sub1Node) {
        sub1Node = {
          id: sub1Key,
          name: item.first_level_subcomponent,
          type: '一级子部件',
          isExpanded: false,
          children: [],
        }
        treeMap.set(sub1Key, sub1Node)
        componentNode.children!.push(sub1Node)
      }

      // 二级子部件 - 只有当second_level_subcomponent不为空时才创建
      if (item.second_level_subcomponent && item.second_level_subcomponent.trim()) {
        const sub2Key = `${sub1Key}_sub2_${item.second_level_subcomponent}`
        const sub2Node: TreeNode = {
          id: sub2Key,
          name: item.second_level_subcomponent,
          type: '二级子部件',
          isExpanded: false,
          orientation: item.orientation || undefined,
          defectSubject: item.defect_subject || undefined,
          defectDescription: item.defect_description || undefined,
          location: item.location || undefined,
          quantity: item.quantity || undefined,
        }
        sub1Node.children!.push(sub2Node)
      }
    }
  }

  return result
}

/**
 * 将树形结构转换为扁平数据
 */
export function treeToFlat(
  tree: TreeNode[],
  configurationId: number
): IndexData[] {
  const result: IndexData[] = []

  function traverse(nodes: TreeNode[], pathData: {
    mainArea?: string,
    mainComponent?: string,
    firstLevel?: string
  }) {
    for (const node of nodes) {
      // 为每个分支创建新的路径数据副本
      let branchPathData = { ...pathData }
      
      // 根据节点类型更新路径数据
      if (node.type === '主区域') {
        branchPathData = {
          mainArea: node.name,
          mainComponent: undefined,
          firstLevel: undefined
        }
      } else if (node.type === '主部件') {
        branchPathData = {
          ...branchPathData,
          mainComponent: node.name,
          firstLevel: undefined
        }
        // 检查主部件是否没有子节点
        if (!node.children || node.children.length === 0) {
          // 主部件没有子节点，创建一条空记录
          result.push({
            id: 0, // 将由后端分配
            main_area: branchPathData.mainArea!,
            main_component: node.name,
            first_level_subcomponent: '',
            second_level_subcomponent: '',
            orientation: '',
            defect_subject: '',
            defect_description: '',
            location: '',
            quantity: '',
            configuration_id: configurationId,
            created_at: new Date().toISOString(),
          })
        }
      } else if (node.type === '一级子部件') {
        branchPathData = {
          ...branchPathData,
          firstLevel: node.name
        }
        // 检查一级子部件是否没有子节点
        if (!node.children || node.children.length === 0) {
          // 一级子部件没有子节点，创建一条记录
          result.push({
            id: 0, // 将由后端分配
            main_area: branchPathData.mainArea!,
            main_component: branchPathData.mainComponent!,
            first_level_subcomponent: node.name,
            second_level_subcomponent: '',
            orientation: '',
            defect_subject: '',
            defect_description: '',
            location: '',
            quantity: '',
            configuration_id: configurationId,
            created_at: new Date().toISOString(),
          })
        }
      } else if (node.type === '二级子部件') {
        // 二级子部件是一条完整的索引记录
        if (branchPathData.mainArea && branchPathData.mainComponent && branchPathData.firstLevel) {
          result.push({
            id: 0, // 将由后端分配
            main_area: branchPathData.mainArea,
            main_component: branchPathData.mainComponent,
            first_level_subcomponent: branchPathData.firstLevel,
            second_level_subcomponent: node.name,
            orientation: node.orientation || '',
            defect_subject: node.defectSubject || '',
            defect_description: node.defectDescription || '',
            location: node.location || '',
            quantity: node.quantity || '',
            configuration_id: configurationId,
            created_at: new Date().toISOString(),
          })
        }
      }

      // 递归处理子节点，使用当前分支的路径数据
      if (node.children) {
        traverse(node.children, branchPathData)
      }
    }
  }

  traverse(tree, {})
  return result
}

/**
 * 获取树节点的所有叶子节点（二级子部件）
 */
export function getLeafNodes(nodes: TreeNode[]): TreeNode[] {
  const result: TreeNode[] = []
  
  function traverse(nodes: TreeNode[]) {
    for (const node of nodes) {
      if (node.type === '二级子部件' && !node.children) {
        result.push(node)
      }
      if (node.children) {
        traverse(node.children)
      }
    }
  }
  
  traverse(nodes)
  return result
}

/**
 * 在树中更新节点
 */
export function updateNodeInTree(
  tree: TreeNode[],
  nodeId: string,
  updater: (node: TreeNode) => Partial<TreeNode>
): TreeNode[] {
  return tree.map(node => {
    if (node.id === nodeId) {
      return { ...node, ...updater(node) }
    }
    if (node.children) {
      return { ...node, children: updateNodeInTree(node.children, nodeId, updater) }
    }
    return node
  })
}

/**
 * 在树中删除节点
 */
export function deleteNodeFromTree(
  tree: TreeNode[],
  nodeId: string
): TreeNode[] {
  return tree
    .filter(node => {
      if (node.id === nodeId) {
        return false
      }
      if (node.children) {
        node.children = deleteNodeFromTree(node.children, nodeId)
      }
      return true
    })
}

