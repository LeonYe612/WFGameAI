// 脚本管理组件
const ScriptManagement = {
    template: `
        <div>
            <div class="row mb-3">
                <div class="col">
                    <div class="card">
                        <div class="card-header d-flex justify-content-between align-items-center">
                            <h5 class="card-title mb-0">脚本列表</h5>
                            <div class="action-buttons">
                                <button class="btn btn-primary btn-sm" @click="showCreateModal">
                                    <i class="fa fa-plus"></i> 新增脚本
                                </button>
                                <button class="btn btn-outline-secondary btn-sm ms-2">
                                    <i class="fa fa-upload"></i> 导入
                                </button>
                            </div>
                        </div>
                        <div class="card-body">
                            <div class="filters mb-3">
                                <div class="row">
                                    <div class="col-lg-3 col-md-4 mb-2">
                                        <input type="text" class="form-control form-control-sm" placeholder="搜索脚本..." v-model="searchQuery">
                                    </div>
                                    <div class="col-lg-2 col-md-3 mb-2">
                                        <select class="form-select form-select-sm" v-model="typeFilter">
                                            <option value="">所有类型</option>
                                            <option value="普通脚本">普通脚本</option>
                                            <option value="优先级脚本">优先级脚本</option>
                                            <option value="AI增强脚本">AI增强脚本</option>
                                        </select>
                                    </div>
                                    <div class="col-lg-2 col-md-3 mb-2">
                                        <select class="form-select form-select-sm" v-model="statusFilter">
                                            <option value="">所有状态</option>
                                            <option value="active">启用</option>
                                            <option value="inactive">禁用</option>
                                        </select>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="table-responsive">
                                <table class="table table-hover">
                                    <thead>
                                        <tr>
                                            <th>ID</th>
                                            <th>脚本名称</th>
                                            <th>类型</th>
                                            <th>步骤数</th>
                                            <th>最后修改</th>
                                            <th>版本</th>
                                            <th>状态</th>
                                            <th>操作</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr v-for="script in filteredScripts" :key="script.id">
                                            <td>#{{ script.id }}</td>
                                            <td>{{ script.name }}</td>
                                            <td>{{ script.type }}</td>
                                            <td>{{ script.steps }}</td>
                                            <td>{{ script.lastModified }}</td>
                                            <td>{{ script.version }}</td>
                                            <td>
                                                <span :class="script.status === 'active' ? 'badge bg-success' : 'badge bg-secondary'">
                                                    {{ script.status === 'active' ? '启用' : '禁用' }}
                                                </span>
                                            </td>
                                            <td>
                                                <div class="table-actions">
                                                    <button class="action-btn view" title="查看" @click="viewScript(script)">
                                                        <i class="fa fa-eye"></i>
                                                    </button>
                                                    <button class="action-btn edit" title="编辑" @click="editScript(script)">
                                                        <i class="fa fa-edit"></i>
                                                    </button>
                                                    <button class="action-btn run" title="运行" @click="runScript(script)">
                                                        <i class="fa fa-play"></i>
                                                    </button>
                                                    <button class="action-btn delete" title="删除" @click="deleteScript(script)">
                                                        <i class="fa fa-trash"></i>
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                            
                            <div class="pagination-wrapper d-flex justify-content-between align-items-center mt-3">
                                <div class="page-info">显示 {{ scripts.length }} 条中的 {{ filteredScripts.length }} 条</div>
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
            
            <!-- 创建脚本模态框 -->
            <div class="modal fade" id="createScriptModal" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">创建新脚本</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="关闭"></button>
                        </div>
                        <div class="modal-body">
                            <form>
                                <div class="mb-3">
                                    <label class="form-label">脚本名称</label>
                                    <input type="text" class="form-control" v-model="newScript.name">
                                </div>
                                <div class="row mb-3">
                                    <div class="col-md-6">
                                        <label class="form-label">脚本类型</label>
                                        <select class="form-select" v-model="newScript.type">
                                            <option value="普通脚本">普通脚本</option>
                                            <option value="优先级脚本">优先级脚本</option>
                                            <option value="AI增强脚本">AI增强脚本</option>
                                        </select>
                                    </div>
                                    <div class="col-md-6">
                                        <label class="form-label">版本</label>
                                        <input type="text" class="form-control" v-model="newScript.version">
                                    </div>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">脚本描述</label>
                                    <textarea class="form-control" rows="3" v-model="newScript.description"></textarea>
                                </div>
                                
                                <h6 class="mt-4 mb-3">步骤定义</h6>
                                <div class="step-wrapper mb-3" v-for="(step, index) in newScript.steps" :key="index">
                                    <div class="step-header d-flex justify-content-between align-items-center mb-2">
                                        <h6 class="mb-0">步骤 {{ index + 1 }}</h6>
                                        <button type="button" class="btn btn-sm btn-outline-danger" @click="removeStep(index)">删除</button>
                                    </div>
                                    <div class="step-body p-3 border rounded">
                                        <div class="row mb-3">
                                            <div class="col-md-6">
                                                <label class="form-label">动作类型</label>
                                                <select class="form-select" v-model="step.type">
                                                    <option value="点击">点击</option>
                                                    <option value="滑动">滑动</option>
                                                    <option value="输入">输入</option>
                                                    <option value="等待">等待</option>
                                                    <option value="验证">验证</option>
                                                    <option value="AI识别">AI识别</option>
                                                </select>
                                            </div>
                                            <div class="col-md-6">
                                                <label class="form-label">目标元素</label>
                                                <input type="text" class="form-control" v-model="step.target">
                                            </div>
                                        </div>
                                        <div class="mb-3" v-if="step.type === '输入'">
                                            <label class="form-label">输入内容</label>
                                            <input type="text" class="form-control" v-model="step.text">
                                        </div>
                                        <div class="mb-3" v-if="step.type === '等待'">
                                            <label class="form-label">等待时间 (毫秒)</label>
                                            <input type="number" class="form-control" v-model="step.duration">
                                        </div>
                                        <div class="mb-3" v-if="step.type === 'AI识别'">
                                            <label class="form-label">识别目标</label>
                                            <select class="form-select" v-model="step.aiTarget">
                                                <option value="文本">文本</option>
                                                <option value="图像">图像</option>
                                                <option value="控件">控件</option>
                                            </select>
                                        </div>
                                    </div>
                                </div>
                                <button type="button" class="btn btn-sm btn-outline-primary" @click="addStep">
                                    <i class="fa fa-plus"></i> 添加步骤
                                </button>
                            </form>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                            <button type="button" class="btn btn-primary" @click="createScript">保存</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            scripts: [],
            searchQuery: '',
            typeFilter: '',
            statusFilter: '',
            newScript: {
                name: '',
                type: '普通脚本',
                version: '1.0.0',
                description: '',
                steps: [
                    {
                        type: '点击',
                        target: '',
                        text: '',
                        duration: 1000,
                        aiTarget: ''
                    }
                ]
            },
            createModal: null
        };
    },
    computed: {
        filteredScripts() {
            return this.scripts.filter(script => {
                const matchesSearch = script.name.toLowerCase().includes(this.searchQuery.toLowerCase());
                const matchesType = this.typeFilter ? script.type === this.typeFilter : true;
                const matchesStatus = this.statusFilter ? script.status === this.statusFilter : true;
                return matchesSearch && matchesType && matchesStatus;
            });
        }
    },
    mounted() {
        this.loadScripts();
        this.createModal = new bootstrap.Modal(document.getElementById('createScriptModal'));
    },
    methods: {
        async loadScripts() {
            try {
                const response = await api.request('/scripts');
                this.scripts = response.data;
            } catch (error) {
                console.error('加载脚本失败:', error);
            }
        },
        showCreateModal() {
            this.createModal.show();
        },
        addStep() {
            this.newScript.steps.push({
                type: '点击',
                target: '',
                text: '',
                duration: 1000,
                aiTarget: ''
            });
        },
        removeStep(index) {
            this.newScript.steps.splice(index, 1);
        },
        createScript() {
            // 这里实现创建脚本的逻辑
            console.log('创建脚本:', this.newScript);
            this.createModal.hide();
            
            // 重置表单
            this.newScript = {
                name: '',
                type: '普通脚本',
                version: '1.0.0',
                description: '',
                steps: [
                    {
                        type: '点击',
                        target: '',
                        text: '',
                        duration: 1000,
                        aiTarget: ''
                    }
                ]
            };
        },
        viewScript(script) {
            console.log('查看脚本:', script);
        },
        editScript(script) {
            console.log('编辑脚本:', script);
        },
        runScript(script) {
            console.log('运行脚本:', script);
            Router.navigate('tasks');
        },
        deleteScript(script) {
            if (confirm(`确定要删除脚本 "${script.name}" 吗？`)) {
                console.log('删除脚本:', script);
                // 这里实现删除脚本的逻辑
            }
        }
    }
}; 