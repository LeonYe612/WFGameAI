// OCR历史记录组件
const OCRHistoryView = {
    template: `
        <div>
            <div class="row mb-3">
                <div class="col">
                    <div class="card">
                        <div class="card-header d-flex justify-content-between align-items-center">
                            <h5 class="card-title mb-0">OCR历史记录</h5>
                            <div class="action-buttons">
                                <button class="btn btn-outline-secondary btn-sm">
                                    <i class="fa fa-file-export"></i> 导出全部
                                </button>
                            </div>
                        </div>
                        <div class="card-body">
                            <div class="filters mb-3">
                                <div class="row">
                                    <div class="col-lg-3 col-md-4 mb-2">
                                        <input type="text" class="form-control form-control-sm" placeholder="搜索任务..." v-model="searchQuery">
                                    </div>
                                    <div class="col-lg-2 col-md-3 mb-2">
                                        <select class="form-select form-select-sm" v-model="projectFilter">
                                            <option value="">所有项目</option>
                                            <option v-for="project in projects" :key="project.id" :value="project.id">
                                                {{ project.name }}
                                            </option>
                                        </select>
                                    </div>
                                    <div class="col-lg-2 col-md-3 mb-2">
                                        <select class="form-select form-select-sm" v-model="statusFilter">
                                            <option value="">所有状态</option>
                                            <option value="completed">已完成</option>
                                            <option value="processing">处理中</option>
                                            <option value="failed">失败</option>
                                            <option value="pending">等待中</option>
                                        </select>
                                    </div>
                                </div>
                            </div>

                            <div class="table-responsive">
                                <table class="table table-hover">
                                    <thead>
                                        <tr>
                                            <th>ID</th>
                                            <th>项目</th>
                                            <th>来源类型</th>
                                            <th>总图片数</th>
                                            <th>匹配图片数</th>
                                            <th>匹配率</th>
                                            <th>创建时间</th>
                                            <th>状态</th>
                                            <th>操作</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr v-for="task in filteredTasks" :key="task.id">
                                            <td>{{ task.id }}</td>
                                            <td>{{ task.project_name }}</td>
                                            <td>{{ getSourceTypeName(task.source_type) }}</td>
                                            <td>{{ task.total_images }}</td>
                                            <td>{{ task.matched_images }}</td>
                                            <td>
                                                <div class="progress" style="height: 8px; width: 80px;">
                                                    <div class="progress-bar" role="progressbar"
                                                         :style="{width: task.match_rate + '%'}"
                                                         :class="getMatchRateClass(task.match_rate)">
                                                    </div>
                                                </div>
                                                <small>{{ task.match_rate }}%</small>
                                            </td>
                                            <td>{{ formatDate(task.created_at) }}</td>
                                            <td>
                                                <span :class="getStatusBadgeClass(task.status)">
                                                    {{ getStatusName(task.status) }}
                                                </span>
                                            </td>
                                            <td>
                                                <div class="table-actions">
                                                    <button class="action-btn view" title="查看" @click="viewTask(task)">
                                                        <i class="fa fa-eye"></i>
                                                    </button>
                                                    <button class="action-btn download" title="下载" @click="downloadResults(task)">
                                                        <i class="fa fa-download"></i>
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
                                <div class="page-info">显示 {{ filteredTasks.length }} 条中的 {{ tasks.length }} 条</div>
                                <ul class="pagination pagination-sm">
                                    <li class="page-item" :class="{ disabled: currentPage === 1 }">
                                        <a class="page-link" href="#" @click.prevent="changePage(currentPage - 1)">上一页</a>
                                    </li>
                                    <li v-for="page in totalPages" :key="page" class="page-item" :class="{ active: currentPage === page }">
                                        <a class="page-link" href="#" @click.prevent="changePage(page)">{{ page }}</a>
                                    </li>
                                    <li class="page-item" :class="{ disabled: currentPage === totalPages }">
                                        <a class="page-link" href="#" @click.prevent="changePage(currentPage + 1)">下一页</a>
                                    </li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 任务详情模态框 -->
            <div class="modal fade" id="taskDetailModal" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">任务详情</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="关闭"></button>
                        </div>
                        <div class="modal-body" v-if="selectedTask">
                            <div class="task-header mb-4">
                                <div class="row">
                                    <div class="col-md-6">
                                        <h6>基本信息</h6>
                                        <table class="table table-sm">
                                            <tr>
                                                <th width="30%">任务ID</th>
                                                <td>{{ selectedTask.id }}</td>
                                            </tr>
                                            <tr>
                                                <th>项目</th>
                                                <td>{{ selectedTask.project_name }}</td>
                                            </tr>
                                            <tr>
                                                <th>来源类型</th>
                                                <td>{{ getSourceTypeName(selectedTask.source_type) }}</td>
                                            </tr>
                                            <tr>
                                                <th>创建时间</th>
                                                <td>{{ formatDate(selectedTask.created_at) }}</td>
                                            </tr>
                                        </table>
                                    </div>
                                    <div class="col-md-6">
                                        <h6>处理结果</h6>
                                        <table class="table table-sm">
                                            <tr>
                                                <th width="30%">总图片数</th>
                                                <td>{{ selectedTask.total_images }}</td>
                                            </tr>
                                            <tr>
                                                <th>匹配图片数</th>
                                                <td>{{ selectedTask.matched_images }}</td>
                                            </tr>
                                            <tr>
                                                <th>匹配率</th>
                                                <td>{{ selectedTask.match_rate }}%</td>
                                            </tr>
                                            <tr>
                                                <th>状态</th>
                                                <td>
                                                    <span :class="getStatusBadgeClass(selectedTask.status)">
                                                        {{ getStatusName(selectedTask.status) }}
                                                    </span>
                                                </td>
                                            </tr>
                                        </table>
                                    </div>
                                </div>
                            </div>

                            <div class="task-results mb-4" v-if="selectedTask.results && selectedTask.results.length">
                                <h6>识别结果</h6>
                                <div class="table-responsive">
                                    <table class="table table-sm">
                                        <thead>
                                            <tr>
                                                <th>图片路径</th>
                                                <th>识别文本</th>
                                                <th>语言</th>
                                                <th>是否匹配</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <tr v-for="(result, index) in selectedTask.results" :key="index">
                                                <td>{{ result.image_path }}</td>
                                                <td>{{ result.texts.join(', ') }}</td>
                                                <td>{{ result.pic_resolution }}</td>
                                                <td>{{ Object.keys(result.languages).join(', ') }}</td>
                                                <td>
                                                    <span :class="result.has_match ? 'badge bg-success' : 'badge bg-secondary'">
                                                        {{ result.has_match ? '是' : '否' }}
                                                    </span>
                                                </td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                            </div>

                            <div class="task-report mb-4" v-if="selectedTask.report">
                                <h6>汇总报告</h6>
                                <div class="report-content p-3 border bg-light">
                                    <pre>{{ selectedTask.report.content }}</pre>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                            <button type="button" class="btn btn-primary" @click="downloadResults(selectedTask)">下载结果</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            tasks: [],
            projects: [],
            searchQuery: '',
            projectFilter: '',
            statusFilter: '',
            currentPage: 1,
            pageSize: 10,
            selectedTask: null,
            taskDetailModal: null
        };
    },
    computed: {
        filteredTasks() {
            return this.tasks.filter(task => {
                const matchesSearch = this.searchQuery ?
                    task.id.toLowerCase().includes(this.searchQuery.toLowerCase()) :
                    true;
                const matchesProject = this.projectFilter ?
                    task.project === parseInt(this.projectFilter) :
                    true;
                const matchesStatus = this.statusFilter ?
                    task.status === this.statusFilter :
                    true;

                return matchesSearch && matchesProject && matchesStatus;
            });
        },
        paginatedTasks() {
            const start = (this.currentPage - 1) * this.pageSize;
            const end = start + this.pageSize;
            return this.filteredTasks.slice(start, end);
        },
        totalPages() {
            return Math.ceil(this.filteredTasks.length / this.pageSize);
        }
    },
    mounted() {
        this.loadTasks();
        this.loadProjects();
        this.taskDetailModal = new bootstrap.Modal(document.getElementById('taskDetailModal'));
    },
    methods: {
        async loadTasks() {
            try {
                const response = await fetch('/api/ocr/history/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        action: 'list'
                    })
                });

                if (response.ok) {
                    const data = await response.json();
                    this.tasks = data.tasks || [];
                } else {
                    console.error('加载OCR任务失败:', response.statusText);
                }
            } catch (error) {
                console.error('加载OCR任务失败:', error);
            }
        },
        async loadProjects() {
            try {
                const response = await fetch('/api/ocr/projects/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        action: 'list'
                    })
                });

                if (response.ok) {
                    const data = await response.json();
                    this.projects = data || [];
                } else {
                    console.error('加载OCR项目失败:', response.statusText);
                }
            } catch (error) {
                console.error('加载OCR项目失败:', error);
            }
        },
        getSourceTypeName(type) {
            const types = {
                'git': 'Git仓库',
                'upload': '本地上传'
            };
            return types[type] || type;
        },
        getStatusName(status) {
            const statuses = {
                'pending': '等待中',
                'processing': '处理中',
                'completed': '已完成',
                'failed': '失败'
            };
            return statuses[status] || status;
        },
        getStatusBadgeClass(status) {
            const classes = {
                'pending': 'badge bg-warning',
                'processing': 'badge bg-info',
                'completed': 'badge bg-success',
                'failed': 'badge bg-danger'
            };
            return classes[status] || 'badge bg-secondary';
        },
        getMatchRateClass(rate) {
            if (rate >= 90) return 'bg-success';
            if (rate >= 70) return 'bg-warning';
            return 'bg-danger';
        },
        formatDate(dateString) {
            if (!dateString) return '';
            const date = new Date(dateString);
            return date.toLocaleString();
        },
        changePage(page) {
            if (page < 1 || page > this.totalPages) return;
            this.currentPage = page;
        },
        async viewTask(task) {
            try {
                const response = await fetch('/api/ocr/tasks/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        action: 'get',
                        id: task.id
                    })
                });

                if (response.ok) {
                    const data = await response.json();
                    this.selectedTask = data;
                    this.taskDetailModal.show();
                } else {
                    console.error('获取任务详情失败:', response.statusText);
                }
            } catch (error) {
                console.error('获取任务详情失败:', error);
            }
        },
        downloadResults(task) {
            // 创建下载链接
            const url = `/api/ocr/history/`;

            // 创建表单数据
            const formData = {
                action: 'download',
                task_id: task.id
            };

            // 使用POST请求下载CSV文件
            fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            })
                .then(response => {
                    if (!response.ok) {
                        throw new Error('下载失败');
                    }
                    return response.blob();
                })
                .then(blob => {
                    // 创建下载链接
                    const downloadUrl = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = downloadUrl;
                    a.download = `${task.name || task.id}.csv`;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(downloadUrl);
                    a.remove();
                })
                .catch(error => {
                    console.error('下载失败:', error);
                    alert('下载失败，请稍后重试');
                });
        },
        deleteTask(task) {
            if (confirm(`确定要删除任务 "${task.id}" 吗？`)) {
                fetch('/api/ocr/tasks/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        action: 'delete',
                        id: task.id
                    })
                })
                    .then(response => {
                        if (response.ok) {
                            // 从列表中移除任务
                            this.tasks = this.tasks.filter(t => t.id !== task.id);
                            alert('任务删除成功');
                        } else {
                            alert('删除任务失败，请稍后重试');
                        }
                    })
                    .catch(error => {
                        console.error('删除任务失败:', error);
                        alert('删除任务失败，请稍后重试');
                    });
            }
        }
    }
};