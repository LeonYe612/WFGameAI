<script setup lang="ts">
import { Setting, Refresh, Download } from "@element-plus/icons-vue";

import { ref, onActivated, computed } from "vue";
import { listServer, listWorkerQueue } from "@/api/testcase";
import { superRequest } from "@/utils/request";
import { ElMessageBox, FormInstance, type UploadInstance } from "element-plus";
import { formRules } from "../utils/rules";
import { usePlanStoreHook } from "@/store/modules/plan";
import CircleSelector from "@/views/common/selectors/circleSelector/index.vue";
import CircleSelectorResult from "@/views/common/selectors/circleSelector/result.vue";
import LinkToExecutorDownloader from "@/views/executors/components/link.vue";
import DefaultUploader from "@/views/common/uploaders/defaultUploader/index.vue";
import {
  generateAccountPrefix,
  getPrefixRules,
  generateNicknamePrefix
} from "@/api/plan";
import { message } from "@/utils/message";
import { perms } from "@/utils/permsCode";
import { hasAuth } from "@/router/utils";

import {
  envEnum,
  planRunTypeEnum,
  sortedEnum,
  planInformEnum,
  planTypeEnum,
  reuseAccountEnum,
  getLabel
} from "@/utils/enums";
import { formatTimestamp } from "@/utils/time";

import { useTeamGlobalState } from "@/views/team/mine/utils/teamStoreStateHook";
import { ElMessage } from "element-plus";
import { useUpload } from "@/store/modules/oss";
import { baseUrlApi } from "@/api/utils";

const props = defineProps({
  showHeader: {
    type: Boolean,
    defult: true
  },
  formBorder: {
    type: Boolean,
    default: true
  }
});
const store = usePlanStoreHook();

defineOptions({
  name: "PlanInfoForm"
});

const info = store.info;
const formRef = ref<FormInstance>();
const circleSelectorRef = ref();
// 查询服务器列表选项
const serverOptions = ref<any>();
const fetchServerOptions = async (envParam: number) => {
  await superRequest({
    apiFunc: listServer,
    apiParams: { env: envParam },
    onSucceed: data => {
      serverOptions.value = data;
      // 每次刷新服务器列表时：
      // a. 如果当前 server_no 不在 serverOptions 范围内，就清空 server_no
      // b. 如果当前 server_no 在 serverOptions 范文内，需要重新赋值 server_no (否则仅显示数字而并非option文本)
      const exists = serverOptions.value?.some(
        item => item.server_no == info.server_no
      );
      info.server_no = exists ? info.server_no : null;
    }
  });
};

// 查询执行器列表选项
const workerQueueOptions = ref<any>();
const fetchWorkerQueueOptions = async () => {
  const { data } = await superRequest({
    apiFunc: listWorkerQueue
  });
  if (!data) {
    workerQueueOptions.value = [];
    return;
  }

  workerQueueOptions.value = [...data];
  // 判断 info.worker_queue
  // a. 值为空 ==> 默认选中第一个
  // b. 值不为空 ==> 判断是否存在，不存在则清空(用户必须重新选择)
  if (!info.worker_queue) {
    info.worker_queue = workerQueueOptions.value[0]?.key || "";
  } else {
    const isExist = workerQueueOptions.value.some(
      item => item.key === info.worker_queue
    );
    if (!isExist) {
      info.worker_queue = "";
    }
  }
};

const onExecutorVisibleChange = async (visible: Boolean) => {
  if (visible) {
    await fetchWorkerQueueOptions();
  }
};

const handleRandomPlanName = () => {
  const label = getLabel(planTypeEnum, info.plan_type);
  const dateStr = formatTimestamp(Date.now());
  const randomSuffix = Math.floor(Math.random() * 9000 + 1000); // 1000-9999之间的随机数
  const randomName = `${label}_${dateStr}_${randomSuffix}`;
  info.name = randomName;
};

