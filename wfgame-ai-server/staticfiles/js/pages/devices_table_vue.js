// devices_table_vue.js
// 设备管理页面VUE3实现 - 表格版本
// 具备USB检查、设备报告生成、表格排序筛选等功能

// 检查Vue是否正确加载
if (typeof Vue === 'undefined') {
    console.error('错误: Vue未定义，请检查Vue库是否正确加载!');
    alert('页面加载错误: Vue库未加载，请刷新页面或检查网络连接');
} else {
    console.log('Vue库已正确加载', Vue.version);
}

// 检查挂载点是否存在
document.addEventListener('DOMContentLoaded', function() {
    const appDiv = document.getElementById('app');
    if (!appDiv) {
        console.error('错误: 无法找到id为app的元素，Vue无法挂载!');
        alert('页面加载错误: 找不到Vue挂载点，请联系管理员');
    } else {
        console.log('找到Vue挂载点', appDiv);
        initVueApp();
    }
});

// 初始化Vue应用
function initVueApp() {
    console.log('正在初始化Vue应用...');
    const { createApp, ref, computed, onMounted } = Vue;

    // 创建Vue应用
    const app = createApp({
        setup() {
            console.log('Vue组件setup函数执行');

            // 响应式数据
            const devices = ref([]);
            const loading = ref(false);
            const error = ref('');
            const viewMode = ref('table'); // 'table' or 'card'
            const searchQuery = ref('');
            const statusFilter = ref('');
            const sortField = ref('name');
            const sortDirection = ref('asc');

            // USB检查相关
            const usbCheckLoading = ref(false);
            const usbCheckResult = ref(null);

            // 设备报告相关
            const deviceReportLoading = ref(false);
            const deviceReportData = ref(null);
            const selectedDevice = ref(null);

            // 统计数据
            const deviceStats = computed(() => {
                const total = devices.value.length;
                const online = devices.value.filter(d => d.status === 'online' || d.status === 'device').length;
                const offline = devices.value.filter(d => d.status === 'offline').length;
                const unauthorized = devices.value.filter(d => d.status === 'unauthorized').length;

                return { total, online, offline, unauthorized };
            });

            // 过滤和排序的设备列表
            const filteredAndSortedDevices = computed(() => {
                let result = devices.value;

                // 搜索过滤
                if (searchQuery.value) {
                    const query = searchQuery.value.toLowerCase();
                    result = result.filter(device =>
                        (device.name || '').toLowerCase().includes(query) ||
                        (device.device_id || '').toLowerCase().includes(query) ||
                        (device.ip_address || '').toLowerCase().includes(query)
                    );
                }

                // 状态过滤
                if (statusFilter.value) {
                    result = result.filter(device => device.status === statusFilter.value);
                }

                // 排序
                result = [...result].sort((a, b) => {
                    const aValue = a[sortField.value] || '';
                    const bValue = b[sortField.value] || '';

                    if (sortDirection.value === 'asc') {
                        return aValue.localeCompare(bValue);
                    } else {
                        return bValue.localeCompare(aValue);
                    }
                });

                return result;
            });

            // 获取设备状态显示文本
            const getStatusText = (status) => {
                const statusMap = {
                    'online': '在线',
                    'offline': '离线',
                    'device': '已连接',
                    'unauthorized': '未授权',
                    'busy': '忙碌'
                };
                return statusMap[status] || status;
            };

            // 获取状态样式类
            const getStatusClass = (status) => {
                const classMap = {
                    'online': 'success',
                    'device': 'success',
                    'offline': 'danger',
                    'unauthorized': 'warning',
                    'busy': 'info'
                };
                return classMap[status] || 'secondary';
            };

            // 刷新设备列表
            const loadDeviceList = async () => {
                console.log('开始加载设备列表和执行USB连接检查...');
                loading.value = true;
                error.value = '';

                try {
                    console.log('发送POST请求到 /api/devices/scan/');
                    const response = await fetch('/api/devices/scan/', {
                        method: 'POST',
                        credentials: 'include',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({})
                    });

                    if (!response.ok) {
                        throw new Error(`网络错误: ${response.status} ${response.statusText}`);
                    }

                    const data = await response.json();
                    console.log('成功获取数据:', data);

                    // 保存USB检查结果
                    if (data && data.usb_check_result) {
                        usbCheckResult.value = data.usb_check_result;
                        console.log('已保存USB检查结果:', usbCheckResult.value);
                    }

                    if (data && data.devices_found) {
                        devices.value = data.devices_found.map(dev => ({
                            id: dev.id,
                            name: dev.name,
                            device_id: dev.device_id,
                            status: dev.status,
                            last_online: new Date().toLocaleString(),
                            type_name: 'Android',
                            ip_address: dev.ip_address || '-',
                            connection_status: dev.connection_status || 'unknown',
                            authorization_status: dev.authorization_status || 'unknown',
                            usb_path: dev.usb_path || '-'
                        }));
                        console.log(`加载了 ${devices.value.length} 台设备`);
                    } else {
                        console.warn('服务器返回了空数据或格式不正确:', data);
                        devices.value = [];
                    }

                    // 如果UI中有USB检查结果模态框，自动显示摘要
                    setTimeout(() => {
                        if (usbCheckResult.value && usbCheckResult.value.summary) {
                            const summary = usbCheckResult.value.summary;
                            const message = `USB检查完成: 共发现${summary.total_devices}台设备，${summary.connected_devices}台已连接，${summary.authorized_devices}台已授权`;
                            showToast("USB检查摘要", message, "info");
                        }
                    }, 500);
                } catch (e) {
                    console.error('加载设备列表失败:', e);
                    error.value = '加载设备失败: ' + e.message;
                } finally {
                    loading.value = false;
                    console.log('设备列表和USB检查加载完成');
                }
            };

            // 连接设备
            const connectDevice = async (deviceId) => {
                console.log('尝试连接设备:', deviceId);
                if (!deviceId) {
                    console.error('设备ID为空，无法连接');
                    alert('无法连接：设备ID无效');
                    return;
                }

                if (!confirm('确定要连接该设备吗？')) {
                    console.log('用户取消了连接操作');
                    return;
                }

                try {
                    console.log(`发送连接请求到 /api/devices/${deviceId}/connect/`);
                    const response = await fetch(`/api/devices/${deviceId}/connect/`, {
                        method: 'POST',
                        credentials: 'include',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({})
                    });

                    const data = await response.json();
                    console.log('连接请求结果:', data);

                    if (!response.ok) {
                        throw new Error(data.detail || `状态码: ${response.status}`);
                    }

                    alert(data.detail || '操作完成');
                    await loadDeviceList(); // 重新加载设备列表
                } catch (e) {
                    console.error('连接设备失败:', e);
                    alert('连接设备失败: ' + e.message);
                }
            };

            // 执行USB连接检查
            const performUsbCheck = async () => {
                usbCheckLoading.value = true;
                try {
                    const response = await fetch('/api/devices/usb-check/', {
                        method: 'POST',
                        credentials: 'include',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({})
                    });

                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }

                    const data = await response.json();
                    usbCheckResult.value = data.usb_check_result;

                    showToast("USB检查完成",
                        `发现${data.usb_check_result?.summary?.total_devices || 0}台设备，${data.devices_updated || 0}台设备状态已更新`,
                        "success");

                    // 刷新设备列表显示最新状态
                    await loadDeviceList();
                } catch (e) {
                    console.error('USB检查失败:', e);
                    showToast("USB检查失败", e.message, "error");
                } finally {
                    usbCheckLoading.value = false;
                }
            };

            // 生成设备增强报告
            const generateDeviceReport = async (deviceId = null) => {
                deviceReportLoading.value = true;
                selectedDevice.value = deviceId ? devices.value.find(d => d.id === deviceId) : null;

                try {
                    const url = deviceId ?
                        `/api/devices/${deviceId}/enhanced-report/` :
                        '/api/devices/enhanced-report/';

                    const response = await fetch(url, {
                        method: 'POST',
                        credentials: 'include',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({})
                    });

                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }

                    const data = await response.json();
                    deviceReportData.value = data.data;

                    const message = deviceId ?
                        `设备 ${selectedDevice.value?.name} 的报告已生成` :
                        `已为${data.devices_updated || 0}台设备生成报告`;

                    showToast("设备报告生成完成", message, "success");

                    // 刷新设备列表
                    await loadDeviceList();
                } catch (e) {
                    console.error('生成设备报告失败:', e);
                    showToast("报告生成失败", e.message, "error");
                } finally {
                    deviceReportLoading.value = false;
                }
            };

            // 排序处理
            const sortBy = (field) => {
                if (sortField.value === field) {
                    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc';
                } else {
                    sortField.value = field;
                    sortDirection.value = 'asc';
                }
            };

            // 切换视图模式
            const toggleViewMode = () => {
                viewMode.value = viewMode.value === 'table' ? 'card' : 'table';
            };

            // 显示Toast通知
            const showToast = (title, message, type = 'info') => {
                // 创建一个简单的通知显示
                const toastHtml = `
                    <div class="alert alert-${type === 'info' ? 'info' : type === 'success' ? 'success' : 'warning'} alert-dismissible fade show position-fixed"
                         style="top: 20px; right: 20px; z-index: 9999; max-width: 350px;">
                        <strong>${title}:</strong> ${message}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                `;
                document.body.insertAdjacentHTML('beforeend', toastHtml);

                // 5秒后自动消失
                setTimeout(() => {
                    const alerts = document.querySelectorAll('.alert');
                    if (alerts.length > 0) {
                        alerts[alerts.length - 1].remove();
                    }
                }, 5000);
            };

            // 绑定事件监听器
            onMounted(() => {
                console.log('Vue组件已挂载，绑定事件...');

                // 绑定刷新按钮
                const refreshBtn = document.getElementById('refreshDeviceBtn');
                if (refreshBtn) {
                    console.log('找到刷新按钮，绑定点击事件');
                    refreshBtn.addEventListener('click', loadDeviceList);
                } else {
                    console.warn('未找到ID为refreshDeviceBtn的按钮');
                }

                // 绑定USB检查按钮
                const usbCheckBtn = document.getElementById('usbCheckBtn');
                if (usbCheckBtn) {
                    usbCheckBtn.addEventListener('click', () => {
                        const modal = new bootstrap.Modal(document.getElementById('usbCheckModal'));
                        modal.show();
                        runUsbCheck();
                    });
                }

                // 绑定重新检查按钮
                const runUsbCheckBtn = document.getElementById('runUsbCheckBtn');
                if (runUsbCheckBtn) {
                    runUsbCheckBtn.addEventListener('click', runUsbCheck);
                }

                // 自动加载设备列表
                console.log('自动加载设备列表...');
                loadDeviceList();
            });            return {
                // 数据
                devices,
                loading,
                error,
                viewMode,
                searchQuery,
                statusFilter,
                sortField,
                sortDirection,
                usbCheckLoading,
                usbCheckResult,
                deviceReportLoading,
                deviceReportData,
                selectedDevice,

                // 计算属性
                deviceStats,
                filteredAndSortedDevices,

                // 方法
                loadDeviceList,
                connectDevice,
                performUsbCheck,
                generateDeviceReport,
                sortBy,
                toggleViewMode,
                getStatusText,
                getStatusClass,
                showToast
            };
        },
        template: `
        <div>
            <!-- 统计卡片 -->
            <div class="row mb-4" v-if="!loading">
                <div class="col-md-3">
                    <div class="card text-center bg-primary text-white">
                        <div class="card-body">
                            <h5 class="card-title">{{ deviceStats.total }}</h5>
                            <p class="card-text">总设备数</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center bg-success text-white">
                        <div class="card-body">
                            <h5 class="card-title">{{ deviceStats.online }}</h5>
                            <p class="card-text">在线设备</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center bg-danger text-white">
                        <div class="card-body">
                            <h5 class="card-title">{{ deviceStats.offline }}</h5>
                            <p class="card-text">离线设备</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center bg-warning text-white">
                        <div class="card-body">
                            <h5 class="card-title">{{ deviceStats.unauthorized }}</h5>
                            <p class="card-text">未授权设备</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 搜索和筛选 -->
            <div class="row mb-3" v-if="!loading">
                <div class="col-md-4">
                    <input type="text" class="form-control" placeholder="搜索设备..." v-model="searchQuery">
                </div>
                <div class="col-md-3">
                    <select class="form-select" v-model="statusFilter">
                        <option value="">所有状态</option>
                        <option value="online">在线</option>
                        <option value="device">已连接</option>
                        <option value="offline">离线</option>
                        <option value="unauthorized">未授权</option>
                    </select>
                </div>
                <div class="col-md-3">
                    <button class="btn btn-outline-secondary" @click="toggleViewMode">
                        <i :class="viewMode === 'table' ? 'fas fa-th' : 'fas fa-table'"></i>
                        {{ viewMode === 'table' ? '卡片视图' : '表格视图' }}
                    </button>
                </div>
                <div class="col-md-2">
                    <button class="btn btn-primary" @click="loadDeviceList">
                        <i class="fas fa-sync"></i> 刷新
                    </button>
                </div>
            </div>

            <!-- 加载状态 -->
            <div v-if="loading" class="text-center py-5">
                <div class="spinner-border text-primary" role="status"></div>
                <p class="mt-2">正在加载设备列表...</p>
            </div>

            <!-- 错误信息 -->
            <div v-if="error" class="alert alert-danger">{{ error }}</div>

            <!-- 无设备提示 -->
            <div v-if="!loading && devices.length === 0" class="alert alert-warning">
                暂无设备，请检查设备连接状态
            </div>

            <!-- 表格视图 -->
            <div v-if="!loading && devices.length > 0 && viewMode === 'table'" class="card">
                <div class="table-responsive">
                    <table class="table table-hover mb-0">
                        <thead class="table-dark">
                            <tr>
                                <th @click="sortBy('name')" style="cursor: pointer;">
                                    设备名称
                                    <i v-if="sortField === 'name'" :class="sortDirection === 'asc' ? 'fas fa-sort-up' : 'fas fa-sort-down'"></i>
                                </th>
                                <th @click="sortBy('device_id')" style="cursor: pointer;">
                                    设备ID
                                    <i v-if="sortField === 'device_id'" :class="sortDirection === 'asc' ? 'fas fa-sort-up' : 'fas fa-sort-down'"></i>
                                </th>
                                <th @click="sortBy('status')" style="cursor: pointer;">
                                    状态
                                    <i v-if="sortField === 'status'" :class="sortDirection === 'asc' ? 'fas fa-sort-up' : 'fas fa-sort-down'"></i>
                                </th>
                                <th>IP地址</th>
                                <th>类型</th>
                                <th>最后在线</th>
                                <th>操作</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="device in filteredAndSortedDevices" :key="device.id || device.device_id">
                                <td>
                                    <span class="device-status"
                                        :class="{
                                            'status-online': device.status === 'online' || device.status === 'device',
                                            'status-offline': device.status === 'offline',
                                            'status-busy': device.status === 'busy',
                                            'status-unauthorized': device.status === 'unauthorized'
                                        }"></span>
                                    {{ device.name }}
                                </td>
                                <td><code>{{ device.device_id }}</code></td>
                                <td>
                                    <span class="badge" :class="'bg-' + getStatusClass(device.status)">
                                        {{ getStatusText(device.status) }}
                                    </span>
                                </td>
                                <td>{{ device.ip_address || '-' }}</td>
                                <td>{{ device.type_name || 'Android' }}</td>
                                <td>{{ device.last_online || '刚刚' }}</td>
                                <td>
                                    <div class="btn-group btn-group-sm">
                                        <button class="btn btn-outline-success"
                                            @click="connectDevice(device.id || device.device_id)"
                                            :disabled="device.status === 'online' || device.status === 'device'">
                                            <i class="fas fa-link"></i> 连接
                                        </button>
                                        <button class="btn btn-outline-info"
                                            @click="generateDeviceReport(device)">
                                            <i class="fas fa-chart-bar"></i> 报告
                                        </button>
                                        <button class="btn btn-outline-primary" disabled>
                                            <i class="fas fa-desktop"></i> 屏幕
                                        </button>
                                    </div>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- 卡片视图 -->
            <div v-if="!loading && devices.length > 0 && viewMode === 'card'" class="row">
                <div class="col-md-4" v-for="device in filteredAndSortedDevices" :key="device.id || device.device_id">
                    <div class="card device-card mb-3">
                        <div class="card-body">
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <h5 class="card-title">
                                    <span class="device-status"
                                        :class="{
                                            'status-online': device.status === 'online' || device.status === 'device',
                                            'status-offline': device.status === 'offline',
                                            'status-busy': device.status === 'busy',
                                            'status-unauthorized': device.status === 'unauthorized'
                                        }"></span>
                                    {{ device.name }}
                                </h5>
                                <span class="badge" :class="'bg-' + getStatusClass(device.status)">
                                    {{ getStatusText(device.status) }}
                                </span>
                            </div>
                            <div class="card-text">
                                <p class="text-muted mb-1">设备ID: <code>{{ device.device_id }}</code></p>
                                <p class="text-muted mb-1">IP地址: {{ device.ip_address || '-' }}</p>
                                <p class="text-muted mb-3">最后在线: {{ device.last_online || '刚刚' }}</p>
                            </div>
                            <div class="d-flex gap-2">
                                <button class="btn btn-sm btn-outline-success"
                                    @click="connectDevice(device.id || device.device_id)"
                                    :disabled="device.status === 'online' || device.status === 'device'">
                                    <i class="fas fa-link"></i> 连接
                                </button>
                                <button class="btn btn-sm btn-outline-info"
                                    @click="generateDeviceReport(device)">
                                    <i class="fas fa-chart-bar"></i> 报告
                                </button>
                                <button class="btn btn-sm btn-outline-primary" disabled>
                                    <i class="fas fa-desktop"></i> 屏幕
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        `
    });

    // 挂载应用
    try {
        console.log('尝试挂载Vue应用到 #app');
        app.mount('#app');
        console.log('Vue应用挂载成功!');
    } catch (e) {
        console.error('Vue应用挂载失败:', e);
        alert('Vue应用挂载失败: ' + e.message);
    }
}

// 全局函数，供模态框使用
window.showUsbCheckModal = function() {
    const modal = new bootstrap.Modal(document.getElementById('usbCheckModal'));
    modal.show();
    // Vue实例会处理USB检查
};

window.showDeviceReportModal = function(deviceId) {
    const modal = new bootstrap.Modal(document.getElementById('deviceReportModal'));
    modal.show();
    // Vue实例会处理设备报告生成
};
