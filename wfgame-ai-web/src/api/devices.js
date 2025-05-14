/**
 * 设备管理相关API
 * @file src/api/devices.js
 * @author WFGame AI Team
 * @date 2024-05-15
 */

import axios from 'axios';

// API基础路径
const BASE_URL = '/api/v1/devices';

/**
 * 获取设备列表
 * @param {Object} params - 查询参数
 * @param {string} [params.status] - 设备状态 (online/offline/busy/error)
 * @param {string} [params.name] - 设备名称关键词
 * @returns {Promise} 返回请求Promise
 */
export function getDevices(params = {}) {
  return axios({
    url: `${BASE_URL}/`,
    method: 'get',
    params
  });
}

/**
 * 获取设备详情
 * @param {number} id - 设备ID
 * @returns {Promise} 返回请求Promise
 */
export function getDeviceDetail(id) {
  return axios({
    url: `${BASE_URL}/${id}/`,
    method: 'get'
  });
}

/**
 * 添加设备
 * @param {Object} data - 设备数据
 * @returns {Promise} 返回请求Promise
 */
export function addDevice(data) {
  return axios({
    url: `${BASE_URL}/`,
    method: 'post',
    data
  });
}

/**
 * 更新设备
 * @param {number} id - 设备ID
 * @param {Object} data - 更新数据
 * @returns {Promise} 返回请求Promise
 */
export function updateDevice(id, data) {
  return axios({
    url: `${BASE_URL}/${id}/`,
    method: 'put',
    data
  });
}

/**
 * 删除设备
 * @param {number} id - 设备ID
 * @returns {Promise} 返回请求Promise
 */
export function deleteDevice(id) {
  return axios({
    url: `${BASE_URL}/${id}/`,
    method: 'delete'
  });
}

/**
 * 连接设备
 * @param {number} id - 设备ID
 * @returns {Promise} 返回请求Promise
 */
export function connectDevice(id) {
  return axios({
    url: `${BASE_URL}/${id}/connect/`,
    method: 'post'
  });
}

/**
 * 断开设备连接
 * @param {number} id - 设备ID
 * @returns {Promise} 返回请求Promise
 */
export function disconnectDevice(id) {
  return axios({
    url: `${BASE_URL}/${id}/disconnect/`,
    method: 'post'
  });
}

/**
 * 重启设备
 * @param {number} id - 设备ID
 * @returns {Promise} 返回请求Promise
 */
export function restartDevice(id) {
  return axios({
    url: `${BASE_URL}/${id}/restart/`,
    method: 'post'
  });
}

/**
 * 获取设备截图
 * @param {number} id - 设备ID
 * @returns {Promise} 返回请求Promise
 */
export function getDeviceScreenshot(id) {
  return axios({
    url: `${BASE_URL}/${id}/screenshot/`,
    method: 'get',
    responseType: 'blob'
  });
}

/**
 * 扫描可用设备
 * @returns {Promise} 返回请求Promise
 */
export function scanDevices() {
  return axios({
    url: `${BASE_URL}/scan/`,
    method: 'post'
  });
}

/**
 * 获取设备日志
 * @param {number} id - 设备ID
 * @param {Object} params - 查询参数
 * @param {string} [params.level] - 日志级别
 * @param {string} [params.start_date] - 开始日期
 * @param {string} [params.end_date] - 结束日期
 * @returns {Promise} 返回请求Promise
 */
export function getDeviceLogs(id, params = {}) {
  return axios({
    url: `${BASE_URL}/${id}/logs/`,
    method: 'get',
    params
  });
} 