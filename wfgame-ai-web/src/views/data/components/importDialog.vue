<script setup lang="ts">
import { ref, computed } from "vue";
import { Upload, Download } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import type { DataSource } from "@/api/data";
import { importDataFormRules } from "../utils/rules";
import type { FormInstance, UploadUserFile } from "element-plus";

defineOptions({
  name: "ImportDialog"
});

defineProps<{
  modelValue: boolean;
  dataSources: DataSource[];
}>();

const emit = defineEmits(["update:modelValue", "import"]);

const formRef = ref<FormInstance>();
const fileList = ref<UploadUserFile[]>([]);
const formData = ref({
  sourceId: "",
  encoding: "utf-8",
  delimiter: ",",
  hasHeader: true
});

const selectedFile = computed(() => {
  return fileList.value.length > 0 ? fileList.value[0] : null;
});

// 关闭对话框
const closeDialog = () => {
  emit("update:modelValue", false);
  formRef.value?.resetFields();
  fileList.value = [];
};

// 文件上传前检查
const beforeUpload = (file: File) => {
  const isValidType =
    file.type.includes("excel") ||
    file.type.includes("csv") ||
    file.name.endsWith(".xlsx") ||
    file.name.endsWith(".xls") ||
    file.name.endsWith(".csv");

  if (!isValidType) {
    ElMessage.error("只能上传 Excel 或 CSV 文件！");
    return false;
  }

  const isLt10M = file.size / 1024 / 1024 < 10;
  if (!isLt10M) {
    ElMessage.error("文件大小不能超过 10MB！");
    return false;
  }

  return false; // 阻止自动上传，我们手动处理
};

// 文件列表变化
const handleFileChange = (
  uploadFile: UploadUserFile,
  uploadFiles: UploadUserFile[]
) => {
  fileList.value = uploadFiles.slice(-1); // 只保留最后一个文件
};

// 确认导入
const handleImport = async () => {
  if (!formRef.value) return;
  if (!selectedFile.value) {
    ElMessage.error("请选择要导入的文件");
    return;
  }

  try {
    await formRef.value.validate();

    const importConfig = {
      file: selectedFile.value.raw as File,
      sourceId: formData.value.sourceId || undefined,
      encoding: formData.value.encoding,
      delimiter: formData.value.delimiter,
      hasHeader: formData.value.hasHeader
    };

    emit("import", importConfig);
    closeDialog();
  } catch (error) {
    console.error("表单验证失败:", error);
  }
};

// 下载模板
const downloadTemplate = () => {
  // 创建模板数据
  const templateData = [
    ["字段1", "字段2", "字段3"],
    ["示例数据1", "示例数据2", "示例数据3"],
    ["示例数据4", "示例数据5", "示例数据6"]
  ];

  // 转换为CSV格式
  const csvContent = templateData.map(row => row.join(",")).join("\n");
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });

  // 创建下载链接
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "data_template.csv";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
};
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    title="导入数据"
    width="600px"
    :draggable="true"
    @close="closeDialog"
  >
    <el-form
      ref="formRef"
      :model="formData"
      :rules="importDataFormRules"
      label-width="100px"
      label-position="left"
    >
      <el-form-item label="选择文件" required>
        <el-upload
          v-model:file-list="fileList"
          drag
          :auto-upload="false"
          :before-upload="beforeUpload"
          :on-change="handleFileChange"
          :limit="1"
          accept=".xlsx,.xls,.csv"
          class="w-full"
        >
          <el-icon class="el-icon--upload">
            <Upload />
          </el-icon>
          <div class="el-upload__text">将文件拖到此处，或<em>点击上传</em></div>
          <template #tip>
            <div class="el-upload__tip">
              支持 .xlsx/.xls/.csv 文件，且不超过 10MB
            </div>
          </template>
        </el-upload>
      </el-form-item>

      <el-form-item label="目标数据源">
        <el-select
          v-model="formData.sourceId"
          placeholder="选择已有数据源或留空创建新数据源"
          style="width: 100%"
          clearable
        >
          <el-option
            v-for="source in dataSources"
            :key="source.id"
            :label="source.name"
            :value="source.id"
          />
        </el-select>
        <div class="text-xs text-gray-500 mt-1">
          留空将根据文件名创建新的数据源
        </div>
      </el-form-item>

      <el-form-item label="文件编码" prop="encoding">
        <el-select
          v-model="formData.encoding"
          placeholder="请选择文件编码"
          style="width: 100%"
        >
          <el-option label="UTF-8" value="utf-8" />
          <el-option label="GBK" value="gbk" />
          <el-option label="GB2312" value="gb2312" />
        </el-select>
      </el-form-item>

      <el-form-item v-if="selectedFile?.name.endsWith('.csv')" label="分隔符">
        <el-select
          v-model="formData.delimiter"
          placeholder="请选择分隔符"
          style="width: 100%"
        >
          <el-option label="逗号 (,)" value="," />
          <el-option label="分号 (;)" value=";" />
          <el-option label="制表符" value="\t" />
        </el-select>
      </el-form-item>

      <el-form-item label="包含表头">
        <el-switch v-model="formData.hasHeader" />
        <div class="text-xs text-gray-500 ml-2">文件第一行是否为字段名</div>
      </el-form-item>

      <el-form-item>
        <el-button :icon="Download" type="info" plain @click="downloadTemplate">
          下载模板文件
        </el-button>
      </el-form-item>
    </el-form>

    <template #footer>
      <div class="flex justify-end space-x-2">
        <el-button @click="closeDialog">取消</el-button>
        <el-button type="primary" @click="handleImport"> 开始导入 </el-button>
      </div>
    </template>
  </el-dialog>
</template>
