<script setup lang="ts">
import draggable from "vuedraggable";
import {
  Guide,
  Plus,
  CirclePlusFilled,
  MoreFilled
} from "@element-plus/icons-vue";
import { ref, computed, onMounted, nextTick } from "vue";
import DragIcon from "@/assets/svg/drag.svg?component";
import { usePlanStoreHook } from "@/store/modules/plan";
import TestPlanCaseSelector from "@/views/common/selectors/arrangeCasesSeletor/index.vue";
import { perms } from "@/utils/permsCode";
import { hasAuth } from "@/router/utils";
import { caseInsertModeEnum, planRunTypeEnum } from "@/utils/enums";
import { storeToRefs } from "pinia";
import { CaseQueueItem, MenuClickEvent } from "@/store/types";
import CaseCard from "@/views/plan/detail/components/caseCard.vue";
// import { throttle } from "lodash-es";
import { message } from "@/utils/message";
import TestcaseEditor from "./caseEditor.vue";
import ArrangerContextMenu from "./arrangerContextMenu.vue";
import { ElMessageBox } from "element-plus";
import { ArrowDown } from "@element-plus/icons-vue";

const store = usePlanStoreHook();
const { info } = storeToRefs(store);

const state = store.shareState;

onMounted(() => {});

defineOptions({
  name: "CasesArranger"
});

// 是否有编辑权限
const canEdit = computed(() => {
  return (
    hasAuth(perms.plan.detail.writable) &&
    (!info.value.id || info.value.run_type === planRunTypeEnum.WEBHOOK.value)
  );
});

// =========================== 复选框 =========================
const checkAll = computed({
  get: () => {
    return info.value.case_queue.every(block =>
      block.every(item => item.checked)
    );
  },
  set: val => {
    handleCheckChange(val);
  }
});

const handleCheckChange = val => {
  info.value.case_queue.forEach(block => {
    block.forEach(item => {
      item.checked = val;
    });
  });
};

const checkedCases = computed(() => {
  return info.value.case_queue.flat().filter(item => item.checked);
});

const totalCases = computed(() => {
  return info.value.case_queue.reduce(
    (total, block) => total + block.length,
    0
  );
});

const totalClients = computed(() => {
  return info.value.account_num_max - info.value.account_num_min + 1;
});
// =================== 右键菜单 =================================
const contextMenuRef = ref(null);
const handleRightClick = (event: any) => {
  console.log(event);
  // 暂时不使用右键菜单
  // event.preventDefault();
  // contextMenuRef.value.show(event);
};

const handleContextMenuClick = (event: MenuClickEvent) => {
  console.log(event);
};
// =========================== 批量操作 ==========================
// 批量设置账号uid
const handleBatchSetUid = () => {
  ElMessageBox.prompt("请输入要设置的账号尾缀：", "账号设置", {
    inputValue: "",
    inputType: "number",
    inputPlaceholder: "请输入账号尾缀",
    inputValidator: val => {
      if (
        Number(val) >= info.value.account_num_min &&
        Number(val) <= info.value.account_num_max
      ) {
        return true;
      }
      return `账号尾缀值超出范围！请输入${info.value.account_num_min}~${info.value.account_num_max}之间的数字`;
    }
  }).then(({ value }) => {
    const uid = Number(value);
    checkedCases.value.forEach(item => {
      item.uid = uid;
      item.checked = false; // 清除选中状态
    });
  });
};

const handleBatchDelete = () => {
  // 倒序遍历 info.value.case_queue 以避免删除时索引错乱
  for (let i = info.value.case_queue.length - 1; i >= 0; i--) {
    const block = info.value.case_queue[i];
    for (let j = block.length - 1; j >= 0; j--) {
      if (block[j].checked) {
        block.splice(j, 1);
      }
    }
    // 如果执行组为空，则删除该组
    if (block.length === 0) {
      info.value.case_queue.splice(i, 1);
    }
  }
};

