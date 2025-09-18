<!-- 此组件用于辅助填写 GM 命令的 param参数 -->
<script lang="ts" setup>
import { message } from "@/utils/message";
import { ref } from "vue";
import { superRequest } from "@/utils/request";
import ComponentPager from "@/components/RePager/index.vue";
import { Search } from "@element-plus/icons-vue";
import { envTypeEnum, fishTypeEnum, sortedEnum } from "@/utils/enums";
import { listFish } from "@/api/outter";
import { copyTextToClipboard } from "@pureadmin/utils";

const props = defineProps({
  env: {
    type: Number,
    default: envTypeEnum.TEST.value
  },
  envDisabled: {
    type: Boolean,
    default: true
  },
  target_num: {
    type: Number,
    default: 1
  }
});

defineOptions({
  name: "FishInfoDialog"
});

const emit = defineEmits(["complete"]);

// 捕鱼列表 组件变量
const title = ref(`🐟 多多玩 - 捕鱼 - 鱼信息`);
const dialogVisible = ref(false);

// =============【鱼类型相关的信息列表】相关 ==============
const query = {
  page: 1,
  size: 20,
  env: props.env, //现在不用
  target_num: props.target_num,
  id: 0,
  keyword: ""
};
const itemLoading = ref(false);
const queryRef = ref(query);
// const itemsList = ref([]);
const itemTotal = ref(0);
const itemsList = ref([]);
const fetchItems = async () => {
  await superRequest({
    apiFunc: listFish,
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
      fishIdRef.value?.scrollTo({ top: 0 });
    }
  });
};

const handleQuerychanged = (val: any, key: string) => {
  queryRef.value[key] = val;
  fetchItems();
};

const randomFish = () => {
  if (itemsList.value.length > 0) {
    fishIdRef.value.clearSelection();
    const filteredItemsList = itemsList.value.filter(
      item => item.name !== p.value
    );

    if (filteredItemsList.length === 0) return;

    const randomIndex = Math.floor(Math.random() * filteredItemsList.length);
    const randomItem = filteredItemsList[randomIndex];

    fishIdRef.value?.toggleRowSelection(randomItem, true);

    scrollToRow(randomIndex);
  }
};

// 通过获取到的 index 去滚动到对应的行，el-table本身是固定宽，根据
const scrollToRow = async rowIndex => {
  const tableRef = fishIdRef.value;
  if (tableRef) {
    const rows = tableRef.$el.querySelectorAll(
      ".el-table__body-wrapper tbody tr"
    );
    if (rows.length > rowIndex) {
      const targetRow = rows[rowIndex];
      if (targetRow) {
        targetRow.scrollIntoView({ behavior: "auto", block: "center" });
      }
    }
  }
};

// =============【鱼列表】相关 ==============
const fishIdRef = ref();

// 判断该行是否可选
const isSelectable = row => {
  const selectedRowsCount = fishIdRef?.value?.getSelectionRows().length || 0;
  const selectedColor = "#cee5ff";
  const disabledColor = "#f5f7fa";
  const normalColor = "";

  let result = false;
  // 只能选择一条鱼
  if (selectedRowsCount === 1) {
    const selectedRow = fishIdRef?.value?.getSelectionRows()[0];
    result = row.id === selectedRow.id;
    if (result) {
      row.bgColor = selectedColor;
    } else {
      row.bgColor = disabledColor;
    }
  } else if (selectedRowsCount === 0) {
    row.bgColor = normalColor;
    result = true;
  } else {
    row.bgColor = disabledColor;
    result = false;
  }
  return result;
};

let p: any;
const show = (pointer: any) => {
  p = pointer;
  dialogVisible.value = true;
  queryRef.value.env = props.env;
  queryRef.value.target_num = props.target_num;
  fetchItems();
};

const cancel = () => {
  dialogVisible.value = false;
  fishIdRef.value.clearSelection();
};

const confirm = () => {
  const rows = fishIdRef.value.getSelectionRows();
  if (rows.length === 0) {
    message("尚未选择鱼信息", { type: "error" });
    return;
  }
  emit("complete", rows);
  dialogVisible.value = false;
  // 更新 input 框中的鱼信息
  const fishName = rows[0].name;
  p.value = fishName;
  fishIdRef.value.clearSelection();
};

const rowStyle = item => {
  return { backgroundColor: item.row.bgColor };
};

