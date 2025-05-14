<!--
  主应用组件
  @file src/App.vue
  @author WFGame AI Team
  @date 2024-05-15
-->
<template>
  <div id="app" :class="{'sidebar-collapsed': sidebarCollapsed}">
    <el-container v-if="isLoggedIn">
      <!-- 侧边栏 -->
      <el-aside :width="sidebarCollapsed ? '64px' : '240px'" class="sidebar">
        <div class="logo">
          <img src="@/assets/logo.png" alt="Logo" width="40" />
          <h1 v-show="!sidebarCollapsed">WFGame AI</h1>
        </div>
        
        <!-- 导航菜单 -->
        <el-menu
          :default-active="activeMenu"
          class="sidebar-menu"
          router
          background-color="#304156"
          text-color="#bfcbd9"
          active-text-color="#409EFF"
          :collapse="sidebarCollapsed"
        >
          <el-menu-item index="/">
            <i class="el-icon-s-home"></i>
            <span slot="title">控制台</span>
          </el-menu-item>
          
          <el-menu-item index="/devices">
            <i class="el-icon-mobile-phone"></i>
            <span slot="title">设备管理</span>
          </el-menu-item>
          
          <el-menu-item index="/scripts">
            <i class="el-icon-s-order"></i>
            <span slot="title">脚本管理</span>
          </el-menu-item>
          
          <el-menu-item index="/tasks">
            <i class="el-icon-s-operation"></i>
            <span slot="title">任务管理</span>
          </el-menu-item>
          
          <el-menu-item index="/reports">
            <i class="el-icon-s-data"></i>
            <span slot="title">测试报告</span>
          </el-menu-item>
          
          <el-menu-item index="/settings">
            <i class="el-icon-setting"></i>
            <span slot="title">系统设置</span>
          </el-menu-item>
        </el-menu>
      </el-aside>
      
      <!-- 主内容区域 -->
      <el-container class="main-container">
        <!-- 头部导航 -->
        <el-header height="60px" class="header">
          <div class="header-left">
            <i 
              :class="sidebarCollapsed ? 'el-icon-s-unfold' : 'el-icon-s-fold'"
              class="sidebar-toggle" 
              @click="toggleSidebar"
            ></i>
          </div>
          
          <div class="header-right">
            <el-dropdown @command="handleCommand">
              <span class="user-dropdown">
                {{ username }}
                <i class="el-icon-arrow-down"></i>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="profile">个人中心</el-dropdown-item>
                  <el-dropdown-item command="logout">退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </el-header>
        
        <!-- 内容区域 -->
        <el-main>
          <router-view v-slot="{ Component }">
            <keep-alive :include="cachedViews">
              <component :is="Component" :key="$route.fullPath" />
            </keep-alive>
          </router-view>
        </el-main>
      </el-container>
    </el-container>
    
    <!-- 登录页 -->
    <router-view v-if="!isLoggedIn" />
  </div>
</template>

<script>
export default {
  name: 'App',
  
  data() {
    return {
      isLoggedIn: true, // 临时设为true以便开发与调试
      username: '管理员',
      cachedViews: ['ScriptsList', 'DevicesList', 'TasksList'],
      sidebarCollapsed: false
    };
  },
  
  computed: {
    activeMenu() {
      // 获取当前路由路径
      return this.$route.path;
    }
  },
  
  created() {
    // 检查是否已登录
    const token = localStorage.getItem('token');
    
    // 开发模式下，可以暂时跳过登录检查
    if (process.env.NODE_ENV === 'development') {
      this.isLoggedIn = true;
    } else {
      this.isLoggedIn = !!token;
      
      // 如果未登录，且当前路由需要登录，则重定向到登录页
      if (!this.isLoggedIn && this.$route.meta.requiresAuth) {
        this.$router.push('/login');
      }
    }
  },
  
  methods: {
    // 处理下拉菜单命令
    handleCommand(command) {
      if (command === 'logout') {
        this.logout();
      } else if (command === 'profile') {
        this.$router.push('/profile');
      }
    },
    
    // 退出登录
    logout() {
      localStorage.removeItem('token');
      this.isLoggedIn = false;
      this.$router.push('/login');
    },
    
    // 切换侧边栏
    toggleSidebar() {
      this.sidebarCollapsed = !this.sidebarCollapsed;
      
      // 在DOM更新后执行
      this.$nextTick(() => {
        window.dispatchEvent(new Event('resize'));
      });
    }
  }
};
</script>

<style lang="scss">
html, body {
  margin: 0;
  padding: 0;
  height: 100%;
  font-family: "stheitimedium", "Microsoft YaHei", "微软雅黑", sans-serif;
}

#app {
  height: 100%;
}

.sidebar {
  background-color: #304156;
  color: #fff;
  height: 100vh;
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  z-index: 1001;
  transition: width 0.3s;
  overflow-y: auto;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  
  .logo {
    height: 60px;
    padding: 0 20px;
    display: flex;
    align-items: center;
    background-color: #2b3649;
    overflow: hidden;
    
    h1 {
      color: #fff;
      font-size: 18px;
      margin: 0 0 0 12px;
      font-weight: 600;
      white-space: nowrap;
    }
  }
  
  .sidebar-menu {
    border-right: none;
    
    &.el-menu--collapse {
      width: 64px;
    }
  }
}

.main-container {
  min-height: 100vh;
  background-color: #f0f2f5;
  position: relative;
  transition: margin-left 0.3s;
  margin-left: 240px;
}

.header {
  background-color: #fff;
  border-bottom: 1px solid #e6e6e6;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  position: sticky;
  top: 0;
  z-index: 1000;
  
  .header-left {
    display: flex;
    align-items: center;
    
    .sidebar-toggle {
      font-size: 20px;
      cursor: pointer;
      color: #606266;
      
      &:hover {
        color: #409EFF;
      }
    }
  }
  
  .header-right {
    display: flex;
    align-items: center;
    
    .user-dropdown {
      cursor: pointer;
      color: #606266;
      display: flex;
      align-items: center;
      gap: 5px;
      
      &:hover {
        color: #409EFF;
      }
    }
  }
}

// 当侧边栏折叠时
.sidebar-collapsed {
  .main-container {
    margin-left: 64px;
  }
}
</style> 