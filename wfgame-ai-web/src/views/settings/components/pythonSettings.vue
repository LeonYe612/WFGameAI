<script setup lang="ts">
import { computed } from "vue";
import { Refresh, Monitor, CircleCheck } from "@element-plus/icons-vue";
import type { PythonEnvironment } from "../utils/types";

defineOptions({
  name: "PythonSettings"
});

const props = defineProps<{
  environments: PythonEnvironment[];
  loading: boolean;
  error: string;
}>();

const emit = defineEmits<{
  refresh: [];
  switch: [envPath: string];
}>();

// 获取环境状态类型
const getEnvStatusType = (env: PythonEnvironment) => {
  return env.active ? "success" : "info";
};

// 获取环境状态文本
const getEnvStatusText = (env: PythonEnvironment) => {
  return env.active ? "当前环境" : "可选环境";
};

// 获取Python版本显示文本
const getPythonVersionText = (version?: string) => {
  return version ? `Python ${version}` : "Python 未知版本";
};

// 获取包数量文本
const getPackageCountText = (packages?: string[]) => {
  return `包含 ${packages?.length || 0} 个已安装包`;
};

// 刷新环境列表
const handleRefresh = () => {
  emit("refresh");
};

// 切换Python环境
const handleSwitchEnv = (envPath: string) => {
  emit("switch", envPath);
};

// 是否有环境数据
const hasEnvironments = computed(() => {
  return props.environments && props.environments.length > 0;
});
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <div class="card-header">
        <div class="header-left">
          <el-icon><Monitor /></el-icon>
          <span class="header-title">Python环境管理</span>
        </div>
        <el-button
          type="primary"
          size="default"
          :loading="loading"
          @click="handleRefresh"
        >
          <el-icon><Refresh /></el-icon>
          检测环境
        </el-button>
      </div>
    </template>

    <div class="python-settings-content">
      <!-- 提示信息 -->
      <el-alert type="info" :closable="false" show-icon class="mb-4">
        <template #title>
          检测系统中所有可用的Python环境，自动识别Anaconda/Miniconda环境，并可以切换当前环境。
        </template>
      </el-alert>

      <!-- 加载状态 -->
      <div v-if="loading" class="loading-container">
        <el-icon class="loading-icon"><Refresh /></el-icon>
        <p class="loading-text">正在检测系统中的Python环境，请稍候...</p>
      </div>

      <!-- 错误提示 -->
      <el-alert
        v-else-if="error"
        type="error"
        :title="error"
        show-icon
        :closable="false"
      />

      <!-- 环境列表 -->
      <div v-else-if="hasEnvironments" class="environments-grid">
        <el-card
          v-for="env in environments"
          :key="env.path"
          shadow="hover"
          class="env-card"
          :class="{ 'env-card--active': env.active }"
        >
          <template #header>
            <div class="env-header">
              <h4 class="env-name">{{ env.name }}</h4>
              <el-tag :type="getEnvStatusType(env)" size="default">
                {{ getEnvStatusText(env) }}
              </el-tag>
            </div>
          </template>

          <div class="env-content">
            <div class="env-info">
              <p class="python-version">
                {{ getPythonVersionText(env.version) }}
              </p>
              <p class="env-path">{{ env.path }}</p>
              <p class="package-count">
                {{ getPackageCountText(env.packages) }}
              </p>
            </div>

            <div class="env-actions">
              <el-button
                v-if="env.active"
                type="success"
                :icon="CircleCheck"
                disabled
                size="default"
              >
                当前环境
              </el-button>
              <el-button
                v-else
                type="primary"
                size="default"
                @click="handleSwitchEnv(env.path)"
              >
                切换到此环境
              </el-button>
            </div>
          </div>
        </el-card>
      </div>

      <!-- 空状态 -->
      <el-empty
        v-else-if="!loading"
        description="点击 [检测环境] 按钮, 开始扫描可用的Python环境"
        class="empty-state"
      />
    </div>
  </el-card>
</template>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.header-left {
  display: flex;
  align-items: center;
}

.header-title {
  margin-left: 8px;
  font-weight: 500;
}

.python-settings-content {
  padding: 20px 0;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px 0;
}

.loading-icon {
  font-size: 48px;
  color: var(--el-color-primary);
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

.loading-text {
  color: var(--el-text-color-regular);
  font-size: 14px;
  margin: 0;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.environments-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 20px;
}

.env-card {
  transition: all 0.3s ease;
  border: 2px solid transparent;
}

.env-card--active {
  border-color: var(--el-color-success);
  background-color: var(--el-color-success-light-9);
}

.env-card:hover {
  transform: translateY(-2px);
}

.env-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.env-name {
  margin: 0;
  font-size: 18px;
  font-weight: 500;
}

.env-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.env-info {
  flex: 1;
}

.python-version {
  font-size: 16px;
  font-weight: 500;
  color: var(--el-text-color-primary);
  margin: 0 0 8px 0;
}

.env-path {
  font-size: 12px;
  color: var(--el-text-color-regular);
  margin: 0 0 8px 0;
  word-break: break-all;
}

.package-count {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin: 0;
}

.env-actions {
  display: flex;
  justify-content: flex-end;
}

.empty-state {
  padding: 60px 0;
}

.mb-4 {
  margin-bottom: 20px;
}
</style>
