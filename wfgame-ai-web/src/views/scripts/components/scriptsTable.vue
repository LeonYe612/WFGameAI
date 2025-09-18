<script setup lang="ts">
import { ref, computed } from "vue";
import {
  Search,
  Refresh,
  Document,
  Edit,
  CopyDocument,
  Delete,
  VideoPlay,
  Grid,
  List,
  Switch,
  ArrowDown,
  Plus,
  Upload
} from "@element-plus/icons-vue";
import type { ScriptInfo, ScriptStats, ScriptCategory } from "@/api/scripts";
import ScriptEditDialog from "./scriptEditDialog.vue";
import ScriptReplayDialog from "./scriptReplayDialog.vue";

defineOptions({
  name: "ScriptsTable"
});

const props = defineProps<{
  scripts: ScriptInfo[];
  categories: ScriptCategory[];
  loading: boolean;
  error: string;
  stats: ScriptStats;
  searchQuery: string;
  categoryFilter: string;
  typeFilter: string;
  includeInLogFilter: string;
  viewMode: string;
  filteredSortedScripts: ScriptInfo[];
}>();

const emit = defineEmits([
  "edit",
  "replay",
  "copy",
  "delete",
  "toggle-log",
  "refresh",
  "create",
  "import",
  "update:search-query",
  "update:category-filter",
  "update:type-filter",
  "update:include-in-log-filter",
  "update:view-mode"
]);

const editDialogRef = ref();
const replayDialogRef = ref();
const sortField = ref("filename");
const sortDirection = ref("asc");

// 获取日志状态显示文本
const getLogStatusText = (includeInLog: boolean) => {
  return includeInLog ? "已加入日志" : "未加入日志";
};

// 获取日志状态标签类型
const getLogStatusType = (includeInLog: boolean) => {
  return includeInLog ? "success" : "warning";
};

// 排序处理
const sortBy = (field: string) => {
  if (sortField.value === field) {
    sortDirection.value = sortDirection.value === "asc" ? "desc" : "asc";
  } else {
    sortField.value = field;
    sortDirection.value = "asc";
  }
};

// 过滤和排序的脚本列表
const filteredAndSortedScripts = computed(() => {
  let filtered = props.scripts;

  // 搜索过滤
  if (props.searchQuery) {
    const query = props.searchQuery.toLowerCase();
    filtered = filtered.filter(
      script =>
        script.filename?.toLowerCase().includes(query) ||
        script.category?.toLowerCase().includes(query) ||
        script.description?.toLowerCase().includes(query)
    );
  }

  // 分类过滤
  if (props.categoryFilter) {
    filtered = filtered.filter(
      script => script.category === props.categoryFilter
    );
  }

  // 类型过滤
  if (props.typeFilter) {
    filtered = filtered.filter(
      script => script.script_type === props.typeFilter
    );
  }

  // 日志包含状态过滤
  if (props.includeInLogFilter !== "") {
    const includeInLog = props.includeInLogFilter === "true";
    filtered = filtered.filter(
      script => script.include_in_log === includeInLog
    );
  }

  // 排序
  if (sortField.value) {
    filtered = [...filtered].sort((a, b) => {
      const aVal = a[sortField.value] || "";
      const bVal = b[sortField.value] || "";
      const result = aVal.toString().localeCompare(bVal.toString());
      return sortDirection.value === "asc" ? result : -result;
    });
  }

  return filtered;
});

// 编辑脚本
const handleEdit = (script: ScriptInfo) => {
  editDialogRef.value?.showDialog(script);
};

// 回放脚本
const handleReplay = (script: ScriptInfo) => {
  replayDialogRef.value?.showDialog(script);
};

// 复制脚本
const handleCopy = (script: ScriptInfo) => {
  emit("copy", script.filename);
};

// 删除脚本
const handleDelete = (script: ScriptInfo) => {
  emit("delete", script.filename);
};

// 切换日志状态
const handleToggleLog = (script: ScriptInfo) => {
  emit("toggle-log", script.filename, !script.include_in_log);
};

// 切换视图模式
const toggleViewMode = () => {
  const newMode = props.viewMode === "table" ? "card" : "table";
  emit("update:view-mode", newMode);
};

// 格式化文件大小
const formatFileSize = (bytes: number) => {
  if (bytes < 1024) {
    return bytes + " B";
  } else if (bytes < 1024 * 1024) {
    return (bytes / 1024).toFixed(2) + " KB";
  } else {
    return (bytes / (1024 * 1024)).toFixed(2) + " MB";
  }
};

