<script setup lang="ts">
import { ref, computed, nextTick } from "vue";
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
import { syncCases } from "@/api/testcase";
import { superRequest } from "@/utils/request";
import { CopyDocument, Delete } from "@element-plus/icons-vue";
import draggable from "vuedraggable";
import DragIcon from "@/assets/svg/drag.svg?component";
import { v4 as uuidv4 } from "uuid";

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  newCaseBaseId: {
    type: Number,
    default: 0
  },
  newContentId: {
    type: Number,
    default: 0
  },
  newCatalogId: {
    type: Number,
    default: 0
  },
  newRequestArray: {
    type: Array,
    default: () => []
  },
  newResponseArray: {
    type: Array,
    default: () => []
  },
  newCaseName: {
    type: String,
    default: ref("")
  },
  baseJsonObj: {
    type: Object,
    default: () => {
      return {};
    }
  }
});

defineOptions({
  name: "FireProtoSelectDialog"
});
const stepTable = ref(null);
const dialogTitle = ref("🐝 请选择所需要的步骤:");
const stepScrollRef = ref(null);
const addStepList = ref([]);
const stepList = computed(() => {
  return props.newRequestArray.concat(props.newResponseArray).map(item => ({
    ...item,
    _disabled: false
  }));
});
// console.log("stepList : ", stepList);
const emits = defineEmits(["update:show", "reset"]);

const dialogVisible = computed({
  get: () => props.show,
  set: val => emits("update:show", val)
});

const clearP = (done: () => void) => {
  done();
};

const cancel = () => {
  dialogVisible.value = false;
};

const confirm = () => {
  if (addStepList.value.length === 0) {
    message("请先选择需要添加的步骤", { type: "warning" });
    return;
  }
  // 调用创建用例接口，并获取协议步骤相关数据
  const requestArray = handleCases(addStepList.value, props.baseJsonObj);
  superRequest({
    apiFunc: syncCases,
    apiParams: {
      case_base_id: props.newCaseBaseId,
      case_content_id: props.newContentId,
      catalog_id: props.newCatalogId,
      // case_name: props.newCaseName, // 目前不在此处修改用例名称
      request: requestArray
    },
    enableSucceedMsg: true,
    succeedMsgContent: "用例步骤生成成功 ！",
    enableFailedMsg: true
  });
  addStepList.value = [];
  dialogVisible.value = false;
  reset();
};

// 滚动到最底部
const scrollToBottom = () => {
  nextTick(() => {
    stepScrollRef.value.setScrollTop((addStepList.value.length || 0) * 100);
  });
};

const addStep = () => {
  const selectedRows = stepTable.value.getSelectionRows();
  if (selectedRows.length === 0) {
    message("请先选择需要添加的协议", { type: "warning" });
    return;
  }
  const hasRequest = selectedRows.some(row => row.type === "request");
  if (!hasRequest) {
    message("请选择至少一个 request 类型的步骤", { type: "error" });
    return;
  }
  // 创建一个新的步骤对象
  const newStep = {
    uuid: uuidv4(),
    name: "",
    send: [],
    recv: []
  };

  // 遍历选中的行，更新 newStep 对象
  selectedRows.forEach(row => {
    if (row.type === "request") {
      newStep.name = row.proto_name;
      newStep.send.push(row.step_id);
    } else if (row.type === "response") {
      newStep.recv.push(row.step_id);
    }
  });

  // 将新步骤对象添加到步骤列表中
  addStepList.value.push(newStep);
  stepTable.value.clearSelection();
  scrollToBottom();
};

// 拷贝步骤
const copyStep = element => {
  // 只更新对应的uuid，其他不变
  element.uuid = uuidv4();
  addStepList.value.push(element);
};

// 清理所有步骤
const clearStep = () => {
  addStepList.value = [];
};

// 删除指定步骤
const deleteStep = element => {
  const index = addStepList.value.findIndex(item => item.uuid === element.uuid);
  addStepList.value.splice(index, 1);
};

