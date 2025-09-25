<template>
  <el-card class="task-info-card">
    <el-descriptions title="任务信息" :column="1" border>
      <template #extra>
        <el-button type="warning" plain @click="downloadTask(props.taskId)"
          >下载报告</el-button
        >
      </template>
      <el-descriptions-item
        label="任务ID"
        label-class-name="desc-label"
        width="120px"
      >
        <span class="font-bold">{{ task?.id || "-" }}</span>
      </el-descriptions-item>
      <el-descriptions-item label="状态" label-class-name="desc-label">
        <el-tag
          :type="getEnumEntry(taskStatusEnum, task?.status)?.type || 'info'"
          size="small"
        >
          {{ getLabel(taskStatusEnum, task?.status) }}
        </el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="数据来源" label-class-name="desc-label">
        <div class="source-info">
          <el-tag
            :type="task?.source_type === 'git' ? 'success' : 'info'"
            size="small"
            class="source-type-tag"
          >
            {{ task?.source_type === "git" ? "Git" : "上传" }}
          </el-tag>
          <span>{{ getSourceDisplay(task) }}</span>
        </div>
      </el-descriptions-item>
      <el-descriptions-item label="耗时" label-class-name="desc-label">{{
        task?.duration || "-"
      }}</el-descriptions-item>
      <el-descriptions-item label="图片总数" label-class-name="desc-label">{{
        task?.total_images
      }}</el-descriptions-item>
      <el-descriptions-item label="命中数" label-class-name="desc-label">{{
        task?.matched_images
      }}</el-descriptions-item>
      <el-descriptions-item label="匹配率" label-class-name="desc-label"
        >{{ task?.match_rate || 0 }}%</el-descriptions-item
      >
      <el-descriptions-item label="创建者" label-class-name="desc-label">{{
        task?.created_by || "-"
      }}</el-descriptions-item>
      <el-descriptions-item label="创建时间" label-class-name="desc-label">{{
        TimeDefault(task?.created_at)
      }}</el-descriptions-item>
      <el-descriptions-item
        label="备注"
        :span="2"
        label-class-name="desc-label"
      >
        <span
          :class="{
            'text-red-400': task?.remark
          }"
        >
          {{ task?.remark || "-" }}
        </span>
      </el-descriptions-item>
    </el-descriptions>
  </el-card>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { type OcrTask } from "@/api/ocr";
import { taskStatusEnum, getEnumEntry, getLabel } from "@/utils/enums";
import { TimeDefault } from "@/utils/time";
import { ocrTaskApi } from "@/api/ocr";
import { superRequest } from "@/utils/request";
import { useOcr } from "../utils/hook";

const { downloadTask } = useOcr();

const props = defineProps<{
  taskId: string;
}>();

const task = ref<OcrTask | null>(null);
const getSourceDisplay = (task: OcrTask) => {
  if (task?.source_type === "git") {
    return `${task?.git_repository_url} ${
      task?.git_branch ? `(${task?.git_branch})` : ""
    }`;
  }
  return "文件上传";
};

const refresh = async () => {
  if (!props.taskId) return;
  try {
    const res = await superRequest({
      apiFunc: ocrTaskApi.get,
      apiParams: props.taskId
    });
    console.log("task details:", res.data);
    task.value = res?.data || null;
  } catch (error) {
    console.error(error);
  }
};

watch(
  () => props.taskId,
  newId => {
    if (newId) {
      refresh();
    } else {
      task.value = null;
    }
  },
  { immediate: true }
);
</script>

<style lang="scss" scoped>
.task-info-card {
  .card-header {
    font-weight: bold;
  }

  .source-info {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .desc-label {
    width: 120px;
  }
}
</style>
