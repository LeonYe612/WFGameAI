<script setup lang="ts">
import { ElMessage } from "element-plus";
import { defineProps, ref } from "vue";

interface Props {
  text: string; // 要复制的文本
  label?: string; // 提示文字
  successMsg?: string; // 成功提示
  errorMsg?: string; // 失败提示
  icon?: string; // 可传入自定义 icon 名称（与 ReIcon 体系兼容）
  inline?: boolean; // 是否内联显示，不包裹块级样式
  autoHideMsg?: boolean; // 是否自动隐藏提示（默认 true）
  showCheck?: boolean; // 复制成功后是否显示勾选
  checkDuration?: number; // 勾选显示时长(ms)
  wrap?: boolean; // 是否包裹 slot 内容并让其整体可点击复制
}

const props = defineProps<Props>();
const copying = ref(false);
const copied = ref(false);

const doCopy = async () => {
  const value = props.text || "";
  if (!value || copying.value) return;
  copying.value = true;
  try {
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(value);
    } else {
      const el = document.createElement("textarea");
      el.value = value;
      el.setAttribute("readonly", "");
      el.style.position = "absolute";
      el.style.left = "-9999px";
      document.body.appendChild(el);
      el.select();
      document.execCommand("copy");
      document.body.removeChild(el);
    }
    ElMessage.success(props.successMsg || "已复制");
    if (props.showCheck) {
      copied.value = true;
      const ttl = props.checkDuration ?? 1200;
      setTimeout(() => (copied.value = false), ttl);
    }
  } catch (e) {
    ElMessage.error(props.errorMsg || "复制失败");
  } finally {
    copying.value = false;
  }
};
</script>
<template>
  <component
    :is="props.wrap ? 'span' : 'span'"
    class="copy-wrapper"
    :data-copying="copying ? '1' : '0'"
    :title="props.label || '复制'"
    @click="doCopy"
  >
    <slot v-if="props.wrap" />
    <svg
      v-if="!props.wrap && !copied"
      class="copy-icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4c0-1.1.9-2 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
    <svg
      v-if="!props.wrap && copied"
      class="copy-icon copied"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <path d="M20 6L9 17l-5-5" />
    </svg>
  </component>
</template>
<style scoped>
.copy-wrapper {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  user-select: none;
  padding: 4px;
  border-radius: 6px;
  transition: background 0.15s, color 0.15s;
  color: #475569;
}
.copy-wrapper:hover {
  background: #e2e8f0;
  color: #0f172a;
}
.copy-wrapper:active {
  background: #cbd5e1;
}
.copy-wrapper[data-copying="1"] {
  opacity: 0.6;
  pointer-events: none;
}
.copy-icon {
  width: 16px;
  height: 16px;
  display: block;
}
.copy-icon.copied {
  color: #059669;
  animation: pop 0.4s ease;
}
@keyframes pop {
  0% {
    transform: scale(0.6);
    opacity: 0.2;
  }
  60% {
    transform: scale(1.15);
    opacity: 1;
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
}
</style>
