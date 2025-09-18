<script setup lang="ts">
import { ref } from "vue";
import { Plus, Document, DocumentCopy, Coin } from "@element-plus/icons-vue";
import type { DataSource } from "@/api/data";
import { DATA_SOURCE_TYPES } from "../utils/types";
import { dataSourceFormRules, databaseConfigRules } from "../utils/rules";
import type { FormInstance } from "element-plus";

defineOptions({
  name: "DataSourceDialog"
});

defineProps<{
  modelValue: boolean;
}>();

const emit = defineEmits(["update:modelValue", "confirm"]);

const formRef = ref<FormInstance>();
const fileInput = ref<HTMLInputElement>();
const formData = ref<Partial<DataSource>>({
  name: "",
  type: "excel",
  description: "",
  config: {}
});

const isEdit = ref(false);

// 显示对话框
const showDialog = (source?: DataSource) => {
  if (source) {
    formData.value = { ...source };
    isEdit.value = true;
  } else {
    formData.value = {
      name: "",
      type: "excel",
      description: "",
      config: {}
    };
    isEdit.value = false;
  }
  emit("update:modelValue", true);
};

// 关闭对话框
const closeDialog = () => {
  emit("update:modelValue", false);
  formRef.value?.resetFields();
};

// 确认提交
const handleConfirm = async () => {
  if (!formRef.value) return;

  try {
    await formRef.value.validate();
    emit("confirm", formData.value);
    closeDialog();
  } catch (error) {
    console.error("表单验证失败:", error);
  }
};

// 文件选择处理
const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];
  if (file) {
    if (!formData.value.config) {
      formData.value.config = {};
    }
    formData.value.config.filePath = file.name;
    // 这里可以添加文件上传逻辑
  }
};

// 数据库配置字段
const databaseFields = [
  { key: "host", label: "主机地址", placeholder: "localhost" },
  { key: "port", label: "端口", placeholder: "3306" },
  { key: "database", label: "数据库名", placeholder: "database_name" },
  { key: "username", label: "用户名", placeholder: "username" },
  { key: "password", label: "密码", placeholder: "password", type: "password" }
];

defineExpose({
  showDialog
});
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    :title="isEdit ? '编辑数据源' : '新建数据源'"
    width="600px"
    :draggable="true"
    @close="closeDialog"
  >
    <el-form
      ref="formRef"
      :model="formData"
      :rules="dataSourceFormRules"
      label-width="100px"
      label-position="left"
    >
      <el-form-item label="数据源名称" prop="name">
        <el-input
          v-model="formData.name"
          placeholder="请输入数据源名称"
          clearable
        />
      </el-form-item>

      <el-form-item label="数据源类型" prop="type">
        <el-select
          v-model="formData.type"
          placeholder="请选择数据源类型"
          style="width: 100%"
          :disabled="isEdit"
        >
          <el-option
            v-for="type in DATA_SOURCE_TYPES"
            :key="type.value"
            :label="type.label"
            :value="type.value"
          >
            <div class="flex items-center">
              <el-icon class="mr-2">
                <Document
                  v-if="type.value === 'excel' || type.value === 'csv'"
                />
                <Coin v-else-if="type.value === 'database'" />
                <DocumentCopy v-else />
              </el-icon>
              {{ type.label }}
            </div>
          </el-option>
        </el-select>
      </el-form-item>

      <el-form-item label="描述" prop="description">
        <el-input
          v-model="formData.description"
          type="textarea"
          :rows="3"
          placeholder="请输入数据源描述（可选）"
        />
      </el-form-item>

      <!-- 数据库连接配置 -->
      <div v-if="formData.type === 'database'">
        <el-divider content-position="left">数据库连接配置</el-divider>

        <el-form-item
          v-for="field in databaseFields"
          :key="field.key"
          :label="field.label"
          :prop="`config.${field.key}`"
          :rules="databaseConfigRules[field.key]"
        >
          <el-input
            v-model="formData.config![field.key]"
            :type="field.type || 'text'"
            :placeholder="field.placeholder"
            clearable
          />
        </el-form-item>
      </div>

      <!-- 文件配置 -->
      <div v-if="['excel', 'csv', 'json'].includes(formData.type!)">
        <el-divider content-position="left">文件配置</el-divider>

        <el-form-item label="文件路径">
          <el-input
            v-model="formData.config!.filePath"
            placeholder="请输入文件路径或上传文件"
            clearable
          >
            <template #append>
              <el-button :icon="Plus" @click="fileInput?.click()">
                选择文件
              </el-button>
            </template>
          </el-input>
          <input
            ref="fileInput"
            type="file"
            style="display: none"
            :accept="
              formData.type === 'excel'
                ? '.xlsx,.xls'
                : formData.type === 'csv'
                ? '.csv'
                : '.json'
            "
            @change="handleFileSelect"
          />
        </el-form-item>

        <el-form-item v-if="formData.type === 'csv'" label="编码格式">
          <el-select
            v-model="formData.config!.encoding"
            placeholder="请选择编码格式"
            style="width: 100%"
          >
            <el-option label="UTF-8" value="utf-8" />
            <el-option label="GBK" value="gbk" />
            <el-option label="GB2312" value="gb2312" />
          </el-select>
        </el-form-item>

        <el-form-item v-if="formData.type === 'csv'" label="分隔符">
          <el-select
            v-model="formData.config!.delimiter"
            placeholder="请选择分隔符"
            style="width: 100%"
          >
            <el-option label="逗号 (,)" value="," />
            <el-option label="分号 (;)" value=";" />
            <el-option label="制表符" value="\t" />
          </el-select>
        </el-form-item>

        <el-form-item
          v-if="['excel', 'csv'].includes(formData.type!)"
          label="包含表头"
        >
          <el-switch v-model="formData.config!.hasHeader" />
        </el-form-item>
      </div>
    </el-form>

    <template #footer>
      <div class="flex justify-end space-x-2">
        <el-button @click="closeDialog">取消</el-button>
        <el-button type="primary" @click="handleConfirm">
          {{ isEdit ? "更新" : "创建" }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>
