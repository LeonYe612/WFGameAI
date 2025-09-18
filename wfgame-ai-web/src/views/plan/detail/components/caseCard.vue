<template>
  <div
    @click="handelToggleChecked"
    class="w-[240px] h-48 flex flex-col flex-shrink-0 select-none rounded-lg overflow-hidden shadow-sm cursor-pointer border"
    :class="{
      'border-primary shadow-lg bg-blue-50 dark:bg-slate-700': itemRef.checked,
      'border-gray-200 hover:border-primary hover:shadow-md bg-white dark:bg-slate-800':
        !itemRef.checked
    }"
  >
    <!-- 卡片头部 -->
    <div
      class="p-2 border-b border-gray-200/80 dark:border-slate-700/80 transition-colors duration-300"
    >
      <div class="flex items-center gap-x-2">
        <!-- 拖拽图标 -->
        <div
          class="caseHandle flex justify-center items-center cursor-move text-gray-400 hover:text-primary"
        >
          <el-icon size="18">
            <DragIcon />
          </el-icon>
        </div>
        <!-- 用例Id -->
        <span class="text-xs font-semibold text-gray-400">
          ID: {{ item.case_base_id }}
        </span>
        <!-- 版本变更 -->
        <el-select
          :disabled="!canEdit"
          class="ml-auto"
          v-model="itemRef.selectedVersion"
          size="small"
          placeholder="版本号"
          style="width: 80px"
        >
          <el-option
            v-for="option in store.GET_VERSION_LIST(item)"
            :key="option.value"
            :label="option.label"
            :value="option.value"
          />
        </el-select>
        <!-- 复制按钮 -->
        <el-button
          :disabled="!canEdit"
          type="info"
          size="small"
          circle
          plain
          :icon="CopyDocument"
          @click.stop="handleCopy"
        />
        <!-- 删除按钮 -->
        <el-button
          style="margin-left: 0.25rem"
          :disabled="!canEdit"
          type="danger"
          size="small"
          circle
          plain
          :icon="Close"
          @click.stop="handleDelete"
        />
      </div>
    </div>

    <!-- 卡片主体 -->
    <div class="p-3 flex-1 h-0 flex items-center justify-center">
      <div class="w-full text-center">
        <p
          class="name-text text-base font-semibold text-gray-800 dark:text-gray-200"
          :class="{ 'hover:text-primary hover:underline': canEdit }"
          @click.stop="canEdit && handleEdit()"
        >
          {{ itemRef.name }}
        </p>
      </div>
    </div>

    <!-- 卡片底部 -->
    <div
      class="p-2 border-t border-gray-200/80 dark:border-slate-700/80 w-full transition-colors duration-300"
      v-if="showFooter"
    >
      <div class="flex items-center justify-between">
        <!-- UID Display -->
        <div
          class="w-[100px] rounded p-1 flex items-center justify-center flex-shrink-0 shadow-md"
          :style="`background-color: ${color}`"
        >
          <span class="text-white text-xs font-bold mr-1">
            {{ itemRef.uid ? `Client ${itemRef.uid}` : "❔" }}
          </span>
        </div>
        <!-- UID Input -->
        <div @click.stop>
          <el-input-number
            v-model="itemRef.uid"
            :min="min"
            :max="max"
            size="small"
            controls-position="right"
            style="width: 88px"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { CaseQueueItem } from "@/store/types";
import { defineProps, computed, defineEmits } from "vue";
import { usePlanStoreHook } from "@/store/modules/plan";
import { storeToRefs } from "pinia";
import DragIcon from "@/assets/svg/drag.svg?component";
import { Close, CopyDocument } from "@element-plus/icons-vue";
import { getColorByIndex } from "@/store/types";

const store = usePlanStoreHook();
const { info } = storeToRefs(store);

defineOptions({
  name: "CaseCard"
});

const emit = defineEmits(["edit"]);

const props = defineProps({
  item: {
    type: Object as () => CaseQueueItem,
    required: true
  },
  blockIndex: {
    type: Number,
    default: 0
  },
  innerIndex: {
    type: Number,
    default: 0
  },
  showFooter: {
    type: Boolean,
    default: true
  },
  canEdit: {
    type: Boolean,
    default: false
  },
  min: {
    type: Number,
    default: 1
  },
  max: {
    type: Number,
    default: 1
  }
});

const itemRef = computed({
  get: () => {
    // 为 item 填充 checked 和 selectedVersion
    // return {
    //   ...props.item,
    //   selectedVersion: props.item.selectedVersion || props.item.version || 1,
    //   checked: props.item.checked || false
    // };
    return props.item;
  },
  set: value => {
    info.value.case_queue[props.blockIndex][props.innerIndex] = value;
  }
});

const color = computed(() => {
  return itemRef.value.uid ? getColorByIndex(itemRef.value.uid) : "#DCDFE6";
});

const handleEdit = () => {
  emit("edit", itemRef.value);
};

const handelToggleChecked = () => {
  itemRef.value.checked = !itemRef.value.checked;
};

const handleDelete = () => {
  if (!info.value.case_queue[props.blockIndex]) return;
  info.value.case_queue[props.blockIndex].splice(props.innerIndex, 1);
  if (info.value.case_queue[props.blockIndex].length === 0) {
    info.value.case_queue.splice(props.blockIndex, 1);
  }
};

const handleCopy = () => {
  const newItem = { ...itemRef.value };
  newItem.checked = false; // 默认不选中
  newItem.selectedVersion = newItem.version || 1; // 保持版本号一致
  info.value.case_queue[props.blockIndex].splice(
    props.innerIndex + 1,
    0,
    newItem
  );
};
</script>

<style scoped>
.name-text {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
