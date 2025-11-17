<script setup lang="ts">
// 任务进度展示组件（实时）
import { replayApi } from "@/api/scripts";
import CopyToClipboard from "@/components/Common/CopyToClipboard.vue";
import { connectSocket } from "@/views/replay/utils/socket";
import { defineProps, onMounted, onUnmounted, ref, watch } from "vue";

const props = defineProps<{
  taskId: string;
  progress?: number;
  status?: string;
  celeryId?: string;
}>();

const progress = ref<number>(props.progress ?? 0); // 进度百分比（0-100）
const status = ref<string>(props.status ?? "执行中");
const socketRef = ref<any>(null);
const gotProgress = ref(false);
const celeryId = ref<string | undefined>(props.celeryId);

// 状态用于驱动动画（不直接显示文字）

// 外部 props 变更时，同步初始值
watch(
  () => [props.progress, props.status],
  ([p, s]) => {
    if (typeof p === "number") progress.value = Math.max(0, Math.min(100, p));
    if (typeof s === "string" && s) status.value = s;
  }
);

watch(
  () => props.celeryId,
  cid => {
    if (cid) celeryId.value = cid;
  }
);

const updateProgress = (val?: any) => {
  // 支持多种 payload 结构：{ percent } 或 { current, total }
  let pct: number | null = null;
  if (val && typeof val === "object") {
    if (typeof val.percent === "number") pct = val.percent;
    else if (
      typeof val.current === "number" &&
      typeof val.total === "number" &&
      val.total > 0
    ) {
      pct = Math.round((val.current / val.total) * 100);
    }
  } else if (typeof val === "number") {
    pct = val;
  }
  if (pct != null) progress.value = Math.max(0, Math.min(100, pct));
};

const updateStatus = (val?: any) => {
  // 归一化状态
  const norm = String(val || "").toLowerCase();
  if (["done", "finished", "success", "completed"].includes(norm)) {
    status.value = "完成";
    if (progress.value < 100) progress.value = 100;
  } else if (["failed", "error"].includes(norm)) {
    status.value = "失败";
  } else if (norm) {
    status.value = "执行中";
  }
};

const trySetCeleryId = (data?: any) => {
  if (!data) return;
  let cid: any;
  if (data?.celery_id) cid = data.celery_id;
  else if (data?.celeryId) cid = data.celeryId;
  else if (data?.celeryID) cid = data.celeryID;
  else if (data?.celery_task_id) cid = data.celery_task_id;
  // 兼容部分服务以 task_id 传递 Celery 任务ID（通常为 UUID）
  if (!cid) {
    const maybe = data?.task_id || data?.taskId;
    if (
      maybe &&
      typeof maybe === "string" &&
      maybe.includes("-") &&
      maybe !== String(props.taskId)
    ) {
      cid = maybe;
    }
  }
  if (cid && !celeryId.value) celeryId.value = String(cid);
};

