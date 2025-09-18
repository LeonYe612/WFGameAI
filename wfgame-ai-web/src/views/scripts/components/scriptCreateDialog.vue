<script setup lang="ts">
import { ref, reactive } from "vue";
import { Document, Plus } from "@element-plus/icons-vue";
import { saveScriptContent } from "@/api/scripts";
import type { ScriptCategory } from "@/api/scripts";
import { superRequest } from "@/utils/request";
import { message } from "@/utils/message";
import { scriptFormRules } from "../utils/rules";
import type { FormInstance } from "element-plus";

defineOptions({
  name: "ScriptCreateDialog"
});

defineProps<{
  categories: ScriptCategory[];
}>();

const emit = defineEmits(["created"]);

const dialogVisible = ref(false);
const loading = ref(false);
const formRef = ref<FormInstance>();

const scriptForm = reactive({
  filename: "",
  category: "",
  description: "",
  content: ""
});

// 默认脚本模板
const defaultTemplate = `{
  "name": "新建脚本",
  "version": "1.0",
  "description": "请描述脚本功能",
  "steps": [
    {
      "action": "click",
      "target": {
        "type": "coordinate",
        "x": 100,
        "y": 100
      },
      "description": "点击坐标(100, 100)"
    }
  ],
  "settings": {
    "delay": 1000,
    "timeout": 30000
  }
}`;

const showDialog = () => {
  resetForm();
  dialogVisible.value = true;
};

const resetForm = () => {
  Object.assign(scriptForm, {
    filename: "",
    category: "",
    description: "",
    content: defaultTemplate
  });
  formRef.value?.resetFields();
};

const formatJson = () => {
  try {
    const parsed = JSON.parse(scriptForm.content);
    scriptForm.content = JSON.stringify(parsed, null, 2);
    message("JSON格式化成功", { type: "success" });
  } catch (error) {
    message("JSON格式错误，无法格式化", { type: "error" });
  }
};

const createScript = async () => {
  if (!formRef.value) return;

  try {
    await formRef.value.validate();

    // 验证JSON格式
    try {
      JSON.parse(scriptForm.content);
    } catch (error) {
      message("JSON格式错误，请检查语法", { type: "error" });
      return;
    }

    // 确保文件名以.json结尾
    let filename = scriptForm.filename.trim();
    if (!filename.endsWith(".json")) {
      filename += ".json";
    }

    await superRequest({
      apiFunc: saveScriptContent,
      apiParams: [filename, scriptForm.content],
      enableSucceedMsg: true,
      succeedMsgContent: "脚本创建成功！",
      onBeforeRequest: () => {
        loading.value = true;
      },
      onSucceed: () => {
        emit("created");
        closeDialog();
      },
      onFailed: () => {
        message("脚本创建失败", { type: "error" });
      },
      onCompleted: () => {
        loading.value = false;
      }
    });
  } catch (error) {
    console.error("表单验证失败:", error);
  }
};

const closeDialog = () => {
  dialogVisible.value = false;
  resetForm();
};

const useTemplate = (templateType: string) => {
  let template = "";

  switch (templateType) {
    case "click":
      template = `{
  "name": "点击脚本",
  "version": "1.0",
  "description": "点击指定坐标的脚本",
  "steps": [
    {
      "action": "click",
      "target": {
        "type": "coordinate",
        "x": 100,
        "y": 100
      },
      "description": "点击坐标(100, 100)"
    }
  ],
  "settings": {
    "delay": 1000,
    "timeout": 30000
  }
}`;
      break;

    case "input":
      template = `{
  "name": "输入脚本",
  "version": "1.0",
  "description": "输入文本的脚本",
  "steps": [
    {
      "action": "input",
      "target": {
        "type": "coordinate",
        "x": 100,
        "y": 100
      },
      "text": "Hello World",
      "description": "在坐标(100, 100)输入文本"
    }
  ],
  "settings": {
    "delay": 1000,
    "timeout": 30000
  }
}`;
      break;

    case "swipe":
      template = `{
  "name": "滑动脚本",
  "version": "1.0",
  "description": "滑动操作的脚本",
  "steps": [
    {
      "action": "swipe",
      "start": {
        "x": 100,
        "y": 100
      },
      "end": {
        "x": 200,
        "y": 200
      },
      "duration": 1000,
      "description": "从(100, 100)滑动到(200, 200)"
    }
  ],
  "settings": {
    "delay": 1000,
    "timeout": 30000
  }
}`;
      break;

    case "wait":
      template = `{
  "name": "等待脚本",
  "version": "1.0",
  "description": "等待指定时间的脚本",
  "steps": [
    {
      "action": "wait",
      "duration": 3000,
      "description": "等待3秒"
    }
  ],
  "settings": {
    "delay": 1000,
    "timeout": 30000
  }
}`;
      break;

    default:
      template = defaultTemplate;
  }

  scriptForm.content = template;
  message(`已应用${templateType}模板`, { type: "success" });
};

