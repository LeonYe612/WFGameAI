<!-- 此组件用于辅助填写 GM 命令的 param参数 -->
<script lang="ts" setup>
import { message } from "@/utils/message";
import { ref } from "vue";
import { superRequest } from "@/utils/request";
import { envTypeEnum, sortedEnum } from "@/utils/enums";
import { listScore } from "@/api/outter";

const props = defineProps({
  env: {
    type: Number,
    default: envTypeEnum.TEST.value
  },
  envDisabled: {
    type: Boolean,
    default: true
  }
});

defineOptions({
  name: "ScoreInfoDialog"
});

// 捕鱼列表 组件变量
const title = ref(`🐟 多多玩 - 捕鱼 - 炮台分数选择器`);
const dialogVisible = ref(false);

// =============【房间炮台分数】相关 ==============
const query = {
  env: props.env
};
const itemLoading = ref(false);
const queryRef = ref(query);
const itemsList = ref([]);
const itemTotal = ref(0);
const itemTableRef = ref();
const selectedValue = ref("");

const fetchItems = async () => {
  await superRequest({
    apiFunc: listScore,
    apiParams: queryRef.value,
    onBeforeRequest: () => {
      itemLoading.value = true;
    },
    onSucceed: data => {
      itemsList.value = data.list || [];
      itemTotal.value = data.total;
    },
    onCompleted: () => {
      itemLoading.value = false;
      itemTableRef.value?.scrollTo({ top: 0 });
    }
  });
};

// =============【dialog按钮】相关 ==============

let p: any;
const show = (pointer: any) => {
  p = pointer;
  dialogVisible.value = true;
  queryRef.value.env = props.env;
  fetchItems();
};

const cancel = () => {
  dialogVisible.value = false;
};

const confirm = () => {
  if (!selectedValue.value || selectedValue.value.length === 0) {
    message("尚未选择正确的炮台分数 ！", { type: "warning" });
    return;
  }
  p.value = selectedValue.value[selectedValue.value.length - 1];
  selectedValue.value = null;
  dialogVisible.value = false;
};

const clearP = (done: () => void) => {
  p.value = null;
  selectedValue.value = null;
  done();
};

defineExpose({ show });
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    :title="title"
    width="35vw"
    :draggable="true"
    align-center
    :before-close="clearP"
  >
    <!-- 顶部信息 -->
    <div class="flex justify-start mb-4 items-center">
      <!-- 环境选择 -->
      <div class="flex justify-center items-center">
        <el-tooltip
          content="请选择此用例的运行环境"
          effect="dark"
          placement="top"
        >
          <IconifyIconOnline icon="material-symbols:help-outline" />
        </el-tooltip>
        <span class="text-base mx-2 text-gray-500 dark:text-white">环 境</span>
      </div>
      <el-radio-group v-model="query.env" size="large" @change="fetchItems">
        <el-radio
          :disabled="props.envDisabled"
          v-for="item in sortedEnum(envTypeEnum)"
          :key="item.order"
          :label="item.value"
          border
          style="margin-right: 5px"
        >
          {{ item.label }}
        </el-radio>
      </el-radio-group>
      <el-divider direction="vertical" />
      <div class="ml-auto">
        <el-button
          @click="fetchItems"
          :loading="itemLoading"
          size="large"
          type="primary"
          plain
        >
          同步炮台信息
        </el-button>
      </div>
    </div>

    <!-- 鱼信息列表 -->
    <div
      class="flex bg-gray-100 m-2 rounded-lg overflow-hidden"
      style="width: 80%; margin-left: 60px; margin-top: 35px"
    >
      <!-- A. 鱼信息列表 id  name  desc type -->
      <div class="w-2/5 p-2" style="width: 100%">
        <div
          class="rounded-md bg-white border-1 h-full overflow-hidden shadow-md flex flex-col"
        >
          <!--  级联选择器 -> 捕鱼room - scores  -->
          <el-cascader-panel
            :options="itemsList"
            v-model="selectedValue"
            :show-all-levels="false"
          />
        </div>
      </div>
    </div>
    <template #footer>
      <el-button @click="cancel" size="large">取 消</el-button>
      <el-button type="primary" @click="confirm" size="large"> 确定</el-button>
    </template>
  </el-dialog>
</template>
