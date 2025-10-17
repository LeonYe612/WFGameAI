<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useScriptStoreHook } from "@/store/modules/script";
import draggable from "vuedraggable";
import { InfoFilled, Plus, Search } from "@element-plus/icons-vue";
import { message } from "@/utils/message";
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

// 根据动作名称显示详情
const showActionDetailsByName = actionType => {
  const action = scriptStore.actionLibrary.find(
    act => act.action_type === actionType
  );
  if (!action) {
    message(`未在动作库中找到类型为 [${actionType}] 的动作！`, {
      type: "error"
    });
    return;
  }
  showActionDetails(action);
};

defineExpose({
  showActionDetailsByName
});
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
            <div class="action-content">
              <span class="drag-handle">⠿</span>
              <IconifyIconOnline
                v-if="element.icon"
                :icon="element.icon"
                class="action-icon text-primary"
              />
              <span class="action-name">{{ element.name }}</span>
              <el-tag
                size="small"
                effect="plain"
                class="ml-auto mr-2 action-tag"
                >{{ element.action_type }}</el-tag
              >
              <div class="action-buttons">
                <el-button
                  type="text"
                  circle
                  plain
                  @click.stop="showActionDetails(element)"
                >
                  <el-icon size="20">
                    <InfoFilled class="text-gray-400" />
                  </el-icon>
                </el-button>
              </div>
            </div>
            <el-button
              v-if="!readonly"
              size="small"
              type="primary"
              class="add-button"
              plain
              @click.stop="addActionToSteps(element)"
            >
              <el-icon size="20">
                <Plus />
              </el-icon>
            </el-button>
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
    align-items: stretch; // 改为 stretch 以便子元素撑满高度
    width: 100%;
    height: 40px;
    padding: 0; // 移除 padding，移到 action-content
    background-color: #f5f7fa;
    border: 1px solid #e4e7ed;
    border-radius: 6px;
    cursor: grab;
    user-select: none;
    margin-bottom: 6px;
    transition: all 0.2s ease-in-out;
    position: relative;
    overflow: hidden; // 隐藏子元素的超出部分，确保圆角效果
    &:hover {
      border-color: #c0c4cc;
      background-color: #f5f7fa;
    }
  }

  .action-content {
    flex: 1;
    display: flex;
    align-items: center;
    padding: 0 12px;
    position: relative;
    min-width: 0;
  }

  .add-button {
    flex-shrink: 0;
    width: 50px;
    height: 100%;
    border-radius: 0;
    border: none;
    border-left: 1px solid #e4e7ed;
    margin: 0;
  }

  .action-item:hover .add-button {
    border-left-color: #c0c4cc;
  }

  .action-buttons {
    display: flex;
    align-items: center;
  }

  .drag-handle {
    cursor: grab;
    margin-right: 8px;
    color: #909399;
  }

  .action-icon {
    font-size: 18px;
    margin-right: 8px;
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