defineExpose({
  showDialog
});
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    title="新建脚本"
    width="90%"
    :draggable="true"
    @close="closeDialog"
  >
    <div v-loading="loading" class="script-create-content">
      <el-form
        ref="formRef"
        :model="scriptForm"
        :rules="scriptFormRules"
        label-width="100px"
        class="create-form"
      >
        <!-- 脚本基本信息 -->
        <el-card shadow="never" class="border mb-4">
          <template #header>
            <div class="flex items-center">
              <el-icon class="mr-2">
                <Document />
              </el-icon>
              <span class="font-medium">脚本信息</span>
            </div>
          </template>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <el-form-item label="脚本名称" prop="filename">
              <el-input
                v-model="scriptForm.filename"
                placeholder="请输入脚本名称"
                :disabled="loading"
              >
                <template #suffix>.json</template>
              </el-input>
            </el-form-item>

            <el-form-item label="脚本分类" prop="category">
              <el-select
                v-model="scriptForm.category"
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
            </el-form-item>
          </div>

          <el-form-item label="脚本描述" prop="description">
            <el-input
              v-model="scriptForm.description"
              type="textarea"
              :rows="2"
              placeholder="请输入脚本描述（可选）"
              :disabled="loading"
            />
          </el-form-item>
        </el-card>

        <!-- 脚本模板 -->
        <el-card shadow="never" class="border mb-4">
          <template #header>
            <div class="flex items-center justify-between">
              <span class="font-medium">脚本模板</span>
              <div class="flex space-x-2">
                <el-button
                  size="small"
                  type="primary"
                  @click="useTemplate('click')"
                  :disabled="loading"
                >
                  点击模板
                </el-button>
                <el-button
                  size="small"
                  type="success"
                  @click="useTemplate('input')"
                  :disabled="loading"
                >
                  输入模板
                </el-button>
                <el-button
                  size="small"
                  type="warning"
                  @click="useTemplate('swipe')"
                  :disabled="loading"
                >
                  滑动模板
                </el-button>
                <el-button
                  size="small"
                  type="info"
                  @click="useTemplate('wait')"
                  :disabled="loading"
                >
                  等待模板
                </el-button>
              </div>
            </div>
          </template>

          <div class="text-sm text-gray-600 mb-3">
            选择一个模板快速开始，或者直接编辑下方的JSON内容
          </div>
        </el-card>

        <!-- 脚本内容编辑器 -->
        <el-card shadow="never" class="border">
          <template #header>
            <div class="flex items-center justify-between">
              <span class="font-medium">脚本内容</span>
              <div class="flex space-x-2">
                <el-button
                  size="small"
                  type="info"
                  @click="formatJson"
                  :disabled="loading"
                >
                  格式化JSON
                </el-button>
              </div>
            </div>
          </template>

          <el-form-item prop="content">
            <el-input
              v-model="scriptForm.content"
              type="textarea"
              :rows="20"
              placeholder="请输入脚本内容（JSON格式）"
              class="font-mono"
              :disabled="loading"
            />
          </el-form-item>

          <!-- 字符统计 -->
          <div class="flex justify-between items-center text-sm text-gray-500">
            <span>字符数: {{ scriptForm.content.length }}</span>
            <span class="text-blue-500">
              <i class="el-icon-info mr-1" />
              请确保JSON格式正确
            </span>
          </div>
        </el-card>
      </el-form>
    </div>

    <template #footer>
      <div class="flex justify-end space-x-2">
        <el-button @click="closeDialog" :disabled="loading"> 取消 </el-button>
        <el-button
          type="primary"
          :icon="Plus"
          :loading="loading"
          @click="createScript"
        >
          {{ loading ? "创建中..." : "创建脚本" }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.script-create-content {
  min-height: 400px;
}

.create-form :deep(.el-textarea__inner) {
  font-family: "Consolas", "Monaco", "Courier New", monospace;
  background-color: #f8f9fa;
  border: 1px solid #e9ecef;
}

.font-mono {
  font-family: "Consolas", "Monaco", "Courier New", monospace;
}
</style>
