<script setup lang="ts">
import { ref } from "vue";
import { Document, Loading } from "@element-plus/icons-vue";
import { ElMessageBox } from "element-plus";
import { getScriptContent, saveScriptContent } from "@/api/scripts";
import type { ScriptInfo } from "@/api/scripts";
import { superRequest } from "@/utils/request";
import { message } from "@/utils/message";

defineOptions({
  name: "ScriptEditDialog"
});

const emit = defineEmits(["saved"]);

const dialogVisible = ref(false);
const loading = ref(false);
const saving = ref(false);
const selectedScript = ref<ScriptInfo | null>(null);
const scriptContent = ref("");
const originalContent = ref("");

const showDialog = async (script: ScriptInfo) => {
  selectedScript.value = script;
  scriptContent.value = "";
  originalContent.value = "";
  dialogVisible.value = true;

  // 加载脚本内容
  await loadScriptContent();
};

const loadScriptContent = async () => {
  if (!selectedScript.value) return;

  await superRequest({
    apiFunc: getScriptContent,
    apiParams: selectedScript.value.filename,
    onBeforeRequest: () => {
      loading.value = true;
    },
    onSucceed: (data: ScriptInfo) => {
      scriptContent.value = data.content || "";
      originalContent.value = data.content || "";
    },
    onFailed: () => {
      message("加载脚本内容失败", { type: "error" });
    },
    onCompleted: () => {
      loading.value = false;
    }
  });
};

const formatJson = () => {
  try {
    const parsed = JSON.parse(scriptContent.value);
    scriptContent.value = JSON.stringify(parsed, null, 2);
    message("JSON格式化成功", { type: "success" });
  } catch (error) {
    message("JSON格式错误，无法格式化", { type: "error" });
  }
};

const saveScript = async () => {
  if (!selectedScript.value) return;

  // 验证JSON格式
  try {
    JSON.parse(scriptContent.value);
  } catch (error) {
    message("JSON格式错误，请检查语法", { type: "error" });
    return;
  }

  await superRequest({
    apiFunc: saveScriptContent,
    apiParams: [selectedScript.value.filename, scriptContent.value],
    enableSucceedMsg: true,
    succeedMsgContent: "脚本保存成功！",
    onBeforeRequest: () => {
      saving.value = true;
    },
    onSucceed: () => {
      originalContent.value = scriptContent.value;
      emit("saved");
      closeDialog();
    },
    onFailed: () => {
      message("脚本保存失败", { type: "error" });
    },
    onCompleted: () => {
      saving.value = false;
    }
  });
};

const closeDialog = () => {
  dialogVisible.value = false;
  selectedScript.value = null;
  scriptContent.value = "";
  originalContent.value = "";
};

const hasChanges = () => {
  return scriptContent.value !== originalContent.value;
};

const confirmClose = () => {
  if (hasChanges()) {
    ElMessageBox.confirm("脚本内容已修改但未保存，确定要关闭吗？", "确认关闭", {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning"
    })
      .then(() => {
        closeDialog();
      })
      .catch(() => {
        // 用户取消
      });
  } else {
    closeDialog();
  }
};

defineExpose({
  showDialog
});
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    :title="`编辑脚本 - ${selectedScript?.filename || ''}`"
    width="90%"
    :draggable="true"
    :before-close="confirmClose"
  >
    <div v-loading="loading" class="script-edit-content">
      <div v-if="!loading && selectedScript" class="space-y-4">
        <!-- 脚本信息 -->
        <el-card shadow="never" class="border">
          <template #header>
            <div class="flex items-center justify-between">
              <div class="flex items-center">
                <el-icon class="mr-2">
                  <Document />
                </el-icon>
                <span class="font-medium">脚本信息</span>
              </div>
              <div class="flex space-x-2">
                <el-button
                  size="small"
                  type="info"
                  @click="formatJson"
                  :disabled="saving"
                >
                  格式化JSON
                </el-button>
              </div>
            </div>
          </template>

          <div class="grid grid-cols-2 gap-4 text-sm mb-4">
            <div>
              <span class="text-gray-500">文件名: </span>
              <span class="font-medium">{{ selectedScript.filename }}</span>
            </div>
            <div v-if="selectedScript.category">
              <span class="text-gray-500">分类: </span>
              <el-tag type="info" size="small">{{
                selectedScript.category
              }}</el-tag>
            </div>
            <div v-if="selectedScript.size">
              <span class="text-gray-500">文件大小: </span>
              <span>{{ (selectedScript.size / 1024).toFixed(2) }} KB</span>
            </div>
            <div v-if="selectedScript.modified_at">
              <span class="text-gray-500">修改时间: </span>
              <span>{{
                new Date(selectedScript.modified_at).toLocaleString()
              }}</span>
            </div>
          </div>

          <!-- 脚本内容编辑器 -->
          <div class="script-editor">
            <el-input
              v-model="scriptContent"
              type="textarea"
              :rows="20"
              placeholder="请输入脚本内容（JSON格式）"
              class="font-mono"
              :disabled="saving"
            />
          </div>

          <!-- 字符统计 -->
          <div
            class="flex justify-between items-center mt-2 text-sm text-gray-500"
          >
            <span>字符数: {{ scriptContent.length }}</span>
            <span v-if="hasChanges()" class="text-orange-500">
              <i class="el-icon-warning-outline mr-1" />
              内容已修改
            </span>
          </div>
        </el-card>
      </div>

      <div v-if="loading" class="text-center py-12">
        <el-icon class="animate-spin text-4xl text-primary mb-4">
          <Loading />
        </el-icon>
        <p class="text-gray-500">正在加载脚本内容...</p>
      </div>
    </div>

    <template #footer>
      <div class="flex justify-end space-x-2">
        <el-button @click="confirmClose" :disabled="saving"> 取消 </el-button>
        <el-button
          type="primary"
          :icon="Document"
          :loading="saving"
          @click="saveScript"
          :disabled="!hasChanges()"
        >
          {{ saving ? "保存中..." : "保存脚本" }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.script-edit-content {
  min-height: 400px;
}

.script-editor :deep(.el-textarea__inner) {
  font-family: "Consolas", "Monaco", "Courier New", monospace;
  background-color: #f8f9fa;
  border: 1px solid #e9ecef;
}

.font-mono {
  font-family: "Consolas", "Monaco", "Courier New", monospace;
}
</style>
