<template>
  <MainContent title="测试报告">
    <template #header-extra>
      <el-row class="items-center justify-between">
        <div class="flex ml-auto">
          <div class="w-40 mr-2">
            <el-select
              v-model="queryForm.status"
              placeholder="报告状态"
              clearable
              @change="onQueryChanged($event, 'status')"
            >
              <el-option label="生成中" value="generating" />
              <el-option label="已完成" value="completed" />
              <el-option label="失败" value="failed" />
            </el-select>
          </div>
          <div class="w-72 mr-2">
            <el-input
              v-model="queryForm.keyword"
              placeholder="搜索报告名称..."
              clearable
              :prefix-icon="Search"
              @change="onQueryChanged($event, 'keyword')"
            />
          </div>
          <el-button type="default" :icon="Refresh" @click="handleResetQuery">
            重置
          </el-button>
        </div>
      </el-row>
    </template>

    <ReportsTable ref="reportsTableRef" />
  </MainContent>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick, watch } from "vue";
import { Search, Refresh } from "@element-plus/icons-vue";
import MainContent from "@/layout/components/mainContent/index.vue";
import ReportsTable from "./components/reportsTable.vue";
import { useNavigate } from "@/views/common/utils/navHook";
const { getParameter } = useNavigate();

// 页面标题
defineOptions({
  name: "ReportsPage"
});

const reportsTableRef = ref();

// 从子组件获取 queryForm 和相关方法
const queryForm = computed(() => reportsTableRef.value?.queryForm || {});
const handleResetQuery = () => reportsTableRef.value?.handleResetQuery();

// 查询条件变更
const onQueryChanged = (value: any, key: string) => {
  if (reportsTableRef.value) {
    reportsTableRef.value.onQueryChanged(value, key);
  }
};

// 页面加载时检查 URL 参数，自动查询并打开对应报告
const openReportByUrlParam = async () => {
  const id = getParameter.id || "";
  if (!id) return;
  const reportId = Number(id);
  if (isNaN(reportId) || reportId === 0) return;

  // 等待 reportsTableRef 挂载并加载完成
  await nextTick();

  if (reportsTableRef.value) {
    reportsTableRef.value.queryForm.keyword = `id=${reportId}`;
    await reportsTableRef.value.fetchData();
    // 等待 DOM 更新后再查找并点击行
    await nextTick();
    reportsTableRef.value.findAndClickRowById(reportId);
  }
};

onMounted(() => {
  // 使用 watch 监听 reportsTableRef，确保组件已加载
  let unwatch: (() => void) | null = null;
  unwatch = watch(
    () => reportsTableRef.value,
    newVal => {
      if (newVal) {
        openReportByUrlParam();
        if (unwatch) {
          unwatch(); // 执行一次后取消监听
        }
      }
    },
    { immediate: true }
  );
});
</script>

<style scoped>
/* 页面级别样式可以在这里定义 */
</style>
