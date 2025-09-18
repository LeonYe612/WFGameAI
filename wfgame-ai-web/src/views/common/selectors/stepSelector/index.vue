<!-- 此组件弹出用例列表用于选择用例 -->
<script lang="ts" setup>
import { message } from "@/utils/message";
import { ref, computed, nextTick, watch } from "vue";
import { listCase, listStep } from "@/api/testcase";
import { superRequest } from "@/utils/request";
import ComponentPager from "@/components/RePager/index.vue";
import TestcaseQuery from "./query.vue";
import CatalogTreeTableSelector from "@/views/testcase/list/components/catalogSelector.vue";
import { Delete, CopyDocument } from "@element-plus/icons-vue";
import draggable from "vuedraggable";
import DragIcon from "@/assets/svg/drag.svg?component";
import { v4 as uuidv4 } from "uuid";

defineOptions({
  name: "StepSelector"
});

const emit = defineEmits(["complete"]);
const dialogVisible = ref(false);
const title = ref(`🤡 请选择要导入的用例步骤：`);
const queryForm = {
  page: 1,
  size: 20,
  keyword: "",
  env: null,
  catalog_id: null
};
const queryFormRef = ref(queryForm);
const testcaseTable = ref(null);
const currentRow = ref(null);
const stepTable = ref(null);
const catalogSelectorRef = ref();
const caseQueryRef = ref();
const loading = ref(false);
const stepLoading = ref(false);
const dataList = ref([]);
const dataTotal = ref(0);
const stepList = ref([]);
const stepTotal = ref(0);

const recordCurrentChange = (row: any) => {
  currentRow.value = row;
};

const fetchData = async () => {
  superRequest({
    apiFunc: listCase,
    apiParams: queryForm,
    onBeforeRequest: () => {
      loading.value = true;
    },
    onSucceed: data => {
      data.list.forEach(item => {
        item.selectedVersion = item.version;
      });
      dataList.value = data.list;
      dataTotal.value = data.total;
    },
    onCompleted: () => {
      loading.value = false;
    }
  });
};

watch(
  () => currentRow.value,
  (curr, old) => {
    if (curr !== old) {
      fetchStepData();
    }
  }
);

const fetchStepData = async () => {
  if (!currentRow.value?.id) return;
  superRequest({
    apiFunc: listStep,
    apiParams: {
      case_base_id: currentRow.value.id,
      version: currentRow.value.version
    },
    onBeforeRequest: () => {
      stepLoading.value = true;
    },
    onSucceed: data => {
      stepList.value = data.list || [];
      stepTotal.value = data.total || 0;
    },
    onCompleted: () => {
      stepLoading.value = false;
    }
  });
};

const getVersionOptions = computed(() => {
  return version => {
    const versionOptions = [];
    for (let i = 1; i <= version; i++) {
      versionOptions.push({
        label: `第 ${i} 版`,
        value: i
      });
    }
    return versionOptions;
  };
});

const onSelectorChanged = catalog => {
  queryFormRef.value.catalog_id = catalog?.id;
  stepList.value = [];
  stepTotal.value = 0;
  fetchData();
};

const show = (env: number, clear = true) => {
  dialogVisible.value = true;
  if (clear) {
    clearStep();
  }
  queryFormRef.value.env = env;
  nextTick(() => {
    catalogSelectorRef.value?.fetchDataWithMemoryCurrent();
  });
};

const cancel = () => {
  dialogVisible.value = false;
};

const onQueryReset = () => {
  testcaseTable.value?.clearSelection();
};

// ==================== 待添加步骤列表 =======================
const addStepList = ref([]);
const stepScrollRef = ref(null);

// 获取选中的行
const selectionRows = computed(() => {
  return stepTable.value?.getSelectionRows();
});

const clearSelection = () => {
  stepTable.value?.clearSelection();
};

// 获取选中行的总行数
const selectionRowsCount = computed(() => {
  return stepTable.value?.getSelectionRows().length || 0;
});

const scrollToBottom = () => {
  // 滚动到最底部
  nextTick(() => {
    stepScrollRef.value.setScrollTop((addStepList.value.length || 0) * 100);
  });
};

const batchAddSteps = () => {
  if (!selectionRowsCount.value) {
    message("尚未选择任何用例步骤", { type: "error" });
    return;
  }
  selectionRows.value.forEach(row => {
    addStep(row);
  });
  clearSelection();
};

const addStep = (row: any) => {
  const newStep = JSON.parse(JSON.stringify(row));
  newStep.uuid = uuidv4();
  addStepList.value.push(newStep);
  scrollToBottom();
};

const copyStep = (row: any) => {
  addStep(row);
};

const deleteStep = (row: any) => {
  const index = addStepList.value.findIndex(item => item.uuid === row.uuid);
  addStepList.value.splice(index, 1);
};

const clearStep = () => {
  addStepList.value = [];
};

const confirm = () => {
  if (!addStepList.value?.length) {
    message("尚未选择任何用例步骤", { type: "error" });
    return;
  }
  dialogVisible.value = false;
  emit("complete", addStepList.value);
};

