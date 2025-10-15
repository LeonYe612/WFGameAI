<script setup lang="ts">
import {
  Plus,
  Delete,
  Edit,
  Check,
  Close,
  Rank,
  Menu
} from "@element-plus/icons-vue";
import draggable from "vuedraggable";
import { useActionSettings } from "./actionHook";
import { type ActionTypeItem, type ActionParamItem } from "./actionHook";
import { onMounted, onUnmounted, computed, ref, nextTick } from "vue";
import type { ElScrollbar } from "element-plus";

defineOptions({
  name: "ActionSettings"
});

const scrollbarRef = ref<InstanceType<typeof ElScrollbar>>();

const {
  loading,
  actionTypes,
  activeCollapse,
  handleAddActionType,
  handleSaveActionType,
  handleDeleteActionType,
  handleCancelEditActionType,
  onActionTypeSortEnd,
  handleAddParam,
  handleSaveParam,
  handleDeleteParam,
  handleCancelEditParam,
  onParamSortEnd
} = useActionSettings();

const onAddActionTypeClick = () => {
  handleAddActionType();
  nextTick(() => {
    scrollbarRef.value?.scrollTo({ top: 0, behavior: "smooth" });
  });
};

const paramTypes = [
  "string",
  "int",
  "float",
  "boolean",
  "array",
  "object",
  "enum",
  "json",
  "date",
  "datetime",
  "file",
  "image"
];

const toggleEdit = (item: ActionTypeItem | ActionParamItem) => {
  item.editing = !item.editing;
};

const openIconWebsite = () => {
  window.open("https://icon-sets.iconify.design/", "_blank");
};

const defaultValueProxy = (param: ActionParamItem) => {
  return computed({
    get() {
      try {
        return param.default.value;
      } catch (e) {
        // If parsing fails, return a sensible default
        return getDefaultValueForType(param.type);
      }
    },
    set(newValue) {
      // Automatically convert to number if type is int or float
      if (
        (param.type === "int" || param.type === "float") &&
        typeof newValue === "string"
      ) {
        const num = parseFloat(newValue);
        if (!isNaN(num)) {
          newValue = num;
        }
      }
      param.default = { value: newValue };
    }
  });
};

const getDefaultValueForType = (type: string) => {
  switch (type) {
    case "int":
    case "float":
      return 0;
    case "boolean":
      return false;
    case "array":
      return [];
    case "object":
    case "json":
      return {};
    default:
      return "";
  }
};

const handleGlobalSave = (event: KeyboardEvent) => {
  if (event.ctrlKey && (event.key === "s" || event.key === "S")) {
    event.preventDefault();
    actionTypes.value.forEach(actionType => {
      if (actionType.editing) {
        handleSaveActionType(actionType);
      }
      if (actionType.params) {
        actionType.params.forEach((param: ActionParamItem) => {
          if (param.editing) {
            handleSaveParam(param, actionType);
          }
        });
      }
    });
  }
};

onMounted(() => {
  window.addEventListener("keydown", handleGlobalSave);
});

onUnmounted(() => {
  window.removeEventListener("keydown", handleGlobalSave);
});
</script>

