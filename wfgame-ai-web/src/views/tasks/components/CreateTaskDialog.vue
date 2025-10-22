<template>
  <div>
    <el-dialog
      :model-value="props.visible"
      :title="isEdit ? '编辑任务' : '新建任务'"
      width="1000px"
      :close-on-click-modal="true"
      @update:model-value="onDialogVisibleChange"
      @close="handleCancel"
    >
      <div class="dialog-content">
        <div class="dialog-content">
          <el-form
            ref="formRef"
            :model="formData"
            :rules="taskFormRules"
            label-width="75px"
            label-position="left"
            size="large"
          >
            <div class="dialog-flex-row">
              <!-- 左侧：任务信息表单卡片 -->
              <el-card shadow="always" class="form-card form-card-flex">
                <template #header>
                  <span class="form-title">基本信息</span>
                </template>
                <div class="form-content form-content-flex">
                  <div class="form-fields">
                    <el-form-item label="任务名称" prop="name">
                      <el-input
                        v-model="formData.name"
                        placeholder="请输入任务名称"
                        maxlength="50"
                        show-word-limit
                        size="large"
                        clearable
                      />
                    </el-form-item>

                    <el-form-item label="任务类型" prop="task_type">
                      <el-select
                        v-model="formData.task_type"
                        placeholder="请选择任务类型"
                        style="width: 100%"
                      >
                        <el-option
                          v-for="option in taskTypeOptions.filter(
                            opt => opt.value !== null
                          )"
                          :key="option.value"
                          :label="option.label"
                          :value="option.value"
                        >
                          <div
                            style="display: flex; align-items: center; gap: 8px"
                          >
                            <el-icon>
                              <component
                                :is="taskTypeConfig[option.value]?.icon"
                              />
                            </el-icon>
                            {{ option.label }}
                          </div>
                        </el-option>
                      </el-select>
                    </el-form-item>

                    <el-form-item
                      label="运行类型"
                      prop="run_type"
                    >
                      <el-select
                        v-model="formData.run_type"
                        placeholder="请选择运行类型"
                        style="width: 100%"
                      >
                        <el-option
                          v-for="option in taskRunTypeOptions.filter(
                            opt => opt.value !== null
                          )"
                          :key="option.value"
                          :label="option.label"
                          :value="option.value"
                        >
                          <div
                            style="display: flex; align-items: center; gap: 8px"
                          >
                            <el-icon>
                              <component
                                :is="runTypeConfig[option.value]?.icon"
                              />
                            </el-icon>
                            {{ option.label }}
                          </div>
                        </el-option>
                      </el-select>
                    </el-form-item>
                    <el-form-item
                      v-if="formData.run_type === 3"
                      label="计划时间"
                      prop="run_info.schedule"
                      style="padding-left: 1em; padding-right: 1em;"
                      size="small"
                      class="schedule-form-item-bg"
                    >
                      <el-date-picker
                        v-model="formData.run_info.schedule"
                        type="datetime"
                        value-format="YYYY-MM-DD HH:mm:ss"
                        placeholder="请选择日期和时间"
                        :disabled-date="dt => dt.getTime() < Date.now() - 8.64e7"
                        style="width: 100%"
                      />
                    </el-form-item>
                    <el-form-item label="目标设备" prop="device_ids">
                      <el-select
                        v-model="formData.device_ids"
                        multiple
                        placeholder="请选择目标设备"
                        style="width: 100%"
                        filterable
                        size="large"
                      >
                        <el-option
                          v-for="device in deviceOptions"
                          :key="device.value"
                          :label="device.label"
                          :value="device.value"
                        />
                      </el-select>
                    </el-form-item>

                    <el-form-item label="选择脚本" prop="script_ids">
                      <el-button
                        type="primary"
                        size="default"
                        @click.prevent="scriptSelectorVisible = true"
                      >
                        选择脚本
                      </el-button>
                    </el-form-item>
                  </div>
                  <el-form-item label="任务描述" class="form-desc-item">
                    <el-input
                      v-model="formData.description"
                      type="textarea"
                      :autosize="{ minRows: 3, maxRows: 3 }"
                      placeholder="请输入任务描述（可选）"
                      maxlength="200"
                      show-word-limit
                      size="large"
                    />
                  </el-form-item>
                </div>
              </el-card>

              <!-- 右侧：脚本选择区卡片（仅展示和拖拽，不做表单校验） -->
              <div class="dialog-vsplit" />
              <el-card shadow="always" class="script-card">
                <template #header>
                  <span class="script-title">脚本编辑（共 {{ scripts.length }} 个）</span>
                </template>
                <div class="script-content-row">
                    <div class="script-list-col">
                    <DraggableScriptList v-model="scripts" @update:modelValue="onScriptsChanged" />
                  </div>
                </div>
              </el-card>
            </div>
          </el-form>
        </div>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button type="default" @click="handleCancel">取消</el-button>
          <el-button type="primary" @click="handleSubmit">
            {{ isEdit ? "保存" : "创建" }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  <ScriptSelector
    v-model="scriptSelectorVisible"
    @confirm="onScriptSelectorConfirm"
    width="60vw"
    contentHeight="60vh"
  />
  </div>
</template>

<script setup lang="ts">
import { scriptApi, type ScriptItem } from "@/api/scripts";
import ScriptSelector from "@/views/common/selectors/scriptSelector/index.vue";
import { ElMessage, type FormInstance } from "element-plus";
import { nextTick, ref, watch } from "vue";
import {
    runTypeConfig,
    taskFormRules,
    taskRunTypeOptions,
    taskTypeConfig,
    taskTypeOptions
} from "../utils/rules";
import type {
    TaskFormData,
    TaskFormDialogEmits,
    TaskFormDialogProps
} from "../utils/types";
import DraggableScriptList from "./DraggableScriptList.vue";

// 表单引用
const formRef = ref<FormInstance>();

// 表单数据 - 使用类型安全的默认值（避免 null 传入 Element Plus 控件）
const formData = ref<TaskFormData>({
  name: "",
    task_type: null,
    run_type: null,
  run_info: { schedule: "" },
  device_ids: [],
  description: "",
  script_ids: []
});

// 脚本多选与拖拽 — 使用共享组件和真实 API 数据
const scripts = ref<ScriptItem[]>([]); // the actual selected script objects (order matters)
const scriptSelectorVisible = ref(false);
// 防止 scripts <-> formData.script_ids 之间的循环更新
const syncingScripts = ref(false);
// 当 scripts watcher 主动更新 formData.script_ids 时，设置该标志以避免 formData watcher 再触发加载
const updatingIds = ref(false);
// 记录上次加载过的 id 顺序，避免重复加载导致循环
const lastLoadedIds = ref<number[]>([]);
// global lock to prevent re-entrant sync cycles
const syncLock = ref(false);

// Handle confirm from ScriptSelector: set selected scripts and sync ids
async function onScriptSelectorConfirm(rows: ScriptItem[]) {
  if (!Array.isArray(rows)) return;
  // we already have full script objects from the selector, set them directly
  syncLock.value = true;
  scripts.value = rows;
  // avoid the formData watcher re-loading these ids immediately
  updatingIds.value = true;
  const ids = rows.map(r => r.id as number);
  formData.value.script_ids = ids;
  // mark as last loaded to avoid redundant fetch
  lastLoadedIds.value = ids.slice();
  await nextTick();
  updatingIds.value = false;
  syncLock.value = false;
  scriptSelectorVisible.value = false;
}

// end onScriptSelectorConfirm



// load full script objects for given ids
const loadScriptsByIds = async (ids: number[]) => {
  if (!ids || ids.length === 0) {
    scripts.value = [];
    return;
  }
  try {
    const promises = ids.map(id =>
      scriptApi
        .detail(id)
        .then(res => res.data)
        .catch(() => null)
    );
    const results = (
      await Promise.all(promises)
    ).filter(Boolean) as ScriptItem[];
    // preserve the incoming order
    const ordered = ids
      .map(id => results.find(r => r.id === id))
      .filter(Boolean) as ScriptItem[];
    // mark that we're programmatically setting scripts to avoid watcher feedback
    syncLock.value = true;
    syncingScripts.value = true;
    scripts.value = ordered;
    // record loaded ids to avoid re-loading the same set
    lastLoadedIds.value = ids.slice();
    // clear flag after DOM update so subsequent user-driven changes sync normally
    await nextTick();
    syncingScripts.value = false;
    syncLock.value = false;
  } catch (e) {
    console.error("Failed to load scripts by ids:", e);
  }
};

// sync: when formData.script_ids changes, load script objects
watch(
  () => formData.value.script_ids,
  ids => {
    // if ids are being updated by scripts watcher or a programmatic sync, skip to avoid recursion
    if (updatingIds.value || syncLock.value) return;
    // ensure we have numeric ids
    const idsArr = (ids || [])
      .map((n: any) => Number(n))
      .filter((n: number) => Number.isFinite(n));
    // avoid re-loading the same ids/order
    const same =
      idsArr.length === lastLoadedIds.value.length &&
      idsArr.every((v, i) => v === lastLoadedIds.value[i]);
    if (same) return;
    loadScriptsByIds(idsArr as number[]);
  },
  { immediate: true, flush: "post" }
);

// sync: when scripts array (order/contents) changes, update formData.script_ids
// handle updates coming from the DraggableScriptList child (user reorder/remove)
async function onScriptsChanged(updated: ScriptItem[]) {
  // if the child update corresponds to a programmatic load, skip
  if (syncingScripts.value) return;
  const ids = Array.isArray(updated) ? updated.map(s => s.id as number) : [];
  const cur = formData.value.script_ids || [];
  const different = ids.length !== cur.length || ids.some((id, i) => id !== cur[i]);
  if (different) {
    updatingIds.value = true;
    formData.value.script_ids = ids;
    // record lastLoadedIds so the form watcher doesn't re-load unnecessarily
    lastLoadedIds.value = ids.slice();
    await nextTick();
    updatingIds.value = false;
  }
}

// DraggableScriptList emits updates via v-model; no explicit onDragEnd required

// Props & Emits（由父组件完全控制可见性）
const props = defineProps<
  TaskFormDialogProps & { fillValues?: Partial<TaskFormData> }
>();
const emit = defineEmits<TaskFormDialogEmits>();

// 对话框可见性变更时，向父级同步（配合 v-model:visible）
const onDialogVisibleChange = (val: boolean) => {
  emit("update:visible", val);
};

// 是否编辑模式（新建任务始终为 false）
const isEdit = ref(false);

// 设备选项 (模拟数据，实际应该从API获取)
const deviceOptions = ref([
  { label: "OnePlus 9 Pro", value: 1 },
  { label: "Samsung Galaxy S21", value: 2 },
  { label: "Xiaomi Mi 11", value: 3 }
]);

// 重置表单
const resetForm = () => {
  // 新建时自动填充任务名称
  let defaultName = "";
  if (!isEdit.value) {
    defaultName = `task_${Date.now()}`;
  }
  // 合并并确保类型安全（props.fillValues 可能为部分字段）
  // Normalize incoming values to the types expected by the form controls
  const incoming = props.fillValues || {};
  const toNumber = (v: any): number | null => {
    if (v === undefined || v === null || v === "") return null;
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  };
  const toNumberArray = (v: any): number[] => {
    if (v === undefined || v === null || v === "") return [];
    if (Array.isArray(v)) return v.map((x: any) => {
      const n = Number(x);
      return Number.isFinite(n) ? n : null;
    }).filter((n: any) => n != null) as number[];
    return String(v)
      .split(",")
      .map(s => {
        const n = Number(s.trim());
        return Number.isFinite(n) ? n : null;
      })
      .filter((n: any) => n != null) as number[];
  };

  formData.value = {
    // 如果父级通过 fillValues 传入了 name，优先使用它；否则使用默认名称
    name: incoming.name ? String(incoming.name) : defaultName,
    task_type: toNumber(incoming.task_type),
    run_type: toNumber(incoming.run_type),
    run_info: {
      schedule: incoming.run_info && incoming.run_info.schedule ? String(incoming.run_info.schedule) : ""
    },
    device_ids: toNumberArray(incoming.device_ids),
    description: incoming.description ? String(incoming.description) : "",
    script_ids: toNumberArray(incoming.script_ids)
  };
  // debug logs removed
  nextTick(() => {
    formRef.value?.clearValidate();
  });
};

// 弹窗打开时重置表单，关闭时也重置，防止残留数据
watch(
  () => props.visible,
  v => {
    if (v) {
      resetForm();
    }
  }
  , { immediate: true }
);

// 如果父组件更新了 fillValues（例如路由解析后再赋值），也应重新 reset 表单
watch(
  () => props.fillValues,
  () => {
    // 仅当弹窗打开时才同步，以避免不必要覆盖
    if (props.visible) resetForm();
  },
  { deep: true }
);

// 处理提交
const handleSubmit = async () => {
  try {
    await formRef.value?.validate();
    emit("submit", { ...formData.value });
    emit("update:visible", false); // 提交成功后自动关闭
  } catch (error) {
    ElMessage.warning("请完善表单信息");
  }
};

// 处理取消
const handleCancel = () => {
  emit("update:visible", false);
  emit("cancel");
};

</script>

<style scoped>
/* 触发按钮完全由父组件控制，此处不再管理 header 样式 */
/* 主体横向布局 */
.dialog-flex-row {
  display: flex;
  flex-direction: row;
  gap: 0;
  align-items: stretch; /* ensure children cards stretch to same height */
  min-height: 410px;
}

.form-card-flex {
  flex: 0 0 35%;
  min-width: 220px;
  max-width: 400px;
  border-radius: 12px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.1);
  margin-right: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  align-items: stretch;
  height: 520px; /* match script-card height */
}