defineExpose({ show });
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    :title="title"
    width="90vw"
    :draggable="true"
    align-center
  >
    <el-container class="main-content cursor-pointer" style="height: 65vh">
      <el-aside width="20%" class="p-5 pr-0">
        <el-card
          class="h-full flex flex-col"
          body-class="flex-1 overflow-hidden"
          shadow="never"
        >
          <template #header>
            <h3 class="text-info text-center">用例目录</h3>
          </template>
          <CatalogTreeTableSelector
            class="h-full"
            ref="catalogSelectorRef"
            @changed="onSelectorChanged"
          />
        </el-card>
      </el-aside>
      <el-main class="pl-0 h-full">
        <div class="h-full flex justify-between">
          <!-- A. 用例列表 -->
          <div class="w-[38%] h-full border border-gray-300 rounded">
            <el-container class="h-full">
              <el-header>
                <!-- 查询条件 -->
                <TestcaseQuery
                  :query-form="queryForm"
                  @fetch-data="fetchData"
                  @reset="onQueryReset"
                  ref="caseQueryRef"
                />
              </el-header>
              <el-main>
                <!-- 表格 -->
                <el-table
                  ref="testcaseTable"
                  v-loading="loading"
                  :data="dataList"
                  row-key="id"
                  height="100%"
                  stripe
                  fit
                  :cell-style="{ textAlign: 'left' }"
                  :header-cell-style="{
                    textAlign: 'left',
                    fontWeight: 'bolder'
                  }"
                  highlight-current-row
                  @current-change="recordCurrentChange"
                >
                  <el-table-column label="ID" prop="id" width="80" />
                  <el-table-column label="名称" prop="name" />
                  <el-table-column label="版本" prop="version" width="150">
                    <template #default="{ row }">
                      <el-select
                        size="large"
                        v-model="row.selectedVersion"
                        placeholder="版本选择"
                        style="width: 110px; text-align: center"
                      >
                        <el-option
                          v-for="item in getVersionOptions(row.version)"
                          :key="item.value"
                          :label="item.label"
                          :value="item.value"
                        />
                      </el-select>
                    </template>
                  </el-table-column>
                </el-table>
              </el-main>
              <el-footer>
                <!-- 分页组件 -->
                <ComponentPager
                  layout="total, sizes, prev, next, jumper"
                  :query-form="queryForm"
                  :total="dataTotal"
                  @fetch-data="fetchData"
                />
              </el-footer>
            </el-container>
          </div>
          <!-- B. 步骤列表 -->
          <div class="w-[30%] h-full border border-gray-300 rounded">
            <el-container class="h-full">
              <el-header>
                <div class="h-full flex justify-between items-center">
                  <h3 class="text-info text-center">用例步骤</h3>
                  <el-button
                    :type="selectionRowsCount > 0 ? 'success' : 'info'"
                    plain
                    @click="batchAddSteps"
                  >
                    添加已选({{ selectionRowsCount }})
                  </el-button>
                </div>
              </el-header>
              <el-main>
                <!-- 表格 -->
                <el-table
                  ref="stepTable"
                  v-loading="stepLoading"
                  :data="stepList"
                  row-key="id"
                  height="100%"
                  empty-text="请先选择测试用例"
                  stripe
                  fit
                  :cell-style="{ textAlign: 'left' }"
                  :header-cell-style="{
                    textAlign: 'left',
                    fontWeight: 'bolder'
                  }"
                  @row-click="stepTable?.toggleRowSelection"
                >
                  <el-table-column
                    type="selection"
                    reserve-selection
                    align="center"
                  />
                  <el-table-column label="序号" type="index" width="80" />
                  <el-table-column label="步骤名称">
                    <template #default="{ row }">
                      <div class="text-base font-medium">{{ row.name }}</div>
                      <div class="text-xs text-gray-400 mt-[2px]">
                        {{
                          `请求数量: ${row.send_total} | 响应数量: ${row.recv_total}`
                        }}
                      </div>
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" v-if="false" width="90">
                    <template #default="{ row }">
                      <el-button
                        type="success"
                        plain
                        round
                        @click="addStep(row)"
                        >添加</el-button
                      >
                    </template>
                  </el-table-column>
                </el-table>
              </el-main>
            </el-container>
          </div>
          <!-- C. 步骤编辑器 -->
          <div class="w-[30%] h-full border border-gray-300 rounded">
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
                    >清空</el-button
                  >
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
                    item-key="uuid"
                    force-fallback="true"
                    animation="300"
                    handle=".stepHandle"
                  >
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
                          >
                            <span
                              class="text-gray-600 dark:text-white text-base max-w-full whitespace-nowrap overflow-hidden overflow-ellipsis"
                            >
                              {{ element.name || "未命名步骤" }}
                            </span>
                            <div class="mt-1 flex justify-start items-center">
                              <span class="text-gray-400/80 text-xs">
                                请求:
                                <i
                                  :class="{
                                    'text-red-500 font-bold':
                                      !element.send_total
                                  }"
                                  >{{ element.send_total || 0 }}</i
                                >
                                个 | 响应:
                                <i
                                  :class="{
                                    'text-red-500 font-bold':
                                      !element.recv_total
                                  }"
                                  >{{ element.recv_total || 0 }}</i
                                >
                                个
                              </span>
                            </div>
                          </div>
                          <!-- 操作 -->
                          <div class="h-full ml-auto flex items-center mr-3">
                            <!-- 拷贝按钮 -->
                            <el-button
                              :title="`拷贝步骤 (ID: ${element.id})`"
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
        </div>
      </el-main>
    </el-container>

    <template #footer>
      <el-button @click="cancel" size="large">取 消</el-button>
      <el-button type="primary" @click="confirm" size="large"> 确定 </el-button>
    </template>
  </el-dialog>
</template>

<style>
.el-table__body tr.current-row > td {
  background: rgb(184, 227, 255) !important;
  color: #409eff;
}
</style>
