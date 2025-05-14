// 设备管理组件
const DeviceManagement = {
    template: `
        <div>
            <div class="row mb-3">
                <div class="col">
                    <div class="card">
                        <div class="card-header d-flex justify-content-between align-items-center">
                            <h5 class="card-title mb-0">设备列表</h5>
                            <div class="action-buttons">
                                <button class="btn btn-primary btn-sm" @click="showAddDeviceModal">
                                    <i class="fa fa-plus"></i> 添加设备
                                </button>
                                <button class="btn btn-outline-secondary btn-sm ms-2" @click="refreshDevices">
                                    <i class="fa fa-sync"></i> 刷新
                                </button>
                            </div>
                        </div>
                        <div class="card-body">
                            <div class="device-filters d-flex mb-3">
                                <div class="me-3">
                                    <select class="form-select form-select-sm" v-model="statusFilter">
                                        <option value="">所有状态</option>
                                        <option value="online">在线</option>
                                        <option value="offline">离线</option>
                                        <option value="executing">执行中</option>
                                    </select>
                                </div>
                                <div class="me-3">
                                    <select class="form-select form-select-sm" v-model="modelFilter">
                                        <option value="">所有型号</option>
                                        <option value="OnePlus">OnePlus</option>
                                        <option value="OPPO">OPPO</option>
                                        <option value="Samsung">Samsung</option>
                                        <option value="Xiaomi">Xiaomi</option>
                                    </select>
                                </div>
                                <div class="ms-auto">
                                    <div class="input-group input-group-sm">
                                        <input type="text" class="form-control" placeholder="搜索设备..." v-model="searchQuery">
                                        <button class="btn btn-outline-secondary" type="button">
                                            <i class="fa fa-search"></i>
                                        </button>
                                    </div>
                                </div>
                            </div>

                            <div class="device-grid">
                                <div class="row">
                                    <div class="col-lg-4 col-md-6 mb-3" v-for="device in filteredDevices" :key="device.id">
                                        <div class="device-card" :class="{'device-offline': device.status === 'offline', 'device-executing': device.status === 'executing'}">
                                            <div class="device-status-indicator" :class="getStatusIndicatorClass(device.status)"></div>
                                            <div class="device-header d-flex justify-content-between">
                                                <h6 class="device-name mb-0">{{ device.name }}</h6>
                                                <div class="device-actions">
                                                    <button class="action-btn" title="查看详情" @click="viewDeviceDetail(device)">
                                                        <i class="fa fa-eye"></i>
                                                    </button>
                                                    <button class="action-btn" title="编辑" @click="editDevice(device)">
                                                        <i class="fa fa-edit"></i>
                                                    </button>
                                                    <button class="action-btn" title="重启" @click="restartDevice(device)">
                                                        <i class="fa fa-redo"></i>
                                                    </button>
                                                </div>
                                            </div>
                                            <div class="device-body">
                                                <div class="device-info">
                                                    <div class="info-item">
                                                        <span class="info-label">型号:</span>
                                                        <span class="info-value">{{ device.model }}</span>
                                                    </div>
                                                    <div class="info-item">
                                                        <span class="info-label">分辨率:</span>
                                                        <span class="info-value">{{ device.resolution }}</span>
                                                    </div>
                                                    <div class="info-item">
                                                        <span class="info-label">状态:</span>
                                                        <span class="info-value">{{ getStatusText(device.status) }}</span>
                                                    </div>
                                                    <div class="info-item">
                                                        <span class="info-label">上次活动:</span>
                                                        <span class="info-value">{{ device.lastActivity }}</span>
                                                    </div>
                                                </div>
                                            </div>
                                            <div class="device-footer d-flex justify-content-between">
                                                <button class="btn btn-sm btn-outline-primary" @click="connectDevice(device)" :disabled="device.status !== 'offline'">
                                                    <i class="fa fa-link"></i> 连接
                                                </button>
                                                <button class="btn btn-sm btn-outline-danger" @click="disconnectDevice(device)" :disabled="device.status === 'offline'">
                                                    <i class="fa fa-unlink"></i> 断开
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 设备详情弹窗 -->
            <div class="row mb-3" v-if="selectedDevice">
                <div class="col">
                    <div class="card">
                        <div class="card-header d-flex justify-content-between align-items-center">
                            <h5 class="card-title mb-0">设备详情: {{ selectedDevice.name }}</h5>
                            <button type="button" class="btn-close" @click="selectedDevice = null"></button>
                        </div>
                        <div class="card-body">
                            <div class="row">
                                <div class="col-md-6">
                                    <h6>基本信息</h6>
                                    <table class="table table-sm">
                                        <tr>
                                            <th width="25%">设备名称</th>
                                            <td>{{ selectedDevice.name }}</td>
                                        </tr>
                                        <tr>
                                            <th>设备型号</th>
                                            <td>{{ selectedDevice.model }}</td>
                                        </tr>
                                        <tr>
                                            <th>屏幕分辨率</th>
                                            <td>{{ selectedDevice.resolution }}</td>
                                        </tr>
                                        <tr>
                                            <th>连接状态</th>
                                            <td>
                                                <span :class="getStatusBadgeClass(selectedDevice.status)">
                                                    {{ getStatusText(selectedDevice.status) }}
                                                </span>
                                            </td>
                                        </tr>
                                        <tr>
                                            <th>上次活动</th>
                                            <td>{{ selectedDevice.lastActivity }}</td>
                                        </tr>
                                    </table>
                                </div>
                                <div class="col-md-6">
                                    <h6>设备截图</h6>
                                    <div class="device-screenshot border">
                                        <img src="images/device_screenshot.png" alt="设备截图" class="img-fluid">
                                    </div>
                                    <div class="d-flex justify-content-center mt-2">
                                        <button class="btn btn-sm btn-outline-primary me-2" @click="refreshScreenshot">
                                            <i class="fa fa-sync"></i> 刷新截图
                                        </button>
                                        <button class="btn btn-sm btn-outline-secondary">
                                            <i class="fa fa-download"></i> 保存
                                        </button>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="row mt-3">
                                <div class="col-md-6">
                                    <h6>系统信息</h6>
                                    <table class="table table-sm">
                                        <tr>
                                            <th width="40%">操作系统</th>
                                            <td>Android 13</td>
                                        </tr>
                                        <tr>
                                            <th>内存使用</th>
                                            <td>
                                                <div class="progress" style="height: 8px;">
                                                    <div class="progress-bar" role="progressbar" style="width: 64%"></div>
                                                </div>
                                                <small>3.2GB / 5GB (64%)</small>
                                            </td>
                                        </tr>
                                        <tr>
                                            <th>存储空间</th>
                                            <td>
                                                <div class="progress" style="height: 8px;">
                                                    <div class="progress-bar" role="progressbar" style="width: 42%"></div>
                                                </div>
                                                <small>54GB / 128GB (42%)</small>
                                            </td>
                                        </tr>
                                        <tr>
                                            <th>电池电量</th>
                                            <td>
                                                <div class="progress" style="height: 8px;">
                                                    <div class="progress-bar bg-success" role="progressbar" style="width: 78%"></div>
                                                </div>
                                                <small>78%</small>
                                            </td>
                                        </tr>
                                    </table>
                                </div>
                                <div class="col-md-6">
                                    <h6>当前任务</h6>
                                    <div v-if="deviceTask">
                                        <table class="table table-sm">
                                            <tr>
                                                <th width="25%">任务名称</th>
                                                <td>{{ deviceTask.name }}</td>
                                            </tr>
                                            <tr>
                                                <th>执行脚本</th>
                                                <td>{{ deviceTask.script }}</td>
                                            </tr>
                                            <tr>
                                                <th>开始时间</th>
                                                <td>{{ deviceTask.startTime }}</td>
                                            </tr>
                                            <tr>
                                                <th>执行进度</th>
                                                <td>
                                                    <div class="progress" style="height: 8px;">
                                                        <div class="progress-bar progress-bar-striped progress-bar-animated" 
                                                             role="progressbar" :style="{width: deviceTask.progress}"></div>
                                                    </div>
                                                    <small>{{ deviceTask.progress }}</small>
                                                </td>
                                            </tr>
                                        </table>
                                        <div class="d-flex justify-content-end">
                                            <button class="btn btn-sm btn-danger" @click="stopDeviceTask(deviceTask)">
                                                <i class="fa fa-stop"></i> 停止任务
                                            </button>
                                        </div>
                                    </div>
                                    <div v-else class="text-center p-3 text-muted">
                                        <i class="fa fa-info-circle"></i> 设备当前没有执行中的任务
                                        <div class="mt-2">
                                            <button class="btn btn-sm btn-primary" @click="assignNewTask">分配新任务</button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="row mt-3">
                                <div class="col-12">
                                    <h6>历史任务</h6>
                                    <div class="table-responsive">
                                        <table class="table table-sm">
                                            <thead>
                                                <tr>
                                                    <th>任务名称</th>
                                                    <th>执行脚本</th>
                                                    <th>执行时间</th>
                                                    <th>状态</th>
                                                    <th>操作</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                <tr v-for="(task, index) in deviceHistory" :key="index">
                                                    <td>{{ task.name }}</td>
                                                    <td>{{ task.script }}</td>
                                                    <td>{{ task.executionTime }}</td>
                                                    <td>
                                                        <span :class="getTaskStatusBadgeClass(task.status)">
                                                            {{ task.status }}
                                                        </span>
                                                    </td>
                                                    <td>
                                                        <button class="btn btn-sm btn-outline-primary me-1">
                                                            <i class="fa fa-eye"></i>
                                                        </button>
                                                        <button class="btn btn-sm btn-outline-success">
                                                            <i class="fa fa-redo"></i>
                                                        </button>
                                                    </td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="row mt-3">
                                <div class="col-12 d-flex justify-content-end">
                                    <button class="btn btn-secondary" @click="selectedDevice = null">关闭</button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 添加设备模态框 -->
            <div class="modal fade" id="addDeviceModal" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">添加设备</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <div class="mb-3">
                                <label class="form-label">设备名称</label>
                                <input type="text" class="form-control" v-model="newDevice.name">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">设备型号</label>
                                <input type="text" class="form-control" v-model="newDevice.model">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">连接方式</label>
                                <select class="form-select" v-model="newDevice.connectionType">
                                    <option value="usb">USB</option>
                                    <option value="wifi">Wi-Fi</option>
                                    <option value="cloud">云端</option>
                                </select>
                            </div>
                            <div class="mb-3" v-if="newDevice.connectionType === 'wifi' || newDevice.connectionType === 'cloud'">
                                <label class="form-label">IP地址</label>
                                <input type="text" class="form-control" v-model="newDevice.ip">
                            </div>
                            <div class="mb-3" v-if="newDevice.connectionType === 'wifi' || newDevice.connectionType === 'cloud'">
                                <label class="form-label">端口</label>
                                <input type="number" class="form-control" v-model="newDevice.port">
                            </div>
                            <div class="device-advanced-toggle mt-3 mb-2">
                                <a href="#" @click.prevent="showAdvanced = !showAdvanced">
                                    高级选项 <i :class="showAdvanced ? 'fa fa-chevron-up' : 'fa fa-chevron-down'"></i>
                                </a>
                            </div>
                            <div v-if="showAdvanced">
                                <div class="mb-3">
                                    <label class="form-label">ADB路径</label>
                                    <input type="text" class="form-control" v-model="newDevice.adbPath">
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">自定义参数</label>
                                    <textarea class="form-control" rows="2" v-model="newDevice.customParams"></textarea>
                                </div>
                                <div class="mb-3 form-check">
                                    <input type="checkbox" class="form-check-input" id="autoReconnect" v-model="newDevice.autoReconnect">
                                    <label class="form-check-label" for="autoReconnect">断开连接后自动重连</label>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                            <button type="button" class="btn btn-primary" @click="addDevice">添加</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            devices: [],
            searchQuery: '',
            statusFilter: '',
            modelFilter: '',
            selectedDevice: null,
            deviceTask: null,
            deviceHistory: [
                { name: "登录场景测试", script: "login_steps.json", executionTime: "2025-05-12 15:48:46", status: "成功" },
                { name: "引导流程验证", script: "guide_steps.json", executionTime: "2025-05-10 10:23:15", status: "失败" },
                { name: "战斗系统测试", script: "battle_test.json", executionTime: "2025-05-08 14:30:21", status: "成功" }
            ],
            addDeviceModal: null,
            newDevice: {
                name: '',
                model: '',
                connectionType: 'usb',
                ip: '',
                port: 5555,
                adbPath: '',
                customParams: '',
                autoReconnect: true
            },
            showAdvanced: false
        };
    },
    computed: {
        filteredDevices() {
            return this.devices.filter(device => {
                const matchesSearch = device.name.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
                                     device.model.toLowerCase().includes(this.searchQuery.toLowerCase());
                                     
                const matchesStatus = this.statusFilter ? device.status === this.statusFilter : true;
                
                const matchesModel = this.modelFilter ? device.model === this.modelFilter : true;
                
                return matchesSearch && matchesStatus && matchesModel;
            });
        }
    },
    mounted() {
        this.loadDevices();
        this.addDeviceModal = new bootstrap.Modal(document.getElementById('addDeviceModal'));
    },
    methods: {
        async loadDevices() {
            try {
                const response = await api.request('/devices');
                this.devices = response.data;
            } catch (error) {
                console.error('加载设备失败:', error);
            }
        },
        getStatusIndicatorClass(status) {
            switch (status) {
                case 'online': return 'status-online';
                case 'offline': return 'status-offline';
                case 'executing': return 'status-executing';
                default: return 'status-unknown';
            }
        },
        getStatusText(status) {
            switch (status) {
                case 'online': return '在线';
                case 'offline': return '离线';
                case 'executing': return '执行中';
                default: return '未知';
            }
        },
        getStatusBadgeClass(status) {
            switch (status) {
                case 'online': return 'badge bg-success';
                case 'offline': return 'badge bg-secondary';
                case 'executing': return 'badge bg-primary';
                default: return 'badge bg-secondary';
            }
        },
        getTaskStatusBadgeClass(status) {
            switch (status) {
                case '成功': return 'badge bg-success';
                case '失败': return 'badge bg-danger';
                case '执行中': return 'badge bg-primary';
                default: return 'badge bg-secondary';
            }
        },
        viewDeviceDetail(device) {
            this.selectedDevice = device;
            
            // 如果设备正在执行任务，设置当前任务信息
            if (device.status === 'executing') {
                this.deviceTask = {
                    name: '登录场景测试',
                    script: 'login_steps.json',
                    startTime: '2025-05-12 15:48:46',
                    progress: '65%'
                };
            } else {
                this.deviceTask = null;
            }
        },
        editDevice(device) {
            console.log('编辑设备:', device);
            // 这里实现编辑设备的逻辑
        },
        restartDevice(device) {
            if (confirm(`确定要重启设备 "${device.name}" 吗？`)) {
                console.log('重启设备:', device);
                // 这里实现重启设备的逻辑
            }
        },
        connectDevice(device) {
            console.log('连接设备:', device);
            // 这里实现连接设备的逻辑
        },
        disconnectDevice(device) {
            if (confirm(`确定要断开设备 "${device.name}" 的连接吗？`)) {
                console.log('断开设备连接:', device);
                // 这里实现断开设备连接的逻辑
            }
        },
        refreshScreenshot() {
            console.log('刷新设备截图');
            // 这里实现刷新设备截图的逻辑
        },
        stopDeviceTask(task) {
            if (confirm(`确定要停止任务 "${task.name}" 吗？`)) {
                console.log('停止设备任务:', task);
                // 这里实现停止设备任务的逻辑
                this.deviceTask = null;
            }
        },
        assignNewTask() {
            console.log('为设备分配新任务');
            Router.navigate('tasks');
        },
        refreshDevices() {
            console.log('刷新设备列表');
            this.loadDevices();
        },
        showAddDeviceModal() {
            this.addDeviceModal.show();
        },
        addDevice() {
            console.log('添加设备:', this.newDevice);
            // 这里实现添加设备的逻辑
            this.addDeviceModal.hide();
            
            // 重置表单
            this.newDevice = {
                name: '',
                model: '',
                connectionType: 'usb',
                ip: '',
                port: 5555,
                adbPath: '',
                customParams: '',
                autoReconnect: true
            };
            this.showAdvanced = false;
        }
    }
}; 