// 获取游戏账号随机前缀
const nickLoading = ref(false);
const fetchNicknamePrefix = async () => {
  if (!store.info.server_no) {
    message("生成随机昵称需要先完成游戏服的选择！", { type: "warning" });
    return;
  }
  nickLoading.value = true;
  await superRequest({
    apiFunc: generateNicknamePrefix,
    apiParams: {
      env: store.info.env,
      server_no: store.info.server_no
    },
    enableFailedMsg: true,
    onSucceed: (nickname: string) => {
      store.info.nick_prefix = nickname;
    },
    onCompleted: () => {
      nickLoading.value = false;
    }
  });
};

// 获取游戏账号随机前缀
const accountPrefixLoading = ref(false);
const fetchAccountPrefix = async () => {
  accountPrefixLoading.value = true;
  if (!store.info.id) {
    await superRequest({
      apiFunc: generateAccountPrefix,
      apiParams: {
        env: store.info.env,
        is_reuse: store.info.is_reuse,
        target_num: store.info.account_num,
        target_num_min: store.info.account_num_min,
        target_num_max: store.info.account_num_max
      },
      enableFailedMsg: false,
      onSucceed: data => {
        accountPrefixLoading.value = false;
        store.info.prefix = data.prefix;
        store.info.account_len = data.account_len;
      },
      onFailed: (data, msg) => {
        accountPrefixLoading.value = false;
        if (msg.includes("【前缀规则】")) {
          ElMessage.error(msg);
        } else {
          ElMessageBox.alert(
            `您设置的账号长度超出输入范围<br>` +
              `规则：账号长度 = 前缀字符长度 + 执行人数单位长度<br>` +
              `即10 = 7【前缀字符长度】+ 3【执行人数 999】<br>`,
            {
              dangerouslyUseHTMLString: true,
              type: "error"
            }
          );
        }
      },
      onCompleted: () => {
        accountPrefixLoading.value = false;
      }
    });
  } else {
    accountPrefixLoading.value = false; // 如果有planID，则为查看计划内容，直接设置false且不请求
  }
};
const prefixRulesLoading = ref(false);
const prefixRules = ref([]);
const prefixLen = ref(5);
const nick_prefix_len = ref(5);
const fetchPrefixRules = async () => {
  if (info.assign_account_type === 1) {
    return;
  }
  prefixRulesLoading.value = true;
  await superRequest({
    apiFunc: getPrefixRules,
    apiParams: { env: store.info.env },
    onSucceed: data => {
      prefixRulesLoading.value = false;
      const rules = eval(data.form_rules);
      prefixLen.value = data.prefix_len; // 添加这一行，获取prefix_len字段
      nick_prefix_len.value = data.nick_prefix_len;
      // 检查规则是否非空
      if (rules && rules.length > 0) {
        // 应用规则到表单验证
        prefixRules.value = rules;
      } else {
        // 处理空规则的情况
        prefixRules.value = [];
        ElMessage.warning("账号前缀规则为空，请自行检查输入的账号前缀是否合规");
      }
    }
  });
};
// const prefix = computed(() => info.prefix);
//
// watch(prefix, (newInf, oldInf) => {
//   console.log('store.info changed from', oldInf, 'to', newInf);
// });
// 获取运行类型的提示信息
const getRunTypeTip = computed(() => {
  return value => {
    if (value === planRunTypeEnum.SINGLE.value) {
      return "Tip: 创建完成并启用后立即执行, 仅执行一次";
    } else if (value === planRunTypeEnum.SCHEDULE.value) {
      return "Tip: 设置时间启用后到达时间节点时执行，仅执行一次";
    } else if (value === planRunTypeEnum.CIRCLE.value) {
      return "Tip: 设置循环频率，可执行多次";
    }
  };
});

// 获取运行类型列表
const getRunTypeOptions = computed(() => {
  const options = sortedEnum(planRunTypeEnum).filter(
    item =>
      item.value !== planRunTypeEnum.DEBUG.value &&
      item.value !== planRunTypeEnum.ALL.value &&
      item.value !== planRunTypeEnum.WEBHOOK.value
  );
  // 只有[通用计划类型]允许设置 webhook执行
  if (
    info.plan_type === planTypeEnum.PLAN.value ||
    info.plan_type === planTypeEnum.ARRANGE.value
  ) {
    options.push(planRunTypeEnum.WEBHOOK);
  }
  return options;
});

