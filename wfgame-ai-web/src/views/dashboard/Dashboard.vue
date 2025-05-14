<template>
  <div class="dashboard-container">
    <!-- 统计卡片 -->
    <div class="stat-cards">
      <el-row :gutter="20">
        <el-col :span="6" v-for="(stat, index) in stats" :key="index">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-icon" :class="stat.type">
              <el-icon :size="32"><component :is="stat.icon" /></el-icon>
            </div>
            <div class="stat-content">
              <h2 class="stat-value">{{ stat.value }}</h2>
              <p class="stat-label">{{ stat.label }}</p>
              <div class="stat-trend" :class="{'up': stat.trend > 0, 'down': stat.trend < 0}">
                <el-icon v-if="stat.trend > 0"><ArrowUp /></el-icon>
                <el-icon v-else-if="stat.trend < 0"><ArrowDown /></el-icon>
                <span>{{ stat.trend > 0 ? '+' : '' }}{{ stat.trend }}{{ stat.trendUnit || '' }}</span>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>
    
    <!-- 图表 -->
    <div class="charts-container">
      <el-row :gutter="20">
        <el-col :span="16">
          <el-card shadow="hover" class="chart-card">
            <template #header>
              <div class="card-header">
                <h3>测试执行趋势</h3>
                <div class="header-actions">
                  <el-select v-model="trendPeriod" placeholder="选择时段" size="small">
                    <el-option label="最近7天" value="7days"></el-option>
                    <el-option label="最近30天" value="30days"></el-option>
                    <el-option label="本月" value="thisMonth"></el-option>
                  </el-select>
                </div>
              </div>
            </template>
            <div class="chart-container" ref="trendChartRef"></div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="hover" class="chart-card">
            <template #header>
              <div class="card-header">
                <h3>设备状态</h3>
              </div>
            </template>
            <div class="chart-container" ref="deviceChartRef"></div>
          </el-card>
        </el-col>
      </el-row>
    </div>
    
    <!-- 最近执行的测试任务 -->
    <el-card shadow="hover" class="recent-tasks">
      <template #header>
        <div class="card-header">
          <h3>最近执行的测试</h3>
          <div class="header-actions">
            <el-button type="primary" size="small" @click="refreshRecentTasks">
              <el-icon><Refresh /></el-icon> 刷新
            </el-button>
            <el-button type="success" size="small" @click="$router.push('/tasks')">
              <el-icon><Plus /></el-icon> 新建任务
            </el-button>
          </div>
        </div>
      </template>
      <el-table :data="recentTasks" stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="80"></el-table-column>
        <el-table-column prop="name" label="任务名称"></el-table-column>
        <el-table-column prop="executedAt" label="执行时间" width="180"></el-table-column>
        <el-table-column prop="device" label="设备" width="180"></el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)" effect="light">
              {{ scope.row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="scope">
            <el-button type="primary" :icon="View" circle size="small" @click="viewTask(scope.row.id)"></el-button>
            <el-button type="success" :icon="VideoPlay" circle size="small" @click="replayTask(scope.row.id)"></el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts/core'
import { BarChart, LineChart, PieChart } from 'echarts/charts'
import {
  TitleComponent, TooltipComponent, GridComponent, LegendComponent
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import {
  Cellphone, Document, VideoPlay, View, List, Check,
  ArrowUp, ArrowDown, Refresh, Plus
} from '@element-plus/icons-vue'

// 注册echarts组件
echarts.use([
  TitleComponent, TooltipComponent, GridComponent, LegendComponent,
  BarChart, LineChart, PieChart, CanvasRenderer
])

// 路由
const router = useRouter()

// 统计数据
const stats = ref([
  {
    icon: 'Cellphone',
    label: '设备总数',
    value: 12,
    trend: 2,
    type: 'primary'
  },
  {
    icon: 'Document',
    label: '脚本总数',
    value: 156,
    trend: 15,
    type: 'success'
  },
  {
    icon: 'VideoPlay',
    label: '今日任务',
    value: 38,
    trend: 5,
    type: 'info'
  },
  {
    icon: 'Check',
    label: '成功率',
    value: '92.7%',
    trend: 0.5,
    trendUnit: '%',
    type: 'warning'
  }
])

// 图表引用
const trendChartRef = ref(null)
const deviceChartRef = ref(null)

// 趋势时段
const trendPeriod = ref('7days')

// 存储图表实例
let trendChart = null
let deviceChart = null

// 最近任务列表
const recentTasks = ref([
  {
    id: '1001',
    name: '登录场景测试',
    executedAt: '2025-05-12 15:48:46',
    device: 'OnePlus-KB2000',
    status: '通过'
  },
  {
    id: '1002',
    name: '引导流程验证',
    executedAt: '2025-05-12 14:30:21',
    device: 'OPPO-Find X3',
    status: '部分通过'
  },
  {
    id: '1003',
    name: '多脚本顺序执行',
    executedAt: '2025-05-12 13:15:09',
    device: 'Samsung-S21',
    status: '失败'
  }
])

// 获取状态对应的Tag类型
const getStatusType = (status) => {
  const map = {
    '通过': 'success',
    '部分通过': 'warning',
    '失败': 'danger',
    '运行中': 'info',
    '等待中': ''
  }
  return map[status] || 'info'
}

// 刷新最近任务列表
const refreshRecentTasks = () => {
  // TODO: 从API获取最新的任务列表
  console.log('刷新最近任务')
}

// 查看任务详情
const viewTask = (id) => {
  router.push(`/tasks/${id}`)
}

// 重新执行任务
const replayTask = (id) => {
  // TODO: 调用API重新执行任务
  console.log('重新执行任务', id)
}

// 初始化趋势图表
const initTrendChart = () => {
  if (!trendChartRef.value) return
  
  trendChart = echarts.init(trendChartRef.value)
  
  const option = {
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      data: ['执行数', '成功数', '失败数']
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: ['5/5', '5/6', '5/7', '5/8', '5/9', '5/10', '5/11', '5/12']
    },
    yAxis: {
      type: 'value'
    },
    series: [
      {
        name: '执行数',
        type: 'line',
        smooth: true,
        data: [35, 38, 42, 37, 45, 40, 43, 38],
        itemStyle: {
          color: '#409EFF'
        }
      },
      {
        name: '成功数',
        type: 'line',
        smooth: true,
        data: [30, 32, 37, 32, 40, 36, 39, 35],
        itemStyle: {
          color: '#67C23A'
        }
      },
      {
        name: '失败数',
        type: 'line',
        smooth: true,
        data: [5, 6, 5, 5, 5, 4, 4, 3],
        itemStyle: {
          color: '#F56C6C'
        }
      }
    ]
  }
  
  trendChart.setOption(option)
}

// 初始化设备状态图表
const initDeviceChart = () => {
  if (!deviceChartRef.value) return
  
  deviceChart = echarts.init(deviceChartRef.value)
  
  const option = {
    tooltip: {
      trigger: 'item',
      formatter: '{a} <br/>{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      right: 10,
      top: 'center',
      data: ['空闲', '执行中', '离线', '故障']
    },
    series: [
      {
        name: '设备状态',
        type: 'pie',
        radius: ['50%', '70%'],
        avoidLabelOverlap: false,
        label: {
          show: false,
          position: 'center'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: '18',
            fontWeight: 'bold'
          }
        },
        labelLine: {
          show: false
        },
        data: [
          { value: 7, name: '空闲', itemStyle: { color: '#4cc9f0' } },
          { value: 3, name: '执行中', itemStyle: { color: '#4361ee' } },
          { value: 1, name: '离线', itemStyle: { color: '#a5a5a5' } },
          { value: 1, name: '故障', itemStyle: { color: '#ff4d6d' } }
        ]
      }
    ]
  }
  
  deviceChart.setOption(option)
}

// 窗口大小变化时调整图表尺寸
const resizeCharts = () => {
  trendChart?.resize()
  deviceChart?.resize()
}

// 生命周期钩子
onMounted(() => {
  // 初始化图表
  initTrendChart()
  initDeviceChart()
  
  // 监听窗口大小变化
  window.addEventListener('resize', resizeCharts)
})

onUnmounted(() => {
  // 移除事件监听
  window.removeEventListener('resize', resizeCharts)
  
  // 销毁图表实例
  trendChart?.dispose()
  deviceChart?.dispose()
})
</script>

<style lang="scss" scoped>
.dashboard-container {
  .stat-cards {
    margin-bottom: 20px;
    
    .stat-card {
      display: flex;
      padding: 20px;
      
      .stat-icon {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 64px;
        height: 64px;
        border-radius: 8px;
        margin-right: 16px;
        
        &.primary {
          background-color: rgba(64, 158, 255, 0.1);
          color: #409EFF;
        }
        
        &.success {
          background-color: rgba(103, 194, 58, 0.1);
          color: #67C23A;
        }
        
        &.info {
          background-color: rgba(144, 147, 153, 0.1);
          color: #909399;
        }
        
        &.warning {
          background-color: rgba(230, 162, 60, 0.1);
          color: #E6A23C;
        }
        
        &.danger {
          background-color: rgba(245, 108, 108, 0.1);
          color: #F56C6C;
        }
      }
      
      .stat-content {
        flex: 1;
        
        .stat-value {
          font-size: 24px;
          font-weight: bold;
          margin: 0 0 4px 0;
          line-height: 1.2;
        }
        
        .stat-label {
          font-size: 14px;
          color: #606266;
          margin: 0 0 8px 0;
        }
        
        .stat-trend {
          display: flex;
          align-items: center;
          font-size: 12px;
          
          &.up {
            color: #67C23A;
          }
          
          &.down {
            color: #F56C6C;
          }
        }
      }
    }
  }
  
  .charts-container {
    margin-bottom: 20px;
    
    .chart-card {
      margin-bottom: 20px;
      
      .chart-container {
        height: 300px;
      }
    }
  }
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    h3 {
      margin: 0;
      font-size: 16px;
      font-weight: 600;
    }
    
    .header-actions {
      display: flex;
      gap: 8px;
    }
  }
  
  .recent-tasks {
    margin-bottom: 20px;
  }
}
</style> 