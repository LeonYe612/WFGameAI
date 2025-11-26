<template>
  <MainContent title="OCR 识别结果">
    <template #header-extra>
      <div class="flex">
        <el-button
          v-if="false"
          class="ml-auto"
          type="primary"
          plain
          @click="startVerify"
        >
          审图模式
        </el-button>
      </div>
    </template>
    <div v-if="taskId" class="flex-full gap-4">
      <OcrTaskInfo class="flex-[1]" :task-id="taskId" />
      <OcrResultList
        class="flex-[3]"
        v-if="taskId"
        :task-id="taskId"
        :key="refreshKey"
      />
    </div>
    <div v-else>
      <el-empty description="请传递有效的 Task Id" />
    </div>

    <OcrResultVerifyer
      v-if="taskId"
      v-model:visible="verifyVisible"
      :task-id="taskId"
      @refresh="handleRefresh"
    />
  </MainContent>
</template>
<script setup lang="ts">
import { ref, onMounted } from "vue";
import MainContent from "@/layout/components/mainContent/index.vue";
import OcrTaskInfo from "./components/OcrTaskInfo.vue";
import OcrResultList from "./components/OcrResultList.vue";
import OcrResultVerifyer from "./components/OcrResultVerifyer.vue";
import { useNavigate } from "@/views/common/utils/navHook";

defineOptions({
  name: "OcrResult"
});

const { getParameter } = useNavigate();
const taskId = ref<string | null>(null);
const verifyVisible = ref(false);
const refreshKey = ref(0);

const startVerify = () => {
  verifyVisible.value = true;
};

const handleRefresh = () => {
  refreshKey.value++;
};

onMounted(() => {
  const id = getParameter.id as string;
  taskId.value = id || "";
});
</script>

<style lang="scss" scoped></style>
