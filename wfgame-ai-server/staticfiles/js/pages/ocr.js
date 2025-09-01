/**
 * OCR模块前端JavaScript
 * 提供OCR识别页面的交互功能
 */

// 全局 resultDetail modal
let resultModalInstance = null;

// 页面加载完成后执行初始化
document.addEventListener('DOMContentLoaded', function () {
    // 初始化 ocr 相关的全局监听
    initGlobalListeners();

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
        resetProcessParams(); // 重置处理参数
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

    // 获取GPU配置
    const useGpu = document.getElementById('useGpu').checked;
    const gpuId = document.getElementById('gpuId').value;

    // 准备表单数据
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('project_id', projectSelect.value);
    formData.append('languages', JSON.stringify(selectedLanguages));
    formData.append('use_gpu', useGpu);
    formData.append('gpu_id', gpuId);

    // 显示进度条
    document.getElementById('progressContainer').style.display = 'block';
    document.getElementById('progressBar').style.width = '5%';
    document.getElementById('progressBar').textContent = '5%';

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
            document.getElementById('progressBar').style.width = '10%';
            document.getElementById('progressBar').textContent = '10%';

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
                    document.getElementById('matchRate').textContent = `${parseFloat(data.match_rate).toFixed(1)}%`;

                    // 启用开始识别按钮
                    // document.getElementById('startOcrBtn').disabled = false;

                    // 清理fileInput对象
                    const fileInput = document.getElementById('fileInput');
                    if (fileInput) {
                        fileInput.value = null;
                        fileInput.disabled = false;
                    }
                    // 显示结果
                    updateUploadStatus('处理完成！');
                    showResults(data);

                } else if (status === 'failed') {
                    clearInterval(intervalId);
                    updateUploadStatus(`处理失败: ${data.remark || '未知错误'}`, true);
                    document.getElementById('progressContainer').style.display = 'none';

                } else if (status === 'running') {
                    // 更新进度条
                    const progress = data.progress || 50;
                    document.getElementById('progressBar').style.width = `${progress}%`;
                    document.getElementById('progressBar').textContent = `${progress}%`;

                    // 更新进度统计
                    if (data.executed_images && data.total_images) {
                        document.getElementById('processedCount').textContent = data.executed_images;
                        document.getElementById('totalCount').textContent = data.total_images;
                        const matchRate = data.matched_count / data.executed_images * 100 || 0;
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
            <p>匹配率: ${parseFloat(data.match_rate).toFixed(1)}%</p>
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
function showDetailedResults(taskId, page = 1) {
    // 打开模态框
    const resultModal = document.getElementById('resultModal');
    if (!resultModalInstance) {
        resultModalInstance = new bootstrap.Modal(resultModal);
    }
    resultModalInstance.show();

    // 清空之前的结果
    const detailedResults = document.getElementById('detailedResults');
    if (detailedResults) {
        detailedResults.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div><p class="mt-2">正在加载结果...</p></div>';
    }

    // 存储当前 taskid 和页码
    const modalElement = document.getElementById('resultModal');
    if (!modalElement) {
        console.error("错误：在页面中找不到 id 为 'resultModal' 的元素！");
        return;
    }
    modalElement.dataset.taskId = taskId;
    modalElement.dataset.page = page;

    const hasMatched = document.getElementById('showOnlyMatched')?.checked || false;
    const searchInput = document.getElementById('resultSearchInput');
    const keyword = searchInput && searchInput.value ? searchInput.value.trim() : '';
    const resultType = document.querySelector('#resultTypeFilterGroup .active')?.getAttribute('data-type') || '';

    // 加载详细结果
    fetch('/api/ocr/tasks/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            action: 'get_details',
            has_match: hasMatched,
            keyword: keyword,
            result_type: resultType,
            id: taskId,
            page: page,
            page_size: 50
        })
    })
        .then(response => response.json())
        .then(data => {
            if (!data.results || !detailedResults) return;
            detailedResults.innerHTML = '';
            const resultTypes = [
                { label: "正确", value: 1, btn: "btn-success" },
                { label: "误检", value: 2, btn: "btn-danger" },
                { label: "漏检", value: 3, btn: "btn-warning" }
            ];
            data.results.forEach(result => {
                const imageId = result.id;
                const selectedType = result.result_type || 1;
                let radioGroup = `
                    <div class="p-2" style="border-radius: 0.5rem; display: inline-block; margin-bottom: 0.5rem;">
                        <div class="btn-group btn-group-sm" role="group" id="resultTypeGroup_${imageId}">
                `;
                                resultTypes.forEach((rt, idx) => {
                                    const checked = rt.value == selectedType ? 'checked' : '';
                                    const btnClass = rt.value == selectedType ? rt.btn : '';
                                    let style = "border:1px solid #bdbdbd;";
                                    if (idx === 0) style += "border-radius:0.5rem 0 0 0.5rem;";
                                    else if (idx === resultTypes.length - 1) style += "border-radius:0 0.5rem 0.5rem 0;";
                                    else style += "border-radius:0;";
                                    radioGroup += `
                        <input type="radio" class="btn-check" name="resultType_${imageId}" id="resultType_${imageId}_${rt.value}" value="${rt.value}" ${checked} autocomplete="off" data-original="${selectedType}">
                        <label class="btn ${btnClass}" style="${style}" for="resultType_${imageId}_${rt.value}">${rt.label}</label>
                    `;
                                });
                                radioGroup += `
                        </div>
                    </div>
                `;
                const imagePath = result.image_path;
                const imageUrl = `/media/${imagePath}`;
                const fileName = imagePath.split('/').pop();
                const hasMatch = result.has_match ? 'text-success' : 'text-muted';
                const matchIcon = result.has_match ? 'check-circle' : 'times-circle';
                const resultItem = document.createElement('div');
                resultItem.className = 'card result-card mb-3';
                resultItem.innerHTML = `
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-3">
                            <img src="${imageUrl}" class="img-fluid result-image" style="cursor:pointer;" 
                                onclick="showImageModal('${imageUrl}')"
                                onerror="this.onerror=null; this.src='/static/images/image-not-found.png'; this.alt='图片加载失败';" alt="图片预览">
                        </div>
                        <div class="col-md-9">
                            <h5 class="card-title">
                                ${fileName} <i class="fas fa-${matchIcon} ${hasMatch}"></i>
                                <span class="ms-3">${radioGroup}</span>
                            </h5>
                            <h6 class="card-subtitle mb-2 text-muted">语言: ${Object.keys(result.languages).join(', ')}</h6>
                            <div class="card-text">
                                <strong>识别文本:</strong>
                                <div class="text-container mt-2">
                                    <ul class="list-group text-list">
                                        ${(result.texts || []).map(text => {
                    const maxLength = 200;
                    const truncatedText = text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
                    return `<li class="list-group-item text-item" title="${text.replace(/"/g, '&quot;')}">${truncatedText}</li>`;
                }).join('')}
                                    </ul>
                                </div>
                            </div>
                            <div class="mt-2">
                                <small class="text-muted">完整路径: ${imagePath}</small>
                            </div>
                        </div>
                    </div>
                </div>
            `;
                detailedResults.appendChild(resultItem);
                setTimeout(() => {
                    resultTypes.forEach(rt => {
                        const radio = document.getElementById(`resultType_${imageId}_${rt.value}`);
                        if (radio) {
                            radio.addEventListener('change', function () {
                                resultTypes.forEach(rtt => {
                                    const label = document.querySelector(`label[for="resultType_${imageId}_${rtt.value}"]`);
                                    if (label) {
                                        label.classList.remove('btn-success', 'btn-danger', 'btn-warning');
                                    }
                                });
                                const selectedLabel = document.querySelector(`label[for="resultType_${imageId}_${rt.value}"]`);
                                if (selectedLabel) {
                                    selectedLabel.classList.add(rt.btn);
                                }
                            });
                        }
                    });
                }, 0);
            });
            if (data.total_pages > 1) {
                const paginationContainer = document.createElement('div');
                renderPagination(paginationContainer, data.page, data.total_pages, function (newPage) {
                    showDetailedResults(taskId, newPage);
                });
                detailedResults.appendChild(paginationContainer);

                // 页码信息显示在分页条下方
                const pageInfo = document.createElement('div');
                pageInfo.className = 'text-center mb-2';
                pageInfo.innerHTML = `第 ${data.page} 页 / 共 ${data.total_pages} 页`;
                detailedResults.appendChild(pageInfo);
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
    const formats = ['json', 'csv', 'txt', 'xlsx'];

    formats.forEach(format => {
        const exportBtn = document.getElementById(`export${format.charAt(0).toUpperCase() + format.slice(1)}`);
        if (exportBtn) {
            exportBtn.onclick = function (e) {
                e.preventDefault();

                // 使用 fetch 发送 POST 请求
                fetch('/api/ocr/tasks/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        action: 'export',
                        id: taskId,
                        format: format
                    })
                })
                    .then(response => {
                        // 检查网络响应是否成功
                        if (!response.ok) {
                            // 尝试读取错误信息并抛出
                            return response.json().then(err => { throw new Error(err.detail || '网络响应错误'); });
                        }
                        // 从响应头中获取文件名
                        const disposition = response.headers.get('Content-Disposition');
                        let filename = `export.${format}`; // 设置一个默认文件名
                        if (disposition && disposition.includes('attachment')) {
                            const filenameMatch = disposition.match(/filename="?([^"]+)"?/);
                            if (filenameMatch && filenameMatch[1]) {
                                filename = filenameMatch[1];
                            }
                        }
                        // 将响应体转换为 Blob 对象，并传递文件名
                        return response.blob().then(blob => ({ blob, filename }));
                    })
                    .then(({ blob, filename }) => {
                        // 创建一个隐藏的链接来触发下载
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.style.display = 'none';
                        a.href = url;
                        a.download = filename; // 设置下载的文件名
                        document.body.appendChild(a);
                        a.click();

                        // 清理创建的临时对象
                        window.URL.revokeObjectURL(url);
                        document.body.removeChild(a);
                    })
                    .catch(error => {
                        console.error('导出失败:', error);
                        alert(`导出文件失败: ${error.message}`);
                    });
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

    // 重置 部分显示参数
    resetGitProcessParams()

    updateGitStatus('正在启动Git仓库识别任务，请稍候...');

    // 调用API处理Git仓库
    OCRAPI.process.git(projectId, repoId, branch, selectedLanguages, useGpu, gpuId, token, skipSSLVerify)
        .then(data => {
            updateGitStatus('Git仓库识别任务已启动，正在处理...');
            document.getElementById('gitProgressBar').style.width = '10%';
            document.getElementById('gitProgressBar').textContent = '10%';

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
                    document.getElementById('gitMatchRate').textContent = `${parseFloat(data.match_rate).toFixed(1)}%`;

                    // 启用开始识别按钮
                    document.getElementById('startGitOcrBtn').disabled = false;

                    // 启用下拉框
                    document.getElementById('projectSelect').disabled = false;
                    document.getElementById('repoSelect').disabled = false;
                    document.getElementById('branchSelect').disabled = false;

                    // 显示结果
                    updateGitStatus('Git仓库识别完成！');
                    showGitResults(data);

                } else if (status === 'failed') {
                    clearInterval(intervalId);
                    updateGitStatus(`处理失败: ${data.remark || '未知错误'}`, true);
                    // 启用开始识别按钮
                    document.getElementById('startGitOcrBtn').disabled = false;

                    // 启用下拉框
                    document.getElementById('projectSelect').disabled = false;
                    document.getElementById('repoSelect').disabled = false;
                    document.getElementById('branchSelect').disabled = false;

                    // 隐藏进度条
                    document.getElementById('gitProgressContainer').style.display = 'none';

                } else if (status === 'running') {
                    // 更新进度条
                    const progress = data.progress || 50;
                    document.getElementById('gitProgressBar').style.width = `${progress}%`;
                    document.getElementById('gitProgressBar').textContent = `${progress}%`;

                    // 更新进度统计
                    if (data.executed_images && data.total_images) {
                        document.getElementById('gitProcessedCount').textContent = data.executed_images;
                        document.getElementById('gitTotalCount').textContent = data.total_images;
                        const matchRate = data.matched_count / data.executed_images * 100 || 0;
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
                <p>匹配率: ${parseFloat(data.match_rate).toFixed(1)}%</p>
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

                // 使用 fetch 发送 POST 请求
                fetch('/api/ocr/tasks/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        action: 'export',
                        id: taskId,
                        format: format
                    })
                })
                    .then(response => {
                        // 检查网络响应是否成功
                        if (!response.ok) {
                            // 尝试读取错误信息并抛出
                            return response.json().then(err => { throw new Error(err.detail || '网络响应错误'); });
                        }
                        // 从响应头中获取文件名
                        const disposition = response.headers.get('Content-Disposition');
                        let filename = `export.${format}`; // 设置一个默认文件名
                        if (disposition && disposition.includes('attachment')) {
                            const filenameMatch = disposition.match(/filename="?([^"]+)"?/);
                            if (filenameMatch && filenameMatch[1]) {
                                filename = filenameMatch[1];
                            }
                        }
                        // 将响应体转换为 Blob 对象，并传递文件名
                        return response.blob().then(blob => ({ blob, filename }));
                    })
                    .then(({ blob, filename }) => {
                        // 创建一个隐藏的链接来触发下载
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.style.display = 'none';
                        a.href = url;
                        a.download = filename; // 设置下载的文件名
                        document.body.appendChild(a);
                        a.click();

                        // 清理创建的临时对象
                        window.URL.revokeObjectURL(url);
                        document.body.removeChild(a);
                    })
                    .catch(error => {
                        console.error('导出失败:', error);
                        alert(`导出文件失败: ${error.message}`);
                    });
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
                <td>${task.git_branch}</td>
                <td>${task.source_type === 'git' ? 'Git仓库' : '本地上传'}</td>
                <td>${formattedDate}</td>
                <td>${task.total_images}</td>
                <td>${task.matched_images}</td>
                <td>${parseFloat(task.match_rate).toFixed(1)}%</td>
                <td><span class="badge ${statusClass}">${getStatusText(task.status)}</span></td>
                <td>
                    <button class="btn btn-sm btn-primary view-task" data-id="${task.id}">查看</button>
                    <button class="btn btn-sm btn-success download-task" data-id="${task.id}">下载</button>
                    <button class="btn btn-sm btn-danger del-task" data-id="${task.id}">删除</button>
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

            // 添加删除任务按钮点击事件
            historyTable.querySelectorAll('.del-task').forEach(button => {
                button.addEventListener('click', function () {
                    const taskId = this.getAttribute('data-id');
                    if (confirm('确定要删除该图片结果吗？')) {
                        deleteResult(taskId);
                    }
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
    renderPagination(pagination, data.page, data.total_pages, function (newPage) {
        loadHistoryPage(newPage);
    });
}

/**
 * 绑定历史记录表格的操作按钮事件
 */
function bindHistoryTableActions() {
    const historyTable = document.querySelector('#historyTable tbody');
    if (!historyTable) return;

    // 查看按钮
    historyTable.querySelectorAll('.view-task').forEach(button => {
        button.addEventListener('click', function () {
            const taskId = this.getAttribute('data-id');
            showDetailedResults(taskId);
        });
    });

    // 下载按钮
    historyTable.querySelectorAll('.download-task').forEach(button => {
        button.addEventListener('click', function () {
            const taskId = this.getAttribute('data-id');
            downloadTaskResults(taskId);
        });
    });

    // 添加删除任务按钮点击事件
    historyTable.querySelectorAll('.del-task').forEach(button => {
        button.addEventListener('click', function () {
            const taskId = this.getAttribute('data-id');
            if (confirm('确定要删除该图片结果吗？')) {
                deleteResult(taskId);
            }
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
            const tbody = document.querySelector('#historyTable tbody');
            if (tbody) {
                tbody.innerHTML = '';
                (data.tasks || []).forEach(task => {
                    const formattedDate = new Date(task.created_at).toLocaleString();
                    const statusClass = getStatusClass(task.status);
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${task.id}</td>
                        <td>${task.project_name}</td>
                        <td>${task.git_branch}</td>
                        <td>${task.source_type === 'git' ? 'Git仓库' : '本地上传'}</td>
                        <td>${formattedDate}</td>
                        <td>${task.total_images}</td>
                        <td>${task.matched_images}</td>
                        <td>${parseFloat(task.match_rate).toFixed(1)}%</td>
                        <td><span class="badge ${statusClass}">${getStatusText(task.status)}</span></td>
                        <td>
                            <button class="btn btn-sm btn-primary view-task" data-id="${task.id}">查看</button>
                            <button class="btn btn-sm btn-success download-task" data-id="${task.id}">下载</button>
                            <button class="btn btn-sm btn-danger del-task" data-id="${task.id}">删除</button>
                        </td>
                    `;
                    tbody.appendChild(row);
                });

                // 重新绑定操作按钮事件
                bindHistoryTableActions();
            }

            // 渲染分页（略，保持原有逻辑）
            updateHistoryPagination(data);
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
 * 删除历史记录中的单个结果
 */
