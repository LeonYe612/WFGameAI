<script setup lang="ts">
// 任务进度展示组件
import { defineProps, ref } from "vue";
const props = defineProps<{
  taskId: string;
  progress?: number;
  status?: string;
}>();

// 假数据参数化
const progress = ref(props.progress ?? 35); // 进度百分比
const status = ref(props.status ?? "执行中");
</script>
<template>
  <div class="task-progress">
    <h3>
      任务进度 <span class="task-id">({{ taskId }})</span>
    </h3>
    <div class="progress-bar-outer">
      <div class="progress-bar-inner" :style="{ width: progress + '%' }">
        <span class="progress-label">{{ progress }}%</span>
      </div>
    </div>
    <div class="progress-status">
      <span :class="[
        'status-dot',
        status === '执行中' ? 'running' : status === '完成' ? 'done' : 'error'
      ]" />
      {{ status }}
    </div>
  </div>
</template>
<style scoped>
.task-progress {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 18px 22px 18px 22px;
  margin-bottom: 16px;
  box-shadow: 0 2px 8px rgba(80, 120, 255, 0.06);
}

.task-id {
  color: #7b8cff;
  font-size: 1.05rem;
  margin-left: 8px;
}

.progress-bar-outer {
  width: 100%;
  height: 18px;
  background: #e0e7ff;
  border-radius: 10px;
  margin: 18px 0 10px 0;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(80, 120, 255, 0.04);
}

.progress-bar-inner {
  height: 100%;
  background: linear-gradient(90deg, #7b8cff 60%, #a5b4fc 100%);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  transition: width 0.4s;
  position: relative;
}

.progress-label {
  color: #fff;
  font-size: 0.98rem;
  font-weight: bold;
  margin-right: 12px;
  text-shadow: 0 1px 4px #7b8cff44;
}

.progress-status {
  margin-top: 8px;
  font-size: 1.08rem;
  color: #3a4a7c;
  display: flex;
  align-items: center;
}

.status-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 8px;
  background: #bfcfff;
}

.status-dot.running {
  background: #7b8cff;
  animation: pulse 1.2s infinite;
}

.status-dot.done {
  background: #22c55e;
}

.status-dot.error {
  background: #ff4d4f;
}

@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 #7b8cff44;
  }

  70% {
    box-shadow: 0 0 0 8px #7b8cff11;
  }

  100% {
    box-shadow: 0 0 0 0 #7b8cff44;
  }
}
</style>
