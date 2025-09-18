<script setup lang="ts">
import { ref, computed } from "vue";
import { Upload, Document, Delete } from "@element-plus/icons-vue";
import { importScript, batchImportScripts } from "@/api/scripts";
import type { ScriptCategory } from "@/api/scripts";
import { superRequest } from "@/utils/request";
import { message } from "@/utils/message";

defineOptions({
  name: "ScriptImportDialog"
});

defineProps<{
  categories: ScriptCategory[];
}>();

const emit = defineEmits(["imported"]);

const dialogVisible = ref(false);
const activeTab = ref("single");
const loading = ref(false);

// 单文件导入
const singleFile = ref<File | null>(null);
const singleCategory = ref("");
const singleDescription = ref("");

// 批量导入
const batchFiles = ref<any[]>([]);
const batchCategory = ref("");
const uploadProgress = ref(0);

const showDialog = () => {
  resetForm();
  dialogVisible.value = true;
};

const resetForm = () => {
  singleFile.value = null;
  singleCategory.value = "";
  singleDescription.value = "";
  batchFiles.value = [];
  batchCategory.value = "";
  uploadProgress.value = 0;
  activeTab.value = "single";
};

// 单文件选择
const handleSingleFileSelect = (file: File) => {
  if (!file.name.endsWith(".json")) {
    message("请选择JSON格式的脚本文件", { type: "warning" });
    return false;
  }
  singleFile.value = file;
  return false; // 阻止自动上传
};

// 批量文件选择
const handleBatchFileSelect = (files: File[]) => {
  const jsonFiles = files.filter(file => file.name.endsWith(".json"));

  if (jsonFiles.length === 0) {
    message("请选择JSON格式的脚本文件", { type: "warning" });
    return;
  }

  batchFiles.value = jsonFiles.map(file => ({
    file,
    status: "pending"
  }));
};

// 移除单个文件
const removeSingleFile = () => {
  singleFile.value = null;
};

// 移除批量文件中的某个文件
const removeBatchFile = (index: number) => {
  batchFiles.value.splice(index, 1);
};

// 清空批量文件
const clearBatchFiles = () => {
  batchFiles.value = [];
};

// 格式化文件大小
const formatFileSize = (bytes: number) => {
  if (bytes < 1024) {
    return bytes + " B";
  } else if (bytes < 1024 * 1024) {
    return (bytes / 1024).toFixed(2) + " KB";
  } else {
    return (bytes / (1024 * 1024)).toFixed(2) + " MB";
  }
};

// 单文件导入
const importSingle = async () => {
  if (!singleFile.value) {
    message("请选择要导入的脚本文件", { type: "warning" });
    return;
  }

  const formData = new FormData();
  formData.append("file", singleFile.value);
  if (singleCategory.value) {
    formData.append("category", singleCategory.value);
  }
  if (singleDescription.value) {
    formData.append("description", singleDescription.value);
  }

  await superRequest({
    apiFunc: importScript,
    apiParams: formData,
    enableSucceedMsg: true,
    succeedMsgContent: "脚本导入成功！",
    onBeforeRequest: () => {
      loading.value = true;
    },
    onSucceed: () => {
      emit("imported");
      closeDialog();
    },
    onFailed: () => {
      message("脚本导入失败", { type: "error" });
    },
    onCompleted: () => {
      loading.value = false;
    }
  });
};

// 批量导入
const importBatch = async () => {
  if (batchFiles.value.length === 0) {
    message("请选择要导入的脚本文件", { type: "warning" });
    return;
  }

  const formData = new FormData();

  // 添加所有文件
  batchFiles.value.forEach((fileStatus, _index) => {
    formData.append("files", fileStatus.file);
  });

  if (batchCategory.value) {
    formData.append("category", batchCategory.value);
  }

  await superRequest({
    apiFunc: batchImportScripts,
    apiParams: formData,
    enableSucceedMsg: true,
    succeedMsgContent: "批量导入完成！",
    onBeforeRequest: () => {
      loading.value = true;
      uploadProgress.value = 0;
    },
    onSucceed: result => {
      const { success_count, total_count } = result;
      message(`成功导入 ${success_count}/${total_count} 个脚本`, {
        type: success_count > 0 ? "success" : "warning"
      });
      emit("imported");
      closeDialog();
    },
    onFailed: () => {
      message("批量导入失败", { type: "error" });
    },
    onCompleted: () => {
      loading.value = false;
      uploadProgress.value = 100;
    }
  });
};

