<script setup lang="ts">
import {
  DataLine,
  View,
  Delete,
  Search,
  CloseBold
} from "@element-plus/icons-vue";
import ComponentPager from "@/components/RePager/index.vue";
import { useTeamGlobalState } from "@/views/team/mine/utils/teamStoreStateHook";
import { usePlanListTable } from "@/views/plan/list/utils/planListTablehook";
import ComputerIcon from "@/assets/svg/computer.svg?component";
import {
  Refresh,
  CirclePlusFilled,
  DocumentCopy,
  ChromeFilled
} from "@element-plus/icons-vue";
import { TimeDefault } from "@/utils/time";
import {
  planTypeEnum,
  planStatusEnum,
  getLabel,
  planRunTypeEnum,
  planEnableEnum,
  sortedEnum
} from "@/utils/enums";
import ActiveTeamInfo from "@/views/common/display/activeTeamInfo.vue";
import { ref, computed, nextTick, watch, onMounted } from "vue";
import RewardReturnDialog from "@/views/report/detail/components/rewardReturnDialog.vue";
import PlanConfirmer from "@/views/testcase/components/planConfirmer.vue";
import ApiMan from "@/components/ApiMan.vue";

defineOptions({
  name: "PlanListTable"
});

const props = defineProps({
  writable: {
    type: Boolean,
    default: false
  },
  disableStatusToggle: {
    type: Boolean,
    default: false
  }
});

const tableRef = ref();
// 查询条件
const queryForm = {
  page: 1,
  size: 20,
  keyword: "",
  disabled: null,
  plan_type: null,
  run_type: null
};

const query = ref(queryForm);

const {
  dataList,
  dataTotal,
  loading,
  delLoadings,
  rewardDialogRef,
  showPlanConfirmer,
  workerLabel,
  showApiMan,
  apiUrl,
  apiMethod,
  apiJson,
  autoRefresh,
  getRunTypeTag,
  fetchData,
  fetchWorkerNames,
  handleCreate,
  handleReplay,
  handleReport,
  handleRewardReport,
  handleEdit,
  handleEnable,
  handleDelete,
  handleStop,
  handleRestart,
  handleMock
} = usePlanListTable({
  queryForm,
  tableRef,
  //过滤计划执行状态：待执行
  run_filter: props.disableStatusToggle
});

const planStatusType = computed(() => {
  return value => {
    if (value === planStatusEnum.PENDING.value) {
      return "warning";
    } else if (value === planStatusEnum.RUNNING.value) {
      return "";
    } else if (value === planStatusEnum.ENDING.value) {
      return "success";
    } else if (value === planStatusEnum.IMPLEMENT_FAIL.value) {
      return "error";
    }
  };
});

const onQueryChanged = (value: any, key: string) => {
  query.value[key] = value;
  fetchData();
};

const columnWidth = ref(0);

// 优化按钮宽度自适应
const calculateButtonCount = () => {
  nextTick(() => {
    const buttonContainers = tableRef.value?.$el?.querySelectorAll(
      ".el-table__body-wrapper .el-table__row .w-full.flex.justify-start.items-center.pr-4"
    );
    if (buttonContainers && buttonContainers.length > 0) {
      let maxButtonCount = 0;
      buttonContainers.forEach(container => {
        let visibleButtonCount = 0;
        const buttons = container.querySelectorAll("button, .el-popconfirm");
        buttons.forEach(button => {
          if (getComputedStyle(button).display !== "none") {
            visibleButtonCount++;
          }
        });
        if (visibleButtonCount > maxButtonCount) {
          maxButtonCount = visibleButtonCount;
        }
      });
      columnWidth.value = maxButtonCount * 50;
    }
  });
};

watch(dataList, () => {
  calculateButtonCount();
});

const { initWatchTeamId } = useTeamGlobalState();
initWatchTeamId(fetchData, true, fetchWorkerNames);
</script>

