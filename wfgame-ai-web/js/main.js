// 主应用脚本
const app = new Vue({
    el: '#app',
    template: `
        <div class="app-container" :class="{'loading': loading}">
            <!-- 加载中遮罩 -->
            <div class="loading-overlay" v-if="loading">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">加载中...</span>
                </div>
            </div>

            <!-- 侧边栏 -->
            <div class="sidebar">
                <div class="sidebar-header">
                    <div class="logo">
                        <img src="images/logo.png" alt="WFGame AI">
                        <span>WFGame AI</span>
                    </div>
                </div>
                <div class="sidebar-menu">
                    <ul>
                        <li :class="{active: currentPage === 'dashboard'}">
                            <a href="#/dashboard">
                                <i class="fa fa-tachometer-alt"></i>
                                <span>仪表盘</span>
                            </a>
                        </li>
                        <li :class="{active: currentPage === 'scripts'}">
                            <a href="#/scripts">
                                <i class="fa fa-code"></i>
                                <span>脚本管理</span>
                            </a>
                        </li>
                        <li :class="{active: currentPage === 'tasks'}">
                            <a href="#/tasks">
                                <i class="fa fa-tasks"></i>
                                <span>测试任务</span>
                            </a>
                        </li>
                        <li :class="{active: currentPage === 'devices'}">
                            <a href="#/devices">
                                <i class="fa fa-mobile-alt"></i>
                                <span>设备管理</span>
                            </a>
                        </li>
                        <li :class="{active: currentPage === 'reports'}">
                            <a href="#/reports">
                                <i class="fa fa-chart-bar"></i>
                                <span>报告中心</span>
                            </a>
                        </li>
                        <li :class="{active: currentPage === 'ocr_history'}">
                            <a href="#/ocr_history">
                                <i class="fa fa-file-alt"></i>
                                <span>OCR历史</span>
                            </a>
                        </li>
                        <li :class="{active: currentPage === 'data'}">
                            <a href="#/data">
                                <i class="fa fa-database"></i>
                                <span>数据驱动</span>
                            </a>
                        </li>
                        <li :class="{active: currentPage === 'settings'}">
                            <a href="#/settings">
                                <i class="fa fa-cog"></i>
                                <span>系统设置</span>
                            </a>
                        </li>
                    </ul>
                </div>
            </div>

            <!-- 主内容区 -->
            <div class="main-content">
                <!-- 顶部导航 -->
                <div class="top-navbar">
                    <div class="page-title">
                        <h1>{{ pageTitle }}</h1>
                    </div>
                    <div class="navbar-right">
                        <div class="notifications">
                            <i class="fa fa-bell"></i>
                            <span class="badge">3</span>
                        </div>
                        <div class="user-profile" @click="showUserMenu = !showUserMenu">
                            <img src="images/avatar.png" alt="用户头像">
                            <span>管理员</span>
                            <i class="fa fa-chevron-down"></i>

                            <!-- 用户菜单 -->
                            <div class="user-menu" v-show="showUserMenu">
                                <ul>
                                    <li><a href="#"><i class="fa fa-user"></i> 个人资料</a></li>
                                    <li><a href="#"><i class="fa fa-cog"></i> 账号设置</a></li>
                                    <li><a href="#" @click="logout"><i class="fa fa-sign-out-alt"></i> 退出登录</a></li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 组件内容区 -->
                <div class="content-wrapper">
                    <component :is="currentComponent"></component>
                </div>
            </div>
        </div>
    `,
    data: {
        loading: true,
        currentPage: 'dashboard',
        pageTitle: '仪表盘',
        showUserMenu: false
    },
    computed: {
        currentComponent() {
            // 根据当前页面返回对应组件
            switch (this.currentPage) {
                case 'dashboard': return Dashboard;
                case 'scripts': return ScriptManagement;
                case 'tasks': return TestTasks;
                case 'devices': return DeviceManagement;
                case 'reports': return ReportCenter;
                case 'data': return DataDriven;
                case 'settings': return SystemSettings;
                case 'ocr_history': return OCRHistoryView;
                default: return Dashboard;
            }
        }
    },
    created() {
        // 监听哈希变化
        window.addEventListener('hashchange', this.handleRouteChange);
        // 初始路由处理（解决刷新或首次访问时的路由问题）
        this.handleRouteChange();

        // 模拟加载延迟
        setTimeout(() => {
            this.loading = false;
        }, 800);
    },
    methods: {
        handleRouteChange() {
            const hash = window.location.hash;
            if (!hash) {
                this.currentPage = 'dashboard';
                this.pageTitle = '仪表盘';
                return;
            }

            const route = hash.slice(2); // 移除 #/
            switch (route) {
                case 'dashboard':
                    this.currentPage = 'dashboard';
                    this.pageTitle = '仪表盘';
                    break;
                case 'scripts':
                    this.currentPage = 'scripts';
                    this.pageTitle = '脚本管理';
                    break;
                case 'tasks':
                    this.currentPage = 'tasks';
                    this.pageTitle = '测试任务';
                    break;
                case 'devices':
                    this.currentPage = 'devices';
                    this.pageTitle = '设备管理';
                    break;
                case 'reports':
                    this.currentPage = 'reports';
                    this.pageTitle = '报告中心';
                    break;
                case 'data':
                    this.currentPage = 'data';
                    this.pageTitle = '数据驱动';
                    break;
                case 'settings':
                    this.currentPage = 'settings';
                    this.pageTitle = '系统设置';
                    break;
                case 'ocr_history':
                    this.currentPage = 'ocr_history';
                    this.pageTitle = 'OCR历史记录';
                    break;
                default:
                    this.currentPage = 'dashboard';
                    this.pageTitle = '仪表盘';
            }

            // 关闭用户菜单
            this.showUserMenu = false;
        },
        logout() {
            // 模拟登出操作
            alert('退出登录');
            window.location.href = 'pages/login.html';
        }
    }
});
