<script setup lang="ts">
import { ref, onMounted } from "vue";
import {
  Refresh,
  Plus,
  VideoPlay,
  Setting,
  Document,
  Upload
} from "@element-plus/icons-vue";
import MainContent from "@/layout/components/mainContent/index.vue";
import ScriptsStats from "./components/scriptsStats.vue";
import ScriptsTable from "./components/scriptsTable.vue";
import ScriptImportDialog from "./components/scriptImportDialog.vue";
import ScriptCreateDialog from "./components/scriptCreateDialog.vue";
import ScriptSettingsDialog from "./components/scriptSettingsDialog.vue";
import { useScriptsManagement } from "./utils/hook";
import { ElMessageBox } from "element-plus";

defineOptions({
  name: "ScriptsManagement"
});

const {
  scripts,
  categories,
  loading,
  error,
  stats,
  searchQuery,
  categoryFilter,
  typeFilter,
  includeInLogFilter,
  viewMode,
  filteredAndSortedScripts,
  settings,
  fetchScripts,
  fetchCategories,
  executeDebug,
  executeRecord,
  duplicateScript,
  removeScript,
  toggleScriptLogStatus,
  loadSettings,
  saveSettings
} = useScriptsManagement();

// 对话框引用
const importDialogRef = ref();
const createDialogRef = ref();
const settingsDialogRef = ref();

onMounted(() => {
  loadSettings();
  fetchScripts();
  fetchCategories();
});

// 处理脚本复制
const handleCopyScript = async (filename: string) => {
  try {
    const result = await ElMessageBox.prompt("请输入新脚本名称:", "复制脚本", {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      inputValue: `复制_${filename}`,
      inputValidator: (value: string) => {
        if (!value || value.trim() === "") {
          return "脚本名称不能为空";
        }
        if (value.length > 100) {
          return "脚本名称不能超过100个字符";
        }
        return true;
      },
      inputErrorMessage: "请输入有效的脚本名称"
    });

    if (result.value) {
      await duplicateScript(filename, result.value.trim());
    }
  } catch (error) {
    // 用户取消操作
  }
};

// 处理脚本删除
const handleDeleteScript = async (filename: string) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除脚本 "${filename}" 吗？此操作不可恢复。`,
      "确认删除",
      {
        confirmButtonText: "确定删除",
        cancelButtonText: "取消",
        type: "warning"
      }
    );

    await removeScript(filename);
  } catch (error) {
    // 用户取消操作
  }
};

// 显示导入对话框
const showImportDialog = () => {
  importDialogRef.value?.showDialog();
};

// 显示新建脚本对话框
const showCreateDialog = () => {
  createDialogRef.value?.showDialog();
};

// 显示设置对话框
const showSettingsDialog = () => {
  settingsDialogRef.value?.showDialog(settings.value);
};

// 处理设置保存
const handleSettingsSaved = newSettings => {
  saveSettings(newSettings);
};

// 处理导入完成
const handleImported = () => {
  fetchScripts();
};

// 处理脚本创建完成
const handleCreated = () => {
  fetchScripts();
};
</script>

<template>
  <MainContent title="脚本管理">
    <!-- 头部扩展功能 -->
    <template #header-extra>
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-2 ml-auto">
          <el-button
            :icon="Plus"
            size="large"
            type="primary"
            @click="showCreateDialog"
          >
            新建脚本
          </el-button>
          <el-button
            :icon="Upload"
            size="large"
            type="success"
            plain
            @click="showImportDialog"
          >
            导入脚本
          </el-button>
          <el-divider direction="vertical" />
          <el-button
            :icon="Document"
            size="large"
            type="info"
            plain
            @click="executeDebug"
            :loading="loading"
          >
            调试脚本
          </el-button>
          <el-button
            :icon="VideoPlay"
            size="large"
            type="warning"
            plain
            @click="executeRecord"
            :loading="loading"
          >
            录制脚本
          </el-button>
          <el-divider direction="vertical" />
          <el-button
            :icon="Setting"
            size="large"
            type="primary"
            plain
            @click="showSettingsDialog"
          >
            设置
          </el-button>
          <el-button
            :icon="Refresh"
            size="large"
            type="primary"
            plain
            @click="fetchScripts"
            :loading="loading"
          >
            刷新列表
          </el-button>
        </div>
      </div>
    </template>

    <!-- 页面内容 -->
    <div class="scripts-content">
      <!-- 功能演示提示 -->
      <el-alert
        title="功能演示"
        type="info"
        class="mb-6"
        show-icon
        :closable="true"
      >
        <template #default>
          <p>
            <strong>脚本日志功能:</strong>
            可以通过"加入日志"和"移出日志"功能控制哪些脚本会出现在测试报告中。
            已加入日志的脚本会在测试报告中显示执行记录，未加入日志的脚本则不会。
          </p>
        </template>
      </el-alert>

      <!-- 统计卡片 -->
      <ScriptsStats v-if="false" :stats="stats" :loading="loading" />

      <!-- 脚本表格/卡片视图 -->

      <div class="flex-1 min-h-0">
        <ScriptsTable
          :scripts="scripts"
          :categories="categories"
          :loading="loading"
          :error="error"
          :stats="stats"
          :search-query="searchQuery"
          :category-filter="categoryFilter"
          :type-filter="typeFilter"
          :include-in-log-filter="includeInLogFilter"
          :view-mode="viewMode"
          :filtered-sorted-scripts="filteredAndSortedScripts"
          @copy="handleCopyScript"
          @delete="handleDeleteScript"
          @toggle-log="toggleScriptLogStatus"
          @refresh="fetchScripts"
          @create="showCreateDialog"
          @import="showImportDialog"
          @update:search-query="searchQuery = $event"
          @update:category-filter="categoryFilter = $event"
          @update:type-filter="typeFilter = $event"
          @update:include-in-log-filter="includeInLogFilter = $event"
          @update:view-mode="viewMode = $event"
        />
      </div>
    </div>

    <!-- 脚本导入对话框 -->
    <ScriptImportDialog
      ref="importDialogRef"
      :categories="categories"
      @imported="handleImported"
    />

    <!-- 新建脚本对话框 -->
    <ScriptCreateDialog
      ref="createDialogRef"
      :categories="categories"
      @created="handleCreated"
    />

    <!-- 脚本设置对话框 -->
    <ScriptSettingsDialog
      ref="settingsDialogRef"
      @saved="handleSettingsSaved"
    />
  </MainContent>
</template>

<style scoped lang="scss">
.scripts-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
  height: 100%;
}
</style>
