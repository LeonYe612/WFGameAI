// 测试任务组件
const TestTasks = {
    template: `
        <div>
            <div class="row mb-3">
                <div class="col">
                    <div class="card">
                        <div class="card-header d-flex justify-content-between align-items-center">
                            <h5 class="card-title mb-0">任务列表</h5>
                            <div class="action-buttons">
                                <button class="btn btn-primary btn-sm" @click="showCreateTaskModal">
                                    <i class="fa fa-plus"></i> 新建任务
                                </button>
                                <button class="btn btn-success btn-sm ms-2" @click="showBatchRunModal">
                                    <i class="fa fa-play"></i> 批量执行
                                </button>
                            </div>
                        </div>
                        <div class="card-body">
                            <div class="task-filters d-flex flex-wrap align-items-center mb-3">
                                <div class="me-3 mb-2">
                                    <select class="form-select form-select-sm" v-model="selectedDevice">
                                        <option value="">所有设备</option>
                                        <option v-for="device in devices" :key="device.id" :value="device.name">
                                            {{ device.name }}
                                        </option>
                                    </select>
                                </div>
                                <div class="me-3 mb-2">
                                    <select class="form-select form-select-sm" v-model="selectedStatus">
                                        <option value="">所有状态</option>
                                        <option value="pending">等待中</option>
                                        <option value="executing">执行中</option>
                                        <option value="completed">已完成</option>
                                        <option value="failed">失败</option>
                                    </select>
                                </div>
                                <div class="me-3 mb-2">
                                    <div class="input-group input-group-sm">
                                        <span class="input-group-text">日期</span>
                                        <input type="date" class="form-control" v-model="dateFilter">
                                    </div>
                                </div>
                                <div class="ms-auto mb-2">
                                    <div class="input-group input-group-sm">
                                        <input type="text" class="form-control" placeholder="搜索任务..." v-model="searchQuery">
                                        <button class="btn btn-outline-secondary" type="button">
                                            <i class="fa fa-search"></i>
                                        </button>
                                    </div>
                                </div>
                            </div>

                            <div class="table-responsive">
                                <table class="table table-hover">
                                    <thead>
                                        <tr>
                                            <th>
                                                <div class="form-check">
                                                    <input class="form-check-input" type="checkbox" v-model="selectAll" @change="toggleSelectAll">
                                                </div>
                                            </th>
                                            <th>ID</th>
                                            <th>任务名称</th>
                                            <th>脚本</th>
                                            <th>设备</th>
                                            <th>开始时间</th>
                                            <th>状态</th>
                                            <th>进度</th>
                                            <th>操作</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr v-for="task in filteredTasks" :key="task.id" :class="{'table-warning': task.status === 'executing'}">
                                            <td>
                                                <div class="form-check">
                                                    <input class="form-check-input" type="checkbox" v-model="task.selected">
                                                </div>
                                            </td>
                                            <td>#{{ task.id }}</td>
                                            <td>{{ task.name }}</td>
                                            <td>{{ task.script }}</td>
                                            <td>{{ task.device }}</td>
                                            <td>{{ task.startTime }}</td>
                                            <td>
                                                <span :class="getStatusBadgeClass(task.status)">
                                                    {{ getStatusText(task.status) }}
                                                </span>
                                            </td>
                                            <td>
                                                <div class="progress" style="height: 8px;">
                                                    <div class="progress-bar" role="progressbar"
                                                         :style="{width: task.progress}"
                                                         :class="getProgressBarClass(task.status)">
                                                    </div>
                                                </div>
                                                <small>{{ task.progress }}</small>
                                            </td>
                                            <td>
                                                <div class="table-actions">
                                                    <button class="action-btn view" title="查看详情" @click="viewTaskDetail(task)">
                                                        <i class="fa fa-eye"></i>
                                                    </button>
                                                    <button class="action-btn stop" title="停止" v-if="task.status === 'executing'" @click="stopTask(task)">
                                                        <i class="fa fa-stop"></i>
                                                    </button>
                                                    <button class="action-btn restart" title="重新执行" v-if="task.status === 'completed' || task.status === 'failed'" @click="restartTask(task)">
                                                        <i class="fa fa-redo"></i>
                                                    </button>
                                                    <button class="action-btn delete" title="删除" @click="deleteTask(task)">
                                                        <i class="fa fa-trash"></i>
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>

                            <div class="pagination-wrapper d-flex justify-content-between align-items-center mt-3">
                                <div class="page-info">显示 {{ filteredTasks.length }} / {{ tasks.length }} 条任务</div>
                                <ul class="pagination pagination-sm">
                                    <li class="page-item disabled"><a class="page-link" href="#">上一页</a></li>
                                    <li class="page-item active"><a class="page-link" href="#">1</a></li>
                                    <li class="page-item"><a class="page-link" href="#">2</a></li>
                                    <li class="page-item"><a class="page-link" href="#">3</a></li>
                                    <li class="page-item"><a class="page-link" href="#">下一页</a></li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 任务详情 -->
            <div class="row mb-3" v-if="selectedTask">
                <div class="col">
                    <div class="card">
                        <div class="card-header d-flex justify-content-between align-items-center">
                            <h5 class="card-title mb-0">任务详情: {{ selectedTask.name }}</h5>
                            <button type="button" class="btn-close" @click="selectedTask = null"></button>
                        </div>
                        <div class="card-body">
                            <div class="row">
                                <div class="col-md-6">
                                    <h6>基本信息</h6>
                                    <table class="table table-sm">
                                        <tr>
                                            <th width="25%">任务ID</th>
                                            <td>#{{ selectedTask.id }}</td>
                                        </tr>
                                        <tr>
                                            <th>任务名称</th>
                                            <td>{{ selectedTask.name }}</td>
                                        </tr>
                                        <tr>
                                            <th>执行脚本</th>
                                            <td>{{ selectedTask.script }}</td>
                                        </tr>
                                        <tr>
                                            <th>执行设备</th>
                                            <td>{{ selectedTask.device }}</td>
                                        </tr>
                                        <tr>
                                            <th>开始时间</th>
                                            <td>{{ selectedTask.startTime }}</td>
                                        </tr>
                                        <tr>
                                            <th>当前状态</th>
                                            <td>
                                                <span :class="getStatusBadgeClass(selectedTask.status)">
                                                    {{ getStatusText(selectedTask.status) }}
                                                </span>
                                            </td>
                                        </tr>
                                    </table>
                                </div>
                                <div class="col-md-6">
                                    <h6>执行进度</h6>
                                    <div class="progress mb-3" style="height: 20px;">
                                        <div class="progress-bar" role="progressbar"
                                             :style="{width: selectedTask.progress}"
                                             :class="getProgressBarClass(selectedTask.status)">
                                            {{ selectedTask.progress }}
                                        </div>
                                    </div>

                                    <h6>执行日志</h6>
                                    <div class="task-log border p-2" style="height: 200px; overflow-y: auto;">
                                        <div v-for="(log, index) in taskLogs" :key="index" class="log-entry">
                                            <span class="log-time">{{ log.time }}</span>
                                            <span :class="'log-level-' + log.level">{{ log.message }}</span>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div class="row mt-3">
                                <div class="col-12">
                                    <h6>步骤执行情况</h6>
                                    <div class="table-responsive">
                                        <table class="table table-sm">
                                            <thead>
                                                <tr>
                                                    <th width="5%">步骤</th>
                                                    <th width="15%">操作类型</th>
                                                    <th width="25%">目标元素</th>
                                                    <th width="20%">执行时间</th>
                                                    <th width="10%">状态</th>
                                                    <th>结果</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                <tr v-for="(step, index) in taskSteps" :key="index" :class="getStepRowClass(step.status)">
                                                    <td>{{ index + 1 }}</td>
                                                    <td>{{ step.type }}</td>
                                                    <td>{{ step.target }}</td>
                                                    <td>{{ step.executionTime }}</td>
                                                    <td>
                                                        <span :class="getStepStatusClass(step.status)">
                                                            {{ step.status }}
                                                        </span>
                                                    </td>
                                                    <td>{{ step.result }}</td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>

                            <div class="row mt-3">
                                <div class="col-12 d-flex justify-content-end">
                                    <button class="btn btn-primary me-2" @click="generateReport">生成报告</button>
                                    <button class="btn btn-secondary" @click="selectedTask = null">关闭</button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 创建任务模态框 -->
            <div class="modal fade" id="createTaskModal" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">创建新任务</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <div class="mb-3">
                                <label class="form-label">任务名称</label>
                                <input type="text" class="form-control" v-model="newTask.name">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">选择脚本</label>
                                <select class="form-select" v-model="newTask.script">
                                    <option v-for="script in scripts" :key="script.id" :value="script.name">
                                        {{ script.name }}
                                    </option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">选择设备</label>
                                <select class="form-select" v-model="newTask.device">
                                    <option v-for="device in devices" :key="device.id" :value="device.name">
                                        {{ device.name }} ({{ getDeviceStatusText(device.status) }})
                                    </option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">执行优先级</label>
                                <select class="form-select" v-model="newTask.priority">
                                    <option value="low">低</option>
                                    <option value="normal">普通</option>
                                    <option value="high">高</option>
                                </select>
                            </div>
                            <div class="mb-3 form-check">
                                <input type="checkbox" class="form-check-input" id="aiEnhanced" v-model="newTask.aiEnhanced">
                                <label class="form-check-label" for="aiEnhanced">启用AI视觉增强</label>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                            <button type="button" class="btn btn-primary" @click="createTask">创建</button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 批量执行模态框 -->
            <div class="modal fade" id="batchRunModal" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">批量执行</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <div class="row mb-3">
                                <div class="col-md-6">
                                    <label class="form-label">选择脚本</label>
                                    <div class="scripts-select border p-2" style="height: 200px; overflow-y: auto;">
                                        <div class="form-check" v-for="script in scripts" :key="script.id">
                                            <input class="form-check-input" type="checkbox" :id="'script-' + script.id" v-model="script.selected">
                                            <label class="form-check-label" :for="'script-' + script.id">
                                                {{ script.name }}
                                            </label>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label">选择设备</label>
                                    <div class="devices-select border p-2" style="height: 200px; overflow-y: auto;">
                                        <div class="form-check" v-for="device in devices" :key="device.id">
                                            <input class="form-check-input" type="checkbox" :id="'device-' + device.id" v-model="device.selected" :disabled="device.status === 'offline'">
                                            <label class="form-check-label" :for="'device-' + device.id">
                                                {{ device.name }}
                                                <span :class="getDeviceStatusIndicatorClass(device.status)">
                                                    ({{ getDeviceStatusText(device.status) }})
                                                </span>
                                            </label>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="row">
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <label class="form-label">执行模式</label>
                                        <select class="form-select" v-model="batchSettings.executionMode">
                                            <option value="sequential">顺序执行</option>
                                            <option value="parallel">并行执行</option>
                                        </select>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <label class="form-label">执行优先级</label>
                                        <select class="form-select" v-model="batchSettings.priority">
                                            <option value="low">低</option>
                                            <option value="normal">普通</option>
                                            <option value="high">高</option>
                                        </select>
                                    </div>
                                </div>
                            </div>
                            <div class="mb-3 form-check">
                                <input type="checkbox" class="form-check-input" id="batchAiEnhanced" v-model="batchSettings.aiEnhanced">
                                <label class="form-check-label" for="batchAiEnhanced">启用AI视觉增强</label>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                            <button type="button" class="btn btn-primary" @click="startBatchExecution">开始执行</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            tasks: [],
            scripts: [],
            devices: [],
            searchQuery: '',
            selectedDevice: '',
            selectedStatus: '',
            dateFilter: '',
            selectAll: false,
            selectedTask: null,
            taskLogs: [
                { time: '2025-05-12 15:48:46', level: 'info', message: '任务开始执行' },
                { time: '2025-05-12 15:48:47', level: 'info', message: '连接设备: OnePlus-KB2000' },
                { time: '2025-05-12 15:48:48', level: 'info', message: '加载脚本: login_steps.json' },
                { time: '2025-05-12 15:48:50', level: 'info', message: '执行步骤 1: 点击按钮 "开始游戏"' },
                { time: '2025-05-12 15:48:53', level: 'info', message: '执行步骤 2: 等待页面加载' },
                { time: '2025-05-12 15:48:58', level: 'info', message: '执行步骤 3: 输入账号' },
                { time: '2025-05-12 15:49:02', level: 'info', message: '执行步骤 4: 输入密码' },
                { time: '2025-05-12 15:49:06', level: 'info', message: '执行步骤 5: 点击登录按钮' },
                { time: '2025-05-12 15:49:10', level: 'info', message: '执行步骤 6: 等待登录完成' },
                { time: '2025-05-12 15:49:15', level: 'success', message: '任务执行完成' }
            ],
            taskSteps: [
                { type: '点击', target: '开始游戏按钮', executionTime: '2025-05-12 15:48:50', status: '成功', result: '点击成功' },
                { type: '等待', target: '页面加载', executionTime: '2025-05-12 15:48:53', status: '成功', result: '页面加载完成' },
                { type: '输入', target: '账号输入框', executionTime: '2025-05-12 15:48:58', status: '成功', result: '输入成功' },
                { type: '输入', target: '密码输入框', executionTime: '2025-05-12 15:49:02', status: '成功', result: '输入成功' },
                { type: '点击', target: '登录按钮', executionTime: '2025-05-12 15:49:06', status: '成功', result: '点击成功' },
                { type: '等待', target: '登录完成', executionTime: '2025-05-12 15:49:10', status: '成功', result: '登录成功' },
                { type: 'AI识别', target: '主界面元素', executionTime: '2025-05-12 15:49:14', status: '成功', result: '识别成功，匹配度：98%' }
            ],
            newTask: {
                name: '',
                script: '',
                device: '',
                priority: 'normal',
                aiEnhanced: false
            },
            createTaskModal: null,
            batchRunModal: null,
            batchSettings: {
                executionMode: 'sequential',
                priority: 'normal',
                aiEnhanced: false
            }
        };
    },
    computed: {
        filteredTasks() {
            return this.tasks.filter(task => {
                // 设备筛选
                const matchesDevice = this.selectedDevice ? task.device === this.selectedDevice : true;

                // 状态筛选
                const matchesStatus = this.selectedStatus ? task.status === this.selectedStatus : true;

                // 搜索筛选
                const matchesSearch = this.searchQuery ?
                    task.name.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
                    task.script.toLowerCase().includes(this.searchQuery.toLowerCase()) :
                    true;

                // 日期筛选
                const matchesDate = this.dateFilter ?
                    task.startTime.includes(this.dateFilter) :
                    true;

                return matchesDevice && matchesStatus && matchesSearch && matchesDate;
            });
        }
    },
    mounted() {
        this.loadTasks();
        this.loadScripts();
        this.loadDevices();
        this.createTaskModal = new bootstrap.Modal(document.getElementById('createTaskModal'));
        this.batchRunModal = new bootstrap.Modal(document.getElementById('batchRunModal'));
    },
    methods: {
        async loadTasks() {
            try {
                const response = await api.request('/tasks');
                this.tasks = response.data.map(task => ({...task, selected: false}));
            } catch (error) {
                console.error('加载任务失败:', error);
            }
        },
        async loadScripts() {
            try {
                const response = await api.request('/scripts');
                this.scripts = response.data.map(script => ({...script, selected: false}));
            } catch (error) {
                console.error('加载脚本失败:', error);
            }
        },
        async loadDevices() {
            try {
                const response = await api.request('/devices');
                this.devices = response.data.map(device => ({...device, selected: false}));
            } catch (error) {
                console.error('加载设备失败:', error);
            }
        },
        toggleSelectAll() {
            this.tasks.forEach(task => {
                task.selected = this.selectAll;
            });
        },
        getStatusBadgeClass(status) {
            switch (status) {
                case 'pending': return 'badge bg-secondary';
                case 'executing': return 'badge bg-primary';
                case 'completed': return 'badge bg-success';
                case 'failed': return 'badge bg-danger';
                default: return 'badge bg-secondary';
            }
        },
        getStatusText(status) {
            switch (status) {
                case 'pending': return '等待中';
                case 'executing': return '执行中';
                case 'completed': return '已完成';
                case 'failed': return '失败';
                default: return '未知';
            }
        },
        getProgressBarClass(status) {
            switch (status) {
                case 'pending': return 'bg-secondary';
                case 'executing': return 'bg-primary progress-bar-striped progress-bar-animated';
                case 'completed': return 'bg-success';
                case 'failed': return 'bg-danger';
                default: return 'bg-secondary';
            }
        },
        getStepRowClass(status) {
            switch (status) {
                case '成功': return '';
                case '失败': return 'table-danger';
                case '跳过': return 'table-secondary';
                case '执行中': return 'table-warning';
                default: return '';
            }
        },
        getStepStatusClass(status) {
            switch (status) {
                case '成功': return 'badge bg-success';
                case '失败': return 'badge bg-danger';
                case '跳过': return 'badge bg-secondary';
                case '执行中': return 'badge bg-warning';
                default: return 'badge bg-secondary';
            }
        },
        getDeviceStatusText(status) {
            switch (status) {
                case 'online': return '在线';
                case 'offline': return '离线';
                case 'executing': return '执行中';
                default: return '未知';
            }
        },
        getDeviceStatusIndicatorClass(status) {
            switch (status) {
                case 'online': return 'text-success';
                case 'offline': return 'text-secondary';
                case 'executing': return 'text-primary';
                default: return 'text-secondary';
            }
        },
        viewTaskDetail(task) {
            this.selectedTask = task;
        },
        stopTask(task) {
            if (confirm(`确定要停止任务 "${task.name}" 吗？`)) {
                console.log('停止任务:', task);
                // 这里实现停止任务的逻辑
            }
        },
        restartTask(task) {
            if (confirm(`确定要重新执行任务 "${task.name}" 吗？`)) {
                console.log('重新执行任务:', task);
                // 这里实现重新执行任务的逻辑
            }
        },
        deleteTask(task) {
            if (confirm(`确定要删除任务 "${task.name}" 吗？`)) {
                console.log('删除任务:', task);
                // 这里实现删除任务的逻辑
            }
        },
        showCreateTaskModal() {
            this.createTaskModal.show();
        },
        createTask() {
            console.log('创建任务:', this.newTask);
            // 这里实现创建任务的逻辑
            this.createTaskModal.hide();

            // 重置表单
            this.newTask = {
                name: '',
                script: '',
                device: '',
                priority: 'normal',
                aiEnhanced: false
            };
        },
        showBatchRunModal() {
            this.batchRunModal.show();
        },
        startBatchExecution() {
            const selectedScripts = this.scripts.filter(script => script.selected);
            const selectedDevices = this.devices.filter(device => device.selected);

            console.log('批量执行:', {
                scripts: selectedScripts,
                devices: selectedDevices,
                settings: this.batchSettings
            });

            // 这里实现批量执行的逻辑
            this.batchRunModal.hide();
        },
        generateReport() {
            console.log('生成报告:', this.selectedTask);
            Router.navigate('reports');
        }
    }
};