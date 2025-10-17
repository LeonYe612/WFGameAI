<script setup lang="ts">
import { computed, ref, watch, nextTick } from "vue";
import { useScriptStoreHook } from "@/store/modules/script";
import draggable from "vuedraggable";
import {
  Close,
  Delete,
  Download,
  CopyDocument,
  MagicStick
} from "@element-plus/icons-vue";

defineOptions({
  name: "ScriptStepsList"
});
defineEmits(["open-step-importer", "open-yolo-selector"]);

const scriptStore = useScriptStoreHook();
const activeStep = computed(() => scriptStore.getActiveStep); // 控制展开项
const activeFocus = computed(() => scriptStore.getActiveFocus);

const stepsListRef = ref(null); // 用于引用步骤列表的容器

const steps = computed({
  get: () => scriptStore.getSteps,
  set: value => scriptStore.updateSteps(value)
});

const getActionInfo = actionType => {
  return scriptStore.actionLibrary.find(a => a.action_type === actionType);
};

const toggleStep = (index: number) => {
  if (scriptStore.activeStep === index) {
    scriptStore.setActiveFocus(null);
  } else {
    scriptStore.setActiveFocus(index);
  }
};

const onAdd = (event: { newIndex: number }) => {
  scriptStore.setActiveFocus(event.newIndex);
};

const onDragEnd = (event: { oldIndex: number; newIndex: number }) => {
  const { oldIndex, newIndex } = event;
  // 如果拖拽的是当前激活的步骤，则更新其索引
  if (scriptStore.activeStep === oldIndex) {
    scriptStore.setActiveFocus(newIndex);
  }
};

const removeStep = (event: MouseEvent, index: number) => {
  event.stopPropagation(); // 阻止事件冒泡，防止点击删除时触发展开/折叠
  steps.value.splice(index, 1);
  if (activeStep.value === index) {
    scriptStore.setActiveFocus(null);
  }
};

const copyStep = (event: MouseEvent, index: number) => {
  event.stopPropagation();
  const stepToCopy = steps.value[index];
  // 深拷贝
  const copiedStep = JSON.parse(JSON.stringify(stepToCopy));
  // 可以在备注中添加 " (复制)" 以作区分
  copiedStep.remark = `${copiedStep.remark}`;
  steps.value.splice(index + 1, 0, copiedStep);
  // 激活新复制的步骤
  scriptStore.setActiveFocus(index + 1);
};

const clearSteps = () => {
  steps.value.splice(0, steps.value.length);
  scriptStore.setActiveFocus(null);
};

const updateActiveFocus = (stepIndex: number, paramName: string) => {
  scriptStore.setActiveFocus(stepIndex, paramName);
};

