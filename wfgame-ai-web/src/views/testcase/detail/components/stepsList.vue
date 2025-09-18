<script setup lang="ts">
import draggable from "vuedraggable";
import { Guide, CirclePlusFilled } from "@element-plus/icons-vue";
import {
  ref,
  nextTick,
  onDeactivated,
  onBeforeUnmount,
  defineProps
} from "vue";
import {
  Delete,
  Loading,
  CopyDocument,
  Download
} from "@element-plus/icons-vue";
import DragIcon from "@/assets/svg/drag.svg?component";
import { useTestcaseStoreHook } from "@/store/modules/testcase";
const {
  baseInfo,
  stepsList,
  shareState,
  currentStep,
  savingStatus,
  activeStep,
  addStep,
  delStep,
  sortStep,
  saveStep,
  saveStepSettings,
  copyStep,
  showStepSelector
} = useTestcaseStoreHook();
import { caseTypeEnum } from "@/utils/enums";
import _ from "lodash";

defineOptions({
  name: "TestcaseStepsList"
});

defineProps({
  editable: {
    type: Boolean,
    default: false
  }
});

const scrollRef = ref(null);

// 【滚动】到最后一个步骤元素
// const scrollToLastStep = () => {
//   const lastStepId = stepsList.length
//     ? stepsList[stepsList.length - 1].id
//     : null;
//   if (lastStepId) {
//     scrollToStep(lastStepId);
//   }
// };

// 【滚动】到指定ID的步骤元素
const scrollToStep = (stepId: number) => {
  nextTick(() => {
    const stepElement = document.getElementById(`step-${stepId}`);
    if (stepElement) {
      scrollRef.value.setScrollTop(stepElement.offsetTop);
    }
  });
};

// 【新增】点击事件
const handleAdd = () => {
  addStep({
    onSucceed: () => {
      scrollToStep(currentStep.id);
    }
  });
};

// 【拷贝】点击事件
const handleCopy = (stepId: number) => {
  copyStep({
    stepId,
    onSucceed: () => {
      scrollToStep(currentStep.id);
      // 触发排序更新
      sortStep();
    }
  });
};

// 【change】 保存步骤的运行设置
const funcMemo = {};
const changeFuncFactory = (stepId: number) => {
  if (!funcMemo[stepId]) {
    funcMemo[stepId] = _.debounce((step: any) => {
      saveStepSettings(step);
    }, 700);
  }
  return funcMemo[stepId];
};

/**
 * 实现用例步骤的自动保存
 *【新增步骤】的时候，步骤刚刚新建保存，即使currentStep变更也不需要自动保存
 * 1. 每次双击切换步骤的时候，自动保存切换前的步骤信息
 * 2. 离开页面的时候，自动保存当前 currentStep
 */
const autoSaveBeforeLeave = () => {
  if (currentStep.id) {
    console.log("检测到离开页面, 自动保存当前步骤:CurrentStep");
    saveStep();
  }
};
onDeactivated(autoSaveBeforeLeave);
onBeforeUnmount(autoSaveBeforeLeave);
</script>

