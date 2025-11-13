<template>
  <el-dialog
    v-model="localVisible"
    title="任务详情"
    width="650px"
    :close-on-click-modal="false"
    class="task-detail-dialog"
    top="5vh"
  >
    <div v-if="task" class="task-detail">
      <el-card class="info-card" shadow="never">
        <el-row :gutter="24">
          <el-col :span="12">
            <div class="info-group left-group">
              <div class="info-subgroup base-block">
                <div class="info-item"><label>ID：</label><span>{{ task.id ?? '--' }}</span></div>
                <div class="info-item"><label>Celery ID：</label><span>{{ task.celery_id ?? task.celery_task_id ?? '--' }}</span></div>
                <div class="info-item"><label>任务名称：</label><span>{{ task.name ?? '--' }}</span></div>
                <div class="info-item"><label>优先级：</label>
                  <el-tag :type="priorityConfig[task.priority]?.type" size="small" effect="light" class="tag-left">
                    {{ priorityConfig[task.priority]?.label ?? task.priority ?? '--' }}
                  </el-tag>
                </div>
                <div class="info-item"><label>任务类型：</label>
                  <el-tag :type="taskTypeConfig[task.task_type]?.type" size="small" effect="light" class="tag-left">
                    <span v-if="taskTypeConfig[task.task_type]?.icon" class="icon-wrap"><el-icon><component :is="taskTypeConfig[task.task_type].icon" /></el-icon></span>
                    {{ taskTypeConfig[task.task_type]?.label ?? task.task_type ?? '--' }}
                  </el-tag>
                </div>
                <div class="info-item"><label>运行类型：</label>
                  <el-tag :type="runTypeConfig[task.run_type]?.type" size="small" effect="light" class="tag-left">
                    <span v-if="runTypeConfig[task.run_type]?.icon" class="icon-wrap"><el-icon><component :is="runTypeConfig[task.run_type].icon" /></el-icon></span>
                    {{ runTypeConfig[task.run_type]?.label ?? task.run_type ?? '--' }}
                  </el-tag>
                </div>
<!--           <div v-if="task.run_type===3" class="schedule-detail-row">
                  <label>计划时间：</label>
                  <el-tag size="small" effect="light" class="tag-left" >
                    <span v-if="runTypeConfig[task.run_type]?.icon" class="icon-wrap"></span>
                    {{ task.run_info?.schedule ?? '&#45;&#45;' }}
                  </el-tag>
                </div>-->
                <div class="info-item"><label>执行状态：</label>
                  <el-tag :type="taskStatusConfig[task.status]?.type" size="small" effect="light" class="tag-left">
                    <span v-if="taskStatusConfig[task.status]?.icon" class="icon-wrap"><el-icon class="status-icon"><component :is="taskStatusConfig[task.status].icon" /></el-icon></span>
                    {{ taskStatusConfig[task.status]?.label ?? task.status ?? '--' }}
                  </el-tag>
                </div>
              </div>
              <div class="info-subgroup resource-block">
                <div class="info-item"><label>设备数：</label><span>{{ task.devices_count ?? "--" }}</span></div>
                <div class="info-item"><label>设备信息：</label>
                  <span v-if="Array.isArray(task.devices_list)">
                    <el-tag
                      v-for="(name, idx) in task.devices_list"
                      :key="name"
                      :type="(['success','primary','warning','danger'][idx % 4] as any)"
                      size="small"
                      style="margin-right:4px;"
                    >{{ name }}</el-tag>
                  </span>
                  <span v-else>{{ task.devices_list ?? "--" }}</span>
                </div>
                <div class="info-item"><label>脚本数：</label><span>{{ task.scripts_count ?? "--" }}</span></div>
                <div class="info-item"><label>脚本信息：</label>
                  <span v-if="Array.isArray(task.scripts_list)">
                    <el-tag
                      v-for="(name, idx) in task.scripts_list"
                      :key="name"
                      :type="(['primary','success','warning','danger'][idx % 4] as any)"
                      size="small"
                      style="margin-right:4px;"
                    >{{ name }}</el-tag>
                  </span>
                  <span v-else>{{ task.scripts_list ?? "--" }}</span>
                </div>

              </div>
            </div>
          </el-col>
          <el-col :span="12">
            <div class="info-group right-group">
              <div class="info-subgroup time-block">
                <div class="info-item"><label>计划时间：</label><span>{{ task.run_info?.schedule }}</span></div>
                <div class="info-item"><label>开始时间：</label><span>{{ formatDateTime(task.start_time) }}</span></div>
                <div class="info-item"><label>结束时间：</label><span>{{ formatDateTime(task.end_time) }}</span></div>
                <div class="info-item"><label>执行耗时：</label><span>{{ task.execution_time ?? '--' }}</span></div>
              </div>
              <div class="info-subgroup user-block">
                <div class="info-item"><label>创建人：</label>
                  <el-tag type="primary" size="default" effect="light" v-if="task.creator_name">{{ task.creator_name }}</el-tag>
                  <span v-else>--</span>
                </div>
                <div class="info-item"><label>创建人ID：</label><span>{{ task.creator_id ?? '--' }}</span></div>
                <div class="info-item"><label>创建时间：</label><span>{{ formatDateTime(task.created_at) }}</span></div>
                <!-- 更新人名接口无，暂隐藏 -->
                <div class="info-item"><label>更新人：</label>
                  <el-tag type="success" size="default" effect="light" v-if="task.updater_name">{{ task.updater_name }}</el-tag>
                  <span v-else>--</span>
                </div>
                <div class="info-item"><label>更新人ID：</label><span>{{ task.updater_id ?? '--' }}</span></div>
                <div class="info-item"><label>更新时间：</label><span>{{ formatDateTime(task.updated_at) }}</span></div>
              </div>
            </div>
          </el-col>
        </el-row>
        <div class="cmd-block">
          <label>执行命令：</label>
          <span class="cmd-text" :title="execCmd">{{ execCmd || "--" }}</span>
          <el-button
            v-if="execCmd"
            class="cmd-copy-btn"
            circle
            plain
            size="small"
            type="primary"
            :icon="CopyDocument"
            @click="copyExecCmd"
          />
        </div>
        <div class="description-block">
          <label>描述：</label>
          <span>{{ task.description ?? "--" }}</span>
        </div>
      </el-card>

