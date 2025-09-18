<template>
  <el-dialog
    :title="title"
    v-model="visible"
    width="50vw"
    :draggable="true"
    align-center
    custom-class="api-man-dialog"
  >
    <div class="flex flex-col space-y-6 p-6">
      <!-- 请求方式选择 -->
      <div class="flex space-x-6">
        <el-select v-model="method" placeholder="请选择请求方式" class="w-1/3">
          <el-option label="GET" value="get" />
          <el-option label="POST" value="post" />
        </el-select>
        <!-- URL 输入框 -->
        <el-input v-model="url" placeholder="请输入请求 URL" class="w-2/3" />
      </div>
      <!-- JSON 编辑区域 -->
      <div class="h-80 border border-gray-300 rounded-md overflow-hidden">
        <Codemirror
          v-model:value="json"
          :options="cmOptions"
          style="font-size: 16px"
          smartIndent
          border
        />
      </div>
    </div>
    <template #footer>
      <div class="flex flex-col space-y-6 p-6">
        <!-- 执行按钮 -->
        <el-button type="primary" @click="executeRequest" class="self-center"
          >执行请求</el-button
        >
        <!-- 请求结果展示区域 -->
        <div
          v-if="responseData"
          class="border border-gray-300 p-4 rounded-md"
          :class="textClass"
        >
          <pre
            class="whitespace-pre-wrap text-left h-[100px] overflow-y-scroll"
          >
            {{ responseData }}
          </pre>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, defineProps, defineEmits, watch } from "vue";
import { http } from "../utils/http";
import { RequestMethods } from "../utils/http/types";
import { ApiResult } from "../api/utils";
import "codemirror/mode/javascript/javascript";
import Codemirror from "codemirror-editor-vue3";
import "codemirror/theme/darcula.css";
import "codemirror/addon/display/autorefresh.js";
import "codemirror/addon/fold/foldgutter.css";
import "codemirror/addon/fold/foldcode";
import "codemirror/addon/fold/foldgutter";
import "codemirror/addon/fold/brace-fold";
import "codemirror/addon/fold/comment-fold";
import "codemirror/addon/fold/markdown-fold";
import "codemirror/addon/fold/xml-fold";
import "codemirror/addon/fold/indent-fold";
import "codemirror/addon/fold/foldgutter.js";

// 定义组件的 props
const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: "Api Man"
  },
  method: {
    type: String,
    default: "get"
  },
  json: {
    type: String,
    default: "{}"
  },
  url: {
    type: String,
    default: ""
  }
});

// 定义组件的 emits
const emits = defineEmits(["update:modelValue"]);

// 控制模态框的显示和隐藏
const visible = ref(props.modelValue);
const method = ref(props.method);
const url = ref(props.url);
const json = ref(props.json);
const responseData = ref("");
const textClass = ref("");
// CodeMirror 配置
const cmOptions = {
  autoRefresh: true, // 重点是这句，为true
  scrollbarStyle: null,
  mode: "application/json", // 语言模式
  theme: "darcula", // 主题样式
  lineWrapping: false, // 是否自动换行
  // 代码折叠
  gutters: [
    "CodeMirror-lint-markers",
    "CodeMirror-linenumbers",
    "CodeMirror-foldgutter"
  ],
  foldGutter: true // 启用行槽中的代码折叠
};

// 监听 modelValue 的变化
watch(
  () => props.modelValue,
  newValue => {
    visible.value = newValue;
  }
);
watch(
  () => props.method,
  newValue => {
    method.value = newValue;
  }
);

watch(
  () => props.url,
  newValue => {
    url.value = newValue;
  }
);

watch(
  () => props.json,
  newValue => {
    json.value = newValue;
  }
);

// 执行请求的方法
const executeRequest = async () => {
  try {
    responseData.value = "正在请求...";
    let requestParams = {};
    if (method.value === "post") {
      requestParams = {
        data: JSON.parse(json.value)
      };
    } else {
      requestParams = {
        params: JSON.parse(json.value)
      };
    }
    const response = await http.request<ApiResult>(
      method.value as RequestMethods,
      url.value,
      requestParams
    );
    responseData.value = JSON.stringify(response, null, 2);
    textClass.value = "text-green-500";
  } catch (error) {
    const errResp = error?.response?.data;
    textClass.value = "text-red-500";
    if (errResp) {
      responseData.value = JSON.stringify(errResp, null, 2);
    } else {
      responseData.value = `请求错误，错误信息：${error?.message}`;
    }
  }
};

// 监听 visible 的变化，更新 modelValue
watch(visible, newValue => {
  emits("update:modelValue", newValue);
});
</script>

<style scoped>
/* 自定义对话框样式 */
.api-man-dialog .el-dialog__body {
  padding: 0;
}

/* 输入框和选择框样式 */
.el-select,
.el-input {
  border-radius: 4px;
  border: 1px solid #dcdfe6;
}

/* 执行按钮样式 */
.el-button {
  padding: 12px 24px;
  border-radius: 4px;
}

/* 请求结果展示区域样式 */
.text-green-500 {
  color: #67c23a;
}

.text-red-500 {
  color: #f56c6c;
}
</style>
