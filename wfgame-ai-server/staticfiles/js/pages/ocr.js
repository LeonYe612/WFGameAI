/**
 * OCR模块前端JavaScript
 * 提供OCR识别页面的交互功能
 */

// 页面加载完成后执行初始化
document.addEventListener('DOMContentLoaded', function () {
    // 初始化上传功能
    initUploadFunctions();

    // 初始化项目管理功能
    initProjectManagement();

    // 初始化Git仓库功能
    initGitRepository();

    // 初始化Git仓库识别功能
    initGitOcrFunctions();

    // 初始化历史记录功能
    initHistoryRecords();

    // 加载项目列表
    loadProjects();

    console.log('OCR模块前端初始化完成');
});

/**
 * 初始化文件上传相关功能
 */
function initUploadFunctions() {
    const dropArea = document.getElementById('dropArea');
    const fileInput = document.getElementById('fileInput');
    const selectFileBtn = document.getElementById('selectFileBtn');
    const startOcrBtn = document.getElementById('startOcrBtn');

    if (!dropArea || !fileInput || !selectFileBtn || !startOcrBtn) {
        console.error('上传区域DOM元素不存在');
        return;
    }

    // 选择文件按钮点击事件
    selectFileBtn.addEventListener('click', function () {
        fileInput.click();
    });

    // 文件选择变化事件
    fileInput.addEventListener('change', function () {
        if (fileInput.files.length > 0) {
            startOcrBtn.disabled = false;
            updateUploadStatus(`已选择 ${fileInput.files.length} 个文件`);
        } else {
            startOcrBtn.disabled = true;
            updateUploadStatus('准备就绪，等待上传文件...');
        }
    });

    // 拖放区域事件
    dropArea.addEventListener('dragover', function (e) {
        e.preventDefault();
        dropArea.classList.add('border-primary');
    });

    dropArea.addEventListener('dragleave', function () {
        dropArea.classList.remove('border-primary');
    });

    dropArea.addEventListener('drop', function (e) {
        e.preventDefault();
        dropArea.classList.remove('border-primary');

        if (e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files;
            startOcrBtn.disabled = false;
            updateUploadStatus(`已拖入 ${fileInput.files.length} 个文件`);
        }
    });

    // 开始OCR识别按钮
    startOcrBtn.addEventListener('click', function () {
        uploadAndProcess();
    });
}

/**
 * 更新上传状态显示
 */
function updateUploadStatus(message, isError = false) {
    const statusDiv = document.getElementById('processStatus');
    if (!statusDiv) return;

    statusDiv.className = isError ? 'alert alert-danger' : 'alert alert-info';
    statusDiv.textContent = message;
}

/**
 * 上传文件并处理
 */
function uploadAndProcess() {
    const fileInput = document.getElementById('fileInput');
    const projectSelect = document.getElementById('projectSelect');

    if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
        updateUploadStatus('请先选择文件', true);
        return;
    }

    if (!projectSelect || !projectSelect.value) {
        updateUploadStatus('请选择项目', true);
        return;
    }

    // 获取选中的语言
    const selectedLanguages = [];
    document.querySelectorAll('input[id^="lang-"]:checked').forEach(function (checkbox) {
        selectedLanguages.push(checkbox.value);
    });

    if (selectedLanguages.length === 0) {
        updateUploadStatus('请至少选择一种语言', true);
        return;
    }

    // 准备表单数据
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('project_id', projectSelect.value);
    formData.append('languages', JSON.stringify(selectedLanguages));

    // 显示进度条
    document.getElementById('progressContainer').style.display = 'block';
    document.getElementById('progressBar').style.width = '10%';
    document.getElementById('progressBar').textContent = '10%';

    updateUploadStatus('正在上传文件，请稍候...');

    // 执行上传
    fetch('/api/ocr/upload/', {
        method: 'POST',
        body: formData
    })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.detail || '上传失败');
                });
            }
            return response.json();
        })
        .then(data => {
            updateUploadStatus('文件上传成功，正在处理...');
            document.getElementById('progressBar').style.width = '50%';
            document.getElementById('progressBar').textContent = '50%';

            // 轮询任务状态
            pollTaskStatus(data.task.id);
        })
        .catch(error => {
            updateUploadStatus(`上传失败: ${error.message}`, true);
            document.getElementById('progressContainer').style.display = 'none';
        });
}

/**
 * 轮询任务状态
 */
