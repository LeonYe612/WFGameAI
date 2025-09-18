<script setup lang="ts">
import { Refresh, Delete, Search } from "@element-plus/icons-vue";
import { ref, computed, onMounted, watch, nextTick, withDefaults } from "vue";
import { useTestcaseStore } from "@/store/modules/testcase";
import { usePlanStoreHook } from "@/store/modules/plan";
import PlanInfoForm from "@/views/plan/detail/components/infoForm.vue";
import { message } from "@/utils/message";
import {
  caseTypeEnum,
  planTypeEnum,
  planInformEnum,
  // getLabel,
  collectTypeEnum
} from "@/utils/enums";
import { usePlanConfirmerHook } from "./planConfirmerHook";
import ComponentPager from "@/components/RePager/index.vue";
import { useTeamGlobalState } from "@/views/team/mine/utils/teamStoreStateHook";
import { useNavigate } from "@/views/common/utils/navHook";
const { navigateToReportDetail } = useNavigate();

defineOptions({
  name: "PlanConfirmer"
});

const props = withDefaults(
  defineProps<{
    modelValue: boolean; // 控制弹窗显示隐藏
    showCollect?: boolean; // 是否显示左侧收藏列表
  }>(),
  {
    modelValue: false,
    showCollect: true
  }
);

const emit = defineEmits<{
  (e: "update:modelValue", value: boolean): void;
}>();

const planFormRef = ref();
const testcaseStore = useTestcaseStore();
const planStore = usePlanStoreHook();

const dialogVisible = computed({
  get: () => props.modelValue,
  set: value => {
    emit("update:modelValue", value);
  }
});

watch(
  () => props.modelValue,
  value => {
    if (value) {
      nextTick(() => {
        initPlanForm();
      });
    }
  }
);

// 用例类型与计划类型的映射关系
const typeMap = {
  [caseTypeEnum.COMMON.value]: planTypeEnum.PLAN.value,
  [caseTypeEnum.PRESSURE.value]: planTypeEnum.PRESS.value,
  [caseTypeEnum.ROBOT.value]: planTypeEnum.ROBOT.value,
  [caseTypeEnum.BET.value]: planTypeEnum.BET.value,
  [caseTypeEnum.FIRE.value]: planTypeEnum.FIRE.value,
  [caseTypeEnum.OTHER.value]: planTypeEnum.PLAN.value,
  [caseTypeEnum.LOAD_TEST.value]: planTypeEnum.LOAD_TEST.value
};
// 用例类型与计划通知的映射关系
const informMap = {
  [caseTypeEnum.COMMON.value]: planInformEnum.DISABLE.value,
  [caseTypeEnum.PRESSURE.value]: planInformEnum.ENABLE.value,
  [caseTypeEnum.ROBOT.value]: planInformEnum.ENABLE.value,
  [caseTypeEnum.BET.value]: planTypeEnum.BET.value,
  [caseTypeEnum.FIRE.value]: planTypeEnum.FIRE.value,
  [caseTypeEnum.OTHER.value]: planInformEnum.DISABLE.value,
  [caseTypeEnum.LOAD_TEST.value]: planInformEnum.ENABLE.value
};

/**
 * 打开窗口时候的初始化表单数据
 * 【A. 用户设置：无需记住设置，自动刷新】
 *  自动刷新的情况下，是根据用例信息组织数据
 *
 * 【B. 用户设置：下次打开时记住当前设置】
 * 其他设置不变，但是依旧需要：生成服务器列表、获取规则、生成 case_queue
 */
