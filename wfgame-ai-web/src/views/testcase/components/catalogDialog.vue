<script setup lang="ts">
import { ref, computed, watch } from "vue";
import TestcaseCatalog from "@/views/testcase/catalog/index.vue";
import { useTestcaseStoreHook } from "@/store/modules/testcase";

const testcaseStore = useTestcaseStoreHook();

defineOptions({
  name: "CatalogDialog"
});

const props = defineProps<{
  modelValue: boolean;
}>();
const emit = defineEmits<{
  (e: "update:modelValue", value: boolean): void;
  (e: "onClosed"): void; // 定义窗口关闭事件
}>();

const dialogVisible = computed({
  get: () => props.modelValue,
  set: value => {
    emit("update:modelValue", value);
  }
});

watch(
  () => props.modelValue,
  value => {
    if (value) {
      console.log("🎃 catelogDialog opened!");
    } else {
      emit("onClosed");
      // 尝试更新用例表单组件 baseInfoFormRef 中的目录列表
      testcaseStore.components.baseInfoFormRef?.fetchTreeSelectOptions();
    }
  }
);

const title = ref("");
defineExpose({});
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    :title="title"
    width="80vw"
    height="80vh"
    :draggable="true"
    align-center
  >
    <div class="w-full h-[75vh] overflow-y-auto">
      <el-scrollbar class="h-full">
        <TestcaseCatalog />
      </el-scrollbar>
    </div>
    <template #footer>
      <div class="w-full flex items-center" v-if="false">
        <el-button
          @click="dialogVisible = false"
          size="large"
          class="px-8 ml-auto"
        >
          取消调试
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style lang="scss" scoped>
:deep() .el-input__inner {
  @apply text-primary text-sm font-semibold;
}
</style>
