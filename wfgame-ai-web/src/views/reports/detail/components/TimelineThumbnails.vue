<script setup lang="ts">
import { ref, watch, nextTick, computed, onMounted, onUnmounted } from "vue";
import type { FlatStep } from "../utils/types";
import { formatRelativeTime } from "@/utils/format";
import {
  Picture,
  VideoCameraFilled,
  VideoPause
} from "@element-plus/icons-vue";
import type { ScrollbarInstance } from "element-plus";
import { message } from "@/utils/message";

interface Props {
  steps: FlatStep[];
  selectedIndex: number;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: "update:selectedIndex", index: number): void;
}>();

defineOptions({
  name: "TimelineThumbnails"
});

// 滚动相关
const scrollbarRef = ref<ScrollbarInstance>();
const timelineRef = ref<HTMLElement>();
const thumbnailRefs = ref<HTMLElement[]>([]);
const sliderValue = ref(0);
const maxSliderValue = ref(0);

// 自动隐藏功能
const autoHide = ref(false);
const isHovered = ref(false);
const isFolded = computed(() => autoHide.value && !isHovered.value);

// 自动回放状态
const isAutoPlaying = ref(false);
const autoPlayTimer = ref<number | null>(null);

// 鼠标事件处理
const handleMouseEnter = () => {
  isHovered.value = true;
};

const handleMouseLeave = () => {
  isHovered.value = false;
};

// 获取起始时间（第一个步骤的开始时间）
const startTime = computed(() => {
  return props.steps[0]?.step.result?.start_time || 0;
});

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

// 自动回放控制
const startAutoPlay = (intervalMs = 800) => {
  if (isAutoPlaying.value) {
    stopAutoPlay();
    return;
  }

  isAutoPlaying.value = true;
  message("📹 开始自动回放", { type: "success" });

  // 重置到第一步
  selectStep(0);
  let currentIndex = 0;

  const playNext = () => {
    if (currentIndex < props.steps.length && isAutoPlaying.value) {
      selectStep(currentIndex);
      currentIndex += 1;

      if (currentIndex >= props.steps.length) {
        stopAutoPlay();
      } else {
        autoPlayTimer.value = window.setTimeout(playNext, intervalMs);
      }
    }
  };

  // 开始播放下一步
  autoPlayTimer.value = window.setTimeout(playNext, intervalMs);
};

// 停止自动回放
const stopAutoPlay = () => {
  isAutoPlaying.value = false;
  if (autoPlayTimer.value) {
    clearTimeout(autoPlayTimer.value);
    autoPlayTimer.value = null;
  }
  message("⏹️ 自动回放已停止", { type: "info" });
  // 重置到第一步
  selectStep(0);
};

// 初始化滑块最大值
onMounted(() => {
  nextTick(() => {
    updateMaxSliderValue();
    // 添加窗口大小变化监听
    window.addEventListener("resize", updateMaxSliderValue);
  });
});

// 组件卸载时清理事件监听
onUnmounted(() => {
  window.removeEventListener("resize", updateMaxSliderValue);
  // 清理自动回放定时器
  if (autoPlayTimer.value) {
    clearTimeout(autoPlayTimer.value);
  }
});

// 更新滑块最大值
const updateMaxSliderValue = () => {
  if (timelineRef.value && scrollbarRef.value) {
    // 正确获取Element Plus scrollbar的内部引用
    const wrapEl = scrollbarRef.value.wrapRef;
    if (wrapEl) {
      const scrollWidth = timelineRef.value.scrollWidth;
      const clientWidth = wrapEl.clientWidth;
      maxSliderValue.value = Math.max(0, scrollWidth - clientWidth);
    }
  }
};

// 滑块输入处理（参考官方示例）
const handleSliderInput = (value: number | number[]) => {
  if (scrollbarRef.value) {
    const scrollValue = Array.isArray(value) ? value[0] : value;
    scrollbarRef.value.setScrollLeft(scrollValue);
  }
};

// 滚动事件处理（参考官方示例）
const handleScroll = ({ scrollLeft }: { scrollLeft: number }) => {
  sliderValue.value = scrollLeft;
};

