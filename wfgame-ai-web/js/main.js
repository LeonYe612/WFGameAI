// 主应用脚本
const app = new Vue({
    el: '#app',
    data: {
        loading: true,
        currentPage: 'dashboard',
        pageTitle: '仪表盘',
        showUserMenu: false
    },
    computed: {
        currentComponent() {
            // 根据当前页面返回对应组件
            switch(this.currentPage) {
                case 'dashboard': return Dashboard;
                case 'scripts': return ScriptManagement;
                case 'tasks': return TestTasks;
                case 'devices': return DeviceManagement;
                case 'reports': return ReportCenter;
                case 'data': return DataDriven;
                case 'settings': return SystemSettings;
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
            switch(route) {
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
