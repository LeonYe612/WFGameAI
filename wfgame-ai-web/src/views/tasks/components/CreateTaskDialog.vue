<template>
  <div>
    <el-dialog
      :model-value="props.visible"
      :title="isEdit ? '编辑任务' : '新建任务'"
      width="1100px"
      :close-on-click-modal="true"
      @update:model-value="onDialogVisibleChange"
      @close="handleCancel"
      top="8vh"
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

                    <el-form-item label="运行类型" prop="run_type">
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
                      style="padding-left: 1em; padding-right: 1em"
                      size="small"
                      class="schedule-form-item-bg"
                    >
                      <el-date-picker
                        v-model="formData.run_info.schedule"
                        type="datetime"
                        value-format="YYYY-MM-DD HH:mm:ss"
                        placeholder="请选择日期和时间"
                        :disabled-date="
                          dt => dt.getTime() < Date.now() - 8.64e7
                        "
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
                        @visible-change="onDeviceDropdownVisible"
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
                    <!-- 将任务描述移入同一列，缩短与“选择脚本”的距离 -->
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
                </div>
              </el-card>

              <!-- 右侧：脚本选择区卡片（含每脚本参数输入与预览） -->
              <div class="dialog-vsplit" />
              <el-card shadow="always" class="script-card">
                <template #header>
                  <span class="script-title"
                    >脚本编辑（共 {{ scripts.length }} 个）</span
                  >
                </template>
                <div class="script-content">
                  <div class="script-list-scroll">
                    <DraggableScriptList
                      v-model="scripts"
                      v-model:paramsMap="paramsMap"
                      @update:modelValue="onScriptsChanged"
                    />
                  </div>
                </div>
              </el-card>
            </div>
            <!-- 底部：全部命令独立卡片，放在基本信息和脚本编辑下方 -->
            <el-card shadow="always" class="preview-card">
              <div class="preview-cmd-container">
                <div class="preview-cmd-line">
                  <span class="preview-label">执行命令：</span>
                  <span class="preview-base">{{ previewParts.base }}</span>

                  <div class="preview-arg-list preview-arg-list-scroll">
                    <span
                      v-for="(g, idx) in previewParts.groups"
                      :key="idx"
                      class="preview-arg-badge"
                      :style="{ background: argColor(idx), color: '#0b2545' }"
                    >
                      {{ g }}
                    </span>
                  </div>
                </div>
              </div>
            </el-card>
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
import { listDevices, type DeviceItem } from "@/api/devices";
import { scriptApi, type ScriptItem } from "@/api/scripts";
import { superRequest } from "@/utils/request";
import ScriptSelector from "@/views/common/selectors/scriptSelector/index.vue";
import { ElMessage, type FormInstance } from "element-plus";
import { computed, nextTick, ref, watch } from "vue";
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
  // 采用“追加”而非“替换”：保留已有，追加新选择的去重项
  const existing = Array.isArray(scripts.value) ? scripts.value.slice() : [];
  const exists = new Set(existing.map(s => Number(s.id)));
  const append = rows.filter(r => !exists.has(Number(r.id)));
  const combined = existing.concat(append);
  scripts.value = combined;
  // avoid the formData watcher re-loading these ids immediately
  updatingIds.value = true;
  const ids = combined.map(r => r.id as number);
  formData.value.script_ids = ids;
  // 初始化每脚本参数
  ensureParamsFor(ids);
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
    const results = (await Promise.all(promises)).filter(
      Boolean
    ) as ScriptItem[];
    // preserve the incoming order
    const ordered = ids
      .map(id => results.find(r => r.id === id))
      .filter(Boolean) as ScriptItem[];
    // mark that we're programmatically setting scripts to avoid watcher feedback
    syncLock.value = true;
    syncingScripts.value = true;
    scripts.value = ordered;
    // 初始化每脚本参数
    const idsOnly = ordered.map(o => o.id as number);
    ensureParamsFor(idsOnly);
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
  const different =
    ids.length !== cur.length || ids.some((id, i) => id !== cur[i]);
  if (different) {
    updatingIds.value = true;
    formData.value.script_ids = ids;
    // record lastLoadedIds so the form watcher doesn't re-load unnecessarily
    lastLoadedIds.value = ids.slice();
    // 确保每脚本参数存在
    ensureParamsFor(ids);
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

// 设备选项（从后端获取最新设备列表）
const deviceOptions = ref<{ label: string; value: number }[]>([]);
// 设备ID(主键) -> 序列号(device_id) 映射，用于拼接预览命令的 --device serial
const deviceIdToSerial = ref<Record<number, string>>({});

// 拉取设备列表并转换为下拉选项
const fetchDevices = async () => {
  await superRequest({
    apiFunc: listDevices,
    apiParams: { available_for_me: true },
    onSucceed: (data: DeviceItem[]) => {
      const arr = Array.isArray(data) ? data : [];
      const options = arr.map(d => ({
        // 使用设备主键作为提交值；显示 device_id 与型号品牌，便于选择
        value: Number(d.id as number),
        label: [
          d.device_id,
          [d.brand, d.model].filter(Boolean).join(" "),
          d.status === "online" && d.current_user_name
            ? `占用:${d.current_user_name}`
            : null
        ]
          .filter(Boolean)
          .join(" | ")
      }));
      deviceOptions.value = options;
      // 构建 id -> serial 映射
      const map: Record<number, string> = {};
      for (const d of arr) {
        const key = Number(d.id as number);
        if (Number.isFinite(key) && d.device_id) {
          map[key] = String(d.device_id);
        }
      }
      deviceIdToSerial.value = map;
    }
  });
};

// 仅在下拉被展开时拉取一次；收起后重置标记，下一次展开再拉取
const deviceDropdownFetched = ref(false);
const deviceFetchLoading = ref(false);
const onDeviceDropdownVisible = async (visible: boolean) => {
  if (visible) {
    if (deviceDropdownFetched.value || deviceFetchLoading.value) return;
    deviceFetchLoading.value = true;
    try {
      await fetchDevices();
      deviceDropdownFetched.value = true;
    } finally {
      deviceFetchLoading.value = false;
    }
  } else {
    // 关闭下拉后，允许下一次打开再次拉取
    deviceDropdownFetched.value = false;
  }
};

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
    if (Array.isArray(v))
      return v
        .map((x: any) => {
          const n = Number(x);
          return Number.isFinite(n) ? n : null;
        })
        .filter((n: any) => n != null) as number[];
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
      schedule:
        incoming.run_info && incoming.run_info.schedule
          ? String(incoming.run_info.schedule)
          : ""
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
      // 确保预览命令能拿到设备序列号映射
      if (!deviceDropdownFetched.value) {
        fetchDevices();
        deviceDropdownFetched.value = true;
      }
    }
  },
  { immediate: true }
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

    // 构建新的创建载荷：脚本/设备使用对象数组携带附加信息
    const scriptItems = (Array.isArray(scripts.value) ? scripts.value : []).map(
      s => {
        const id = Number(s.id);
        const cfg = paramsMap.value[id] || { loopCount: 1, maxDuration: null };
        const item: Record<string, any> = {
          id,
          "loop-count": Number(cfg.loopCount) > 0 ? Number(cfg.loopCount) : 1
        };
        if (cfg.maxDuration && Number(cfg.maxDuration) > 0) {
          item["max-duration"] = Number(cfg.maxDuration);
        }
        return item;
      }
    );

    const deviceItems = (
      Array.isArray(formData.value.device_ids)
        ? (formData.value.device_ids as number[])
        : []
    ).map(id => ({
      id: Number(id),
      serial: deviceIdToSerial.value[Number(id)] || ""
    }));

    const payload = {
      name: formData.value.name,
      task_type: formData.value.task_type,
      run_type: formData.value.run_type,
      run_info: formData.value.run_info,
      description: formData.value.description,
      script_ids: scriptItems,
      device_ids: deviceItems,
      // 预留全局参数对象（如需可由上层传入或在此扩展输入项）
      params: {}
    };

    emit("submit", payload as any);
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

