<template>
  <div class="login-container">
    <div class="login-form-container">
      <!-- Logo和标题 -->
      <div class="login-header">
        <img src="@/assets/logo.png" alt="WFGame AI" class="logo">
        <h1 class="title">WFGame AI自动化测试平台</h1>
      </div>
      
      <!-- 登录表单 -->
      <el-form
        ref="loginForm"
        :model="loginData"
        :rules="rules"
        label-position="top"
        class="login-form">
        
        <el-form-item prop="username" label="用户名">
          <el-input
            v-model="loginData.username"
            prefix-icon="User"
            placeholder="请输入用户名"
            @keyup.enter="submitForm"
          />
        </el-form-item>
        
        <el-form-item prop="password" label="密码">
          <el-input
            v-model="loginData.password"
            type="password"
            prefix-icon="Lock"
            show-password
            placeholder="请输入密码"
            @keyup.enter="submitForm"
          />
        </el-form-item>
        
        <div class="form-actions">
          <el-checkbox v-model="loginData.remember">记住我</el-checkbox>
          <el-button text type="primary" @click="forgotPassword">忘记密码?</el-button>
        </div>
        
        <el-form-item>
          <el-button
            type="primary"
            :loading="loading"
            @click="submitForm"
            class="submit-button">
            登录
          </el-button>
        </el-form-item>
      </el-form>
      
      <!-- 底部信息 -->
      <div class="login-footer">
        <p class="copyright">Copyright © 2025 WFGame AI自动化测试平台</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

// 路由
const router = useRouter()
const route = useRoute()

// 用户状态
const userStore = useUserStore()

// 加载状态
const loading = ref(false)

// 表单引用
const loginForm = ref(null)

// 登录数据
const loginData = reactive({
  username: '',
  password: '',
  remember: false
})

// 表单验证规则
const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度应为3-20个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少为6个字符', trigger: 'blur' }
  ]
}

// 提交表单
const submitForm = async () => {
  if (!loginForm.value) return
  
  await loginForm.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      
      try {
        // 调用登录方法
        const success = await userStore.login({
          username: loginData.username,
          password: loginData.password
        })
        
        if (success) {
          // 登录成功，跳转到之前的页面或者首页
          const redirectPath = route.query.redirect || '/dashboard'
          router.push(redirectPath)
          ElMessage.success('登录成功')
        } else {
          ElMessage.error(userStore.error || '登录失败')
        }
      } catch (error) {
        ElMessage.error('登录过程中发生错误')
        console.error('登录错误', error)
      } finally {
        loading.value = false
      }
    } else {
      ElMessage.warning('请正确填写登录信息')
      return false
    }
  })
}

// 忘记密码
const forgotPassword = () => {
  ElMessage.info('请联系系统管理员重置密码')
}
</script>

<style lang="scss" scoped>
.login-container {
  height: 100vh;
  width: 100vw;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #f5f7fa;
  background-image: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

.login-form-container {
  width: 400px;
  padding: 40px;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
}

.login-header {
  text-align: center;
  margin-bottom: 30px;
  
  .logo {
    width: 64px;
    height: 64px;
    margin-bottom: 16px;
  }
  
  .title {
    font-size: 24px;
    color: #303133;
    margin: 0;
  }
}

.login-form {
  .form-actions {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
  }
  
  .submit-button {
    width: 100%;
    padding: 12px 0;
    font-size: 16px;
  }
}

.login-footer {
  margin-top: 24px;
  text-align: center;
  
  .copyright {
    font-size: 12px;
    color: #909399;
  }
}
</style> 