const initPlanForm = async () => {
  if (!planFormRef.value) {
    message("计划表单组件实例[planFormRef]未找到!", { type: "error" });
    return;
  }
  // 计划设置快照
  const lastPlanInfo = JSON.parse(JSON.stringify(planStore.info));

  // 无论用户如何设置：打开窗口时，都需要刷新计划名称 & 用例执行列表
  // const newName = `【${getLabel(
  //   caseTypeEnum,
  //   testcaseStore.baseInfo.type
  // )}计划】${testcaseStore.baseInfo.name}-${generateSerialNumber()}`;
  // 2025-02-18： 优化计划名称生成规则, 用例名称 + 随机数。不再体现用例类型。
  const newName = `${testcaseStore.baseInfo.name}-${generateSerialNumber()}`;
  const newCaseQueue = [
    {
      case_base_id: testcaseStore.baseInfo.id,
      version: testcaseStore.baseInfo.version,
      selectedVersion: testcaseStore.baseInfo.version,
      name: testcaseStore.baseInfo.name
    }
  ];

  const firstInit =
    !planStore.info.name &&
    !planStore.info.case_queue.length &&
    !planStore.info.server_no &&
    !planStore.info.prefix;
  if (!planStore.shareState.keepCurrentSettings || firstInit) {
    // A. 用户设置：无需记住设置，自动刷新
    planStore.RESET_INFO();
    const server_no = planFormRef.value?.hasServer()
      ? testcaseStore.baseInfo.server_no
      : "";
    planStore.SET_INFO({
      name: newName,
      case_queue: newCaseQueue,
      env: testcaseStore.baseInfo.env,
      server_no: server_no,
      plan_type: typeMap[testcaseStore.baseInfo.type],
      inform: informMap[testcaseStore.baseInfo.type],
      select_disabled: true
    });
    planFormRef.value?.fetchAccountPrefix();
    collectTableRef.value?.setCurrentRow();
  } else {
    // B. 用户设置记录设置：只更新个别字段
    planStore.SET_INFO({
      name: newName,
      case_queue: newCaseQueue,
      server_no: lastPlanInfo.server_no,
      plan_type: typeMap[testcaseStore.baseInfo.type], // 为了动态绑定用例类型-计划类型
      select_disabled: true
    });
  }

  // 先同步获取服务器列表数据（目的是为了让 server_no 正常显示）
  planStore.SET_INFO({ id: null });
  planFormRef.value?.fetchServerOptions(planStore.info.env);
  planFormRef.value?.fetchWorkerQueueOptions();
  planFormRef.value?.fetchPrefixRules();
};

const generateSerialNumber = () => {
  const currentDate = new Date();
  const year = String(currentDate.getFullYear()).slice(-2);
  const month = ("0" + (currentDate.getMonth() + 1)).slice(-2);
  const day = ("0" + currentDate.getDate()).slice(-2);
  const datePart = year + month + day;
  const randomPart = Math.floor(1000 + Math.random() * 9000);
  return datePart + randomPart;
};

const confirm = () => {
  planStore.SET_INFO({
    case_queue: [
      {
        case_base_id: testcaseStore.baseInfo.id,
        version: testcaseStore.baseInfo.version,
        selectedVersion: testcaseStore.baseInfo.version,
        name: testcaseStore.baseInfo.name
      }
    ]
  });
  planStore.save(planFormRef.value?.formRef, planData => {
    dialogVisible.value = false;
    const reportId = planData?.latest_result_id;
    // 如果计划创建成功并且能够获取到报告ID，则跳转到报告详情页
    if (reportId) {
      navigateToReportDetail(reportId, true, { fullscreen: true }, false);
    }
  });
};

onMounted(() => {
  testcaseStore.fetchServerOptions(testcaseStore.baseInfo.env);
  fetchCollectList();
});

/**
 * 增加收藏计划运行设置功能
 */
const { initWatchTeamId } = useTeamGlobalState();
const query = {
  page: 1,
  size: 20,
  id: 0,
  type: collectTypeEnum.PLAN_RUN_SETTINGS.value,
  name: "",
  json_data: ""
};
const {
  collectTableRef,
  collectParams,
  collectListLoading,
  collectListTotal,
  collectList,
  currentCollectId,
  formLoading,
  fetchCollectList,
  handleCellDblclick,
  handleCancelEditState,
  handleNameChanged,
  handleSaveCurrentSettings,
  handleDeleteCollect,
  handleCollectRowClick
} = usePlanConfirmerHook({ query });
initWatchTeamId(fetchCollectList);

const handleRowClick = row => {
  handleCollectRowClick(row);
  planFormRef.value?.fetchServerOptions(testcaseStore.baseInfo.env);
};

defineExpose({});
</script>

