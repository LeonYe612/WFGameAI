// 数据驱动组件
const DataDriven = {
    template: `
        <div>
            <div class="row mb-3">
                <div class="col-md-4">
                    <div class="card">
                        <div class="card-header">
                            <h5 class="card-title mb-0">数据集</h5>
                        </div>
                        <div class="card-body">
                            <div class="dataset-filter mb-3">
                                <div class="input-group input-group-sm">
                                    <input type="text" class="form-control" placeholder="搜索数据集..." v-model="datasetSearchQuery">
                                    <button class="btn btn-outline-secondary" type="button">
                                        <i class="fa fa-search"></i>
                                    </button>
                                </div>
                            </div>

                            <div class="dataset-list">
                                <div class="list-group">
                                    <a href="#" class="list-group-item list-group-item-action"
                                       v-for="dataset in filteredDatasets"
                                       :key="dataset.id"
                                       :class="{'active': selectedDataset && selectedDataset.id === dataset.id}"
                                       @click.prevent="selectDataset(dataset)">
                                        <div class="d-flex w-100 justify-content-between">
                                            <h6 class="mb-1">{{ dataset.name }}</h6>
                                            <small>{{ dataset.itemCount }}项</small>
                                        </div>
                                        <p class="mb-1 small">{{ dataset.description }}</p>
                                        <small>{{ dataset.lastUpdated }}</small>
                                    </a>
                                </div>
                            </div>

                            <div class="dataset-actions mt-3">
                                <button class="btn btn-primary btn-sm" @click="showCreateDatasetModal">
                                    <i class="fa fa-plus"></i> 新建数据集
                                </button>
                                <button class="btn btn-outline-secondary btn-sm ms-2" @click="importDataset">
                                    <i class="fa fa-upload"></i> 导入
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="col-md-8">
                    <div class="card" v-if="selectedDataset">
                        <div class="card-header d-flex justify-content-between align-items-center">
                            <h5 class="card-title mb-0">{{ selectedDataset.name }}</h5>
                            <div class="action-buttons">
                                <button class="btn btn-primary btn-sm" @click="showAddDataModal">
                                    <i class="fa fa-plus"></i> 添加数据
                                </button>
                                <button class="btn btn-outline-secondary btn-sm ms-2" @click="exportDataset">
                                    <i class="fa fa-download"></i> 导出
                                </button>
                            </div>
                        </div>
                        <div class="card-body">
                            <div class="dataset-description mb-3">
                                <p>{{ selectedDataset.description }}</p>
                            </div>

                            <div class="data-filter d-flex mb-3">
                                <div class="me-3">
                                    <select class="form-select form-select-sm" v-model="dataTypeFilter">
                                        <option value="">所有类型</option>
                                        <option value="text">文本</option>
                                        <option value="image">图片</option>
                                        <option value="json">JSON</option>
                                    </select>
                                </div>
                                <div class="ms-auto">
                                    <div class="input-group input-group-sm">
                                        <input type="text" class="form-control" placeholder="搜索数据..." v-model="dataSearchQuery">
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
                                            <th>ID</th>
                                            <th>名称</th>
                                            <th>类型</th>
                                            <th>标签</th>
                                            <th>上传时间</th>
                                            <th>操作</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr v-for="item in filteredData" :key="item.id">
                                            <td>#{{ item.id }}</td>
                                            <td>{{ item.name }}</td>
                                            <td>
                                                <span :class="getDataTypeBadgeClass(item.type)">
                                                    {{ getDataTypeText(item.type) }}
                                                </span>
                                            </td>
                                            <td>
                                                <span class="badge bg-secondary me-1" v-for="(tag, index) in item.tags" :key="index">
                                                    {{ tag }}
                                                </span>
                                            </td>
                                            <td>{{ item.uploadTime }}</td>
                                            <td>
                                                <div class="table-actions">
                                                    <button class="action-btn view" title="查看" @click="viewData(item)">
                                                        <i class="fa fa-eye"></i>
                                                    </button>
                                                    <button class="action-btn edit" title="编辑" @click="editData(item)">
                                                        <i class="fa fa-edit"></i>
                                                    </button>
                                                    <button class="action-btn delete" title="删除" @click="deleteData(item)">
                                                        <i class="fa fa-trash"></i>
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>

                            <div class="pagination-wrapper d-flex justify-content-between align-items-center mt-3">
                                <div class="page-info">显示 {{ filteredData.length }} / {{ dataItems.length }} 条数据</div>
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

                    <div class="card" v-else>
                        <div class="card-body text-center py-5">
                            <i class="fa fa-database fa-3x text-muted mb-3"></i>
                            <h5>请选择数据集</h5>
                            <p class="text-muted">从左侧选择一个数据集，或创建新的数据集</p>
                            <button class="btn btn-primary" @click="showCreateDatasetModal">
                                <i class="fa fa-plus"></i> 创建数据集
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 数据预览弹窗 -->
            <div class="modal fade" id="dataPreviewModal" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">数据预览: {{ selectedDataItem ? selectedDataItem.name : '' }}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body" v-if="selectedDataItem">
                            <div class="data-info mb-3">
                                <div class="row">
                                    <div class="col-md-6">
                                        <p><strong>ID:</strong> #{{ selectedDataItem.id }}</p>
                                        <p><strong>名称:</strong> {{ selectedDataItem.name }}</p>
                                        <p><strong>类型:</strong> {{ getDataTypeText(selectedDataItem.type) }}</p>
                                    </div>
                                    <div class="col-md-6">
                                        <p><strong>上传时间:</strong> {{ selectedDataItem.uploadTime }}</p>
                                        <p><strong>标签:</strong>
                                            <span class="badge bg-secondary me-1" v-for="(tag, index) in selectedDataItem.tags" :key="index">
                                                {{ tag }}
                                            </span>
                                        </p>
                                    </div>
                                </div>
                            </div>

                            <h6>数据内容</h6>
                            <div class="data-preview p-3 border rounded bg-light">
                                <!-- 图片类型 -->
                                <div v-if="selectedDataItem.type === 'image'" class="text-center">
                                    <img :src="selectedDataItem.content" alt="图片数据" class="img-fluid">
                                </div>

                                <!-- 文本类型 -->
                                <div v-else-if="selectedDataItem.type === 'text'" class="text-content">
                                    {{ selectedDataItem.content }}
                                </div>

                                <!-- JSON类型 -->
                                <div v-else-if="selectedDataItem.type === 'json'" class="json-content">
                                    <pre>{{ formatJson(selectedDataItem.content) }}</pre>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 创建数据集模态框 -->
            <div class="modal fade" id="createDatasetModal" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">创建数据集</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <div class="mb-3">
                                <label class="form-label">数据集名称</label>
                                <input type="text" class="form-control" v-model="newDataset.name">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">描述</label>
                                <textarea class="form-control" rows="3" v-model="newDataset.description"></textarea>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">数据集类型</label>
                                <select class="form-select" v-model="newDataset.type">
                                    <option value="text">文本数据集</option>
                                    <option value="image">图片数据集</option>
                                    <option value="mixed">混合数据集</option>
                                </select>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                            <button type="button" class="btn btn-primary" @click="createDataset">创建</button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 添加数据模态框 -->
            <div class="modal fade" id="addDataModal" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">添加数据</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <div class="mb-3">
                                <label class="form-label">数据名称</label>
                                <input type="text" class="form-control" v-model="newData.name">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">数据类型</label>
                                <select class="form-select" v-model="newData.type">
                                    <option value="text">文本</option>
                                    <option value="image">图片</option>
                                    <option value="json">JSON</option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">标签 (用逗号分隔)</label>
                                <input type="text" class="form-control" v-model="newData.tagsString">
                            </div>
                            <div class="mb-3" v-if="newData.type === 'text'">
                                <label class="form-label">文本内容</label>
                                <textarea class="form-control" rows="5" v-model="newData.content"></textarea>
                            </div>
                            <div class="mb-3" v-if="newData.type === 'json'">
                                <label class="form-label">JSON内容</label>
                                <textarea class="form-control" rows="5" v-model="newData.content"></textarea>
                            </div>
                            <div class="mb-3" v-if="newData.type === 'image'">
                                <label class="form-label">上传图片</label>
                                <input type="file" class="form-control" accept="image/*">
                                <div class="form-text">支持JPG、PNG格式，最大5MB</div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                            <button type="button" class="btn btn-primary" @click="addData">添加</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            datasets: [
                { id: 1, name: '游戏场景文本', description: '包含游戏中各种场景的文本数据', itemCount: 42, lastUpdated: '2025-05-10' },
                { id: 2, name: '界面元素识别', description: '游戏界面UI元素截图集合', itemCount: 78, lastUpdated: '2025-05-08' },
                { id: 3, name: '战斗系统参数', description: '战斗系统相关的JSON参数数据', itemCount: 15, lastUpdated: '2025-05-05' }
            ],
            datasetSearchQuery: '',
            selectedDataset: null,
            dataItems: [
                { id: 1, name: '登录按钮', type: 'image', tags: ['UI', '按钮', '登录'], uploadTime: '2025-05-10 14:30', content: 'images/data/login_button.png' },
                { id: 2, name: '错误提示文本', type: 'text', tags: ['错误', '提示'], uploadTime: '2025-05-09 15:45', content: '登录失败，请检查您的账号和密码是否正确。' },
                { id: 3, name: '角色属性配置', type: 'json', tags: ['配置', '角色'], uploadTime: '2025-05-08 09:20', content: '{"id": 1, "name": "战士", "hp": 1000, "attack": 85, "defense": 60}' },
                { id: 4, name: '主菜单按钮', type: 'image', tags: ['UI', '按钮', '菜单'], uploadTime: '2025-05-07 16:10', content: 'images/data/main_menu.png' },
                { id: 5, name: '欢迎消息', type: 'text', tags: ['消息', '欢迎'], uploadTime: '2025-05-06 11:35', content: '欢迎回到游戏世界，冒险者！今天有新的任务等待着你。' }
            ],
            dataTypeFilter: '',
            dataSearchQuery: '',
            selectedDataItem: null,
            dataPreviewModal: null,
            createDatasetModal: null,
            addDataModal: null,
            newDataset: {
                name: '',
                description: '',
                type: 'text'
            },
            newData: {
                name: '',
                type: 'text',
                tagsString: '',
                content: ''
            }
        };
    },
    computed: {
        filteredDatasets() {
            return this.datasets.filter(dataset => {
                return dataset.name.toLowerCase().includes(this.datasetSearchQuery.toLowerCase()) ||
                       dataset.description.toLowerCase().includes(this.datasetSearchQuery.toLowerCase());
            });
        },
        filteredData() {
            if (!this.selectedDataset) return [];

            return this.dataItems.filter(item => {
                const matchesType = this.dataTypeFilter ? item.type === this.dataTypeFilter : true;

                const matchesSearch = this.dataSearchQuery ?
                    item.name.toLowerCase().includes(this.dataSearchQuery.toLowerCase()) ||
                    item.tags.some(tag => tag.toLowerCase().includes(this.dataSearchQuery.toLowerCase())) :
                    true;

                return matchesType && matchesSearch;
            });
        }
    },
    mounted() {
        this.dataPreviewModal = new bootstrap.Modal(document.getElementById('dataPreviewModal'));
        this.createDatasetModal = new bootstrap.Modal(document.getElementById('createDatasetModal'));
        this.addDataModal = new bootstrap.Modal(document.getElementById('addDataModal'));

        // 默认选中第一个数据集
        if (this.datasets.length > 0) {
            this.selectDataset(this.datasets[0]);
        }
    },
    methods: {
        selectDataset(dataset) {
            this.selectedDataset = dataset;
        },
        importDataset() {
            console.log('导入数据集');
            // 这里实现导入数据集的逻辑
        },
        exportDataset() {
            console.log('导出数据集:', this.selectedDataset);
            // 这里实现导出数据集的逻辑
        },
        getDataTypeBadgeClass(type) {
            switch (type) {
                case 'text': return 'badge bg-primary';
                case 'image': return 'badge bg-success';
                case 'json': return 'badge bg-warning';
                default: return 'badge bg-secondary';
            }
        },
        getDataTypeText(type) {
            switch (type) {
                case 'text': return '文本';
                case 'image': return '图片';
                case 'json': return 'JSON';
                default: return '未知';
            }
        },
        viewData(item) {
            this.selectedDataItem = item;
            this.dataPreviewModal.show();
        },
        editData(item) {
            console.log('编辑数据:', item);
            // 这里实现编辑数据的逻辑
        },
        deleteData(item) {
            if (confirm(`确定要删除数据 "${item.name}" 吗？`)) {
                console.log('删除数据:', item);
                // 这里实现删除数据的逻辑
            }
        },
        formatJson(jsonString) {
            try {
                const parsedJson = JSON.parse(jsonString);
                return JSON.stringify(parsedJson, null, 2);
            } catch (e) {
                return jsonString;
            }
        },
        showCreateDatasetModal() {
            this.createDatasetModal.show();
        },
        createDataset() {
            console.log('创建数据集:', this.newDataset);
            // 这里实现创建数据集的逻辑

            // 模拟创建
            const newId = this.datasets.length + 1;
            const dataset = {
                id: newId,
                name: this.newDataset.name,
                description: this.newDataset.description,
                type: this.newDataset.type,
                itemCount: 0,
                lastUpdated: new Date().toISOString().split('T')[0]
            };

            this.datasets.push(dataset);
            this.selectDataset(dataset);

            // 重置表单
            this.newDataset = {
                name: '',
                description: '',
                type: 'text'
            };

            this.createDatasetModal.hide();
        },
        showAddDataModal() {
            this.addDataModal.show();
        },
        addData() {
            console.log('添加数据:', this.newData);

            // 处理标签
            const tags = this.newData.tagsString.split(',')
                .map(tag => tag.trim())
                .filter(tag => tag !== '');

            // 模拟添加数据
            const newId = this.dataItems.length + 1;
            const newItem = {
                id: newId,
                name: this.newData.name,
                type: this.newData.type,
                tags: tags,
                uploadTime: new Date().toLocaleString(),
                content: this.newData.content
            };

            this.dataItems.push(newItem);

            // 更新数据集计数
            if (this.selectedDataset) {
                this.selectedDataset.itemCount++;
                this.selectedDataset.lastUpdated = new Date().toISOString().split('T')[0];
            }

            // 重置表单
            this.newData = {
                name: '',
                type: 'text',
                tagsString: '',
                content: ''
            };

            this.addDataModal.hide();
        }
    }
};