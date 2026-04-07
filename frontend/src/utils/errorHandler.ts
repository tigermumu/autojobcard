import { message } from 'antd'

/**
 * 从错误对象中提取错误消息
 */
export function getErrorMessage(error: any): string {
  if (error?.response?.data?.detail) {
    return error.response.data.detail
  }
  if (error?.response?.data?.message) {
    return error.response.data.message
  }
  if (error?.message) {
    return error.message
  }
  if (typeof error === 'string') {
    return error
  }
  return '未知错误'
}

/**
 * 显示错误消息
 */
export function showError(error: any, defaultMessage: string = '操作失败'): void {
  const errorMsg = getErrorMessage(error)
  message.error(`${defaultMessage}: ${errorMsg}`)
}

/**
 * 静默处理错误（不显示消息，仅用于非关键操作）
 */
export function handleErrorSilently(error: any): void {
  // 静默处理，不影响主流程
  // 可以在这里添加日志记录
  console.error('Silent error:', error)
}

/**
 * 将 NR/000000324 格式转换为 50324 格式
 * 规则：去掉 NR/ 前缀和前5个字符(00000)，保留后4位数字，然后在前面加上 5
 * 例如：NR/000000324 → 0324 → 50324
 */
export function formatWorkcardNumberToShort(original: string | null | undefined): string {
  if (!original) return ''
  // 如果已经是短格式（以5开头且全是数字），直接返回
  if (/^5\d+$/.test(original)) return original
  // 如果不是 NR/ 格式，直接返回原值
  if (!original.startsWith('NR/')) return original
  // 去掉 NR/ 前缀，保留后4位数字
  const numPart = original.replace('NR/', '')
  const last4Digits = numPart.slice(-4).padStart(4, '0')
  return '5' + last4Digits
}

/**
 * 将 50324 格式转换回 NR/000000324 格式（用于API调用）
 * 规则：去掉开头的5，保留后4位，补齐前导零到9位，加上 NR/ 前缀
 * 例如：50324 → 0324 → NR/000000324
 */
export function formatWorkcardNumberToFull(shortFormat: string | null | undefined): string {
  if (!shortFormat) return ''
  // 如果已经是 NR/ 格式，直接返回
  if (shortFormat.startsWith('NR/')) return shortFormat
  // 如果不是以5开头，直接返回原值
  if (!shortFormat.startsWith('5')) return shortFormat
  // 去掉开头的5（后4位数字），补齐前导零到9位
  const numPart = shortFormat.substring(1) // 后4位，如 0324
  return 'NR/' + numPart.padStart(9, '0')
}
