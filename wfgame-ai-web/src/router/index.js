/**
 * 路由配置
 * @file src/router/index.js
 * @author WFGame AI Team
 * @date 2024-05-15
 */

import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

// 路由配置
const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/dashboard/Dashboard.vue'),
    meta: {
      title: '控制台',
      requiresAuth: true
    }
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/Login.vue'),
    meta: {
      title: '登录',
      requiresAuth: false
    }
  },
  {
    path: '/scripts',
    name: 'ScriptsList',
    component: () => import('@/views/scripts/ScriptsList.vue'),
    meta: {
      title: '脚本管理',
      requiresAuth: true
    }
  },
  {
    path: '/scripts/:id',
    name: 'ScriptDetail',
    component: () => import('@/views/scripts/ScriptDetail.vue'),
    meta: {
      title: '脚本详情',
      requiresAuth: true
    }
  },
  {
    path: '/scripts/:id/edit',
    name: 'ScriptEdit',
    component: () => import('@/views/scripts/ScriptDetail.vue'),
    meta: {
      title: '编辑脚本',
      requiresAuth: true,
      isEdit: true
    }
  },
  {
    path: '/devices',
    name: 'DevicesList',
    component: () => import('@/views/devices/DevicesList.vue'),
    meta: {
      title: '设备管理',
      requiresAuth: true
    }
  },
  {
    path: '/tasks',
    name: 'TasksList',
    component: () => import('@/views/tasks/TasksList.vue'),
    meta: {
      title: '任务管理',
      requiresAuth: true
    }
  },
  {
    path: '/reports',
    name: 'ReportsList',
    component: () => import('@/views/reports/ReportsList.vue'),
    meta: {
      title: '测试报告',
      requiresAuth: true
    }
  },
  {
    path: '/executions/:id',
    name: 'ExecutionDetail',
    component: () => import('@/views/executions/ExecutionDetail.vue'),
    meta: {
      title: '执行详情',
      requiresAuth: true
    }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/settings/Settings.vue'),
    meta: {
      title: '系统设置',
      requiresAuth: true
    }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue'),
    meta: {
      title: '页面未找到',
      requiresAuth: false
    }
  }
]

// 创建路由
const router = createRouter({
  history: createWebHistory(),
  routes
})

// 导航守卫
router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  
  // 设置页面标题
  if (to.meta.title) {
    document.title = `${to.meta.title} - WFGame AI自动化测试平台`
  } else {
    document.title = 'WFGame AI自动化测试平台'
  }
  
  // 权限验证
  if (to.meta.requiresAuth && !userStore.isLoggedIn) {
    // 如果需要登录但用户未登录，重定向到登录页面
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else {
    // 允许通过
    next()
  }
})

export default router 