<template>
  <el-dialog
    class="plan-confirmer"
    v-model="dialogVisible"
    :title="`🎯 快捷创建计划：${testcaseStore.baseInfo.name}`"
    width="auto"
    :draggable="true"
    align-center
    @click="handleCancelEditState"
  >
    <!-- 编辑状态蒙层 -->
    <div
      v-if="false"
      class="absolute left-0 top-0 bg-black opacity-50 z-10 w-full h-full"
      @click="dialogVisible = false"
    />
    <!-- 提示 -->
    <div
      v-if="false"
      class="flex flex-col mt-6 text-base font-light text-gray-600 pl-4"
    >
      <text class="font-bold">🎯 Tips</text>
      <text class="mt-2">
        1. 点击 "+1" 按钮会自动修改游戏账号的数字后缀；
      </text>
      <text class="mt-1">2. 调试前系统会自动保存，无需重复操作； </text>
    </div>
    <div class="mx-auto flex h-[72vh]">
      <!-- 左侧：收藏列表 -->
      <div
        v-if="showCollect"
        class="w-[340px] h-full overflow-hidden flex flex-col rounded-md border-gray-200 border-[1px]"
      >
        <!-- 搜索框 -->
        <div class="w-full my-1 px-1">
          <el-input
            v-model="collectParams.name"
            size="large"
            placeholder="使用关键字搜索您收藏的运行设置"
            :prefix-icon="Search"
            @change="fetchCollectList"
            clearable
          />
        </div>
        <div class="flex-1 overflow-auto cursor-pointer">
          <el-table
            height="100%"
            ref="collectTableRef"
            :loading="collectListLoading"
            :data="collectList"
            row-key="id"
            :current-row-key="currentCollectId"
            empty-text="尚未添加收藏"
            highlight-current-row
            @cell-dblclick="handleCellDblclick"
            @row-click="handleRowClick"
          >
            <el-table-column v-if="false" label="ID" prop="id" width="50px" />
            <el-table-column label="💛 我的收藏" prop="name">
              <template #default="{ row }">
                <div v-if="row.enableNameEdit" @click.stop>
                  <!-- 编辑 -->
                  <el-input
                    v-focus="true"
                    class="text-primary font-bold"
                    size="large"
                    v-model="row.name"
                    clearable
                    placeholder="编辑后按回车键确认修改"
                    @keyup.enter="handleNameChanged(row)"
                  />
                </div>
                <!-- 只读 -->
                <span v-else class="text-base font-light text-black">
                  {{ "◽  " + row.name }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="60px">
              <template #header>
                <div class="flex items-center justify-between">
                  <span />
                  <el-button-group class="ml-2">
                    <el-button
                      circle
                      title="刷新数据"
                      type="default"
                      plain
                      size="small"
                      :icon="Refresh"
                      @click="fetchCollectList"
                    />
                  </el-button-group>
                </div>
              </template>
              <template #default="{ row }">
                <div class="w-full flex justify-end">
                  <el-button
                    title="删除"
                    type="danger"
                    size="small"
                    plain
                    round
                    :icon="Delete"
                    @click.stop="handleDeleteCollect(row.id)"
                  />
                </div>
              </template>
            </el-table-column>
          </el-table>
        </div>
        <!-- 分页组件 -->
        <ComponentPager
          layout="total, sizes, prev, next"
          :query-form="query"
          :total="collectListTotal"
          @fetch-data="fetchCollectList"
        />
      </div>
      <!-- 右侧：计划表单组件 -->
      <div
        class="h-full overflow-hidden rounded-md border-gray-200 border-[1px] ml-2"
        v-loading="formLoading"
      >
        <el-scrollbar class="h-full">
          <PlanInfoForm
            ref="planFormRef"
            :show-header="false"
            :form-border="false"
          />
        </el-scrollbar>
      </div>
    </div>

    <!-- 底部按钮 -->
    <template #footer>
      <div class="w-full flex items-center">
        <el-checkbox
          v-if="showCollect"
          v-model="planStore.shareState.keepCurrentSettings"
          label="下次打开时保留当前设置"
          size="large"
        />
        <el-button
          v-if="showCollect"
          class="ml-auto"
          style="width: 200px"
          size="large"
          type="warning"
          plain
          @click="handleSaveCurrentSettings"
        >
          💛 收 藏
        </el-button>
        <el-button
          :class="{ 'ml-auto': !showCollect }"
          style="width: 120px"
          @click="dialogVisible = false"
          size="large"
        >
          取消创建
        </el-button>
        <el-button
          style="width: 120px"
          type="primary"
          @click="confirm"
          size="large"
          :loading="testcaseStore.shareState.debugButtonLoading"
        >
          执行计划
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style lang="scss">
.plan-confirmer .el-dialog__body {
  padding-top: 10px !important;
  padding-bottom: 10px !important;
}
</style>
