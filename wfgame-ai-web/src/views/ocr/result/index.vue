<template>
  <MainContent title="OCR 识别结果">
    <template #header-more>
      <span>|</span>
    </template>
    <div v-if="taskId" class="flex-full gap-4">
      <OcrTaskInfo class="flex-[1]" :task-id="taskId" />
      <OcrResultList class="flex-[3]" v-if="taskId" :task-id="taskId" />
    </div>
    <div v-else>
      <el-empty description="请传递有效的 Task Id" />
    </div>
  </MainContent>
</template>
<script setup lang="ts">
import { ref, onMounted } from "vue";
import MainContent from "@/layout/components/mainContent/index.vue";
import OcrTaskInfo from "./components/OcrTaskInfo.vue";
import OcrResultList from "./components/OcrResultList.vue";
import { useNavigate } from "@/views/common/utils/navHook";

defineOptions({
  name: "OcrResult"
});

const { getParameter } = useNavigate();
const taskId = ref<string | null>(null);

onMounted(() => {
  const id = getParameter.id as string;
  taskId.value = id || "";
});
</script>

<style lang="scss" scoped></style>
