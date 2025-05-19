// devices.js
// 设备管理页面前端交互脚本
// 负责加载设备列表、刷新、状态指示等

// 页面加载后自动获取设备列表
window.addEventListener('DOMContentLoaded', function() {
    loadDeviceList();
    // 兼容按钮可能未渲染时的情况
    setTimeout(function() {
        var refreshBtn = document.getElementById('refreshDeviceBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', loadDeviceList);
        }
    }, 100);
});

function loadDeviceList() {
    const container = document.getElementById('deviceListContainer');
    container.innerHTML = '<div class="text-center py-3"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div><p class="mt-2">正在加载设备列表...</p></div>';
    fetch('/api/devices/?format=json', {
        credentials: 'include'
    })
    .then(response => response.json())
    .then(data => {
        renderDeviceList(data);
    })
    .catch(err => {
        container.innerHTML = '<div class="alert alert-danger">加载设备失败: ' + err + '</div>';
    });
}

function renderDeviceList(devices) {
    const container = document.getElementById('deviceListContainer');
    if (!devices || devices.length === 0) {
        container.innerHTML = '<div class="alert alert-warning">暂无设备</div>';
        return;
    }
    let html = '';
    devices.forEach(device => {
        let statusClass = 'status-offline';
        if (device.status === 'online') statusClass = 'status-online';
        if (device.status === 'busy') statusClass = 'status-busy';
        html += `
        <div class="col-md-4">
            <div class="card device-card mb-3">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h5 class="card-title"><span class="device-status ${statusClass}"></span> ${device.name}</h5>
                        <span class="badge bg-primary">${device.type_name || '未知类型'}</span>
                    </div>
                    <div class="card-text">
                        <p class="text-muted mb-1">设备ID: ${device.device_id}</p>
                        <p class="text-muted mb-1">IP地址: ${device.ip_address || '-'}</p>
                        <p class="text-muted mb-3">最后在线: ${device.last_online || '-'}</p>
                    </div>
                    <div class="d-flex">
                        <button class="btn btn-sm btn-outline-secondary me-2" onclick="connectDevice(${device.id})"><i class="fas fa-mobile-alt"></i> 连接</button>
                        <button class="btn btn-sm btn-outline-primary me-2" disabled><i class="fas fa-desktop"></i> 屏幕</button>
                        <button class="btn btn-sm btn-outline-info" disabled><i class="fas fa-info-circle"></i> 详情</button>
                    </div>
                </div>
            </div>
        </div>
        `;
    });
    container.innerHTML = html;
}

function connectDevice(deviceId) {
    if (!confirm('确定要连接该设备吗？')) return;
    fetch(`/api/devices/${deviceId}/connect/`, {
        method: 'POST',
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        alert(data.detail || '操作完成');
        loadDeviceList();
    })
    .catch(err => {
        alert('连接设备失败: ' + err);
    });
} 