// =========================== 账号填充 ==========================
const handleFillingAccount = (command: string) => {
  switch (command) {
    case "all_sequential":
      // 全量顺序填充
      allSequentialFill();
      break;
    case "group_sequential":
      // 组内顺序填充
      groupSequentialFill();
      break;
  }
};

const allSequentialFill = () => {
  if (!info.value.account_num_min) {
    info.value.account_num_min = 1;
  }
  info.value.account_num_max =
    info.value.account_num_min + totalCases.value - 1;
  let num = info.value.account_num_min;
  info.value.case_queue.forEach(block => {
    block.forEach(item => {
      item.uid = num;
      num++;
    });
  });
  message("账号已填充！", { type: "success" });
};

const groupSequentialFill = () => {
  if (!info.value.account_num_min) {
    info.value.account_num_min = 1;
  }
  const maxGroupCasesLen = info.value.case_queue.reduce((max, block) => {
    return Math.max(max, block.length);
  }, 0);
  info.value.account_num_max =
    info.value.account_num_min + maxGroupCasesLen - 1;
  info.value.case_queue.forEach(block => {
    let num = 1;
    block.forEach(item => {
      item.uid = num;
      num++;
    });
  });
  message("账号已填充！", { type: "success" });
};

// =========================== 用例编辑器 =========================
const editorVisible = ref(false);
const editorRef = ref(null);
const handleCaseEdit = (item: CaseQueueItem) => {
  console.log(item);
  // 打开用例编辑器
  editorVisible.value = true;
  editorRef.value?.refresh(item.case_base_id, item.selectedVersion);
};

// =========================== 用例选择器 =========================

const testcaseSelectorRef = ref(null);
const scrollRef = ref(null);

/**
 * 在case_queue 的指定位置插入元素
 * @param position 插入位置配置
 * @returns 新数组
 */
function insertBlock(
  position:
    | { type: "end" } // 插入到末尾
    | { type: "start" } // 插入到开头
    | {
        type: "before" | "after";
        index: number; // 在指定索引的前/后插入
      }
) {
  const newItem = [];
  switch (position.type) {
    case "end":
      info.value.case_queue.push(newItem);
      scrollToBlock(info.value.case_queue.length - 1);
      break;

    case "start":
      info.value.case_queue.unshift(newItem);
      scrollToBlock(0);
      break;

    case "before":
      if (
        position.index >= 0 &&
        position.index <= info.value.case_queue.length
      ) {
        info.value.case_queue.splice(position.index, 0, newItem);
      } else {
        console.warn(`Index ${position.index} out of bounds, inserting at end`);
        info.value.case_queue.push(newItem);
      }
      scrollToBlock(position.index);
      break;

    case "after":
      if (
        position.index >= -1 &&
        position.index < info.value.case_queue.length
      ) {
        info.value.case_queue.splice(position.index + 1, 0, newItem);
      } else {
        console.warn(`Index ${position.index} out of bounds, inserting at end`);
        info.value.case_queue.push(newItem);
      }
      scrollToBlock(position.index + 1);
      break;
  }
}

// 滚动到指定索引的 BLOCK
const scrollToBlock = (index: number) => {
  if (info.value.case_queue?.[index]) {
    let totalHeight = 0;
    const caseRowHeight = 215;
    for (let i = 0; i <= index; i++) {
      const blockCasesCount = info.value.case_queue[i].length || 0;
      totalHeight += Math.floor(blockCasesCount / 4) * caseRowHeight + 80;
    }
    nextTick(() => {
      scrollRef.value?.scrollTo({
        top: totalHeight,
        behavior: "smooth"
      });
    });
  }
};

const handleBlockCommand = (command: { type: string; index: number }) => {
  switch (command.type) {
    case "delete":
      deleteBlock(command.index);
      return;
    case "insertBefore":
      insertBlock({ type: "before", index: command.index });
      return;
    case "insertAfter":
      insertBlock({ type: "after", index: command.index });
      return;
    default:
      break;
  }
};

const deleteBlock = (index: number) => {
  store.REMOVE_FROM_CASE_QUEUE(index);
};