function pollTaskStatus(taskId) {
    const intervalId = setInterval(function () {
        fetch('/api/ocr/tasks/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                action: 'get',
                id: taskId
            })
        })
            .then(response => response.json())
            .then(data => {
                const status = data.status;

                if (status === 'completed') {
                    clearInterval(intervalId);
                    document.getElementById('progressBar').style.width = '100%';
                    document.getElementById('progressBar').textContent = '100%';

                    // 更新进度统计
                    document.getElementById('processedCount').textContent = data.total_images;
                    document.getElementById('totalCount').textContent = data.total_images;
                    document.getElementById('matchRate').textContent = `${data.match_rate.toFixed(1)}%`;

                    // 显示结果
                    updateUploadStatus('处理完成！');
                    showResults(data);

                } else if (status === 'failed') {
                    clearInterval(intervalId);
                    updateUploadStatus(`处理失败: ${data.error || '未知错误'}`, true);
                    document.getElementById('progressContainer').style.display = 'none';

                } else if (status === 'running') {
                    // 更新进度条
                    const progress = data.progress || 50;
                    document.getElementById('progressBar').style.width = `${progress}%`;
                    document.getElementById('progressBar').textContent = `${progress}%`;

                    // 更新进度统计
                    if (data.processed_count && data.total_count) {
                        document.getElementById('processedCount').textContent = data.processed_count;
                        document.getElementById('totalCount').textContent = data.total_count;
                        const matchRate = data.matched_count / data.processed_count * 100 || 0;
                        document.getElementById('matchRate').textContent = `${matchRate.toFixed(1)}%`;
                    }

                    updateUploadStatus('正在处理中，请稍候...');
                }
            })
            .catch(error => {
                console.error('轮询任务状态失败:', error);
            });
    }, 3000); // 每3秒检查一次
}

/**
 * 显示处理结果
 */
function showResults(data) {
    // 显示结果容器
    const resultsContainer = document.getElementById('resultsContainer');
    if (!resultsContainer) return;

    resultsContainer.style.display = 'block';

    // 更新结果摘要
    const resultsSummary = document.getElementById('resultsSummary');
    if (resultsSummary) {
        resultsSummary.innerHTML = `
            <h5>处理完成</h5>
            <p>总图片数: ${data.total_images}</p>
            <p>匹配图片: ${data.matched_images}</p>
            <p>匹配率: ${data.match_rate.toFixed(1)}%</p>
            <p>任务ID: ${data.id}</p>
        `;
    }

    // 查看详细结果按钮
    const viewDetailsBtn = document.getElementById('viewDetailsBtn');
    if (viewDetailsBtn) {
        viewDetailsBtn.onclick = function () {
            showDetailedResults(data.id);
        };
    }

    // 导出按钮
    setupExportButtons(data.id);
}

/**
 * 显示详细结果
 */
function showDetailedResults(taskId) {
    // 打开模态框
    const resultModal = new bootstrap.Modal(document.getElementById('resultModal'));
    resultModal.show();

    // 清空之前的结果
    const detailedResults = document.getElementById('detailedResults');
    if (detailedResults) {
        detailedResults.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div><p class="mt-2">正在加载结果...</p></div>';
    }

    // 加载详细结果
    fetch('/api/ocr/tasks/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            action: 'get_details',
            id: taskId,
            page: 1,
            page_size: 50
        })
    })
        .then(response => response.json())
        .then(data => {
            if (!data.results || !detailedResults) return;

            // 清空加载动画
            detailedResults.innerHTML = '';

            // 添加结果
            data.results.forEach(result => {
                const resultItem = document.createElement('div');
                resultItem.className = 'card result-card mb-3';

                // 使用完整的相对路径，而不是只取文件名
                const imagePath = result.image_path;
                const hasMatch = result.has_match ? 'text-success' : 'text-muted';
                const matchIcon = result.has_match ? 'check-circle' : 'times-circle';

                // 构建正确的图片URL - 确保不重复添加ocr/uploads/前缀
                // 直接使用/media/前缀 + 数据库中存储的相对路径
                const imageUrl = `/media/${imagePath}`;

                // 提取文件名用于显示
                const fileName = imagePath.split('/').pop();

                resultItem.innerHTML = `
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-3">
                            <img src="${imageUrl}" class="img-fluid result-image" onerror="this.onerror=null; this.src='/static/images/image-not-found.png'; this.alt='图片加载失败';" alt="图片预览">
                        </div>
                        <div class="col-md-9">
                            <h5 class="card-title">${fileName} <i class="fas fa-${matchIcon} ${hasMatch}"></i></h5>
                            <h6 class="card-subtitle mb-2 text-muted">语言: ${Object.keys(result.languages).join(', ')}</h6>
                            <div class="card-text">
                                <strong>识别文本:</strong>
                                <ul class="list-group mt-2">
                                    ${result.texts.map(text => `<li class="list-group-item">${text}</li>`).join('')}
                                </ul>
                            </div>
                            <div class="mt-2">
                                <small class="text-muted">完整路径: ${imagePath}</small>
                            </div>
                        </div>
                    </div>
                </div>
            `;

                detailedResults.appendChild(resultItem);
            });

            // 添加分页
            if (data.total_pages > 1) {
                const pagination = document.createElement('nav');
                pagination.innerHTML = `
                <ul class="pagination justify-content-center">
                    <li class="page-item ${data.page === 1 ? 'disabled' : ''}">
                        <a class="page-link" href="#" data-page="${data.page - 1}">上一页</a>
                    </li>
                    ${[...Array(data.total_pages).keys()].map(i => `
                        <li class="page-item ${data.page === i + 1 ? 'active' : ''}">
                            <a class="page-link" href="#" data-page="${i + 1}">${i + 1}</a>
                        </li>
                    `).join('')}
                    <li class="page-item ${data.page === data.total_pages ? 'disabled' : ''}">
                        <a class="page-link" href="#" data-page="${data.page + 1}">下一页</a>
                    </li>
                </ul>
            `;

                detailedResults.appendChild(pagination);

                // 添加分页点击事件
                pagination.querySelectorAll('.page-link').forEach(link => {
                    link.addEventListener('click', function (e) {
                        e.preventDefault();
                        const page = parseInt(this.getAttribute('data-page'));
                        loadResultsPage(taskId, page);
                    });
                });
            }
        })
        .catch(error => {
            console.error('加载详细结果失败:', error);
            if (detailedResults) {
                detailedResults.innerHTML = `<div class="alert alert-danger">加载失败: ${error.message}</div>`;
            }
        });
}