// 选择行变更事件处理
const handleSelectionChange = selection => {
  let hasRequestSelected = false;

  // 检查是否有 request 类型的行被选中
  selection.forEach(row => {
    if (row.type === "request") {
      hasRequestSelected = true;
    }
  });

  if (hasRequestSelected) {
    // 如果有 request 类型的行被选中，则将其他 request 类型的行设置为不可选择
    stepList.value.forEach(row => {
      if (
        row.type === "request" &&
        !selection.some(selectedRow => selectedRow.step_id === row.step_id)
      ) {
        row._disabled = true;
      } else if (
        row.type === "request" &&
        selection.some(selectedRow => selectedRow.step_id === row.step_id)
      ) {
        row._disabled = false;
      }
    });
  } else {
    // 如果没有 request 类型的行被选中，则将所有 request 类型的行设置为可选择
    stepList.value.forEach(row => {
      if (row.type === "request") {
        row._disabled = false;
      }
    });
  }
};

// 查询当前行是否可选
const selectable = row => {
  return !row._disabled;
};

// 拼接协议内容
const handleCases = (addStepList, base_obj) => {
  const finalArray = [];
  addStepList.forEach(item => {
    const newDict = {};
    // 处理 send /recv 数组
    item.send.concat(item.recv).forEach(step_id => {
      console.log("==>>> step_id: ", step_id);
      if (base_obj[step_id]) {
        newDict[step_id] = base_obj[step_id];
      }
    });
    finalArray.push(newDict);
  });

  return finalArray;
};

// 【重置按钮】点击事件
const reset = () => {
  emits("reset");
};

defineExpose({});
</script>

