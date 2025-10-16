<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useScriptStoreHook } from "@/store/modules/script";
import draggable from "vuedraggable";
import { InfoFilled, Plus, Search } from "@element-plus/icons-vue";
import { useSSE, SSEEvent } from "@/layout/components/sseState/useSSE";
const { on } = useSSE();

defineOptions({
  name: "ScriptActionLibrary"
});

defineProps({
  readonly: {
    type: Boolean,
    default: false
  }
});

on(SSEEvent.ACTION_UPDATE, () => {
  scriptStore.fetchActionLibrary();
});

const scriptStore = useScriptStoreHook();

// 搜索功能
const searchQuery = ref("");
const filteredActionLibrary = computed(() => {
  if (!searchQuery.value) {
    return scriptStore.actionLibrary;
  }
  const lowerCaseQuery = searchQuery.value.toLowerCase();
  return scriptStore.actionLibrary.filter(
    action =>
      action.name.toLowerCase().includes(lowerCaseQuery) ||
      action.action_type.toLowerCase().includes(lowerCaseQuery)
  );
});

// Dialog相关
const dialogVisible = ref(false);
const selectedAction = ref(null);

onMounted(() => {
  scriptStore.fetchActionLibrary();
});

// 拖拽克隆，而不是移动
const cloneAction = action => {
  return {
    action: action.action_type,
    remark: action.name,
    ...action.params.reduce((acc, param) => {
      if (param.default !== null && param.default !== undefined) {
        acc[param.name] = param.default?.value || null;
      }
      return acc;
    }, {})
  };
};

// 点击“说明”按钮时触发
const showActionDetails = action => {
  selectedAction.value = action;
  dialogVisible.value = true;
};

// 点击“添加”按钮时触发
const addActionToSteps = action => {
  scriptStore.addStep(action);
};
</script>

<template>
  <div class="action-library flex-col pb-8">
    <div class="flex justify-between items-center h-[34px] mb-2">
      <h3 class="font-bold">🌈 动作库</h3>
      <el-input
        style="width: 200px"
        v-model="searchQuery"
        placeholder="搜索动作名称或类型"
        clearable
        :prefix-icon="Search"
      />
    </div>
    <el-scrollbar class="flex-1 min-h-0">
      <draggable
        v-model="filteredActionLibrary"
        class="list-group"
        item-key="id"
        :group="{ name: 'steps', pull: 'clone', put: false }"
        :sort="false"
        :clone="cloneAction"
      >
        <template #item="{ element }">
          <div class="action-item">
            <span class="drag-handle">⠿</span>
            <IconifyIconOnline
              v-if="element.icon"
              :icon="element.icon"
              class="action-icon"
            />
            <span class="action-name">{{ element.name }}</span>
            <el-tag size="small" effect="plain" class="mr-auto ml-2">{{
              element.action_type
            }}</el-tag>
            <div class="action-buttons">
              <el-button
                size="small"
                :icon="InfoFilled"
                round
                plain
                @click.stop="showActionDetails(element)"
              />
              <el-button
                v-if="!readonly"
                size="small"
                type="success"
                :icon="Plus"
                round
                plain
                @click.stop="addActionToSteps(element)"
              />
            </div>
          </div>
        </template>
      </draggable>
    </el-scrollbar>

    <!-- Action 详情 Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="selectedAction?.name"
      width="700px"
      draggable
    >
      <div v-if="selectedAction" class="dialog-content">
        <p class="description">{{ selectedAction.description }}</p>
        <h4 class="param-title">参数列表</h4>
        <el-table :data="selectedAction.params" border size="small">
          <el-table-column prop="name" label="参数" width="200" />
          <el-table-column prop="type" label="类型" width="80" />
          <el-table-column prop="required" label="必需" width="60">
            <template #default="{ row }">
              <el-tag :type="row.required ? 'danger' : 'info'" size="small">{{
                row.required ? "是" : "否"
              }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="default" label="默认值" width="100">
            <template #default="{ row }">
              {{ row?.default?.value ?? "-" }}
            </template>
          </el-table-column>
          <el-table-column prop="description" label="说明" />
        </el-table>
      </div>
      <template v-if="false" #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">关闭</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.action-library {
  .list-group {
    height: 100%;
    min-height: 200px;
  }

  .action-item {
    display: flex;
    align-items: center;
    width: 100%;
    height: 40px;
    padding: 0 12px;
    background-color: #f5f7fa;
    border: 1px solid #e4e7ed;
    border-radius: 6px;
    cursor: grab;
    user-select: none;
    margin-bottom: 6px;
    transition: all 0.2s ease-in-out;
  }

  .action-buttons {
    display: flex;
    align-items: center;
    gap: 6px;
    opacity: 0;
    transition: opacity 0.2s ease-in-out;
  }

  .action-item:hover .action-buttons {
    opacity: 1;
  }

  .drag-handle {
    cursor: grab;
    margin-right: 8px;
    color: #909399;
  }

  .action-icon {
    font-size: 18px;
    margin-right: 8px;
    color: #409eff;
  }

  .action-name {
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-right: 10px;
  }

  .info-icon {
    cursor: pointer;
    color: #909399;
    margin-left: 10px;
    &:hover {
      color: #409eff;
    }
  }

  :deep(.sortable-ghost) {
    opacity: 0.5;
    background: #c8ebfb;
    border: 1px dashed #409eff;
    border-radius: 6px;
    & > * {
      visibility: hidden;
    }
  }

  :deep(.sortable-drag) {
    transform: rotate(2deg);
    box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);
    opacity: 0.9;
    cursor: grabbing;
  }
}

.popover-content {
  .description {
    color: #606266;
    font-size: 14px;
    margin-bottom: 12px;
  }
}

.dialog-content {
  .description {
    color: #606266;
    font-size: 14px;
    margin-bottom: 16px;
    padding-left: 8px;
    border-left: 3px solid #409eff;
  }
  .param-title {
    font-weight: bold;
    margin-bottom: 10px;
  }
}
</style>
