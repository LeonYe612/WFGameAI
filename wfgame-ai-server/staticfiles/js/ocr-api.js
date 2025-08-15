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
        create: async function (projectId, url, branch, token, skipSSLVerify) {
            return await sendRequest('/api/ocr/repositories/', {
                action: 'create',
                project: projectId,
                url: url,
                branch: branch || 'main',
                token: token,
                skip_ssl_verify: skipSSLVerify
            });
        },
        delete: async function (id) {
            return await sendRequest('/api/ocr/repositories/', {
                action: 'delete',
                id: id
            });
        },
        getBranches: async function (id, skipSSLVerify) {
            return await sendRequest('/api/ocr/repositories/', {
                action: 'get_branches',
                id: id,
                skip_ssl_verify: skipSSLVerify
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
        git: async function (projectId, repoId, branch, languages, token, skipSSLVerify) {
            return await sendRequest('/api/ocr/process/', {
                action: 'process_git',
                project_id: projectId,
                repo_id: repoId,
                branch: branch || 'main',
                languages: languages || ['ch'],
                token: token,
                skip_ssl_verify: skipSSLVerify
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
        try {
            // 尝试解析为JSON
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `状态码: ${response.status}`);
            } else {
                // 非JSON响应（可能是HTML等）
                const textContent = await response.text();
                console.error('服务器返回非JSON响应:', textContent.substring(0, 200));
                throw new Error(`服务器错误(${response.status})，请联系管理员检查服务器日志`);
            }
        } catch (parseError) {
            if (parseError.message.includes('服务器错误')) {
                throw parseError;
            } else {
                console.error('处理响应错误:', parseError);
                throw new Error(`解析响应失败: ${response.status} ${response.statusText}`);
            }
        }
    }

    try {
        return await response.json();
    } catch (error) {
        console.error('解析JSON响应失败:', error);
        throw new Error('无法解析服务器响应');
    }
}

// 导出API
window.OCRAPI = OCRAPI;