// 滑块提示格式化
const formatTooltip = (value: number) => {
  if (maxSliderValue.value === 0) return "0%";
  const percentage = Math.round((value / maxSliderValue.value) * 100);
  return `${percentage}%`;
};

// 监听选中索引变化，智能滚动到对应位置
watch(
  () => props.selectedIndex,
  async newIndex => {
    await nextTick();
    if (thumbnailRefs.value[newIndex] && scrollbarRef.value) {
      const thumbnail = thumbnailRefs.value[newIndex];
      const scrollContainer = scrollbarRef.value.wrapRef;

      if (thumbnail && scrollContainer) {
        const currentScrollLeft = scrollContainer.scrollLeft;
        const containerWidth = scrollContainer.clientWidth;
        const thumbnailLeft = thumbnail.offsetLeft;
        const thumbnailWidth = thumbnail.offsetWidth;

        // 计算缩略图的可见边界
        const thumbnailRight = thumbnailLeft + thumbnailWidth;
        const visibleLeft = currentScrollLeft;
        const visibleRight = currentScrollLeft + containerWidth;

        // 只有当选中的缩略图不完全可见时才滚动
        let targetScrollLeft = currentScrollLeft;

        if (thumbnailLeft < visibleLeft) {
          // 选中项在左侧不可见区域，滚动到左边界
          targetScrollLeft = thumbnailLeft - 20; // 预留20px边距
        } else if (thumbnailRight > visibleRight) {
          // 选中项在右侧不可见区域，滚动到右边界
          targetScrollLeft = thumbnailRight - containerWidth + 20; // 预留20px边距
        }

        // 确保滚动值在有效范围内
        targetScrollLeft = Math.max(
          0,
          Math.min(targetScrollLeft, maxSliderValue.value)
        );

        // 只有需要滚动时才执行
        if (targetScrollLeft !== currentScrollLeft) {
          scrollbarRef.value.setScrollLeft(targetScrollLeft);
        }
      }
    }
  }
);

// 监听步骤数组变化，更新滑块最大值
watch(
  () => props.steps.length,
  () => {
    nextTick(() => {
      updateMaxSliderValue();
    });
  }
);
</script>

<template>
  <div
    class="timeline-wrapper"
    :class="{ 'timeline-folded': isFolded }"
    @mouseenter="handleMouseEnter"
    @mouseleave="handleMouseLeave"
  >
    <div class="timeline-container">
      <!-- 时间轴滚动区域 -->
      <div class="timeline-scrollbar-wrapper">
        <!-- 滑块控制器 -->
        <div class="timeline-slider">
          <div class="slider-wrapper">
            <el-icon size="22" class="slider-icon">
              <VideoCameraFilled />
            </el-icon>
            <span class="text-lg font-semibold mr-2">
              步骤快览（共 {{ steps.length }} 步）
            </span>
            <el-slider
              v-if="maxSliderValue > 0"
              v-model="sliderValue"
              :max="maxSliderValue"
              :format-tooltip="formatTooltip"
              @input="handleSliderInput"
              size="small"
              class="timeline-slider-control"
            />

            <div class="auto-hide-switch">
              <el-divider direction="vertical" />
              <span class="slider-info mx-2">自动折叠</span>
              <el-switch v-model="autoHide" />
            </div>
            <div>
              <el-divider direction="vertical" />
              <el-button
                :type="isAutoPlaying ? 'danger' : 'success'"
                size="small"
                :icon="isAutoPlaying ? VideoPause : VideoCameraFilled"
                @click="startAutoPlay(800)"
                :title="isAutoPlaying ? '停止回放' : '自动回放'"
                round
              >
                {{ isAutoPlaying ? "停止" : "回放" }}
              </el-button>
            </div>
          </div>
        </div>
        <el-scrollbar
          ref="scrollbarRef"
          height="auto"
          @scroll="handleScroll"
          class="timeline-scrollbar"
        >
          <div ref="timelineRef" class="timeline-track">
            <div
              v-for="(item, index) in steps"
              :key="index"
              :ref="el => setThumbnailRef(el, index)"
              class="timeline-item"
              :class="{
                'timeline-item--selected': index === selectedIndex,
                'timeline-item--success':
                  item.step.result?.status === 'success',
                'timeline-item--failed': item.step.result?.status === 'failed'
              }"
              @click="selectStep(index)"
            >
              <!-- 缩略图 -->
              <div class="timeline-thumbnail">
                <el-image
                  v-if="item.step.result?.oss_pic_pth"
                  :src="item.step.result.oss_pic_pth"
                  fit="cover"
                  class="thumbnail-image"
                >
                  <template #error>
                    <div class="image-placeholder">
                      <el-icon><Picture /></el-icon>
                    </div>
                  </template>
                </el-image>
                <div v-else class="image-placeholder">
                  <el-icon><Picture /></el-icon>
                </div>

                <!-- 步骤索引标记 -->
                <div class="timeline-index">{{ item.globalIndex }}</div>

                <!-- 状态指示器 -->
                <div
                  v-if="item.step.result?.status"
                  class="status-indicator"
                  :class="`status-indicator--${item.step.result.status}`"
                />
              </div>

              <!-- 时间标签 -->
              <div class="timeline-time">
                {{
                  formatRelativeTime(item.step.result?.start_time, startTime)
                }}
              </div>
            </div>
          </div>
        </el-scrollbar>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.timeline-wrapper {
  width: 100%;
  transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
  transform: translateY(0);

  // 折叠状态：默认隐藏大部分内容
  &.timeline-folded {
    transform: translateY(164px);
  }

  // 添加背景遮罩层以增强磨玻璃效果
  &::before {
    content: "";
    position: absolute;
    top: -10px;
    left: -10px;
    right: -10px;
    bottom: -10px;
    background: radial-gradient(
      ellipse 80% 50% at 50% 100%,
      rgba(245, 247, 250, 0.4) 0%,
      rgba(245, 247, 250, 0.1) 60%,
      transparent 100%
    );
    pointer-events: none;
    z-index: -1;
  }
}

