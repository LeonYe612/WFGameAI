import axios from '@/utils/axios'

// 获取脚本列表
export const getScripts = (params) => {
  return axios.get('/api/v1/scripts/scripts/', { params })
    .then(response => response.data)
}

// 获取脚本详情
export const getScript = (id) => {
  return axios.get(`/api/v1/scripts/scripts/${id}/`)
    .then(response => response.data)
}

// 创建脚本
export const createScript = (data) => {
  return axios.post('/api/v1/scripts/scripts/', data)
    .then(response => response.data)
}

// 更新脚本
export const updateScript = (id, data) => {
  return axios.put(`/api/v1/scripts/scripts/${id}/`, data)
    .then(response => response.data)
}

// 删除脚本
export const deleteScript = (id) => {
  return axios.delete(`/api/v1/scripts/scripts/${id}/`)
    .then(response => response.data)
}

// 克隆脚本
export const cloneScript = (id) => {
  return axios.post(`/api/v1/scripts/scripts/${id}/clone/`)
    .then(response => response.data)
}

// 导出脚本
export const exportScript = (id) => {
  return axios.get(`/api/v1/scripts/scripts/${id}/export/`, {
    responseType: 'blob'
  }).then(response => {
    // 从Content-Disposition中提取文件名
    const contentDisposition = response.headers['content-disposition']
    let filename = 'script.json'
    
    if (contentDisposition) {
      const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/
      const matches = filenameRegex.exec(contentDisposition)
      if (matches != null && matches[1]) {
        filename = matches[1].replace(/['"]/g, '')
      }
    }
    
    // 创建Blob并下载
    const blob = new Blob([response.data], { type: 'application/json' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    
    return { success: true, filename }
  })
}

// 导入脚本
export const importScript = (file, category) => {
  const formData = new FormData()
  formData.append('file', file)
  if (category) {
    formData.append('category', category)
  }
  
  return axios.post('/api/v1/scripts/scripts/import/', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  }).then(response => response.data)
}

// 回滚脚本到指定版本
export const rollbackScript = (id, version) => {
  return axios.post(`/api/v1/scripts/scripts/${id}/rollback/${version}/`)
    .then(response => response.data)
}

// 获取脚本分类列表
export const getScriptCategories = () => {
  return axios.get('/api/v1/scripts/categories/')
    .then(response => response.data)
}

// 创建脚本分类
export const createScriptCategory = (data) => {
  return axios.post('/api/v1/scripts/categories/', data)
    .then(response => response.data)
}

// 更新脚本分类
export const updateScriptCategory = (id, data) => {
  return axios.put(`/api/v1/scripts/categories/${id}/`, data)
    .then(response => response.data)
}

// 删除脚本分类
export const deleteScriptCategory = (id) => {
  return axios.delete(`/api/v1/scripts/categories/${id}/`)
    .then(response => response.data)
}

// 获取指定分类下的脚本
export const getScriptsByCategory = (categoryId) => {
  return axios.get(`/api/v1/scripts/categories/${categoryId}/scripts/`)
    .then(response => response.data)
} 