function deleteResult(taskId) {
    fetch('/api/ocr/history/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            action: 'del',
            task_id: taskId
        })
    })
        .then(res => res.json())
        .then(resp => {
            alert(resp.detail || '删除成功');
            // 判断当前页面
            const modalElement = document.getElementById('resultModal');
            if (modalElement && modalElement.classList.contains('show')) {
                // 如果模态框打开，刷新详情页
                const detailTaskId = modalElement.dataset.taskId;
                const page = modalElement.dataset.page || 1;
                if (detailTaskId) showDetailedResults(detailTaskId, page);
            } else {
                // 否则刷新历史记录表格
                loadHistoryRecords();
            }
        })
        .catch(err => {
            alert('删除失败');
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

/**
 * 重置处理状态显示中涉及的相关参数
 */
function resetProcessParams() {
    const resultsContainer = document.getElementById('resultsContainer');
    if (resultsContainer){
        // 隐藏结果摘要
        resultsContainer.style.display = 'none';

        // 显示进度条
        document.getElementById('progressContainer').style.display = 'block';
        document.getElementById('progressBar').style.width = '5%';
        document.getElementById('progressBar').textContent = '5%';

        // 已处理数量
        document.getElementById('processedCount').textContent = '0';
        document.getElementById('totalCount').textContent = '0';

        // 命中率
        document.getElementById('matchRate').textContent = '0%';

        // 禁用开始识别按钮
        document.getElementById('startOcrBtn').disabled = true;

        // 禁用文件上传按钮
        document.getElementById('fileInput').disabled = true;
    }
}

/**
 * Git 重置处理状态显示中涉及的相关参数
 */
function resetGitProcessParams() {
    const gitResultsContainer = document.getElementById('gitResultsContainer');
    if (gitResultsContainer){
        // 隐藏结果摘要
        gitResultsContainer.style.display = 'none';

        // 显示进度条
        document.getElementById('gitProgressContainer').style.display = 'block';
        document.getElementById('gitProgressBar').style.width = '5%';
        document.getElementById('gitProgressBar').textContent = '5%';

        // 已处理数量
        document.getElementById('gitProcessedCount').textContent = '0';
        document.getElementById('gitTotalCount').textContent = '0';

        // 命中率
        document.getElementById('gitMatchRate').textContent = '0%';

        // 禁用开始识别按钮
        document.getElementById('startGitOcrBtn').disabled = true;

        // 禁用下拉框
        document.getElementById('projectSelect').disabled = true;
        document.getElementById('repoSelect').disabled = true;
        document.getElementById('branchSelect').disabled = true;

    }
}

/**
 * 显示图片模态框
 */
function showImageModal(url) {
    const modalImg = document.getElementById('modalImage');
    modalImg.src = url;
    resetImageZoom(); // 每次打开都还原
    new bootstrap.Modal(document.getElementById('imageModal')).show();
}

/**
 * 图片缩放
 */
function zoomImage(factor) {
    const modalImg = document.getElementById('modalImage');
    // 取当前宽度（像素），不是百分比
    let currentWidth = modalImg.width;
    let newWidth = currentWidth * factor;
    modalImg.style.width = newWidth + 'px';
    modalImg.style.height = 'auto';
    modalImg.dataset.zoom = factor * (parseFloat(modalImg.dataset.zoom || '1'));
}

/**
 * 重置图片缩放
 */
function resetImageZoom() {
    const modalImg = document.getElementById('modalImage');
    modalImg.style.width = modalImg.naturalWidth + 'px';
    modalImg.style.height = modalImg.naturalHeight + 'px';
    modalImg.dataset.zoom = '1';
}

/**
 * 更新图片的标注类型
 */
function submitResultTypes({ forceAll = false, batchType = null } = {}) {
    const ids = {};
    document.querySelectorAll('[name^="resultType_"]').forEach(radio => {
        const imageId = radio.name.replace('resultType_', '');
        const selectedType = parseInt(radio.value);
        const originalType = parseInt(radio.getAttribute('data-original'));

        // 批量标注时，强制全部提交并更新data-original
        if (forceAll && batchType !== null) {
            if (radio.value === batchType) {
                radio.checked = true;
                radio.setAttribute('data-original', batchType);
                radio.dispatchEvent(new Event('change'));
                ids[imageId] = selectedType;
            }
        } else {
            // 普通提交，只提交有变更的
            if (radio.checked && selectedType !== originalType) {
                ids[imageId] = selectedType;
            }
        }
    });

    if (Object.keys(ids).length === 0) {
        alert('没有需要更新的标注');
        return;
    }

    fetch('/api/ocr/results/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            action: 'update',
            ids: ids
        })
    })
        .then(res => res.json())
        .then(resp => {
            alert(resp.detail || '操作完成');
            // 更新 data-original
            document.querySelectorAll('[name^="resultType_"]:checked').forEach(radio => {
                radio.setAttribute('data-original', radio.value);
            });
        })
        .catch(err => {
            alert('接口调用失败');
        });
}

