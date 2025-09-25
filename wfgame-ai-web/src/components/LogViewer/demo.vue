<template>
  <div class="log-viewer-demo">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>日志查看器演示</span>
          <div class="header-buttons">
            <el-button-group size="small">
              <el-button
                :type="isConnected ? 'success' : 'info'"
                :icon="isConnected ? 'connection' : 'disconnect'"
                @click="toggleConnection"
              >
                {{ isConnected ? "已连接" : "未连接" }}
              </el-button>
              <el-button :icon="Refresh" @click="resetDemo">
                重置演示
              </el-button>
            </el-button-group>
          </div>
        </div>
      </template>

      <div class="demo-controls">
        <el-row :gutter="16">
          <el-col :span="8">
            <el-card shadow="never">
              <template #header>手动添加日志</template>
              <el-form size="small">
                <el-form-item label="日志级别">
                  <el-select v-model="testLog.level" style="width: 100%">
                    <el-option
                      v-for="level in LOG_LEVELS"
                      :key="level"
                      :label="level.toUpperCase()"
                      :value="level"
                    />
                  </el-select>
                </el-form-item>
                <el-form-item label="日志源">
                  <el-input v-model="testLog.source" placeholder="可选" />
                </el-form-item>
                <el-form-item label="日志内容">
                  <el-input
                    v-model="testLog.message"
                    type="textarea"
                    :rows="2"
                    placeholder="输入日志内容..."
                  />
                </el-form-item>
                <el-form-item>
                  <el-button
                    type="primary"
                    @click="addTestLog"
                    style="width: 100%"
                  >
                    添加日志
                  </el-button>
                </el-form-item>
              </el-form>
            </el-card>
          </el-col>

          <el-col :span="8">
            <el-card shadow="never">
              <template #header>批量操作</template>
              <div class="batch-controls">
                <el-form size="small">
                  <el-form-item label="生成数量">
                    <el-input-number
                      v-model="batchConfig.count"
                      :min="10"
                      :max="1000"
                      :step="10"
                      style="width: 100%"
                    />
                  </el-form-item>
                  <el-form-item label="时间间隔(ms)">
                    <el-input-number
                      v-model="batchConfig.interval"
                      :min="10"
                      :max="5000"
                      :step="10"
                      style="width: 100%"
                    />
                  </el-form-item>
                  <el-form-item>
                    <el-button-group style="width: 100%">
                      <el-button @click="addBatchLogs" :loading="isBatchAdding">
                        批量添加
                      </el-button>
                      <el-button
                        @click="startAutoGenerate"
                        :type="isAutoGenerating ? 'danger' : 'success'"
                      >
                        {{ isAutoGenerating ? "停止" : "自动生成" }}
                      </el-button>
                    </el-button-group>
                  </el-form-item>
                </el-form>
              </div>
            </el-card>
          </el-col>

          <el-col :span="8">
            <el-card shadow="never">
              <template #header>模拟场景</template>
              <div class="scenario-controls">
                <el-button-group size="small">
                  <el-button @click="simulateServerStartup">
                    服务器启动
                  </el-button>
                  <el-button @click="simulateError"> 模拟错误 </el-button>
                </el-button-group>
                <el-button-group size="small" style="margin-top: 8px">
                  <el-button @click="simulateUserActivity">
                    用户活动
                  </el-button>
                  <el-button @click="simulateSystemMonitor">
                    系统监控
                  </el-button>
                </el-button-group>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>
    </el-card>

    <el-card style="margin-top: 16px">
      <LogViewer
        ref="logViewerRef"
        height="600px"
        :max-log-lines="logConfig.maxLines"
        :auto-connect="false"
        title="演示日志查看器"
        @connected="handleConnected"
        @disconnected="handleDisconnected"
        @error="handleError"
        @log-added="handleLogAdded"
      />
    </el-card>

    <!-- 统计信息 -->
    <el-card style="margin-top: 16px">
      <template #header>
        <span>统计信息</span>
      </template>
      <el-row :gutter="16">
        <el-col :span="6">
          <el-statistic title="总日志数" :value="statistics.totalLogs" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="错误日志" :value="statistics.errorLogs" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="警告日志" :value="statistics.warnLogs" />
        </el-col>
        <el-col :span="6">
          <el-statistic
            title="运行时长"
            :value="statistics.uptime"
            suffix="秒"
          />
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onBeforeUnmount } from "vue";
import { ElMessage } from "element-plus";
import { Refresh } from "@element-plus/icons-vue";
import LogViewer from "@/components/LogViewer/index.vue";
import type { LogEntry, LogLevel } from "@/components/LogViewer/types";