const setDisabledDate = dt => {
  return dt.getTime() < Date.now() - 8.64e7;
};

const onEnvChanged = value => {
  // a. 清空服务器选项
  info.server_no = null;
  fetchServerOptions(value);
  // b. 切换环境清空用例绑定
  if (store.info.case_queue?.length) {
    store.CLEAR_CASE_QUEUE();
    message("请重新为计划绑定所选环境下的用例！", { type: "warning" });
  }
};

const showCircleSelector = () => {
  circleSelectorRef.value?.show();
};

const onRunTypeChanged = value => {
  if (value === planRunTypeEnum.CIRCLE.value) {
    showCircleSelector();
  }
};

onActivated(() => {
  // fetchServerOptions(info.env);
  // fetchAccountPrefix();
});

const onCircleSelecotComplete = (circleObj: any) => {
  store.SET_RUN_INFO_CIRCLE(circleObj);
};

const handlePlanTypeChange = (value: number) => {
  // 清理选中的case及tab信息
  store.RESET_ASSIGN_FIELD_INFO([
    "case_queue",
    "old_tab_name",
    "new_tab_name",
    "whole_case_queue",
    "editableTabs",
    "case_type"
  ]);
  store.UPDATE_PLAN_TYPE(value);
  // 如果是 [自定义编排类型] 无需设置默认的编辑表格
  if (value !== planTypeEnum.ARRANGE.value) {
    store.UPDATE_DEFAULT_EDITTABLES(value);
  }
  // 机器人计划类型时默认开启推送通知
  if (value === planTypeEnum.ROBOT.value) {
    store.info.inform = planInformEnum.ENABLE.value;
  } else {
    store.info.inform = planInformEnum.DISABLE.value;
  }
};

// 判断服务器列表中是否存在指定服务器
const hasServer = (server_no: number) => {
  return serverOptions.value?.some(item => item.server_no === server_no);
};

const formatAccount = (prefix: string, appendix: number) => {
  const appendixStr = String(appendix);
  return `${prefix}${appendixStr.padStart(
    store.info.account_len - (prefix?.length || 0),
    "0"
  )}`;
};

// 处理循环类型切换：控制循环次数 <-> 控制循环时间
const handleCycleTypeChange = () => {
  if (info.cycle_type === 0) {
    info.cycle_text = "次，间隔";
  } else {
    info.cycle_text = "分钟，间隔";
  }
};

// const selectedPlanTypeLabel = () => {
//   const selectedType = Object.values(planTypeEnum).find(
//     item => item.value === info.plan_type
//   );
//   return selectedType ? selectedType.label : "未选择";
// };

// ========== 指定测试账号 & 上传/下载 文件相关==========
const onAcountTypeChanged = value => {
  // a. 清理已经上传的文件
  if (value === 0) {
    fetchPrefixRules();
    info.assign_account = "";
    info.upload_file_list.splice(0, info.upload_file_list.length);
  } else {
    // b. 清理已定义的测试账号前缀 & 区间
    info.prefix = "";
    info.account_num_min = 1;
    info.account_num_max = 1;
  }
};
const uploadRef = ref<UploadInstance | null>(null);
const setUploadRef = (ref: UploadInstance | null) => {
  uploadRef.value = ref;
};
const { beforeUpload, handleExceed, handleError, handleRemove } =
  useUpload(uploadRef);

