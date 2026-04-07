import React from 'react'
import { Alert, Card, Radio, Space, Tag, Typography } from 'antd'
import type { RadioChangeEvent } from 'antd'
import type { CleanMatchMode } from '../hooks/useCleanMatchMode'

const { Text } = Typography

type Props = {
  mode: CleanMatchMode
  onChange: (mode: CleanMatchMode) => void
}

const MODE_LABEL: Record<CleanMatchMode, string> = {
  ai: 'AI清洗与匹配（当前规则）',
  local: '本地清洗与匹配',
}

export const CleanMatchModeSidebar: React.FC<Props> = ({ mode, onChange }) => {
  const handleChange = (e: RadioChangeEvent) => {
    onChange(e.target.value as CleanMatchMode)
  }

  return (
    <Card title="清洗与匹配方式" size="small">
      <Space direction="vertical" style={{ width: '100%' }} size={12}>
        <div>
          <Text type="secondary">当前选择：</Text>
          <div style={{ marginTop: 8 }}>
            <Tag color={mode === 'ai' ? 'blue' : 'gold'}>{MODE_LABEL[mode]}</Tag>
          </div>
        </div>

        <Radio.Group onChange={handleChange} value={mode} style={{ width: '100%' }}>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Radio value="ai">{MODE_LABEL.ai}</Radio>
            <Radio value="local">{MODE_LABEL.local}</Radio>
          </Space>
        </Radio.Group>

        {mode === 'ai' ? (
          <Alert
            type="info"
            showIcon
            message="说明"
            description="将使用当前已有的清洗与匹配规则（AI流程保持不变）。"
          />
        ) : (
          <Alert
            type="info"
            showIcon
            message="说明"
            description="本地清洗与匹配已接入：请先在“本地词典管理(/keyword-manager)”导入词典版本，然后在页面选择构型并执行本地清洗/匹配。最终会回归到现有导入流程。"
          />
        )}
      </Space>
    </Card>
  )
}



