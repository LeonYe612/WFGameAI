<script setup lang="ts">
import { ref, computed, watch, nextTick } from "vue";
import { ElMessage } from "element-plus";
import type { ScriptResult } from "@/api/reports";
import type { FlatStep } from "../utils/types";
import { formatDuration, formatDurationFromTimestamps } from "@/utils/format";
import {
  SuccessFilled,
  CircleCloseFilled,
  WarningFilled,
  List
} from "@element-plus/icons-vue";

interface Props {
  scriptResults: ScriptResult[];
  flatSteps: FlatStep[];
  selectedIndex: number;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: "update:selectedIndex", index: number): void;
  (e: "jumpToError"): void;
}>();

defineOptions({
  name: "ScriptStepsTable"
});

const tableRef = ref();
const expandedRowKeys = ref<any[]>([]);
const statusFilter = ref<string>("");
const currentErrorIndex = ref<number>(0);
const isInternalClick = ref<boolean>(false); // 标记是否为内部点击

// 初始化展开所有行
const initExpandedRows = () => {
  expandedRowKeys.value = props.scriptResults.map((_, index) => index);
};

// 表格数据 - 脚本列表
interface ScriptRow {
  id: number;
  scriptIndex: number;
  scriptName: string;
  loopCount: number;
  loopIndex: number;
  duration: number;
  totalSteps: number;
  successSteps: number;
  failedSteps: number;
  skippedSteps: number;
  scriptResult: ScriptResult;
  startGlobalIndex: number;
}

const scriptRows = computed<ScriptRow[]>(() => {
  let globalIndex = 1;
  let scriptResults = props.scriptResults || [];
  if (!Array.isArray(scriptResults)) {
    scriptResults = [];
  }
  return scriptResults.map((result, index) => {
    const startIndex = globalIndex;
    const row: ScriptRow = {
      id: index,
      scriptIndex: index,
      scriptName: result.meta.name || `脚本 ${index + 1}`,
      loopCount: result.meta["loop-count"] || 0,
      loopIndex: result.meta["loop-index"] || 0,
      duration: result.summary.duration || 0,
      totalSteps: result.summary.total || 0,
      successSteps: result.summary.success || 0,
      failedSteps: result.summary.failed || 0,
      skippedSteps: result.summary.skipped || 0,
      scriptResult: result,
      startGlobalIndex: startIndex
    };
    globalIndex += result.steps.length;
    return row;
  });
});

// 获取脚本的步骤列表
const getScriptSteps = (scriptIndex: number) => {
  return props.flatSteps.filter(item => item.scriptIndex === scriptIndex);
};

// 处理步骤点击
const handleStepClick = (flatStep: FlatStep) => {
  isInternalClick.value = true; // 标记为内部点击
  emit("update:selectedIndex", flatStep.globalIndex - 1);
  // 使用 nextTick 确保在下一个事件循环中重置标记
  nextTick(() => {
    isInternalClick.value = false;
  });
};

const currentRowKey = computed<number | null>(() => {
  const selectedStep = props.flatSteps[props.selectedIndex];
  return selectedStep ? selectedStep.globalIndex : null;
});

// 跳转到错误步骤
const handleJumpToError = () => {
  const errorSteps = props.flatSteps.filter(
    item => item.step.result?.status === "failed"
  );

  if (errorSteps.length === 0) {
    ElMessage.info("没有错误步骤");
    return;
  }

  const targetStep = errorSteps[currentErrorIndex.value % errorSteps.length];

  if (!expandedRowKeys.value.includes(targetStep.scriptIndex)) {
    expandedRowKeys.value.push(targetStep.scriptIndex);
  }

  emit("update:selectedIndex", targetStep.globalIndex - 1);

  currentErrorIndex.value = (currentErrorIndex.value + 1) % errorSteps.length;

  // ElMessage.success(
  //   `已定位到第 ${currentErrorIndex.value || errorSteps.length} 个错误步骤`
  // );
};

// 滚动到指定步骤
const scrollToStep = async (stepIndex: number) => {
  await nextTick();

  // 查找包含目标步骤的 DOM 元素
  const stepElements = document.querySelectorAll(".step-row");
  let targetElement: Element | null = null;

  // 遍历所有步骤行，找到对应的全局索引
  for (const element of Array.from(stepElements)) {
    const stepIndexText = element.querySelector(".step-index")?.textContent;
    if (stepIndexText && stepIndexText.includes(`#${stepIndex + 1}`)) {
      targetElement = element;
      break;
    }
  }

  if (targetElement) {
    // 滚动到目标元素
    targetElement.scrollIntoView({
      behavior: "smooth",
      inline: "nearest"
    });

    // 添加高亮效果
    targetElement.classList.add("step-row-highlight");
    setTimeout(() => {
      targetElement?.classList.remove("step-row-highlight");
    }, 2000);
  }
};

