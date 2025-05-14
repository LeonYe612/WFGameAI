import axios from '@/utils/axios'

// 登录
export const login = (credentials) => {
  return axios.post('/api/v1/users/login/', credentials)
    .then(response => response.data)
}

// 登出
export const logout = () => {
  return axios.post('/api/v1/users/logout/')
    .then(response => response.data)
}

// 获取当前用户信息
export const getUser = () => {
  return axios.get('/api/v1/users/me/')
    .then(response => response.data)
}

// 注册
export const register = (userData) => {
  return axios.post('/api/v1/users/register/', userData)
    .then(response => response.data)
}

// 重置密码
export const resetPassword = (email) => {
  return axios.post('/api/v1/users/reset-password/', { email })
    .then(response => response.data)
}

// 更新用户资料
export const updateProfile = (userData) => {
  return axios.patch('/api/v1/users/me/', userData)
    .then(response => response.data)
}

// 更改密码
export const changePassword = (passwords) => {
  return axios.post('/api/v1/users/change-password/', passwords)
    .then(response => response.data)
} 