<!--      &lt;!&ndash; 执行日志 &ndash;&gt;-->
<!--      <el-card class="logs-card" shadow="never">-->
<!--        <template #header>-->
<!--          <div class="card-header">-->
<!--            <span>执行日志</span>-->
<!--            <el-button size="small" :loading="logsLoading" @click="loadLogs">-->
<!--              <el-icon>-->
<!--                <Refresh />-->
<!--              </el-icon>-->
<!--              刷新日志-->
<!--            </el-button>-->
<!--          </div>-->
<!--        </template>-->
<!--        <div class="logs-container">-->
<!--          <el-scrollbar height="300px">-->
<!--            <div v-if="logsLoading" class="logs-loading">-->
<!--              <el-icon class="is-loading">-->
<!--                <Loading />-->
<!--              </el-icon>-->
<!--              加载日志中...-->
<!--            </div>-->
<!--            <pre v-else-if="logs" class="logs-content">{{ logs }}</pre>-->
<!--            <div v-else class="logs-empty">暂无日志信息</div>-->
<!--          </el-scrollbar>-->
<!--        </div>-->
<!--      </el-card>-->
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="localVisible = false"> 关闭 </el-button>
<!--        <el-button-->
<!--          v-if="task && task.status !== TaskStatus.RUNNING"-->
<!--          type="primary"-->
<!--          @click="handleAction('start')"-->
<!--        >-->
<!--          <el-icon>-->
<!--            <VideoPlay />-->
<!--          </el-icon>-->
<!--          启动任务-->
<!--        </el-button>-->
        <el-button
          v-if="task && task.status === TaskStatus.RUNNING"
          type="danger"
          @click="handleAction('stop')"
        >
          <el-icon>
            <VideoPause />
          </el-icon>
          停止任务
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { scriptApi } from "@/api/scripts";
import { getTaskLogs } from "@/api/tasks";
import { CopyDocument, VideoPause } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { computed, ref, watch } from "vue";
import { TaskStatus } from "../utils/enums";
import {
    priorityConfig,
    runTypeConfig,
    taskStatusConfig,
    taskTypeConfig
} from "../utils/rules";
import type {
    TaskAction,
    TaskDetailDialogEmits,
    TaskDetailDialogProps
} from "../utils/types";

// Props
const props = withDefaults(defineProps<TaskDetailDialogProps>(), {
  visible: false,
  task: null,
  loading: false
});

// Emits
const emit = defineEmits<TaskDetailDialogEmits>();