// 监听选中索引变化
watch(
  () => props.selectedIndex,
  async newIndex => {
    // 如果是内部点击触发的，跳过自动滚动
    if (isInternalClick.value) {
      return;
    }

    const selectedStep = props.flatSteps[newIndex];
    if (selectedStep) {
      // 确保对应的脚本行被展开
      if (!expandedRowKeys.value.includes(selectedStep.scriptIndex)) {
        expandedRowKeys.value.push(selectedStep.scriptIndex);
      }

      // 等待DOM更新后滚动到目标步骤
      await nextTick();
      await nextTick(); // 多等一帧，确保展开动画完成
      scrollToStep(newIndex);
    }
  }
);

// 过滤步骤
const filterSteps = (steps: FlatStep[]) => {
  if (!statusFilter.value) return steps;
  return steps.filter(item => item.step.result?.status === statusFilter.value);
};

// 行类名
const _tableRowClassName = ({ row }: { row: ScriptRow }) => {
  if (row.failedSteps > 0) return "row-error";
  if (row.successSteps === row.totalSteps) return "row-success";
  return "";
};

// 步骤行类名
const stepRowClassName = (flatStep: FlatStep) => {
  const isSelected = flatStep.globalIndex - 1 === props.selectedIndex;
  const status = flatStep.step.result?.status;

  let className = "step-row";
  if (isSelected) className += " step-row-selected";
  if (status === "failed") className += " step-row-error";
  else if (status === "success") className += " step-row-success";

  return className;
};

// 处理行点击事件，切换展开状态
const handleRowClick = (row: ScriptRow) => {
  const index = expandedRowKeys.value.indexOf(row.scriptIndex);
  if (index > -1) {
    expandedRowKeys.value.splice(index, 1);
  } else {
    expandedRowKeys.value.push(row.scriptIndex);
  }
};

// 初始化时展开所有行
watch(
  () => props.scriptResults,
  () => {
    if (props.scriptResults.length > 0 && expandedRowKeys.value.length === 0) {
      initExpandedRows();
    }
  },
  { immediate: true }
);
</script>

