<template>
  <div class="app-container">
    <!-- 加载状态 -->
    <div class="loading-container" v-if="loading">
      <el-icon class="loading-icon" :size="48"><Loading /></el-icon>
      <div class="loading-text">加载中...</div>
    </div>
    
    <!-- 应用主体 -->
    <div class="app-layout" v-else>
      <!-- 侧边栏 -->
      <div class="sidebar">
        <!-- Logo -->
        <div class="logo">
          <router-link to="/">
            <img src="@/assets/logo.png" alt="WFGame AI" />
            <h1>WFGame AI</h1>
          </router-link>
        </div>
        
        <!-- 导航菜单 -->
        <el-menu
          :default-active="activeMenuItem"
          class="main-menu"
          router
          background-color="#001428"
          text-color="#e6e6e6"
          active-text-color="#409EFF">
          
          <el-menu-item index="/dashboard">
            <el-icon><Dashboard /></el-icon>
            <span>仪表盘</span>
          </el-menu-item>
          
          <el-menu-item index="/scripts">
            <el-icon><Document /></el-icon>
            <span>脚本管理</span>
          </el-menu-item>
          
          <el-menu-item index="/tasks">
            <el-icon><List /></el-icon>
            <span>测试任务</span>
          </el-menu-item>
          
          <el-menu-item index="/devices">
            <el-icon><Cellphone /></el-icon>
            <span>设备管理</span>
          </el-menu-item>
          
          <el-menu-item index="/reports">
            <el-icon><DocumentCopy /></el-icon>
            <span>报告中心</span>
          </el-menu-item>
          
          <el-menu-item index="/data">
            <el-icon><DataAnalysis /></el-icon>
            <span>数据驱动</span>
          </el-menu-item>
          
          <el-menu-item index="/settings">
            <el-icon><Setting /></el-icon>
            <span>系统设置</span>
          </el-menu-item>
        </el-menu>
        
        <!-- 用户信息 -->
        <div class="user-info">
          <el-avatar :size="36" src="https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png"></el-avatar>
          <div class="user-details">
            <div class="username">{{ userStore.username }}</div>
            <div class="role">{{ userStore.role }}</div>
          </div>
        </div>
      </div>
      
      <!-- 主内容区 -->
      <div class="main-content">
        <!-- 头部导航 -->
        <header class="header">
          <div class="breadcrumb">
            <el-breadcrumb separator="/">
              <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
              <el-breadcrumb-item v-for="(item, index) in breadcrumbItems" :key="index">{{ item }}</el-breadcrumb-item>
            </el-breadcrumb>
          </div>
          
          <div class="header-actions">
            <!-- 通知中心 -->
            <el-dropdown trigger="click" @command="handleNotificationCommand">
              <el-badge :value="unreadCount" :max="99" class="notification-badge">
                <el-button type="primary" plain circle>
                  <el-icon><Bell /></el-icon>
                </el-button>
              </el-badge>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item v-for="(notification, index) in notifications" :key="index" :command="notification.id">
                    {{ notification.title }}
                  </el-dropdown-item>
                  <el-dropdown-item divided command="viewAll">查看全部通知</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            
            <!-- 用户菜单 -->
            <el-dropdown trigger="click" @command="handleUserCommand">
              <el-button plain>
                {{ userStore.username }}
                <el-icon><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="profile">个人资料</el-dropdown-item>
                  <el-dropdown-item command="settings">系统设置</el-dropdown-item>
                  <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </header>
        
        <!-- 页面内容 -->
        <main class="page-container">
          <router-view v-slot="{ Component }">
            <transition name="fade" mode="out-in">
              <keep-alive>
                <component :is="Component" />
              </keep-alive>
            </transition>
          </router-view>
        </main>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { 
  Dashboard, Document, List, Cellphone, DocumentCopy, 
  DataAnalysis, Setting, Bell, Loading, ArrowDown 
} from '@element-plus/icons-vue'

// 加载状态
const loading = ref(true)

// 用户状态
const userStore = useUserStore()

// 路由
const route = useRoute()

// 活动菜单项
const activeMenuItem = computed(() => route.path)

// 面包屑导航
const breadcrumbItems = computed(() => {
  const items = []
  if (route.meta.title) items.push(route.meta.title)
  return items
})

// 通知
const notifications = ref([
  { id: 1, title: '测试任务完成', read: false },
  { id: 2, title: '设备状态变更', read: false },
  { id: 3, title: '系统更新提醒', read: true }
])
const unreadCount = computed(() => {
  return notifications.value.filter(item => !item.read).length
})

// 方法
const handleNotificationCommand = (command) => {
  if (command === 'viewAll') {
    // 查看全部通知
    console.log('查看全部通知')
  } else {
    // 查看特定通知
    const notification = notifications.value.find(item => item.id === command)
    if (notification) {
      notification.read = true
      console.log(`查看通知: ${notification.title}`)
    }
  }
}

const handleUserCommand = (command) => {
  switch (command) {
    case 'profile':
      console.log('查看个人资料')
      break
    case 'settings':
      console.log('系统设置')
      break
    case 'logout':
      userStore.logout()
      break
  }
}

// 生命周期
onMounted(() => {
  // 模拟加载过程
  setTimeout(() => {
    loading.value = false
  }, 1000)
})
</script>

<style lang="scss">
// 全局样式
body {
  margin: 0;
  padding: 0;
  font-family: 'stheitimedium', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #333;
  background-color: #f5f7fa;
}

// App容器
.app-container {
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}

// 加载状态
.loading-container {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 100%;
  
  .loading-icon {
    animation: rotate 1.5s linear infinite;
    color: #409EFF;
  }
  
  .loading-text {
    margin-top: 16px;
    font-size: 18px;
    color: #606266;
  }
}

@keyframes rotate {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

// 应用布局
.app-layout {
  display: flex;
  height: 100%;
}

// 侧边栏
.sidebar {
  width: 220px;
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: #001428;
  color: #fff;
  
  .logo {
    height: 60px;
    padding: 0 16px;
    display: flex;
    align-items: center;
    
    a {
      display: flex;
      align-items: center;
      text-decoration: none;
      color: #fff;
    }
    
    img {
      width: 32px;
      height: 32px;
      margin-right: 8px;
    }
    
    h1 {
      margin: 0;
      font-size: 18px;
      font-weight: 600;
    }
  }
  
  .main-menu {
    flex: 1;
    border-right: none;
  }
  
  .user-info {
    height: 64px;
    padding: 0 16px;
    display: flex;
    align-items: center;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    
    .user-details {
      margin-left: 12px;
      
      .username {
        font-size: 14px;
        color: #e6e6e6;
      }
      
      .role {
        font-size: 12px;
        color: #909399;
      }
    }
  }
}

// 主内容区
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  
  .header {
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 24px;
    background-color: #fff;
    box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
    
    .breadcrumb {
      
    }
    
    .header-actions {
      display: flex;
      align-items: center;
      
      .notification-badge {
        margin-right: 16px;
      }
    }
  }
  
  .page-container {
    flex: 1;
    padding: 24px;
    overflow: auto;
  }
}

// 页面过渡动画
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style> 