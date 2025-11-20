<script setup lang="ts">
import { ref, watch } from "vue";
import { ReportItem } from "@/api/reports";
import DetailsList from "./detailsList.vue";

interface Props {
  modelValue: boolean;
  report: ReportItem | null;
  title?: string;
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: false,
  report: null
});

const emit = defineEmits<{
  (e: "update:modelValue", value: boolean): void;
}>();

defineOptions({
  name: "DetailsListDrawer"
});

const visible = ref(props.modelValue);

// 监听 modelValue 变化
watch(
  () => props.modelValue,
  newVal => {
    visible.value = newVal;
  }
);

// 监听 visible 变化，同步到父组件
watch(visible, newVal => {
  emit("update:modelValue", newVal);
});

const handleClose = () => {
  visible.value = false;
};
</script>

<template>
  <el-drawer
    v-model="visible"
    :title="title"
    direction="rtl"
    size="70%"
    :before-close="handleClose"
  >
    <DetailsList v-if="visible && report" :report="report" />
    <el-empty v-else description="请选择一个报告查看详情" />
  </el-drawer>
</template>

<style scoped lang="scss">
:deep(.el-drawer__body) {
  padding: 0;
}
.details-container {
  height: 100% !important;
}
</style>
