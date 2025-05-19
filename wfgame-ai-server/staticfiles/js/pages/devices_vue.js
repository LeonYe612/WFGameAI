// devices_vue.js
// 设备管理页面VUE3实现，动态加载设备列表、刷新、连接等

const { createApp, ref, onMounted } = Vue;

createApp({
    setup() {
        // 设备列表
        const devices = ref([]);
        // 加载状态
        const loading = ref(false);
        // 错误信息
        const error = ref('');
        // 刷新设备列表
        const loadDeviceList = () => {
            loading.value = true;
            error.value = '';
            fetch('/api/devices/?format=json', { credentials: 'include' })
                .then(res => {
                    if (!res.ok) throw new Error('网络错误');
                    return res.json();
                })
                .then(data => {
                    devices.value = data;
                })
                .catch(e => {
                    error.value = '加载设备失败: ' + e.message;
                })
                .finally(() => {
                    loading.value = false;
                });
        };
        // 连接设备
        const connectDevice = (deviceId) => {
            if (!confirm('确定要连接该设备吗？')) return;
            fetch(`/api/devices/${deviceId}/connect/`, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' }
            })
                .then(res => res.json())
                .then(data => {
                    alert(data.detail || '操作完成');
                    loadDeviceList();
                })
                .catch(e => alert('连接设备失败: ' + e.message));
        };
        // 页面加载自动刷新
        onMounted(loadDeviceList);

        return { devices, loading, error, loadDeviceList, connectDevice };
    },
    template: `
    <div>
        <div class="d-flex justify-content-between align-items-center mb-4">
            <div>
                <h2><i class="fas fa-mobile-alt"></i> 设备管理</h2>
                <p class="text-muted">管理和监控测试设备状态</p>
            </div>
            <div>
                <button class="btn btn-primary me-2" @click="loadDeviceList"><i class="fas fa-sync-alt"></i> 刷新设备</button>
                <button class="btn btn-success" disabled><i class="fas fa-plus"></i> 添加设备</button>
            </div>
        </div>
        <div v-if="loading" class="text-center py-3">
            <div class="spinner-border text-primary" role="status"></div>
            <p class="mt-2">正在加载设备列表...</p>
        </div>
        <div v-if="error" class="alert alert-danger">{{ error }}</div>
        <div v-if="!loading && devices.length === 0" class="alert alert-warning">暂无设备</div>
        <div class="row" v-if="!loading && devices.length > 0">
            <div class="col-md-4" v-for="device in devices" :key="device.id">
                <div class="card device-card mb-3">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h5 class="card-title">
                                <span class="device-status"
                                    :class="{
                                        'status-online': device.status === 'online',
                                        'status-offline': device.status === 'offline',
                                        'status-busy': device.status === 'busy'
                                    }"></span>
                                {{ device.name }}
                            </h5>
                            <span class="badge bg-primary">{{ device.type_name || '未知类型' }}</span>
                        </div>
                        <div class="card-text">
                            <p class="text-muted mb-1">设备ID: {{ device.device_id }}</p>
                            <p class="text-muted mb-1">IP地址: {{ device.ip_address || '-' }}</p>
                            <p class="text-muted mb-3">最后在线: {{ device.last_online || '-' }}</p>
                        </div>
                        <div class="d-flex">
                            <button class="btn btn-sm btn-outline-secondary me-2" @click="connectDevice(device.id)">
                                <i class="fas fa-mobile-alt"></i> 连接
                            </button>
                            <button class="btn btn-sm btn-outline-primary me-2" disabled>
                                <i class="fas fa-desktop"></i> 屏幕
                            </button>
                            <button class="btn btn-sm btn-outline-info" disabled>
                                <i class="fas fa-info-circle"></i> 详情
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    `
}).mount('#app'); 