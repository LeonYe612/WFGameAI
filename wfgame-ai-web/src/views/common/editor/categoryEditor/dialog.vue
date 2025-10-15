<script setup lang="ts">
import { ref, computed, watch } from "vue";
import CategoryEditor from "./index.vue";

defineOptions({
  name: "CatalogDialog"
});

const props = defineProps<{
  modelValue: boolean;
}>();
const emit = defineEmits<{
  (e: "update:modelValue", value: boolean): void;
  (e: "closed"): void; // 定义窗口关闭事件
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
      emit("closed");
      // 尝试更新用例表单组件 baseInfoFormRef 中的目录列表
      // testcaseStore.components.baseInfoFormRef?.fetchTreeSelectOptions();
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
      <CategoryEditor />
      <!-- <el-scrollbar class="h-full">
      </el-scrollbar> -->
    </div>
    <template #footer />
  </el-dialog>
</template>

<style lang="scss" scoped>
:deep() .el-input__inner {
  @apply text-primary text-sm font-semibold;
}
</style>