// 本地显示状态
const localVisible = computed({
  get: () => props.visible,
  set: value => emit("update:visible", value)
});

// 日志相关状态
const logs = ref<string>("");
const logsLoading = ref(false);
const execCmd = ref<string>("");

// 监听任务变化，自动加载日志
watch(
  () => props.task,
  newTask => {
    if (newTask) {
      loadLogs();
      buildExecCmd(newTask);
    }
  },
  { immediate: true }
);

// 加载任务日志
const loadLogs = async () => {
  if (!props.task) return;

  try {
    logsLoading.value = true;
    const response = await getTaskLogs(props.task.id);
    logs.value = response.data || "暂无日志信息";
  } catch (error) {
    console.error("加载日志失败:", error);
    logs.value = "加载日志失败";
  } finally {
    logsLoading.value = false;
  }
};

// 处理操作
const handleAction = (action: TaskAction) => {
  if (props.task) {
    emit("action", action, props.task);
  }
};

// 构建执行命令（仅基于最新结构：script_params 为快照对象）
const buildExecCmd = async (task: any) => {
  try {
    const sp = task?.script_params;
    if (!sp || typeof sp !== "object" || Array.isArray(sp)) {
      execCmd.value = "";
      return;
    }

    // 设备序列号
    const serials: string[] = Array.isArray(sp.device_ids)
      ? sp.device_ids
          .map((d: any) => (d && typeof d.serial === "string" ? d.serial : ""))
          .filter((s: string) => !!s)
      : [];

    // 脚本与参数
    const specs: Array<{ id: number; lc: number; md?: number }> = [];
    const arr = Array.isArray(sp.script_ids) ? sp.script_ids : [];
    for (const it of arr) {
      if (!it || typeof it !== "object") continue;
      const id = Number(it.id);
      if (!Number.isFinite(id)) continue;
      const lc = Number(it["loop-count"]) > 0 ? Number(it["loop-count"]) : 1;
      const mdRaw = it["max-duration"];
      const md = typeof mdRaw === "number" && mdRaw > 0 ? mdRaw : undefined;
      specs.push({ id, lc, md });
    }
    if (!specs.length) {
      execCmd.value = "";
      return;
    }

    const toFileName = (s: any): string => {
      if (!s) return "";
      const raw = (s.filename || s.path || s.name || "").toString();
      const base = raw.split(/[\\/]/).pop() || "";
      if (base.endsWith(".json")) return base;
      return base ? `${base}.json` : "";
    };

    const parts: string[] = ["python", "replay_script.py"];
    for (const ser of serials) parts.push("--device", ser);

    // 批量查询脚本名
    const uniqueIds = Array.from(new Set(specs.map(s => s.id)));
    const fetched = await Promise.all(
      uniqueIds.map((id: number) =>
        scriptApi
          .detail(id)
          .then(r => r.data)
          .catch(() => null)
      )
    );
    const idToFile = new Map<number, string>();
    uniqueIds.forEach((id, idx) => {
      const obj = fetched[idx];
      idToFile.set(id, obj ? toFileName(obj) : `script_${id}.json`);
    });

    for (const s of specs) {
      const file = idToFile.get(s.id) || `script_${s.id}.json`;
      parts.push("--script", file, "--loop-count", String(s.lc));
      if (s.md) parts.push("--max-duration", String(s.md));
    }

    execCmd.value = parts.join(" ");
  } catch (e) {
    console.error("构建执行命令失败:", e);
    execCmd.value = "";
  }
};

// 复制执行命令
const copyExecCmd = async () => {
  try {
    const text = execCmd.value || "";
    if (!text) return;
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
    } else {
      const textarea = document.createElement("textarea");
      textarea.value = text;
      textarea.style.position = "fixed";
      textarea.style.left = "-9999px";
      document.body.appendChild(textarea);
      textarea.focus();
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
    }
    ElMessage({ type: "success", message: "已复制执行命令" });
  } catch (e) {
    console.error("复制命令失败:", e);
    ElMessage({ type: "error", message: "复制失败，请手动复制" });
  }
};

// 格式化日期时间
const formatDateTime = (dateTime: string) => {
  if (!dateTime) return "--";
  return new Date(dateTime).toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  });
};
</script>

