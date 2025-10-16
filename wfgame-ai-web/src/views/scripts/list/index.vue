<script setup lang="ts">
import { Operation } from "@element-plus/icons-vue";
import CategorySelector from "@/views/scripts/list/components/categorySelector.vue";
import CategoryEditorDialog from "@/views/common/editor/categoryEditor/dialog.vue";
import ScriptListTable from "@/views/scripts/list/components/scriptListTable.vue";
import { ref, nextTick } from "vue";
import { useScriptStore } from "@/store/modules/script";
import { storeToRefs } from "pinia";

const store = useScriptStore();
const { components } = storeToRefs(store);

defineOptions({
  name: "ScriptList"
});
const ScriptListTableRef = ref();
const categorySelectorRef = ref();

const onSelectorChanged = (newVal, catalogPath) => {
  nextTick(() => {
    ScriptListTableRef.value?.onQueryChanged(newVal?.id || null, "category");
    ScriptListTableRef.value?.setCatalogPath(catalogPath || []);
  });
};
const onReset = () => {
  categorySelectorRef.value?.setCurrent(null);
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
          <h3 class="text-info text-center">脚本管理</h3>
        </template>
        <template #default>
          <CategorySelector
            ref="categorySelectorRef"
            @changed="onSelectorChanged"
          />
        </template>
        <template #footer>
          <div class="w-full">
            <el-button
              class="w-full mb-2 mt-3"
              :icon="Operation"
              size="large"
              @click="components.showCategoryEditor = true"
              >目录管理</el-button
            >
          </div>
        </template>
      </el-card>
    </el-aside>
    <el-main style="padding: 0 0 0 10px">
      <ScriptListTable
        select-mode="multiple"
        class="w-full h-full"
        ref="ScriptListTableRef"
        @reset="onReset"
      />
    </el-main>
    <CategoryEditorDialog v-model="components.showCategoryEditor" />
  </el-container>
</template>
<style>
.category-card .el-card__footer {
  padding-top: 0;
  padding-bottom: 0;
}
</style>
