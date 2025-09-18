<script setup lang="ts">
defineOptions({
  name: "PlaceholderSettings"
});

defineProps<{
  title: string;
  icon: string;
  description?: string;
}>();
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <div class="card-header">
        <el-icon><component :is="icon" /></el-icon>
        <span class="header-title">{{ title }}</span>
      </div>
    </template>

    <div class="placeholder-content">
      <el-empty
        :description="description || `${title}功能正在开发中，敬请期待...`"
        :image-size="120"
      />
    </div>
  </el-card>
</template>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  font-weight: 500;
}

.header-title {
  margin-left: 8px;
}

.placeholder-content {
  padding: 40px 0;
}
</style>
