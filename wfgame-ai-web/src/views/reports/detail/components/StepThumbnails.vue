<script setup lang="ts">
import { ref, watch, nextTick, computed } from "vue";
import type { FlatStep } from "../utils/types";
import { formatRelativeTime } from "@/utils/format";
import { Picture, CameraFilled } from "@element-plus/icons-vue";

interface Props {
  steps: FlatStep[];
  selectedIndex: number;
}

const props = defineProps<Props>();

// 获取起始时间（第一个步骤的开始时间）
const startTime = computed(() => {
  return props.steps[0]?.step.result?.start_time || 0;
});

const emit = defineEmits<{
  (e: "update:selectedIndex", index: number): void;
}>();

defineOptions({
  name: "StepThumbnails"
});

const scrollbarRef = ref();
const thumbnailRefs = ref<HTMLElement[]>([]);

// 设置缩略图引用
const setThumbnailRef = (el: any, index: number) => {
  if (el) {
    thumbnailRefs.value[index] = el;
  }
};

// 选择步骤
const selectStep = (index: number) => {
  emit("update:selectedIndex", index);
};

// 监听选中索引变化，自动滚动到对应位置
watch(
  () => props.selectedIndex,
  async newIndex => {
    await nextTick();
    if (thumbnailRefs.value[newIndex]) {
      thumbnailRefs.value[newIndex].scrollIntoView({
        behavior: "smooth",
        block: "nearest",
        inline: "center"
      });
    }
  }
);
</script>

<template>
  <el-card shadow="never" class="thumbnails-card">
    <template #header>
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <el-icon :size="20" color="#409eff">
            <CameraFilled />
          </el-icon>
          <span class="text-lg font-semibold">步骤快览</span>
        </div>
        <span class="text-sm text-gray-500">
          共 {{ steps.length }} 个步骤
        </span>
      </div>
    </template>

    <el-scrollbar ref="scrollbarRef" class="thumbnails-scrollbar">
      <div class="thumbnails-container">
        <div
          v-for="(item, index) in steps"
          :key="index"
          :ref="el => setThumbnailRef(el, index)"
          class="thumbnail-item"
          :class="{
            selected: index === selectedIndex,
            error: item.step.result?.status === 'failed',
            success: item.step.result?.status === 'success'
          }"
          @click="selectStep(index)"
        >
          <div class="thumbnail-wrapper">
            <el-image
              v-if="item.step.result?.oss_pic_pth"
              :src="item.step.result.oss_pic_pth"
              fit="cover"
              class="thumbnail-image"
              :preview-src-list="[item.step.result.oss_pic_pth]"
              :initial-index="0"
              hide-on-click-modal
            >
              <template #error>
                <div class="image-error">
                  <el-icon><Picture /></el-icon>
                  <span>加载失败</span>
                </div>
              </template>
            </el-image>
            <div v-else class="thumbnail-placeholder">
              <el-icon><Picture /></el-icon>
              <span>无图片</span>
            </div>

            <div
              class="thumbnail-index"
              :class="{
                'index-success': item.step.result?.status === 'success',
                'index-failed': item.step.result?.status === 'failed'
              }"
            >
              {{ item.globalIndex }}
            </div>
          </div>

          <div class="thumbnail-time">
            {{ formatRelativeTime(item.step.result?.start_time, startTime) }}
          </div>
        </div>
      </div>
    </el-scrollbar>
  </el-card>
</template>

<style scoped lang="scss">
.thumbnails-card {
  :deep(.el-card__body) {
    padding: 12px;
  }
}

.thumbnails-scrollbar {
  height: 210px;
}

.thumbnails-container {
  display: flex;
  gap: 6px;
  padding: 4px;
}

.thumbnail-item {
  flex-shrink: 0;
  width: 90px;
  cursor: pointer;
  border: 2px solid transparent;
  border-radius: 6px;
  padding: 4px;
  transition: all 0.3s;

  &:hover {
    border-color: #409eff;
    transform: translateY(-2px);
    box-shadow: 0 2px 8px rgba(64, 158, 255, 0.3);
  }

  &.selected {
    border-color: #409eff;
    background-color: #ecf5ff;
  }
}

.thumbnail-wrapper {
  position: relative;
  width: 100%;
  height: 160px;
  border-radius: 4px;
  overflow: hidden;
  background-color: #f5f7fa;
}

.thumbnail-image {
  width: 100%;
  height: 100%;

  :deep(.el-image__inner) {
    width: 100%;
    height: 100%;
  }
}

.thumbnail-placeholder,
.image-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  color: #909399;
  font-size: 12px;

  .el-icon {
    font-size: 24px;
    margin-bottom: 4px;
  }
}

.thumbnail-index {
  position: absolute;
  top: 4px;
  left: 4px;
  background-color: rgba(0, 0, 0, 0.6);
  color: white;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 12px;
  font-weight: bold;
  transition: background-color 0.3s;

  &.index-success {
    background-color: #67c23a;
  }

  &.index-failed {
    background-color: #f56c6c;
  }
}

.thumbnail-time {
  margin-top: 4px;
  text-align: center;
  font-size: 12px;
  color: #606266;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