const activeIndex = ref(-1);
// 【新增用例】：打开用例选择器
const handleOpenSelector = (index: number) => {
  testcaseSelectorRef.value?.show(store.info.env);
  activeIndex.value = index;
};

const newCaseQueueItem = (item: any): CaseQueueItem => {
  return {
    case_base_id: item.case_base_id || item.id,
    version: item.version,
    selectedVersion: item.selectedVersion || item.version,
    name: item.name,
    version_list: store.GET_VERSION_LIST(item.version),
    account: "",
    password: "",
    nick_name: "",
    block_index: -1,
    inner_index: -1, // 初始为0，后续可根据实际情况调整
    checked: false
  };
};

// 【用例选择完成】：添加到CASE_QUEUE中渲染显示
const handleConfirm = (selected: any[], mode: string) => {
  if (mode === caseInsertModeEnum.SAME_GROUP.value) {
    if (activeIndex.value === -1) {
      info.value.case_queue.push([
        ...selected.map(item => newCaseQueueItem(item))
      ]);
    }
    // 在当前执行组中添加用例
    if (info.value.case_queue[activeIndex.value]) {
      info.value.case_queue[activeIndex.value].push(
        ...selected.map(item => newCaseQueueItem(item))
      );
    }
  } else if (mode === caseInsertModeEnum.SEPARATE_GROUP.value) {
    if (activeIndex.value === -1) {
      activeIndex.value = info.value.case_queue?.length
        ? info.value.case_queue.length - 1
        : 0;
    }
    // 向当前 activeIndex 位置插入 n 个执行组，每个组中添加一个用例
    selected.forEach((item, idx) => {
      info.value.case_queue.splice(activeIndex.value + idx + 1, 0, [
        newCaseQueueItem(item)
      ]);
    });
  }
};
</script>