// 监听 activeStep 的变化，自动滚动到可视区域
watch(
  () => scriptStore.activeStep,
  newIndex => {
    if (newIndex !== null && stepsListRef.value) {
      nextTick(() => {
        const stepElement = stepsListRef.value.$el.querySelector(
          `.step-wrapper:nth-child(${newIndex + 1})`
        );
        if (stepElement) {
          stepElement.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      });
    }
  },
  { flush: "post" }
);
</script>

<template>
  <div class="steps-list flex flex-col">
    <div class="flex items-center h-[37px] mb-2">
      <h3 class="font-bold">✏️ 脚本编排</h3>
      <el-divider direction="vertical" />
      <h4 class="text-gray-500">共 {{ steps.length || 0 }} 步</h4>
      <!-- 按钮组操作栏 -->
      <el-button-group class="ml-auto">
        <el-button
          size="small"
          :icon="Download"
          plain
          @click="$emit('open-step-importer')"
        >
          导入步骤
        </el-button>
        <el-button size="small" :icon="Delete" plain @click="clearSteps">
          清空步骤
        </el-button>
      </el-button-group>
    </div>
    <el-scrollbar ref="stepsListRef" class="flex-1 min-h-0">
      <draggable
        class="h-full"
        v-model="steps"
        item-key="step"
        handle=".drag-handle"
        group="steps"
        @add="onAdd"
        @end="onDragEnd"
      >
        <template #item="{ element, index }">
          <div class="step-wrapper">
            <div
              class="step-header"
              :class="{ 'is-active': activeStep === index }"
              @click="toggleStep(index)"
            >
              <span class="drag-handle">⠿</span>
              <IconifyIconOnline
                v-if="getActionInfo(element.action)?.icon"
                :icon="getActionInfo(element.action).icon"
                class="action-icon"
              />
              <span class="step-index">步骤 {{ index + 1 }} </span>
              <el-divider direction="vertical" />
              <span class="step-title" :title="element.remark">
                {{ element.remark }}</span
              >
              <el-tag size="small" effect="plain" class="mx-2">{{
                element.action
              }}</el-tag>
              <el-button
                type="primary"
                :icon="CopyDocument"
                circle
                plain
                size="small"
                class="copy-btn"
                title="复制步骤"
                @click="copyStep($event, index)"
              />
              <el-button
                type="danger"
                :icon="Close"
                circle
                plain
                size="small"
                class="delete-btn"
                @click="removeStep($event, index)"
              />
            </div>
            <el-collapse-transition>
              <el-form
                v-if="activeStep === index"
                label-width="auto"
                inline
                class="step-form"
                @click.stop
              >
                <el-form-item
                  title="步骤说明"
                  label="remark"
                  :class="{
                    'is-focused':
                      activeFocus &&
                      activeFocus.stepIndex === index &&
                      activeFocus.paramName === 'remark'
                  }"
                >
                  <el-input
                    v-model="element.remark"
                    placeholder="请填写步骤说明"
                    @focus="updateActiveFocus(index, 'remark')"
                  />
                </el-form-item>
                <el-form-item
                  v-for="param in getActionInfo(element.action)?.params || []"
                  :key="param.name"
                  :label="param.name"
                  :title="param.description || '暂无说明'"
                  :class="{
                    'is-focused':
                      activeFocus &&
                      activeFocus.stepIndex === index &&
                      activeFocus.paramName === param.name
                  }"
                >
                  <el-input
                    v-if="param.type === 'string'"
                    v-model="element[param.name]"
                    :placeholder="param.description"
                    @focus="updateActiveFocus(index, param.name)"
                  />
                  <el-input-number
                    v-else-if="param.type === 'int' || param.type === 'float'"
                    v-model="element[param.name]"
                    :placeholder="param.description"
                    controls-position="right"
                    class="w-full"
                    @change="updateActiveFocus(index, param.name)"
                    @focus="updateActiveFocus(index, param.name)"
                  />
                  <el-switch
                    v-else-if="param.type === 'boolean'"
                    v-model="element[param.name]"
                    @change="updateActiveFocus(index, param.name)"
                  />
                  <el-select
                    v-else-if="param.type === 'enum'"
                    v-model="element[param.name]"
                    :placeholder="param.description"
                    @focus="updateActiveFocus(index, param.name)"
                  >
                    <el-option
                      v-for="option in param.options"
                      :key="option.value"
                      :label="option.label"
                      :value="option.value"
                    />
                  </el-select>
                  <el-input
                    v-else-if="param.type === 'object'"
                    :model-value="
                      typeof element[param.name] === 'object'
                        ? JSON.stringify(element[param.name], null, 2)
                        : element[param.name]
                    "
                    type="textarea"
                    :autosize="{ minRows: 2, maxRows: 10 }"
                    :placeholder="param.description"
                    @update:model-value="
                      val => {
                        try {
                          // 尝试解析为JSON，如果成功则更新为对象
                          element[param.name] = JSON.parse(val);
                        } catch (e) {
                          // 如果解析失败（例如，用户正在输入），则暂时将其存为字符串
                          element[param.name] = val;
                        }
                      }
                    "
                    @focus="updateActiveFocus(index, param.name)"
                  />
                  <el-input
                    v-else
                    v-model="element[param.name]"
                    :placeholder="`未知类型: ${param.type}`"
                    @focus="updateActiveFocus(index, param.name)"
                  />
                  <!-- yolo class 弹出按钮-->
                  <el-button
                    v-if="param.name === 'yolo_class'"
                    :icon="MagicStick"
                    type="text"
                    @click.stop="$emit('open-yolo-selector')"
                  >
                    辅助选择
                  </el-button>
                </el-form-item>
              </el-form>
            </el-collapse-transition>
          </div>
        </template>
        <template #footer>
          <el-empty
            v-if="steps.length === 0"
            description="从左侧拖拽或点击添加一个动作"
            class="mt-4"
          />
        </template>
      </draggable>
    </el-scrollbar>
  </div>
</template>

<style scoped lang="scss">
.steps-list {
  .step-wrapper {
    margin-bottom: 8px;
    width: 100%;
    border-radius: 6px;
    transition: box-shadow 0.3s ease-in-out;
    overflow: hidden;
    border: 1px solid transparent;
    &.is-active {
      border-color: #409eff;
      background-color: #ffffff;
    }
  }

  .step-header {
    display: flex;
    align-items: center;
    width: 100%;
    height: 42px;
    padding: 0 12px;
    background-color: #f9fafb;
    border: 1px solid #e4e7ed;
    border-radius: 6px;
    cursor: pointer;
    user-select: none;
    transition: all 0.2s;

    &:hover {
      border-color: #cdd0d6;
      background-color: #f4f4f5;
    }

    &.is-active {
      border-color: #409eff;
      background-color: #ecf5ff;
      border-bottom-left-radius: 0;
      border-bottom-right-radius: 0;
    }
  }
  .drag-handle {
    cursor: grab;
    margin-right: 8px;
    color: #909399;
  }

  .step-index {
    font-weight: bold;
    margin-right: 10px;
    color: #409eff;
  }

  .action-icon {
    font-size: 18px;
    margin-right: 8px;
    color: #409eff;
  }

  .step-title {
    flex: 1;
    min-width: 0;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-right: 10px;
  }

  .delete-btn,
  .copy-btn {
    margin-left: 10px;
    opacity: 0;
    transition: opacity 0.2s ease-in-out;
  }

  .step-header:hover .delete-btn,
  .step-header:hover .copy-btn {
    opacity: 1;
  }

  .step-form {
    padding: 12px 16px;
    background-color: #fafcff;
    border: 1px solid #409eff;
    border-top: none;
    border-bottom-left-radius: 6px;
    border-bottom-right-radius: 6px;
  }

  .step-form .el-form-item {
    margin-bottom: 12px;
  }

  .step-form .el-form-item.is-focused {
    :deep(.el-form-item__label) {
      font-weight: bold !important;
      color: #409eff !important;
    }
    :deep(.el-input__wrapper),
    :deep(.el-input-number) {
      box-shadow: 0 0 0 1px #409eff inset;
    }
  }

  :deep(.sortable-ghost) {
    height: 42px;
    margin-bottom: 8px;
    opacity: 0.5;
    background: #c8ebfb;
    border: 1px dashed #409eff;
    border-radius: 8px;
    & > * {
      visibility: hidden;
    }
  }

  :deep(.sortable-drag) {
    transform: rotate(1deg);
    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15);
    opacity: 0.9;
    cursor: grabbing;
  }
}
</style>