// ---------------- 回放参数（构建有序 CLI 参数） ----------------
// 每脚本参数映射：key=脚本ID，value={loopCount,maxDuration}
const paramsMap = ref<
  Record<number, { loopCount: number; maxDuration: number | null }>
>({});

// 确保为当前脚本集初始化/保留参数项
const ensureParamsFor = (ids: number[]) => {
  const next: Record<
    number,
    { loopCount: number; maxDuration: number | null }
  > = {};
  for (const id of ids) {
    const cur = paramsMap.value[id];
    next[id] = {
      loopCount: cur?.loopCount && cur.loopCount > 0 ? cur.loopCount : 1,
      maxDuration:
        cur?.maxDuration && cur.maxDuration > 0 ? cur.maxDuration : null
    };
  }
  paramsMap.value = next;
};

// 保留计算逻辑供预览使用，但不再提交给后端
// 取消提交 script_params 结构，按路径模式由后端解析命令

// 生成 CLI 预览命令按脚本分别展示的逻辑已拆分为 previewParts（每脚本一组），不再保留完整字符串形式

// 将命令拆分为 base (python replay_script.py) 与参数组（每个脚本的一组参数为一组）
const previewParts = computed(() => {
  const toFileName = (s: any): string => {
    if (!s) return "";
    const raw = (s.filename || s.path || s.name || "").toString();
    const base = raw.split(/[\\/]/).pop() || "";
    return base.endsWith(".json") ? base : base ? `${base}.json` : "";
  };

  const ids = Array.isArray(formData.value.device_ids)
    ? (formData.value.device_ids as number[])
    : [];
  const serials = ids
    .map(id => deviceIdToSerial.value[id])
    .filter((s): s is string => !!s && s.length > 0);

  const base = "python replay_script.py";
  const groups: string[] = [];

  // devices: each device its own group
  for (const ser of serials) {
    groups.push(`--device ${ser}`);
  }

  // scripts: group per script including its loop/max-duration
  if (Array.isArray(scripts.value) && scripts.value.length) {
    for (const s of scripts.value) {
      const file = toFileName(s);
      if (!file) continue;
      const cfg = paramsMap.value[Number(s.id)] || {
        loopCount: 1,
        maxDuration: null
      };
      const parts: string[] = [];
      // quote filename if it contains whitespace
      const fileDisplay = /\s/.test(file) ? `"${file}"` : file;
      parts.push(`--script ${fileDisplay}`);
      const lc = Number(cfg.loopCount);
      if (Number.isFinite(lc) && lc > 0) parts.push(`--loop-count ${lc}`);
      const md = cfg.maxDuration != null ? Number(cfg.maxDuration) : null;
      if (md && Number.isFinite(md) && md > 0)
        parts.push(`--max-duration ${md}`);

      groups.push(parts.join(" "));
    }
  }

  return { base, groups };
});

