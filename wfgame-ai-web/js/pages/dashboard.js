// 仪表盘组件
const Dashboard = {
    template: `
        <div>
            <div class="row">
                <div class="col col-3">
                    <div class="stat-card">
                        <div class="stat-icon primary">
                            <i class="fa fa-mobile-alt"></i>
                        </div>
                        <div class="stat-content">
                            <h3 class="stat-value">12</h3>
                            <p class="stat-label">设备总数</p>
                            <div class="stat-trend up">
                                <i class="fa fa-arrow-up"></i> +2
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col col-3">
                    <div class="stat-card">
                        <div class="stat-icon success">
                            <i class="fa fa-code"></i>
                        </div>
                        <div class="stat-content">
                            <h3 class="stat-value">156</h3>
                            <p class="stat-label">脚本总数</p>
                            <div class="stat-trend up">
                                <i class="fa fa-arrow-up"></i> +15
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col col-3">
                    <div class="stat-card">
                        <div class="stat-icon info">
                            <i class="fa fa-play"></i>
                        </div>
                        <div class="stat-content">
                            <h3 class="stat-value">38</h3>
                            <p class="stat-label">今日任务</p>
                            <div class="stat-trend up">
                                <i class="fa fa-arrow-up"></i> +5
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col col-3">
                    <div class="stat-card">
                        <div class="stat-icon warning">
                            <i class="fa fa-check"></i>
                        </div>
                        <div class="stat-content">
                            <h3 class="stat-value">92.7%</h3>
                            <p class="stat-label">成功率</p>
                            <div class="stat-trend up">
                                <i class="fa fa-arrow-up"></i> +0.5%
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="row">
                <div class="col col-8">
                    <div class="card">
                        <div class="card-header">
                            <h5 class="card-title">测试执行趋势</h5>
                        </div>
                        <div class="card-body">
                            <div id="trendChart" style="height: 300px;"></div>
                        </div>
                    </div>
                </div>
                <div class="col col-4">
                    <div class="card">
                        <div class="card-header">
                            <h5 class="card-title">设备状态</h5>
                        </div>
                        <div class="card-body">
                            <div id="deviceChart" style="height: 300px;"></div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="row">
                <div class="col col-12">
                    <div class="card">
                        <div class="card-header">
                            <h5 class="card-title">最近执行的测试</h5>
                        </div>
                        <div class="card-body">
                            <div class="table-responsive">
                                <table class="table">
                                    <thead>
                                        <tr>
                                            <th>ID</th>
                                            <th>任务名称</th>
                                            <th>执行时间</th>
                                            <th>设备</th>
                                            <th>状态</th>
                                            <th>操作</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                            <td>#1001</td>
                                            <td>登录场景测试</td>
                                            <td>2025-05-12 15:48:46</td>
                                            <td>OnePlus-KB2000</td>
                                            <td><span class="badge bg-success">通过</span></td>
                                            <td>
                                                <div class="table-actions">
                                                    <button class="action-btn view"><i class="fa fa-eye"></i></button>
                                                    <button class="action-btn edit"><i class="fa fa-play"></i></button>
                                                </div>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td>#1002</td>
                                            <td>引导流程验证</td>
                                            <td>2025-05-12 14:30:21</td>
                                            <td>OPPO-Find X3</td>
                                            <td><span class="badge bg-warning">部分通过</span></td>
                                            <td>
                                                <div class="table-actions">
                                                    <button class="action-btn view"><i class="fa fa-eye"></i></button>
                                                    <button class="action-btn edit"><i class="fa fa-play"></i></button>
                                                </div>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td>#1003</td>
                                            <td>多脚本顺序执行</td>
                                            <td>2025-05-12 13:15:09</td>
                                            <td>Samsung-S21</td>
                                            <td><span class="badge bg-danger">失败</span></td>
                                            <td>
                                                <div class="table-actions">
                                                    <button class="action-btn view"><i class="fa fa-eye"></i></button>
                                                    <button class="action-btn edit"><i class="fa fa-play"></i></button>
                                                </div>
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `,
    mounted() {
        this.initCharts();
    },
    methods: {
        initCharts() {
            // 初始化趋势图表
            const trendChart = echarts.init(document.getElementById('trendChart'));
            trendChart.setOption({
                tooltip: {
                    trigger: 'axis'
                },
                legend: {
                    data: ['执行数', '成功数', '失败数']
                },
                grid: {
                    left: '3%',
                    right: '4%',
                    bottom: '3%',
                    containLabel: true
                },
                xAxis: {
                    type: 'category',
                    boundaryGap: false,
                    data: ['5/5', '5/6', '5/7', '5/8', '5/9', '5/10', '5/11', '5/12']
                },
                yAxis: {
                    type: 'value'
                },
                series: [
                    {
                        name: '执行数',
                        type: 'line',
                        smooth: true,
                        data: [35, 38, 42, 37, 45, 40, 43, 38]
                    },
                    {
                        name: '成功数',
                        type: 'line',
                        smooth: true,
                        data: [30, 32, 37, 32, 40, 36, 39, 35]
                    },
                    {
                        name: '失败数',
                        type: 'line',
                        smooth: true,
                        data: [5, 6, 5, 5, 5, 4, 4, 3]
                    }
                ]
            });

            // 初始化设备状态图表
            const deviceChart = echarts.init(document.getElementById('deviceChart'));
            deviceChart.setOption({
                tooltip: {
                    trigger: 'item',
                    formatter: '{a} <br/>{b}: {c} ({d}%)'
                },
                legend: {
                    orient: 'vertical',
                    right: 10,
                    top: 'center',
                    data: ['空闲', '执行中', '离线', '故障']
                },
                series: [
                    {
                        name: '设备状态',
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
                            { value: 7, name: '空闲', itemStyle: { color: '#4cc9f0' } },
                            { value: 3, name: '执行中', itemStyle: { color: '#4361ee' } },
                            { value: 1, name: '离线', itemStyle: { color: '#a5a5a5' } },
                            { value: 1, name: '故障', itemStyle: { color: '#ff4d6d' } }
                        ]
                    }
                ]
            });

            // 监听窗口大小变化，调整图表尺寸
            window.addEventListener('resize', () => {
                trendChart.resize();
                deviceChart.resize();
            });
        }
    }
};