<template>
  <el-container class="h-full border-gray-200 border-r">
    <el-header class="pt-2">
      <div
        class="mt-2 flex items-center p-8 bg-slate-100 dark:bg-transparent rounded-lg w-full h-12"
      >
        <!-- 基本信息 -->
        <div class="flex items-center">
          <el-icon size="22">
            <Guide />
          </el-icon>
          <span class="text-lg font-bold ml-2 text-gray-600 dark:text-white">
            用例编排： 客户端
            <span class="text-blue-500">
              {{ totalClients }}
            </span>
            个，用例
            <span class="text-blue-500">
              {{ totalCases }}
            </span>
            个
          </span>
          <el-divider direction="vertical" />
        </div>
        <!-- 批量操作 -->
        <div class="flex items-center ml-4">
          <div class="flex items-center">
            <el-checkbox
              class="scale-110"
              v-model="checkAll"
              :indeterminate="
                checkedCases.length > 0 && checkedCases.length < totalCases
              "
              @change="handleCheckChange"
            >
              全选
            </el-checkbox>
          </div>
          <el-button-group class="ml-4" v-if="checkedCases.length > 0">
            <el-button @click="handleBatchSetUid" type="primary" plain>
              设置账号({{ checkedCases.length || 0 }})
            </el-button>
            <el-button @click="handleBatchDelete" type="primary" plain>
              删除已选({{ checkedCases.length || 0 }})
            </el-button>
          </el-button-group>
        </div>
        <!-- 账号填充 -->
        <div class="flex flex-wrap items-center ml-auto">
          <el-dropdown @command="handleFillingAccount">
            <el-button type="warning" plain>
              账号自动填充
              <el-icon class="el-icon--right"><arrow-down /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="all_sequential">
                  全部顺序填充
                </el-dropdown-item>
                <el-dropdown-item command="group_sequential">
                  每组顺序填充
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </el-header>
    <el-main v-loading="state.detailLoading" class="pr-10">
      <el-scrollbar ref="scrollRef">
        <el-empty
          class="mt-12"
          v-if="!info.case_queue?.length"
          description="尚未在测试计划中添加任何用例"
        />
        <draggable
          :list="info.case_queue"
          item-key="id"
          chosen-class="chosen"
          force-fallback="true"
          animation="300"
          handle=".blockHandle"
        >
          <template #item="{ element, index }">
            <div
              class="w-full block-container cursor-pointer mb-3 min-h-[230px]"
            >
              <!-- A. 操作栏 -->
              <div
                class="w-full h-[40px] bg-slate-100 flex items-center select-none"
              >
                <!-- a1. 拖拽图标 -->
                <div
                  v-if="canEdit"
                  class="blockHandle px-2 flex justify-center items-center cursor-move"
                >
                  <el-icon size="22">
                    <DragIcon />
                  </el-icon>
                </div>
                <!-- a2. 组序号 -->
                <div class="font-base font-semibold text-slate-800">
                  {{ `◽ 执行组 - ${index + 1}` }}
                </div>
                <!-- a3. 操作 -->
                <div class="ml-auto flex items-center">
                  <el-button
                    type="text"
                    :disabled="!canEdit"
                    title="添加用例"
                    plain
                    @click="handleOpenSelector(index)"
                  >
                    <el-icon size="16" color="text-slate-600">
                      <Plus />
                    </el-icon>
                  </el-button>
                  <el-dropdown placement="bottom" @command="handleBlockCommand">
                    <el-button
                      class="mx-3"
                      type="text"
                      :disabled="!canEdit"
                      plain
                    >
                      <el-icon size="16" color="text-slate-600">
                        <MoreFilled />
                      </el-icon>
                    </el-button>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item
                          :command="{ type: 'insertBefore', index: index }"
                          >上方插入组</el-dropdown-item
                        >
                        <el-dropdown-item
                          :command="{ type: 'insertAfter', index: index }"
                          >下方插入组</el-dropdown-item
                        >
                        <el-dropdown-item
                          :command="{ type: 'delete', index: index }"
                        >
                          删除执行组
                        </el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </div>
              </div>

              <!-- B. 用例组 -->
              <div class="w-full p-3 bg-slate-50 dark:bg-black/20">
                <draggable
                  class="flex flex-wrap gap-1"
                  :list="element"
                  item-key="id"
                  chosen-class="chosen"
                  force-fallback="true"
                  animation="300"
                  handle=".caseHandle"
                  group="same-group"
                >
                  <template #item="{ element: caseItem, index: caseIndex }">
                    <CaseCard
                      class="m-2"
                      :item="caseItem"
                      :block-index="index"
                      :inner-index="caseIndex"
                      :can-edit="canEdit"
                      :min="info.account_num_min"
                      :max="info.account_num_max"
                      @edit="handleCaseEdit"
                      @contextmenu="handleRightClick"
                    />
                  </template>
                </draggable>
              </div>
            </div>
          </template>
        </draggable>
        <div class="my-5 flex justify-center">
          <el-button
            v-if="false"
            type="primary"
            :icon="CirclePlusFilled"
            size="large"
            plain
            @click="insertBlock({ type: 'end' })"
          >
            添加执行组
          </el-button>
          <el-button
            v-if="canEdit"
            type="primary"
            :icon="CirclePlusFilled"
            size="large"
            plain
            @click="handleOpenSelector(-1)"
          >
            添加用例
          </el-button>
        </div>
      </el-scrollbar>
    </el-main>
    <!-- 右键菜单 -->
    <ArrangerContextMenu
      v-if="false"
      ref="contextMenuRef"
      @menu-click="handleContextMenuClick"
    />
    <!-- 用例选择器 -->
    <TestPlanCaseSelector
      v-if="canEdit"
      ref="testcaseSelectorRef"
      @complete="handleConfirm"
    />
    <!-- 用例编辑器 -->
    <TestcaseEditor ref="editorRef" v-model="editorVisible" />
  </el-container>
</template>
<style lang="scss" scoped>
.chosen {
  background-color: #f5f5f5;
  border: dashed 1px #dae8ff !important;
  border-radius: 10px;
  font-size: bold;
}

.block-container {
  @apply border border-gray-200 shadow-sm rounded-md overflow-hidden;
}
</style>