<template>
  <el-card shadow="never" class="script-steps-card">
    <template #header>
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <el-icon :size="20" color="#409eff">
            <List />
          </el-icon>
          <span class="text-lg font-semibold">步骤列表</span>
        </div>
        <div class="flex items-center gap-2">
          <el-select
            v-model="statusFilter"
            placeholder="状态筛选"
            clearable
            size="small"
            style="width: 120px"
          >
            <el-option label="成功" value="success" />
            <el-option label="失败" value="failed" />
            <el-option label="跳过" value="skipped" />
          </el-select>
          <el-button
            type="danger"
            size="small"
            @click="handleJumpToError"
            plain
          >
            跳至错误步骤
          </el-button>
        </div>
      </div>
    </template>
    <div class="table-wrapper">
      <el-table
        height="100%"
        ref="tableRef"
        :data="scriptRows"
        row-key="id"
        :expand-row-keys="expandedRowKeys"
        :stripe="false"
        @row-click="handleRowClick"
      >
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="steps-container">
              <el-table
                :data="filterSteps(getScriptSteps(row.scriptIndex))"
                :row-class-name="({ row }) => stepRowClassName(row)"
                @row-click="handleStepClick"
                highlight-current-row
                :current-row-key="currentRowKey"
                row-key="globalIndex"
              >
                <el-table-column
                  label="状态"
                  width="80"
                  align="center"
                  :filters="[
                    { text: '成功', value: 'success' },
                    { text: '失败', value: 'failed' },
                    { text: '跳过', value: 'skipped' }
                  ]"
                  :filter-method="
                    (value, row) => row.step.result?.status === value
                  "
                >
                  <template #default="{ row }">
                    <div class="status-icon">
                      <el-icon
                        v-if="row.step.result?.status === 'success'"
                        class="status-success"
                        :size="20"
                      >
                        <SuccessFilled />
                      </el-icon>
                      <el-icon
                        v-else-if="row.step.result?.status === 'failed'"
                        class="status-failed"
                        :size="20"
                      >
                        <CircleCloseFilled />
                      </el-icon>
                      <el-icon
                        v-else-if="row.step.result?.status === 'skipped'"
                        class="status-skipped"
                        :size="20"
                      >
                        <WarningFilled />
                      </el-icon>
                      <span v-else class="status-none">-</span>
                    </div>
                  </template>
                </el-table-column>

                <el-table-column label="序号" width="80" align="center">
                  <template #default="{ row }">
                    <span class="step-index">#{{ row.globalIndex }}</span>
                  </template>
                </el-table-column>

                <el-table-column label="名称" min-width="200">
                  <template #default="{ row }">
                    <span class="step-remark">{{
                      row.step.remark || "-"
                    }}</span>
                  </template>
                </el-table-column>

                <el-table-column label="操作" min-width="150">
                  <template #default="{ row }">
                    <span class="step-action">{{
                      row.step.action || "-"
                    }}</span>
                  </template>
                </el-table-column>

                <el-table-column
                  label="耗时"
                  width="100"
                  align="center"
                  sortable
                >
                  <template #default="{ row }">
                    <span class="step-duration">{{
                      formatDurationFromTimestamps(
                        row.step.result?.start_time,
                        row.step.result?.end_time
                      )
                    }}</span>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="脚本名称" prop="scriptName" min-width="200" />

        <el-table-column label="循环" width="100" align="center">
          <template #default="{ row }">
            {{ row.loopIndex }} / {{ row.loopCount }}
          </template>
        </el-table-column>

        <el-table-column label="步骤数" width="100" align="center">
          <template #default="{ row }">
            {{ row.totalSteps }}
          </template>
        </el-table-column>

        <el-table-column label="成功" width="80" align="center">
          <template #default="{ row }">
            <span class="text-green-600">{{ row.successSteps }}</span>
          </template>
        </el-table-column>

        <el-table-column label="失败" width="80" align="center">
          <template #default="{ row }">
            <span class="text-red-600">{{ row.failedSteps }}</span>
          </template>
        </el-table-column>

        <el-table-column label="跳过" width="80" align="center">
          <template #default="{ row }">
            <span class="text-gray-500">{{ row.skippedSteps }}</span>
          </template>
        </el-table-column>

        <el-table-column
          label="耗时"
          width="120"
          align="center"
          sortable
          :sort-method="(a, b) => a.duration - b.duration"
        >
          <template #default="{ row }">
            {{ formatDuration(row.duration * 1000) }}
          </template>
        </el-table-column>
      </el-table>
    </div>
  </el-card>
</template>

<style scoped lang="scss">
.script-steps-card {
  display: flex;
  flex-direction: column;
  height: 100%;

  :deep(.el-card__body) {
    padding: 0;
    display: flex;
    flex: 1;
    min-height: 0;

    .table-wrapper {
      flex: 1;
      overflow: auto;
      min-width: 0; // 防止flex子元素溢出
    }
  }
}

.steps-container {
  padding: 0 40px;
  :deep(.el-table) {
    .step-row {
      cursor: pointer;
    }

    // .step-row-selected {
    //   background-color: #89c4ff !important;
    //   color: #ffffff;
    // }

    // // 步骤表格行 hover 样式 - 仅加粗字体，不改变背景色
    // &.el-table--enable-row-hover .el-table__body tr:hover > td {
    //   background-color: inherit !important;
    // }

    // // 确保选中状态的优先级更高
    // &.el-table--enable-row-hover
    //   .el-table__body
    //   tr.step-row-selected:hover
    //   > td {
    //   background-color: #6db6ff !important;
    //   color: #ffffff;
    // }
  }

  // 状态图标样式
  .status-icon {
    display: flex;
    align-items: center;
    justify-content: center;

    .status-success {
      color: #67c23a;
    }

    .status-failed {
      color: #f56c6c;
    }

    .status-skipped {
      color: #e6a23c;
    }

    .status-none {
      color: #909399;
      font-size: 14px;
    }
  }

  // 文本层次样式
  .step-index {
    font-weight: 600;
    font-size: 14px;
  }

  .step-action {
    font-weight: 500;
    font-size: 14px;
  }

  .step-remark {
    font-size: 13px;
  }

  .step-duration {
    font-family: "Consolas", "Monaco", monospace;
    font-size: 13px;
  }
}
</style>
