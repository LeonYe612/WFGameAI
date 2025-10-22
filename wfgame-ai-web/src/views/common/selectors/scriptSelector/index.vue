<script setup lang="ts">
import CategorySelector from "@/views/scripts/list/components/categorySelector.vue";
import ScriptListTable from "@/views/scripts/list/components/scriptListTable.vue";
import { ref, nextTick, computed } from "vue";
import { type ScriptItem } from "@/api/scripts";

defineOptions({
  name: "ScriptSelector"
});

const props = defineProps({
  modelValue: {
    type: Boolean,
    required: true
  },
  title: {
    type: String,
    default: "请选择："
  },
  // allow caller to specify dialog width (e.g. '60vw' or '800px')
  width: {
    type: String,
    default: "80vw"
  },
  // allow caller to specify inner content height to avoid auto-stretch
  contentHeight: {
    type: String,
    default: "60vh"
  }
});
const emit = defineEmits<{
  (e: "update:modelValue", value: boolean): void;
  (e: "confirm", selectionRows: ScriptItem[]): void; // 确认事件，传递选择的行数据(脚本数据)
  (e: "cancel"): void; // 定义窗口关闭事件
}>();

const dialogVisible = computed({
  get: () => props.modelValue,
  set: value => {
    emit("update:modelValue", value);
  }
});

const ScriptListTableRef = ref();
const categorySelectorRef = ref();

const onSelectorChanged = (newVal, catalogPath) => {
  nextTick(() => {
    ScriptListTableRef.value?.onQueryChanged(newVal?.id || null, "category");
    ScriptListTableRef.value?.setCatalogPath(catalogPath || []);
  });
};
const onReset = () => {
  categorySelectorRef.value?.setCurrent(null);
};

const selectionRows = computed(
  () => ScriptListTableRef.value?.selectionRows || []
);

const onCancel = () => {
  emit("cancel");
  dialogVisible.value = false;
};

const onConfirm = () => {
  emit("confirm", selectionRows.value as ScriptItem[]);
  ScriptListTableRef.value?.clearSelection();
  dialogVisible.value = false;
};
</script>

<template>
  <el-dialog
    class="script-selector-dialog"
    v-model="dialogVisible"
    :title="title"
    :width="width"
    :draggable="true"
    align-center
    :style="{ '--script-selector-content-height': contentHeight }"
  >
  <el-container class="w-full h-full" style="height: var(--script-selector-content-height)">
      <el-aside width="20%">
        <el-card
          class="category-card h-full cursor-pointer flex flex-col"
          shadow="never"
          body-class="flex-1 overflow-hidden"
        >
          <template #header v-if="false">
            <h3 class="text-info text-center">脚本管理</h3>
          </template>
          <template #default>
            <CategorySelector
              ref="categorySelectorRef"
              @changed="onSelectorChanged"
            />
          </template>
        </el-card>
      </el-aside>
      <el-main style="padding: 0 0 0 10px; overflow: auto">
        <ScriptListTable
          readonly
          class="w-full h-full"
          ref="ScriptListTableRef"
          @reset="onReset"
        />
      </el-main>
    </el-container>
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="onCancel">取 消</el-button>
        <el-button
          type="primary"
          @click="onConfirm"
          :disabled="!selectionRows?.length"
        >
          确 定
          <span>（已选 {{ selectionRows?.length || 0 }}）</span>
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>
<style>
.script-selector-dialog {
  .el-dialog__header {
    padding-bottom: 4px !important;
  }
}
</style>