const closeDialog = () => {
  dialogVisible.value = false;
  resetForm();
};

const canImportSingle = computed(() => {
  return singleFile.value !== null;
});

const canImportBatch = computed(() => {
  return batchFiles.value.length > 0;
});

defineExpose({
  showDialog
});
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    title="导入脚本"
    width="800px"
    :draggable="true"
    @close="closeDialog"
  >
    <div v-loading="loading" class="script-import-content">
      <el-tabs v-model="activeTab" class="import-tabs">
        <!-- 单文件导入 -->
        <el-tab-pane label="单文件导入" name="single">
          <div class="space-y-4">
            <!-- 文件上传区域 -->
            <el-upload
              class="upload-demo"
              drag
              :show-file-list="false"
              :before-upload="handleSingleFileSelect"
              accept=".json"
              :disabled="loading"
            >
              <div class="upload-content">
                <el-icon class="text-4xl text-gray-400 mb-4">
                  <Upload />
                </el-icon>
                <div class="text-gray-600">
                  <p class="text-lg mb-2">点击或拖拽JSON文件到此区域</p>
                  <p class="text-sm text-gray-500">
                    支持单个.json格式的脚本文件
                  </p>
                </div>
              </div>
            </el-upload>

            <!-- 已选择的文件 -->
            <div v-if="singleFile" class="selected-file">
              <el-card shadow="never" class="border">
                <div class="flex items-center justify-between">
                  <div class="flex items-center">
                    <el-icon class="text-primary mr-2">
                      <Document />
                    </el-icon>
                    <div>
                      <div class="font-medium">{{ singleFile.name }}</div>
                      <div class="text-sm text-gray-500">
                        {{ formatFileSize(singleFile.size) }}
                      </div>
                    </div>
                  </div>
                  <el-button
                    size="small"
                    type="danger"
                    :icon="Delete"
                    @click="removeSingleFile"
                    :disabled="loading"
                  >
                    移除
                  </el-button>
                </div>
              </el-card>
            </div>

            <!-- 脚本信息 -->
            <div v-if="singleFile" class="script-info">
              <el-card shadow="never" class="border">
                <template #header>
                  <span class="font-medium">脚本信息</span>
                </template>
                <div class="space-y-4">
                  <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">
                      脚本分类
                    </label>
                    <el-select
                      v-model="singleCategory"
                      placeholder="请选择分类（可选）"
                      style="width: 100%"
                      clearable
                      :disabled="loading"
                    >
                      <el-option
                        v-for="category in categories"
                        :key="category.id"
                        :label="category.name"
                        :value="category.id"
                      />
                    </el-select>
                  </div>
                  <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">
                      脚本描述
                    </label>
                    <el-input
                      v-model="singleDescription"
                      type="textarea"
                      :rows="3"
                      placeholder="请输入脚本描述（可选）"
                      :disabled="loading"
                    />
                  </div>
                </div>
              </el-card>
            </div>
          </div>
        </el-tab-pane>

        <!-- 批量导入 -->
        <el-tab-pane label="批量导入" name="batch">
          <div class="space-y-4">
            <!-- 批量上传区域 -->
            <el-upload
              class="upload-demo"
              drag
              multiple
              :show-file-list="false"
              :on-change="
                (file, fileList) =>
                  handleBatchFileSelect(fileList.map(f => f.raw))
              "
              accept=".json"
              :disabled="loading"
            >
              <div class="upload-content">
                <el-icon class="text-4xl text-gray-400 mb-4">
                  <Upload />
                </el-icon>
                <div class="text-gray-600">
                  <p class="text-lg mb-2">点击或拖拽多个JSON文件到此区域</p>
                  <p class="text-sm text-gray-500">
                    支持批量上传.json格式的脚本文件
                  </p>
                </div>
              </div>
            </el-upload>

            <!-- 文件列表 -->
            <div v-if="batchFiles.length > 0" class="file-list">
              <el-card shadow="never" class="border">
                <template #header>
                  <div class="flex items-center justify-between">
                    <span class="font-medium">
                      已选择 {{ batchFiles.length }} 个文件
                    </span>
                    <el-button
                      size="small"
                      type="danger"
                      @click="clearBatchFiles"
                      :disabled="loading"
                    >
                      清空列表
                    </el-button>
                  </div>
                </template>

                <div class="space-y-2 max-h-60 overflow-y-auto">
                  <div
                    v-for="(fileStatus, index) in batchFiles"
                    :key="index"
                    class="flex items-center justify-between p-2 bg-gray-50 rounded"
                  >
                    <div class="flex items-center">
                      <el-icon class="text-primary mr-2">
                        <Document />
                      </el-icon>
                      <div>
                        <div class="text-sm font-medium">
                          {{ fileStatus.file.name }}
                        </div>
                        <div class="text-xs text-gray-500">
                          {{ formatFileSize(fileStatus.file.size) }}
                        </div>
                      </div>
                    </div>
                    <el-button
                      size="small"
                      type="danger"
                      :icon="Delete"
                      @click="removeBatchFile(index)"
                      :disabled="loading"
                    >
                      移除
                    </el-button>
                  </div>
                </div>
              </el-card>

              <!-- 批量设置 -->
              <el-card shadow="never" class="border">
                <template #header>
                  <span class="font-medium">批量设置</span>
                </template>
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-1">
                    统一分类
                  </label>
                  <el-select
                    v-model="batchCategory"
                    placeholder="为所有脚本设置统一分类（可选）"
                    style="width: 100%"
                    clearable
                    :disabled="loading"
                  >
                    <el-option
                      v-for="category in categories"
                      :key="category.id"
                      :label="category.name"
                      :value="category.id"
                    />
                  </el-select>
                </div>
              </el-card>
            </div>

            <!-- 进度条 -->
            <div v-if="loading && uploadProgress > 0" class="upload-progress">
              <el-progress
                :percentage="uploadProgress"
                :stroke-width="8"
                status="success"
              />
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <template #footer>
      <div class="flex justify-end space-x-2">
        <el-button @click="closeDialog" :disabled="loading"> 取消 </el-button>
        <el-button
          v-if="activeTab === 'single'"
          type="primary"
          :icon="Upload"
          :loading="loading"
          :disabled="!canImportSingle"
          @click="importSingle"
        >
          {{ loading ? "导入中..." : "导入脚本" }}
        </el-button>
        <el-button
          v-if="activeTab === 'batch'"
          type="primary"
          :icon="Upload"
          :loading="loading"
          :disabled="!canImportBatch"
          @click="importBatch"
        >
          {{ loading ? "导入中..." : `批量导入 (${batchFiles.length})` }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.script-import-content {
  min-height: 300px;
}

.upload-demo :deep(.el-upload-dragger) {
  padding: 40px 20px;
  border: 2px dashed #dcdfe6;
  border-radius: 8px;
  background-color: #fafbfc;
  transition: all 0.3s;
}

.upload-demo :deep(.el-upload-dragger:hover) {
  border-color: var(--el-color-primary);
  background-color: var(--el-color-primary-light-9);
}

.upload-content {
  text-align: center;
}

.selected-file,
.file-list,
.script-info {
  margin-top: 16px;
}

.import-tabs :deep(.el-tabs__content) {
  padding-top: 20px;
}
</style>
