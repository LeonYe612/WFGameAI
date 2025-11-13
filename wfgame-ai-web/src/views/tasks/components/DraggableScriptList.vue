<template>
  <div class="draggable-root">
    <draggable
      v-model="internal"
      item-key="id"
      chosen-class="chosen"
      force-fallback="true"
      animation="300"
      handle=".stepHandle"
    >
      <template #item="{ element, index }">
        <div class="p-1 script-row">
          <div :class="['row-inner', index > 0 ? 'other-group' : '']">
            <!-- 拖拽图标 -->
            <div class="stepHandle">
              <el-icon class="drag-svg"><TasksDragIcon /></el-icon>
            </div>

            <!-- 序号圆圈 -->
            <div class="index-bubble">{{ index + 1 }}</div>

            <!-- 名称与参数同一行 -->
            <div class="info-col">
              <div class="name-params-row">
                <el-tooltip
                  v-if="element.name"
                  :content="element.name"
                  placement="top"
                  effect="light"
                >
                  <span class="item-title item-title-large">
                    {{ element.name }}
                  </span>
                </el-tooltip>
                <span v-else class="item-deleted">
                  脚本({{ element.id }})已被删除, 请注意移除
                </span>
                <div class="params-row">
                  <div class="param-field">
                    <span class="param-label">循环次数</span>
                    <el-input-number
                      v-model="localParams[element.id].loopCount"
                      :min="1"
                      :step="1"
                      size="small"
                      controls-position="right"
                      class="compact-input"
                    />
                  </div>
                  <div class="param-field">
                    <span class="param-label">最大时长(秒)</span>
                    <el-input-number
                      v-model="localParams[element.id].maxDuration"
                      :min="1"
                      :step="10"
                      size="small"
                      controls-position="right"
                      :value-on-clear="null"
                      :precision="0"
                      class="compact-input"
                    />
                  </div>
                </div>
              </div>
            </div>

            <!-- 操作列 -->
            <div class="actions-col">
              <el-button size="small" type="danger" @click="remove(index)"
                >移除</el-button
              >
            </div>
          </div>
        </div>
      </template>
    </draggable>
  </div>
</template>

<script setup lang="ts">
import TasksDragIcon from "@/assets/svg/tasks_drag.svg?component";
import { ref, watch } from "vue";
import draggable from "vuedraggable";

type Param = {
  loopCount: number;
  maxDuration: number | null;
};
type ParamsMap = Record<number, Param>;

const props = defineProps<{ modelValue: any[]; paramsMap?: ParamsMap }>();
const emit = defineEmits(["update:modelValue", "update:paramsMap"]);
// internal copy to avoid mutating parent's array in-place
const internal = ref<any[]>(
  Array.isArray(props.modelValue) ? [...props.modelValue] : []
);

// 本地参数映射，双向同步到父组件
const localParams = ref<ParamsMap>({});

const ensureDefaults = (ids: number[], src: ParamsMap): ParamsMap => {
  const next: ParamsMap = {};
  for (const id of ids) {
    const cur = src[id];
    next[id] = {
      loopCount: cur?.loopCount && cur.loopCount > 0 ? cur.loopCount : 1,
      maxDuration:
        cur?.maxDuration && cur.maxDuration > 0 ? cur.maxDuration : null
    };
  }
  return next;
};

function sameById(a: any[], b: any[]) {
  if (!Array.isArray(a) || !Array.isArray(b)) return false;
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) {
    if ((a[i] && a[i].id) !== (b[i] && b[i].id)) return false;
  }
  return true;
}

// sync from parent prop -> internal (only when different)
watch(
  () => props.modelValue,
  val => {
    const arr = Array.isArray(val) ? val : [];
    if (!sameById(arr, internal.value)) {
      internal.value = [...arr];
    }
    // 同步 paramsMap：确保每个脚本有参数项，且移除已删除脚本的项
    const ids = arr
      .map((s: any) => Number(s?.id))
      .filter((n: any) => Number.isFinite(n));
    const incoming = (props.paramsMap || {}) as ParamsMap;
    localParams.value = ensureDefaults(ids, incoming);
  },
  { deep: true }
);

// sync from internal -> parent via emit (only when different)
watch(
  internal,
  val => {
    const modelVal = Array.isArray(props.modelValue) ? props.modelValue : [];
    if (!sameById(val, modelVal)) {
      emit("update:modelValue", [...val]);
    }
    // 同步本地参数给父组件
    emit("update:paramsMap", { ...localParams.value });
  },
  { deep: true }
);

// 当本地参数变化时，通知父组件（保持与脚本顺序变更解耦）
watch(
  () => localParams.value,
  () => {
    emit("update:paramsMap", { ...localParams.value });
  },
  { deep: true }
);

function remove(idx: number) {
  internal.value.splice(idx, 1);
}
</script>

<style scoped>
.draggable-root {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.chosen {
  background-color: #f5f5f5;
  border: dashed 1px #dae8ff !important;
  border-radius: 10px;
}

.script-row {
  width: 100%;
}

.row-inner {
  min-height: 64px;
  border: 1px solid #e5e7ea;
  border-radius: 8px;
  display: flex;
  align-items: center;
  padding: 8px 12px;
  background: #fff;
}

.other-group {
  background: #f9f9f9; /* 淡灰 */
}

.stepHandle {
  width: 28px;
  display: flex;
  justify-content: center;
  align-items: center;
  cursor: move;
  color: #9aa0a6;
}

.index-bubble {
  margin-left: 6px;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f3f4f6;
  color: #555;
  font-weight: 600;
}

.info-col {
  margin-left: 10px;
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  overflow: hidden;
}

.item-title {
  color: #333;
  font-weight: 600;
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-title-large {
  font-size: 16px;
  font-weight: 700;
  color: #222;
}

.item-deleted {
  color: #d9534f;
}

.name-params-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.params-row {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-left: auto;
}

.param-field {
  display: flex;
  align-items: center;
  gap: 6px;
}

.param-label {
  font-size: 12px;
  color: #666;
  white-space: nowrap;
}

.actions-col {
  margin-left: 12px;
}

/* 将数字输入框宽度缩小约 40%（默认 ~180px -> 110px 左右） */
.compact-input {
  width: 80px;
}
</style>
