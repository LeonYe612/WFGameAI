/**
 * 脚本管理相关API
 * @file src/api/scripts.js
 * @author WFGame AI Team
 * @date 2024-05-15
 */

import axios from 'axios';

// 配置axios默认请求头，添加CSRF令牌支持
axios.defaults.xsrfCookieName = 'csrftoken';
axios.defaults.xsrfHeaderName = 'X-CSRFToken';
axios.defaults.withCredentials = true;

// API基础路径
const BASE_URL = '/api/v1/scripts';

/**
 * 获取脚本列表
 * @param {Object} params - 查询参数
 * @param {string} [params.name] - 脚本名称关键词
 * @param {string} [params.type] - 脚本类型 (record/manual/generated)
 * @param {number} [params.category] - 分类ID
 * @param {number} [params.page] - 页码
 * @param {number} [params.page_size] - 每页数量
 * @returns {Promise} 返回请求Promise
 */
export function getScripts(params = {}) {
  return axios({
    url: `${BASE_URL}/`,
    method: 'get',
    params
  });
}

/**
 * 获取脚本详情
 * @param {number} id - 脚本ID
 * @returns {Promise} 返回请求Promise
 */
export function getScriptDetail(id) {
  return axios({
    url: `${BASE_URL}/${id}/`,
    method: 'get'
  });
}

/**
 * 创建脚本
 * @param {Object} data - 脚本数据
 * @returns {Promise} 返回请求Promise
 */
export function createScript(data) {
  return axios({
    url: `${BASE_URL}/`,
    method: 'post',
    data
  });
}

/**
 * 更新脚本
 * @param {number} id - 脚本ID
 * @param {Object} data - 更新数据
 * @returns {Promise} 返回请求Promise
 */
export function updateScript(id, data) {
  return axios({
    url: `${BASE_URL}/${id}/`,
    method: 'put',
    data
  });
}

/**
 * 删除脚本
 * @param {number} id - 脚本ID
 * @returns {Promise} 返回请求Promise
 */
export function deleteScript(id) {
  return axios({
    url: `${BASE_URL}/${id}/`,
    method: 'delete'
  });
}

/**
 * 执行脚本
 * @param {number} id - 脚本ID
 * @param {Object} [data] - 执行参数
 * @param {number} [data.device] - 设备ID
 * @param {Object} [data.params] - 其他参数
 * @returns {Promise} 返回请求Promise
 */
export function executeScript(id, data = {}) {
  return axios({
    url: `${BASE_URL}/${id}/execute/`,
    method: 'post',
    data
  });
}

/**
 * 获取脚本执行记录
 * @param {number} id - 脚本ID
 * @param {Object} [params] - 查询参数
 * @returns {Promise} 返回请求Promise
 */
export function getScriptExecutions(id, params = {}) {
  return axios({
    url: `${BASE_URL}/${id}/executions/`,
    method: 'get',
    params
  });
}

/**
 * 切换脚本启用状态
 * @param {number} id - 脚本ID
 * @returns {Promise} 返回请求Promise
 */
export function toggleScriptActive(id) {
  return axios({
    url: `${BASE_URL}/${id}/toggle_active/`,
    method: 'post'
  });
}

/**
 * 获取脚本分类列表
 * @param {Object} [params] - 查询参数
 * @returns {Promise} 返回请求Promise
 */
export function getScriptCategories(params = {}) {
  return axios({
    url: '/api/v1/script-categories/',
    method: 'get',
    params
  });
}

/**
 * 录制脚本
 * @param {Object} data - 录制参数
 * @param {string} data.name - 脚本名称
 * @param {number} data.category - 分类ID
 * @param {number} data.device - 设备ID
 * @param {string} [data.description] - 脚本描述
 * @returns {Promise} 返回请求Promise
 */
export function recordScript(data) {
  return axios({
    url: `${BASE_URL}/record/`,
    method: 'post',
    data
  });
}

/**
 * 停止录制
 * @param {number} id - 录制ID
 * @returns {Promise} 返回请求Promise
 */
export function stopRecording(id) {
  return axios({
    url: `${BASE_URL}/record/${id}/stop/`,
    method: 'post'
  });
}

/**
 * 获取所有脚本执行记录
 * @param {Object} params - 查询参数
 * @param {number} [params.script] - 脚本ID
 * @param {string} [params.status] - 执行状态
 * @param {number} [params.executed_by] - 执行人ID
 * @param {string} [params.start_date] - 开始日期
 * @param {string} [params.end_date] - 结束日期
 * @returns {Promise} 返回请求Promise
 */
export function getScriptExecutionsList(params = {}) {
  return axios({
    url: `${BASE_URL}/executions/`,
    method: 'get',
    params
  });
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
  
  return axios.post('/api/v1/scripts/import/', formData, {
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

// 获取指定分类下的脚本
export const getScriptsByCategory = (categoryId) => {
  return axios.get(`/api/v1/scripts/categories/${categoryId}/scripts/`)
    .then(response => response.data)
} 