const clearP = (done: () => void) => {
  fishIdRef.value.clearSelection();
  done();
};

const handleCopyAccount = (account: string) => {
  const success = copyTextToClipboard(account);
  success
    ? message("已复制到系统剪切板！", { type: "success" })
    : message("复制到系统剪切板失败", { type: "error" });
};

const handleRowClick = row => {
  if (isSelectable(row)) {
    fishIdRef?.value?.toggleRowSelection(row);
  } else {
    message("只能选择一种类型的鱼 ！", { type: "warning" });
  }
};
defineExpose({ show });
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    :title="title"
    width="60vw"
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
      <el-radio-group
        :disabled="props.envDisabled"
        v-model="query.env"
        size="large"
        @change="handleQuerychanged($event, 'env')"
      >
        <el-radio
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
      <!-- 鱼类型 -->
      <div class="flex justify-center items-center" style="margin-left: 15px">
        <el-tooltip content="请选择鱼类型" effect="dark" placement="top">
          <IconifyIconOnline icon="material-symbols:help-outline" />
        </el-tooltip>
        <span class="text-base mx-2 text-gray-500 dark:text-white">鱼类型</span>
      </div>
      <el-radio-group
        v-model="query.target_num"
        size="large"
        @change="handleQuerychanged($event, 'target_num')"
      >
        <el-radio
          v-for="item in sortedEnum(fishTypeEnum)"
          :key="item.order"
          :label="item.value"
          border
          style="margin-right: 5px"
        >
          {{ item.label }}
        </el-radio>
      </el-radio-group>
      <div class="flex justify-start items-center">
        <el-divider direction="vertical" />
        <div class="ml-auto fixed-width" style="margin-left: 80px">
          <el-button size="large" type="warning" plain @click="randomFish()"
            >随机鱼
          </el-button>
        </div>
      </div>
      <el-divider direction="vertical" />
      <div class="ml-auto">
        <el-button
          @click="fetchItems()"
          :loading="itemLoading"
          size="large"
          type="primary"
          plain
          >同步鱼列表
        </el-button>
      </div>
    </div>

    <!-- 鱼信息列表 -->
    <div
      class="flex bg-gray-100 m-2 rounded-lg overflow-hidden"
      style="height: 60vh"
    >
      <!-- A. 鱼信息列表 id  name  desc type -->
      <div class="w-2/5 p-2" style="width: 100%">
        <div
          class="rounded-md bg-white border-1 h-full overflow-hidden shadow-md flex flex-col"
        >
          <!-- 搜索框 -->
          <div class="w-full my-1 px-1">
            <el-input
              v-model="queryRef.keyword"
              size="large"
              placeholder="搜索鱼信息"
              :prefix-icon="Search"
              @change="handleQuerychanged($event, 'keyword')"
              clearable
            />
          </div>
          <div class="flex-1 overflow-auto">
            <el-table
              style="height: 100%; width: 100%"
              ref="fishIdRef"
              v-loading="itemLoading"
              :data="itemsList"
              row-key="id"
              empty-text="请选择鱼信息"
              :row-style="rowStyle"
              @row-click="handleRowClick"
              id="fish-table"
            >
              <el-table-column
                type="selection"
                width="120"
                reserve-selection
                :selectable="isSelectable"
              />
              <el-table-column label="ID" prop="id" width="84px" sortable />
              <el-table-column
                label="鱼名（英）"
                prop="name"
                sortable
                show-overflow-tooltip
              >
                <template v-slot="scope">
                  <span
                    @click="handleCopyAccount(scope.row.name)"
                    class="el-button el-button--warning el-button--large is-plain"
                  >
                    {{ scope.row.name }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column
                label="鱼名（中）"
                prop="desc"
                sortable
                show-overflow-tooltip
              />
              <el-table-column
                label="类型"
                prop="type"
                sortable
                show-overflow-tooltip
                width="84"
              />
            </el-table>
          </div>

          <!-- 分页组件 -->
          <ComponentPager
            :query-form="query"
            :total="itemTotal"
            @fetch-data="fetchItems"
          />
        </div>
      </div>
    </div>
    <template #footer>
      <!-- <el-button class="float-left" type="success" size="large" plain>
        GM 请求快捷导入
      </el-button> -->
      <el-button @click="cancel" size="large">取 消</el-button>
      <el-button type="primary" @click="confirm" size="large"> 确定</el-button>
    </template>
  </el-dialog>
</template>