// 格式化日期
const formatDate = (dateString: string) => {
  if (!dateString) return "-";
  return new Date(dateString).toLocaleDateString();
};
</script>

<template>
  <div class="w-full h-full bg-red-200">
    <!-- 搜索和筛选工具栏 -->
    <div
      v-if="!loading && scripts.length > 0"
      class="flex items-center justify-between mb-4"
    >
      <div class="flex items-center space-x-4">
        <el-input
          :model-value="searchQuery"
          @update:model-value="emit('update:search-query', $event)"
          placeholder="搜索脚本名称、分类、描述..."
          :prefix-icon="Search"
          style="width: 300px"
          clearable
        />

        <el-select
          :model-value="categoryFilter"
          @update:model-value="emit('update:category-filter', $event)"
          placeholder="所有分类"
          style="width: 150px"
          clearable
        >
          <el-option
            v-for="category in categories"
            :key="category.id"
            :label="category.name"
            :value="category.id"
          />
        </el-select>

        <el-select
          :model-value="typeFilter"
          @update:model-value="emit('update:type-filter', $event)"
          placeholder="所有类型"
          style="width: 150px"
          clearable
        >
          <el-option label="录制脚本" value="recorded" />
          <el-option label="手动脚本" value="manual" />
        </el-select>

        <el-select
          :model-value="includeInLogFilter"
          @update:model-value="emit('update:include-in-log-filter', $event)"
          placeholder="日志状态"
          style="width: 150px"
          clearable
        >
          <el-option label="已加入日志" value="true" />
          <el-option label="未加入日志" value="false" />
        </el-select>
      </div>

      <div class="flex items-center space-x-2">
        <el-button
          :icon="viewMode === 'table' ? Grid : List"
          @click="toggleViewMode"
        >
          {{ viewMode === "table" ? "卡片视图" : "表格视图" }}
        </el-button>

        <el-button :icon="Refresh" type="primary" @click="emit('refresh')">
          刷新
        </el-button>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="text-center py-12">
      <el-icon class="animate-spin text-4xl text-primary mb-4">
        <Refresh />
      </el-icon>
      <p class="text-gray-500">正在加载脚本列表...</p>
    </div>

    <!-- 错误信息 -->
    <el-alert v-if="error" :title="error" type="error" class="mb-4" show-icon />

    <!-- 无脚本提示 -->
    <div v-if="!loading && scripts.length === 0" class="text-center py-12">
      <el-empty description="暂无脚本">
        <template #default>
          <div class="space-y-4">
            <p class="text-gray-500">
              还没有任何脚本，开始创建你的第一个脚本吧！
            </p>
            <div class="flex justify-center space-x-4">
              <el-button type="primary" :icon="Plus" @click="emit('create')">
                新建脚本
              </el-button>
              <el-button type="success" :icon="Upload" @click="emit('import')">
                导入脚本
              </el-button>
            </div>
          </div>
        </template>
      </el-empty>
    </div>

    <!-- 表格视图 -->
    <el-table
      v-if="!loading && scripts.length > 0 && viewMode === 'table'"
      :data="filteredAndSortedScripts"
      stripe
      style="width: 100%"
      class="scripts-table"
    >
      <el-table-column
        prop="filename"
        label="脚本名称"
        min-width="180"
        sortable
        @click="sortBy('filename')"
      >
        <template #default="{ row }">
          <div class="flex items-center">
            <el-icon class="mr-2 text-primary">
              <Document />
            </el-icon>
            <span class="font-medium">{{ row.filename }}</span>
          </div>
        </template>
      </el-table-column>

      <el-table-column
        prop="category"
        label="分类"
        width="120"
        sortable
        @click="sortBy('category')"
      >
        <template #default="{ row }">
          <el-tag v-if="row.category" type="info" size="small">
            {{ row.category }}
          </el-tag>
          <span v-else class="text-gray-400">-</span>
        </template>
      </el-table-column>

      <el-table-column
        prop="description"
        label="描述"
        min-width="200"
        show-overflow-tooltip
      >
        <template #default="{ row }">
          {{ row.description || "-" }}
        </template>
      </el-table-column>

      <el-table-column
        prop="size"
        label="文件大小"
        width="100"
        sortable
        @click="sortBy('size')"
      >
        <template #default="{ row }">
          {{ row.size ? formatFileSize(row.size) : "-" }}
        </template>
      </el-table-column>

      <el-table-column
        prop="include_in_log"
        label="日志状态"
        width="120"
        sortable
        @click="sortBy('include_in_log')"
      >
        <template #default="{ row }">
          <el-tag :type="getLogStatusType(row.include_in_log)" size="small">
            {{ getLogStatusText(row.include_in_log) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="modified_at" label="修改时间" width="120">
        <template #default="{ row }">
          {{ formatDate(row.modified_at) }}
        </template>
      </el-table-column>

      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <div class="flex space-x-1">
            <el-button
              size="small"
              type="primary"
              :icon="Edit"
              @click="handleEdit(row)"
            >
              编辑
            </el-button>

            <el-button
              size="small"
              type="success"
              :icon="VideoPlay"
              @click="handleReplay(row)"
            >
              回放
            </el-button>

            <el-button
              size="small"
              type="info"
              :icon="CopyDocument"
              @click="handleCopy(row)"
            >
              复制
            </el-button>

            <el-button
              size="small"
              :type="row.include_in_log ? 'warning' : 'success'"
              :icon="Switch"
              @click="handleToggleLog(row)"
            >
              {{ row.include_in_log ? "移出" : "加入" }}日志
            </el-button>

            <el-button
              size="small"
              type="danger"
              :icon="Delete"
              @click="handleDelete(row)"
            >
              删除
            </el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <!-- 卡片视图 -->
    <div
      v-if="!loading && scripts.length > 0 && viewMode === 'card'"
      class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
    >
      <el-card
        v-for="script in filteredAndSortedScripts"
        :key="script.id || script.filename"
        shadow="hover"
        class="script-card"
      >
        <template #header>
          <div class="flex items-center justify-between">
            <div class="flex items-center">
              <el-icon class="mr-2 text-primary">
                <Document />
              </el-icon>
              <span class="font-medium truncate">{{ script.filename }}</span>
            </div>
            <el-tag
              :type="getLogStatusType(script.include_in_log)"
              size="small"
            >
              {{ getLogStatusText(script.include_in_log) }}
            </el-tag>
          </div>
        </template>

        <div class="space-y-2 text-sm">
          <div class="flex justify-between">
            <span class="text-gray-500">分类:</span>
            <el-tag v-if="script.category" type="info" size="small">
              {{ script.category }}
            </el-tag>
            <span v-else>-</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-500">大小:</span>
            <span>{{ script.size ? formatFileSize(script.size) : "-" }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-500">修改时间:</span>
            <span>{{ formatDate(script.modified_at) }}</span>
          </div>
          <div v-if="script.description" class="pt-2 border-t">
            <span class="text-gray-500">描述:</span>
            <p class="mt-1 text-sm text-gray-700 line-clamp-2">
              {{ script.description }}
            </p>
          </div>
        </div>

        <template #footer>
          <div class="flex justify-between space-x-1">
            <el-button
              size="small"
              type="primary"
              :icon="Edit"
              @click="handleEdit(script)"
            >
              编辑
            </el-button>

            <el-button
              size="small"
              type="success"
              :icon="VideoPlay"
              @click="handleReplay(script)"
            >
              回放
            </el-button>

            <el-dropdown trigger="click">
              <el-button size="small" type="info">
                更多
                <el-icon class="ml-1">
                  <ArrowDown />
                </el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item
                    :icon="CopyDocument"
                    @click="handleCopy(script)"
                  >
                    复制脚本
                  </el-dropdown-item>
                  <el-dropdown-item
                    :icon="Switch"
                    @click="handleToggleLog(script)"
                  >
                    {{ script.include_in_log ? "移出" : "加入" }}日志
                  </el-dropdown-item>
                  <el-dropdown-item
                    :icon="Delete"
                    @click="handleDelete(script)"
                    divided
                  >
                    删除脚本
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </template>
      </el-card>
    </div>

    <!-- 脚本编辑对话框 -->
    <ScriptEditDialog ref="editDialogRef" @saved="emit('refresh')" />

    <!-- 脚本回放对话框 -->
    <ScriptReplayDialog ref="replayDialogRef" :scripts="scripts" />
  </div>
</template>

<style scoped>
.scripts-table {
  border-radius: 8px;
  overflow: hidden;
}

.script-card {
  transition: all 0.3s ease;
}

.script-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
