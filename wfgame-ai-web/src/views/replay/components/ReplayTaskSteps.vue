<script setup lang="ts">
// 任务执行步骤信息块
import { defineProps, ref } from "vue";
const props = defineProps<{ taskId: string; steps?: { name: string; status: string; time: string }[] }>();

// 假数据参数化
const steps = ref(props.steps ?? [
  { name: "启动设备", status: "完成", time: "10:01:12" },
  { name: "环境准备", status: "完成", time: "10:01:18" },
  { name: "上传脚本", status: "完成", time: "10:01:22" },
  { name: "执行脚本", status: "执行中", time: "10:01:25" },
  { name: "收集结果", status: "等待", time: "-" }
]);
</script>
<template>
  <div class="task-steps">
    <h3>任务执行步骤 <span class="task-id">({{ taskId }})</span></h3>
    <ol class="steps-list">
      <li v-for="(step, idx) in steps" :key="idx" :class="['step-item', step.status]">
        <span class="step-index">{{ idx + 1 }}</span>
        <span class="step-name">{{ step.name }}</span>
        <span class="step-status">
          <span :class="['status-dot', step.status]" />
          {{ step.status }}
        </span>
        <span class="step-time">{{ step.time }}</span>
      </li>
    </ol>
  </div>
</template>
<style scoped>
.task-steps {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 18px 22px 18px 22px;
  margin-bottom: 16px;
  box-shadow: 0 2px 8px rgba(80,120,255,0.06);
}
.task-id {
  color: #7b8cff;
  font-size: 1.05rem;
  margin-left: 8px;
}
.steps-list {
  list-style: none;
  margin: 18px 0 0 0;
  padding: 0;
}
.step-item {
  display: flex;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #e0e7ff;
  font-size: 1.05rem;
  transition: background 0.2s;
}
.step-item:last-child {
  border-bottom: none;
}
.step-index {
  width: 28px;
  height: 28px;
  background: #e0e7ff;
  color: #7b8cff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  margin-right: 12px;
  font-size: 1.08rem;
}
.step-name {
  flex: 1;
  color: #3a4a7c;
}
.step-status {
  min-width: 80px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.status-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 4px;
  background: #bfcfff;
}
.status-dot.完成 {
  background: #22c55e;
}
.status-dot.执行中 {
  background: #7b8cff;
  animation: pulse 1.2s infinite;
}
.status-dot.等待 {
  background: #bfcfff;
}
.status-dot.失败 {
  background: #ff4d4f;
}
.step-time {
  min-width: 70px;
  text-align: right;
  color: #64748b;
  font-size: 0.98rem;
}
@keyframes pulse {
  0% { box-shadow: 0 0 0 0 #7b8cff44; }
  70% { box-shadow: 0 0 0 8px #7b8cff11; }
  100% { box-shadow: 0 0 0 0 #7b8cff44; }
}
</style>
