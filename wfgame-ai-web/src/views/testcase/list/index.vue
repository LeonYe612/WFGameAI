<script setup lang="ts">
import { Operation } from "@element-plus/icons-vue";
import CatalogTreeTableSelector from "@/views/testcase/list/components/catalogSelector.vue";
import CaselistTable from "@/views/testcase/list/components/caseListTable.vue";
import { ref, nextTick } from "vue";
import { useNavigate } from "@/views/common/utils/navHook";

defineOptions({
  name: "TestCaseList"
});
const caseListTableRef = ref();
const catalogSelectorRef = ref();
const { navigateToCatalog } = useNavigate();

const onSelectorChanged = (newVal, catalogPath) => {
  nextTick(() => {
    caseListTableRef.value?.onQueryChanged(newVal?.id || null, "catalog_id");
    caseListTableRef.value?.setCatalogPath(catalogPath || []);
  });
};
const onReset = () => {
  catalogSelectorRef.value?.setCurrent(null);
};
</script>

<template>
  <el-container class="h-full-content">
    <el-aside width="20vw">
      <el-card
        class="category-card h-full cursor-pointer flex flex-col"
        shadow="never"
        body-class="flex-1 overflow-hidden"
      >
        <template #header>
          <h3 class="text-info text-center">用例目录</h3>
        </template>
        <template #default>
          <CatalogTreeTableSelector
            ref="catalogSelectorRef"
            @changed="onSelectorChanged"
          />
        </template>
        <template #footer>
          <div class="w-full">
            <el-button
              class="w-full mb-2 mt-3"
              :icon="Operation"
              size="large"
              @click="navigateToCatalog"
              >目录管理</el-button
            >
          </div>
        </template>
      </el-card>
    </el-aside>
    <el-main style="padding: 0 0 0 10px">
      <CaselistTable
        class="w-full h-full"
        ref="caseListTableRef"
        @reset="onReset"
      />
    </el-main>
  </el-container>
</template>
<style>
.category-card .el-card__footer {
  padding-top: 0;
  padding-bottom: 0;
}
</style>