.timeline-container {
  width: 100%;
  height: auto;
  padding-bottom: 6px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(20px) saturate(200%) brightness(115%);
  -webkit-backdrop-filter: blur(24px) saturate(200%) brightness(115%);
  border: 1px solid rgba(255, 255, 255, 0.7);
  border-radius: 16px 16px 0 0;
  box-shadow: 0 20px 56px rgba(0, 0, 0, 0.15), 0 10px 28px rgba(0, 0, 0, 0.1),
    0 5px 14px rgba(0, 0, 0, 0.06), inset 0 1px 0 rgba(255, 255, 255, 0.95),
    inset 0 -1px 0 rgba(255, 255, 255, 0.6);
  overflow: hidden;
  position: relative;
  display: flex;
  flex-direction: column;
  user-select: none;

  // 增加微妙的内发光效果
  &::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(
      90deg,
      transparent 0%,
      rgba(255, 255, 255, 0.8) 50%,
      transparent 100%
    );
    pointer-events: none;
  }

  // 添加底部阴影
  &::after {
    content: "";
    position: absolute;
    bottom: -8px;
    left: 50%;
    transform: translateX(-50%);
    width: 60%;
    height: 8px;
    background: radial-gradient(
      ellipse,
      rgba(0, 0, 0, 0.1) 0%,
      transparent 70%
    );
    pointer-events: none;
  }
}

.timeline-scrollbar-wrapper {
  padding: 0 8px;
  flex: 1;
}

.timeline-scrollbar {
  height: 100%;

  // 隐藏滚动条但保持功能
  :deep(.el-scrollbar__bar.is-horizontal) {
    display: none;
  }

  :deep(.el-scrollbar__bar.is-vertical) {
    display: none;
  }
}
.timeline-track {
  display: flex;
  align-items: flex-start;
  gap: 4px;
  padding: 8px 0 12px 0;
  min-width: max-content;
  height: 160px;
  box-sizing: border-box;
}

