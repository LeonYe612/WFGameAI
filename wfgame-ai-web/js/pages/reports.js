// 报告中心组件
const ReportCenter = {
    template: `
        <div>
            <div class="row mb-3">
                <div class="col">
                    <div class="card">
                        <div class="card-header d-flex justify-content-between align-items-center">
                            <h5 class="card-title mb-0">测试报告列表</h5>
                            <div class="action-buttons">
                                <button class="btn btn-outline-secondary btn-sm">
                                    <i class="fa fa-file-export"></i> 导出
                                </button>
                            </div>
                        </div>
                        <div class="card-body">
                            <div class="report-filters d-flex flex-wrap align-items-center mb-3">
                                <div class="me-3 mb-2">
                                    <div class="input-group input-group-sm">
                                        <span class="input-group-text">开始日期</span>
                                        <input type="date" class="form-control" v-model="startDate">
                                    </div>
                                </div>
                                <div class="me-3 mb-2">
                                    <div class="input-group input-group-sm">
                                        <span class="input-group-text">结束日期</span>
                                        <input type="date" class="form-control" v-model="endDate">
                                    </div>
                                </div>
                                <div class="me-3 mb-2">
                                    <select class="form-select form-select-sm" v-model="selectedPassRate">
                                        <option value="">所有通过率</option>
                                        <option value="high">高 (>90%)</option>
                                        <option value="medium">中 (70%-90%)</option>
                                        <option value="low">低 (<70%)</option>
                                    </select>
                                </div>
                                <div class="ms-auto mb-2">
                                    <div class="input-group input-group-sm">
                                        <input type="text" class="form-control" placeholder="搜索报告..." v-model="searchQuery">
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
                                            <th>报告名称</th>
                                            <th>设备数量</th>
                                            <th>执行时间</th>
                                            <th>成功率</th>
                                            <th>通过率</th>
                                            <th>操作</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr v-for="report in filteredReports" :key="report.id">
                                            <td>#{{ report.id }}</td>
                                            <td>{{ report.name }}</td>
                                            <td>{{ report.devices }}</td>
                                            <td>{{ report.executionTime }}</td>
                                            <td>
                                                <div class="progress" style="height: 8px; width: 80px;">
                                                    <div class="progress-bar" role="progressbar"
                                                         :style="{width: report.successRate}"
                                                         :class="getSuccessRateClass(report.successRate)">
                                                    </div>
                                                </div>
                                                <small>{{ report.successRate }}</small>
                                            </td>
                                            <td>
                                                <div class="progress" style="height: 8px; width: 80px;">
                                                    <div class="progress-bar" role="progressbar"
                                                         :style="{width: report.passRate}"
                                                         :class="getPassRateClass(report.passRate)">
                                                    </div>
                                                </div>
                                                <small>{{ report.passRate }}</small>
                                            </td>
                                            <td>
                                                <div class="table-actions">
                                                    <button class="action-btn view" title="查看" @click="viewReport(report)">
                                                        <i class="fa fa-eye"></i>
                                                    </button>
                                                    <button class="action-btn download" title="下载" @click="downloadReport(report)">
                                                        <i class="fa fa-download"></i>
                                                    </button>
                                                    <button class="action-btn delete" title="删除" @click="deleteReport(report)">
                                                        <i class="fa fa-trash"></i>
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>

                            <div class="pagination-wrapper d-flex justify-content-between align-items-center mt-3">
                                <div class="page-info">显示 {{ filteredReports.length }} / {{ reports.length }} 条报告</div>
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

            <!-- 报告详情 -->
            <div class="row" v-if="selectedReport">
                <div class="col">
                    <div class="card">
                        <div class="card-header d-flex justify-content-between align-items-center">
                            <h5 class="card-title mb-0">报告详情: {{ selectedReport.name }}</h5>
                            <div>
                                <button class="btn btn-sm btn-outline-secondary me-2" @click="printReport">
                                    <i class="fa fa-print"></i> 打印
                                </button>
                                <button type="button" class="btn-close" @click="selectedReport = null"></button>
                            </div>
                        </div>
                        <div class="card-body">
                            <div class="report-header mb-4">
                                <div class="row">
                                    <div class="col-md-6">
                                        <h6>基本信息</h6>
                                        <table class="table table-sm">
                                            <tr>
                                                <th width="25%">报告ID</th>
                                                <td>#{{ selectedReport.id }}</td>
                                            </tr>
                                            <tr>
                                                <th>报告名称</th>
                                                <td>{{ selectedReport.name }}</td>
                                            </tr>
                                            <tr>
                                                <th>执行时间</th>
                                                <td>{{ selectedReport.executionTime }}</td>
                                            </tr>
                                            <tr>
                                                <th>测试设备数</th>
                                                <td>{{ selectedReport.devices }}</td>
                                            </tr>
                                        </table>
                                    </div>
                                    <div class="col-md-6">
                                        <h6>测试结果概览</h6>
                                        <div class="row">
                                            <div class="col-md-6 mb-3">
                                                <div class="report-stat-card">
                                                    <h6 class="stat-label">总用例数</h6>
                                                    <div class="stat-value">24</div>
                                                </div>
                                            </div>
                                            <div class="col-md-6 mb-3">
                                                <div class="report-stat-card">
                                                    <h6 class="stat-label">通过数</h6>
                                                    <div class="stat-value text-success">19</div>
                                                </div>
                                            </div>
                                            <div class="col-md-6 mb-3">
                                                <div class="report-stat-card">
                                                    <h6 class="stat-label">失败数</h6>
                                                    <div class="stat-value text-danger">3</div>
                                                </div>
                                            </div>
                                            <div class="col-md-6 mb-3">
                                                <div class="report-stat-card">
                                                    <h6 class="stat-label">跳过数</h6>
                                                    <div class="stat-value text-muted">2</div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div class="report-charts mb-4">
                                <div class="row">
                                    <div class="col-md-6">
                                        <div class="card">
                                            <div class="card-header">
                                                <h6 class="card-title mb-0">测试结果分布</h6>
                                            </div>
                                            <div class="card-body">
                                                <div id="resultDistributionChart" style="height: 250px;"></div>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="card">
                                            <div class="card-header">
                                                <h6 class="card-title mb-0">执行时间分布</h6>
                                            </div>
                                            <div class="card-body">
                                                <div id="executionTimeChart" style="height: 250px;"></div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div class="report-details mb-4">
                                <h6>设备测试详情</h6>
                                <div class="table-responsive">
                                    <table class="table table-sm">
                                        <thead>
                                            <tr>
                                                <th>设备</th>
                                                <th>执行脚本</th>
                                                <th>开始时间</th>
                                                <th>结束时间</th>
                                                <th>总步骤</th>
                                                <th>通过数</th>
                                                <th>失败数</th>
                                                <th>状态</th>
                                                <th>详情</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <tr v-for="(device, index) in reportDevices" :key="index">
                                                <td>{{ device.name }}</td>
                                                <td>{{ device.script }}</td>
                                                <td>{{ device.startTime }}</td>
                                                <td>{{ device.endTime }}</td>
                                                <td>{{ device.totalSteps }}</td>
                                                <td>{{ device.passedSteps }}</td>
                                                <td>{{ device.failedSteps }}</td>
                                                <td>
                                                    <span :class="getDeviceStatusBadgeClass(device.status)">
                                                        {{ device.status }}
                                                    </span>
                                                </td>
                                                <td>
                                                    <button class="btn btn-sm btn-outline-primary" @click="showDeviceDetail(device)">
                                                        <i class="fa fa-eye"></i>
                                                    </button>
                                                </td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                            </div>

                            <div class="report-failures mb-4">
                                <h6>失败详情分析</h6>
                                <div class="accordion" id="failureAccordion">
                                    <div class="accordion-item" v-for="(failure, index) in failureDetails" :key="index">
                                        <h2 class="accordion-header">
                                            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" :data-bs-target="'#failure' + index">
                                                <span class="badge bg-danger me-2">失败</span>
                                                {{ failure.device }} - {{ failure.step }}
                                            </button>
                                        </h2>
                                        <div :id="'failure' + index" class="accordion-collapse collapse" data-bs-parent="#failureAccordion">
                                            <div class="accordion-body">
                                                <div class="row">
                                                    <div class="col-md-6">
                                                        <h6>错误信息</h6>
                                                        <div class="error-message p-2 border bg-light">
                                                            {{ failure.errorMessage }}
                                                        </div>
                                                        <h6 class="mt-3">失败原因分析</h6>
                                                        <p>{{ failure.analysis }}</p>
                                                    </div>
                                                    <div class="col-md-6">
                                                        <h6>截图</h6>
                                                        <div class="failure-screenshot border">
                                                            <img :src="failure.screenshot" alt="失败截图" class="img-fluid">
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div class="row">
                                <div class="col-12 d-flex justify-content-end">
                                    <button class="btn btn-secondary" @click="selectedReport = null">关闭</button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            reports: [],
            searchQuery: '',
            startDate: '',
            endDate: '',
            selectedPassRate: '',
            selectedReport: null,
            reportDevices: [
                { name: 'OnePlus-KB2000', script: 'login_steps.json', startTime: '2025-05-12 15:48:46', endTime: '2025-05-12 15:50:12', totalSteps: 7, passedSteps: 7, failedSteps: 0, status: '通过' },
                { name: 'OPPO-Find X3', script: 'login_steps.json', startTime: '2025-05-12 15:48:46', endTime: '2025-05-12 15:50:38', totalSteps: 7, passedSteps: 5, failedSteps: 2, status: '失败' },
                { name: 'Samsung-S21', script: 'login_steps.json', startTime: '2025-05-12 15:48:46', endTime: '2025-05-12 15:49:59', totalSteps: 7, passedSteps: 7, failedSteps: 0, status: '通过' }
            ],
            failureDetails: [
                {
                    device: 'OPPO-Find X3',
                    step: '点击登录按钮',
                    errorMessage: 'Error: 未找到目标元素 "login_button"，等待超时。',
                    analysis: '可能是界面加载延迟导致元素未及时出现，建议增加等待时间或添加元素存在检查。',
                    screenshot: 'images/failure1.png'
                },
                {
                    device: 'OPPO-Find X3',
                    step: '等待登录完成',
                    errorMessage: 'Error: 登录失败，未检测到成功界面。',
                    analysis: '由于前一步骤失败，登录流程未完成，导致未能进入成功界面。',
                    screenshot: 'images/failure2.png'
                }
            ]
        };
    },
    computed: {
        filteredReports() {
            return this.reports.filter(report => {
                // 搜索筛选
                const matchesSearch = this.searchQuery ?
                    report.name.toLowerCase().includes(this.searchQuery.toLowerCase()) :
                    true;

                // 通过率筛选
                let matchesPassRate = true;
                if (this.selectedPassRate) {
                    const passRateValue = parseInt(report.passRate);
                    if (this.selectedPassRate === 'high') {
                        matchesPassRate = passRateValue > 90;
                    } else if (this.selectedPassRate === 'medium') {
                        matchesPassRate = passRateValue >= 70 && passRateValue <= 90;
                    } else if (this.selectedPassRate === 'low') {
                        matchesPassRate = passRateValue < 70;
                    }
                }

                // 日期范围筛选
                const reportDate = new Date(report.executionTime.split(' ')[0]);
                const matchesStartDate = this.startDate ? new Date(this.startDate) <= reportDate : true;
                const matchesEndDate = this.endDate ? new Date(this.endDate) >= reportDate : true;

                return matchesSearch && matchesPassRate && matchesStartDate && matchesEndDate;
            });
        }
    },
    mounted() {
        this.loadReports();
    },
    methods: {
        async loadReports() {
            try {
                const response = await api.request('/reports');
                this.reports = response.data;
            } catch (error) {
                console.error('加载报告失败:', error);
            }
        },
        getSuccessRateClass(rate) {
            const rateValue = parseInt(rate);
            if (rateValue >= 90) return 'bg-success';
            if (rateValue >= 70) return 'bg-warning';
            return 'bg-danger';
        },
        getPassRateClass(rate) {
            const rateValue = parseInt(rate);
            if (rateValue >= 90) return 'bg-success';
            if (rateValue >= 70) return 'bg-warning';
            return 'bg-danger';
        },
        getDeviceStatusBadgeClass(status) {
            switch (status) {
                case '通过': return 'badge bg-success';
                case '失败': return 'badge bg-danger';
                case '部分通过': return 'badge bg-warning';
                default: return 'badge bg-secondary';
            }
        },
        viewReport(report) {
            this.selectedReport = report;
            this.$nextTick(() => {
                this.initReportCharts();
            });
        },
        downloadReport(report) {
            console.log('下载报告:', report);
            // 这里实现下载报告的逻辑
        },
        deleteReport(report) {
            if (confirm(`确定要删除报告 "${report.name}" 吗？`)) {
                console.log('删除报告:', report);
                // 这里实现删除报告的逻辑
            }
        },
        showDeviceDetail(device) {
            console.log('显示设备详情:', device);
            // 这里实现显示设备详情的逻辑
        },
        printReport() {
            console.log('打印报告:', this.selectedReport);
            window.print();
        },
        initReportCharts() {
            // 初始化测试结果分布图表
            const resultDistributionChart = echarts.init(document.getElementById('resultDistributionChart'));
            resultDistributionChart.setOption({
                tooltip: {
                    trigger: 'item',
                    formatter: '{a} <br/>{b}: {c} ({d}%)'
                },
                legend: {
                    orient: 'vertical',
                    right: 10,
                    top: 'center',
                    data: ['通过', '失败', '跳过']
                },
                series: [
                    {
                        name: '测试结果',
                        type: 'pie',
                        radius: ['50%', '70%'],
                        avoidLabelOverlap: false,
                        label: {
                            show: false,
                            position: 'center'
                        },
                        emphasis: {
                            label: {
                                show: true,
                                fontSize: '18',
                                fontWeight: 'bold'
                            }
                        },
                        labelLine: {
                            show: false
                        },
                        data: [
                            { value: 19, name: '通过', itemStyle: { color: '#4cc9f0' } },
                            { value: 3, name: '失败', itemStyle: { color: '#f72585' } },
                            { value: 2, name: '跳过', itemStyle: { color: '#adb5bd' } }
                        ]
                    }
                ]
            });

            // 初始化执行时间分布图表
            const executionTimeChart = echarts.init(document.getElementById('executionTimeChart'));
            executionTimeChart.setOption({
                tooltip: {
                    trigger: 'axis'
                },
                xAxis: {
                    type: 'category',
                    data: ['OnePlus-KB2000', 'OPPO-Find X3', 'Samsung-S21']
                },
                yAxis: {
                    type: 'value',
                    name: '秒',
                    nameLocation: 'end'
                },
                series: [
                    {
                        name: '执行时间',
                        type: 'bar',
                        data: [86, 112, 73],
                        itemStyle: {
                            color: '#4361ee'
                        }
                    }
                ]
            });

            // 监听窗口大小变化，调整图表尺寸
            window.addEventListener('resize', () => {
                resultDistributionChart.resize();
                executionTimeChart.resize();
            });
        }
    }
};