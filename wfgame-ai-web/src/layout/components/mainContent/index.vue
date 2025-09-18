<script setup lang="ts">
import ActiveTeamInfo from "@/views/common/display/activeTeamInfo.vue";

defineOptions({
  name: "MainContent"
});

defineProps({
  title: {
    type: String,
    default: "页面标题"
  },
  showHeader: {
    type: Boolean,
    default: true
  },
  showTeamInfo: {
    type: Boolean,
    default: true
  },
  scrollMode: {
    type: Boolean,
    default: false
  }
});
</script>

<template>
  <el-card class="h-full-content content-card" shadow="never">
    <!-- Card-Header -->
    <template #header v-if="showHeader">
      <ActiveTeamInfo :title="title" v-if="showTeamInfo">
        <!-- 预留 header 插槽 -->
        <slot name="header-extra" />
      </ActiveTeamInfo>
      <slot name="custom-header" />
    </template>
    <!-- Card Body -->
    <template #default>
      <el-scrollbar class="flex-1-scrollbar" v-if="scrollMode">
        <slot />
      </el-scrollbar>
      <div class="flex-1-container" v-else>
        <slot />
      </div>
    </template>
    <!-- Card Footer -->
    <template #footer v-if="$slots.footer">
      <slot name="footer" />
    </template>
  </el-card>
</template>
<style scoped lang="scss">
.content-card {
  display: flex;
  flex-direction: column;
  // 确保 card 占据全部高度
  :deep() .el-card__body {
    flex: 1;
    min-height: 0; // 重要：允许 flex 项目缩小
    display: flex; // 让 card body 也成为 flex 容器
    flex-direction: column; // 垂直排列子元素
  }

  :deep() .el-table__inner-wrapper {
    height: 100% !important;
  }
}

// 滚动容器样式
.flex-1-scrollbar {
  flex: 1;
  min-height: 0;
}

// 非滚动容器样式
.flex-1-container {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
</style>
