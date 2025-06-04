# WFGame AI 服务器URL配置指南

## URL访问方式说明

### 推荐访问方式
- **主要URL**: `http://localhost:8000`
- **API文档**: `http://localhost:8000/api/docs/`
- **设备管理**: `http://localhost:8000/static/pages/devices.html`

### 服务器配置
- **服务器绑定**: `0.0.0.0:8000` (允许所有IP访问)
- **推荐访问**: `localhost:8000` (与启动脚本输出一致)
- **备用访问**: `127.0.0.1:8000` (直接IP访问)

## 技术差异

### localhost vs 127.0.0.1
| 方面 | localhost | 127.0.0.1 |
|------|-----------|-----------|
| 类型 | 域名 | IP地址 |
| DNS解析 | 需要 | 不需要 |
| 解析速度 | 稍慢(几毫秒) | 稍快 |
| 兼容性 | 标准 | 标准 |
| 可读性 | 更好 | 一般 |

### 实际使用建议
1. **开发环境**: 推荐使用 `localhost:8000`
2. **生产环境**: 根据具体需求选择
3. **API调用**: 前端使用相对路径，自动适配

## 当前系统配置

### Django配置 (settings.py)
```python
ALLOWED_HOSTS = ['*']  # 允许所有主机访问
```

### 启动脚本 (start_wfgame_ai.py)
```python
# 服务器绑定到所有接口
command = [sys.executable, 'manage.py', 'runserver', '0.0.0.0:8000']

# 用户界面显示localhost
print("- 后端: http://localhost:8000")
```

### 前端代码
- 使用相对路径调用API: `/api/devices/scan/`
- 自动适配当前域名和端口
- 无需修改硬编码URL

## 网络访问说明

### 本地访问
- `http://localhost:8000` ✅ 推荐
- `http://127.0.0.1:8000` ✅ 可用

### 局域网访问
- `http://[本机IP]:8000` ✅ 可用 (如: `http://192.168.1.100:8000`)

### 端口说明
- **8000**: Django开发服务器默认端口
- **绑定**: 0.0.0.0 (所有网络接口)
- **访问**: 支持localhost、127.0.0.1和局域网IP

## 故障排查

### 如果localhost:8000无法访问
1. 检查hosts文件: `C:\Windows\System32\drivers\etc\hosts`
2. 确认localhost解析: `ping localhost`
3. 尝试使用127.0.0.1:8000
4. 检查防火墙设置

### 如果127.0.0.1:8000无法访问
1. 检查服务是否启动: `netstat -an | findstr 8000`
2. 检查Django ALLOWED_HOSTS配置
3. 确认端口未被占用

## 最佳实践

1. **开发阶段**: 统一使用 `localhost:8000`
2. **文档和说明**: 统一使用 `localhost:8000`
3. **API调用**: 使用相对路径，保持灵活性
4. **错误处理**: 提供两种访问方式的说明

---
*更新时间: 2025-06-04*
*版本: 1.0*
