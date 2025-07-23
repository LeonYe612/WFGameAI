/**
 * OCR模块API封装
 * 提供与后端OCR API交互的函数
 */

const OCRAPI = {
    // 项目相关API
    projects: {
        list: async function () {
            return await sendRequest('/api/ocr/projects/', {
                action: 'list'
            });
        },
        create: async function (name, description) {
            return await sendRequest('/api/ocr/projects/', {
                action: 'create',
                name: name,
                description: description
            });
        },
        get: async function (id) {
            return await sendRequest('/api/ocr/projects/', {
                action: 'get',
                id: id
            });
        },
        delete: async function (id) {
            return await sendRequest('/api/ocr/projects/', {
                action: 'delete',
                id: id
            });
        }
    },

    // Git仓库相关API
    repositories: {
        list: async function (projectId) {
            return await sendRequest('/api/ocr/repositories/', {
                action: 'list',
                project_id: projectId
            });
        },
        create: async function (projectId, url, branch) {
            return await sendRequest('/api/ocr/repositories/', {
                action: 'create',
                project: projectId,
                url: url,
                branch: branch || 'main'
            });
        },
        delete: async function (id) {
            return await sendRequest('/api/ocr/repositories/', {
                action: 'delete',
                id: id
            });
        },
        getBranches: async function (id) {
            return await sendRequest('/api/ocr/repositories/', {
                action: 'get_branches',
                id: id
            });
        }
    },

    // 任务相关API
    tasks: {
        list: async function (projectId) {
            return await sendRequest('/api/ocr/tasks/', {
                action: 'list',
                project_id: projectId || null
            });
        },
        create: async function (data) {
            return await sendRequest('/api/ocr/tasks/', {
                action: 'create',
                ...data
            });
        },
        get: async function (id) {
            return await sendRequest('/api/ocr/tasks/', {
                action: 'get',
                id: id
            });
        },
        delete: async function (id) {
            return await sendRequest('/api/ocr/tasks/', {
                action: 'delete',
                id: id
            });
        },
        getDetails: async function (id, page, pageSize) {
            return await sendRequest('/api/ocr/tasks/', {
                action: 'get_details',
                id: id,
                page: page || 1,
                page_size: pageSize || 20
            });
        },
        export: function (id, format) {
            // 直接返回下载URL
            return `/api/ocr/tasks/?action=export&id=${id}&format=${format}`;
        }
    },

    // 结果相关API
    results: {
        list: async function (taskId) {
            return await sendRequest('/api/ocr/results/', {
                action: 'list',
                task_id: taskId
            });
        },
        get: async function (id) {
            return await sendRequest('/api/ocr/results/', {
                action: 'get',
                id: id
            });
        },
        search: async function (taskId, query, onlyMatched, page, pageSize) {
            return await sendRequest('/api/ocr/results/', {
                action: 'search',
                task_id: taskId,
                query: query || '',
                only_matched: onlyMatched || false,
                page: page || 1,
                page_size: pageSize || 20
            });
        }
    },

    // 文件上传API
    upload: async function (formData) {
        return await fetch('/api/ocr/upload/', {
            method: 'POST',
            body: formData
        }).then(handleResponse);
    },

    // 处理API
    process: {
        git: async function (projectId, repoId, branch, languages, useGpu, gpuId) {
            return await sendRequest('/api/ocr/process/', {
                action: 'process_git',
                project_id: projectId,
                repo_id: repoId,
                branch: branch || 'main',
                languages: languages || ['ch'],
                use_gpu: useGpu !== false,
                gpu_id: gpuId || 0
            });
        }
    },

    // 历史记录API
    history: async function (projectId, dateFrom, dateTo, page, pageSize) {
        return await sendRequest('/api/ocr/history/', {
            project_id: projectId || null,
            date_from: dateFrom || null,
            date_to: dateTo || null,
            page: page || 1,
            page_size: pageSize || 20
        });
    }
};

/**
 * 发送请求
 */
async function sendRequest(url, data) {
    return await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    }).then(handleResponse);
}

/**
 * 处理响应
 */
async function handleResponse(response) {
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `状态码: ${response.status}`);
    }
    return await response.json();
}

// 导出API
window.OCRAPI = OCRAPI;