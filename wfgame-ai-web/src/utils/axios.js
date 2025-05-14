import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

// 创建axios实例
const instance = axios.create({
  baseURL: process.env.VUE_APP_API_URL || 'http://localhost:8000',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
instance.interceptors.request.use(
  config => {
    // 从localStorage获取token
    const token = localStorage.getItem('token')
    
    // 如果有token则带上
    if (token) {
      config.headers['Authorization'] = `Token ${token}`
    }
    
    return config
  },
  error => {
    console.error('请求错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
instance.interceptors.response.use(
  response => {
    return response
  },
  error => {
    if (error.response) {
      const { status, data } = error.response
      
      // 处理常见错误
      switch (status) {
        case 400:
          // 请求参数错误
          ElMessage.error(data.detail || '请求参数错误')
          break
          
        case 401:
          // 未授权，可能是token过期
          ElMessage.error('登录已失效，请重新登录')
          // 清除token
          localStorage.removeItem('token')
          // 跳转到登录页
          router.push('/login')
          break
          
        case 403:
          // 权限不足
          ElMessage.error('权限不足，无法执行此操作')
          break
          
        case 404:
          // 资源不存在
          ElMessage.error('请求的资源不存在')
          break
          
        case 500:
          // 服务器错误
          ElMessage.error('服务器错误，请稍后再试')
          break
          
        default:
          // 其他错误
          ElMessage.error(data.detail || '请求失败')
      }
    } else if (error.request) {
      // 请求发送但没有收到响应
      ElMessage.error('网络异常，无法连接服务器')
    } else {
      // 请求配置出错
      ElMessage.error('请求配置错误')
    }
    
    return Promise.reject(error)
  }
)

export default instance 