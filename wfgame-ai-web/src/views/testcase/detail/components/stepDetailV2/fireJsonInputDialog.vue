<script setup lang="ts">
import { ref, computed } from "vue";
import Codemirror from "codemirror-editor-vue3";
import "codemirror/mode/javascript/javascript.js";
import "codemirror/theme/idea.css";
import "codemirror/addon/display/autorefresh.js";
import "codemirror/addon/fold/foldgutter.css";
import "codemirror/addon/fold/foldcode";
import "codemirror/addon/fold/foldgutter";
import "codemirror/addon/fold/brace-fold";
import "codemirror/addon/fold/comment-fold";
import "codemirror/addon/fold/markdown-fold";
import "codemirror/addon/fold/xml-fold";
import "codemirror/addon/fold/indent-fold";
import { message } from "@/utils/message";
import { checkJson } from "@/api/testcase";
import { superRequest } from "@/utils/request";
import FireProtoSelectDialog from "@/views/testcase/detail/components/stepDetailV2/fireProtoSelectDialog.vue";

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  proto: {
    type: Object,
    default: () => {
      return {};
    }
  }
});

const newCaseBaseId = ref(0);
const newContentId = ref(0);
const newCatalogId = ref(0);
const newRequestArray = ref([]);
const newResponseArray = ref([]);
const newCaseName = ref("");
const baseJsonObj = ref({});
const selectShow = ref(false);

defineOptions({
  name: "FireJsonInputDialog"
});

const emits = defineEmits(["update:show", "reset"]);
const codeMirrorRef = ref(null);

const dialogVisible = computed({
  get: () => {
    if (props.show) {
      codeMirrorRef.value?.refresh();
    }
    return props.show;
  },
  set: val => {
    emits("update:show", val);
  }
});

const dialogTitle = ref("🐝 请输入 JSON 文本:");

const text = ref("");

const clearP = (done: () => void) => {
  done();
};

const cancel = () => {
  dialogVisible.value = false;
};

const confirm = () => {
  let paramsData = {};
  try {
    paramsData = JSON.parse(text.value);
    message("json结构校验成功!", { type: "success" });
    baseJsonObj.value = paramsData;
  } catch (error) {
    message(error.message, { type: "error" });
    return;
  }
  // 调用创建用例接口，并获取协议步骤相关数据
  superRequest({
    apiFunc: checkJson,
    apiParams: { request: paramsData },
    onSucceed: data => {
      text.value = "";
      newCaseBaseId.value = data.case_base_id;
      newContentId.value = data.case_content_id;
      newCatalogId.value = data.catalog_id;
      newRequestArray.value = data.request_array;
      newResponseArray.value = data.response_array;
      newCaseName.value = data.case_name;
      baseJsonObj.value = paramsData;
      dialogVisible.value = false;
      selectShow.value = true; // 触发子组件的显示
    }
  });
};

const cmOptions = {
  mode: "text/javascript",
  theme: "idea", // 主题样式
  lint: true,
  smartIndent: true, // 是否智能缩进
  styleActiveLine: true, // 当前行高亮
  lineNumbers: true, // 显示行号
  foldGutter: true, // 代码折叠
  lineWrapping: true, // 自动换行
  autoRefresh: true,
  gutters: [
    "CodeMirror-linenumbers",
    "CodeMirror-foldgutter",
    "CodeMirror-lint-markers"
  ],
  matchBrackets: true, // 括号匹配显示
  autoCloseBrackets: true // 输入和退格时成对
};

const handleReset = () => {
  emits("reset");
};

defineExpose({});
</script>

<template>
  <el-dialog
    class="json-parser"
    :title="dialogTitle"
    v-model="dialogVisible"
    width="50vw"
    :draggable="true"
    align-center
    :before-close="clearP"
  >
    <div
      class="flex items-center justify-between px-1 py-1 rounded-t-md dark:bg-transparent bg-[#F7F7F7] border-[1px] border-gray-200"
    >
      <!-- 操作 -->
      <div class="ml-auto flex">
        <el-button-group class="ml-4">
          <el-button title="清空填写内容" class="ml-2" plain @click="text = ''">
            清 空
          </el-button>
        </el-button-group>
      </div>
    </div>
    <Codemirror
      ref="codeMirrorRef"
      width="100%"
      height="50vh"
      v-model:value="text"
      :options="cmOptions"
      style="font-size: 18px"
      border
    />
    <template #footer>
      <div class="w-full h-full flex justify-start items-center mt-[-20px]">
        <div class="ml-auto">
          <el-button @click="cancel" size="large">取 消</el-button>
          <el-button type="primary" @click="confirm" size="large">
            确定
          </el-button>
        </div>
      </div>
    </template>
  </el-dialog>
  <FireProtoSelectDialog
    :newCaseBaseId="newCaseBaseId"
    :newContentId="newContentId"
    :newCatalogId="newCatalogId"
    :newCaseName="newCaseName"
    :new-request-array="newRequestArray"
    :new-response-array="newResponseArray"
    :base-json-obj="baseJsonObj"
    v-model:show="selectShow"
    @reset="handleReset"
  />
</template>

<style scoped>
.CodeMirror {
  line-height: 1.5;
}

.CodeMirror-gutter-wrapper {
  padding-right: 10px;
}
</style>
