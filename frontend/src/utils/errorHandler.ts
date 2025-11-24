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
}













