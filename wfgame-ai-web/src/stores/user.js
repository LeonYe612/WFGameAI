import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import router from '@/router'
import { login as apiLogin, logout as apiLogout, getUser } from '@/api/auth'

export const useUserStore = defineStore('user', () => {
  // 状态
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(null)
  const loading = ref(false)
  const error = ref(null)
  
  // 计算属性
  const isLoggedIn = computed(() => !!token.value)
  const username = computed(() => user.value?.username || '未登录')
  const role = computed(() => user.value?.role || '访客')
  
  // 方法
  const login = async (credentials) => {
    loading.value = true
    error.value = null
    
    try {
      const response = await apiLogin(credentials)
      token.value = response.token
      localStorage.setItem('token', response.token)
      
      // 获取用户信息
      await fetchUserInfo()
      
      // 重定向
      const redirectPath = router.currentRoute.value.query.redirect || '/dashboard'
      router.push(redirectPath)
      
      return true
    } catch (err) {
      error.value = err.message || '登录失败'
      return false
    } finally {
      loading.value = false
    }
  }
  
  const logout = async () => {
    loading.value = true
    
    try {
      // 调用登出API
      if (token.value) {
        await apiLogout()
      }
    } catch (err) {
      console.error('登出出错', err)
    } finally {
      // 清除本地状态
      token.value = ''
      user.value = null
      localStorage.removeItem('token')
      
      // 重定向到登录页
      router.push('/login')
      loading.value = false
    }
  }
  
  const fetchUserInfo = async () => {
    if (!token.value) return
    
    loading.value = true
    
    try {
      const userData = await getUser()
      user.value = userData
    } catch (err) {
      console.error('获取用户信息失败', err)
      // 如果获取用户信息失败，可能是token无效，执行登出
      await logout()
    } finally {
      loading.value = false
    }
  }
  
  // 初始化 - 如果有token则获取用户信息
  if (token.value) {
    fetchUserInfo()
  }
  
  return {
    // 状态
    token,
    user,
    loading,
    error,
    
    // 计算属性
    isLoggedIn,
    username,
    role,
    
    // 方法
    login,
    logout,
    fetchUserInfo
  }
}) 