/**
 * 加载结果的特定页
 */
function loadResultsPage(taskId, page) {
    const detailedResults = document.getElementById('detailedResults');
    if (!detailedResults) return;

    detailedResults.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div><p class="mt-2">正在加载结果...</p></div>';

    fetch('/api/ocr/tasks/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            action: 'get_details',
            id: taskId,
            page: page,
            page_size: 50
        })
    })
        .then(response => response.json())
        .then(data => {
            showDetailedResults(taskId);
        })
        .catch(error => {
            console.error('加载结果页失败:', error);
        });
}

/**
 * 设置导出按钮功能
 */
function setupExportButtons(taskId) {
    const formats = ['json', 'csv', 'txt'];

    formats.forEach(format => {
        const exportBtn = document.getElementById(`export${format.charAt(0).toUpperCase() + format.slice(1)}`);
        if (exportBtn) {
            exportBtn.onclick = function (e) {
                e.preventDefault();
                window.location.href = `/api/ocr/tasks/?action=export&id=${taskId}&format=${format}`;
            };
        }
    });
}

/**
 * 初始化项目管理功能
 */
function initProjectManagement() {
    // 创建项目按钮点击事件
    const createProjectBtn = document.getElementById('createProjectBtn');
    if (createProjectBtn) {
        createProjectBtn.addEventListener('click', function () {
            const projectModal = new bootstrap.Modal(document.getElementById('projectModal'));
            projectModal.show();
        });
    }

    // 保存项目按钮点击事件
    const saveProjectBtn = document.getElementById('saveProjectBtn');
    if (saveProjectBtn) {
        saveProjectBtn.addEventListener('click', function () {
            const projectName = document.getElementById('projectName').value;
            const projectDescription = document.getElementById('projectDescription').value;

            if (!projectName) {
                alert('请输入项目名称');
                return;
            }

            createProject(projectName, projectDescription);
        });
    }
}

/**
 * 创建新项目
 */
function createProject(name, description) {
    fetch('/api/ocr/projects/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            action: 'create',
            name: name,
            description: description
        })
    })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.detail || '创建项目失败');
                });
            }
            return response.json();
        })
        .then(data => {
            // 关闭模态框
            bootstrap.Modal.getInstance(document.getElementById('projectModal')).hide();

            // 清空表单
            document.getElementById('projectName').value = '';
            document.getElementById('projectDescription').value = '';

            // 重新加载项目列表
            loadProjects();

            alert('项目创建成功');
        })
        .catch(error => {
            alert(`创建项目失败: ${error.message}`);
        });
}

/**
 * 加载项目列表
 */