<template>
  <el-container class="h-full border-gray-200 border-r">
    <el-header class="pt-2">
      <div
        class="mt-2 flex items-center py-8 px-4 bg-slate-100 dark:bg-transparent rounded-lg w-full h-12"
      >
        <div class="flex items-center w-full">
          <el-icon size="22">
            <Guide />
          </el-icon>
          <span class="text-lg font-bold ml-2 text-gray-600 dark:text-white">
            用例步骤
            <span v-show="!shareState.baseInfoFormVisible">
              （共
              <span class="text-blue-500">{{ stepsList?.length || 0 }}</span>
              步）
            </span>
          </span>
          <el-button
            v-if="editable"
            title="导入步骤"
            class="ml-auto"
            type="primary"
            plain
            :icon="Download"
            size="large"
            :loading="shareState.stepAddLoading"
            @click="showStepSelector"
          >
            导入步骤
          </el-button>
          <el-button
            v-if="editable"
            class="ml-auto"
            title="新增步骤"
            type="primary"
            :icon="CirclePlusFilled"
            size="large"
            :loading="shareState.stepAddLoading"
            @click="handleAdd"
          >
            新增步骤
          </el-button>
        </div>
      </div>
    </el-header>
    <el-main v-loading="shareState.stepListLoading">
      <el-scrollbar class="h-full" ref="scrollRef">
        <el-empty
          v-if="!stepsList || stepsList.length === 0"
          description="尚未添加任何步骤"
        />
        <!-- 单列拖拽 -->
        <draggable
          v-else
          :list="stepsList"
          item-key="id"
          chosen-class="chosen"
          force-fallback="true"
          animation="300"
          handle=".stepHandle"
          @sort="sortStep"
        >
          <!-- <template #header>
            <div>Header</div>
          </template> -->
          <template #item="{ element, index }">
            <div
              :id="`step-${element.id}`"
              class="p-1 cursor-pointer select-none border border-gray-200 shadow-sm rounded-md mb-2"
              :class="{ currentStepClass: currentStep.id == element.id }"
              @click="activeStep(index)"
            >
              <!-- 步骤信息 -->
              <div
                style="height: 70px"
                class="h-full flex justify-start items-center"
              >
                <!-- 拖拽图标 -->
                <div
                  v-if="editable"
                  class="h-full w-10 flex justify-center items-center stepHandle cursor-move"
                >
                  <el-icon size="22">
                    <DragIcon />
                  </el-icon>
                </div>
                <!-- 序号 -->
                <div
                  class="ml-2 w-8 h-8 rounded-full flex justify-center items-center"
                  :class="{
                    'bg-gray-100 text-gray-400': !element.is_pre,
                    'bg-blue-200 text-blue-400': element.is_pre
                  }"
                >
                  <span class="font-bold">
                    {{ index + 1 }}
                  </span>
                </div>
                <!-- 步骤名称 -->
                <div
                  class="ml-3 flex-1 h-full flex items-start flex-col justify-center overflow-hidden"
                >
                  <span
                    class="text-gray-600 dark:text-white text-base font-medium max-w-full whitespace-nowrap overflow-hidden overflow-ellipsis"
                  >
                    {{ element.name || "未命名步骤" }}
                  </span>
                  <div class="mt-2 flex justify-start items-center">
                    <span class="text-gray-400 text-xs font-medium">
                      请求消息:
                      <i
                        :class="{
                          'text-red-500 font-bold': !element.send_total
                        }"
                        >{{ element.send_total || 0 }}</i
                      >
                      个 | 响应消息:
                      <i
                        :class="{
                          'text-red-500 font-bold': !element.recv_total
                        }"
                        >{{ element.recv_total || 0 }}</i
                      >
                      个
                    </span>
                    <span
                      class="text-blue-400 text-xs ml-4"
                      v-show="savingStatus[element.id]"
                    >
                      <el-icon class="is-loading mr-1"><Loading /></el-icon>
                      <span>保存中...</span>
                    </span>
                  </div>
                </div>
                <!-- 操作 -->
                <div
                  class="h-full ml-auto flex items-center mr-3"
                  v-if="editable"
                >
                  <!-- 拷贝按钮 -->
                  <el-button
                    :title="`拷贝步骤 (ID: ${element.id})`"
                    :icon="CopyDocument"
                    type="primary"
                    circle
                    plain
                    :loading="shareState.stepCopyLoadings[element.id]"
                    @click.stop="handleCopy(element.id)"
                  />
                  <!-- 删除按钮 -->
                  <el-popconfirm
                    title="是否确认删除?"
                    @confirm="delStep(index)"
                  >
                    <template #reference>
                      <el-button
                        title="删除步骤"
                        :icon="Delete"
                        circle
                        plain
                        type="danger"
                        :loading="shareState.stepDelLoadings[element.id]"
                        @click.stop
                      />
                    </template>
                  </el-popconfirm>
                </div>
              </div>
              <!-- 运行设置 -->
              <div
                v-show="editable && shareState.stepSettingsVisible"
                class="border-t-[1px] py-2 px-4 w-full border-dashed border-gray-200 flex justify-between items-center text-gray-400"
              >
                <div class="flex justify-center items-center" @click.stop>
                  <el-tooltip
                    class="box-item"
                    content="标记为前置步骤后, 在机器人或压测场景下不参与用例集合的循环执行"
                    effect="light"
                    placement="top"
                    :hide-after="0"
                  >
                    <IconifyIconOnline icon="material-symbols:help-outline" />
                  </el-tooltip>
                  <label class="mx-1 text-sm" />
                  <el-checkbox
                    v-model="element.is_pre"
                    label="前置标记"
                    size="large"
                    @change="changeFuncFactory(element.id)(element)"
                  />
                </div>
                <div class="flex justify-center items-center" @click.stop>
                  <el-tooltip
                    class="box-item"
                    content="当前步骤重复执行的次数"
                    effect="light"
                    placement="top"
                    :hide-after="0"
                  >
                    <IconifyIconOnline icon="material-symbols:help-outline" />
                  </el-tooltip>
                  <label class="ml-1 text-sm">
                    {{ shareState.baseInfoFormVisible ? "循环:" : "循环次数:" }}
                  </label>
                  <el-input-number
                    :disabled="
                      ![
                        caseTypeEnum.COMMON.value,
                        caseTypeEnum.PRESSURE.value,
                        caseTypeEnum.ROBOT.value,
                        caseTypeEnum.BET.value,
                        caseTypeEnum.FIRE.value
                      ].includes(baseInfo.type)
                    "
                    style="width: 88px"
                    v-model="element.times"
                    :min="1"
                    size="small"
                    controls-position="right"
                    @change="changeFuncFactory(element.id)(element)"
                  />
                </div>
                <div class="flex justify-center items-center" @click.stop>
                  <el-tooltip
                    class="box-item"
                    content="当前步骤执行完成后的等待时间（毫秒）"
                    effect="light"
                    placement="top"
                    :hide-after="0"
                  >
                    <IconifyIconOnline icon="material-symbols:help-outline" />
                  </el-tooltip>
                  <label class="ml-1 text-sm">
                    {{ shareState.baseInfoFormVisible ? "间隔:" : "间隔时间:" }}
                  </label>
                  <el-input-number
                    style="width: 88px"
                    v-model="element.interval"
                    :min="0"
                    :step="500"
                    size="small"
                    controls-position="right"
                    @change="changeFuncFactory(element.id)(element)"
                  />
                </div>
              </div>
            </div>
          </template>
        </draggable>
      </el-scrollbar>
    </el-main>
  </el-container>
</template>
<style lang="scss" scoped>
.stepContainer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 16px;
  height: 50px;
  border-bottom: 1px solid #e5e4e9;
}
.currentStepClass {
  border: solid 2px #409eff !important;
  background-color: rgb(241 245 249 / 100);
}

.chosen {
  background-color: #f5f5f5;
  border: dashed 1px #dae8ff !important;
  border-radius: 10px;
  font-size: bold;
}
</style>
