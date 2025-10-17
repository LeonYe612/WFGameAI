<script setup lang="ts">
import { ref, watch, computed, nextTick } from "vue";
import { useScriptStoreHook } from "@/store/modules/script";
import Codemirror from "codemirror-editor-vue3";
import type { Editor } from "codemirror";
import "codemirror/mode/javascript/javascript.js";
import "codemirror/theme/dracula.css";
import "codemirror/addon/selection/active-line.js";
import { CopyDocument } from "@element-plus/icons-vue";
import { copyText } from "@/utils/utils";

defineOptions({
  name: "ScriptStepsJson"
});

const scriptStore = useScriptStoreHook();
const code = ref("");
const cmEditorRef = ref(null);
let editor: Editor | null = null;
let lineHighlightMarker = null;

const cmOptions = {
  mode: "application/json",
  theme: "dracula",
  lineNumbers: true,
  smartIndent: true,
  indentUnit: 2,
  foldGutter: true,
  gutters: ["CodeMirror-linenumbers", "CodeMirror-foldgutter"],
  styleActiveLine: true
};

const stepsJson = computed(() => JSON.stringify(scriptStore.getSteps, null, 2));
const activeFocus = computed(() => scriptStore.getActiveFocus);

const highlightLine = (stepIndex: number, paramName: string) => {
  if (!editor) return;
  const line = findLineNumberForStep(stepIndex, paramName);
  if (line !== -1) {
    // 滚动到行
    editor.scrollIntoView({ line, ch: 0 }, 100);
    // 高亮行
    if (lineHighlightMarker) {
      lineHighlightMarker.clear();
      lineHighlightMarker = null;
    }
    lineHighlightMarker = editor.markText(
      { line, ch: 0 },
      { line, ch: editor.getLine(line)?.length || 0 },
      { className: "highlight-line" }
    );
    // 短暂高亮后移除
    // setTimeout(() => {
    //   if (lineHighlightMarker) {
    //     lineHighlightMarker.clear();
    //     lineHighlightMarker = null;
    //   }
    // }, 1500);
  }
};

watch(
  stepsJson,
  newJson => {
    if (code.value !== newJson) {
      code.value = newJson;
      nextTick(() => {
        highlightLine(
          activeFocus.value?.stepIndex,
          activeFocus.value?.paramName
        );
      });
    }
  },
  { immediate: true }
);

const onCodeChange = newCode => {
  try {
    const newSteps = JSON.parse(newCode);
    scriptStore.updateSteps(newSteps);
  } catch (e) {
    // 忽略无效的JSON
  }
};

const onReady = (cm: Editor) => {
  editor = cm;
};

// --- 从 StepsList 到 Codemirror 的同步 ---
watch(activeFocus, newFocus => {
  if (!newFocus || !newFocus.stepIndex === null) return;
  nextTick(() => {
    highlightLine(newFocus.stepIndex, newFocus.paramName);
  });
});

// --- 从 Codemirror 到 StepsList 的同步 ---
const onCursorActivity = (cm: Editor) => {
  const cursor = cm.getCursor();
  const line = cursor.line;
  if (!line) return;
  const { stepIndex, paramName } = findStepFromLineNumber(line);
  scriptStore.setActiveFocus(stepIndex, paramName);
};

/**
 * 根据步骤索引和参数名查找在JSON字符串中的行号
 */
const findLineNumberForStep = (
  stepIndex: number,
  paramName: string | null
): number => {
  const lines = code.value.split("\n");
  let objectStartIndex = -1;
  let objectCounter = -1;

  for (let i = 0; i < lines.length; i++) {
    if (lines[i].trim().includes(`"action":`)) {
      objectCounter++;
      if (objectCounter === stepIndex) {
        objectStartIndex = i;
        break;
      }
    }
  }

  if (objectStartIndex === -1) return -1;

  if (!paramName) {
    return objectStartIndex;
  }

  // 在对象内部查找参数
  for (let i = objectStartIndex; i < lines.length; i++) {
    const lineContent = lines[i].trim();
    if (lineContent.startsWith(`"${paramName}"`)) {
      return i;
    }
    if (lineContent === "}" && i > objectStartIndex) {
      // 超出当前对象范围
      break;
    }
  }

  return objectStartIndex; // 如果找不到参数，则返回对象的起始行
};

/**
 * 根据行号反向查找步骤索引和参数名
 */
const findStepFromLineNumber = (
  line: number
): { stepIndex: number | null; paramName: string | null } => {
  const lines = code.value.split("\n");
  let stepIndex = -1;

  for (let i = 0; i <= line; i++) {
    if (lines[i].trim() === "{") {
      stepIndex++;
    }
  }

  if (stepIndex === -1) return { stepIndex: null, paramName: null };

  // 尝试解析当前行的参数名
  const currentLine = lines[line].trim();
  const match = currentLine.match(/"([^"]+)"\s*:/);
  const paramName = match ? match[1] : null;

  return { stepIndex, paramName };
};

const handleCopyJson = () => {
  copyText(code.value);
};
</script>

<template>
  <div class="json-editor">
    <div class="flex">
      <h3 class="font-bold mb-2 text-white h-[34px]">📋 JSON</h3>
      <!-- 复制按钮 -->
      <el-button
        class="ml-auto mr-2"
        type="text"
        title="复制"
        plain
        @click="handleCopyJson"
      >
        <el-icon :size="20">
          <CopyDocument />
        </el-icon>
      </el-button>
    </div>
    <Codemirror
      ref="cmEditorRef"
      class="cm-editor"
      v-model:value="code"
      :options="cmOptions"
      border
      @change="onCodeChange"
      @ready="onReady"
      @cursor-activity="onCursorActivity"
    />
  </div>
</template>

<style>
.json-editor {
  height: 100%;
  display: flex;
  flex-direction: column;
  .cm-editor {
    flex: 1;
    min-height: 0; /* 允许Codemirror在Flex容器中正确收缩 */
  }
}

.highlight-line {
  background-color: #0b4d99;
  transition: background-color 0.5s;
}
</style>
