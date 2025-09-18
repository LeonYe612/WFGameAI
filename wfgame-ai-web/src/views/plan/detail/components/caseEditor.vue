<template>
  <el-dialog
    v-model="valueProxy"
    width="90%"
    :close-on-click-modal="true"
    :close-on-press-escape="false"
    :title="title"
    align-center
    :append-to-body="false"
  >
    <TestcaseDetail ref="targetRef" />
  </el-dialog>
</template>
<script setup lang="ts">
import TestcaseDetail from "@/views/testcase/detail/index.vue";
import { ref, defineProps, nextTick, watch, computed } from "vue";
import { useTestcaseStoreHook } from "@/store/modules/testcase";
import { storeToRefs } from "pinia";

const testcaseStore = useTestcaseStoreHook();
const { baseInfo } = storeToRefs(testcaseStore);

const emit = defineEmits(["update:modelValue"]);

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
    required: true
  },
  title: {
    type: String,
    default: "📝 编辑用例"
  }
});

// 使用计算属性实现双向绑定
const valueProxy = computed({
  get() {
    return props.modelValue;
  },
  set(newValue) {
    emit("update:modelValue", newValue);
  }
});

watch(valueProxy, val => {
  if (!val) {
    // 关闭编辑用例时，保存当前步骤
    if (testcaseStore.currentStep.id) {
      testcaseStore.saveStep();
    }
  }
});

const targetRef = ref(null);
const refresh = (case_base_id: number, version: number) => {
  // 如果查看的是同一个用例，则不刷新
  if (
    baseInfo.value.id === case_base_id &&
    baseInfo.value.version === version
  ) {
    return;
  }
  nextTick(() => {
    targetRef.value?.refresh(case_base_id, version);
  });
};

defineExpose({
  refresh
});
</script>
<style scoped></style>