const LOG_LEVELS: LogLevel[] = ["debug", "info", "warn", "error", "critical"];

// 组件引用
const logViewerRef = ref();

// 连接状态
const isConnected = ref(false);

// 测试日志表单
const testLog = reactive({
  level: "info" as LogLevel,
  source: "manual",
  message: "这是一条测试日志"
});

// 批量配置
const batchConfig = reactive({
  count: 100,
  interval: 50
});

// 日志配置
const logConfig = reactive({
  maxLines: 5000
});

// 状态
const isBatchAdding = ref(false);
const isAutoGenerating = ref(false);

// 统计信息
const statistics = reactive({
  totalLogs: 0,
  errorLogs: 0,
  warnLogs: 0,
  uptime: 0
});

// 定时器
let autoGenerateTimer: NodeJS.Timeout | null = null;
let uptimeTimer: NodeJS.Timeout | null = null;

// 消息模板
const MESSAGE_TEMPLATES = {
  startup: [
    "正在启动应用服务...",
    "加载配置文件成功",
    "连接数据库成功",
    "初始化缓存完成",
    "启动 HTTP 服务器",
    "服务器启动完成，监听端口 8080"
  ],
  error: [
    "数据库连接超时",
    "文件读取失败: permission denied",
    "内存不足，无法分配更多空间",
    "API 调用失败: timeout after 30s",
    "认证失败: invalid token"
  ],
  user: [
    "用户 admin 登录成功",
    "用户 john 查看了订单列表",
    "用户 mary 创建了新订单 #12345",
    "用户 bob 更新了个人信息",
    "用户 alice 上传了文件"
  ],
  system: [
    "CPU 使用率: 45%",
    "内存使用率: 78%",
    "磁盘空间剩余: 12.5GB",
    "网络流量: 上行 1.2MB/s, 下行 3.4MB/s",
    "活跃连接数: 234"
  ]
};

// 方法
const addTestLog = () => {
  if (!testLog.message.trim()) {
    ElMessage.warning("请输入日志内容");
    return;
  }

  logViewerRef.value?.addLog({
    level: testLog.level,
    source: testLog.source || undefined,
    message: testLog.message,
    timestamp: new Date()
  });

  // 重置消息内容
  testLog.message = "这是一条测试日志";
};

const addBatchLogs = async () => {
  isBatchAdding.value = true;

  try {
    const logs: Array<Omit<LogEntry, "id">> = [];

    for (let i = 0; i < batchConfig.count; i++) {
      const level = LOG_LEVELS[Math.floor(Math.random() * LOG_LEVELS.length)];
      logs.push({
        level,
        source: "batch",
        message: `批量日志 ${i + 1}: ${generateRandomMessage()}`,
        timestamp: new Date(Date.now() + i * 10)
      });
    }

    // 分批添加，避免一次性添加太多
    const batchSize = 50;
    for (let i = 0; i < logs.length; i += batchSize) {
      const batch = logs.slice(i, i + batchSize);
      logViewerRef.value?.addLogs(batch);

      // 添加延迟，让界面有时间更新
      if (i + batchSize < logs.length) {
        await new Promise(resolve => setTimeout(resolve, batchConfig.interval));
      }
    }

    ElMessage.success(`成功添加 ${batchConfig.count} 条日志`);
  } finally {
    isBatchAdding.value = false;
  }
};

const startAutoGenerate = () => {
  if (isAutoGenerating.value) {
    if (autoGenerateTimer) {
      clearInterval(autoGenerateTimer);
      autoGenerateTimer = null;
    }
    isAutoGenerating.value = false;
    ElMessage.info("已停止自动生成日志");
  } else {
    isAutoGenerating.value = true;
    autoGenerateTimer = setInterval(() => {
      const level = LOG_LEVELS[Math.floor(Math.random() * LOG_LEVELS.length)];
      logViewerRef.value?.addLog({
        level,
        source: "auto",
        message: generateRandomMessage(),
        timestamp: new Date()
      });
    }, batchConfig.interval);
    ElMessage.success("开始自动生成日志");
  }
};

