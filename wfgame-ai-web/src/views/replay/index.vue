<script setup lang="ts">
import { useRoute } from "vue-router";

import Replay from "./components/Replay.vue";
import ReplayTaskProgress from "./components/ReplayTaskProgress.vue";
import ReplayTaskSteps from "./components/ReplayTaskSteps.vue";

const route = useRoute();
const task_id = String(route.query.task_id || route.params.task_id);
const device_ids = (route.query.device_ids || "")
  .toString()
  .split(",")
  .filter(Boolean);
const celery_id = String(route.query.celery_id || "");
const script_ids = (route.query.script_ids || "")
  .toString()
  .split(",")
  .filter(Boolean)
  .map(s => Number(s))
  .filter(n => Number.isFinite(n));
</script>

<template>
  <div class="replay-layout">
    <!-- 如果想更优化：
    1. 图片 分片传输
    2. 图片 压缩
    3. 增加前端 拉流（当前是后端推流） -->
    <!-- <GlobalSocket /> -->
    <!-- <div class="ids-row top">
      <span class="id-chip strong">任务ID：{{ task_id }}</span>
      <span v-if="celery_id" class="id-chip alt strong">
        CeleryID：{{ celery_id }}
      </span>
    </div> -->
    <div class="progress-block">
      <ReplayTaskProgress :taskId="task_id" :celeryId="celery_id" />
    </div>
    <div class="main-row">
      <div class="devices-block">
        <div class="devices-inner">
          <Replay :taskId="task_id" :deviceIds="device_ids" />
        </div>
      </div>
      <div class="steps-block">
        <ReplayTaskSteps :taskId="task_id" :scriptIds="script_ids" />
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 主体布局 */
.replay-layout {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 28px 32px 28px 32px;
  min-height: 100vh;
  background: #f7f8fa;
}

.progress-block {
  margin-bottom: 0;
  background: linear-gradient(90deg, #e0e7ff 0%, #f0fdfa 100%);
  border-radius: 10px;
  box-shadow: 0 2px 8px rgba(80, 120, 255, 0.07);
  padding: 18px 24px 10px 24px;
}

.ids-row {
  display: flex;
  gap: 12px;
  margin-top: 8px;
}

.ids-row.top {
  margin-top: -4px;
}

.id-chip {
  background: #eef2ff;
  color: #1f2a44;
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 1.05rem;
  font-weight: 600;
  border: 1px solid #c7d2fe;
  box-shadow: 0 1px 3px rgba(80, 120, 255, 0.15);
}

.id-chip.alt {
  background: #ecfeff;
  border-color: #a5f3fc;
}

.id-chip.strong {
  background: #fff7cc;
  border-color: #f6e6a0;
  color: #7a5c00;
}

.main-row {
  display: flex;
  flex-direction: row;
  gap: 18px;
  width: 100%;
  min-height: 520px;
}

.devices-block {
  flex: 2 1 0%;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(80, 120, 255, 0.06);
  padding: 18px 12px 18px 18px;
  overflow: auto;
}

.devices-inner {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
  align-items: flex-start;
}

.steps-block {
  flex: 1 1 0%;
  min-width: 0;
  background: #fff; /* 改回与设备信息一致的浅色背景 */
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(80, 120, 255, 0.06);
  padding: 18px 18px 18px 18px;
  overflow: auto;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
}

@media (max-width: 1200px) {
  .main-row {
    flex-direction: column;
  }

  .devices-block,
  .steps-block {
    min-width: 0;
    width: 100%;
    margin-bottom: 18px;
  }
}
</style>