<template>
  <el-card class="h-full plan-card" shadow="never">
    <!-- Card-Header -->
    <template #header>
      <ActiveTeamInfo title="待测计划">
        <el-row class="items-center justify-between">
          <div class="h-full flex items-center" />
          <div class="flex items-center">
            <!-- 查询条件：是否启用 -->
            <div v-if="!props.disableStatusToggle">
              <span class="text-gray-500">启用状态：</span>
              <el-radio-group
                v-model="query.disabled"
                size="large"
                @change="onQueryChanged($event, 'disabled')"
              >
                <el-radio
                  v-for="item in sortedEnum(planEnableEnum)"
                  :key="item.value"
                  :label="item.value"
                  border
                  style="margin-right: 6px"
                >
                  {{ item.label }}
                </el-radio>
              </el-radio-group>
            </div>
            <el-divider direction="vertical" />
            <div>
              <span v-if="false" class="text-gray-500">计划类型：</span>
              <el-select
                v-model="query.plan_type"
                @change="fetchData"
                clearable
                placeholder="请选择计划类型"
                size="large"
              >
                <el-option
                  v-for="(item, key) in sortedEnum(planTypeEnum, [
                    planTypeEnum.DEBUG
                  ])"
                  :key="key"
                  :label="`${item.label}类型`"
                  :value="item.value"
                />
              </el-select>
            </div>
            <el-divider direction="vertical" />
            <div>
              <span v-if="false" class="text-gray-500">运行类型：</span>
              <el-select
                v-model="query.run_type"
                @change="fetchData"
                clearable
                placeholder="请选择运行类型"
                size="large"
              >
                <el-option
                  v-for="(item, key) in sortedEnum(planRunTypeEnum, [])"
                  :key="key"
                  :label="`${item.label}`"
                  :value="item.value"
                />
              </el-select>
            </div>
            <el-divider direction="vertical" />
            <div class="w-72 mr-2">
              <el-input
                v-model="query.keyword"
                size="large"
                placeholder="请输入关键字搜索"
                :prefix-icon="Search"
                clearable
                @change="onQueryChanged($event, 'keyword')"
              />
            </div>
            <div class="flex items-center">
              <el-button
                v-if="false"
                :icon="Refresh"
                size="large"
                style="width: 120px"
                @click="fetchData"
              >
                刷新
              </el-button>
              <el-switch
                v-model="autoRefresh"
                active-text="自动刷新"
                class="ml-2"
                style="margin-right: 10px"
                @change="fetchData"
              />
              <el-divider direction="vertical" />
              <!-- 新建计划按钮 -->
              <el-button
                v-if="props.writable"
                :icon="CirclePlusFilled"
                size="large"
                type="primary"
                style="width: 120px"
                @click="handleCreate"
              >
                新建计划
              </el-button>
            </div>
          </div>
        </el-row>
      </ActiveTeamInfo>
    </template>
    <!-- Card-Body -->
    <!-- 表格 -->
    <el-table
      ref="tableRef"
      :data="dataList"
      row-key="id"
      height="calc(100% - 2.5rem)"
      max-height="calc(100% - 2.5rem)"
      stripe
      fit
      :header-cell-style="{
        fontWeight: 'bolder'
      }"
    >
      <el-table-column v-if="false" type="selection" reserve-selection />
      <el-table-column label="ID" prop="id" width="80" />
      <el-table-column label="运行状态" width="150">
        <template #default="{ row }">
          <div class="flex justify-start items-center">
            <el-tag
              :type="planStatusType(row.run_status)"
              effect="dark"
              style="padding: 12px 5px; position: relative"
              round
              class="plan-status-tag"
            >
              <span class="text-sm px-2 py-4 flex items-center">
                <span
                  v-if="row.run_status === planStatusEnum.RUNNING.value"
                  class="dot-animated mr-1"
                />
                {{ getLabel(planStatusEnum, row.run_status) }}
              </span>
            </el-tag>
            <el-switch
              v-if="
                [
                  planRunTypeEnum.CIRCLE.value,
                  planRunTypeEnum.WEBHOOK.value
                ].includes(row.run_type)
              "
              class="ml-2"
              :disabled="!props.writable"
              v-model="row.disabled"
              :active-value="planEnableEnum.ENABLE.value"
              :inactive-value="planEnableEnum.DISABLE.value"
              @change="handleEnable($event, row)"
            />
          </div>
        </template>
      </el-table-column>
      <el-table-column label="执行器" prop="run_type" width="160">
        <template #default="{ row }">
          <div class="flex justify-start items-center">
            <el-icon size="22">
              <ComputerIcon />
            </el-icon>
            <div class="flex flex-col items-start pl-2">
              <span class="font-semibold text-[#4A7FA2]">
                {{ row.worker_queue }}
              </span>
              <span class="text-sm font-medium text-[#78CEAA]">
                {{ workerLabel(row.worker_queue) }}
              </span>
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column
        label="名称"
        prop="name"
        show-overflow-tooltip
        align="left"
        width="600"
      />
      <el-table-column label="执行类型" prop="run_type" width="180">
        <template #default="{ row }">
          <el-tag
            :type="getRunTypeTag(row)"
            size="large"
            effect="light"
            class="w-[100px]"
          >
            {{ getLabel(planRunTypeEnum, row.run_type) }}
          </el-tag>
          <el-button
            v-if="row.run_type === planRunTypeEnum.WEBHOOK.value"
            title="模拟请求"
            :icon="ChromeFilled"
            type="primary"
            class="ml-2"
            @click="handleMock(row)"
            plain
            circle
          />
        </template>
      </el-table-column>
      <el-table-column label="用例数" width="120">
        <template #default="{ row }">
          <span class="text-base"> {{ row.case_queue?.length || 0 }}</span>
        </template>
      </el-table-column>
      <el-table-column label="运行次数" width="120">
        <template #default="{ row }">
          <span class="text-base"> {{ row.run_times || 0 }}</span>
        </template>
      </el-table-column>
      <!-- <el-table-column label="成功率" width="80">
        <template #default="{ row }">
          <span class="text-base"> {{ row.rate || "80%" }}</span>
        </template>
      </el-table-column> -->
      <el-table-column label="创建者" prop="created_name" width="160" />
      <el-table-column label="创建时间" width="180" prop="created_at">
        <template #default="{ row }">
          <span class="text-base">{{
            TimeDefault(row.created_at, "YYYY-MM-DD HH:mm:ss")
          }}</span>
        </template>
      </el-table-column>
      <el-table-column
        fixed="right"
        label="操作"
        :min-width="240"
        :width="columnWidth"
      >
        <template #default="{ row }">
          <div
            class="w-full flex justify-start items-center pr-4"
            ref="buttonContainer"
          >
            <el-button
              :disabled="!props.writable"
              @click="handleReplay(row)"
              title="复用参数，再次投递"
              :icon="DocumentCopy"
              type="info"
              plain
              circle
            />
            <el-button
              :disabled="row.run_status !== planStatusEnum.ENDING.value"
              title="查看报告"
              :icon="DataLine"
              type="success"
              plain
              circle
              @click="handleReport(row)"
            />
            <el-button
              title="查看计划"
              :icon="View"
              type="primary"
              plain
              circle
              @click="handleEdit(row)"
            />
            <el-popconfirm
              v-if="props.writable"
              title="是否确认终止?"
              @confirm="handleStop(row)"
            >
              <template #reference>
                <el-button
                  :disabled="row.run_status === planStatusEnum.ENDING.value"
                  title="终止计划"
                  :loading="delLoadings[row.id]"
                  :icon="CloseBold"
                  type="warning"
                  plain
                  circle
                />
              </template>
            </el-popconfirm>
            <el-popconfirm
              title="是否重新运行计划?"
              v-if="props.writable"
              @confirm="handleRestart(row)"
            >
              <template #reference>
                <el-button
                  title="重置计划"
                  :loading="delLoadings[row.id]"
                  :icon="Refresh"
                  type="warning"
                  plain
                  circle
                />
              </template>
            </el-popconfirm>
            <el-popconfirm
              title="是否确认删除?"
              v-if="props.writable"
              @confirm="handleDelete(row)"
            >
              <template #reference>
                <el-button
                  title="删除计划"
                  :loading="delLoadings[row.id]"
                  :icon="Delete"
                  type="danger"
                  plain
                  circle
                />
              </template>
            </el-popconfirm>
            <el-button
              v-if="row.plan_type === planTypeEnum.BET.value"
              :disabled="row.run_status !== planStatusEnum.ENDING.value"
              title="返奖率报告"
              type="warning"
              plain
              circle
              @click="handleRewardReport(row)"
            >
              <IconifyIconOnline
                class="text-2xl text-yellow-400"
                icon="material-symbols:fishfood"
              />
            </el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>
    <!-- 分页组件 -->
    <ComponentPager
      :query-form="queryForm"
      :total="dataTotal"
      @fetch-data="fetchData"
    />
    <!-- 捕鱼报告弹窗 -->
    <RewardReturnDialog ref="rewardDialogRef" />
    <!-- 执行计划确认 -->
    <PlanConfirmer v-model="showPlanConfirmer" :show-collect="false" />
    <!-- API 执行器 -->
    <ApiMan
      v-model="showApiMan"
      title="🚀 Webhook Mocker"
      :url="apiUrl"
      :method="apiMethod"
      :json="apiJson"
    />
  </el-card>
</template>
<style scoped lang="scss">
.plan-card :deep() .el-card__body {
  height: calc(100% - 100px) !important;
}

.plan-card :deep() .el-table__inner-wrapper {
  height: 100% !important;
}

// 动画小圆点
.dot-animated {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background-color: aquamarine;
  margin-right: 2px;
  animation: dot-blink 1s infinite cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes dot-blink {
  0%,
  100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.3;
    transform: scale(1.4);
  }
}
</style>