<template>
  <el-dialog
    class="json-parser"
    :title="dialogTitle"
    v-model="dialogVisible"
    width="80vw"
    :draggable="true"
    align-center
    :before-close="clearP"
  >
    <el-container class="main-content cursor-pointer" style="height: 65vh">
      <!--A 协议列表-->
      <div class="w-[45%] h-full border border-gray-300 rounded">
        <el-container class="h-full">
          <el-header>
            <div class="h-full flex justify-center items-center">
              <h3 class="text-info text-center">协议列表</h3>
            </div>
          </el-header>
          <el-main>
            <!-- 表格 -->
            <el-table
              ref="stepTable"
              :data="stepList"
              row-key="step_id"
              @selection-change="handleSelectionChange"
              height="100%"
              empty-text="请先选择测试用例"
              :default-sort="{ prop: 'step_id', order: 'ascending' }"
              stripe
              fit
              :cell-style="{ textAlign: 'left' }"
              :header-cell-style="{
                textAlign: 'left',
                fontWeight: 'bolder'
              }"
            >
              <el-table-column
                label="步骤id"
                type="selection"
                prop="step_id"
                width="55"
                sortable
                :selectable="selectable"
              />
              <el-table-column label="步骤id" prop="step_id" width="100" />
              <el-table-column label="协议id" prop="proto_id" width="120" />
              <el-table-column label="协议名称" prop="proto_name" width="200">
                <template #default="{ row }">
                  <div
                    :style="{
                      backgroundColor:
                        row.proto_name === 'unknown' ? 'red' : '',
                      padding: '5px',
                      borderRadius: '4px',
                      display: 'inline-block'
                    }"
                  >
                    <span
                      :style="{
                        color: row.proto_name === 'unknown' ? 'black' : ''
                      }"
                    >
                      {{ row.proto_name }}
                    </span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="协议类型" prop="type" sortable>
                <template #default="{ row }">
                  <div
                    :style="{
                      backgroundColor:
                        row.type === 'request' ? '#ffe6e6' : '#e6ffe6',
                      padding: '5px',
                      borderRadius: '4px',
                      display: 'inline-block'
                    }"
                  >
                    <span
                      :style="{
                        color: row.type === 'request' ? 'red' : 'green'
                      }"
                    >
                      {{ row.type }}
                    </span>
                  </div>
                </template>
              </el-table-column>
            </el-table>
          </el-main>
        </el-container>
      </div>
      <!--B 添加按钮-->
      <div class="w-[10%] h-full border border-gray-300 rounded">
        <el-container class="h-full">
          <el-header>
            <div class="h-full flex justify-center items-center">
              <h3 class="text-info text-center" />
            </div>
          </el-header>
          <el-button
            style="margin-top: 150%; height: 50px"
            type="warning"
            plain
            @click="addStep"
          >
            添加步骤
          </el-button>
        </el-container>
      </div>
      <!--C 步骤列表-->
      <div class="w-[45%] h-full border border-gray-300 rounded">
        <el-container class="h-full">
          <el-header>
            <div class="h-full flex justify-center items-center">
              <h3 class="text-info text-center text-primary">
                已选择步骤 ({{ addStepList?.length || 0 }})
              </h3>
              <el-button
                class="ml-auto"
                type="info"
                plain
                round
                @click="clearStep"
                >清空
              </el-button>
            </div>
          </el-header>
          <el-main>
            <el-scrollbar class="h-full" ref="stepScrollRef">
              <el-empty
                v-if="!addStepList?.length"
                description="尚未添加任何步骤"
              />
              <!-- 单列拖拽 -->
              <draggable
                v-else
                :list="addStepList"
                item-key="step_id"
                force-fallback="true"
                animation="300"
                handle=".stepHandle"
              >
                {{ addStepList }}
                <template #item="{ element, index }">
                  <div
                    class="p-1 cursor-pointer select-none"
                    style="height: 76px"
                  >
                    <div
                      class="h-full border border-gray-200 shadow-sm rounded-md flex justify-start items-center"
                    >
                      <!-- 拖拽图标 -->
                      <div
                        class="h-full w-10 flex justify-center items-center stepHandle cursor-move"
                      >
                        <el-icon size="22">
                          <DragIcon />
                        </el-icon>
                      </div>
                      <!-- 序号 -->
                      <div
                        class="ml-2 w-8 h-8 rounded-full flex justify-center items-center bg-gray-100"
                      >
                        <span class="text-gray-400 font-bold">
                          {{ index + 1 }}
                        </span>
                      </div>
                      <!-- 步骤名称 -->
                      <div
                        class="ml-3 flex-1 h-full flex items-start flex-col justify-center overflow-hidden"
                        style="height: 60%"
                      >
                        <span
                          class="text-gray-800 dark:text-white text-base max-w-full whitespace-nowrap overflow-hidden overflow-ellipsis"
                        >
                          {{ element.name || "未命名步骤" }}
                        </span>
                      </div>
                      <!-- 请求和响应 -->
                      <div
                        class="ml-3 flex-1 h-full flex flex-col justify-center overflow-hidden"
                      >
                        <div class="mt-1 flex justify-start items-center">
                          <span class="text-gray-400/80 text-xs">
                            请求:
                            <i
                              :class="{
                                'text-red-500 font-bold': !element.send
                              }"
                              >{{ element.send.length || 0 }} 个 ➡️【{{
                                element.send.join(", ")
                              }}】</i
                            >
                          </span>
                        </div>
                        <div class="mt-1 flex justify-start items-center">
                          <span class="text-gray-400/80 text-xs">
                            响应:
                            <i
                              :class="{
                                'text-red-500 font-bold': !element.recv
                              }"
                              >{{ element.recv.length || 0 }} 个 ➡️【{{
                                element.recv.join(", ")
                              }}】</i
                            >
                          </span>
                        </div>
                      </div>
                      <!-- 操作 -->
                      <div class="h-full ml-auto flex items-center mr-3">
                        <!-- 拷贝按钮 -->
                        <el-button
                          :title="`拷贝步骤 (ID: ${element.step_id})`"
                          :icon="CopyDocument"
                          type="primary"
                          circle
                          plain
                          @click.stop="copyStep(element)"
                        />
                        <!-- 删除按钮 -->
                        <el-button
                          title="删除步骤"
                          :icon="Delete"
                          circle
                          plain
                          type="danger"
                          @click.stop="deleteStep(element)"
                        />
                        <!-- 删除按钮(带二次确认) -->
                        <!-- <el-popconfirm
                          title="是否确认删除?"
                          @confirm="deleteStep(index)"
                        >
                          <template #reference>
                            <el-button
                              title="删除步骤"
                              :icon="Delete"
                              circle
                              plain
                              type="danger"
                              @click.stop
                            />
                          </template>
                        </el-popconfirm> -->
                      </div>
                    </div>
                  </div>
                </template>
              </draggable>
              <!-- 操作按钮 -->
              <div class="p-2" />
            </el-scrollbar>
          </el-main>
        </el-container>
      </div>
    </el-container>
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