<style scoped>
.icon-wrap {
  display: inline-flex;
  align-items: center;
  margin-right: 4px;
}
/* 左右两列色块高度自适应，右侧与左侧对齐 */
.left-group {
  background: none;
  border-radius: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  height: 100%;
}
.right-group {
  background: none;
  border-radius: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.info-card {
  border: 1px solid var(--el-border-color-light);
  background: #f8fafc;
  padding: 8px 8px 4px 8px;
}
.left-group {
  background: none;
  border-radius: 0;
  padding: 0;
}
.base-block {
  background: #eaf6fa;
  border-radius: 8px;
  padding: 16px 12px 12px 12px;
  margin-bottom: 16px;
}
.resource-block {
  background: #eae6fa;
  border-radius: 8px;
  padding: 16px 12px 12px 12px;
}
.right-group {
  /* 色块高度自适应，右侧与左侧对齐 */
  margin-left: 0;
  margin-right: 8px;
  vertical-align: middle;
}

.right-group .resource-block {
  background: #eae6fa;
  border-radius: 8px;
  padding: 16px 12px 12px 12px;
  flex: 1 1 auto;
}

.right-group .time-block {
  background: #eae6fa;
  border-radius: 8px;
  padding: 16px 12px 12px 12px;
  margin-bottom: 16px;
  flex: 1 1 auto;
}

.right-group .user-block {
  background: #e6f4fa;
  border-radius: 8px;
  padding: 16px 12px 12px 12px;
  flex: 1 1 auto;
}
.logs-card {
  border: 1px solid var(--el-border-color-light);
  margin-top: 8px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  padding: 6px 16px 6px 16px;
  background: #f5f7fa;
  border-bottom: 1px solid #e0e3e8;
}

/* info-item标签内容自动换行，避免撑宽左侧 */
.info-item {
  display: flex;
  align-items: flex-start;
  margin-bottom: 12px;
  gap: 8px;
  flex-wrap: wrap;
}

/* 标签内容区域自适应宽度，标签自动换行 */
.info-item label {
  font-weight: 500;
  color: var(--el-text-color-regular);
  min-width: 80px;
  flex-shrink: 0;
}
.info-item span {
  word-break: break-all;
  white-space: normal;
  flex: 1;
  min-width: 0;
}

.info-item.full-width {
  flex-direction: column;
  align-items: flex-start;
}

/* 备注块单独样式，淡黄色背景 */
.description-block {
  margin: 12px 0 0 0;
  padding: 10px 14px;
  background: #fffbe6;
  border-radius: 6px;
  line-height: 1.6;
  font-size: 15px;
  font-weight: 500;
  color: #8a6d3b;
  border: 1px solid #faebcc;
}

/* 执行命令单行展示，自动换行并提供悬停查看完整 title */
.cmd-block {
  position: relative;
  margin: 10px 0 6px 0;
  padding: 8px 12px;
  padding-right: 48px; /* 为右下角复制按钮预留空间 */
  background: #fff1f0; /* 浅红背景 */
  border: 1px solid #ffd6d6;
  border-radius: 6px;
  font-size: 13px;
  display: flex;
  gap: 8px;
}
.cmd-block label {
  font-weight: 600;
  color: #1f4e79;
  min-width: 80px;
}
.cmd-text {
  font-family: monospace;
  white-space: pre-line;
  word-break: break-all;
  color: #0f172a;
  flex: 1;
}

/* 复制按钮：更小、右下角悬浮 */
.cmd-copy-btn {
  position: absolute;
  right: 8px;
  bottom: 8px;
  transform: translateZ(0); /* 保证渲染清晰 */
}

.status-icon {
  margin-right: 4px;
}

.logs-container {
  border: 1px solid var(--el-border-color-light);
  border-radius: 4px;
  background: var(--el-fill-color-light);
  height: 180px;
  max-height: 180px;
  overflow: auto;
}

.logs-loading,
.logs-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 300px;
  color: var(--el-text-color-regular);
}

.logs-content {
  padding: 12px;
  margin: 0;
  font-family: "Courier New", monospace;
  font-size: 12px;
  line-height: 1.4;
  color: var(--el-text-color-primary);
  background: transparent;
  white-space: pre-wrap;
  word-break: break-word;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* 任务详情计划时间高亮红色且整体小20% */
.schedule-detail-row {
  background: #ffccc7;
  border-radius: 6px;
  padding: 1px 10px;
  margin-left: 1em;
  margin-top: -8px;
  margin-bottom: 12px;
  font-size: 80%;
  color: indianred;
  display: flex;
  align-items: center;
  width: fit-content;
}
</style>