<template>
  <el-card class="action-settings h-full" shadow="never">
    <template #header>
      <div class="flex items-center">
        <el-icon><Menu /></el-icon>
        <span class="ml-2"
          >动作库管理 (共 {{ actionTypes?.length || 0 }} 个)</span
        >
        <el-button
          class="ml-auto"
          type="success"
          :icon="Plus"
          @click="onAddActionTypeClick"
          plain
        >
          添加新动作
        </el-button>
      </div>
    </template>
    <el-scrollbar class="h-full select-none" ref="scrollbarRef">
      <el-skeleton :rows="10" animated :loading="loading">
        <draggable
          v-model="actionTypes"
          item-key="id"
          handle=".drag-handle"
          :animation="200"
          @end="onActionTypeSortEnd"
          class="action-type-list"
          :scroll="true"
          :scroll-sensitivity="50"
          :scroll-speed="20"
          :force-fallback="true"
        >
          <template #item="{ element: actionType, index }">
            <div
              class="action-type-item"
              :class="{ 'is-editing': actionType.editing }"
            >
              <div class="header">
                <div class="drag-handle">
                  <el-icon><Rank /></el-icon>
                </div>
                <IconifyIconOnline
                  v-if="actionType.icon && !actionType.editing"
                  :icon="actionType.icon"
                  class="action-icon"
                />
                <div v-if="actionType.editing" class="editing-item">
                  <span>图标</span>
                  <el-input v-model="actionType.icon" placeholder="图标" />
                  <IconifyIconOnline
                    v-if="actionType.icon"
                    :icon="actionType.icon"
                    class="action-icon ml-2 cursor-pointer"
                    @click="openIconWebsite"
                  />
                </div>
                <span v-if="!actionType.editing" class="action-name">
                  {{ actionType.name }}
                </span>
                <div v-if="actionType.editing" class="editing-item">
                  <el-divider direction="vertical" />
                  <span>名称</span>
                  <el-input v-model="actionType.name" placeholder="动作名称" />
                </div>
                <span
                  v-if="!actionType.editing"
                  class="text-gray-500 text-pretty ml-4 italic"
                >
                  <el-divider direction="vertical" />
                  {{ actionType.action_type }}
                </span>
                <div v-if="actionType.editing" class="editing-item">
                  <el-divider direction="vertical" />
                  <span>类型</span>
                  <el-input
                    v-model="actionType.action_type"
                    placeholder="动作类型"
                  />
                </div>

                <div class="action-buttons">
                  <template v-if="actionType.editing">
                    <el-button
                      type="success"
                      :icon="Check"
                      circle
                      plain
                      size="small"
                      @click="handleSaveActionType(actionType)"
                    />
                    <el-button
                      :icon="Close"
                      circle
                      plain
                      size="small"
                      @click="handleCancelEditActionType(actionType, index)"
                    />
                  </template>
                  <template v-else>
                    <el-button
                      type="primary"
                      :icon="Edit"
                      circle
                      plain
                      size="small"
                      @click="toggleEdit(actionType)"
                    />
                    <el-popconfirm
                      title="确定删除这个动作吗？"
                      @confirm="handleDeleteActionType(actionType)"
                    >
                      <template #reference>
                        <el-button
                          type="danger"
                          :icon="Delete"
                          circle
                          plain
                          size="small"
                        />
                      </template>
                    </el-popconfirm>
                  </template>
                </div>
              </div>
              <el-collapse accordion v-model="activeCollapse">
                <el-collapse-item
                  :name="actionType.action_type"
                  class="params-collapse"
                >
                  <template #title>
                    <span class="collapse-title">查看参数列表</span>
                  </template>
                  <div
                    class="params-container"
                    v-if="activeCollapse === actionType.action_type"
                  >
                    <div class="flex justify-end mb-2">
                      <el-button
                        size="small"
                        type="success"
                        plain
                        :icon="Plus"
                        @click="handleAddParam(actionType)"
                        >添加参数</el-button
                      >
                    </div>
                    <draggable
                      v-model="actionType.params"
                      item-key="id"
                      handle=".param-drag-handle"
                      :animation="150"
                      @end="onParamSortEnd(actionType)"
                      class="param-list"
                    >
                      <template #item="{ element: param, index: pIndex }">
                        <div
                          class="param-item"
                          :class="{ 'is-editing': param.editing }"
                        >
                          <div class="param-drag-handle">
                            <el-icon><Rank /></el-icon>
                          </div>
                          <div class="param-form">
                            <el-form
                              :model="param"
                              inline
                              size="small"
                              label-width="60px"
                              class="param-form-grid"
                            >
                              <el-form-item label="名称">
                                <el-input
                                  v-model="param.name"
                                  :disabled="!param.editing"
                                />
                              </el-form-item>
                              <el-form-item label="类型">
                                <el-select
                                  v-model="param.type"
                                  :disabled="!param.editing"
                                >
                                  <el-option
                                    v-for="t in paramTypes"
                                    :key="t"
                                    :label="t"
                                    :value="t"
                                  />
                                </el-select>
                              </el-form-item>
                              <el-form-item label="必需">
                                <el-switch
                                  v-model="param.required"
                                  :disabled="!param.editing"
                                />
                              </el-form-item>
                              <el-form-item label="默认值">
                                <el-input
                                  v-if="
                                    ['string', 'int', 'float'].includes(
                                      param.type
                                    )
                                  "
                                  v-model="defaultValueProxy(param).value"
                                  :disabled="!param.editing"
                                  :type="
                                    param.type === 'int' ||
                                    param.type === 'float'
                                      ? 'number'
                                      : 'text'
                                  "
                                />
                                <el-switch
                                  v-else-if="param.type === 'boolean'"
                                  v-model="defaultValueProxy(param).value"
                                  :disabled="!param.editing"
                                />
                                <el-input
                                  v-else
                                  v-model="defaultValueProxy(param).value"
                                  :disabled="!param.editing"
                                  type="textarea"
                                  :rows="1"
                                />
                              </el-form-item>
                              <el-form-item
                                label="说明"
                                class="description-item"
                              >
                                <el-input
                                  v-model="param.description"
                                  :disabled="!param.editing"
                                  type="textarea"
                                  :rows="1"
                                />
                              </el-form-item>
                            </el-form>
                          </div>
                          <div class="param-buttons">
                            <template v-if="param.editing">
                              <el-button
                                type="success"
                                :icon="Check"
                                circle
                                plain
                                size="small"
                                @click="handleSaveParam(param, actionType)"
                              />
                              <el-button
                                :icon="Close"
                                circle
                                plain
                                size="small"
                                @click="
                                  handleCancelEditParam(
                                    param,
                                    actionType,
                                    pIndex
                                  )
                                "
                              />
                            </template>
                            <template v-else>
                              <el-button
                                type="primary"
                                :icon="Edit"
                                circle
                                plain
                                size="small"
                                @click="toggleEdit(param)"
                              />
                              <el-popconfirm
                                title="确定删除这个参数吗？"
                                @confirm="handleDeleteParam(param, actionType)"
                              >
                                <template #reference>
                                  <el-button
                                    type="danger"
                                    :icon="Delete"
                                    circle
                                    plain
                                    size="small"
                                  />
                                </template>
                              </el-popconfirm>
                            </template>
                          </div>
                        </div>
                      </template>
                    </draggable>
                  </div>
                </el-collapse-item>
              </el-collapse>
            </div>
          </template>
        </draggable>
      </el-skeleton>
    </el-scrollbar>
  </el-card>
