<script setup lang="ts">
import { ref, reactive, computed, nextTick } from "vue";
import ScriptListTable from "@/views/scripts/list/components/scriptListTable.vue";
import CategorySelector from "@/views/scripts/list/components/categorySelector.vue";
import { scriptApi, type ScriptItem } from "@/api/scripts";
import { message } from "@/utils/message";
import { superRequest } from "@/utils/request";

defineOptions({
  name: "ScriptStepImporter"
});

const emit = defineEmits(["import"]);

const dialogVisible = ref(false);
const selectedScript = ref<ScriptItem | null>(null);
const scriptSteps = ref([]);
const selectedStepIds = ref([]);

const scriptListRef = ref();
const categoryRef = ref();

const onSelectorChanged = (newVal, catalogPath) => {
  nextTick(() => {
    scriptListRef.value?.onQueryChanged(newVal?.id || null, "category");
    scriptListRef.value?.setCatalogPath(catalogPath || []);
  });
};
const onReset = () => {
  categoryRef.value?.setCurrent(null);
  scriptListRef.value?.clearSelection();
  selectedScript.value = null;
};

const state = reactive({
  loadingSteps: false
});

const _resetSelection = () => {
  selectedScript.value = null;
  scriptSteps.value = [];
  selectedStepIds.value = [];
  scriptListRef.value?.clearSelection();
};

const open = () => {
  dialogVisible.value = true;
  // resetSelection();
};

// 脚本表格的行选中事件
const handleSingleSelectionChange = (script: ScriptItem) => {
  if (script && script.id !== selectedScript.value?.id) {
    selectedScript.value = script;
    fetchScriptSteps(script.id);
  }
};

const fetchScriptSteps = async (scriptId: number) => {
  state.loadingSteps = true;
  superRequest({
    apiFunc: scriptApi.detail,
    apiParams: scriptId,
    onSucceed: data => {
      scriptSteps.value = (data?.steps || []).map((step, index) => ({
        ...step,
        originalIndex: index
      }));
    },
    onFailed: error => {
      message("获取脚本步骤失败", { type: "error" });
      console.error("Failed to fetch script steps:", error);
      scriptSteps.value = [];
    }
  }).finally(() => {
    state.loadingSteps = false;
  });
};

const handleImport = () => {
  const stepsToImport = selectedStepIds.value.map(
    id => scriptSteps.value?.[id]
  );
  if (stepsToImport.length === 0) {
    message("请先选择要导入的步骤", { type: "warning" });
    return;
  }
  emit("import", stepsToImport);
  console.log("Importing steps:", stepsToImport);
  dialogVisible.value = false;
  selectedStepIds.value = [];
};

const allStepsSelected = computed({
  get: () =>
    scriptSteps.value.length > 0 &&
    selectedStepIds.value.length === scriptSteps.value.length,
  set: val => {
    if (val) {
      selectedStepIds.value = scriptSteps.value.map((_, index) => index);
    } else {
      selectedStepIds.value = [];
    }
  }
});

defineExpose({
  open
});
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    title="从脚本库导入步骤"
    width="85vw"
    align-center
  >
    <el-row :gutter="20" style="height: 80vh">
      <!-- Left: Script Category -->
      <el-col class="h-full" :span="4">
        <el-card class="category-card" shadow="never">
          <template #header>
            <h3 class="text-info text-center">脚本目录</h3>
          </template>
          <CategorySelector
            class="h-full"
            ref="categoryRef"
            @changed="onSelectorChanged"
          />
        </el-card>
      </el-col>
      <!-- Center: Script List -->
      <el-col class="h-full" :span="12">
        <ScriptListTable
          class="h-full"
          ref="scriptListRef"
          readonly
          select-mode="single"
          display-mode="brief"
          @reset="onReset"
          @single-selection-change="handleSingleSelectionChange"
        />
      </el-col>

      <!-- Right: Steps of Selected Script -->
      <el-col class="h-full" :span="8">
        <el-card class="h-full flex flex-col">
          <template #header>
            <div class="flex justify-between items-center">
              <el-checkbox
                v-if="scriptSteps.length > 0"
                v-model="allStepsSelected"
                label="全选"
                size="large"
              />
            </div>
          </template>
          <el-scrollbar class="flex-1 min-h-0">
            <div v-if="!selectedScript" class="text-center text-gray-400 pt-10">
              请先从左侧选择一个脚本
            </div>
            <div
              v-else-if="state.loadingSteps"
              class="text-center text-gray-400 pt-10"
            >
              步骤加载中...
            </div>
            <el-checkbox-group
              v-else-if="scriptSteps.length > 0"
              v-model="selectedStepIds"
              class="w-full my-2"
            >
              <div
                v-for="step in scriptSteps"
                :key="step.originalIndex"
                class="mb-2 p-2 border border-gray-200 rounded hover:bg-gray-100"
              >
                <el-checkbox
                  :label="step.step"
                  :value="step.originalIndex"
                  class="step-checkbox"
                >
                  <div class="flex items-center">
                    <span class="font-bold">
                      步骤 {{ step.originalIndex + 1 }}
                    </span>
                    <el-divider direction="vertical" />
                    <div class="flex-1 min-w-0 truncate">
                      <span :title="step.remark">
                        {{ step.remark }}
                      </span>
                    </div>
                    <el-tag size="small" effect="plain" class="mr-1">{{
                      step.action
                    }}</el-tag>
                  </div>
                </el-checkbox>
              </div>
            </el-checkbox-group>
            <div v-else class="text-center text-gray-400 pt-10">
              该脚本没有可导入的步骤
            </div>
          </el-scrollbar>
        </el-card>
      </el-col>
    </el-row>
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          @click="handleImport"
          :disabled="selectedStepIds.length === 0"
        >
          导入 {{ selectedStepIds.length }} 个步骤
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<style scoped lang="scss">
.category-card {
  height: 100%;
  display: flex;
  flex-direction: column;
  .el-card__body {
    flex: 1;
    min-height: 0;
  }
}
.step-checkbox {
  width: 100% !important;
  :deep(span.el-checkbox__label) {
    display: inline-block;
    width: 100% !important;
  }
}
</style>