// 颜色调色板（浅色背景，便于分组区分）
const _palette = [
  "#e8f1ff", // blue tint
  "#e8fff0", // green tint
  "#fff7e6", // orange tint
  "#f3e8ff", // purple tint
  "#e8f8ff", // cyan tint
  "#ffe8f1", // pink tint
  "#f0ffe8", // lime tint
  "#e8eaff", // indigo tint
  "#fffbe8", // yellow tint
  "#e8fff9" // teal tint
];

const argColor = (idx: number) => {
  return _palette[idx % _palette.length];
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
  justify-content: space-between; /* distribute extra space to edges so right卡片贴近右侧，与左侧对称 */
}

.form-card-flex {
  /* 左侧基本信息：3/7 比例中的 3 */
  flex: 0 0 30%;
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
  height: 505px; /* match left card height */
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
  gap: 6px; /* 让选择脚本与任务描述更接近一些 */
}

.form-desc-item {
  margin-top: 8px;
  margin-bottom: 0;
  width: 100%;
}

.dialog-vsplit {
  width: 1px;
  min-height: 410px;
  background: #e5e6eb;
  margin: 0 6px; /* 收紧分割线左右空白 */
  border-radius: 1px;
}

.script-card {
  /* 右侧脚本编辑：3/7 比例中的 7 */
  flex: 1 1 70%;
  min-width: 260px;
  max-width: 750px; /* 右侧加宽约 50px */
  border-radius: 12px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.1);
  padding: 0;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  align-items: stretch;
  height: 505px; /* match left card height */
  overflow: hidden;
}

.script-content {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  height: 100%;
}

.script-list-scroll {
  flex: 1 1 auto;
  overflow: auto;
  padding: 12px;
  min-height: 0;
}

/* 底部预览卡片（显示全部命令） */
.preview-card {
  margin-top: 10px;
  border-radius: 12px;
}

.replay-card-wrapper {
  padding: 12px;
}

.replay-card {
  border-radius: 10px;
}

.replay-title {
  font-weight: 600;
}

.replay-form :deep(.el-form-item) {
  margin-bottom: 10px;
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

/* 回放参数卡片 header 样式 */
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
  overflow: hidden; /* 让上方列表区域滚动，底部预览固定 */
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

/* 预览命令文本域不允许拉伸，保持与任务描述一致的交互 */
:deep(.script-card .el-textarea__inner) {
  resize: none;
}

/* 独立预览卡片内的文本域同样不允许拉伸 */
:deep(.preview-card .el-textarea__inner) {
  resize: none;
}

.preview-cmd-container {
  padding: 8px 12px;
}
.preview-cmd-line {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap; /* allow badges to wrap to next line when long */
}
.preview-label {
  font-size: 1.25em;
  font-weight: 700;
  color: #1a237e;
  flex: 0 0 auto;
}
.preview-base {
  font-size: 1em;
  color: #222;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, "Roboto Mono", "Helvetica Neue", monospace;

  white-space: nowrap;
  flex: 0 0 auto;
}
.preview-arg-list {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  padding-left: 6px;
}
.preview-arg-list-scroll {
  max-height: calc(2 * 38px); /* 3 rows, each badge ~38px tall incl. margin */
  overflow-y: auto;
  min-height: 38px;
}
.preview-arg-badge {
  padding: 6px 10px;
  border-radius: 8px;

  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, "Roboto Mono", monospace;

  font-size: 0.95em;
  white-space: nowrap;
  box-shadow: 0 1px 0 rgba(0, 0, 0, 0.03);
}

.preview-cmd-highlight {
  background: linear-gradient(90deg, #e3f0ff 0%, #f7fbff 100%);
  border-radius: 8px;
  padding: 10px 12px;
  margin: 4px 0 0 0;
}
.preview-cmd-input :deep(.el-textarea__inner) {
  font-size: 1.25em;
  font-weight: bold;
  background: transparent;
  color: #1a237e;
  border: none;
  box-shadow: none;
}
</style>
