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
        <div class="p-1 script-row" style="height: 80px">
          <div class="row-inner">
            <!-- 拖拽图标 -->
            <div class="stepHandle">
              <el-icon class="drag-svg"><TasksDragIcon /></el-icon>
            </div>

            <!-- 序号圆圈 -->
            <div class="index-bubble">{{ index + 1 }}</div>

            <!-- 名称列 -->
            <div class="info-col">
              <span v-if="element.name" class="item-title">{{
                element.name
              }}</span>
              <span v-else class="item-deleted"
                >脚本({{ element.id }})已被删除, 请注意移除</span
              >
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

const props = defineProps<{ modelValue: any[] }>();
const emit = defineEmits(["update:modelValue"]);
// internal copy to avoid mutating parent's array in-place
const internal = ref<any[]>(Array.isArray(props.modelValue) ? [...props.modelValue] : []);

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
  (val) => {
    const arr = Array.isArray(val) ? val : [];
    if (!sameById(arr, internal.value)) {
      internal.value = [...arr];
    }
  },
  { deep: true }
);

// sync from internal -> parent via emit (only when different)
watch(
  internal,
  (val) => {
    const modelVal = Array.isArray(props.modelValue) ? props.modelValue : [];
    if (!sameById(val, modelVal)) {
      emit("update:modelValue", [...val]);
    }
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
  height: 100%;
  border: 1px solid #e5e7ea;
  border-radius: 8px;
  display: flex;
  align-items: center;
  padding: 8px 12px;
  background: #fff;
}

.stepHandle {
  width: 40px;
  display: flex;
  justify-content: center;
  align-items: center;
  cursor: move;
  color: #9aa0a6;
}

.index-bubble {
  margin-left: 8px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f3f4f6;
  color: #555;
  font-weight: 600;
}

.info-col {
  margin-left: 12px;
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

.item-deleted {
  color: #d9534f;
}

.actions-col {
  margin-left: 12px;
}
</style>
