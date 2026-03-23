import axios from 'axios'
import type { TripFormData, TripPlanResponse, RagIngestResponse } from '@/types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 2分钟超时
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    console.log('发送请求:', config.method?.toUpperCase(), config.url)
    return config
  },
  (error) => {
    console.error('请求错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    console.log('收到响应:', response.status, response.config.url)
    return response
  },
  (error) => {
    console.error('响应错误:', error.response?.status, error.message)
    return Promise.reject(error)
  }
)

/**
 * 生成旅行计划
 */
export async function generateTripPlan(formData: TripFormData): Promise<TripPlanResponse> {
  try {
    const response = await apiClient.post<TripPlanResponse>('/api/trip/plan', formData)
    return response.data
  } catch (error: any) {
    console.error('生成旅行计划失败:', error)
    throw new Error(error.response?.data?.detail || error.message || '生成旅行计划失败')
  }
}

/**
 * 健康检查
 */
export async function healthCheck(): Promise<any> {
  try {
    const response = await apiClient.get('/health')
    return response.data
  } catch (error: any) {
    console.error('健康检查失败:', error)
    throw new Error(error.message || '健康检查失败')
  }
}

/**
 * 导入知识库文本
 */
export async function ingestRagText(title: string, text: string): Promise<RagIngestResponse> {
  try {
    const response = await apiClient.post<RagIngestResponse>('/api/rag/ingest/text', { title, text })
    return response.data
  } catch (error: any) {
    console.error('导入文本失败:', error)
    throw new Error(error.response?.data?.detail || error.message || '导入文本失败')
  }
}

/**
 * 导入知识库URL
 */
export async function ingestRagUrl(title: string, url: string): Promise<RagIngestResponse> {
  try {
    const response = await apiClient.post<RagIngestResponse>('/api/rag/ingest/url', { title, url })
    return response.data
  } catch (error: any) {
    console.error('导入URL失败:', error)
    throw new Error(error.response?.data?.detail || error.message || '导入URL失败')
  }
}

/**
 * 上传文件并导入知识库
 */
export async function ingestRagFile(file: File, title = ''): Promise<RagIngestResponse> {
  try {
    const form = new FormData()
    form.append('file', file)
    form.append('title', title)

    const response = await apiClient.post<RagIngestResponse>('/api/rag/ingest/file', form, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    return response.data
  } catch (error: any) {
    console.error('导入文件失败:', error)
    throw new Error(error.response?.data?.detail || error.message || '导入文件失败')
  }
}

export default apiClient