</template>

<style scoped lang="scss">
.el-card {
  display: flex;
  flex-direction: column;
  .el-card__body {
    flex: 1;
    min-height: 0;
  }
}

.editing-item {
  display: flex;
  align-items: center;
  margin-right: 12px;
  span {
    font-size: 14px;
    color: #909399;
    margin-right: 6px;
  }
  .el-input {
    width: 220px;
  }
}
.action-settings {
  .action-type-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .action-type-item {
    background-color: #fcfcfc;
    border: 1px solid #e4e7ed;
    border-radius: 8px;
    transition: box-shadow 0.2s ease-in-out;

    &.is-editing {
      background-color: #f0f8ff;
      border-color: #a0cfff;
    }

    &:hover {
      box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
    }

    .header {
      display: flex;
      justify-content: start;
      align-items: center;
      padding: 10px 15px;
      border-bottom: 1px solid #f0f2f5;
    }

    .drag-handle {
      cursor: grab;
      margin-right: 12px;
      color: #909399;
      font-size: 20px;
      display: flex;
      justify-content: center;
      align-items: center;
    }

    .action-icon {
      font-size: 20px;
      margin-right: 8px;
      color: #409eff;
    }

    .action-name {
      font-weight: 500;
      font-size: 16px;
    }

    .action-buttons {
      margin-left: auto;
    }
  }

  .params-collapse {
    :deep(.el-collapse-item__header) {
      border-bottom: none;
      background-color: transparent;
      padding-left: 15px;
    }
    :deep(.el-collapse-item__wrap) {
      border-bottom: none;
      background-color: #ffffff;
    }
    :deep(.el-collapse-item__content) {
      padding: 15px;
    }
    .collapse-title {
      font-weight: 500;
      color: #409eff;
    }
  }

  .params-container {
    padding: 0 10px;
  }

  .param-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .param-item {
    display: flex;
    align-items: flex-start;
    padding: 6px 10px;
    background-color: #f5f7fa;
    border-radius: 6px;
    border: 1px solid #e9e9eb;
    transition: background-color 0.2s ease-in-out;

    &.is-editing {
      background-color: #e6f7ff;
      border-color: #91d5ff;
    }
  }

  .param-drag-handle {
    cursor: grab;
    margin-right: 10px;
    padding-top: 8px;
    color: #909399;
  }

  .param-form {
    flex-grow: 1;
  }

  .param-form-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 0 10px;
    width: 100%;

    :deep(.el-form-item) {
      margin-bottom: 5px;
    }

    .description-item {
      grid-column: 1 / -1;
    }
  }

  .param-buttons {
    display: flex;
    align-items: center;
    gap: 8px;
    padding-top: 4px;
    margin-left: 15px;
  }
}
</style>
