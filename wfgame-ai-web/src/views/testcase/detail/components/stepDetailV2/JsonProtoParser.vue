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
import { useTestcaseStoreHook } from "@/store/modules/testcase";
import { nextTick } from "vue";

const testcaseStore = useTestcaseStoreHook();

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

const emits = defineEmits(["update:show"]);
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

let protoInfo: any;
const text = ref("");

const clearP = (done: () => void) => {
  protoInfo = null;
  done();
};

const cancel = () => {
  dialogVisible.value = false;
};

// 将小驼峰格式字符串转换为下划线格式
const camelToSnake = (s: string) => {
  return s
    .replace(/[\w]([A-Z])/g, function (m) {
      return m[0] + "_" + m[1];
    })
    .toLowerCase();
};

// 将Long类型转换为Number类型
type Long = {
  low: number;
  high: number;
  unsigned: boolean;
};
const longToInt = (longObj: Long) => {
  // 无符号和有符号分别计算
  return longObj.unsigned
    ? (longObj.high >>> 0) * (1 << 16) * (1 << 16) + (longObj.low >>> 0)
    : longObj.high * (1 << 16) * (1 << 16) + (longObj.low >>> 0);
};

// 递归对象的每个键去将Long类型转换为Number类型
const convertLongTypeToInt = (obj: any) => {
  for (const key in obj) {
    const value = obj[key];
    // 检查当前键的值是否是对象，并且包含 low, high, unsigned 这三个键
    if (
      value &&
      typeof value === "object" &&
      "low" in value &&
      "high" in value &&
      "unsigned" in value
    ) {
      obj[key] = longToInt(value);
    } else if (typeof value === "object") {
      // 如果当前键的值是一个对象，则递归调用此函数
      convertLongTypeToInt(value);
    }
  }
};

const fillProtoDataFromJson = (nodes: any, jsonData: any) => {
  for (let i = 0; i < nodes.length; i++) {
    // debugger;
    const node = nodes[i];
    const fieldName = node.field;
    let jsonValue;
    if (node.modifier === "item") {
      jsonValue = jsonData?.[i];
    } else {
      jsonValue = jsonData?.[fieldName];
      if (jsonValue === undefined) {
        jsonValue = jsonData?.[camelToSnake(fieldName)];
      }
    }
    if (jsonValue === undefined) {
      if (testcaseStore.shareState.jsonParserStrictMode) {
        // 严格模式下，如果json数据中不存在对应的字段，则抛出错误
        throw new Error(`json数据中, 字段 ${fieldName} 不存在！`);
      } else {
        // 非严格模式下，如果json数据中不存在对应的字段，则跳过
        continue;
      }
    }

    // A. 参数有子节点
    if (node?.children?.length) {
      // A.1 repeated 类型
      if (node.modifier === "repeated") {
        // a. 确认json数据对应的字段类型为：数组
        if (!Array.isArray(jsonValue)) {
          throw new Error(
            `json数据中, 字段 ${fieldName} 不是数组类型(Array)！`
          );
        }
        // b. 确保 len(field.childern) == len(jsonValue)
        if (node.children.length !== jsonValue.length) {
          const template = JSON.stringify(node.children[0]);
          node.children = [];
          // 如果没有记录模板，就记录一个
          if (!node?.childTemplate) {
            node.childTemplate = JSON.parse(template);
          }
          for (let i = 0; i < jsonValue.length; i++) {
            const child = JSON.parse(template);
            child.key = testcaseStore.uniqueId();
            node.children.push(child);
          }
        }

        // c. 遍历数组, 递归填充子节点
        fillProtoDataFromJson(node.children, jsonValue);
      }
      // A.2 map 类型
      if (node.modifier === "map") {
        // a. 确认json数据对应的字段类型为：对象
        if (typeof jsonValue !== "object") {
          throw new Error(
            `json数据中, 字段 ${fieldName} 不是对象类型(Object)！`
          );
        }
        // b. 确保 len(field.childern) == len(jsonValue)
        if (node.children.length !== Object.keys(jsonValue).length) {
          const template = JSON.stringify(node.children[0]);
          node.children = [];
          if (!node?.childTemplate) {
            node.childTemplate = JSON.parse(template);
          }
          for (const _ in jsonValue) {
            const child = JSON.parse(template);
            child.key = testcaseStore.uniqueId();
            node.children.push(child);
          }
        }
        // c. 遍历对象, 递归填充子节点
        fillProtoDataFromJson(node.children, jsonValue);
      }
      // A.3 optional 类型
      if (node.modifier !== "repeated" && node.modifier !== "map") {
        fillProtoDataFromJson(node.children, jsonValue);
      }
    }

    // B. 参数无子节点
    if (String(jsonValue).includes("!")) {
      node.operator = "!=";
      jsonValue = jsonValue.replace("!", "");
    }

    node.value = jsonValue;
  }
};

const confirm = () => {
  try {
    protoInfo = props.proto;
    const data = JSON.parse(text.value);
    // 1. 兼容两种json数据格式
    // a. 如果 json数据中有code字段, 则认为其为: {code: xxx, body: xxx} 格式 (报告中的json)
    // b. 否则, 认为其为: {xxx: xxx} 格式 (前端控制台中的json)
    let paramsData = {};
    if (Object.keys(data).includes("code")) {
      protoInfo.code = data.code;
      paramsData = data.body || {};
    } else {
      paramsData = data || {};
    }

    // 2. 将Long类型转换为Number类型
    convertLongTypeToInt(paramsData);

    // 3. 填充协议参数值
    fillProtoDataFromJson(protoInfo.proto_data, paramsData);

    // 4. 为每个参数添加key
    testcaseStore.addKeyForProtoData(protoInfo);
    dialogVisible.value = false;
    message("成功将json数据填充到协议参数值!", { type: "success" });

    // 5. 通过变更选中协议索引，刷新显示
    const temp = testcaseStore.currentProtoIndex;
    testcaseStore.currentProtoIndex = -1;
    nextTick(() => {
      testcaseStore.currentProtoIndex = temp;
    });
  } catch (error) {
    message(error.message, { type: "error" });
  }
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
      <!-- 协议基础信息 -->
      <div v-if="false">
        <el-tag class="ml-2 font-mono" type="" size="large">
          <span class="font-bold text-base">
            ID: {{ props.proto?.proto_id }}
          </span>
        </el-tag>
        <div class="flex justify-center items-center ml-3">
          <el-tooltip
            :content="props.proto?.proto_name"
            effect="light"
            placement="top"
          >
            <IconifyIconOnline icon="material-symbols:help-outline" />
          </el-tooltip>
        </div>
        <div class="flex-1 items-center justify-start truncate px-1">
          <span class="text-base font-semibold font-serif text-gray-700">
            {{ props.proto?.proto_message }}
          </span>
        </div>
      </div>
      <!-- 操作 -->
      <div class="flex justify-center items-center">
        <el-tooltip
          content="严格模式下: 如果json数据中不存在对应的字段会抛出错误并停止填充"
          effect="light"
          placement="top"
        >
          <IconifyIconOnline
            class="mx-1"
            icon="material-symbols:help-outline"
          />
        </el-tooltip>
        <el-switch
          style="zoom: 1.2"
          v-model="testcaseStore.shareState.jsonParserStrictMode"
          inline-prompt
          inactive-color="#a6a6a6"
          active-text="严格模式"
          inactive-text="严格模式"
        />
      </div>

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
</template>
<style scoped>
.CodeMirror {
  line-height: 1.5;
}

.CodeMirror-gutter-wrapper {
  padding-right: 10px;
}
</style>