onMounted(() => {
  if (!props.taskId) return;
  socketRef.value = connectSocket(
    { room: `replay_task_${String(props.taskId)}` },
    {
      onSysMsg: (_msg, payload) => {
        const evt = payload?.event || "";
        const data = payload?.data;
        switch (evt) {
          case "task_progress":
          case "progress":
          case "progress_update": {
            gotProgress.value = true;
            updateProgress(data);
            trySetCeleryId(data);
            // 若进度达到100%，标记完成
            if (typeof data?.percent === "number") {
              if (data.percent >= 100) updateStatus("finished");
              else updateStatus("running");
            } else if (
              typeof data?.current === "number" &&
              typeof data?.total === "number" &&
              data.total > 0
            ) {
              const pct = Math.round((data.current / data.total) * 100);
              if (pct >= 100) updateStatus("finished");
              else updateStatus("running");
            }
            break;
          }
          case "task_status":
          case "status":
            trySetCeleryId(data);
            updateStatus(data?.status ?? data);
            break;
          case "task_finished":
          case "finished":
            trySetCeleryId(data);
            updateStatus("finished");
            break;
          default:
            // no-op for other events
            break;
        }
      }
    }
  );

  // 刷新兜底：短时间未收到进度事件，则从后端快照计算一次全局进度与状态
  const t = setTimeout(async () => {
    if (gotProgress.value) return;
    try {
      const resp = await replayApi.snapshot({ task_id: String(props.taskId) });
      // 兜底从快照中提取 celeryId（若后端提供）
      trySetCeleryId(resp?.data);
      trySetCeleryId((resp as any)?.task);
      const devices = Array.isArray(resp?.data?.devices)
        ? resp.data.devices
        : Array.isArray((resp as any)?.devices)
        ? (resp as any).devices
        : [];
      let total = 0;
      let completed = 0;
      for (const dev of devices) {
        const records = Array.isArray(dev?.records) ? dev.records : [];
        for (const rec of records) {
          const steps = Array.isArray(rec?.steps) ? rec.steps : [];
          total += steps.length;
          for (const s of steps) {
            const st = String(s?.status || "").toLowerCase();
            if (st === "success" || st === "failed") completed += 1;
          }
        }
      }
      if (total > 0) {
        const pct = Math.round((completed / total) * 100);
        updateProgress(pct);
        if (pct >= 100) updateStatus("finished");
      }
    } catch (_) {
      // ignore
    }
  }, 800);
  // 清理定时器
  onUnmounted(() => clearTimeout(t));
});

onUnmounted(() => {
  if (socketRef.value) socketRef.value.disconnect();
});

onUnmounted(() => {
  if (socketRef.value) socketRef.value.disconnect();
});
</script>
<template>
  <div class="task-progress">
    <div class="progress-header">
      <h3 class="progress-title">
        任务进度
        <el-tooltip
          content="当前任务执行进度（后端聚合），页面刷新会自动从快照恢复"
          placement="top"
        >
          <span class="help-icon" aria-label="help">?</span>
        </el-tooltip>
      </h3>
      <div class="ids-inline">
        <span class="id-chip">
          任务ID: <strong>{{ props.taskId }}</strong>
        </span>
        <span class="id-chip" v-if="celeryId">
          CeleryID: <strong>{{ celeryId }}</strong>
          <CopyToClipboard :text="String(celeryId)" label="复制 CeleryID" />
        </span>
        <div class="runner" v-if="status === '执行中'" aria-label="running">
          <span class="dot" />
          <span class="dot" />
          <span class="dot" />
        </div>
      </div>
    </div>
    <div class="progress-bar-outer">
      <div class="progress-bar-inner" :style="{ width: progress + '%' }">
        <span class="progress-label">{{ progress }}%</span>
      </div>
    </div>
  </div>
</template>
<style scoped>
.task-progress {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 12px 16px 12px 16px; /* 紧凑 */
  margin-bottom: 12px;
  box-shadow: 0 2px 8px rgba(80, 120, 255, 0.06);
}

.progress-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.ids-inline {
  display: flex;
  align-items: center;
  gap: 10px;
}

.id-chip {
  background: #f1f5f9;
  color: #475569;
  padding: 5px 12px;
  border-radius: 6px;
  font-size: 14px;
  line-height: 1.2;
  border: 1px solid #e2e8f0;
  box-shadow: inset 0 0 0 1px #ffffffaa;
}

.id-chip strong {
  font-weight: 700;
  color: #0f172a;
  font-size: 15px;
}

/* 删除了头部重复的标题与提示样式 */

.progress-bar-outer {
  width: 100%;
  height: 20px; /* 更低 */
  background: #e0e7ff;
  border-radius: 10px;
  margin: 10px 0 0 0; /* 更紧凑 */
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
  font-size: 0.85rem;
  font-weight: bold;
  margin-right: 10px;
  text-shadow: 0 1px 4px #7b8cff44;
}

.runner {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #3b82f6;
  animation: dotPulse 1.2s infinite ease-in-out;
}

.dot:nth-child(2) {
  animation-delay: 0.15s;
}
.dot:nth-child(3) {
  animation-delay: 0.3s;
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

@keyframes dotPulse {
  0%,
  80%,
  100% {
    transform: scale(0.8);
    opacity: 0.6;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}
</style>
