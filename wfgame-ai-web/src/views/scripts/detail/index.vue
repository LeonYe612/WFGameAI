<script setup lang="ts">
import MainContent from "@/layout/components/mainContent/index.vue";
import ScriptActionLibrary from "./components/scriptActionLibrary.vue";
import ScriptStepsList from "./components/scriptStepsList.vue";
import ScriptStepsJson from "./components/scriptStepsJson.vue";
import scriptBaseInfo from "./components/scriptBaseInfo.vue";
import ScriptStepImporter from "./components/scriptStepImporter.vue";
import { useNavigate } from "@/views/common/utils/navHook";
import { computed, watch, ref } from "vue";
import { useScriptStoreHook } from "@/store/modules/script";
const scriptStore = useScriptStoreHook();

defineOptions({
  name: "ScriptDetail"
});

const props = defineProps({
  id: {
    type: Number,
    default: 0
  }
});

const { getParameter } = useNavigate();
const scriptId = computed(() => Number(getParameter.id) || props.id || 0);

watch(
  scriptId,
  newId => {
    if (newId >= 0) {
      scriptStore.fetchScriptDetail(newId);
    }
  },
  {
    immediate: true // 立即执行一次，替代 onMounted 和 onActivated
  }
);

const emit = defineEmits<{
  save: [];
}>();
const onSave = () => {
  emit("save");
};

const scriptStepImporterRef = ref(null);

const openImporter = () => {
  scriptStepImporterRef.value?.open();
};

const handleStepsImport = (steps: any[]) => {
  scriptStore.insertSteps(steps);
};
</script>

<template>
  <MainContent title="" :show-team-info="false">
    <template #custom-header>
      <scriptBaseInfo @save="onSave" />
    </template>
    <el-row :gutter="10" class="component-row">
      <el-col :span="7">
        <div class="component-wrapper">
          <ScriptActionLibrary class="h-full" />
        </div>
      </el-col>
      <el-col :span="9">
        <div class="component-wrapper">
          <ScriptStepsList class="h-full" @open-importer="openImporter" />
        </div>
      </el-col>
      <el-col :span="8">
        <div class="component-wrapper bg-[#292a36]">
          <ScriptStepsJson class="h-full" />
        </div>
      </el-col>
    </el-row>
    <ScriptStepImporter
      ref="scriptStepImporterRef"
      @import="handleStepsImport"
    />
  </MainContent>
</template>

<style lang="scss" scoped>
.component-row {
  height: 100%;
  .el-col {
    height: 100%;
    .component-wrapper {
      border: 1px solid var(--el-border-color);
      border-radius: 8px;
      padding: 16px;
      height: 100%;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }
  }
}
</style>
