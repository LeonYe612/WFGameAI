<script setup lang="ts">
import { ref, reactive } from "vue";
import { Setting } from "@element-plus/icons-vue";
import type { ScriptSettings } from "@/api/scripts";
import { scriptFormRules } from "../utils/rules";
import type { FormInstance } from "element-plus";

defineOptions({
  name: "ScriptSettingsDialog"
});

const emit = defineEmits(["saved"]);

const dialogVisible = ref(false);
const loading = ref(false);
const formRef = ref<FormInstance>();

const settingsForm = reactive<ScriptSettings>({
  python_path: "python",
  debug_cmd: "record_script.py",
  record_cmd: "record_script.py --record",
  replay_cmd: "replay_script.py --show-screens"
});

const showDialog = (currentSettings: ScriptSettings) => {
  Object.assign(settingsForm, currentSettings);
  dialogVisible.value = true;
};

const resetToDefaults = () => {
  Object.assign(settingsForm, {
    python_path: "python",
    debug_cmd: "record_script.py",
    record_cmd: "record_script.py --record",
    replay_cmd: "replay_script.py --show-screens"
  });
};

const saveSettings = async () => {
  if (!formRef.value) return;

  try {
    await formRef.value.validate();

    loading.value = true;

    // 模拟保存延迟
    await new Promise(resolve => setTimeout(resolve, 500));

    emit("saved", { ...settingsForm });
    closeDialog();
  } catch (error) {
    console.error("表单验证失败:", error);
  } finally {
    loading.value = false;
  }
};

const closeDialog = () => {
  dialogVisible.value = false;
  formRef.value?.resetFields();
};

defineExpose({
  showDialog
});
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    title="脚本设置"
    width="600px"
    :draggable="true"
    @close="closeDialog"
  >
    <div v-loading="loading" class="settings-content">
      <el-form
        ref="formRef"
        :model="settingsForm"
        :rules="scriptFormRules"
        label-width="120px"
        class="settings-form"
      >
        <el-card shadow="never" class="border mb-4">
          <template #header>
            <div class="flex items-center justify-between">
              <div class="flex items-center">
                <el-icon class="mr-2">
                  <Setting />
                </el-icon>
                <span class="font-medium">Python环境设置</span>
              </div>
              <el-button
                size="small"
                type="warning"
                @click="resetToDefaults"
                :disabled="loading"
              >
                恢复默认
              </el-button>
            </div>
          </template>

          <el-form-item label="Python路径" prop="python_path">
            <el-input
              v-model="settingsForm.python_path"
              placeholder="请输入Python可执行文件路径"
              :disabled="loading"
            >
              <template #prepend>python</template>
              <template #append>.exe</template>
            </el-input>
            <div class="text-xs text-gray-500 mt-1">
              例如: python, python3, C:\Python39\python.exe
            </div>
          </el-form-item>
        </el-card>

        <el-card shadow="never" class="border">
          <template #header>
            <span class="font-medium">脚本命令设置</span>
          </template>

          <el-form-item label="调试命令" prop="debug_cmd">
            <el-input
              v-model="settingsForm.debug_cmd"
              placeholder="调试模式执行的命令"
              :disabled="loading"
            />
            <div class="text-xs text-gray-500 mt-1">用于调试脚本录制功能</div>
          </el-form-item>

          <el-form-item label="录制命令" prop="record_cmd">
            <el-input
              v-model="settingsForm.record_cmd"
              placeholder="录制模式执行的命令"
              :disabled="loading"
            />
            <div class="text-xs text-gray-500 mt-1">用于录制新的操作脚本</div>
          </el-form-item>

          <el-form-item label="回放命令" prop="replay_cmd">
            <el-input
              v-model="settingsForm.replay_cmd"
              placeholder="回放模式执行的命令"
              :disabled="loading"
            />
            <div class="text-xs text-gray-500 mt-1">用于回放已录制的脚本</div>
          </el-form-item>
        </el-card>

        <!-- 命令预览 -->
        <el-card shadow="never" class="border mt-4">
          <template #header>
            <span class="font-medium">命令预览</span>
          </template>
          <div class="space-y-2 font-mono text-sm">
            <div class="bg-gray-100 p-2 rounded">
              <span class="text-gray-600">调试: </span>
              <span class="text-blue-600"
                >{{ settingsForm.python_path }}
                {{ settingsForm.debug_cmd }}</span
              >
            </div>
            <div class="bg-gray-100 p-2 rounded">
              <span class="text-gray-600">录制: </span>
              <span class="text-green-600"
                >{{ settingsForm.python_path }}
                {{ settingsForm.record_cmd }}</span
              >
            </div>
            <div class="bg-gray-100 p-2 rounded">
              <span class="text-gray-600">回放: </span>
              <span class="text-purple-600"
                >{{ settingsForm.python_path }}
                {{ settingsForm.replay_cmd }}</span
              >
            </div>
          </div>
        </el-card>
      </el-form>
    </div>

    <template #footer>
      <div class="flex justify-end space-x-2">
        <el-button @click="closeDialog" :disabled="loading"> 取消 </el-button>
        <el-button
          type="primary"
          :icon="Setting"
          :loading="loading"
          @click="saveSettings"
        >
          {{ loading ? "保存中..." : "保存设置" }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.settings-content {
  min-height: 200px;
}

.settings-form :deep(.el-form-item__label) {
  color: #606266;
  font-weight: 500;
}
</style>