const handleDownload = event => {
  event.preventDefault();
  const link = document.createElement("a");
  link.href = baseUrlApi(info.assign_account);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

defineExpose({
  formRef,
  hasServer,
  fetchServerOptions,
  fetchWorkerQueueOptions,
  fetchAccountPrefix,
  fetchPrefixRules
});

const { initWatchTeamId } = useTeamGlobalState();
initWatchTeamId(() => {
  fetchServerOptions(info.env);
  fetchAccountPrefix();
  fetchPrefixRules();
});
</script>

<template>
  <el-container
    v-loading="store.shareState.detailLoading"
    class="h-full rounded-md border-gray-200"
    :class="{ border: props.formBorder }"
  >
    <el-header v-if="props.showHeader" class="pt-2">
      <div
        class="mt-2 flex items-center p-8 bg-slate-100 dark:bg-transparent rounded-lg w-full h-12"
      >
        <div class="flex items-center w-full">
          <el-icon size="22">
            <Setting />
          </el-icon>
          <span class="text-lg font-bold ml-2 text-gray-600 dark:text-white">
            基础信息 & 运行设置
          </span>
        </div>
      </div>
    </el-header>
    <el-main>
      <el-scrollbar class="h-full">
        <el-form
          :disabled="
            (!hasAuth(perms.plan.detail.writable) &&
              !hasAuth(perms.plan.list.writable) &&
              !hasAuth(perms.testcase.list.writable) &&
              !hasAuth(perms.testcase.detail.writable)) ||
            store.info.id
          "
          :model="info"
          size="large"
          label-width="100px"
          ref="formRef"
          :rules="formRules"
        >
          <!-- A-基础信息 -->
          <el-divider style="margin-bottom: 36px">
            <span class="text-gray-400">基础信息</span>
          </el-divider>
          <el-form-item prop="plan_type" class="pr-16">
            <template #label>
              <div class="flex justify-center items-center">
                <el-tooltip
                  content="请择计划类型（普通/机器人/压测）"
                  effect="dark"
                  placement="top"
                >
                  <IconifyIconOnline icon="material-symbols:help-outline" />
                </el-tooltip>
                <label>计划类型</label>
              </div>
            </template>
            <el-select
              class="w-full"
              v-model="info.plan_type"
              filterable
              placeholder="请选择计划类型"
              clearable
              @change="handlePlanTypeChange"
              :disabled="info.select_disabled"
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
          </el-form-item>
          <el-form-item prop="name" class="pr-16">
            <template #label>
              <div class="flex justify-center items-center">
                <el-tooltip
                  content="为计划起一个简洁明了的名称"
                  effect="dark"
                  placement="top"
                >
                  <IconifyIconOnline icon="material-symbols:help-outline" />
                </el-tooltip>
                <label>计划名称</label>
              </div>
            </template>
            <el-input
              v-model="info.name"
              placeholder="请填写计划名称"
              clearable
              style="flex: 1"
            />
            <el-button
              type="primary"
              :icon="Refresh"
              @click="handleRandomPlanName"
              style="font-size: 18px; padding: 10px; margin-left: 10px"
              plain
            />
          </el-form-item>
          <el-form-item prop="inform" class="pr-16">
            <template #label>
              <div class="flex justify-center items-center">
                <el-tooltip
                  content="开启后会将计划执行结果推送到企业微信中(团队设置中预留的企业微信群ID)"
                  effect="dark"
                  placement="top"
                >
                  <IconifyIconOnline icon="material-symbols:help-outline" />
                </el-tooltip>
                <label>推送设置</label>
              </div>
            </template>
            <el-switch
              v-model="info.inform"
              :active-value="planInformEnum.ENABLE.value"
              :inactive-value="planInformEnum.DISABLE.value"
            />
          </el-form-item>
          <!-- B-账号设置 -->
          <el-divider style="margin-bottom: 36px">
            <span class="text-gray-400">账号设置</span>
          </el-divider>

          <el-form-item prop="assign_account_type" class="pr-16">
            <template #label>
              <div class="flex justify-center items-center">
                <el-tooltip
                  content="请选择此计划的账号类型"
                  effect="dark"
                  placement="top"
                >
                  <IconifyIconOnline icon="material-symbols:help-outline" />
                </el-tooltip>
                <label>生成规则</label>
              </div>
            </template>
            <el-radio-group
              v-model="info.assign_account_type"
              @change="onAcountTypeChanged"
            >
              <el-radio :label="0" border>
                <div class="flex items-center">
                  <el-tag type="success" size="small">前缀 & 区间</el-tag>
                </div>
              </el-radio>
              <el-radio :label="1" border>
                <div class="flex items-center">
                  <el-tag type="warning" size="small">账号 & 密码</el-tag>
                </div>
              </el-radio>
            </el-radio-group>
          </el-form-item>

          <el-form-item
            prop="is_reuse"
            class="pr-16"
            v-if="info.plan_type !== 1 && info.assign_account_type != 1"
          >
            <template #label>
              <div class="flex justify-center items-center">
                <el-tooltip
                  content="开启后，将复用游戏账号"
                  effect="dark"
                  placement="top"
                >
                  <IconifyIconOnline icon="material-symbols:help-outline" />
                </el-tooltip>
                <label>复用账号</label>
              </div>
            </template>
            <div class="flex items-center">
              <el-switch
                v-model="info.is_reuse"
                :active-value="reuseAccountEnum.ENABLE.value"
                :inactive-value="reuseAccountEnum.DISABLE.value"
              />
              <span class="ml-2 font-medium text-gray-500/80">
                ⚠️ 启用此参数表示允许使用老账号
              </span>
            </div>
          </el-form-item>
          <!-- B1-账号前缀 -->
          <el-form-item
            prop="prefix"
            class="pr-16"
            v-if="info.assign_account_type != 1"
            :rules="prefixRules"
            :key="prefixRules.length"
          >
            <template #label>
              <div class="flex justify-center items-center">
                <el-tooltip
                  content="填写游戏账号前缀后会自动生成账号，生成规则请在【我的团队】-【环境配置】自行定义"
                  effect="dark"
                  placement="top"
                >
                  <IconifyIconOnline icon="material-symbols:help-outline" />
                </el-tooltip>
                <label>账号前缀</label>
              </div>
            </template>
            <el-input
              v-model="info.prefix"
              placeholder="请填写游戏账号前缀"
              :maxlength="prefixLen || null"
              show-word-limit
              clearable
              style="flex: 1"
            />
            <el-tooltip
              content="点击自动生成游戏账号前缀"
              effect="dark"
              placement="top"
            >
              <el-button
                v-if="true || info.is_reuse === reuseAccountEnum.DISABLE.value"
                type="primary"
                :icon="Refresh"
                @click="fetchAccountPrefix"
                :loading="accountPrefixLoading"
                style="font-size: 18px; padding: 10px; margin-left: 10px"
                plain
              />
            </el-tooltip>
          </el-form-item>
          <!-- B2-执行人数/间隔/次数（压测/机器人计划类型使用）-->
          <el-form-item
            prop="account_num"
            class="pr-16"
            v-if="
              info.plan_type !== planTypeEnum.DEBUG.value &&
              info.plan_type !== planTypeEnum.PLAN.value &&
              info.assign_account_type != 1
            "
          >
            <template #label>
              <div class="flex justify-center items-center">
                <el-tooltip
                  content="填写账号区间会自动生成对应区间内的测试账号"
                  effect="dark"
                  placement="top"
                >
                  <IconifyIconOnline icon="material-symbols:help-outline" />
                </el-tooltip>
                <label>账号区间</label>
              </div>
            </template>
            <div>
              <el-input-number
                style="flex: 1"
                v-model="info.account_num_min"
                placeholder="号段最小值"
                controls-position="right"
                :min="1"
                :max="9999"
                value-on-clear="min"
                @change="
                  info.account_num_max = Math.max(
                    info.account_num_max,
                    info.account_num_min
                  )
                "
              />
              <span class="mx-2 text-base">~</span>
              <el-input-number
                style="flex: 1"
                v-model="info.account_num_max"
                placeholder="号段最大值"
                controls-position="right"
                :min="info.account_num_min"
                :max="9999"
                value-on-clear="min"
              />
            </div>
          </el-form-item>
          <!-- B3-生成账号提示-->
          <el-form-item
            prop="tip"
            class="pr-16 -mt-1"
            v-if="info.prefix && info.assign_account_type != 1"
          >
            <span class="text-sm text-gray-400">
              Tip: 使用
              <b>{{ formatAccount(info.prefix, info.account_num_min) }}</b>
              <b v-show="info.account_num_max > 1">
                ~ {{ formatAccount(info.prefix, info.account_num_max) }}
              </b>
              共
              <b>{{ info.account_num_max - info.account_num_min + 1 }}</b>
              个账号
            </span>
          </el-form-item>
          <!-- B4-昵称前缀-->
          <el-form-item
            prop="nick_prefix"
            class="pr-16"
            v-if="info.assign_account_type != 1"
          >
            <template #label>
              <div class="flex justify-center items-center">
                <el-tooltip
                  content="填写游戏账号指定角色昵称前缀（不填默认后端随机生成角色昵称）"
                  effect="dark"
                  placement="top"
                >
                  <IconifyIconOnline icon="material-symbols:help-outline" />
                </el-tooltip>
                <label>昵称前缀</label>
              </div>
            </template>
            <el-input
              v-model="info.nick_prefix"
              placeholder="不填写则由系统随机生成"
              :maxlength="nick_prefix_len || null"
              show-word-limit
              clearable
              style="flex: 1"
            />
            <el-button
              v-if="true"
              type="primary"
              :icon="Refresh"
              @click="fetchNicknamePrefix"
              :loading="nickLoading"
              style="font-size: 18px; padding: 10px; margin-left: 10px"
              plain
            />
          </el-form-item>
          <!-- B5-分批压测-->
          <el-form-item
            prop="batch_enabled"
            class="pr-16"
            v-if="
              (info.plan_type === planTypeEnum.PRESS.value ||
                info.plan_type === planTypeEnum.LOAD_TEST.value ||
                info.plan_type === planTypeEnum.BET.value ||
                info.plan_type === planTypeEnum.FIRE.value) &&
              info.assign_account_type != 1
            "
          >
            <template #label>
              <div class="flex justify-center items-center">
                <el-tooltip
                  content="启用后将控制账号分批次登录并执行用例"
                  effect="dark"
                  placement="top"
                >
                  <IconifyIconOnline icon="material-symbols:help-outline" />
                </el-tooltip>
                <label>分批压测</label>
              </div>
            </template>
            <div class="w-full h-full flex items-center select-none">
              <el-switch
                v-model="info.batch_enabled"
                :active-value="true"
                :inactive-value="false"
              />
              <div v-show="info.batch_enabled" class="ml-4">
                <span class="mr-1"> 每隔 </span>
                <el-input-number
                  v-model="info.batch_interval"
                  :controls="false"
                  placeholder="X"
                  :min="0"
                  size=""
                  value-on-clear="min"
                  style="width: 80px"
                />
                <span class="mx-1"> 毫秒，运行 </span>
                <el-input-number
                  v-model="info.batch_size"
                  :controls="false"
                  placeholder="X"
                  :min="0"
                  :max="info.account_num_max - info.account_num_min + 1"
                  size=""
                  value-on-clear="min"
                  style="width: 80px"
                />
                <span class="mx-1"> 个账号 </span>
              </div>
            </div>
          </el-form-item>
          <!-- B6-上传指定的测试账号 & 密码 csv文件-->
          <el-form-item
            prop="assign_account"
            v-model="info.assign_account"
            class="pr-16"
            v-if="info.plan_type !== 0 && info.assign_account_type == 1"
          >
            <template #label>
              <div class="flex justify-center items-center">
                <el-tooltip
                  content="上传 / 下载 待测试的账号密码配置文件（.csv）"
                  effect="dark"
                  placement="top"
                >
                  <IconifyIconOnline icon="material-symbols:help-outline" />
                </el-tooltip>
                <label>指定文件</label>
              </div>
            </template>
            <div class="w-full h-full flex items-center select-none">
              <DefaultUploader
                @update:uploadRef="setUploadRef"
                :limit="1"
                :file-list="info.upload_file_list"
                :on-exceed="handleExceed"
                :before-upload="beforeUpload"
                :on-error="handleError"
                :on-remove="handleRemove"
                :show-file-list="true"
                v-loading="store.shareState.uploading"
                multiple
              />
              <!-- 添加下载按钮 -->
              <el-button
                v-if="info.assign_account !== ''"
                type="primary"
                :icon="Download"
                size="large"
                style="
                  width: 120px;
                  font-size: 16px;
                  margin-left: 166px;
                  top: 0px;
                  position: absolute;
                "
                @click="handleDownload"
              >
                下载
              </el-button>
              <a ref="downloadLink" style="display: none" />
            </div>
          </el-form-item>
          <!-- C-运行设置 -->
          <el-divider style="margin-bottom: 36px">
            <span class="text-gray-400">运行设置</span>
          </el-divider>
          <!-- C1-运行环境 -->
          <el-form-item prop="env" class="pr-16">
            <template #label>
              <div class="flex justify-center items-center">
                <el-tooltip
                  content="请选择此计划的运行环境"
                  effect="dark"
                  placement="top"
                >
                  <IconifyIconOnline icon="material-symbols:help-outline" />
                </el-tooltip>
                <label>运行环境</label>
              </div>
            </template>
            <el-radio-group v-model="info.env" @change="onEnvChanged">
              <el-radio :label="envEnum.TEST" border>
                <div class="flex items-center">
                  <el-tag type="success" size="small">测试</el-tag>
                </div>
              </el-radio>
              <el-radio :label="envEnum.DEV" border>
                <div class="flex items-center">
                  <el-tag type="warning" size="small">开发</el-tag>
                </div>
              </el-radio>
            </el-radio-group>
          </el-form-item>
          <!-- C2-选择服务器 -->
          <el-form-item prop="server_no" class="pr-16">
            <template #label>
              <div class="flex justify-center items-center">
                <el-tooltip
                  content="请选择在哪台服务器上执行测试计划"
                  effect="dark"
                  placement="top"
                >
                  <IconifyIconOnline icon="material-symbols:help-outline" />
                </el-tooltip>
                <label>服务器&nbsp;&nbsp;&nbsp;&nbsp;</label>
              </div>
            </template>
            <el-select
              class="w-full"
              v-model="info.server_no"
              filterable
              placeholder="请选择服务器"
              clearable
            >
              <el-option
                v-for="item in serverOptions"
                :key="item.server_no"
                :label="`${item.server_name}[${item.ws_url}]`"
                :value="item.server_no"
              />
            </el-select>
          </el-form-item>
          <el-form-item prop="worker_queue" class="pr-16">
            <template #label>
              <div class="flex justify-center items-center">
                <el-tooltip
                  content="您可以自定义本次执行任务的节点服务器(Worker Queue)"
                  effect="dark"
                  placement="top"
                >
                  <IconifyIconOnline icon="material-symbols:help-outline" />
                </el-tooltip>
                <label>执行器&nbsp;&nbsp;&nbsp;&nbsp;</label>
              </div>
            </template>
            <el-select
              class="w-full"
              v-model="info.worker_queue"
              filterable
              placeholder="请选择本次计划任务的执行器"
              clearable
              @visible-change="onExecutorVisibleChange"
            >
              <el-option
                v-for="item in workerQueueOptions"
                :key="item.key"
                :label="`${item.key} [${item.label}]`"
                :value="item.key"
              />
            </el-select>
            <LinkToExecutorDownloader />
          </el-form-item>
          <!-- 用例组循环控制(后续应该会移动此参数位置) -->
          <el-form-item
            prop="cycle_type"
            class="pr-16"
            v-if="info.plan_type >= planTypeEnum.ROBOT.value"
          >
            <template #label>
              <div class="flex justify-center items-center">
                <el-tooltip
                  content="用来控制用例组的循环执行次数（或循环执行总时间）和间隔时间"
                  effect="dark"
                  placement="top"
                >
                  <IconifyIconOnline icon="material-symbols:help-outline" />
                </el-tooltip>
                <label>循环控制</label>
              </div>
            </template>
            <!-- 默认循环控制类型0（循环次数控制），1（循环时间控制）-->
            <el-radio-group
              v-model="info.cycle_type"
              @change="handleCycleTypeChange"
            >
              <el-radio :key="0" :label="0" border> 次数</el-radio>
              <el-radio :key="1" :label="1" border> 时间</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item
            prop="cycle_type"
            v-model="info.cycle_type"
            class="pr-16"
            style="background-color: rgb(241 245 249)"
            v-if="info.plan_type >= planTypeEnum.ROBOT.value"
          >
            <div class="w-full h-full flex items-center select-none">
              <div>
                <span class="mr-1"> 用例组执行 </span>
                <el-input-number
                  v-model="info.times"
                  :controls="false"
                  placeholder="X"
                  :min="1"
                  value-on-clear="min"
                  style="width: 80px"
                />
                <span class="mx-1"> {{ info.cycle_text }} </span>
                <el-input-number
                  v-model="info.interval"
                  :controls="false"
                  placeholder="X"
                  :min="0"
                  value-on-clear="min"
                  style="width: 80px"
                />
                <span class="mx-1"> 毫秒 </span>
              </div>
            </div>
          </el-form-item>
          <!-- C4-计划类型相关设置 -->
          <el-form-item
            prop="run_type"
            class="pr-16"
            v-if="info.plan_type !== 5"
          >
            <template #label>
              <div class="flex justify-center items-center">
                <el-tooltip
                  content="请选择此计划的运行类型"
                  effect="dark"
                  placement="top"
                >
                  <IconifyIconOnline icon="material-symbols:help-outline" />
                </el-tooltip>
                <label>运行类型</label>
              </div>
            </template>
            <el-radio-group v-model="info.run_type" @change="onRunTypeChanged">
              <el-radio
                v-for="item in getRunTypeOptions"
                :key="item.value"
                :label="item.value"
                size="default"
                border
              >
                {{ item.label }}
              </el-radio>
            </el-radio-group>
          </el-form-item>
          <!--提示内容-->
          <el-form-item prop="tip" class="pr-16 -mt-1">
            <span class="text-sm text-gray-400">
              {{ getRunTypeTip(info.run_type) }}
            </span>
          </el-form-item>
          <!-- 定时类型：专用参数 run_info.schedule -->
          <el-form-item
            v-if="info.run_type === planRunTypeEnum.SCHEDULE.value"
            prop="run_info.schedule"
            class="pr-16"
          >
            <template #label>
              <div class="flex justify-center items-center">
                <el-tooltip
                  content="请设置定时执行的日期和时间"
                  effect="dark"
                  placement="top"
                >
                  <IconifyIconOnline icon="material-symbols:help-outline" />
                </el-tooltip>
                <label>设置定时</label>
              </div>
            </template>
            <el-date-picker
              v-model="info.run_info.schedule"
              type="datetime"
              value-format="YYYY-MM-DD HH:mm:ss"
              placeholder="请选择日期和时间"
              :disabled-date="setDisabledDate"
            />
          </el-form-item>
          <!-- 周期类型：专用参数 run_info.circle -->
          <el-form-item
            v-if="info.run_type === planRunTypeEnum.CIRCLE.value"
            prop="run_info.circle"
            class="pr-16"
          >
            <template #label>
              <div class="flex justify-center items-center">
                <el-tooltip
                  content="请设置周期执行的规则"
                  effect="dark"
                  placement="top"
                >
                  <IconifyIconOnline icon="material-symbols:help-outline" />
                </el-tooltip>
                <label>周期规则</label>
              </div>
            </template>
            <CircleSelectorResult :settings="store.info.run_info.circle" />
            <div>
              <el-button
                :icon="Setting"
                @click="showCircleSelector"
                size="small"
              >
                设置规则
              </el-button>
            </div>
          </el-form-item>
        </el-form>
        <!-- 当设置为周期类型时候的，周期设置选择器 -->
        <CircleSelector
          ref="circleSelectorRef"
          @complete="onCircleSelecotComplete"
        />
      </el-scrollbar>
    </el-main>
  </el-container>
</template>

<style scoped>
.custom-background {
  background-color: #f0f0f0; /* 你想要的背景颜色 */
}
</style>