function loadProjects() {
    fetch('/api/ocr/projects/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            action: 'list'
        })
    })
        .then(response => response.json())
        .then(data => {
            // 填充项目下拉框
            const projectSelects = [
                document.getElementById('projectSelect'),
                document.getElementById('repoProjectSelect'),
                document.getElementById('historyProjectFilter')
            ];

            projectSelects.forEach(select => {
                if (!select) return;

                // 保留第一个选项
                const firstOption = select.options[0];
                select.innerHTML = '';
                select.appendChild(firstOption);

                // 添加项目选项
                data.forEach((project, index) => {
                    const option = document.createElement('option');
                    option.value = project.id;
                    option.textContent = project.name;
                    select.appendChild(option);

                    // 如果是第一个项目且是项目选择下拉框，则自动选中
                    if (index === 0 && select.id === 'projectSelect') {
                        option.selected = true;
                        // 自动触发项目选择变化事件，加载仓库列表
                        if (select.dispatchEvent) {
                            const event = new Event('change');
                            select.dispatchEvent(event);
                        }
                    }
                });
            });

            // 填充项目表格
            const projectsTable = document.querySelector('#projectsTable tbody');
            if (projectsTable) {
                projectsTable.innerHTML = '';

                data.forEach(project => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                    <td>${project.id}</td>
                    <td>${project.name}</td>
                    <td>${project.description}</td>
                    <td>${new Date(project.created_at).toLocaleString()}</td>
                    <td>
                        <button class="btn btn-sm btn-danger delete-project" data-id="${project.id}">删除</button>
                    </td>
                `;
                    projectsTable.appendChild(row);
                });

                // 添加删除项目按钮点击事件
                projectsTable.querySelectorAll('.delete-project').forEach(button => {
                    button.addEventListener('click', function () {
                        const projectId = this.getAttribute('data-id');
                        if (confirm('确定要删除这个项目吗？')) {
                            deleteProject(projectId);
                        }
                    });
                });
            }
        })
        .catch(error => {
            console.error('加载项目列表失败:', error);
        });
}

/**
 * 删除项目
 */
function deleteProject(projectId) {
    fetch('/api/ocr/projects/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            action: 'delete',
            id: projectId
        })
    })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.detail || '删除项目失败');
                });
            }
            return response.json();
        })
        .then(data => {
            loadProjects();
            alert('项目删除成功');
        })
        .catch(error => {
            alert(`删除项目失败: ${error.message}`);
        });
}

/**
 * 初始化Git仓库功能
 */
function initGitRepository() {
    // 项目选择变化事件
    const repoProjectSelect = document.getElementById('repoProjectSelect');
    if (repoProjectSelect) {
        repoProjectSelect.addEventListener('change', function () {
            loadRepositories(this.value);
        });
    }

    // 添加仓库按钮点击事件
    const addRepoBtn = document.getElementById('addRepoBtn');
    if (addRepoBtn) {
        addRepoBtn.addEventListener('click', function () {
            const projectId = document.getElementById('repoProjectSelect').value;
            const repoUrl = document.getElementById('repoUrl').value;
            const repoBranch = document.getElementById('repoBranch').value;

            if (!projectId) {
                alert('请选择项目');
                return;
            }

            if (!repoUrl) {
                alert('请输入仓库URL');
                return;
            }

            addRepository(projectId, repoUrl, repoBranch);
        });
    }

    // 当项目选择变化时，启用/禁用添加仓库按钮
    document.getElementById('repoProjectSelect')?.addEventListener('change', function () {
        const addRepoBtn = document.getElementById('addRepoBtn');
        if (addRepoBtn) {
            addRepoBtn.disabled = !this.value;
        }
    });
}

/**
 * 加载仓库列表
 */
function loadRepositories(projectId) {
    if (!projectId) return;

    fetch('/api/ocr/repositories/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            action: 'list',
            project_id: projectId
        })
    })
        .then(response => response.json())
        .then(data => {
            const reposTable = document.querySelector('#reposTable tbody');
            if (!reposTable) return;

            reposTable.innerHTML = '';

            data.forEach(repo => {
                const row = document.createElement('tr');
                row.innerHTML = `
                <td>${repo.id}</td>
                <td>${repo.url}</td>
                <td>${repo.branch}</td>
                <td>
                    <button class="btn btn-sm btn-danger delete-repo" data-id="${repo.id}">删除</button>
                </td>
            `;
                reposTable.appendChild(row);
            });

            // 添加删除仓库按钮点击事件
            reposTable.querySelectorAll('.delete-repo').forEach(button => {
                button.addEventListener('click', function () {
                    const repoId = this.getAttribute('data-id');
                    if (confirm('确定要删除这个仓库吗？')) {
                        deleteRepository(repoId);
                    }
                });
            });
        })
        .catch(error => {
            console.error('加载仓库列表失败:', error);
        });
}

/**
 * 添加仓库
 */
function addRepository(projectId, url, branch) {
    const token = document.getElementById('repoToken')?.value || '';
    const skipSSLVerify = document.getElementById('skipSSLVerify')?.checked || false;

    fetch('/api/ocr/repositories/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            action: 'create',
            project: projectId,
            url: url,
            branch: branch || 'main',
            token: token,  // 添加令牌字段
            skip_ssl_verify: skipSSLVerify  // 添加跳过SSL验证字段
        })
    })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.detail || '添加仓库失败');
                });
            }
            return response.json();
        })
        .then(data => {
            // 清空表单
            document.getElementById('repoUrl').value = '';
            document.getElementById('repoBranch').value = 'main';
            if (document.getElementById('repoToken')) {
                document.getElementById('repoToken').value = '';
            }
            if (document.getElementById('skipSSLVerify')) {
                document.getElementById('skipSSLVerify').checked = false;
            }

            // 重新加载仓库列表
            loadRepositories(projectId);

            alert('仓库添加成功');
        })
        .catch(error => {
            alert(`添加仓库失败: ${error.message}`);
        });
}

/**
 * 删除仓库
 */
function deleteRepository(repoId) {
    fetch('/api/ocr/repositories/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            action: 'delete',
            id: repoId
        })
    })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.detail || '删除仓库失败');
                });
            }
            return response.json();
        })
        .then(data => {
            // 重新加载仓库列表
            const projectId = document.getElementById('repoProjectSelect').value;
            loadRepositories(projectId);

            alert('仓库删除成功');
        })
        .catch(error => {
            alert(`删除仓库失败: ${error.message}`);
        });
}

/**
 * 初始化Git仓库识别功能
 */
function initGitOcrFunctions() {
    // 项目选择器变化事件
    const projectSelect = document.getElementById('projectSelect');
    if (projectSelect) {
        projectSelect.addEventListener('change', function () {
            const projectId = this.value;
            const repoSelect = document.getElementById('repoSelect');

            if (!projectId) {
                // 如果没有选择项目，禁用仓库下拉框
                repoSelect.disabled = true;
                repoSelect.innerHTML = '<option value="" selected>请先选择项目...</option>';

                // 禁用分支下拉框
                const branchSelect = document.getElementById('branchSelect');
                branchSelect.disabled = true;
                branchSelect.innerHTML = '<option value="" selected>请先选择仓库...</option>';

                // 禁用开始识别按钮
                document.getElementById('startGitOcrBtn').disabled = true;
                return;
            }

            // 如果选择了项目，启用仓库下拉框，并加载仓库列表
            repoSelect.disabled = false;
            loadGitRepos(projectId);
        });
    }

    // 仓库选择器变化事件
    const repoSelect = document.getElementById('repoSelect');
    if (repoSelect) {
        repoSelect.addEventListener('change', function () {
            const repoId = this.value;
            const branchSelect = document.getElementById('branchSelect');

            if (!repoId) {
                // 如果没有选择仓库，禁用分支下拉框
                branchSelect.disabled = true;
                branchSelect.innerHTML = '<option value="" selected>请先选择仓库...</option>';

                // 禁用开始识别按钮
                document.getElementById('startGitOcrBtn').disabled = true;
                return;
            }

            // 如果选择了仓库，启用分支下拉框，并加载分支列表
            branchSelect.disabled = false;
            loadGitBranches(repoId);
        });
    }

    // 分支选择器变化事件
    const branchSelect = document.getElementById('branchSelect');
    if (branchSelect) {
        branchSelect.addEventListener('change', function () {
            // 如果选择了分支，启用开始识别按钮
            document.getElementById('startGitOcrBtn').disabled = !this.value;
        });
    }

    // 开始Git仓库识别按钮
    const startGitOcrBtn = document.getElementById('startGitOcrBtn');
    if (startGitOcrBtn) {
        startGitOcrBtn.addEventListener('click', function () {
            processGitRepository();
        });
    }
}

/**
 * 加载Git仓库下拉框
 */
function loadGitRepos(projectId) {
    const repoSelect = document.getElementById('repoSelect');
    if (!repoSelect) return;

    // 显示加载中提示
    repoSelect.innerHTML = '<option value="" selected>加载中...</option>';

    fetch('/api/ocr/repositories/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            action: 'list',
            project_id: projectId
        })
    })
        .then(response => response.json())
        .then(data => {
            if (data.length === 0) {
                repoSelect.innerHTML = '<option value="" selected>该项目下没有仓库...</option>';
                return;
            }

            // 清空并添加新选项
            repoSelect.innerHTML = '<option value="">选择仓库...</option>';

            // 添加仓库选项
            data.forEach((repo, index) => {
                const option = document.createElement('option');
                option.value = repo.id;
                option.textContent = `${repo.url} (${repo.branch})`;
                repoSelect.appendChild(option);

                // 如果是第一个仓库，则自动选中
                if (index === 0) {
                    option.selected = true;
                    // 自动触发仓库选择变化事件，加载分支列表
                    if (repoSelect.dispatchEvent) {
                        const event = new Event('change');
                        repoSelect.dispatchEvent(event);
                    }
                }
            });
        })
        .catch(error => {
            console.error('加载仓库列表失败:', error);
            repoSelect.innerHTML = '<option value="" selected>加载失败，请重试...</option>';
        });
}

/**
 * 加载Git分支下拉框
 */
function loadGitBranches(repoId) {
    const branchSelect = document.getElementById('branchSelect');
    if (!branchSelect) return;

    // 显示加载中提示
    branchSelect.innerHTML = '<option value="" selected>加载中...</option>';

    fetch('/api/ocr/repositories/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            action: 'get_branches',
            id: repoId
        })
    })
        .then(response => response.json())
        .then(data => {
            if (!data.branches || data.branches.length === 0) {
                branchSelect.innerHTML = '<option value="" selected>未找到分支...</option>';
                return;
            }

            // 清空并添加新选项
            branchSelect.innerHTML = '<option value="">选择分支...</option>';

            // 添加分支选项
            data.branches.forEach((branch, index) => {
                const option = document.createElement('option');
                option.value = branch;
                option.textContent = branch;
                branchSelect.appendChild(option);

                // 如果是第一个分支，则自动选中
                if (index === 0) {
                    option.selected = true;
                    // 自动触发分支选择变化事件，启用开始识别按钮
                    if (branchSelect.dispatchEvent) {
                        const event = new Event('change');
                        branchSelect.dispatchEvent(event);
                    }
                }
            });
        })
        .catch(error => {
            console.error('加载分支列表失败:', error);
            branchSelect.innerHTML = '<option value="" selected>加载失败，请重试...</option>';
        });
}

/**
 * 处理Git仓库识别
 */
function processGitRepository() {
    // 获取选中的项目、仓库和分支
    const projectId = document.getElementById('projectSelect').value;
    const repoId = document.getElementById('repoSelect').value;
    const branch = document.getElementById('branchSelect').value;

    if (!projectId || !repoId || !branch) {
        updateGitStatus('请选择项目、仓库和分支', true);
        return;
    }

    // 获取选中的语言
    const selectedLanguages = [];
    document.querySelectorAll('input[id^="git-lang-"]:checked').forEach(function (checkbox) {
        selectedLanguages.push(checkbox.value);
    });

    if (selectedLanguages.length === 0) {
        updateGitStatus('请至少选择一种语言', true);
        return;
    }

    // 获取GPU配置
    const useGpu = document.getElementById('git-useGpu').checked;
    const gpuId = document.getElementById('git-gpuId').value;

    // 获取令牌（如果仓库管理页面有的话）
    let token = '';
    const repoToken = document.getElementById('repoToken');
    if (repoToken) {
        token = repoToken.value;
    }

    // 获取是否跳过SSL验证
    let skipSSLVerify = false;
    const skipSSLVerifyElem = document.getElementById('skipSSLVerify');
    if (skipSSLVerifyElem) {
        skipSSLVerify = skipSSLVerifyElem.checked;
    }

    // 显示进度条
    document.getElementById('gitProgressContainer').style.display = 'block';
    document.getElementById('gitProgressBar').style.width = '10%';
    document.getElementById('gitProgressBar').textContent = '10%';

    updateGitStatus('正在启动Git仓库识别任务，请稍候...');

    // 调用API处理Git仓库
    OCRAPI.process.git(projectId, repoId, branch, selectedLanguages, useGpu, gpuId, token, skipSSLVerify)
        .then(data => {
            updateGitStatus('Git仓库识别任务已启动，正在处理...');
            document.getElementById('gitProgressBar').style.width = '20%';
            document.getElementById('gitProgressBar').textContent = '20%';

            // 轮询任务状态
            pollGitTaskStatus(data.id);
        })
        .catch(error => {
            updateGitStatus(`启动任务失败: ${error.message}`, true);
            document.getElementById('gitProgressContainer').style.display = 'none';
        });
}

/**
 * 更新Git处理状态
 */
function updateGitStatus(message, isError = false) {
    const statusDiv = document.getElementById('gitProcessStatus');
    if (!statusDiv) return;

    statusDiv.className = isError ? 'alert alert-danger' : 'alert alert-info';
    statusDiv.textContent = message;
}

/**
 * 轮询Git任务状态
 */
function pollGitTaskStatus(taskId) {
    const intervalId = setInterval(function () {
        fetch('/api/ocr/tasks/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                action: 'get',
                id: taskId
            })
        })
            .then(response => response.json())
            .then(data => {
                const status = data.status;

                if (status === 'completed') {
                    clearInterval(intervalId);
                    document.getElementById('gitProgressBar').style.width = '100%';
                    document.getElementById('gitProgressBar').textContent = '100%';

                    // 更新进度统计
                    document.getElementById('gitProcessedCount').textContent = data.total_images;
                    document.getElementById('gitTotalCount').textContent = data.total_images;
                    document.getElementById('gitMatchRate').textContent = `${data.match_rate.toFixed(1)}%`;

                    // 显示结果
                    updateGitStatus('Git仓库识别完成！');
                    showGitResults(data);

                } else if (status === 'failed') {
                    clearInterval(intervalId);
                    updateGitStatus(`处理失败: ${data.error || '未知错误'}`, true);
                    document.getElementById('gitProgressContainer').style.display = 'none';

                } else if (status === 'running') {
                    // 更新进度条
                    const progress = data.progress || 50;
                    document.getElementById('gitProgressBar').style.width = `${progress}%`;
                    document.getElementById('gitProgressBar').textContent = `${progress}%`;

                    // 更新进度统计
                    if (data.processed_count && data.total_count) {
                        document.getElementById('gitProcessedCount').textContent = data.processed_count;
                        document.getElementById('gitTotalCount').textContent = data.total_count;
                        const matchRate = data.matched_count / data.processed_count * 100 || 0;
                        document.getElementById('gitMatchRate').textContent = `${matchRate.toFixed(1)}%`;
                    }

                    updateGitStatus('正在处理中，请稍候...');
                }
            })
            .catch(error => {
                console.error('轮询任务状态失败:', error);
            });
    }, 3000); // 每3秒检查一次
}

/**
 * 显示Git仓库识别结果
 */
function showGitResults(data) {
    // 显示结果摘要
    const resultsDiv = document.getElementById('gitResultsContainer');
    if (resultsDiv) {
        resultsDiv.style.display = 'block';

        const summaryDiv = document.getElementById('gitResultsSummary');
        if (summaryDiv) {
            summaryDiv.innerHTML = `
                <h5>处理完成</h5>
                <p>总图片数: ${data.total_images}</p>
                <p>匹配图片: ${data.matched_images}</p>
                <p>匹配率: ${data.match_rate.toFixed(1)}%</p>
                <p>任务ID: ${data.id}</p>
            `;
        }

        // 设置查看详细结果按钮
        const viewDetailsBtn = document.getElementById('gitViewDetailsBtn');
        if (viewDetailsBtn) {
            viewDetailsBtn.onclick = function () {
                showDetailedResults(data.id);
            };
        }

        // 设置导出按钮
        setupGitExportButtons(data.id);
    }
}

/**
 * 设置Git导出按钮
 */
function setupGitExportButtons(taskId) {
    const formats = ['json', 'csv', 'txt'];

    formats.forEach(format => {
        const exportBtn = document.getElementById(`gitExport${format.charAt(0).toUpperCase() + format.slice(1)}`);
        if (exportBtn) {
            exportBtn.onclick = function (e) {
                e.preventDefault();
                window.location.href = `/api/ocr/tasks/?action=export&id=${taskId}&format=${format}`;
            };
        }
    });
}

/**
 * 初始化历史记录功能
 */
function initHistoryRecords() {
    // 搜索历史记录按钮点击事件
    const searchHistoryBtn = document.getElementById('searchHistoryBtn');
    if (searchHistoryBtn) {
        searchHistoryBtn.addEventListener('click', function () {
            loadHistoryRecords();
        });
    }

    // 监听标签页切换事件，当切换到历史记录标签页时自动刷新
    const historyTab = document.getElementById('ocr-history-tab');
    if (historyTab) {
        historyTab.addEventListener('shown.bs.tab', function () {
            loadHistoryRecords();
        });
    }

    // 页面加载完成后加载历史记录
    setTimeout(loadHistoryRecords, 500);
}

/**
 * 加载历史记录
 */
function loadHistoryRecords() {
    const projectId = document.getElementById('historyProjectFilter')?.value || '';
    const dateFrom = document.getElementById('dateFrom')?.value || '';
    const dateTo = document.getElementById('dateTo')?.value || '';

    fetch('/api/ocr/history/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            project_id: projectId || null,
            date_from: dateFrom || null,
            date_to: dateTo || null,
            page: 1,
            page_size: 20
        })
    })
        .then(response => response.json())
        .then(data => {
            const historyTable = document.querySelector('#historyTable tbody');
            if (!historyTable) return;

            historyTable.innerHTML = '';

            if (!data.tasks || data.tasks.length === 0) {
                historyTable.innerHTML = '<tr><td colspan="9" class="text-center">没有找到历史记录</td></tr>';
                return;
            }

            data.tasks.forEach(task => {
                const row = document.createElement('tr');
                const formattedDate = new Date(task.created_at).toLocaleString();
                const statusClass = getStatusClass(task.status);

                row.innerHTML = `
                <td>${task.id}</td>
                <td>${task.project_name}</td>
                <td>${task.source_type === 'git' ? 'Git仓库' : '本地上传'}</td>
                <td>${formattedDate}</td>
                <td>${task.total_images}</td>
                <td>${task.matched_images}</td>
                <td>${parseFloat(task.match_rate).toFixed(1)}%</td>
                <td><span class="badge ${statusClass}">${getStatusText(task.status)}</span></td>
                <td>
                    <button class="btn btn-sm btn-primary view-task" data-id="${task.id}">查看</button>
                    <button class="btn btn-sm btn-success download-task" data-id="${task.id}">下载</button>
                </td>
            `;
                historyTable.appendChild(row);
            });

            // 添加查看任务按钮点击事件
            historyTable.querySelectorAll('.view-task').forEach(button => {
                button.addEventListener('click', function () {
                    const taskId = this.getAttribute('data-id');
                    showDetailedResults(taskId);
                });
            });

            // 添加下载任务按钮点击事件
            historyTable.querySelectorAll('.download-task').forEach(button => {
                button.addEventListener('click', function () {
                    const taskId = this.getAttribute('data-id');
                    downloadTaskResults(taskId);
                });
            });

            // 更新分页
            updateHistoryPagination(data);
        })
        .catch(error => {
            console.error('加载历史记录失败:', error);
            const historyTable = document.querySelector('#historyTable tbody');
            if (historyTable) {
                historyTable.innerHTML = `<tr><td colspan="9" class="text-center text-danger">加载失败: ${error.message}</td></tr>`;
            }
        });
}

/**
 * 更新历史记录分页
 */
function updateHistoryPagination(data) {
    const pagination = document.getElementById('historyPagination');
    if (!pagination) return;

    pagination.innerHTML = '';

    if (data.total_pages <= 1) return;

    const ul = document.createElement('ul');
    ul.className = 'pagination justify-content-center';

    // 上一页
    const prevLi = document.createElement('li');
    prevLi.className = `page-item ${data.page === 1 ? 'disabled' : ''}`;
    prevLi.innerHTML = `<a class="page-link" href="#" data-page="${data.page - 1}">上一页</a>`;
    ul.appendChild(prevLi);

    // 页码
    for (let i = 1; i <= data.total_pages; i++) {
        const li = document.createElement('li');
        li.className = `page-item ${data.page === i ? 'active' : ''}`;
        li.innerHTML = `<a class="page-link" href="#" data-page="${i}">${i}</a>`;
        ul.appendChild(li);
    }

    // 下一页
    const nextLi = document.createElement('li');
    nextLi.className = `page-item ${data.page === data.total_pages ? 'disabled' : ''}`;
    nextLi.innerHTML = `<a class="page-link" href="#" data-page="${data.page + 1}">下一页</a>`;
    ul.appendChild(nextLi);

    pagination.appendChild(ul);

    // 添加分页点击事件
    pagination.querySelectorAll('.page-link').forEach(link => {
        link.addEventListener('click', function (e) {
            e.preventDefault();
            const page = parseInt(this.getAttribute('data-page'));
            loadHistoryPage(page);
        });
    });
}

/**
 * 加载历史记录的特定页
 */
function loadHistoryPage(page) {
    const projectId = document.getElementById('historyProjectFilter')?.value || '';
    const dateFrom = document.getElementById('dateFrom')?.value || '';
    const dateTo = document.getElementById('dateTo')?.value || '';

    fetch('/api/ocr/history/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            project_id: projectId || null,
            date_from: dateFrom || null,
            date_to: dateTo || null,
            page: page,
            page_size: 20
        })
    })
        .then(response => response.json())
        .then(data => {
            loadHistoryRecords();
        })
        .catch(error => {
            console.error('加载历史页面失败:', error);
        });
}

/**
 * 下载任务结果
 */
function downloadTaskResults(taskId) {
    fetch('/api/ocr/history/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            action: 'download',
            task_id: taskId
        })
    })
        .then(response => {
            if (!response.ok) {
                throw new Error('下载失败');
            }
            return response.blob();
        })
        .then(blob => {
            // 创建下载链接
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `ocr_results_${taskId}.csv`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            a.remove();
        })
        .catch(error => {
            console.error('下载失败:', error);
            alert('下载失败，请稍后重试');
        });
}

/**
 * 获取状态对应的CSS类名
 */
function getStatusClass(status) {
    switch (status) {
        case 'pending': return 'bg-warning';
        case 'running': return 'bg-info';
        case 'completed': return 'bg-success';
        case 'failed': return 'bg-danger';
        default: return 'bg-secondary';
    }
}

/**
 * 获取状态对应的文本
 */
function getStatusText(status) {
    switch (status) {
        case 'pending': return '等待中';
        case 'running': return '处理中';
        case 'completed': return '已完成';
        case 'failed': return '失败';
        default: return '未知';
    }
}