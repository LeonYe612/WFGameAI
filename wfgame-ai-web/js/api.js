// API调用服务
const api = {
    baseUrl: 'http://localhost:8000/api',

    // 封装请求方法
    async request(endpoint, method = 'GET', data = null) {
        const url = `${this.baseUrl}${endpoint}`;
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.getToken()}`
            }
        };

        if (data && (method === 'POST' || method === 'PUT')) {
            options.body = JSON.stringify(data);
        }

        try {
            // 这里仅为演示，实际项目中应使用真实API
            console.log(`模拟API请求: ${method} ${url}`);
            console.log('请求数据:', data);

            // 返回模拟数据
            return await this.getMockData(endpoint);
        } catch (error) {
            console.error('API请求错误:', error);
            throw error;
        }
    },

    // 获取存储的Token
    getToken() {
        return localStorage.getItem('auth_token') || '';
    },

    // 模拟数据方法
    async getMockData(endpoint) {
        // 根据不同endpoint返回不同的模拟数据
        if (endpoint.includes('/scripts')) {
            return {
                status: 'success',
                data: [
                    { id: 1, name: '登录场景测试', type: '普通脚本', steps: 7, lastModified: '2025-05-10', version: '1.0.3', status: 'active' },
                    { id: 2, name: '引导流程验证', type: '优先级脚本', steps: 12, lastModified: '2025-05-08', version: '2.1.0', status: 'active' },
                    { id: 3, name: '多脚本顺序执行', type: '普通脚本', steps: 15, lastModified: '2025-05-05', version: '1.2.1', status: 'inactive' }
                ]
            };
        } else if (endpoint.includes('/devices')) {
            return {
                status: 'success',
                data: [
                    { id: 1, name: 'OnePlus-KB2000', model: 'OnePlus', resolution: '1080x2400', status: 'online', lastActivity: '10分钟前' },
                    { id: 2, name: 'OPPO-Find X3', model: 'OPPO', resolution: '1080x2400', status: 'executing', lastActivity: '正在执行' },
                    { id: 3, name: 'Samsung-S21', model: 'Samsung', resolution: '1440x3200', status: 'offline', lastActivity: '3小时前' }
                ]
            };
        } else if (endpoint.includes('/tasks')) {
            return {
                status: 'success',
                data: [
                    { id: 1, name: '登录场景测试', script: 'scene1_login_steps.json', device: 'OnePlus-KB2000', startTime: '2025-05-12 15:48:46', status: 'completed', progress: '100%' },
                    { id: 2, name: '引导流程验证', script: 'scene2_guide_steps.json', device: 'OPPO-Find X3', startTime: '2025-05-12 14:30:21', status: 'executing', progress: '65%' },
                    { id: 3, name: '多脚本顺序执行', script: 'multiple_scripts.json', device: 'Samsung-S21', startTime: '2025-05-12 13:15:09', status: 'failed', progress: '47%' }
                ]
            };
        } else if (endpoint.includes('/reports')) {
            return {
                status: 'success',
                data: [
                    { id: 1, name: '登录场景测试报告', devices: 3, executionTime: '2025-05-12 15:48:46', successRate: '92%', passRate: '87%' },
                    { id: 2, name: '引导流程验证报告', devices: 2, executionTime: '2025-05-12 14:30:21', successRate: '78%', passRate: '71%' },
                    { id: 3, name: '多脚本执行报告', devices: 5, executionTime: '2025-05-12 13:15:09', successRate: '65%', passRate: '58%' }
                ]
            };
        } else {
            return {
                status: 'success',
                data: []
            };
        }
    }
};