.form-content-flex {
  padding: 4px 12px 12px 12px;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  align-items: stretch;
  height: 100%;
}

.form-fields {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  gap: 0;
}

.form-desc-item {
  margin-top: 12px;
  margin-bottom: 0;
  width: 100%;
  /* 保证描述栏始终在底部 */
}

.dialog-vsplit {
  width: 1px;
  min-height: 410px;
  background: #e5e6eb;
  margin: 0 32px;
  border-radius: 1px;
}

.script-card {
  flex: 0 0 59%;
  min-width: 260px;
  max-width: 700px;
  border-radius: 12px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.1);
  padding: 0;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  align-items: stretch;
  height: 520px; /* fixed card height */
  overflow: hidden;
}

.script-content-row {
  display: flex;
  flex-direction: row;
  gap: 16px;
  align-items: stretch; /* stretch children to full card body height */
  height: 100%;
}

.script-list-col {
  flex: 2 1 0;
  min-width: 180px;
  display: flex;
  flex-direction: column;
  overflow: auto; /* scroll when many scripts */
  padding: 12px;
  min-height: 0; /* allow flex child to shrink and enable scrolling */
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* 计划时间选择框整体底色（el-form-item） */
.schedule-form-item-bg {
  background: #fff1f0 !important;
  border-radius: 8px;
  min-height: 40px;
  padding: 4px 0 4px 0;
  display: flex;
  align-items: center;
}

/* 收紧 el-card header 与 body 间距，仅作用于本组件内的卡片 */
:deep(.form-card > .el-card__header),
:deep(.script-card > .el-card__header) {
  padding-top: 7px !important;
  padding-bottom: 6px !important;
  padding-left: 12px !important;
  padding-right: 12px !important;
  display: flex;
  align-items: center;
  justify-content: center;
}

:deep(.form-card > .el-card__body),
:deep(.script-card > .el-card__body) {
  padding-top: 7px !important;
  padding-left: 5px !important;
  padding-right: 10px !important;
}

/* Make card bodies fill their parent's height and scroll when needed */
:deep(.form-card > .el-card__body) {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  overflow: auto;
}
:deep(.script-card > .el-card__body) {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  overflow: auto;
}

/* Tighten label and control spacing in Element Plus form items */
:deep(.form-card .el-form-item__label) {
  padding-right: 8px !important;
}

/* 给非必填项添加隐藏星号占位，保证与必填项对齐 */
:deep(.form-card .el-form-item__label)::before {
  content: "*";
  visibility: hidden;
  margin-right: 4px;
}

:deep(.form-card .el-form-item.is-required .el-form-item__label)::before {
  visibility: visible;
  color: var(--el-color-danger);
}

/* 禁用描述文本域的手动拖拽放大，大小由 autosize 控制 */
:deep(.form-card .el-textarea__inner) {
  resize: none;
}
</style>
