// API配置和服务工具类
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

export interface ApiResponse<T> {
  data: T
  message?: string
}

class ApiClient {
  private baseUrl: string

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`

    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    })

    if (!response.ok) {
      let errorDetail = response.statusText
      try {
        const errorData = await response.json()
        if (errorData.detail) {
          if (Array.isArray(errorData.detail)) {
            errorDetail = errorData.detail.map((err: any) =>
              (err && typeof err === 'object')
                ? `${Array.isArray(err.loc) ? err.loc.join('.') : 'unknown'}: ${err.msg || JSON.stringify(err)}`
                : JSON.stringify(err)
            ).join('; ')
          } else {
            errorDetail = errorData.detail
          }
        } else if (errorData.message) {
          errorDetail = errorData.message
        } else if (Array.isArray(errorData)) {
          // FastAPI验证错误格式 (Shouldn't happen with standard FastAPI but handled just in case)
          errorDetail = errorData.map((err: any) =>
            (err && typeof err === 'object')
              ? `${Array.isArray(err.loc) ? err.loc.join('.') : 'unknown'}: ${err.msg || JSON.stringify(err)}`
              : JSON.stringify(err)
          ).join('; ')
        } else {
          errorDetail = JSON.stringify(errorData)
        }
      } catch {
        // 如果响应不是JSON，使用状态文本
        errorDetail = response.statusText
      }
      const error = new Error(errorDetail || `HTTP error! status: ${response.status}`)
        // 附加响应信息以便调试
        ; (error as any).response = { status: response.status }
      throw error
    }

    return response.json()
  }

  // GET请求
  async get<T>(endpoint: string, params?: Record<string, any>): Promise<T> {
    let url = endpoint
    if (params) {
      const searchParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value !== null && value !== undefined && value !== '') {
          // 对于布尔值，转换为字符串'true'或'false'
          if (typeof value === 'boolean') {
            searchParams.append(key, String(value))
          } else {
            searchParams.append(key, String(value))
          }
        }
      })
      url = `${endpoint}?${searchParams.toString()}`
    }
    return this.request<T>(url, { method: 'GET' })
  }

  // POST请求
  async post<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  // PUT请求
  async put<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  // DELETE请求
  async delete<T>(endpoint: string, params?: Record<string, any>): Promise<T> {
    let url = endpoint
    if (params) {
      const searchParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value !== null && value !== undefined && value !== '') {
          searchParams.append(key, String(value))
        }
      })
      url = `${endpoint}?${searchParams.toString()}`
    }
    return this.request<T>(url, { method: 'DELETE' })
  }

  // 文件上传
  async upload<T>(
    endpoint: string,
    file: File,
    additionalData?: Record<string, any>
  ): Promise<T> {
    const formData = new FormData()
    formData.append('file', file)

    if (additionalData) {
      Object.entries(additionalData).forEach(([key, value]) => {
        formData.append(key, String(value))
      })
    }

    const url = `${this.baseUrl}${endpoint}`
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
      // 不设置 Content-Type，让浏览器自动设置（包含 boundary）
    })

    if (!response.ok) {
      let errorDetail = response.statusText
      try {
        const errorData = await response.json()
        if (errorData.detail) {
          errorDetail = errorData.detail
        } else if (errorData.message) {
          errorDetail = errorData.message
        } else if (Array.isArray(errorData)) {
          errorDetail = errorData.map((err: any) =>
            `${err.loc?.join('.')}: ${err.msg}`
          ).join('; ')
        } else {
          errorDetail = JSON.stringify(errorData)
        }
      } catch {
        // 如果响应不是JSON，使用状态文本
        errorDetail = response.statusText
      }
      const error = new Error(errorDetail || `HTTP error! status: ${response.status}`)
        ; (error as any).response = { status: response.status }
      throw error
    }

    return response.json()
  }

  // Server-Sent Events (SSE) 流式请求
  async stream<T = any>(
    endpoint: string,
    data: any,
    onMessage: (event: T) => void,
    onError?: (error: Error) => void,
    onComplete?: () => void
  ): Promise<void> {
    const url = `${this.baseUrl}${endpoint}`

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      })

      if (!response.ok) {
        const error = new Error(`HTTP error! status: ${response.status}`)
        if (onError) onError(error)
        return
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      if (!reader) {
        const error = new Error('Response body is not readable')
        if (onError) onError(error)
        return
      }

      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()

        if (done) {
          if (onComplete) onComplete()
          break
        }

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              onMessage(data as T)
            } catch (e) {
              console.error('Failed to parse SSE data:', e, line)
            }
          }
        }
      }
    } catch (error) {
      if (onError) {
        onError(error instanceof Error ? error : new Error(String(error)))
      }
    }
  }
}

export const apiClient = new ApiClient(API_BASE_URL)