/**
 * 全局监听
 */
function initGlobalListeners() {
    // 监听 ‘识别结果详情 - 只显示匹配项’ 复选框变化事件
    const showOnlyMatchedCheckbox = document.getElementById('showOnlyMatched');
    if (showOnlyMatchedCheckbox) {
        showOnlyMatchedCheckbox.addEventListener('change', function() {
            // 当 checkbox 状态改变时，我们去模态框上寻找之前存好的 task ID
            const modalElement = document.getElementById('resultModal');
            const taskId = modalElement.dataset.taskId;
            // 如果找到了 task ID (意味着模态框是打开的，并且关联了一个任务)
            if (taskId) {
                // 就用这个 ID 重新调用 showDetailedResults 函数来刷新内容
                showDetailedResults(taskId);
            }
        });
    }

    // 监听 ‘识别结果详情 - 搜索按钮’
    const searchResultsBtn = document.getElementById('resultSearchBtn');
    if (searchResultsBtn) {
        searchResultsBtn.addEventListener('click', function() {
            // 当输入框内容变化时，我们去模态框上寻找之前存好的 task ID
            const modalElement = document.getElementById('resultModal');
            const taskId = modalElement.dataset.taskId;
            // 如果找到了 task ID (意味着模态框是打开的，并且关联了一个任务)
            if (taskId) {
                // 就用这个 ID 重新调用 showDetailedResults 函数来刷新内容
                showDetailedResults(taskId);
            }
        });
    }

    // 监听 ‘识别结果详情 - 清空按钮’
    const clearResultsBtn = document.getElementById('resultSearchClearBtn');
    if (clearResultsBtn) {
        clearResultsBtn.addEventListener('click', function() {
            // 清空搜索输入框
            const searchInput = document.getElementById('resultSearchInput');
            if (searchInput) {
                searchInput.value = '';
            }
            // 重新加载结果
            const modalElement = document.getElementById('resultModal');
            const taskId = modalElement.dataset.taskId;
            if (taskId) {
                showDetailedResults(taskId);
            }
        });
    }

    // 监听结果类型过滤按钮
    const filterGroup = document.getElementById('resultTypeFilterGroup');
    if (filterGroup) {
        filterGroup.querySelectorAll('button').forEach(btn => {
            btn.addEventListener('click', function () {
                // 移除所有按钮的底色和激活
                filterGroup.querySelectorAll('button').forEach(b => {
                    b.classList.remove('active', 'btn-info', 'btn-success', 'btn-danger', 'btn-warning');
                });
                // 当前按钮加底色和激活
                const type = this.getAttribute('data-type');
                if (type === '') this.classList.add('btn-info');
                else if (type === '1') this.classList.add('btn-success');
                else if (type === '2') this.classList.add('btn-danger');
                else if (type === '3') this.classList.add('btn-warning');
                this.classList.add('active');
                // 设置过滤类型到模态框 dataset
                const modalElement = document.getElementById('resultModal');
                modalElement.dataset.resultType = type;
                // 刷新结果
                const taskId = modalElement.dataset.taskId;
                if (taskId) showDetailedResults(taskId);
            });
        });
    }

    // 普通提交
    document.getElementById('submitAllResultTypesBtn')?.addEventListener('click', function() {
        submitResultTypes();
    });

    // 批量标注并提交
    document.querySelectorAll('.dropdown-menu .dropdown-item').forEach(item => {
        item.addEventListener('click', function (e) {
            e.preventDefault();
            const type = this.getAttribute('data-type');
            submitResultTypes({ forceAll: true, batchType: type });
        });
    });
}
