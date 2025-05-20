// devices_vue.js
// 设备管理页面VUE3实现，动态加载设备列表、刷新、连接等

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
    const { createApp, ref, onMounted } = Vue;

    // 创建Vue应用
    const app = createApp({
        setup() {
            console.log('Vue组件setup函数执行');
            // 设备列表
            const devices = ref([]);
            // 加载状态
            const loading = ref(false);
            // 错误信息
            const error = ref('');
            
            // 刷新设备列表
            const loadDeviceList = () => {
                console.log('开始加载设备列表...');
                loading.value = true;
                error.value = '';
                
                // 显示加载状态
                console.log('发送POST请求到 /api/devices/scan/');
                
                fetch('/api/devices/scan/', {
                    method: 'POST',
                    credentials: 'include',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({}) // 空JSON对象作为请求体
                })
                    .then(res => {
                        console.log('收到响应:', res.status, res.statusText);
                        if (!res.ok) throw new Error(`网络错误: ${res.status} ${res.statusText}`);
                        return res.json();
                    })
                    .then(data => {
                        console.log('成功获取数据:', data);
                        if (data && data.devices_found) {
                            // 使用scan API返回的设备数据
                            devices.value = data.devices_found.map(dev => ({
                                id: dev.id,
                                name: dev.name,
                                device_id: dev.device_id,
                                status: dev.status,
                                last_online: new Date().toLocaleString(),
                                type_name: 'Android'
                            }));
                            console.log(`加载了 ${devices.value.length} 台设备`);
                        } else {
                            console.warn('服务器返回了空数据或格式不正确:', data);
                            devices.value = [];
                        }
                    })
                    .catch(e => {
                        console.error('加载设备列表失败:', e);
                        error.value = '加载设备失败: ' + e.message;
                    })
                    .finally(() => {
                        loading.value = false;
                        console.log('设备列表加载完成');
                    });
            };
            
            // 连接设备
            const connectDevice = (deviceId) => {
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
                
                console.log(`发送连接请求到 /api/devices/${deviceId}/connect/`);
                fetch(`/api/devices/${deviceId}/connect/`, {
                    method: 'POST',
                    credentials: 'include',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({}) // 空JSON对象作为请求体
                })
                    .then(res => {
                        console.log('连接请求响应:', res.status, res.statusText);
                        if (!res.ok) {
                            return res.json().then(errData => {
                                throw new Error(errData.detail || `状态码: ${res.status}`);
                            });
                        }
                        return res.json();
                    })
                    .then(data => {
                        console.log('连接请求结果:', data);
                        alert(data.detail || '操作完成');
                        loadDeviceList();
                    })
                    .catch(e => {
                        console.error('连接设备失败:', e);
                        alert('连接设备失败: ' + e.message);
                    });
            };
            
            // 手动绑定刷新按钮点击事件
            onMounted(() => {
                console.log('Vue组件已挂载，绑定事件...');
                
                // 绑定原生刷新按钮
                const refreshBtn = document.getElementById('refreshDeviceBtn');
                if (refreshBtn) {
                    console.log('找到刷新按钮，绑定点击事件');
                    refreshBtn.addEventListener('click', loadDeviceList);
                } else {
                    console.warn('未找到ID为refreshDeviceBtn的按钮');
                }
                
                // 自动加载设备列表
                console.log('自动加载设备列表...');
                loadDeviceList();
            });

            return { devices, loading, error, loadDeviceList, connectDevice };
        },
        template: `
        <div>
            <div v-if="loading" class="text-center py-3">
                <div class="spinner-border text-primary" role="status"></div>
                <p class="mt-2">正在加载设备列表...</p>
            </div>
            <div v-if="error" class="alert alert-danger">{{ error }}</div>
            <div v-if="!loading && devices.length === 0" class="alert alert-warning">暂无设备</div>
            <div class="row" v-if="!loading && devices.length > 0">
                <div class="col-md-4" v-for="device in devices" :key="device.id || device.serial">
                    <div class="card device-card mb-3">
                        <div class="card-body">
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <h5 class="card-title">
                                    <span class="device-status"
                                        :class="{
                                            'status-online': device.status === 'online' || device.status === 'device',
                                            'status-offline': device.status === 'offline',
                                            'status-busy': device.status === 'busy'
                                        }"></span>
                                    {{ device.name || (device.brand + ' ' + device.model) }}
                                </h5>
                                <span class="badge bg-primary">{{ device.type_name || (device.brand ? 'Android' : '未知类型') }}</span>
                            </div>
                            <div class="card-text">
                                <p class="text-muted mb-1">设备ID: {{ device.device_id || device.serial }}</p>
                                <p class="text-muted mb-1">IP地址: {{ device.ip_address || '-' }}</p>
                                <p class="text-muted mb-3">最后在线: {{ device.last_online || '刚刚' }}</p>
                            </div>
                            <div class="d-flex">
                                <button class="btn btn-sm btn-outline-secondary me-2" @click="connectDevice(device.id || device.serial)">
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