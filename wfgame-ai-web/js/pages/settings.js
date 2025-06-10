// 系统设置组件
const SystemSettings = {
    template: `
        <div>
            <div class="row">
                <div class="col-md-3">
                    <div class="card">
                        <div class="card-header">
                            <h5 class="card-title mb-0">设置分类</h5>
                        </div>
                        <div class="card-body p-0">
                            <div class="list-group list-group-flush">
                                <a href="#" class="list-group-item list-group-item-action"
                                   :class="{'active': activeTab === 'general'}"
                                   @click.prevent="activeTab = 'general'">
                                    <i class="fa fa-cog me-2"></i> 通用设置
                                </a>
                                <a href="#" class="list-group-item list-group-item-action"
                                   :class="{'active': activeTab === 'ai'}"
                                   @click.prevent="activeTab = 'ai'">
                                    <i class="fa fa-brain me-2"></i> AI设置
                                </a>
                                <a href="#" class="list-group-item list-group-item-action"
                                   :class="{'active': activeTab === 'device'}"
                                   @click.prevent="activeTab = 'device'">
                                    <i class="fa fa-mobile-alt me-2"></i> 设备设置
                                </a>
                                <a href="#" class="list-group-item list-group-item-action"
                                   :class="{'active': activeTab === 'notification'}"
                                   @click.prevent="activeTab = 'notification'">
                                    <i class="fa fa-bell me-2"></i> 通知设置
                                </a>
                                <a href="#" class="list-group-item list-group-item-action"
                                   :class="{'active': activeTab === 'security'}"
                                   @click.prevent="activeTab = 'security'">
                                    <i class="fa fa-shield-alt me-2"></i> 安全设置
                                </a>
                                <a href="#" class="list-group-item list-group-item-action"
                                   :class="{'active': activeTab === 'system'}"
                                   @click.prevent="activeTab = 'system'">
                                    <i class="fa fa-server me-2"></i> 系统信息
                                </a>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="col-md-9">
                    <div class="card">
                        <div class="card-header">
                            <h5 class="card-title mb-0">{{ getActiveTabTitle() }}</h5>
                        </div>
                        <div class="card-body">
                            <!-- 通用设置 -->
                            <div v-if="activeTab === 'general'">
                                <div class="mb-4">
                                    <h6>界面设置</h6>
                                    <div class="mb-3">
                                        <label class="form-label">主题</label>
                                        <select class="form-select" v-model="settings.general.theme">
                                            <option value="light">浅色</option>
                                            <option value="dark">深色</option>
                                            <option value="auto">跟随系统</option>
                                        </select>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">语言</label>
                                        <select class="form-select" v-model="settings.general.language">
                                            <option value="zh">中文</option>
                                            <option value="en">English</option>
                                        </select>
                                    </div>
                                </div>

                                <div class="mb-4">
                                    <h6>数据设置</h6>
                                    <div class="mb-3 form-check">
                                        <input type="checkbox" class="form-check-input" id="autoBackup" v-model="settings.general.autoBackup">
                                        <label class="form-check-label" for="autoBackup">自动备份数据</label>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">备份频率</label>
                                        <select class="form-select" v-model="settings.general.backupFrequency" :disabled="!settings.general.autoBackup">
                                            <option value="daily">每天</option>
                                            <option value="weekly">每周</option>
                                            <option value="monthly">每月</option>
                                        </select>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">数据保留期限</label>
                                        <select class="form-select" v-model="settings.general.dataRetention">
                                            <option value="30">30天</option>
                                            <option value="90">90天</option>
                                            <option value="180">180天</option>
                                            <option value="365">1年</option>
                                            <option value="-1">永久</option>
                                        </select>
                                    </div>
                                </div>
                            </div>

                            <!-- AI设置 -->
                            <div v-if="activeTab === 'ai'">
                                <div class="mb-4">
                                    <h6>视觉识别设置</h6>
                                    <div class="mb-3">
                                        <label class="form-label">模型类型</label>
                                        <select class="form-select" v-model="settings.ai.modelType">
                                            <option value="fast">快速模式（YOLOv5s）</option>
                                            <option value="balanced">平衡模式（YOLOv5m）</option>
                                            <option value="accurate">精确模式（YOLOv5l）</option>
                                        </select>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">置信度阈值</label>
                                        <input type="range" class="form-range" min="0" max="1" step="0.05" v-model="settings.ai.confidenceThreshold">
                                        <div class="d-flex justify-content-between">
                                            <small>低 (0.3)</small>
                                            <small>{{ settings.ai.confidenceThreshold }}</small>
                                            <small>高 (0.9)</small>
                                        </div>
                                    </div>
                                    <div class="mb-3 form-check">
                                        <input type="checkbox" class="form-check-input" id="enableGPU" v-model="settings.ai.enableGPU">
                                        <label class="form-check-label" for="enableGPU">启用GPU加速</label>
                                    </div>
                                </div>

                                <div class="mb-4">
                                    <h6>智能辅助设置</h6>
                                    <div class="mb-3 form-check">
                                        <input type="checkbox" class="form-check-input" id="autoRetry" v-model="settings.ai.autoRetry">
                                        <label class="form-check-label" for="autoRetry">自动重试失败操作</label>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">最大重试次数</label>
                                        <input type="number" class="form-control" v-model="settings.ai.maxRetries" :disabled="!settings.ai.autoRetry">
                                    </div>
                                    <div class="mb-3 form-check">
                                        <input type="checkbox" class="form-check-input" id="adaptiveWait" v-model="settings.ai.adaptiveWait">
                                        <label class="form-check-label" for="adaptiveWait">自适应等待时间</label>
                                    </div>
                                </div>
                            </div>

                            <!-- 设备设置 -->
                            <div v-if="activeTab === 'device'">
                                <div class="mb-4">
                                    <h6>连接设置</h6>
                                    <div class="mb-3">
                                        <label class="form-label">ADB路径</label>
                                        <div class="input-group">
                                            <input type="text" class="form-control" v-model="settings.device.adbPath">
                                            <button class="btn btn-outline-secondary" type="button">浏览...</button>
                                        </div>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">连接超时（秒）</label>
                                        <input type="number" class="form-control" v-model="settings.device.connectionTimeout">
                                    </div>
                                    <div class="mb-3 form-check">
                                        <input type="checkbox" class="form-check-input" id="autoReconnect" v-model="settings.device.autoReconnect">
                                        <label class="form-check-label" for="autoReconnect">自动重连设备</label>
                                    </div>
                                </div>

                                <div class="mb-4">
                                    <h6>截图设置</h6>
                                    <div class="mb-3">
                                        <label class="form-label">截图质量</label>
                                        <select class="form-select" v-model="settings.device.screenshotQuality">
                                            <option value="low">低（更快）</option>
                                            <option value="medium">中</option>
                                            <option value="high">高（更清晰）</option>
                                        </select>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">截图保存路径</label>
                                        <div class="input-group">
                                            <input type="text" class="form-control" v-model="settings.device.screenshotPath">
                                            <button class="btn btn-outline-secondary" type="button">浏览...</button>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- 通知设置 -->
                            <div v-if="activeTab === 'notification'">
                                <div class="mb-4">
                                    <h6>通知方式</h6>
                                    <div class="mb-3 form-check">
                                        <input type="checkbox" class="form-check-input" id="enableNotification" v-model="settings.notification.enabled">
                                        <label class="form-check-label" for="enableNotification">启用通知</label>
                                    </div>
                                    <div class="mb-3 form-check">
                                        <input type="checkbox" class="form-check-input" id="browserNotification" v-model="settings.notification.browser" :disabled="!settings.notification.enabled">
                                        <label class="form-check-label" for="browserNotification">浏览器通知</label>
                                    </div>
                                    <div class="mb-3 form-check">
                                        <input type="checkbox" class="form-check-input" id="emailNotification" v-model="settings.notification.email" :disabled="!settings.notification.enabled">
                                        <label class="form-check-label" for="emailNotification">邮件通知</label>
                                    </div>
                                </div>

                                <div class="mb-4" v-if="settings.notification.email && settings.notification.enabled">
                                    <h6>邮件设置</h6>
                                    <div class="mb-3">
                                        <label class="form-label">收件邮箱</label>
                                        <input type="email" class="form-control" v-model="settings.notification.emailAddress">
                                    </div>
                                </div>

                                <div class="mb-4">
                                    <h6>通知事件</h6>
                                    <div class="mb-3 form-check">
                                        <input type="checkbox" class="form-check-input" id="notifyTaskComplete" v-model="settings.notification.taskComplete" :disabled="!settings.notification.enabled">
                                        <label class="form-check-label" for="notifyTaskComplete">任务完成</label>
                                    </div>
                                    <div class="mb-3 form-check">
                                        <input type="checkbox" class="form-check-input" id="notifyTaskFail" v-model="settings.notification.taskFail" :disabled="!settings.notification.enabled">
                                        <label class="form-check-label" for="notifyTaskFail">任务失败</label>
                                    </div>
                                    <div class="mb-3 form-check">
                                        <input type="checkbox" class="form-check-input" id="notifyDeviceOffline" v-model="settings.notification.deviceOffline" :disabled="!settings.notification.enabled">
                                        <label class="form-check-label" for="notifyDeviceOffline">设备离线</label>
                                    </div>
                                </div>
                            </div>

                            <!-- 安全设置 -->
                            <div v-if="activeTab === 'security'">
                                <div class="mb-4">
                                    <h6>账户安全</h6>
                                    <div class="mb-3">
                                        <label class="form-label">修改密码</label>
                                        <div class="input-group mb-2">
                                            <span class="input-group-text">当前密码</span>
                                            <input type="password" class="form-control" v-model="passwordForm.current">
                                        </div>
                                        <div class="input-group mb-2">
                                            <span class="input-group-text">新密码</span>
                                            <input type="password" class="form-control" v-model="passwordForm.new">
                                        </div>
                                        <div class="input-group mb-2">
                                            <span class="input-group-text">确认密码</span>
                                            <input type="password" class="form-control" v-model="passwordForm.confirm">
                                        </div>
                                        <button class="btn btn-primary" @click="changePassword">修改密码</button>
                                    </div>
                                </div>

                                <div class="mb-4">
                                    <h6>访问控制</h6>
                                    <div class="mb-3 form-check">
                                        <input type="checkbox" class="form-check-input" id="enableIpFilter" v-model="settings.security.ipFilter">
                                        <label class="form-check-label" for="enableIpFilter">启用IP地址过滤</label>
                                    </div>
                                    <div class="mb-3" v-if="settings.security.ipFilter">
                                        <label class="form-label">允许的IP地址（每行一个）</label>
                                        <textarea class="form-control" rows="3" v-model="settings.security.allowedIPs"></textarea>
                                    </div>
                                    <div class="mb-3 form-check">
                                        <input type="checkbox" class="form-check-input" id="enableTwoFactor" v-model="settings.security.twoFactorAuth">
                                        <label class="form-check-label" for="enableTwoFactor">启用两因素认证</label>
                                    </div>
                                </div>
                            </div>

                            <!-- 系统信息 -->
                            <div v-if="activeTab === 'system'">
                                <div class="mb-4">
                                    <h6>版本信息</h6>
                                    <table class="table table-sm">
                                        <tr>
                                            <th width="30%">软件版本</th>
                                            <td>v2.5.0</td>
                                        </tr>
                                        <tr>
                                            <th>AI引擎版本</th>
                                            <td>v1.8.2</td>
                                        </tr>
                                        <tr>
                                            <th>上次更新</th>
                                            <td>2025-05-01</td>
                                        </tr>
                                    </table>
                                    <button class="btn btn-outline-primary btn-sm" @click="checkForUpdates">
                                        <i class="fa fa-sync me-1"></i> 检查更新
                                    </button>
                                </div>

                                <div class="mb-4">
                                    <h6>系统资源</h6>
                                    <table class="table table-sm">
                                        <tr>
                                            <th width="30%">CPU使用率</th>
                                            <td>
                                                <div class="progress" style="height: 8px;">
                                                    <div class="progress-bar" role="progressbar" style="width: 45%"></div>
                                                </div>
                                                <small>45%</small>
                                            </td>
                                        </tr>
                                        <tr>
                                            <th>内存使用</th>
                                            <td>
                                                <div class="progress" style="height: 8px;">
                                                    <div class="progress-bar" role="progressbar" style="width: 62%"></div>
                                                </div>
                                                <small>3.2GB / 5.2GB (62%)</small>
                                            </td>
                                        </tr>
                                        <tr>
                                            <th>磁盘使用</th>
                                            <td>
                                                <div class="progress" style="height: 8px;">
                                                    <div class="progress-bar" role="progressbar" style="width: 30%"></div>
                                                </div>
                                                <small>45GB / 150GB (30%)</small>
                                            </td>
                                        </tr>
                                    </table>
                                </div>

                                <div class="mb-4">
                                    <h6>日志</h6>
                                    <div class="mb-3">
                                        <label class="form-label">日志级别</label>
                                        <select class="form-select" v-model="settings.system.logLevel">
                                            <option value="error">Error</option>
                                            <option value="warn">Warning</option>
                                            <option value="info">Info</option>
                                            <option value="debug">Debug</option>
                                        </select>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">日志目录</label>
                                        <input type="text" class="form-control" v-model="settings.system.logDirectory" readonly>
                                    </div>
                                    <button class="btn btn-outline-secondary btn-sm" @click="openLogDirectory">
                                        <i class="fa fa-folder-open me-1"></i> 打开日志目录
                                    </button>
                                    <button class="btn btn-outline-secondary btn-sm ms-2" @click="downloadLogs">
                                        <i class="fa fa-download me-1"></i> 下载日志
                                    </button>
                                </div>
                            </div>

                            <div class="settings-actions d-flex justify-content-end mt-4">
                                <button class="btn btn-outline-secondary me-2" @click="resetSettings">重置设置</button>
                                <button class="btn btn-primary" @click="saveSettings">保存设置</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            activeTab: 'general',
            settings: {
                general: {
                    theme: 'light',
                    language: 'zh',
                    autoBackup: true,
                    backupFrequency: 'daily',
                    dataRetention: '90'
                },
                ai: {
                    modelType: 'balanced',
                    confidenceThreshold: 0.6,
                    enableGPU: true,
                    autoRetry: true,
                    maxRetries: 3,
                    adaptiveWait: true
                },
                device: {
                    adbPath: '/usr/local/bin/adb',
                    connectionTimeout: 30,
                    autoReconnect: true,
                    screenshotQuality: 'medium',
                    screenshotPath: './screenshots'
                },
                notification: {
                    enabled: true,
                    browser: true,
                    email: false,
                    emailAddress: '',
                    taskComplete: true,
                    taskFail: true,
                    deviceOffline: true
                },
                security: {
                    ipFilter: false,
                    allowedIPs: '127.0.0.1\n192.168.1.0/24',
                    twoFactorAuth: false
                },
                system: {
                    logLevel: 'info',
                    logDirectory: '/var/log/wfgame-ai'
                }
            },
            passwordForm: {
                current: '',
                new: '',
                confirm: ''
            }
        };
    },
    methods: {
        getActiveTabTitle() {
            switch (this.activeTab) {
                case 'general': return '通用设置';
                case 'ai': return 'AI设置';
                case 'device': return '设备设置';
                case 'notification': return '通知设置';
                case 'security': return '安全设置';
                case 'system': return '系统信息';
                default: return '设置';
            }
        },
        saveSettings() {
            console.log('保存设置:', this.settings);
            alert('设置已保存');
            // 这里实现保存设置的逻辑
        },
        resetSettings() {
            if (confirm('确定要重置所有设置到默认值吗？')) {
                console.log('重置设置');
                // 这里实现重置设置的逻辑
            }
        },
        changePassword() {
            if (!this.passwordForm.current || !this.passwordForm.new || !this.passwordForm.confirm) {
                alert('请填写所有密码字段');
                return;
            }

            if (this.passwordForm.new !== this.passwordForm.confirm) {
                alert('两次输入的新密码不一致');
                return;
            }

            console.log('修改密码');
            alert('密码已修改');

            // 清空表单
            this.passwordForm = {
                current: '',
                new: '',
                confirm: ''
            };
        },
        checkForUpdates() {
            console.log('检查更新');
            alert('您的软件已是最新版本');
        },
        openLogDirectory() {
            console.log('打开日志目录:', this.settings.system.logDirectory);
            // 这里实现打开日志目录的逻辑
        },
        downloadLogs() {
            console.log('下载日志文件');
            // 这里实现下载日志文件的逻辑
        }
    }
};