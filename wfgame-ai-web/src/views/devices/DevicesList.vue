<!--
  设备管理页面 - 表格形式展示设备状态
  @file src/views/devices/DevicesList.vue
  @author WFGame AI Team
  @date 2024-05-15
-->
<template>
  <div class="devices-container">
    <!-- 页面标题和操作栏 -->
    <div class="page-header">
      <div class="header-left">
        <h2><i class="el-icon-mobile-phone"></i> 设备管理</h2>
        <p class="text-muted">管理和监控测试设备状态信息</p>
      </div>
      <div class="header-actions">
        <el-button type="primary" @click="refreshDevices" :loading="loading">
          <i class="el-icon-refresh"></i> 刷新设备
        </el-button>
        <el-button type="success" @click="openAddDeviceDialog">
          <i class="el-icon-plus"></i> 添加设备
        </el-button>
      </div>
    </div>

    <!-- 筛选栏 -->
    <el-card shadow="never" class="filter-card">
      <el-row :gutter="20">
        <el-col :span="6">
          <el-select v-model="statusFilter" placeholder="设备状态" clearable>
            <el-option label="全部状态" value=""></el-option>
            <el-option label="在线" value="online"></el-option>
            <el-option label="离线" value="offline"></el-option>
            <el-option label="忙碌" value="busy"></el-option>
            <el-option label="故障" value="error"></el-option>
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-select v-model="typeFilter" placeholder="设备类型" clearable>
            <el-option label="全部类型" value=""></el-option>
            <el-option label="Android" value="Android"></el-option>
            <el-option label="iOS" value="iOS"></el-option>
          </el-select>
        </el-col>
        <el-col :span="12">
          <el-input
            v-model="searchQuery"
            placeholder="搜索设备名称、型号或ID..."
            prefix-icon="el-icon-search"
            clearable
          ></el-input>
        </el-col>
      </el-row>
    </el-card>

    <!-- 设备列表表格 -->
    <el-card shadow="never" class="table-card">
      <el-table
        :data="filteredDevices"
        v-loading="loading"
        element-loading-text="正在加载设备列表..."
        style="width: 100%"
        :row-class-name="getRowClassName"
        @row-click="handleRowClick"
        stripe
      >
        <el-table-column label="状态" width="80" align="center">
          <template #default="scope">
            <el-tooltip :content="getStatusText(scope.row.status)">
              <div
                class="status-indicator"
                :class="getStatusClass(scope.row.status)"
              ></div>
            </el-tooltip>
          </template>
        </el-table-column>

        <el-table-column prop="name" label="设备名称" min-width="150">
          <template #default="scope">
            <div class="device-name">
              <strong>{{ scope.row.name }}</strong>
              <div class="device-id">{{ scope.row.device_id }}</div>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="model" label="设备型号" width="150">
          <template #default="scope">
            <div class="device-model">
              <div>{{ scope.row.brand || 'Unknown' }}</div>
              <div class="text-muted">{{ scope.row.model || 'Unknown' }}</div>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="android_version" label="系统版本" width="120">
          <template #default="scope">
            <el-tag size="small" type="info">
              {{ scope.row.android_version || 'Unknown' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="连接状态" width="120">
          <template #default="scope">
            <el-tag
              :type="getConnectionTagType(scope.row.connection_status)"
              size="small"
            >
              {{ getConnectionStatusText(scope.row.connection_status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="授权状态" width="120">
          <template #default="scope">
            <el-tag
              :type="getAuthTagType(scope.row.authorization_status)"
              size="small"
            >
              {{ getAuthStatusText(scope.row.authorization_status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="wifi_status" label="WiFi状态" width="120">
          <template #default="scope">
            <el-tag
              :type="scope.row.wifi_status === 'connected' ? 'success' : 'info'"
              size="small"
            >
              {{ scope.row.wifi_status === 'connected' ? '已连接' : '未连接' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="ip_address" label="IP地址" width="140">
          <template #default="scope">
            <span class="ip-address">
              {{ scope.row.ip_address || '-' }}
            </span>
          </template>
        </el-table-column>

        <el-table-column label="测试结果" width="120">
          <template #default="scope">
            <el-tooltip :content="scope.row.test_details || '无测试信息'">
              <el-tag
                :type="getTestResultTagType(scope.row.test_result)"
                size="small"
              >
                {{ getTestResultText(scope.row.test_result) }}
              </el-tag>
            </el-tooltip>
          </template>
        </el-table-column>

        <el-table-column label="整体状态" width="120">
          <template #default="scope">
            <el-tag
              :type="getOverallStatusTagType(scope.row.overall_status)"
              size="small"
            >
              {{ getOverallStatusText(scope.row.overall_status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="last_online" label="最后在线" width="160">
          <template #default="scope">
            <span class="last-online">
              {{ formatDate(scope.row.last_online) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="200" fixed="right">
          <template #default="scope">
            <el-button
              size="mini"
              type="primary"
              @click.stop="connectDevice(scope.row)"
              :disabled="scope.row.status === 'online'"
            >
              连接
            </el-button>
            <el-button
              size="mini"
              type="warning"
              @click.stop="disconnectDevice(scope.row)"
              :disabled="scope.row.status === 'offline'"
            >
              断开
            </el-button>
            <el-dropdown @command="handleDeviceAction" @click.stop>
              <el-button size="mini">
                更多<i class="el-icon-arrow-down el-icon--right"></i>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item :command="{action: 'restart', device: scope.row}">
                    重启设备
                  </el-dropdown-item>
                  <el-dropdown-item :command="{action: 'screenshot', device: scope.row}">
                    获取截图
                  </el-dropdown-item>
                  <el-dropdown-item :command="{action: 'detail', device: scope.row}">
                    查看详情
                  </el-dropdown-item>
                  <el-dropdown-item :command="{action: 'edit', device: scope.row}">
                    编辑设备
                  </el-dropdown-item>
                  <el-dropdown-item divided :command="{action: 'delete', device: scope.row}">
                    删除设备
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
          :current-page="pagination.currentPage"
          :page-sizes="[10, 20, 50, 100]"
          :page-size="pagination.pageSize"
          layout="total, sizes, prev, pager, next, jumper"
          :total="pagination.total"
        ></el-pagination>
      </div>
    </el-card>

    <!-- 设备详情对话框 -->
    <el-dialog
      title="设备详情"
      :visible.sync="detailDialogVisible"
      width="60%"
      destroy-on-close
    >
      <device-detail
        v-if="selectedDevice"
        :device="selectedDevice"
        @close="detailDialogVisible = false"
      ></device-detail>
    </el-dialog>

    <!-- 添加设备对话框 -->
    <el-dialog
      title="添加设备"
      :visible.sync="addDialogVisible"
      width="50%"
      destroy-on-close
    >
      <device-form
        @success="handleAddSuccess"
        @cancel="addDialogVisible = false"
      ></device-form>
    </el-dialog>
  </div>
</template>

<script>
import { connectDevice, deleteDevice, disconnectDevice, getDeviceScreenshot, restartDevice, scanDevices } from '@/api/devices'
import { formatDate } from '@/utils/date'
import DeviceDetail from './components/DeviceDetail.vue'
import DeviceForm from './components/DeviceForm.vue'

export default {
  name: 'DevicesList',
  components: {
    DeviceDetail,
    DeviceForm
  },
  data() {
    return {
      devices: [],
      loading: false,
      searchQuery: '',
      statusFilter: '',
      typeFilter: '',

      // 分页
      pagination: {
        currentPage: 1,
        pageSize: 20,
        total: 0
      },

      // 对话框
      detailDialogVisible: false,
      addDialogVisible: false,
      selectedDevice: null
    }
  },

  computed: {
    filteredDevices() {
      let filtered = this.devices.filter(device => {
        // 搜索过滤
        if (this.searchQuery) {
          const query = this.searchQuery.toLowerCase()
          const matchesName = device.name && device.name.toLowerCase().includes(query)
          const matchesModel = device.model && device.model.toLowerCase().includes(query)
          const matchesId = device.device_id && device.device_id.toLowerCase().includes(query)

          if (!matchesName && !matchesModel && !matchesId) {
            return false
          }
        }

        // 状态过滤
        if (this.statusFilter && device.status !== this.statusFilter) {
          return false
        }

        // 类型过滤
        if (this.typeFilter && device.type_name !== this.typeFilter) {
          return false
        }

        return true
      })

      this.pagination.total = filtered.length

      // 分页
      const start = (this.pagination.currentPage - 1) * this.pagination.pageSize
      const end = start + this.pagination.pageSize
      return filtered.slice(start, end)
    }
  },

  created() {
    this.fetchDevices()
  },

  methods: {
    // 格式化日期
    formatDate,

    // 获取设备列表（整合USB检查功能）
    async fetchDevices() {
      this.loading = true
      try {
        // 调用设备扫描API，整合USB检查功能
        const response = await scanDevices()

        if (response.data && response.data.devices_found) {
          // 处理扫描返回的设备数据，添加增强的设备状态信息
          this.devices = response.data.devices_found.map(device => ({
            ...device,
            // 确保所有必需字段都有默认值
            name: device.name || `${device.brand || 'Unknown'}-${device.model || 'Device'}`,
            brand: device.brand || '',
            model: device.model || '',
            android_version: device.android_version || '',
            connection_status: device.connection_status || 'unknown',
            authorization_status: device.authorization_status || 'unknown',
            wifi_status: device.wifi_status || 'unknown',
            ip_address: device.ip_address || '',
            test_result: device.test_result || 'unknown',
            test_details: device.test_details || '',
            overall_status: device.overall_status || 'unknown',
            last_online: device.last_online || new Date().toISOString()
          }))

          this.$message.success(`成功扫描到 ${this.devices.length} 台设备`)
        } else {
          this.devices = []
          this.$message.warning('未扫描到任何设备')
        }
      } catch (error) {
        console.error('获取设备列表失败:', error)
        this.$message.error('获取设备列表失败: ' + (error.message || '未知错误'))
        this.devices = []
      } finally {
        this.loading = false
      }
    },

    // 刷新设备列表（整合USB检查）
    async refreshDevices() {
      this.$message.info('正在刷新设备列表并执行USB连接检查...')
      await this.fetchDevices()
    },

    // 连接设备
    async connectDevice(device) {
      try {
        await connectDevice(device.id)
        this.$message.success(`设备 ${device.name} 连接成功`)
        this.fetchDevices()
      } catch (error) {
        this.$message.error(`连接设备失败: ${error.message}`)
      }
    },

    // 断开设备
    async disconnectDevice(device) {
      try {
        await this.$confirm(`确定要断开设备 "${device.name}" 的连接吗？`, '确认操作', {
          type: 'warning'
        })

        await disconnectDevice(device.id)
        this.$message.success(`设备 ${device.name} 已断开连接`)
        this.fetchDevices()
      } catch (error) {
        if (error !== 'cancel') {
          this.$message.error(`断开设备失败: ${error.message}`)
        }
      }
    },

    // 处理设备操作
    async handleDeviceAction(command) {
      const { action, device } = command

      switch (action) {
        case 'restart':
          await this.restartDevice(device)
          break
        case 'screenshot':
          await this.getDeviceScreenshot(device)
          break
        case 'detail':
          this.showDeviceDetail(device)
          break
        case 'edit':
          this.editDevice(device)
          break
        case 'delete':
          await this.deleteDevice(device)
          break
      }
    },

    // 重启设备
    async restartDevice(device) {
      try {
        await this.$confirm(`确定要重启设备 "${device.name}" 吗？`, '确认操作', {
          type: 'warning'
        })

        await restartDevice(device.id)
        this.$message.success(`设备 ${device.name} 重启成功`)
        this.fetchDevices()
      } catch (error) {
        if (error !== 'cancel') {
          this.$message.error(`重启设备失败: ${error.message}`)
        }
      }
    },

    // 获取设备截图
    async getDeviceScreenshot(device) {
      try {
        const response = await getDeviceScreenshot(device.id)
        // 创建blob URL并显示截图
        const blob = new Blob([response.data], { type: 'image/png' })
        const url = URL.createObjectURL(blob)

        // 打开新窗口显示截图
        const win = window.open('', '_blank')
        win.document.write(`
          <html>
            <head><title>设备截图 - ${device.name}</title></head>
            <body style="margin:0; display:flex; justify-content:center; align-items:center; min-height:100vh; background:#f0f0f0;">
              <img src="${url}" style="max-width:100%; max-height:100%; box-shadow:0 4px 8px rgba(0,0,0,0.1);" />
            </body>
          </html>
        `)

        this.$message.success('截图获取成功')
      } catch (error) {
        this.$message.error(`获取截图失败: ${error.message}`)
      }
    },

    // 显示设备详情
    showDeviceDetail(device) {
      this.selectedDevice = device
      this.detailDialogVisible = true
    },

    // 编辑设备
    editDevice(device) {
      this.$message.info('编辑设备功能待实现')
    },

    // 删除设备
    async deleteDevice(device) {
      try {
        await this.$confirm(`确定要删除设备 "${device.name}" 吗？此操作不可撤销。`, '确认删除', {
          type: 'warning'
        })

        await deleteDevice(device.id)
        this.$message.success(`设备 ${device.name} 已删除`)
        this.fetchDevices()
      } catch (error) {
        if (error !== 'cancel') {
          this.$message.error(`删除设备失败: ${error.message}`)
        }
      }
    },

    // 表格行点击
    handleRowClick(row) {
      this.showDeviceDetail(row)
    },

    // 获取行类名
    getRowClassName({ row }) {
      return `device-row device-${row.status}`
    },

    // 状态样式
    getStatusClass(status) {
      const statusMap = {
        'online': 'status-online',
        'offline': 'status-offline',
        'busy': 'status-busy',
        'error': 'status-error'
      }
      return statusMap[status] || 'status-unknown'
    },

    // 状态文本
    getStatusText(status) {
      const statusMap = {
        'online': '在线',
        'offline': '离线',
        'busy': '忙碌',
        'error': '故障'
      }
      return statusMap[status] || '未知'
    },

    // 连接状态标签类型
    getConnectionTagType(status) {
      const typeMap = {
        'connected': 'success',
        'disconnected': 'danger',
        'unauthorized': 'warning'
      }
      return typeMap[status] || 'info'
    },

    // 连接状态文本
    getConnectionStatusText(status) {
      const textMap = {
        'connected': '已连接',
        'disconnected': '已断开',
        'unauthorized': '未授权'
      }
      return textMap[status] || '未知'
    },

    // 授权状态标签类型
    getAuthTagType(status) {
      const typeMap = {
        'authorized': 'success',
        'unauthorized': 'danger',
        'pending': 'warning'
      }
      return typeMap[status] || 'info'
    },

    // 授权状态文本
    getAuthStatusText(status) {
      const textMap = {
        'authorized': '已授权',
        'unauthorized': '未授权',
        'pending': '待授权'
      }
      return textMap[status] || '未知'
    },

    // 测试结果标签类型
    getTestResultTagType(result) {
      const typeMap = {
        'passed': 'success',
        'failed': 'danger',
        'partial': 'warning'
      }
      return typeMap[result] || 'info'
    },

    // 测试结果文本
    getTestResultText(result) {
      const textMap = {
        'passed': '通过',
        'failed': '失败',
        'partial': '部分通过'
      }
      return textMap[result] || '未测试'
    },

    // 整体状态标签类型
    getOverallStatusTagType(status) {
      const typeMap = {
        'ready': 'success',
        'not_ready': 'danger',
        'warning': 'warning'
      }
      return typeMap[status] || 'info'
    },

    // 整体状态文本
    getOverallStatusText(status) {
      const textMap = {
        'ready': '就绪',
        'not_ready': '未就绪',
        'warning': '警告'
      }
      return textMap[status] || '未知'
    },

    // 分页
    handleSizeChange(size) {
      this.pagination.pageSize = size
      this.pagination.currentPage = 1
    },

    handleCurrentChange(page) {
      this.pagination.currentPage = page
    },

    // 打开添加设备对话框
    openAddDeviceDialog() {
      this.addDialogVisible = true
    },

    // 添加设备成功
    handleAddSuccess() {
      this.addDialogVisible = false
      this.fetchDevices()
    }
  }
}
</script>

<style scoped>
.devices-container {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

.header-left h2 {
  margin: 0 0 8px 0;
  color: #303133;
  font-size: 24px;
  font-weight: 600;
}

.header-left .text-muted {
  color: #909399;
  font-size: 14px;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.filter-card {
  margin-bottom: 20px;
}

.table-card {
  margin-bottom: 20px;
}

/* 状态指示器 */
.status-indicator {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  margin: 0 auto;
}

.status-online {
  background-color: #67C23A;
  box-shadow: 0 0 8px rgba(103, 194, 58, 0.4);
}

.status-offline {
  background-color: #F56C6C;
}

.status-busy {
  background-color: #E6A23C;
  animation: pulse 2s infinite;
}

.status-error {
  background-color: #F56C6C;
  animation: blink 1s infinite;
}

.status-unknown {
  background-color: #909399;
}

@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.5; }
  100% { opacity: 1; }
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0.3; }
}

/* 设备信息样式 */
.device-name strong {
  color: #303133;
  font-size: 14px;
}

.device-id {
  color: #909399;
  font-size: 12px;
  margin-top: 2px;
}

.device-model {
  font-size: 13px;
}

.device-model .text-muted {
  color: #909399;
  font-size: 12px;
}

.ip-address {
  font-family: 'Courier New', monospace;
  font-size: 12px;
}

.last-online {
  font-size: 12px;
  color: #909399;
}

/* 表格行样式 */
.device-row {
  cursor: pointer;
}

.device-row:hover {
  background-color: #f5f7fa;
}

.device-offline {
  background-color: #fef0f0;
}

.device-busy {
  background-color: #fdf6ec;
}

/* 分页容器 */
.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

/* 响应式布局 */
@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    gap: 16px;
  }

  .header-actions {
    width: 100%;
    justify-content: flex-start;
  }
}
</style>