.timeline-item {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  padding: 6px;
  border-radius: 10px;
  height: 100%;
  box-sizing: border-box;
  min-width: 84px;

  // 添加微妙的悬停区域
  &::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(64, 158, 255, 0.05);
    border-radius: 8px;
    opacity: 0;
    transition: opacity 0.3s ease;
    pointer-events: none;
  }

  &:hover {
    &::before {
      opacity: 1;
    }

    .timeline-thumbnail {
      box-shadow: 0 8px 25px rgba(64, 158, 255, 0.25),
        0 3px 12px rgba(64, 158, 255, 0.15);
      border-color: rgba(64, 158, 255, 0.6);
    }

    .timeline-time {
      color: #409eff;
      font-weight: 500;
    }
  }

  &--selected {
    &::before {
      opacity: 1;
      background: rgba(64, 158, 255, 0.1);
    }

    .timeline-thumbnail {
      border-color: #409eff;
      box-shadow: 0 0 0 3px rgba(64, 158, 255, 0.2),
        0 6px 20px rgba(64, 158, 255, 0.3);
      transform: scale(1.05);
    }

    .timeline-index {
      background: linear-gradient(135deg, #409eff 0%, #66b3ff 100%);
      color: white;
      transform: scale(1.15);
      box-shadow: 0 2px 8px rgba(64, 158, 255, 0.4);
    }

    .timeline-time {
      color: #409eff;
      font-weight: 600;
    }
  }
}

// 移除成功和失败状态的样式，因为已有状态指示器

.timeline-thumbnail {
  position: relative;
  width: 72px;
  height: 120px;
  border: 2px solid rgba(220, 223, 230, 0.8);
  border-radius: 8px;
  overflow: hidden;
  //   background: #f5f7fa;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  flex-shrink: 0;

  .thumbnail-image {
    width: 100%;
    height: 100%;

    :deep(.el-image__inner) {
      width: 100%;
      height: 100%;
    }
  }
}

.image-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  color: #c0c4cc;
  font-size: 24px;
}

.timeline-index {
  position: absolute;
  top: 3px;
  right: 3px;
  background: rgba(0, 0, 0, 0.4);
  color: white;
  padding: 2px 5px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: bold;
  line-height: 1.2;
  transition: all 0.3s ease;
  min-width: 18px;
  text-align: center;
}

.status-indicator {
  position: absolute;
  bottom: 3px;
  left: 3px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.8);

  &--success {
    background: #67c23a;
  }

  &--failed {
    background: #f56c6c;
  }

  &--running {
    background: #e6a23c;
    animation: pulse 1.5s ease-in-out infinite;
  }
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.7;
    transform: scale(1.1);
  }
}

.timeline-time {
  margin-top: 6px;
  font-size: 11px;
  font-weight: 500;
  text-align: center;
  line-height: 1.2;
  white-space: nowrap;
  max-width: 76px;
  overflow: hidden;
  text-overflow: ellipsis;
  flex-shrink: 0;
}

.timeline-slider {
  border-bottom: 1px solid rgba(220, 223, 230, 0.6);
  //   background: rgba(252, 254, 255, 0.85);
  //   backdrop-filter: blur(12px) saturate(150%);
  //   -webkit-backdrop-filter: blur(12px) saturate(150%);
  padding: 6px 10px;
  position: relative;
  flex-shrink: 0;
  min-height: 48px;
  box-sizing: border-box;

  // 添加微妙的内阴影
  &::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(
      90deg,
      transparent 0%,
      rgba(64, 158, 255, 0.2) 50%,
      transparent 100%
    );
    pointer-events: none;
  }
}

.slider-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
}

.slider-icon {
  color: #409eff;
  font-size: 16px;
  flex-shrink: 0;
}

.timeline-slider-control {
  flex: 1;

  :deep(.el-slider__runway) {
    background: rgba(220, 223, 230, 0.6);
  }

  :deep(.el-slider__bar) {
    background: linear-gradient(90deg, #409eff 0%, #66b3ff 100%);
  }

  :deep(.el-slider__button) {
    border-color: #409eff;
    background: white;
    box-shadow: 0 2px 6px rgba(64, 158, 255, 0.3);
  }
}

.slider-info {
  font-size: 14px;
  color: #909399;
  white-space: nowrap;
  flex-shrink: 0;
}

.auto-hide-switch {
  margin-left: auto;
  flex-shrink: 0;
  display: flex;
  align-items: center;

  :deep(.el-switch__label) {
    font-size: 12px;
    color: #909399;
  }

  :deep(.el-switch__label.is-active) {
    color: #409eff;
  }
}
</style>
