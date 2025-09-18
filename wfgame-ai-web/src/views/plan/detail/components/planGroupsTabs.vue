<script setup lang="ts">
import { defineOptions, onMounted } from "vue";
import { plansGroupsConfig } from "../utils/planGroupsHook";
import { hasAuth } from "@/router/utils";
import { perms } from "@/utils/permsCode";
import { usePlanStoreHook } from "@/store/modules/plan";

defineOptions({
  name: "PlanGroupsTabs"
});

const { editableTabs, editableTabsValue, handleTabsEdit, handleTabsChange } =
  plansGroupsConfig();
const store = usePlanStoreHook();
onMounted(() => {
  handleTabsChange({ paneName: editableTabsValue.value }); // 初始化时触发一次，默认选择并发组
});
</script>

<template>
  <el-tabs
    v-model="editableTabsValue"
    type="card"
    :editable="!(!hasAuth(perms.plan.detail.writable) || store.info.id)"
    class="group-tabs"
    @edit="handleTabsEdit"
    @tab-click="handleTabsChange"
  >
    <el-tab-pane
      v-for="item in editableTabs"
      :key="item.name"
      :label="item.title"
      :name="item.name"
      :closable="item.closable"
    />
  </el-tabs>
</template>

<style scoped lang="scss">
.group-tabs {
  width: 100%;
}

.group-tabs:deep(.el-tabs__header) {
  margin-bottom: 0; /* 用于减少或消除头部与内容之间的空间 */
}

.group-tabs:deep(.el-tabs__content) {
  padding: 0px;
  color: #6b778c;
  font-size: 32px;
  font-weight: 600;
  margin-top: 0; /* 确保内容部分顶部不额外空出空间 */
}
</style>