const simulateServerStartup = () => {
  const logs = MESSAGE_TEMPLATES.startup.map((message, index) => ({
    level: (index === MESSAGE_TEMPLATES.startup.length - 1
      ? "info"
      : "debug") as LogLevel,
    source: "server",
    message,
    timestamp: new Date(Date.now() + index * 200)
  }));

  logViewerRef.value?.addLogs(logs);
};

const simulateError = () => {
  const errorMessage =
    MESSAGE_TEMPLATES.error[
      Math.floor(Math.random() * MESSAGE_TEMPLATES.error.length)
    ];
  logViewerRef.value?.addLog({
    level: "error",
    source: "system",
    message: errorMessage,
    timestamp: new Date()
  });

  // 添加相关的调试信息
  setTimeout(() => {
    logViewerRef.value?.addLog({
      level: "debug",
      source: "system",
      message: `Stack trace: at ${Math.random()
        .toString(36)
        .substr(2, 10)}.js:${Math.floor(Math.random() * 100)}`,
      timestamp: new Date()
    });
  }, 100);
};

const simulateUserActivity = () => {
  const message =
    MESSAGE_TEMPLATES.user[
      Math.floor(Math.random() * MESSAGE_TEMPLATES.user.length)
    ];
  logViewerRef.value?.addLog({
    level: "info",
    source: "auth",
    message,
    timestamp: new Date()
  });
};

const simulateSystemMonitor = () => {
  const message =
    MESSAGE_TEMPLATES.system[
      Math.floor(Math.random() * MESSAGE_TEMPLATES.system.length)
    ];
  logViewerRef.value?.addLog({
    level: "debug",
    source: "monitor",
    message,
    timestamp: new Date()
  });
};

const generateRandomMessage = (): string => {
  const templates = [
    `处理请求 ${Math.random().toString(36).substr(2, 8)}`,
    `执行任务 ${Math.floor(Math.random() * 1000)}`,
    `更新记录 ID: ${Math.floor(Math.random() * 10000)}`,
    `发送消息到 ${Math.random().toString(36).substr(2, 6)}`,
    `缓存命中率: ${Math.floor(Math.random() * 100)}%`
  ];
  return templates[Math.floor(Math.random() * templates.length)];
};

const toggleConnection = () => {
  isConnected.value = !isConnected.value;
  ElMessage({
    message: isConnected.value ? "模拟连接已建立" : "模拟连接已断开",
    type: isConnected.value ? "success" : "info"
  });
};

const resetDemo = async () => {
  // 停止自动生成
  if (isAutoGenerating.value) {
    startAutoGenerate();
  }

  // 清空日志
  await logViewerRef.value?.clearLogs();

  // 重置统计
  Object.assign(statistics, {
    totalLogs: 0,
    errorLogs: 0,
    warnLogs: 0,
    uptime: 0
  });

  ElMessage.success("演示已重置");
};

// 事件处理器
const handleConnected = () => {
  ElMessage.success("WebSocket 连接成功");
};

const handleDisconnected = () => {
  ElMessage.warning("WebSocket 连接断开");
};

const handleError = (error: Error) => {
  ElMessage.error(`发生错误: ${error.message}`);
};

const handleLogAdded = (log: LogEntry) => {
  statistics.totalLogs++;
  if (log.level === "error" || log.level === "critical") {
    statistics.errorLogs++;
  } else if (log.level === "warn") {
    statistics.warnLogs++;
  }
};

// 生命周期
onMounted(() => {
  // 启动运行时间计时器
  uptimeTimer = setInterval(() => {
    statistics.uptime++;
  }, 1000);

  // 添加初始日志
  logViewerRef.value?.addLog({
    level: "info",
    source: "demo",
    message: "欢迎使用日志查看器演示页面",
    timestamp: new Date()
  });
});

onBeforeUnmount(() => {
  if (autoGenerateTimer) {
    clearInterval(autoGenerateTimer);
  }
  if (uptimeTimer) {
    clearInterval(uptimeTimer);
  }
});
</script>

<style scoped>
.log-viewer-demo {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-buttons {
  display: flex;
  gap: 8px;
}

.demo-controls {
  margin-bottom: 16px;
}

.batch-controls .el-button-group {
  display: flex;
  width: 100%;
}

.batch-controls .el-button-group .el-button {
  flex: 1;
}

.scenario-controls {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.scenario-controls .el-button-group {
  display: flex;
  width: 100%;
}

.scenario-controls .el-button {
  flex: 1;
}
</style>
