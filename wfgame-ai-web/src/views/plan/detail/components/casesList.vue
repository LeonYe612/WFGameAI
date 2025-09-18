<script setup lang="ts">
import draggable from "vuedraggable";
import { Guide, CirclePlusFilled } from "@element-plus/icons-vue";
import { ref, computed } from "vue";
import { Delete } from "@element-plus/icons-vue";
import DragIcon from "@/assets/svg/drag.svg?component";
import { usePlanStoreHook } from "@/store/modules/plan";
import TestPlanCaseSelector from "@/views/common/selectors/testPlanCasesSelector/index.vue";
import { perms } from "@/utils/permsCode";
import { hasAuth } from "@/router/utils";
import { planRunTypeEnum } from "@/utils/enums";
const store = usePlanStoreHook();
const list = store.info.case_queue;
const state = store.shareState;

defineOptions({
  name: "PlanCasesList"
});

// 是否有编辑权限
const canEdit = computed(() => {
  return (
    hasAuth(perms.plan.detail.writable) &&
    (!store.info.id || store.info.run_type === planRunTypeEnum.WEBHOOK.value)
  );
});

const testcaseSelectorRef = ref(null);
const scrollRef = ref(null);

// 【新增用例】：打开用例选择器
const handleAdd = () => {
  testcaseSelectorRef.value?.show(store.info.env);
};

// 【用例选择完成】：添加到CASE_QUEUE中渲染显示
const handleConfirm = (selected: any[]) => {
  store.ADD_TO_CASE_QUEUE(selected);
};
</script>

<template>
  <el-container class="h-full border-gray-200 border-r">
    <el-header class="pt-2">
      <div
        class="mt-2 flex items-center p-8 bg-slate-100 dark:bg-transparent rounded-lg w-full h-12"
      >
        <div class="flex items-center w-full">
          <el-icon size="22">
            <Guide />
          </el-icon>
          <span class="text-lg font-bold ml-2 text-gray-600 dark:text-white">
            测试计划中的用例 （共
            <span class="text-blue-500">{{ list?.length || 0 }}</span> 个）
          </span>
          <el-button
            v-if="canEdit"
            class="ml-auto"
            type="primary"
            :icon="CirclePlusFilled"
            size="large"
            @click="handleAdd"
          >
            添加用例
          </el-button>
        </div>
      </div>
    </el-header>
    <el-main v-loading="state.detailLoading">
      <el-scrollbar class="h-full" ref="scrollRef">
        <el-empty
          class="mt-12"
          v-if="!list || list.length === 0"
          description="尚未在测试计划中添加任何用例"
        />
        <!-- 单列拖拽 -->
        <draggable
          v-else
          :list="list"
          item-key="id"
          chosen-class="chosen"
          force-fallback="true"
          animation="300"
          handle=".stepHandle"
        >
          <template #item="{ element, index }">
            <div class="p-1 cursor-pointer" style="height: 80px">
              <div
                class="h-full border border-gray-200 shadow-sm rounded-md flex justify-start items-center"
              >
                <!-- 拖拽图标 -->
                <div
                  v-if="canEdit"
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
                <!-- 用例名称 -->
                <div
                  class="ml-4 flex-1 h-full flex items-start flex-col justify-center overflow-hidden"
                >
                  <span
                    v-if="element.name"
                    class="text-gray-600 dark:text-white text-base max-w-full whitespace-nowrap overflow-hidden overflow-ellipsis"
                  >
                    {{ element.name }}
                  </span>
                  <span
                    v-else
                    class="text-red-500 text-base max-w-full whitespace-nowrap overflow-hidden overflow-ellipsis"
                  >
                    用例({{ element.case_base_id }})已被删除, 请注意移除
                  </span>
                </div>
                <!-- 操作 -->
                <div class="h-full ml-auto flex items-center mr-3">
                  <!-- 最新版标记 -->
                  <el-tooltip
                    v-if="element.selectedVersion !== element.version"
                    content="请注意：当前选择用例非最新版本！"
                    effect="dark"
                    placement="top"
                  >
                    <IconifyIconOnline
                      class="text-yellow-500 mr-1"
                      style="width: 26px; height: 26px"
                      icon="ph:seal-warning-duotone"
                    />
                  </el-tooltip>

                  <!-- 版本变更 -->
                  <el-select
                    :disabled="!canEdit"
                    class="mr-4"
                    size="large"
                    v-model="element.selectedVersion"
                    placeholder="版本选择"
                    style="width: 120px"
                  >
                    <el-option
                      v-for="item in store.GET_VERSION_LIST(element)"
                      :key="item.value"
                      :label="item.label"
                      :value="item.value"
                    />
                  </el-select>
                  <!-- 编辑按钮 -->
                  <el-popconfirm
                    v-if="hasAuth(perms.plan.detail.writable)"
                    title="是否确认删除?"
                    @confirm="store.REMOVE_FROM_CASE_QUEUE(index)"
                  >
                    <template #reference>
                      <el-button
                        :disabled="!canEdit"
                        title="移除用例"
                        :icon="Delete"
                        circle
                        plain
                        type="danger"
                      />
                    </template>
                  </el-popconfirm>
                </div>
              </div>
            </div>
          </template>
        </draggable>
      </el-scrollbar>
    </el-main>
    <!-- 用例选择器 -->
    <TestPlanCaseSelector
      v-if="canEdit"
      ref="testcaseSelectorRef"
      @complete="handleConfirm"
    />
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
.chosen {
  background-color: #f5f5f5;
  border: dashed 1px #dae8ff !important;
  border-radius: 10px;
  font-size: bold;
}
</style>
