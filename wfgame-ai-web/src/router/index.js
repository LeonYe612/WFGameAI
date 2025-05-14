import { createRouter, createWebHashHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

// 路由配置
const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/Login.vue'),
    meta: { title: '登录', requiresAuth: false }
  },
  {
    path: '/',
    redirect: '/dashboard',
    meta: { requiresAuth: true }
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/dashboard/Dashboard.vue'),
    meta: { title: '仪表盘', requiresAuth: true }
  },
  {
    path: '/scripts',
    name: 'Scripts',
    component: () => import('@/views/scripts/ScriptList.vue'),
    meta: { title: '脚本管理', requiresAuth: true }
  },
  {
    path: '/scripts/new',
    name: 'ScriptNew',
    component: () => import('@/views/scripts/ScriptEdit.vue'),
    meta: { title: '新建脚本', requiresAuth: true }
  },
  {
    path: '/scripts/:id',
    name: 'ScriptDetail',
    component: () => import('@/views/scripts/ScriptDetail.vue'),
    meta: { title: '脚本详情', requiresAuth: true }
  },
  {
    path: '/scripts/:id/edit',
    name: 'ScriptEdit',
    component: () => import('@/views/scripts/ScriptEdit.vue'),
    meta: { title: '编辑脚本', requiresAuth: true }
  },
  {
    path: '/tasks',
    name: 'Tasks',
    component: () => import('@/views/tasks/TaskList.vue'),
    meta: { title: '测试任务', requiresAuth: true }
  },
  {
    path: '/tasks/new',
    name: 'TaskNew',
    component: () => import('@/views/tasks/TaskEdit.vue'),
    meta: { title: '新建任务', requiresAuth: true }
  },
  {
    path: '/tasks/:id',
    name: 'TaskDetail',
    component: () => import('@/views/tasks/TaskDetail.vue'),
    meta: { title: '任务详情', requiresAuth: true }
  },
  {
    path: '/devices',
    name: 'Devices',
    component: () => import('@/views/devices/DeviceList.vue'),
    meta: { title: '设备管理', requiresAuth: true }
  },
  {
    path: '/devices/:id',
    name: 'DeviceDetail',
    component: () => import('@/views/devices/DeviceDetail.vue'),
    meta: { title: '设备详情', requiresAuth: true }
  },
  {
    path: '/reports',
    name: 'Reports',
    component: () => import('@/views/reports/ReportList.vue'),
    meta: { title: '报告中心', requiresAuth: true }
  },
  {
    path: '/reports/:id',
    name: 'ReportDetail',
    component: () => import('@/views/reports/ReportDetail.vue'),
    meta: { title: '报告详情', requiresAuth: true }
  },
  {
    path: '/data',
    name: 'Data',
    component: () => import('@/views/data/DataList.vue'),
    meta: { title: '数据驱动', requiresAuth: true }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/settings/Settings.vue'),
    meta: { title: '系统设置', requiresAuth: true }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('@/views/auth/Profile.vue'),
    meta: { title: '个人资料', requiresAuth: true }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue'),
    meta: { title: '页面不存在', requiresAuth: false }
  }
]

// 创建路由
const router = createRouter({
  history: createWebHashHistory(),
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